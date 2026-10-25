#!/usr/bin/env python3
"""Root replay of reviewed host controls; never selects a native command."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import unittest

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / "verification/apple-command-finalization-observer-v1"
receipt = json.loads((PRODUCER / "receipt.json").read_bytes())
sha = lambda data: hashlib.sha256(data).hexdigest()
assert receipt["passed"] and receipt["testsRun"] == 22
assert receipt["errors"] == receipt["failures"] == receipt["skipped"] == 0
for field in ("sourceFiles", "referenceFiles"):
    for name, expected in receipt[field].items():
        assert sha((ROOT / name).read_bytes()) == expected["sha256"], name
for name, expected in receipt["outputs"].items():
    assert sha((PRODUCER / name).read_bytes()) == expected["sha256"], name
sys.path.insert(0, str(PRODUCER))
spec = importlib.util.spec_from_file_location("root_observer_controls", PRODUCER / "test_observer.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.BASE = BASE


class RootReplay(module.ObserverTests):
    def tearDown(self):
        # Capture owned per-command diagnostics before TemporaryDirectory cleanup.
        destination = BASE / "cases" / self._testMethodName
        shutil.copytree(self.root, destination)
        for path in destination.rglob("observer.json"):
            observed = json.loads(path.read_text())
            if observed["PID"] is None:
                continue
            until = time.monotonic() + 2
            while True:
                try:
                    os.killpg(observed["PID"], 0)
                except ProcessLookupError:
                    break
                if time.monotonic() >= until:
                    self.fail("Root-owned process group remains after host control")
                time.sleep(.02)


selected = [
    "test_failure_cleanup_kills_closed_pipe_descendants_even_after_leader_exit",
    "test_successful_exit_and_eof_do_not_claim_owned_group_absence",
    "test_split_utf8_and_crlf_match_original_communicate_text_semantics",
    "test_inherited_pipe_timeout_signals_owned_group_even_after_main_exit",
    "test_suite_pass_text_never_shortcuts_timeout_or_cleanup",
    "test_each_stream_overflow_fails_closed_with_bounded_retained_bytes",
]
started = time.monotonic()
with (BASE / "tests.log").open("x") as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.TestSuite(RootReplay(name) for name in selected))
scratch = BASE / "scratch"
assert not list(scratch.iterdir())
scratch.rmdir()
for field in ("sourceFiles", "referenceFiles"):
    for name, expected in receipt[field].items():
        assert sha((ROOT / name).read_bytes()) == expected["sha256"], name
artifacts = {
    str(path.relative_to(BASE)): sha(path.read_bytes())
    for path in sorted((BASE / "cases").rglob("*")) if path.is_file()
}
passed = result.wasSuccessful() and result.testsRun == len(selected) and not result.skipped
acceptance = {
    "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "accepted-standalone-host-observer" if passed else "failed",
    "argv": sys.argv, "python": sys.version,
    "verifierSHA256": sha(Path(__file__).read_bytes()),
    "producerReceiptSHA256": sha((PRODUCER / "receipt.json").read_bytes()),
    "sourceTreeSHA256": receipt["sourceTreeSHA256"],
    "producerTests": 22, "rootReplayedMethods": selected,
    "rootPassed": result.testsRun - len(result.failures) - len(result.errors),
    "errors": len(result.errors), "failures": len(result.failures),
    "elapsedSeconds": time.monotonic() - started,
    "outputs": artifacts, "testsLogSHA256": sha((BASE / "tests.log").read_bytes()),
    "ownedScratchAbsent": not scratch.exists(),
    "rootOwnedProcessGroupsAbsent": passed,
    "correctedFinding": "Leader exit and pipe EOF do not prove process-group cleanup; failure cleanup now requires owned-group absence.",
    "runtimeSelected": False, "integrationPerformed": False, "nativeExecuted": False,
    "scope": "Root source review and focused host replay of producer controls; no independent native evidence.",
    "limitations": ["Historical Xcode finalization stall remains undiagnosed.",
                    "Observer is standalone and not yet integrated with a selected native runner.",
                    "No focus traversal, simulator, phone, FieldLog, signing or GA acceptance."]
}
(BASE / "acceptance.json").write_text(json.dumps(acceptance, indent=2) + "\n")
print(json.dumps({"passed": passed, "rootTests": result.testsRun,
                  "retainedArtifacts": len(artifacts), "nativeExecuted": False}))
raise SystemExit(0 if passed else 1)
