#!/usr/bin/env python3
"""Freeze this owned offline review; no external mutations or acceptance."""
import datetime
import hashlib
import json
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ident(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    target = HERE / "review-seal.json"
    if target.exists():
        raise RuntimeError("review seal is create-once")
    members = []
    for path in sorted(HERE.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("review must contain no links or scratch")
        if path.is_file():
            members.append({"path": str(path.relative_to(HERE)), **ident(path)})
    data = {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Independent bounded offline Android source-pair5/host protocol review and future test plan only",
        "verdict": "migration-design-supported-with-root-selected-input-inventory-clarification; implementation-selection-pending-accepted-corrected-source-and-fresh-qualification",
        "input_protocol_seal_sha256": "2338ce170833c7a33d797d46a6d51d50e3b24398ed05b2b8b2129dafb35eb89f",
        "input_member_count": 657, "input_member_bytes": 7_527_003,
        "root_custody_sha256": "84e7d7b5538d7894459fef493f157d19685bb8cfb010790612f641d983c8f8b3",
        "focus_review_seal_sha256": "69e1f6a02702e5a4181cbb6ff76263301d499e8853115c7059bb39e0c393dcb8",
        "focus_review_scope": "Only seal identity and member-authenticated review.md; whole 1151-member review not replayed/rehashed",
        "contextual_head_at_initial_verification": json.loads((HERE / "input-verification.json").read_text())["head"],
        "python": sys.version, "python_executable": str(Path(sys.executable).resolve()),
        "python_executable_identity": ident(Path(sys.executable).resolve()), "platform": platform.platform(),
        "commands": [json.loads((HERE / name).read_text()) for name in ("offline-replay-command.json", "design-audit-command.json")],
        "results": {"offline_copied_inputs": 602, "actual_frozen_driver_parser_refusals": 5,
                    "synthetic_map_integrity_refusals": 13, "independent_data_groups": 11,
                    "independent_design_corruption_refusals": 10,
                    "retained_historical_support_not_rerun": "9 controls / 61 assertions",
                    "families": 16, "designed_states_per_family": 6, "designed_rows_not_executed": 96,
                    "new_callback_migration_safety_defects_found": 0, "protocol_inventory_clarifications": 1},
        "cleanup": {"owned_children_reaped": True, "scratch_and_temporary_links_removed": True,
                    "native_ui_capture_or_process_inventory_started": False, "other_projects_processes_touched": False},
        "product_java_build_or_native_execution": False, "canonical_or_other_lane_writes": False,
        "git_mutations": False, "implementation_accepted": False, "source_pair5_selected": False,
        "native_public_OTA_or_GA_accepted": False, "members": members,
        "member_count": len(members), "member_bytes": sum(row["bytes"] for row in members),
    }
    target.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({"path": str(target), **ident(target), "members": len(members),
                      "member_bytes": data["member_bytes"], "implementation_accepted": False}, indent=2))


if __name__ == "__main__":
    main()
