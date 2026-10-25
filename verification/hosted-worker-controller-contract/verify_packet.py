#!/usr/bin/env python3
"""Read-only packet verification. This is not controller/platform acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    receipt = json.loads((HERE / "receipt.json").read_text())
    for record in receipt["artifact_files"]:
        raw = (ROOT / record["path"]).read_bytes()
        assert sha(raw) == record["sha256"], record["path"]
        assert len(raw) == record["bytes"]
    records = receipt["input_files"]
    assert sha(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()) == receipt["source_tree_sha256"]
    # Shared active source may change after capture. Report it; do not silently
    # retarget old evidence or claim it is bound to a newer tree.
    changed = [record["path"] for record in records if sha((ROOT / record["path"]).read_bytes()) != record["sha256"]]
    assert not changed, f"allowed source changed after capture: {changed}"
    for command in receipt["commands"]:
        assert command["exit_code"] == command["expected_exit_code"]
    assert receipt["effects"]["product_modules_loaded"] == 0
    sources = json.loads((HERE / "sources.json").read_text())["sources"]
    assert len(sources) == 9
    assert all(s["status"] == 200 and s["url"].startswith("https://developers.cloudflare.com/") and len(s["sha256"]) == 64 for s in sources)
    expected = {"authentication-before-ledger", "malformed-wire-zero-mutation", "machine-and-ref-scope-rejection",
                "query-binds-without-launch", "exact-current-nonce-guard-echo",
                "immutable-conflict-zero-effect", "older-pair-no-provider-query", "same-epoch-owner-conflict",
                "equal-pair-only-forward-expiry", "higher-epoch-lower-revision", "unqualified-clock-fails-closed",
                "expiry-upper-bound-equality", "duplicate-ensure-single-launch", "stop-before-ensure-permanent",
                "timeout-absent-never-relaunch", "delayed-launch-after-stop-no-claim", "claim-consumed-before-lost-grant",
                "stop-ack-not-descendant-proof", "intent-crash-restart-keeps-identity", "duplicate-alarm-retains-single-effect"}
    inventory = subprocess.run(["node", str(HERE / "acceptance.mjs"), "--inventory"], capture_output=True, text=True, check=True, timeout=10)
    ids = json.loads(inventory.stdout)["scenarios"]
    assert len(ids) == len(set(ids)) and set(ids) == expected
    vectors = subprocess.run(["node", str(HERE / "acceptance.mjs"), "--vectors"], capture_output=True, text=True, check=True, timeout=10)
    print(json.dumps({"status": "passed", "scope": "packet-consistency-only", "candidate_scenarios": len(ids),
                      "vectors": json.loads(vectors.stdout), "controller": "pending-no-source-assigned"}))

if __name__ == "__main__":
    main()
