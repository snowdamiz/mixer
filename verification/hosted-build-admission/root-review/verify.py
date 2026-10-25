#!/usr/bin/env python3
"""Recheck the accepted host packet without starting a service or modifying sources."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
RUN = BASE.parent / "attempt-2"


def sha(data):
    return hashlib.sha256(data).hexdigest()


receipt = json.loads((RUN / "receipt.json").read_bytes())
assert receipt["status"] == "passed"
assert receipt["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
inputs = receipt["inputs"]
assert sha(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()) == receipt["source_tree_sha256"]
assert sha((RUN / "source.tar.gz").read_bytes()) == receipt["source_archive_sha256"]
with tarfile.open(RUN / "source.tar.gz") as archive:
    entries = archive.getmembers()
    assert len(entries) == len(inputs) and {e.name for e in entries} == set(inputs)
    for entry in entries:
        assert entry.isfile()
        assert sha(archive.extractfile(entry).read()) == inputs[entry.name], entry.name
        assert sha((ROOT / entry.name).read_bytes()) == inputs[entry.name], entry.name

for command in receipt["commands"]:
    assert command["exit_code"] == command.get("expected_exit_code", 0), command["label"]
    assert sha((RUN / command["log"]).read_bytes()) == command["sha256"], command["label"]
assert (RUN / "postgres-timezone.log").read_text().strip() == "UTC"
assert "production_build_intent_test_workers: absent" in (RUN / "release-test-exclusion.log").read_text()

log = (RUN / "tests.log").read_text()
assert "Result: 227 passed, 2 skipped" in log
proof = re.search(r"independent_post_lock_expiry_proof: %\{([^}]+)\}", log).group(1)
times = {name: int(value) for name, value in re.findall(r"(\w+): (\d+)", proof)}
assert times["transaction_begun_ms"] < times["fixture_expiry_ms"] < times["before_unlock_ms"]
counts = {}
for name, expected in {"MixerHosted.Builds.AdmissionTest": 17,
                       "MixerHosted.BuildAdmissionReview.Test": 11,
                       "MixerHosted.Builds.StorageTest": 15,
                       "MixerHosted.Builds.JournalTest": 14}.items():
    section = log.split(name + " [", 1)[1].split("\nMixerHosted.", 1)[0]
    completed = re.findall(r"^  \* test .+ \([\d.]+ms\) \[L#\d+\]$", section, re.MULTILINE)
    assert len(completed) == expected, (name, len(completed))
    counts[name] = len(completed)
skips = [line.strip() for line in log.splitlines() if "(skipped)" in line]
assert len(skips) == 2 and any("K03 production resolver" in line for line in skips)
assert any("IS04 IS05 actual configured startup" in line for line in skips)
review_path = ROOT / "verification/hosted-build-admission-independent-review/receipt.json"
review = json.loads(review_path.read_bytes())
assert review["status"] == "accepted-internal-development-slice"
assert review["source_tree_sha256"] == receipt["source_tree_sha256"]
assert review["root_receipt_sha256"] == sha((RUN / "receipt.json").read_bytes())
assert review["independent_test_sha256"] == inputs["verification/hosted-build-admission-independent-review/independent_test.exs"]

result = {
    "schema": 1,
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "accepted-host-admission-component",
    "argv": sys.argv,
    "python": sys.version,
    "verifierSHA256": sha(Path(__file__).read_bytes()),
    "sourceTreeSHA256": receipt["source_tree_sha256"],
    "receiptSHA256": sha((RUN / "receipt.json").read_bytes()),
    "independentReceiptSHA256": sha(review_path.read_bytes()),
    "currentAndArchivedInputsRehashed": len(inputs),
    "commandLogsRehashed": len(receipt["commands"]),
    "passedTests": 227,
    "selectedTestCountsIncludedInTotal": counts,
    "skippedTests": skips,
    "postLockExpiryProof": times,
    "databaseTimeZone": "UTC",
    "productionTestConsumersAbsent": True,
    "cleanup": receipt["cleanup"],
    "earlierAttempt": "attempt-1 passed, but its timezone-sensitive expiry proof is superseded by attempt-2",
    "limitations": [
        "Disposable PostgreSQL 17 fixture on macOS; no distributed deployment or provider execution.",
        "Internal admission only; no public authorization, worker identity, production dispatcher or fleet-wide quota.",
        "Two existing Linux-only identity checks remain skipped here.",
        "No native, signing, store, FieldLog or GA gate acceptance."
    ]
}
(BASE / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
