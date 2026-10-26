#!/usr/bin/env python3
"""Check this preparation's frozen input/excerpt and decision consistency only."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if (HERE / "seal.json").exists():
        raise SystemExit("frozen packet: use verify_frozen.py instead")
    checks = []
    manifest = json.loads((HERE / "input-manifest.json").read_text())
    for member in manifest["members"]:
        data = (HERE / member["snapshot"]).read_bytes()
        assert len(data) == member["bytes"] and digest(data) == member["sha256"]
        checks.append("input:" + member["path"])
    rows = "".join(f"{x['path']}\t{x['bytes']}\t{x['sha256']}\n"
                   for x in sorted(manifest["members"], key=lambda x: x["path"]))
    assert digest(rows.encode()) == manifest["consulted_tree_sha256"]
    checks.append("consulted-input-tree-digest")
    seams = json.loads((HERE / "source-seams.json").read_text())
    for member in seams["members"]:
        data = (HERE / member["excerpt"]).read_bytes()
        source = (HERE / "inputs" / member["path"]).read_bytes().splitlines(keepends=True)
        assert data == b"".join(source[member["first_line"] - 1:member["last_line"]])
        assert len(data) == member["bytes"] and digest(data) == member["sha256"]
        checks.append("excerpt:" + member["excerpt"])
    observed = json.loads((HERE / "offline-checks.json").read_text())
    assert observed["row_body_bytes"] + observed["profile_header_bytes"] == observed["profile_bytes"] == 2560512
    assert sum(observed["selected_isolated_G1_G7"]) == observed["selected_isolated_combined_groups"] == 7048
    assert [x["equal"] for x in observed["live_vs_accepted_completion_source_identity"]] == [True, False, False, False, True]
    assert observed["closedpack_members_rehashed"] == 86
    checks.extend(["row-byte-arithmetic", "selected-G-total", "source-identity-distinction", "closedpack-member-count"])
    decision = json.loads((HERE / "decision.json").read_text())
    for key in ["implementation_performed", "new_policy_model", "selected_exact_source_or_cap_changed",
                "full_target_retry_selected", "canonical_integration_selected",
                "general_public_File_admission_accepted", "GA_gate_promoted"]:
        assert decision[key] is False
        checks.append("decision-scope:" + key)
    assert decision["proposed_producer_ownership"] == "verification/swift-cache-state-profile-adapter/** only"
    checks.append("bounded-proposed-ownership")
    summary = {"checks": len(checks), "result": "pass", "scope": "preparation byte/arithmetic/decision consistency only; no product test"}
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "argv": [sys.executable, "-B", str(Path(__file__).relative_to(HERE.parent.parent))],
               "python": sys.version, "script_sha256": digest(Path(__file__).read_bytes()),
               "exit": 0, "checks": checks, "summary": summary,
               "source_revision": manifest["source_revision"], "source_commit_tree": manifest["source_commit_tree"],
               "consulted_tree_sha256": manifest["consulted_tree_sha256"]}
    (HERE / "preparation-check-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    (HERE / "preparation-check.stdout").write_text(json.dumps(summary, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
