#!/usr/bin/env python3
"""Snapshot allowlisted source and make bounded offline observations only.

No candidate source is imported, compiled, executed or selected by this script.
The only writes are below this script's directory. Do not rerun a frozen packet.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

INPUTS = [
    "AGENTS.md",
    "PLAN.md",
    "mixer-product-plan.md",
    "docs/swift-semantic-adapter-prerequisite.md",
    "docs/swift-semantic-adapter-contract-review.md",
    "docs/swift-semantic-adapter-terminal-correction.md",
    "docs/swift-ordered-retention-analyzer.md",
    "docs/swift-ordered-retention-analyzer-library.md",
    "docs/swift-ordered-retention-analyzer-fsm-contract.md",
    "verification/swift-semantic-adapter-root-review/scalar-cursor-implementation-selection.json",
    "verification/swift-cache-state-ci-canonical-review/decision.json",
    "verification/swift-cache-state-ci-workflow-root-review/selection.json",
    "verification/swift-cache-state-ci-independent/corrected-review/final-decision.json",
    "verification/swift-cache-state-ci/README.md",
    "verification/swift-cache-state-ci/check_cache_state.py",
    "verification/swift-cache-state-ci/pack/manifest.json",
    "verification/swift-cache-state-ci/pack/inventories/api-contract.json",
    "verification/swift-cache-state-ci/pack/inventories/bindings.json",
    "verification/swift-cache-state-ci/pack/source/library/analyzer.rs",
    "verification/swift-cache-state-ci/pack/source/library/envelope.rs",
    "verification/swift-cache-state-ci/pack/source/library/cache_state.rs",
    "verification/swift-ordered-retention-diagnostic-completion/candidate-manifest.json",
    "vm/Cargo.toml",
    "vm/src/experimental/swift.rs",
    "vm/src/experimental/swift_descriptor_tests.rs",
    "vm/src/experimental/cache/borrowed.rs",
    "vm/src/experimental_swift_reactor/cache.rs",
    "vm/src/experimental_swift_reactor/control.rs",
    "vm/src/experimental_swift_reactor/mod.rs",
    "vm/tests/swift_reactor_validation_fixture.rs",
]

SEAMS = [
    ("PLAN.md", 85, 266, "current Swift execution paragraph and pending integration"),
    ("mixer-product-plan.md", 15, 34, "binding owned product scope"),
    ("mixer-product-plan.md", 369, 403, "owned interpreter and qualification scope"),
    ("mixer-product-plan.md", 683, 722, "verification and performance targets"),
    ("mixer-product-plan.md", 765, 815, "FieldLog and independent consumer evidence"),
    ("mixer-product-plan.md", 1140, 1203, "GA gates require their own receipts"),
    ("docs/swift-ordered-retention-analyzer.md", 48, 179, "real binding and adapter prerequisites"),
    ("docs/swift-ordered-retention-analyzer.md", 599, 662, "host custody and bounded I/O contract"),
    ("verification/swift-cache-state-ci/pack/source/library/analyzer.rs", 261, 300, "synthetic context and fixed profile rows"),
    ("verification/swift-cache-state-ci/pack/source/library/analyzer.rs", 418, 444, "File admission and output identities"),
    ("verification/swift-cache-state-ci/pack/source/library/cache_state.rs", 49, 102, "private observation and false authority"),
    ("verification/swift-cache-state-ci/pack/source/library/cache_state.rs", 15349, 15440, "same-iteration actual record and envelope bridge"),
    ("verification/swift-cache-state-ci/pack/source/library/cache_state.rs", 15528, 15676, "actual File orchestration and fixture public entry"),
    ("vm/src/experimental/swift.rs", 145, 180, "sealed immutable validated owner"),
    ("vm/src/experimental/swift.rs", 206, 237, "crate-private actual descriptor lookup"),
    ("vm/src/experimental/cache/borrowed.rs", 13, 21, "closed private SnapshotView contract"),
    ("vm/src/experimental/cache/borrowed.rs", 58, 79, "actual Swift owner adapter"),
    ("vm/src/experimental_swift_reactor/cache.rs", 1809, 1894, "actual construction/layout dependency"),
    ("vm/src/experimental_swift_reactor/control.rs", 21, 65, "unchanged run limits"),
    ("vm/src/experimental_swift_reactor/control.rs", 194, 234, "typed result observations need independent serialization"),
    ("vm/src/experimental/swift_descriptor_tests.rs", 276, 320, "existing absolute identity test seam"),
    ("vm/src/experimental/swift_descriptor_tests.rs", 506, 551, "existing immutable nonallocating descriptor test seam"),
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(name: str, data: object) -> None:
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def run(argv: list[str]) -> dict:
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=10, check=False)
    return {
        "argv": argv, "exit": result.returncode,
        "stdout": result.stdout.decode("utf-8", "replace"),
        "stderr": result.stderr.decode("utf-8", "replace"),
    }


def main() -> None:
    if (HERE / "seal.json").exists():
        raise SystemExit("frozen packet: refusing to overwrite")
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    commands = [
        run(["git", "rev-parse", "HEAD"]),
        run(["git", "rev-parse", "HEAD^{tree}"]),
        run(["git", "--version"]),
        run(["rg", "--version"]),
    ]
    assert all(x["exit"] == 0 for x in commands)
    members = []
    captured = {}
    for name in INPUTS:
        source = ROOT / name
        assert source.is_file() and not source.is_symlink(), name
        data = source.read_bytes()
        dest = HERE / "inputs" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        captured[name] = data
        members.append({
            "path": name, "bytes": len(data), "sha256": sha(data),
            "snapshot": str(dest.relative_to(HERE)),
            "context_mutable": name in {"PLAN.md"},
        })
    tree_rows = "".join(f"{x['path']}\t{x['bytes']}\t{x['sha256']}\n"
                        for x in sorted(members, key=lambda x: x["path"]))

    canonical = ROOT / "verification/swift-cache-state-ci"
    runner_hash = sha(captured["verification/swift-cache-state-ci/check_cache_state.py"])
    manifest_hash = sha(captured["verification/swift-cache-state-ci/pack/manifest.json"])
    assert runner_hash == "e531311facb7b38967d3b904b26e92ff3f6c4dc7444c856cd799b70a1d91373b"
    assert manifest_hash == "6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857"
    manifest = json.loads(captured["verification/swift-cache-state-ci/pack/manifest.json"])
    verified = []
    for member in manifest["members"]:
        relative = Path(member["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        path = canonical / "pack" / relative
        assert path.is_file() and not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == member["bytes"] and sha(data) == member["sha256"], str(path)
        verified.append(member["path"])
    assert len(verified) == manifest["member_count"] == 86

    selection = json.loads(captured["verification/swift-cache-state-ci-workflow-root-review/selection.json"])
    assert selection["closed_fixture_CI_integration_selected"] is True
    assert selection["Rust1_98_1_or_actual_Actions_qualified"] is False
    assert selection["canonical_runner_sha256"] == runner_hash
    assert selection["pack_manifest_sha256"] == manifest_hash
    relocation = json.loads(captured["verification/swift-cache-state-ci-canonical-review/decision.json"])
    assert relocation["canonical_relocation_accepted"] is True
    accepted = json.loads(captured["verification/swift-semantic-adapter-root-review/scalar-cursor-implementation-selection.json"])
    assert accepted["general_public_File_admission_qualified"] is False
    assert accepted["canonical_runtime_or_full_target_integration_selected"] is False

    old = json.loads(captured["verification/swift-ordered-retention-diagnostic-completion/candidate-manifest.json"])
    assert len(old) == 132
    compare = []
    for relative in ["src/experimental/swift.rs", "src/experimental/cache/borrowed.rs",
                     "src/experimental_swift_reactor/cache.rs", "src/experimental_swift_reactor/control.rs",
                     "src/experimental_swift_reactor/mod.rs"]:
        current = sha(captured["vm/" + relative])
        compare.append({"path": "vm/" + relative, "live_sha256": current,
                        "accepted_completion_sha256": old[relative], "equal": current == old[relative]})
    assert [x["equal"] for x in compare] == [True, False, False, False, True]
    assert compare[0]["live_sha256"] == "8c9938306112b9288646baa68b7f7f29f487c77ef7c96dffb516516525533798"

    excerpts = []
    for i, (name, first, last, meaning) in enumerate(SEAMS):
        lines = captured[name].splitlines(keepends=True)
        assert 1 <= first <= last <= len(lines), (name, first, last, len(lines))
        data = b"".join(lines[first - 1:last])
        path = HERE / "excerpts" / f"{i:02d}-{Path(name).name}-{first}-{last}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        excerpts.append({"path": name, "first_line": first, "last_line": last,
                         "excerpt": str(path.relative_to(HERE)), "bytes": len(data),
                         "sha256": sha(data), "scope": meaning})

    unchanged = all((ROOT / name).read_bytes() == captured[name] for name in INPUTS)
    assert unchanged, "consulted inputs changed during snapshot/check; retain failure and review"
    ended = datetime.datetime.now(datetime.timezone.utc).isoformat()
    checks = {
        "schema": 1, "at": ended,
        "scope": "offline source/manifest/arithmetic observations only; no implementation acceptance",
        "runner_sha256": runner_hash, "pack_manifest_sha256": manifest_hash,
        "closedpack_members_rehashed": len(verified),
        "closedpack_member_bytes_rehashed": sum(x["bytes"] for x in manifest["members"]),
        "closedpack_tree_sha256_from_selected_manifest": manifest["tree_sha256"],
        "root_selection_and_canonical_review_consistent": True,
        "selected_isolated_G1_G7": accepted["complete_source_groups"],
        "selected_isolated_combined_groups": accepted["combined_groups"],
        "selected_isolated_logical_union": accepted["whole_logical_union"],
        "accepted_completion_manifest_members": len(old),
        "live_vs_accepted_completion_source_identity": compare,
        "row_bytes": 32, "rows": 80000, "row_body_bytes": 80000 * 32,
        "profile_header_bytes": 512, "profile_bytes": 512 + 80000 * 32,
        "consulted_inputs_unchanged_during_formal_check": unchanged,
        "general_public_File_admission": "pending",
        "canonical_runtime_and_full_target_selection": "unselected",
        "actual_Actions_Rust1_98_1_in_reviewed_snapshots": "pending; root owns subsequent status",
        "no_import_or_execution_of_consulted_source": True,
        "no_103_command_pack_or_compiler_invocation": True,
        "no_native_UI_capture_or_process_inventory": True,
        "no_hosted_source_access": True,
        "product_or_gate_pass_claimed": False,
    }
    write_json("input-manifest.json", {
        "schema": 1, "at": ended, "source_revision": commands[0]["stdout"].strip(),
        "source_commit_tree": commands[1]["stdout"].strip(),
        "source_revision_scope": "Context only; exact observed bytes bound individually; live checkout may have other active lanes",
        "consulted_tree_sha256": sha(tree_rows.encode()),
        "tree_digest_definition": "SHA256 of sorted path<TAB>bytes<TAB>sha256<LF> rows",
        "members": members,
    })
    write_json("source-seams.json", {"schema": 1, "members": excerpts})
    write_json("offline-checks.json", checks)
    write_json("command-receipt.json", {
        "schema": 1, "argv": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))],
        "script_sha256": sha(Path(__file__).read_bytes()), "started_at": started, "ended_at": ended,
        "python_executable": sys.executable, "python_version": sys.version,
        "host": {"sysname": os.uname().sysname, "release": os.uname().release, "machine": os.uname().machine},
        "read_only_tool_commands": commands, "exit": 0,
        "writes_scope": str(HERE.relative_to(ROOT)) + "/** only",
        "new_compiler_or_native_or_old_harness_invocations": 0,
        "output": "86 closedpack members verified; 30 consulted inputs snapshotted; 5 source identity comparisons; row size arithmetic verified",
    })
    write_json("decision.json", {
        "schema": 1, "at": ended,
        "decision": "Propose isolated real-validated-snapshot profile-row adapter as next dependency, pending independent contract review and root selection",
        "implementation_performed": False, "new_policy_model": False,
        "selected_exact_source_or_cap_changed": False,
        "proposed_producer_ownership": "verification/swift-cache-state-profile-adapter/** only",
        "public_API_changes_proposed_for_next_slice": False,
        "private_seam": "real execution_function -> fixed little-endian ProfileRowV1 -> bounded row-body File",
        "first_real_adapter_gap": "origin of immutable profile rows",
        "reviewed_fixture_component": "accepted isolated host scope only",
        "full_target_retry_selected": False, "canonical_integration_selected": False,
        "general_public_File_admission_accepted": False, "GA_gate_promoted": False,
        "scope_and_unknowns": ["README.md", "source-review.md", "proposed-contract.md", "test-plan.md"],
    })
    print(json.dumps({"scope": checks["scope"], "closedpack_members_verified": len(verified),
                      "consulted_inputs": len(INPUTS), "excerpt_count": len(excerpts),
                      "live_validator_matches_accepted_completion": compare[0]["equal"],
                      "new_source_implementation_or_execution": False}, sort_keys=True))


if __name__ == "__main__":
    main()
