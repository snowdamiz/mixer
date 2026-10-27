#!/usr/bin/env python3
"""Offline contract input/output pins; never executes Mixer or a compiler."""
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parent.parent
CORRECTION = "verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction"
INDEPENDENT = "verification/swift-guarded-snapshot-actual-owner-rust-retirement-independent"
REVIEW = "verification/swift-semantic-adapter-root-review"
PINS = {
    f"{CORRECTION}/seal.json": "46d811b1264770604106b061386e6eba01ea07e55590240eff722c36af4bcaa0",
    f"{INDEPENDENT}/seal.json": "feb1ed71043022fb2d2cd98dd07ee14800f7828b9d8a325a3a9f5411a000f387",
}
INPUTS = [
    "AGENTS.md",
    *PINS,
    f"{INDEPENDENT}/finding-root-result-lifetime.json",
    f"{INDEPENDENT}/result-root-obligation-followon.json",
    f"{INDEPENDENT}/disposition.json",
    f"{REVIEW}/guarded-snapshot-actual-owner-Rust-implementation-selection.json",
    f"{REVIEW}/guarded-snapshot-actual-owner-Rust-contract-amendment.json",
    f"{CORRECTION}/source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs",
    f"{CORRECTION}/source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs",
    f"{CORRECTION}/source/vm/src/experimental_swift_reactor/control.rs",
    f"{CORRECTION}/source/vm/src/experimental_swift_reactor/cache.rs",
]

def record(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(REPO)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}

