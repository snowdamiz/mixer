#!/usr/bin/env python3
"""Retain bounded host controls and unavailable preflight; never dispatch Linux."""
import argparse
import ast
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("resource_controller", HERE / "run.py")
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    if not args.attempt.isdecimal():
        raise SystemExit("attempt must be numeric")
    attempt = HERE / ("host-attempt-" + args.attempt)
    attempt.mkdir(mode=0o700)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    inputs = {str((HERE / name).relative_to(ROOT)): controller.sha(HERE / name)
              for name in (*controller.HARNESS_FILES, "test_host.py", "author.py", "verify.py")}
    doc = ROOT / "docs/stripe-webhook-linux-resource-harness.md"
    inputs[str(doc.relative_to(ROOT))] = controller.sha(doc)
    for name in ("run.py", "test_host.py", "author.py", "verify.py"):
        ast.parse((HERE / name).read_text(), filename=name)
    test_argv = [sys.executable, "-B", str(HERE / "test_host.py")]
    tests = subprocess.run(test_argv, capture_output=True, text=True, timeout=30,
                           env={"PATH": os.defpath, "LANG": "C"}, cwd=ROOT)
    (attempt / "host-tests.log").write_text(tests.stdout + tests.stderr)
    preflight_dir = HERE / "results" / ("author-preflight-" + args.attempt)
    preflight_argv = [sys.executable, "-B", str(HERE / "run.py"), "--output", str(preflight_dir)]
    preflight = subprocess.run(preflight_argv, capture_output=True, text=True, timeout=30,
                               env={"PATH": os.defpath, "LANG": "C"}, cwd=ROOT)
    (attempt / "preflight.log").write_text(preflight.stdout + preflight.stderr)
    commands = []
    for label, argv in (("python", [sys.executable, "--version"]), ("cc-version-only", ["/usr/bin/cc", "--version"]),
                        ("uname", ["/usr/bin/uname", "-a"])):
        p = subprocess.run(argv, capture_output=True, text=True, timeout=30,
                           env={"PATH": os.defpath, "LANG": "C"}, cwd=ROOT)
        commands.append({"label": label, "argv": argv, "exitCode": p.returncode,
                         "stdout": p.stdout, "stderr": p.stderr,
                         "executableSha256": controller.sha(Path(argv[0]).resolve())})
    tools = {"schema": 1, "observedUTC": now, "system": platform.platform(),
             "machine": platform.machine(), "commands": commands,
             "LinuxCompilePerformed": False, "MacBEAMUsedAsLinuxArtifact": False,
             "softwareInstalled": False, "daemonsContacted": False}
    write(attempt / "tools.json", tools)
    selected = controller.load(controller.CONTRACT / "matrix.json")
    coverage = []
    for row in selected["rows"]:
        coverage.append({**row, "status": "pending-runtime", "runtimeExecuted": False,
                         "implementation": "bounded-candidate-driver-independent-review-pending"
                         if row["id"] in controller.EXECUTABLE_CASES else "comprehensive-driver-pending"})
    write(HERE / "matrix.json", {"schema": 1, "selectionSHA256": controller.SELECTION_SHA,
                                "runtimeCasesExecuted": 0, "gaAccepted": False, "rows": coverage})
    summary = controller.load(preflight_dir / "summary.json")
    test_text = tests.stdout + tests.stderr
    tests_ok = tests.returncode == 0 and "Ran 17 tests" in test_text and "OK (skipped=2)" in test_text
    expected_unavailable = preflight.returncode == 78 and summary["counts"] == {
        "passed": 0, "failed": 0, "unavailable": 18} and summary["runtimeCasesExecuted"] == 0
    receipt = {"schema": 1, "status": "passed-host-controls-linux-unavailable-implementation-incomplete"
               if tests_ok and expected_unavailable else "failed-host-authoring-checks",
               "observedUTC": now, "cwd": str(ROOT), "sourceRevisionContextOnly":
               controller.load(ROOT / "verification/stripe-webhook-resource-ingress-root-review/selection.json")["sourceRevisionContext"],
               "gitOperations": False, "sourceInputs": inputs, "sourceTreeDigest": controller.digest(inputs),
               "acceptedSourceDigest": controller.SOURCE_SHA,
               "selectedClosureDigest": controller.digest(controller.source_inputs()),
               "harnessDigest": controller.harness_digest(), "profileDigest": controller.PROFILE_SHA,
               "commands": [{"argv": test_argv, "exitCode": tests.returncode,
                             "output": str((attempt / "host-tests.log").relative_to(ROOT))},
                            {"argv": preflight_argv, "exitCode": preflight.returncode,
                             "output": str((attempt / "preflight.log").relative_to(ROOT))}],
               "hostTests": {"run": 17, "passed": 15 if tests_ok else None, "skipped": 2 if tests_ok else None},
               "hostScope": "Python guards, safe-schema reconstruction and Unix DGRAM ancillary fixture only; no selected Linux channel or resource acceptance",
               "runtimeCasesExecuted": 0, "LinuxCOrNIFOrBEAMCompiled": False,
               "implementedCandidateDriverIds": sorted(controller.EXECUTABLE_CASES),
               "incompleteComprehensiveDriverIds": sorted(set(controller.CASES) - controller.EXECUTABLE_CASES),
               "independentReview": "pending", "gaAccepted": False, "publicTrailerPolicy": "unselected",
               "cleanup": {"roleStarted": False, "listenerStarted": False, "cgroupCreated": False,
                           "namespaceCreated": False, "stressHelperStarted": False, "databaseStarted": False,
                           "daemonStarted": False, "nativeInstanceStarted": False, "providerContacted": False,
                           "testSocketsClosed": True, "temporaryTestDirectoriesRemoved":
                           not any(HERE.glob("mixer-resource-host-control-*")),
                           "ownedRuntimeScratchCreated": False,
                           "retainedFailures": ["host-attempt-1", "results/macos-preflight-attempt-1"]}}
    write(attempt / "receipt.json", receipt)
    write(HERE / "authoring-receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in ("status", "hostTests", "runtimeCasesExecuted", "independentReview")}))
    return 0 if tests_ok and expected_unavailable else 1


if __name__ == "__main__":
    sys.exit(main())
