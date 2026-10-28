#!/usr/bin/env python3
"""Read/hash/AST-only successor review. Never import or execute producer code."""
from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PACKET = REPO / "verification/hosted-dependency-advisory-correction"
V2 = PACKET / "resolution-v2"
V3 = PACKET / "resolution-v3"
PLAN_SHA = "37784361f18003b3833173a95d50bf94b6607db4076b98cc23e912a284962123"
CONTROLLER_SHA = "91ead67b581a71d6cdc84bb675d031c50426319dc929a1f19956675d2426cce9"
SEAL_SHA = "87585b5b9817e1840162d0d792bbfbb7af485d3b1c6fa75773087c46bc4e3eb0"


def check_time():
    assert time.monotonic() - START < 55, "own offline audit exceeded budget"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while data := source.read(262144):
            check_time()
            digest.update(data)
    return digest.hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result, "duplicate JSON key"
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def seal(path):
    names = []
    for line in path.read_text().splitlines():
        expected, name = line.split("  ", 1)
        assert len(expected) == 64 and not Path(name).is_absolute() and ".." not in Path(name).parts
        assert sha(path.parent / name) == expected
        names.append(name)
    assert len(names) == len(set(names))
    return names


def functions(source):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


def main():
    assert sha(V3 / "seal.sha256") == SEAL_SHA
    assert len(seal(V3 / "seal.sha256")) == 6
    assert sha(V3 / "controller.py") == CONTROLLER_SHA
    assert sha(V3 / "resolution-plan-v3.json") == PLAN_SHA
    assert sha(V2 / "seal.sha256") == "234e19f6e0367d9f90f33205f78b2972ecf22619a8b04b23e848e0ac3b57aadd"
    assert len(seal(V2 / "seal.sha256")) == 5
    assert sha(PACKET / "preparation-seal.sha256") == "26d5a93adf36bfb18acf8b986bbbeb285103a599e57a1944e25775c8002d96d7"
    assert len(seal(PACKET / "preparation-seal.sha256")) == 16
    old_review = OUT.parent / "review-1"
    assert sha(old_review / "review-seal.json") == "b290cd851911a81ffe6f61c2fb2a825863875d2ed78f1f3cd6a83dfda72aaf0c"
    old_seal = read(old_review / "review-seal.json")
    for member in old_seal["files"]:
        assert sha(old_review / member["path"]) == member["sha256"]
    before = read(V2 / "resolution-plan-v2.json")
    plan = read(V3 / "resolution-plan-v3.json")
    preparation = read(PACKET / "preparation-receipt.json")
    for name, expected in plan["packet_inputs"].items():
        assert sha(PACKET / name) == expected
    for pin in plan["additional_pinned_sources"]:
        assert sha(Path(pin["path"])) == pin["sha256"]
    for name, pin in preparation["selected_inputs"].items():
        assert sha(REPO / name) == pin["sha256"]
    for pin in preparation["tool_files"]:
        assert sha(Path(pin["path"])) == pin["sha256"]
    archive = preparation["installed_hex_archive"]
    for name, pin in archive["files"].items():
        assert sha(Path(archive["root"]) / name) == pin["sha256"]
    prior = preparation["prior_advisory_packet"]
    prior_dir = REPO / "verification/hosted-dependency-advisory-review"
    assert sha(prior_dir / "seal.sha256") == prior["seal_sha256"]
    for pin in prior["entries"]:
        assert sha(prior_dir / pin["path"]) == pin["sha256"]
    changed_keys = sorted(key for key in before.keys() | plan.keys() if before.get(key) != plan.get(key))
    assert changed_keys == sorted(["schema", "state", "supersedes", "controller_sha256", "entrypoint", "packet_inputs", "environment", "additional_pinned_sources", "control_byte_binding", "resolver_policy", "signal_cutoff"])
    assert plan["commands"] == before["commands"] and len(plan["commands"]) == 5
    assert plan["absolute_phase_cutoffs_seconds"] == before["absolute_phase_cutoffs_seconds"] == {"work": 40, "cleanup": 46, "posthash_and_scratch_deletion": 52, "receipt": 55}
    assert plan["cumulative_operation_seconds"] == 55
    expected_env = dict(before["environment"])
    expected_env["ERL_FLAGS"] += " -home ${OPERATION_SCRATCH}/beam-home"
    expected_env["ERL_INETRC"] = "${OPERATION_SCRATCH}/inetrc"
    assert plan["environment"] == expected_env
    assert (V3 / "inetrc").read_bytes() == b"{lookup,[dns,file]}.\n"
    assert plan["resolver_policy"]["exact_utf8"].encode() == (V3 / "inetrc").read_bytes()
    assert plan["resolver_policy"]["native_fallback"] is False
    source = (V3 / "controller.py").read_text()
    old_source = (V2 / "controller.py").read_text()
    new_functions, old_functions = functions(source), functions(old_source)
    changed_functions = sorted(name for name in old_functions if old_functions[name] != new_functions[name])
    assert changed_functions == ["interrupt", "main", "verify_packet"]
    assert sorted(new_functions.keys() - old_functions.keys()) == ["pinned_bytes", "signal_cutoff"]
    assert not old_functions.keys() - new_functions.keys()
    unchanged_functions = sorted(set(old_functions) - set(changed_functions))
    # Exact source checks supplement manual control-flow review; they execute no producer code.
    assert 'plan_raw = pinned_bytes(HERE / "resolution-plan-v3.json", sys.argv[3], WORK)\n    plan = json.loads(plan_raw)' in source
    assert 'preparation_raw = pinned_bytes(PACKET / "preparation-receipt.json", preparation_sha, WORK)\n    preparation = json.loads(preparation_raw)' in source
    assert 'candidate_raw = pinned_bytes(ROOT / "verification/hosted-dependency-advisory-review/upgrade-candidates.json", candidate_sha, WORK)\n        candidates = json.loads(candidate_raw)' in source
    assert 'target.write_bytes(pinned_bytes(PACKET / name, plan["packet_inputs"][name], WORK))' in source
    assert 'for command in plan["commands"]:\n            pinned_bytes(scratch / "inetrc", plan["packet_inputs"]["resolution-v3/inetrc"], WORK)\n            pinned_bytes(scratch / "project/mix.exs", plan["packet_inputs"]["proposal/mix.exs"], WORK)\n            run_command' in source
    cutoff = ast.parse(source).body[[getattr(node, "name", None) for node in ast.parse(source).body].index("signal_cutoff")]
    cutoff_source = ast.get_source_segment(source, cutoff)
    assert cutoff_source.index('signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)') < cutoff_source.index('cutoff = time.monotonic()') < cutoff_source.index('signal.sigpending()') < cutoff_source.index('bool(CANCELLED or STATE.get("cancelled") or pending)')
    main_source = ast.get_source_segment(source, next(node for node in ast.parse(source).body if getattr(node, "name", None) == "main"))
    after_cutoff = main_source.split('cancelled = signal_cutoff()', 1)[1]
    assert 'not cancelled' in after_cutoff and 'not STATE["errors"]' in after_cutoff
    assert 'sha(' not in after_cutoff and 'pinned_bytes(' not in after_cutoff and 'verify_sources(' not in after_cutoff
    assert 'signal.SIG_UNBLOCK' not in source and 'signal.SIG_SETMASK' not in source
    release = read(V3 / "preparation-receipt-v3.json")["root_release_command"]
    assert release == ["python3", "-B", "verification/hosted-dependency-advisory-correction/resolution-v3/controller.py", "--root-release", "--plan-sha256", PLAN_SHA]
    assert not (V2 / "attempts").exists() and not (V3 / "attempts").exists()
    result = {
        "schema": 1, "status": "source-review-passed-recommend-exact-root-resolution-v3-release",
        "created_at": datetime.now(timezone.utc).isoformat(), "python": sys.version,
        "command": "python3 -B verification/hosted-dependency-advisory-correction-independent/review-2/audit_sources.py",
        "review_script_sha256": sha(Path(__file__)), "controller_sha256": CONTROLLER_SHA,
        "plan_sha256": PLAN_SHA, "producer_seal_sha256": SEAL_SHA,
        "source_revision": preparation["source_revision"], "source_tree": preparation["source_tree"],
        "verified_counts": {"v3_seal_members": 6, "v2_seal_members": 5, "original_seal_members": 16,
            "prior_independent_members": 3, "packet_inputs": len(plan["packet_inputs"]),
            "additional_pinned_sources": len(plan["additional_pinned_sources"]),
            "canonical_inputs": len(preparation["selected_inputs"]), "tool_files": len(preparation["tool_files"]),
            "Hex_archive_files": len(archive["files"]), "prior_advisory_entries": len(prior["entries"]),
            "sequential_commands": 5, "root_operation_seconds": 55},
        "unchanged_function_ASTs": unchanged_functions, "changed_existing_functions": changed_functions,
        "new_functions": ["pinned_bytes", "signal_cutoff"], "changed_plan_keys": changed_keys,
        "findings": [], "closed_findings": [
            {"id": "R01", "evidence_lines": [56,70,421,438], "result": "all hashing/cleanup precede permanent stop-signal block, finite timestamp and protected pending snapshot; handled/pending cancellation prohibits success"},
            {"id": "R02", "evidence_lines": [333,358], "result": "exact pinned private dns/file inetrc and private BEAM -home selected for every unchanged command; shell HOME unchanged"}],
        "control_binding": "bounded single read/digest before plan, preparation, candidate parse; verified project/lock/inetrc bytes copied; inetrc/project rechecked per command",
        "root_release_argv": release, "recommend_exact_root_runtime_release": True,
        "scope": "One dependency-resolution attempt only; no dependency upgrade or functional/CI/HTTP2 qualification claimed.",
        "source_only_completeness_is_not_runtime_proof": True,
        "controller_imported_or_executed": False, "Mix_compiler_native_DNS_network_process_probe_invocations": 0,
        "elapsed_seconds": round(time.monotonic() - START, 6)}
    (OUT / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
