"""Reproduce only this lane's source/host controls; never selects a native run."""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import stat
import sys
import time
import unittest


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
REFERENCE_FILES = [
    ROOT / "verification/apple-toggle-keyboard-full-case-preparation-v3/inputs/runtime/verification/apple-toggle-pan-origin-correction/harness.py",
    ROOT / "docs/apple-toggle-keyboard-v3-failure-analysis.md",
]
SOURCE_FILES = [BASE / name for name in ("observer.py", "test_observer.py", "verify.py")]
SOURCE_FILES.append(ROOT / "docs/apple-command-finalization-observer-v1.md")


def manifest(paths):
    result = {}
    for path in paths:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Expected ordinary source file: " + str(path))
        data = path.read_bytes()
        result[str(path.relative_to(ROOT))] = {
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
            "mode": format(stat.S_IMODE(info.st_mode), "04o")}
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-revision-context", required=True,
                        help="Root supplied context label only; no Git operation is performed")
    args = parser.parse_args()
    before = manifest(SOURCE_FILES)
    references_before = manifest(REFERENCE_FILES)
    stdout, stderr = io.StringIO(), io.StringIO()
    started = time.monotonic()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        suite = unittest.defaultTestLoader.discover(str(BASE), pattern="test_observer.py")
        result = unittest.TextTestRunner(stream=stderr, verbosity=2).run(suite)
    after = manifest(SOURCE_FILES)
    references_after = manifest(REFERENCE_FILES)
    scratch = BASE / "scratch"
    scratch_entries = sorted(path.name for path in scratch.iterdir()) if scratch.exists() else []
    if scratch.exists() and not scratch_entries:
        scratch.rmdir()
    passed = (result.wasSuccessful() and result.testsRun > 0 and not result.skipped
              and before == after and references_before == references_after and not scratch_entries)
    logs = {"host-tests.stdout.log": stdout.getvalue(), "host-tests.stderr.log": stderr.getvalue()}
    for name, value in logs.items():
        (BASE / name).write_text(value, encoding="utf-8")
    receipt = {
        "schema": "mixer.apple-command-finalization-observer-host.1",
        "recordedUTC": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command": [sys.executable, "-B", str(Path(__file__).resolve()),
                    "--source-revision-context", args.source_revision_context],
        "cwd": os.getcwd(), "sourceRevisionContext": args.source_revision_context,
        "sourceRevisionMeaning": "root-supplied context label; exact source manifest includes uncommitted lane changes",
        "sourceFiles": before, "sourceTreeSHA256": digest(before),
        "referenceFiles": references_before, "referenceTreeSHA256": digest(references_before),
        "sourceFilesUnchangedDuringTests": before == after,
        "referenceFilesUnchangedDuringTests": references_before == references_after,
        "tools": {"python": {"version": sys.version, "executable": str(Path(sys.executable).resolve()),
                              "executableSHA256": hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()},
                  "platform": platform.platform()},
        "outputs": {name: {"sha256": hashlib.sha256(value.encode()).hexdigest(),
                           "bytes": len(value.encode())} for name, value in logs.items()},
        "testsRun": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skipped": len(result.skipped),
        "elapsedSeconds": time.monotonic() - started, "passed": passed,
        "scope": "standalone stdlib orchestration observer; harmless owned host Python children only",
        "runtimeSelection": False, "nativeExecution": False, "nativeAcceptanceGranted": False,
        "authorityOrCatalogImported": False, "integrationPerformed": False,
        "simulatorOrDeviceOperations": False, "physicalPhones": "disconnected-deferred",
        "gaAccepted": False,
        "cleanup": {"ownedScratchDirectoryAbsent": not scratch.exists(),
                    "unexpectedOwnedScratchEntries": scratch_entries,
                    "processScope": "only owned child PID and its start_new_session process group"},
        "limitations": [
            "Host controls do not identify the historical Xcode stall's causal subsystem.",
            "No native command, build, runtime selection, simulator, device, UI or capture operation was performed.",
            "Observer is not integrated with any selected harness or authority/catalog lane.",
            "Result marker presence and selected-suite console text never establish test or release acceptance.",
            "Output exceeding a configured stream cap raises rather than returning truncated success.",
        ],
    }
    (BASE / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": passed, "testsRun": result.testsRun,
                      "sourceTreeSHA256": receipt["sourceTreeSHA256"],
                      "nativeExecution": False, "runtimeSelection": False}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
