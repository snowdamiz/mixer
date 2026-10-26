"""Root byte/receipt audit; does not execute the candidate or grant acceptance."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "verification/swift-envelope-ci-runner-correction"
OUT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(base, rows):
    total = 0
    for row in rows:
        path = base / row["path"]
        if (not path.is_file() or path.is_symlink()
                or path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]):
            raise ValueError("Input differs: " + str(path))
        total += row["bytes"]
    return {"members": len(rows), "bytes": total}


freeze_path = PACKET / "freeze.json"
if digest(freeze_path) != "55a32bf6ea9d792ce52917354e50178d992998712a0c676cf9cdcb191d1eb003":
    raise ValueError("Selected correction freeze changed")
freeze = json.loads(freeze_path.read_bytes())
source_audit = verify(ROOT, freeze["members"])
state = json.loads((PACKET / "full-run-state.json").read_bytes())
run = PACKET / state["retained_output"]
retained_audit = verify(run, state["members"])
if source_audit != {"members": 89, "bytes": 8460084}:
    raise ValueError("Source totals differ")
if retained_audit != {"members": 252, "bytes": 63660987}:
    raise ValueError("Retained totals differ")
receipt = json.loads((run / "receipt.json").read_bytes())
streams = []
for command in receipt["commands"]:
    expected = 1 if command["name"].startswith("api-negative-") else 0
    if (command["exit"] != expected or command["timed_out"]
            or not command["child_returned"] or not command["owned_group_gone"]):
        raise ValueError("Incomplete command: " + command["name"])
    streams.extend([command["stdout"], command["stderr"]])
stream_audit = verify(run, streams)
if len(receipt["commands"]) != 23 or len(streams) != 46:
    raise ValueError("Command inventory differs")
if (receipt["status"] != "passed-host-fixture-check" or receipt["errors"]
        or not receipt["cleanup"]["removed"] or not state["temporary_parent_removed"]
        or receipt["fresh_candidate_comparisons_against_reused_oracles"] != 21714):
    raise ValueError("Fresh closure is incomplete")
result = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__))], "python_version": sys.version,
    "status": "correction-frozen-input-and-full-run-byte-audit-complete",
    "freeze_sha256": digest(freeze_path), "sources": source_audit,
    "retained_run": retained_audit, "commands": 23, "streams": stream_audit,
    "host_receipt_sha256": digest(run / "receipt.json"),
    "retained_mapping_sha256": digest(PACKET / "full-run-state.json"),
    "elapsed_seconds": receipt["elapsed_seconds"],
    "scope": "Byte and producer receipt reconciliation only; final packet seal and independent correction review remain required.",
    "candidate_admitted": False, "root_acceptance": False,
    "CI_1_98_1_envelope_qualified": False, "native_runtime_or_capture_started": False,
    "GA_qualified": False,
}
(OUT / "correction-run-byte-audit.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
