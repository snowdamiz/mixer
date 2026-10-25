#!/usr/bin/env python3
"""Read-only verification of the selected contract packet; no runtime claims."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "verification/hosted-browser-callback-claim"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    handoff_bytes = (PACKET / "handoff.json").read_bytes()
    handoff = json.loads(handoff_bytes)
    assert (PACKET / "handoff.sha256").read_text().strip() == sha(handoff_bytes)
    for name, expected in handoff["members"].items():
        path = ROOT / name
        assert path.resolve().is_relative_to(ROOT)
        data = path.read_bytes()
        assert len(data) == expected["bytes"] and sha(data) == expected["sha256"], name
    attempt = ROOT / handoff["selected_attempt"]
    receipt_bytes = (attempt / "receipt.json").read_bytes()
    receipt = json.loads(receipt_bytes)
    assert (attempt / "receipt.sha256").read_text().strip() == sha(receipt_bytes)
    assert receipt["exit_code"] == 0
    semantic_count = 0
    context_drift = []
    for name, expected in receipt["inputs"].items():
        archived = (attempt / "inputs" / name).read_bytes()
        assert len(archived) == expected["bytes"] and sha(archived) == expected["sha256"]
        current = (ROOT / name).read_bytes()
        if name == "PLAN.md":
            if sha(current) != expected["sha256"]:
                context_drift.append(name)
        else:
            assert sha(current) == expected["sha256"], name
        if name.startswith("hosted/"):
            semantic_count += 1
    for name, expected in receipt["outputs"].items():
        assert sha((attempt / name).read_bytes()) == expected
    result = json.loads((attempt / "stdout.json").read_text())
    assert result["passed"] and all(x["passed"] for x in result["checks"])
    assert result["runtime_cases_passed"] == 0 and result["runtime_cases_pending"] == 39
    assert handoff["runtime_security_pass_claim"] is False
    cleanup = receipt["cleanup"]
    assert not cleanup["temporary_runtime_resources_created"]
    assert all(not value for key, value in cleanup.items() if key != "temporary_runtime_resources_created")
    print(json.dumps({
        "schema": 1,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "passed-contract-packet-only",
        "command": [sys.executable, str(Path(__file__).resolve())],
        "python": sys.version,
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "handoff_sha256": sha(handoff_bytes),
        "sealed_members_verified": len(handoff["members"]),
        "current_semantic_sources_verified": semantic_count,
        "context_only_drift": context_drift,
        "selected_attempt": handoff["selected_attempt"],
        "documentation_checks_passed": len(result["checks"]),
        "runtime_cases_passed": 0,
        "runtime_cases_pending": 39,
        "cleanup": cleanup,
        "scope": "Exact contract/source/output binding only; implementation and runtime acceptance pending",
    }, indent=2))


if __name__ == "__main__":
    main()
