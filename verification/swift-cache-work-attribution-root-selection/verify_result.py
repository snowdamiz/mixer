#!/usr/bin/env python3
"""Read-only verification of the one completed attribution attempt."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / "verification/swift-cache-work-attribution"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())

result = read(HERE / "result-binding.json")
assert sha(PACKET / "seal.json") == result["preparedSealSHA256"]
seal = read(PACKET / "seal.json")
for name, digest in seal["files"].items():
    assert sha(PACKET / name) == digest, name
for name, digest in seal["externalFiles"].items():
    assert sha(ROOT / name) == digest, name
assert len(seal["files"]) == 318
assert sha(HERE / "execution.json") == result["executionSelectionSHA256"]
assert (HERE / "execution.json").read_bytes() == (PACKET / "root-selection.json").read_bytes()
selection = read(HERE / "execution.json")
assert selection["exactCommandSelected"] and selection["maxTargetAttempts"] == 1
assert sha(PACKET / "prepared-selection.json") == selection["preparedSelectionSHA256"]
assert read(PACKET / "target-attempt-started.json")["selection"]["sha256"] == result["executionSelectionSHA256"]
receipt = PACKET / "commands/target-once/receipt.json"
assert sha(receipt) == result["commandReceiptSHA256"]
command = read(receipt)
assert command["exitCode"] == 101 and not command["timedOut"]
assert command["processGroupEmpty"] and command["rawStreamEOFConfirmed"]
for stream in ("stdout", "stderr"):
    assert sha(PACKET / "commands/target-once" / stream) == command[stream]["sha256"]
events = [json.loads(line.split("MIXER_EXACT ", 1)[1]) for line in (PACKET / "commands/target-once/stdout").read_text().splitlines() if "MIXER_EXACT " in line]
assert events == read(PACKET / "target-events.json")
assert sha(PACKET / "target-events.json") == result["eventsSHA256"]
snapshots = [e["payload"] for e in events if e["event"].startswith("attribution_")]
assert len(snapshots) == 6
for snapshot in snapshots:
    assert snapshot["reconciled"] and snapshot["invalid_flags"] == 0
    assert sum(snapshot["successful_credits"]) == snapshot["authoritative_cache_work"]
    if snapshot["authoritative_cache_totals"] is not None:
        totals = snapshot["authoritative_cache_totals"]
        assert snapshot["distinct_completed_decodes"] + snapshot["repeated_completed_decodes"] == totals["decodes"]
        assert snapshot["hits"] == totals["hits"] and snapshot["misses"] == totals["misses"]
assert next(e["payload"] for e in events if e["event"] == "cleanup_reservations_and_live_empty") is True
assert next(e["payload"] for e in events if e["event"] == "cleanup_empty") is False
assert next(e["payload"] for e in events if e["event"] == "runtime_failure") == result["firstFailure"]
assert result["successfulCacheCredits"] == 64_000_000 and result["distinctCompletedDecodes"] == 485
assert result["repeatedCompletedDecodes"] == 38_947 and not result["fullTargetPassed"]
assert not (PACKET / "owned-scratch").exists()
assert read(HERE / "target-cleanup.json")["ownedScratchRemoved"]
print("Verified 318 unchanged preparation members and one failed target attempt; six attribution snapshots reconcile and owned scratch is absent.")
