#!/usr/bin/env python3
"""Seal only this lane's independent review artifacts and its one new document."""

import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def serial(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def main():
    selected = json.loads((BASE / "selected.json").read_bytes())
    attempt = ROOT / selected["attempt"]
    receipt_data = (attempt / "receipt.json").read_bytes()
    receipt = json.loads(receipt_data)
    assert selected["passed"] is True and receipt["exit_code"] == 0
    assert digest(receipt_data) == selected["receipt_sha256"]
    assert digest((ROOT / "verification/hosted-browser-callback-claim/handoff.json").read_bytes()) == selected["producer_handoff_sha256"]
    assert all(digest((ROOT / name).read_bytes()) == record["sha256"] for name, record in receipt["inputs"].items())
    members = [ROOT / "docs/hosted-browser-callback-claim-review.md"]
    members += sorted(path for path in BASE.rglob("*") if path.is_file() and path.name not in {"handoff.json", "handoff.sha256"} and "__pycache__" not in path.parts)
    assert all(not path.is_symlink() for path in members)
    manifest = {str(path.relative_to(ROOT)): {"bytes": path.stat().st_size, "sha256": digest(path.read_bytes())} for path in members}
    handoff = {
        "schema": 1,
        "status": "independent_contract_accepted_only",
        "unit_a_implementation_acceptance": "pending",
        "unit_b_implementation_acceptance": "pending",
        "product_runtime_cases_passed": 0,
        "contract_model_methods_passed": 14,
        "producer_runtime_cases_pending": 39,
        "selected_attempt": selected["attempt"],
        "receipt_sha256": selected["receipt_sha256"],
        "producer_handoff_sha256": selected["producer_handoff_sha256"],
        "selected_source_tree_sha256": receipt["selected_source_tree_sha256"],
        "members": manifest,
    }
    data = serial(handoff)
    (BASE / "handoff.json").write_bytes(data)
    (BASE / "handoff.sha256").write_text(digest(data) + "\n")
    print(json.dumps({"handoff_sha256": digest(data), "members": len(manifest), "selected_attempt": selected["attempt"], "status": handoff["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
