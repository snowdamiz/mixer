#!/usr/bin/env python3
"""Verify the built FieldLog app, XCTest bundle and test selector without a device."""

import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
import sys


SELECTOR = "testOrdinarySavedDraftPinAndSettingsSurviveColdLaunch"
CONFIGURATION = "Debug-iphonesimulator"
PLAN = "FieldLog_iphonesimulator27.2-arm64.xctestrun"


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def require(condition, description):
    if not condition:
        raise SystemExit(f"Build verification failed: {description}")


def sha256(file):
    with file.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_bundle(bundle, identity):
    info = bundle / "Info.plist"
    properties = plistlib.loads(info.read_bytes())
    require(properties["CFBundleIdentifier"] == identity, f"{bundle.name} bundle identity")
    require(properties["CFBundleVersion"] == "1", f"{bundle.name} build number")
    binary = bundle / properties["CFBundleExecutable"]
    require(command("xcrun", "lipo", "-archs", binary).strip() == "arm64", f"{bundle.name} CPU")
    platform = command("xcrun", "vtool", "-show-build", binary)
    require(re.search(r"^\s*platform IOSSIMULATOR\s*$", platform, re.MULTILINE),
            f"{bundle.name} Mach-O platform")
    command("codesign", "--verify", "--deep", "--strict", "-R", f'=identifier "{identity}"', bundle)
    signing = subprocess.run(["codesign", "-dvvv", bundle], check=True,
                             capture_output=True, text=True).stderr
    fields = dict(line.split("=", 1) for line in signing.splitlines() if "=" in line)
    require(fields.get("Signature") == "adhoc", f"{bundle.name} ad hoc signature")
    return binary, {
        "id": identity,
        "version": properties.get("CFBundleShortVersionString"),
        "build": properties["CFBundleVersion"],
        "architecture": "arm64",
        "platform": "IOSSIMULATOR",
        "executableSHA256": sha256(binary),
        "infoPlistSHA256": sha256(info),
        "signature": "adhoc",
        "codeDirectoryHash": fields["CDHash"],
        "strictSignatureVerified": True,
    }


def main(products):
    plan = products / PLAN
    target = plistlib.loads(plan.read_bytes())["FieldLogUITests"]
    runner = "FieldLogUITests-Runner.app"
    test_bundle = "FieldLogUITests.xctest"
    require(target.get("IsUITestBundle") is True and
            target.get("IsXCTRunnerHostedTestBundle") is True and
            target.get("ProductModuleName") == "FieldLogUITests" and
            target.get("UITargetAppPath") == f"__TESTROOT__/{CONFIGURATION}/FieldLog.app" and
            target.get("TestHostPath") == f"__TESTROOT__/{CONFIGURATION}/{runner}" and
            target.get("TestBundlePath") == f"__TESTHOST__/PlugIns/{test_bundle}" and
            target.get("TestHostBundleIdentifier") == "dev.mixer.fieldlog.uitests.xctrunner",
            "test plan UI host, app and test bundle bindings")

    configuration = products / CONFIGURATION
    _, app = verify_bundle(configuration / "FieldLog.app", "dev.mixer.fieldlog")
    require(app["version"] == "0.1.0", "FieldLog marketing version")
    _, runner_info = verify_bundle(configuration / runner, "dev.mixer.fieldlog.uitests.xctrunner")
    test, test_info = verify_bundle(configuration / runner / "PlugIns" / test_bundle,
                                    "dev.mixer.fieldlog.uitests")

    objc = command("xcrun", "otool", "-ov", test)
    require(re.search(rf"^\s*(?:name\s+)?(?:0x)?[a-f0-9]+\s+{SELECTOR}$", objc, re.MULTILINE),
            "exact Objective-C XCTest selector")
    symbols = subprocess.run(["xcrun", "swift-demangle"], input=command("xcrun", "nm", test),
                             check=True, capture_output=True, text=True).stdout
    require("FieldLogUITests.FieldLogUITests." + SELECTOR + "() -> ()" in symbols,
            "compiled Swift implementation on the FieldLogUITests class")

    print(json.dumps({
        "plan": PLAN, "planSHA256": sha256(plan),
        "selector": "FieldLogUITests/FieldLogUITests/" + SELECTOR,
        "executableObjCSelector": SELECTOR,
        "app": app, "runner": runner_info, "testBundle": test_info,
    }, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
