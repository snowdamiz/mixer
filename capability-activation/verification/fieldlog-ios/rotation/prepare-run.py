#!/usr/bin/env python3
"""Inspect or configure one generated FieldLog UI test run. Performs no device actions."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import uuid
from urllib.parse import urlsplit

SELECTOR = "FieldLogUITests/ChecklistJourney/testDevelopmentKeyRotation"
PLAN_SELECTOR = SELECTOR.split("/", 1)[1]

def spec(products, sdk):
    runs = list(products.glob("FieldLog_*.xctestrun"))
    if len(runs) != 1:
        raise ValueError(f"Expected one generated FieldLog XCTest plan in {products}, found {len(runs)}")
    document = plistlib.loads(runs[0].read_bytes())
    if "TestConfigurations" in document:
        targets = [target for configuration in document["TestConfigurations"]
                   if configuration.get("IsEnabled", True) for target in configuration["TestTargets"]]
    else:
        targets = [document.get("FieldLogUITests", {})]
    matches = [target for target in targets if target.get("IsEnabled", True)
               and target.get("BlueprintName") == "FieldLogUITests" and target.get("IsUITestBundle")]
    if len(matches) != 1:
        raise ValueError("Expected one enabled FieldLog UI target")
    target, = matches
    selectors = {PLAN_SELECTOR, PLAN_SELECTOR.split("/", 1)[0]}
    for key in ("OnlyTestIdentifiers", "SkipTestIdentifiers"):
        if key in target:
            values = target[key]
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise ValueError(f"Invalid {key} in {runs[0]}")
            selected = selectors.intersection(value.removesuffix("()") for value in values)
            if bool(selected) != (key == "OnlyTestIdentifiers"):
                raise ValueError(f"{key} excludes {SELECTOR} in {runs[0]}")
    paths = {}
    for key in ("UITargetAppPath", "TestHostPath", "TestBundlePath"):
        raw = target[key].replace("__TESTROOT__", str(products))
        if key == "TestBundlePath":
            raw = raw.replace("__TESTHOST__", str(paths["TestHostPath"]))
        path = Path(raw).resolve(strict=True)
        if not path.is_relative_to(products) or not path.is_dir():
            raise ValueError(f"Unexpected {key} in {runs[0]}")
        paths[key] = path
    info = plistlib.loads((paths["UITargetAppPath"] / "Info.plist").read_bytes())
    if info["CFBundleIdentifier"] != "dev.mixer.fieldlog" or info["DTPlatformName"] != sdk:
        raise ValueError("The app bundle or platform does not match the admitted target")
    bundle = paths["TestBundlePath"]
    if bundle.name != "FieldLogUITests.xctest":
        raise ValueError("The UI test bundle does not match FieldLog")
    executable = plistlib.loads((bundle / "Info.plist").read_bytes())["CFBundleExecutable"]
    if (Path(executable).name != executable or not (bundle / executable).resolve().is_relative_to(bundle)
            or not (bundle / executable).is_file()):
        raise ValueError("The UI test bundle executable is missing or escapes the bundle")
    return document, target, paths

def normalize_testroot(value, products):
    if isinstance(value, str):
        return value.replace("__TESTROOT__", str(products))
    if isinstance(value, list):
        return [normalize_testroot(item, products) for item in value]
    if isinstance(value, dict):
        return {key: normalize_testroot(item, products) for key, item in value.items()}
    return value

def endpoint(value):
    parts = urlsplit(value)
    if (parts.scheme != "http" or parts.hostname != "127.0.0.1" or parts.port is None
            or parts.port < 1024 or parts.path or parts.query or parts.fragment
            or parts.username is not None or parts.password is not None):
        raise ValueError("Expected a loopback-only HTTP origin on an unprivileged port")
    return f"http://127.0.0.1:{parts.port}"

def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdk", choices=("iphonesimulator",))
    parser.add_argument("products", type=Path)
    parser.add_argument("--origin-run", type=Path)
    parser.add_argument("--device-id")
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    products = args.products.resolve(strict=True)
    document, target, paths = spec(products, args.sdk)
    packet = Path(__file__).resolve().parent
    expected = packet / "fixture" / "Installed"
    installed = paths["UITargetAppPath"] / "ChecklistRelease"
    if {file.name for file in installed.iterdir()} != {file.name for file in expected.iterdir()}:
        raise ValueError("The app does not embed the admitted material set")
    for expected_file in expected.iterdir():
        if (installed / expected_file.name).read_bytes() != expected_file.read_bytes():
            raise ValueError(f"The app does not embed the admitted {expected_file.name}")
    if not any((args.origin_run, args.device_id, args.run_dir)):
        print(json.dumps({"scope": "bundle-layout-and-plan-filters", "requestedSelector": SELECTOR,
                          "sdk": args.sdk, **{k: str(v) for k, v in paths.items()}}, indent=2))
        return

    if not all((args.origin_run, args.device_id, args.run_dir)):
        parser.error("--origin-run, --device-id and a new --run-dir are required")
    device = str(uuid.UUID(args.device_id)).upper()
    fingerprints = {platform: json.loads((packet / "fixture" / "host.json").read_bytes())["runtime"]
                    for platform in ("ios",)}
    ready = json.loads((args.origin_run / "ready.json").read_bytes())
    if ready["fingerprints"] != fingerprints:
        raise ValueError("The origin is serving different platform runtime fingerprints")
    control_url, data_url = endpoint(ready["controlURL"]), endpoint(ready["dataURL"])
    if control_url == data_url:
        raise ValueError("The control and delivery origins must use separate ports")
    token = (args.origin_run / "control-token").read_text().strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise ValueError("Invalid fixture control token")
    target.setdefault("EnvironmentVariables", {}).update({
        "FIELDLOG_CHECKLIST_CONTROL_URL": control_url,
        "FIELDLOG_CHECKLIST_DATA_URL": data_url,
        "FIELDLOG_CHECKLIST_CONTROL_TOKEN": token,
    })
    target["OnlyTestIdentifiers"] = [PLAN_SELECTOR]
    target["ParallelizationEnabled"] = False
    target["UserAttachmentLifetime"] = "keepAlways"
    run_dir = args.run_dir.resolve()
    run_dir.mkdir()
    plan = run_dir / "FieldLog-checklist.xctestrun"
    with plan.open("xb") as stream:
        plistlib.dump(normalize_testroot(document, products), stream)
    command = ["xcodebuild", "test-without-building", "-xctestrun", str(plan),
               "-destination", f"platform=iOS Simulator,id={device}", "-parallel-testing-enabled", "NO",
               "-only-testing:" + SELECTOR, "-test-timeouts-enabled", "YES",
               "-maximum-test-execution-time-allowance", "360",
               "-resultBundlePath", str(run_dir / "checklist.xcresult")]
    print(shlex.join(command))

if __name__ == "__main__":
    main()
