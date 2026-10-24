#!/usr/bin/env python3
"""Qualify unchanged run-1 product outputs after summary-parser-only failure."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / "run-1"
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
original = read(RUN / "receipt.json")
hosted = read(RUN / "hosted/receipt.json")
assert original["status"] == "failed" and hosted["status"] == "passed"
assert hosted["inputs"] == original["sourceInputs"]
assert hosted["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
assert original["cleanup"]["isolatedCheckoutRemoved"]
assert sha(RUN / "collector-source.py") == original["collectorInputs"][str((HERE / "run.py").relative_to(ROOT))]
for name, expected in original["collectorInputs"].items():
    if name != str((HERE / "run.py").relative_to(ROOT)):
        assert sha(ROOT / name) == expected, name
for command in original["commands"]:
    assert command["exitCode"] == 0
    assert sha(RUN / command["log"]) == command["sha256"]
for command in hosted["commands"]:
    assert command["exit_code"] == command.get("expected_exit_code", 0)
    assert sha(RUN / "hosted" / command["log"]) == command["sha256"]
with tarfile.open(RUN / "source.tar.gz") as tar:
    entries = {m.name: hashlib.sha256(tar.extractfile(m).read()).hexdigest()
               for m in tar.getmembers() if m.isfile()}
assert entries == original["sourceInputs"]
assert sha(RUN / "hosted/source.tar.gz") == hosted["source_archive_sha256"]
with tarfile.open(RUN / "hosted/source.tar.gz") as tar:
    assert {m.name: hashlib.sha256(tar.extractfile(m).read()).hexdigest()
            for m in tar.getmembers() if m.isfile()} == entries
spec = importlib.util.spec_from_file_location("integration_collector", HERE / "run.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.test_summary("Result: 73 passed, 1 skipped\n") == (74, 0, 1)
assert module.test_summary("74 tests, 0 failures, 1 skipped\n") == (74, 0, 1)
assert module.test_summary("74 tests, 2 failures, 1 skipped\n") == (74, 2, 1)
for malformed in ["Result: 73 passed, 1 failed, 1 skipped", "Result: 73 passed", ""]:
    try:
        module.test_summary(malformed)
    except ValueError:
        pass
    else:
        raise AssertionError(malformed)
assert module.test_summary((RUN / "hosted/tests.log").read_text()) == (74, 0, 1)
for name in ["signed-release-v3.json", "release-v3-cases.json"]:
    path = "services/protocol/testdata/" + name
    assert entries[path] == sha(ROOT / path)
receipt = {
    "schema": 1,
    "status": "passed-root-composed-host-checks-original-summary-parser-failure-retained",
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "baseRevision": original["baseRevision"],
    "originalRunReceiptSHA256": sha(RUN / "receipt.json"),
    "hostedReceiptSHA256": sha(RUN / "hosted/receipt.json"),
    "originalCollectorSHA256": sha(RUN / "collector-source.py"),
    "correctedCollectorSHA256": sha(HERE / "run.py"),
    "postprocessorSHA256": sha(Path(__file__).resolve()),
    "sourceInputs": entries,
    "sourceArchiveSHA256": sha(RUN / "source.tar.gz"),
    "qualification": {"passedTests": 73, "skippedTests": 1, "failedTests": 0,
                      "formatPassed": True, "productionReleaseBuilt": True,
                      "missingConfigurationRejected": True,
                      "bothSharedProtocolFixturesBound": True},
    "failureExplanation": "All product commands and PostgreSQL cleanup passed. Root's postprocessor expected the older ExUnit summary syntax; Elixir1.20 emitted Result:73 passed,1 skipped. Only parsing changed, with positive and negative parser controls. No product test was rerun or relabeled.",
    "excluded": original["excluded"],
    "cleanup": original["cleanup"],
    "componentAcceptance": "Separate root component decisions required",
    "scope": original["scope"],
}
destination = HERE / "completion.json"
assert not destination.exists(), "Preserve append-only qualification"
destination.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": receipt["status"], "sourceInputs": len(entries), "qualification": receipt["qualification"]}))
