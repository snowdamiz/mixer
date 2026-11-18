#!/usr/bin/env python3
"""Verify immutable FieldLog anchors and run the original tests against pinned public SDKs."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

MANIFEST = Path(__file__).with_name("corpus.json")
LIMIT = 600 * 1024**2


def capture(*args):
    return subprocess.check_output(args, stdin=subprocess.DEVNULL)


def git(repo, *args):
    return capture("git", "-C", repo, *args)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def oid(repo, ref):
    return git(repo, "rev-parse", "--verify", ref).decode().strip()


def tree_blob(repo, rev, path):
    row = git(repo, "ls-tree", "-r", rev, "--", path)
    return row.split()[2].decode() if row else None


def verify_history(repo, manifest, output):
    pin = manifest["pin"]
    assert oid(repo, pin + "^{tree}") == manifest["pinTree"]
    ancestry = set(git(repo, "rev-list", pin).decode().splitlines())
    assert len(ancestry) == manifest["historySize"]
    assert len(manifest["cases"]) == len({case["id"] for case in manifest["cases"]}) == 20
    with output.open("x") as log:
        for case in manifest["cases"]:
            before, after = case["before"], case["after"]
            assert after in ancestry and oid(repo, after + "^") == before
            log.write(f'{case["id"]} {case["change"]}\n{before} -> {after}\n')
            for anchor in case["anchors"]:
                path = anchor["path"]
                old, new = (tree_blob(repo, rev, path) for rev in (before, after))
                assert (old, new) == (anchor["beforeBlob"], anchor["afterBlob"])
                assert old != new and new
                start, end = anchor["afterLines"]
                lines = git(repo, "cat-file", "blob", new).splitlines(keepends=True)
                assert 1 <= start <= end <= len(lines)
                excerpt = b"".join(lines[start - 1:end])
                assert digest(excerpt) == anchor["afterLinesSHA256"]
                log.write(f"{path}:{start}-{end}\n{excerpt.decode()}\n")


def extract(repo, tree, dest, *paths):
    dest.mkdir()
    source = git(repo, "archive", "--format=tar", tree, *paths)
    with tarfile.open(fileobj=io.BytesIO(source)) as archive:
        archive.extractall(dest, filter="data")
    return digest(source)


def command(output, name, argv, env=None):
    path = output / (name + ".log")
    with path.open("xb") as log:
        run = subprocess.run(argv, env=env, stdin=subprocess.DEVNULL, stdout=log,
                             stderr=subprocess.STDOUT, check=False)
    return {"argv": [str(arg) for arg in argv], "exit": run.returncode, "log": path.name,
            "logSHA256": digest(path.read_bytes())}


def scratch_bytes(path):
    return int(capture("du", "-sk", path).split()[0]) * 1024


def swift_suite(args, receipt, name, pins):
    fieldlog_pin, sdk_pin = pins
    suite = args.output / name
    suite.mkdir()
    app, sdk, build, cache, tmp, workspaces = (
        suite / subdir for subdir in ("app", "mixer", "build", "cache", "tmp", "workspaces")
    )
    tmp.mkdir()
    workspaces.mkdir()
    generated = name == "generated-pin"
    app_tree = f"{fieldlog_pin}:Integrations/GeneratedReport" if generated else fieldlog_pin
    sdk_tree = f"{sdk_pin}:sdk" if generated else sdk_pin
    sdk_paths = () if generated else ("Package.swift", "sdk")
    row = receipt["suites"][name] = {
        "fieldlog": fieldlog_pin, "sdk": sdk_pin, "sdkTree": oid(args.mixer, f"{sdk_pin}:sdk"),
        "fieldlogArchiveSHA256": extract(args.fieldlog, app_tree, app),
        "sdkArchiveSHA256": extract(args.mixer, sdk_tree, sdk, *sdk_paths)
    }
    env = dict(os.environ, TMPDIR=str(tmp), SWIFTPM_MODULECACHE_OVERRIDE=str(cache / "modules"),
               FIELDLOG_WORKSPACE=str(workspaces), GIT_TERMINAL_PROMPT="0")
    if generated:
        env["FIELDLOG_MIXER_SDK"] = str(sdk)
        row["locator"] = "Documented FIELDLOG_MIXER_SDK"
    else:
        manifest_path = app / "Package.swift"
        original = manifest_path.read_text()
        remote = f'.package(url: "https://github.com/snowdamiz/mixer.git", revision: "{sdk_pin}")'
        assert original.count(remote) == 1
        local = original.replace(remote, '.package(name: "mixer", path: "../mixer")')
        manifest_path.write_text(local)
        row["locator"] = "Private package locator rewrite only, to the exact pinned public package"
        row["packageSHA256"] = {"original": digest(original.encode()), "local": digest(local.encode())}
    row["command"] = command(args.output, name,
        ["swift", "test", "--package-path", app, "--scratch-path", build,
         "--cache-path", cache, "--jobs", "4"], env)
    log = (args.output / row["command"]["log"]).read_text()
    row["passedXCTests"] = re.findall(r"^Test Case '-\[[^ ]+ (\w+)\]' passed", log, re.M)
    row["passedSwiftTests"] = re.findall(r"^✔ Test (\w+)\(.*? passed", log, re.M)
    if name in ("task-presentation", "ordinary-pin"):
        manifest_path = app / "Package.swift"
        driver = app / "Sources/GuestProfileProbe"
        driver.mkdir()
        harness = Path(__file__).with_name("GuestProfileProbe.swift")
        shutil.copyfile(harness, driver / harness.name)
        settings = (
            ', .product(name: "MixerGuest", package: "mixer")], '
            'swiftSettings: [.define("CHECK_GUEST_V1")]'
            if name == "ordinary-pin" else "]"
        )
        with manifest_path.open("a") as file:
            file.write(
                '\npackage.targets.append(.executableTarget(name: "GuestProfileProbe", '
                'dependencies: ["FieldLogFeatures", .product(name: "MixerUI", package: "mixer")'
                + settings + "))\n"
            )
        row["profileProbe"] = command(args.output, name + "-profile",
            ["swift", "run", "--package-path", app, "--scratch-path", build, "--cache-path", cache,
             "--jobs", "4", "GuestProfileProbe", args.output / "f05-frame.json"], env)
        row["profileProbe"]["testSourceSHA256"] = digest(harness.read_bytes())
        row["profileProbe"]["testManifestSHA256"] = digest(manifest_path.read_bytes())
    row["observedBytesBeforeBuildCleanup"] = scratch_bytes(args.output)
    assert row["observedBytesBeforeBuildCleanup"] <= LIMIT, "600 MiB scratch limit exceeded"
    if row.get("profileProbe", {"exit": row["command"]["exit"]})["exit"] == 0:
        for directory in (build, cache, tmp):
            if directory.exists():
                shutil.rmtree(directory)
    return suite


def jvm_checks(args, suite):
    app = suite / "app"
    source, classes = suite / "java-source", suite / "classes"
    classes.mkdir()
    commands = [
        ("java-extract", ["python3", app / "scripts/prepare-report-files-tests.py", "--output", source]),
        ("java-build", [args.jdk / "bin/javac", "-encoding", "UTF-8", "-d", classes,
                        source / "PublicBridge.java", app / "Tests/ReportFilesJava/ReportFilesChecks.java"]),
        ("java-run", [args.jdk / "bin/java", "-cp", classes,
                      "dev.fieldlog.generatedr90.androidhost.ReportFilesChecks", suite / "report-workspace"])
    ]
    results = []
    for name, argv in commands:
        results.append(command(args.output, name, argv))
        if results[-1]["exit"] != 0:
            break
    return results


def main():
    if not __debug__:
        raise SystemExit("Run Python without optimization so the manifest assertions execute.")
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fieldlog", "mixer", "output", "jdk"):
        parser.add_argument("--" + name, type=lambda path: Path(path).resolve(), required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(MANIFEST.read_bytes())
    receipt = {"schema": 1, "status": "INCOMPLETE", "manifestSHA256": digest(MANIFEST.read_bytes()),
               "suites": {}, "tools": {
                   "swift": capture("swift", "--version").decode().strip(),
                   "git": capture("git", "--version").decode().strip(),
                   "java": capture(args.jdk / "bin/java", "--version").decode().strip(),
                   "system": capture("sw_vers").decode().strip()},
               "mixerObservationRevision": oid(args.mixer, "HEAD"),
               "signedOTAProven": 0, "deviceRuns": 0}
    try:
        verify_history(args.fieldlog, manifest, args.output / "source-excerpts.txt")
        receipt["historyAnchorsVerified"] = len(manifest["cases"])
        for name, pins in manifest["suitePins"].items():
            swift_suite(args, receipt, name, pins)
        receipt["jvm"] = jvm_checks(args, args.output / "generated-pin")
        receipt["cases"] = []
        for case in manifest["cases"]:
            controls = []
            for selector in case["hostSelectors"]:
                suite = receipt["suites"][selector["suite"]]
                passed = suite["passedXCTests"] + suite["passedSwiftTests"]
                controls.append(dict(selector, passed=selector["name"] in passed, suiteExit=suite["command"]["exit"]))
            receipt["cases"].append({"id": case["id"], "hostControls": controls,
                                     "inOTADenominator": case["inOTADenominator"], "signedOTAProven": False})
        receipt["eligibleCases"] = sum(case["inOTADenominator"] for case in receipt["cases"])
        receipt["casesWithPassingHostControls"] = sum(bool(case["hostControls"]) and all(
            control["passed"] for control in case["hostControls"]) for case in receipt["cases"])
        suite_failures = [name for name, suite in receipt["suites"].items() if suite["command"]["exit"]]
        receipt["nonzeroWholeSuites"] = suite_failures
        receipt["guestProfileProbePassed"] = all(
            receipt["suites"][name]["profileProbe"]["exit"] == 0
            for name in ("task-presentation", "ordinary-pin"))
        passed_jvm = len(receipt["jvm"]) == 3 and all(step["exit"] == 0 for step in receipt["jvm"])
        passed_cases = all(control["passed"] for case in receipt["cases"] for control in case["hostControls"])
        receipt["status"] = (
            ("SCOPED_CONTROLS_PASS_WITH_HISTORICAL_SUITE_FAILURE" if suite_failures else "PASS_SCOPED_HOST_CONTROLS")
            if passed_cases and receipt["guestProfileProbePassed"] and passed_jvm
            else "HOST_CONTROL_FAILURE"
        )
    finally:
        receipt["retainedScratchBytes"] = scratch_bytes(args.output)
        (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return int(receipt["status"] != "PASS_SCOPED_HOST_CONTROLS")


if __name__ == "__main__":
    raise SystemExit(main())
