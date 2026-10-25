#!/usr/bin/env python3
"""Read-only binding review; never executes the collector or application code."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
COLLECTION = ROOT / "verification/hosted-build-aggregate-admission-root-review/independent-attempt-1"

def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()

def sha_file(path):
    return sha_bytes(path.read_bytes())

receipt_path = COLLECTION / "receipt.json"
receipt = json.loads(receipt_path.read_text())
handoff_path = ROOT / "verification/hosted-build-aggregate-admission/handoff.json"
handoff = json.loads(handoff_path.read_text())
review_name = str((OUT / "aggregate_admission_review_test.exs").relative_to(ROOT))
assert receipt["status"] == "passed"
assert receipt["test_selection"] == "explicit independent tests only"
manifest_hash = sha_bytes(json.dumps(receipt["inputs"], sort_keys=True, separators=(",", ":")).encode())
assert manifest_hash == receipt["source_tree_sha256"]
archive = COLLECTION / "source.tar.gz"
assert sha_file(archive) == receipt["source_archive_sha256"]

handoff_matches = {}
for name, expected in handoff["inputs"].items():
    actual = sha_file(ROOT / name)
    assert actual == expected, name
    handoff_matches[name] = actual

# Deliberately inspect only this review's source and frozen admission handoff
# members. Other hosted lanes receive no new source-review claim here.
selected = [name for name in handoff["inputs"] if name in receipt["inputs"]] + [review_name]
source_matches = {}
with tarfile.open(archive, "r:gz") as bundle:
    for name in selected:
        expected = receipt["inputs"][name]
        current = sha_file(ROOT / name)
        archived = sha_bytes(bundle.extractfile(name).read())
        assert current == archived == expected, name
        source_matches[name] = {"current": current, "archived": archived}

outputs = {}
for command in receipt["commands"]:
    output_path = COLLECTION / command["log"]
    actual = sha_file(output_path)
    assert actual == command["sha256"], command["label"]
    assert command["exit_code"] == command.get("expected_exit_code", 0), command["label"]
    outputs[command["log"]] = actual

tests = (COLLECTION / "tests.log").read_text()
assert "Result: 11 passed" in tests
assert "skipped" not in tests.lower()
assert "failed to connect to Postgres" in tests  # retain the known manual notifier diagnostic
assert "redefining module MixerHosted.Repo.Migrations.AddBuildAggregateLimits" in tests
revision = (COLLECTION / "revision.log").read_text().strip()
assert revision == "aaa9d2d7eaf44e82dc12fefe2b41431d0fd44d11"
assert receipt["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
initdb = next(c for c in receipt["commands"] if c["label"] == "initdb")
scratch = Path(initdb["argv"][initdb["argv"].index("-D") + 1]).parent
assert not scratch.exists()

result = {
    "schema": 1,
    "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, str(Path(__file__).resolve())],
    "cwd": str(Path.cwd()),
    "python": sys.version,
    "platform": platform.platform(),
    "verifier_sha256": sha_file(Path(__file__)),
    "receipt": str(receipt_path.relative_to(ROOT)),
    "receipt_sha256": sha_file(receipt_path),
    "head": revision,
    "source_tree_sha256": manifest_hash,
    "manifest_entries": len(receipt["inputs"]),
    "source_archive_sha256": sha_file(archive),
    "handoff_live_hashes_verified": handoff_matches,
    "selected_current_and_archived_inputs_verified": source_matches,
    "command_outputs_verified": outputs,
    "tests": {"passed": 11, "skipped": 0, "output_sha256": sha_file(COLLECTION / "tests.log")},
    "versions": {name: (COLLECTION / name).read_text().strip() for name in ("elixir-version.log", "postgres-version.log")},
    "diagnostics": [
        "Manual test Oban PostgreSQL notifier reports missing database options; direct persisted job-row and transactional assertions passed. Notification transport delivery is not qualified.",
        "Disposable down/up migration test emits module redefinition warnings; test command exit 0 with all eleven controls passed."
    ],
    "cleanup": {**receipt["cleanup"], "scratch_absent_at_binding_review": not scratch.exists()},
    "scope": "Independent source and real loopback PostgreSQL admission review; no provider, production migration, cloud, native, signing, source authority or GA claim.",
    "limitations": [
        "This reviewer independently rehashed only the seven admission/review source archive members listed here, all nine handoff inputs live, and all 23 command logs. Root's separate verifier covers all 92 current/archive inputs.",
        "The eleven control result is independent-only; the root full suite's 255 passes and two Linux-network skips are separate evidence.",
        "No notification delivery, throughput, fairness, failover or old-writer rollout is qualified."
    ]
}
(OUT / "evidence-binding-review.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"source_tree_sha256": manifest_hash, "handoff_inputs_verified": len(handoff_matches), "current_and_archive_members_verified": len(source_matches), "command_outputs_verified": len(outputs), "passed": 11, "skipped": 0, "scratch_absent": not scratch.exists()}, indent=2))