def write(name, value):
    (PACKET / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def member_record(path):
    result = record(path)
    result["path"] = str(path.relative_to(PACKET))
    return result

def check():
    seal = json.loads((PACKET / "seal.json").read_text())
    assert seal["members"] == [member_record(PACKET / item["path"]) for item in seal["members"]]
    source = json.loads((PACKET / "source-map.json").read_text())
    assert source["inputs"] == [record(REPO / item["path"]) for item in source["inputs"]]
    contract = json.loads((PACKET / "contract.json").read_text())
    tests = json.loads((PACKET / "test-roster.json").read_text())
    assert contract["IR01"]["permanent_barrier_preserved"]
    assert not contract["scope_truth"]["source_implemented"]
    assert not contract["scope_truth"]["root_source_selection"]
    assert contract["shutdown_and_forget"]["full_root_result_charge_lifetime"] == "Pending"
    assert len(tests["negative_probes"]) == 18
    assert len(tests["host_cases"]) == 14
    print(json.dumps({"status": "offline-artifact-consistency-pass", "members": len(seal["members"]),
                      "inputs": len(source["inputs"]), "compiler_product_native_runs": 0,
                      "source_implemented": False, "root_source_selection": False,
                      "seal_sha256": hashlib.sha256((PACKET / "seal.json").read_bytes()).hexdigest()}))

def freeze():
    now = datetime.now(timezone.utc).isoformat()
    inputs = [record(REPO / path) for path in INPUTS]
    for item in inputs:
        if item["path"] in PINS:
            assert item["sha256"] == PINS[item["path"]], item
    correction_seal = json.loads((REPO / f"{CORRECTION}/seal.json").read_text())
    independent_seal = json.loads((REPO / f"{INDEPENDENT}/seal.json").read_text())
    for folder, sealed in [(CORRECTION, correction_seal), (INDEPENDENT, independent_seal)]:
        expected = {item["path"]: item for item in sealed["members"]}
        for item in inputs:
            prefix = folder + "/"
            if item["path"].startswith(prefix):
                short = item["path"][len(prefix):]
                if short in expected:
                    assert (item["bytes"], item["sha256"]) == (expected[short]["bytes"],expected[short]["sha256"])
    write("source-map.json", {
        "schema": 1, "at": now, "inputs": inputs,
        "source_basis": "Frozen correction source146; no current HEAD/Git query and no canonical source copy.",
        "source146_tree_from_pinned_correction_seal": correction_seal["source146_tree"],
        "complete_correction_packet_tree_from_pinned_seal": correction_seal["tree_sha256"],
        "independent_review_basis": "Frozen fresh independent IR01/IR02 findings and followon; original root implementation selection/amendment retained.",
        "anchors": {
            "retained_profile_loader_v1.rs": {
                "original_errors": [87,118], "returned_files_selected_and_adoption": [129,185],
                "raw_loader_outcome": [198,202], "bootstrap_root_reservation": [1475,1529],
                "IR01_barrier": [1565,1573], "admitted_owner": [1877,1885],
                "scope_and_short_owner_borrows": [1954,1997],
                "raw_carrier_and_bare_extractor": [2000,2017],
                "private_generic_core_and_facade": [2027,2063],
                "retirement_facade": [2121,2130]},
            "cache/initial_profile_v1.rs": {
                "fixed_raw_leaf": [671,690], "raw_setup_primary_resource_containers": [727,751],
                "admitted_child_and_raw_extraction": [842,881], "raw_leaf_delegate": [883,894],
                "borrowed_original_observation": [993,1062], "safe_current_outer": [1124,1170]},
            "control.rs": {"raw_adoption_failure_scope_run_and_finish": [1905,1977]},
            "cache.rs": {"ordinary_adopted_cache_owner": [269,269], "selected_loader_test_adoption": [4856,4856], "private_initial_profile_module_and_visible_reexports": [4852,4869]}
        },
        "source_ownership": ["src/experimental_swift_reactor/retained_profile_loader_v1.rs",
                             "src/experimental_swift_reactor/cache/initial_profile_v1.rs"],
        "no_whole_source_copy": True,
        "root_HEAD_advance": "Root reported unrelated console/workflow delivery may advance HEAD; neither queried nor used as this proposal's frozen input authority."
    })
    write("receipt.json", {
        "schema": 1, "at": now, "status": "source-offline-contract-only",
        "scope": "Only verification/swift-guarded-snapshot-root-result-lifetime-contract/** written.",
        "tool": {"python": sys.version, "platform": platform.platform(),
                 "rg": "ripgrep 15.2.0 (rev e89fff89ac); PCRE2 10.45; NEON", "zsh": "5.9 (arm64-apple-darwin26.0)"},
        "commands": [
            {"command": "pwd && cat AGENTS.md && rg -n guarded-snapshot|actual.owner|root.result|IR02|IR01 ~/.codex/memories/MEMORY.md", "scope": "instructions and quick memory pass", "output": "AGENTS read; no relevant memory hit"},
            {"command": "rg --files <two frozen evidence packets and root review>", "scope": "inventory", "output": "overbroad truncated inventory; unused as completeness evidence"},
            {"command": "cat <IR02 finding/followon/disposition and original two root selections>", "scope": "frozen contract inputs", "output": "read successful"},
            {"command": "rg -n <named types and signatures> <frozen loader, initial_profile, cache, control, runtime_control and validate paths>", "scope": "bounded source location search", "output": "runtime_control.rs and validate.rs absent; actual control.rs inspected; no implementation evidence from absent paths"},
            {"command": "sed -n <source-map anchor ranges> <four frozen Rust members>; sed -n '1,80p' <independent seal>", "scope": "source/offline review", "output": "read successful; actual complete source files hashed, no copied source"},
            {"command": "python3 verification/swift-guarded-snapshot-root-result-lifetime-contract/freeze.py", "scope": "offline hash/JSON/artifact validation", "output": "both supplied seal hashes matched, selected frozen member hashes matched, source-map and artifact seal written; no product execution"},
            {"command": "python3 verification/swift-guarded-snapshot-root-result-lifetime-contract/freeze.py --check", "scope": "offline artifact validation", "output": "expected offline-artifact-consistency-pass; actual command stdout is returned to root separately"}
        ],
        "tool_version_commands": [
            {"command":"python3 --version","output":"Python 3.14.8"},
            {"command":"rg --version","output":"ripgrep 15.2.0 (rev e89fff89ac); +pcre2; NEON; PCRE2 10.45 JIT"},
            {"command":"zsh --version","output":"zsh 5.9 (arm64-apple-darwin26.0)"}
        ],
        "input_revision": "Exact frozen input hashes in source-map.json; current HEAD not used.",
        "compiler_runs": 0, "product_runs": 0, "native_UI_capture_runs": 0,
        "whole_source_copies": 0, "network_calls": 0, "Git_operations": 0,
        "canonical_or_frozen_source_edits": False, "new_GA_acceptance": False,
        "paused_native_checks": "Pending; no instance started or cleanup needed by this lane.",
        "limits": ["signature sketch uncompiled", "host/compiler tests prospective only", "root has not selected implementation", "full ownership and forgotten-root funding remain Pending"]
    })
    paths = sorted(path for path in PACKET.iterdir() if path.is_file() and path.name != "seal.json")
    assert all(path.suffix in (".md", ".txt", ".json", ".py") for path in paths)
    write("seal.json", {"schema":1,"at":now,"status":"frozen-proposed-contract-only",
                        "members":[member_record(path) for path in paths],
                        "source_selection_or_implementation":False,
                        "full_ownership_or_forgotten_root_funding":False})
    check()

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--check":
        check()
    elif len(sys.argv) == 1:
        freeze()
    else:
        raise SystemExit("usage: freeze.py [--check]")
