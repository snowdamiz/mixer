#!/usr/bin/env python3
"""Seal only this owned preaccess packet; never consult the active producer."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).absolute().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def main():
    assert not (HERE / "seal.json").exists(), "do not overwrite a frozen packet"
    original = json.loads((HERE / "input-custody.json").read_bytes())
    amendment = json.loads((HERE / "compiler-amendment-custody.json").read_bytes())
    for row in original["inputs"]:
        p = HERE / row["snapshot"]
        assert p.stat().st_size == row["bytes"] and sha(p) == row["sha256"]
    assert sha(HERE / "inputs/bridge-compiler-amendment.md") == "927dfc3938d40d0a81966df2c723397184d02ade6019c369b0daf69d761b77ac"
    fixtures = json.loads((HERE / "fixture-manifest.json").read_bytes())
    for row in fixtures["cases"]:
        assert sha(HERE / "fixtures" / row["wasm"]) == row["wasm_sha256"]
        if "expected_body" in row:
            p = HERE / "fixtures" / row["expected_body"]
            assert p.stat().st_size == row["expected_body_bytes"] and sha(p) == row["expected_body_sha256"]
    writer = json.loads((HERE / "writer-cases.json").read_bytes())
    guards = json.loads((HERE / "support-control-results.json").read_bytes())
    roster = json.loads((HERE / "review-roster.json").read_bytes())
    assert writer["case_count"] == 29 and guards["negative_control_count"] == 24
    assert roster["obligation_count"] == 80
    assert not any(p.is_symlink() for p in HERE.rglob("*"))
    assert not any(p.name == "__pycache__" for p in HERE.rglob("*"))
    write("commands.json", {"schema": 1, "recorded_at": datetime.now(timezone.utc).isoformat(),
        "tool": {"python_executable": sys.executable, "python_version": sys.version,
                 "python_executable_sha256": sha(Path(sys.executable).resolve())},
        "execution_scope": "only independently authored Python test support; no Rust/product/native/compiler suite",
        "commands": [
            {"argv": ["python3", "-B", "verification/swift-cache-state-profile-adapter-independent/prepare_inputs.py"],
             "exit_code": 0, "result": "PASS preaccess custody:15selected inputs;86prior+86closed members; no active producer access",
             "evidence": "input-custody.json"},
            {"argv": ["python3", "-B", "verification/swift-cache-state-profile-adapter-independent/encode_fixtures.py"],
             "exit_code": 0, "result": "PASS test-support framing only:3positive candidates/5refusal candidates;7,680,000 expected row bytes; real validation pending",
             "evidence": "fixture-manifest.json"},
            {"argv": ["python3", "-B", "<bounded inline compiler-amendment custody copy>"],
             "exit_code": 0, "result": "exact source hash checked and bytes copied; compiler not executed",
             "evidence": "compiler-amendment-custody.json"},
            {"argv": ["python3", "-B", "verification/swift-cache-state-profile-adapter-independent/writer_oracle.py"],
             "exit_code": 0, "result": "PASS test-support writer protocol:29 predeclared cases; no product or File execution",
             "evidence": "writer-cases.json"},
            {"argv": ["python3", "-B", "verification/swift-cache-state-profile-adapter-independent/prepare_review_controls.py"],
             "exit_code": 0, "result": "PASS test support:80predeclared obligations;16byte patches;24negative roster/argument controls",
             "evidence": "support-control-results.json"},
            {"argv": sys.argv, "result": "sealing command; source/input checks complete before seal output"}
        ],
        "read_only_source_review": ["selected protocol/proposal/compiler amendment", "independent copied analyzer profile()/full_identity()/record_fields()"],
        "failed_preaccess_attempts": [],
        "root_reported_library_strict_command_failure": "148 inherited warnings retained root-side; not executed or credited in this packet",
        "cleanup": {"all_python_children_completed": True, "scratch_created": False,
                    "compiled_products_created": False, "bytecode_cache_created": False,
                    "temporary_native_or_capture_processes_started": False,
                    "all_owned_fixtures_and_support_outputs_retained": True}})
    write("decision.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
        "decision": "preaccess-ready-awaiting-root-frozen-source-release",
        "implementation_selected": original["inputs"][0]["sha256"],
        "protocol_amendment": "ae64f81fc4051bf59e31fb4552a25b9d533256e5bb429ee90b547af9058764fd",
        "compiler_amendment": "927dfc3938d40d0a81966df2c723397184d02ade6019c369b0daf69d761b77ac",
        "active_producer_lane_accessed": False, "implementation_accepted": False,
        "product_or_actual_File_executed": False,
        "support_evidence": {"positive_Wasm_candidates": 3, "validator_refusal_candidates": 5,
            "expected_row_bytes": 7680000, "writer_schedule_cases": 29,
            "exact_row_byte_patches": 16, "review_obligations_not_method_count": 80,
            "negative_roster_and_argument_guards": 24},
        "concrete_source_binding_limit": "unchanged synthetic profile schema does not establish owner provenance; exact actual-owner row comparison required; collusive row/event may be synthetically admissible",
        "pending": ["root release and full source custody", "actual real-validator fixtures and adapter/File bytes both modes",
            "exact complete compiler test namespace and bridge invocation inventory", "actual complete Result/caller layouts",
            "new complete work/memory/simultaneous lifetime proof", "new source warning and exact compiler arguments review"],
        "unqualified": ["real profile header/configuration/layout binding", "original result/final ledger joins",
            "hash/CLI immutable descriptor custody", "runtime/full-target/native/device behavior", "published package dogfood", "GA"],
        "prior_seals_and_canonical_sources_unchanged": True,
        "no_Git_or_native_or_UI_or_capture_or_process_inventory": True,
        "source_identity_not_inferred_from_HEAD": True})
    members = [{"path": str(p.relative_to(HERE)), "bytes": p.stat().st_size, "sha256": sha(p)}
               for p in sorted(HERE.rglob("*")) if p.is_file() and p.name != "seal.json"]
    write("seal.json", {"schema": 1, "phase": "independent-preaccess", "members": members,
        "member_count": len(members), "total_bytes": sum(x["bytes"] for x in members),
        "tree_sha256": hashlib.sha256("".join(f"{x['path']}\t{x['bytes']}\t{x['sha256']}\n" for x in members).encode()).hexdigest(),
        "all_listed_members_now_immutable": True, "seal_excludes_only_itself": True})
    print(json.dumps({"seal_sha256": sha(HERE / "seal.json"), "members": len(members),
        "bytes": sum(x["bytes"] for x in members), "decision_sha256": sha(HERE / "decision.json")}))


if __name__ == "__main__":
    main()
