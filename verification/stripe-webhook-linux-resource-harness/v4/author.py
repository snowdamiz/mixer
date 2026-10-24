#!/usr/bin/env python3
"""Capture v4 actual-adapter/session controls and unavailable preflight only."""
import argparse
import ast
import datetime
import json
from pathlib import Path
import platform
import subprocess
import sys

import checkpoint
import lifecycle as life
import run as candidate

HERE = Path(__file__).resolve().parent
ROOT = checkpoint.ROOT
base = candidate.base


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def source_table():
    rows = []
    for row in candidate.fault_table():
        stage = life.Stage(row["stage"])
        if row["component"] == "controller":
            name, anchor = "linux_backend.py", f"mark(life.Stage.{stage.name})"
        elif row["component"] == "launcher":
            name, anchor = "fault_helper.c", f'lifecycle({int(stage)}, "{stage.name.lower()}")'
        else:
            name, anchor = "role.exs", f'hook("{stage.name.lower()}")'
        lines = (HERE / name).read_text().splitlines()
        locations = [n for n, line in enumerate(lines, 1) if anchor in line]
        assert locations, (stage, anchor)
        rows.append({**row, "source": name, "sourceSha256": base.sha(HERE / name),
                     "sourceLines": locations, "sourceAnchor": anchor,
                     "runtimeReached": False, "runtimeReview": "pending"})
    return {"schema": 1, "status": "source-contract-mapping-only-runtime-unverified", "faultEnumDigest": base.digest(candidate.fault_table()),
            "phaseNames": list(life.PHASES), "rows": rows, "runtimeRowsExecuted": 0,
            "independentEnumReview": "pending"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    assert args.attempt.isdecimal()
    attempt = HERE / ("host-attempt-" + args.attempt)
    attempt.mkdir(mode=0o700)
    sources = {name: base.sha(HERE / name) for name in (*candidate.SOURCES, "test_host.py", "test_repairs.py", "test_v4.py", "author.py", "verify.py", "README.md")}
    for name in ("run.py", "linux_backend.py", "proc_inventory.py", "lifecycle.py", "checkpoint.py", "test_host.py", "test_repairs.py", "test_v4.py", "author.py", "verify.py"):
        ast.parse((HERE / name).read_text(), filename=name)
    write(HERE / "contract-table.json", source_table())
    # unittest output is a host control diagnostic; no role output is obtained.
    test_code = ("import json,unittest,test_host,test_repairs,test_v4; r=unittest.TextTestRunner(verbosity=2).run("
                 "unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(test_host),"
                 "unittest.defaultTestLoader.loadTestsFromModule(test_repairs),"
                 "unittest.defaultTestLoader.loadTestsFromModule(test_v4)])); "
                 "print(json.dumps({'run':r.testsRun,'passed':r.testsRun-len(r.failures)-len(r.errors)-len(r.skipped),"
                 "'failed':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped)})); "
                 "raise SystemExit(0 if r.wasSuccessful() else 1)")
    test_argv = [sys.executable, "-B", "-c", test_code]
    tests = subprocess.run(test_argv, cwd=HERE, capture_output=True, text=True, timeout=30)
    (attempt / "host-tests.log").write_text(tests.stdout + tests.stderr)
    counts = json.loads(tests.stdout.strip().splitlines()[-1])
    preflight_dir = HERE / "results" / ("author-preflight-" + args.attempt)
    preflight_argv = [sys.executable, "-B", str(HERE / "run.py"), "--output", str(preflight_dir)]
    preflight = subprocess.run(preflight_argv, cwd=ROOT, capture_output=True, text=True, timeout=30)
    (attempt / "preflight.log").write_text(preflight.stdout + preflight.stderr)
    summary = base.load(preflight_dir / "summary.json")
    okay = tests.returncode == 0 and counts == {"run": 66, "passed": 66, "failed": 0, "errors": 0, "skipped": 0} \
        and preflight.returncode == 78 and summary["counts"] == {"passed": 0, "failed": 0, "unavailable": 18} \
        and summary["runtimeRowsExecuted"] == 0
    receipt = {"schema": 1, "status": "passed-host-controls-only-linux-runtime-unavailable" if okay else "failed-host-controls",
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "sourceInputs": sources,
        "sourceTreeDigest": base.digest(sources), "harnessDigest": candidate.harness_digest(),
        "profileDigest": base.PROFILE_SHA, "sourceDigest": base.SOURCE_SHA,
        "selectedClosureDigest": base.digest(base.source_inputs()), "faultEnumDigest": base.digest(candidate.fault_table()),
        "v1Checkpoint": checkpoint.verify(), "amendmentSha256": base.sha(candidate.AMENDMENT),
        "signalAmendmentSha256": base.sha(candidate.SIGNAL_AMENDMENT),
        "repairSelectionSha256": base.sha(candidate.REPAIR_SELECTION),
        "v4RepairSelectionSha256": base.sha(candidate.V4_REPAIR_SELECTION),
        "repairedFindings": ["V3-F1: mandatory owned-PID pid_for_children reference inventory", "V3-F2: immutable cleanup-attempt observations and sticky first failure"],
        "preservedSources": {name: base.sha(HERE / name) for name in ("control_nif.c", "fault_helper.c", "role.exs", "signal-authority.json")},
        "sourceRevisionContextOnly": {"selectedContract": "bbed074d3bd2453bbcc0807f05219d042cedd738",
                                      "rootReportedMain": "cf52825", "gitOperationPerformed": False},
        "tools": {"python": sys.version, "pythonExecutableSha256": base.sha(Path(sys.executable).resolve()),
                  "platform": platform.platform(), "compilerRun": False, "LinuxCOrNIFOrBEAMCompiled": False},
        "commands": [{"argv": test_argv, "cwd": str(HERE), "exitCode": tests.returncode,
                       "output": str((attempt / "host-tests.log").relative_to(ROOT))},
                     {"argv": preflight_argv, "cwd": str(ROOT), "exitCode": preflight.returncode,
                       "output": str((attempt / "preflight.log").relative_to(ROOT))}],
        "hostTests": counts, "hostScope": "actual ProcMetadata with low-level OS mocks and actual Session cleanup sequences; inherited scheduling/metadata models, validators, mocked pidfd fences and immutable bindings; no live proc or Linux enforcement",
        "repairHostControls": 14, "inheritedHostControls": 52,
        "runtimeRowsExecuted": 0, "r14SourcePhaseNames": list(life.PHASES), "r18SourceFaultBoundaries": 34,
        "independentImplementationAndEnumReview": "pending", "implementationComplete": False,
        "gaAccepted": False, "publicTrailerPolicy": "unselected", "dependenciesAdded": [],
        "cleanup": {"roleStarted": False, "stressHelperStarted": False, "listenerStarted": False,
                    "cgroupCreated": False, "namespaceCreated": False, "runtimeScratchCreated": False,
                    "daemonStarted": False, "nativeInstanceStarted": False, "providerContacted": False,
                    "ownedScratchRemains": bool(list(HERE.glob(".owned-scratch-*")))}}
    write(attempt / "receipt.json", receipt)
    write(HERE / "authoring-receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in ("status", "hostTests", "runtimeRowsExecuted", "independentImplementationAndEnumReview")}))
    return 0 if okay else 1


if __name__ == "__main__":
    sys.exit(main())
