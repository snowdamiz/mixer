#!/usr/bin/env python3
"""Hash/AST-only v4 review; no producer import, process control or DNS probe."""
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
CURRENT = PACKET / "resolution-v4"
PREVIOUS = PACKET / "resolution-v3"
CONTROLLER = "e04b71aaab35d748acc6aa87f933699262fe33a24c4400006c64c22a9da3e411"
PLAN = "150cee180b4cfe30a7dc293b9f041308cd0c06ec4cb69b65a200f77a1bf300c4"
SEAL = "fae9e276517ea6c197d6be35ed4b0a87c7ef7c1df4d1fb6ce3af04ffb1bfbe0d"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while data := source.read(262144):
            assert time.monotonic() - START < 55
            digest.update(data)
    return digest.hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def seal(path, expected, count):
    assert sha(path) == expected
    names = []
    for line in path.read_text().splitlines():
        pin, name = line.split("  ", 1)
        assert len(pin) == 64 and not Path(name).is_absolute() and ".." not in Path(name).parts
        assert sha(path.parent / name) == pin
        names.append(name)
    assert len(names) == len(set(names)) == count


def function_sources(source):
    return {node.name: (ast.dump(node, include_attributes=False), ast.get_source_segment(source, node))
            for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


def main():
    seal(CURRENT / "seal.sha256", SEAL, 6)
    seal(PREVIOUS / "seal.sha256", "87585b5b9817e1840162d0d792bbfbb7af485d3b1c6fa75773087c46bc4e3eb0", 6)
    seal(PACKET / "resolution-v2/seal.sha256", "234e19f6e0367d9f90f33205f78b2972ecf22619a8b04b23e848e0ac3b57aadd", 5)
    seal(PACKET / "preparation-seal.sha256", "26d5a93adf36bfb18acf8b986bbbeb285103a599e57a1944e25775c8002d96d7", 16)
    previous_reviews = []
    for directory, expected in [("review-1", "b290cd851911a81ffe6f61c2fb2a825863875d2ed78f1f3cd6a83dfda72aaf0c"), ("review-2", "55b1dc88c4c140b3a4eb388182444c0ebffeac800019ca402cd89493f458c432")]:
        path = OUT.parent / directory
        assert sha(path / "review-seal.json") == expected
        for member in read(path / "review-seal.json")["files"]:
            assert sha(path / member["path"]) == member["sha256"]
        previous_reviews.append({"path": directory, "seal_sha256": expected, "members": 3})
    assert sha(CURRENT / "controller.py") == CONTROLLER
    assert sha(CURRENT / "resolution-plan-v4.json") == PLAN
    plan = read(CURRENT / "resolution-plan-v4.json")
    old_plan = read(PREVIOUS / "resolution-plan-v3.json")
    preparation = read(PACKET / "preparation-receipt.json")
    for name, pin in plan["packet_inputs"].items():
        assert sha(PACKET / name) == pin
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
    changed_keys = sorted(key for key in old_plan.keys() | plan.keys() if old_plan.get(key) != plan.get(key))
    assert changed_keys == sorted(["schema", "state", "supersedes", "controller_sha256", "entrypoint", "packet_inputs", "process_custody", "failure_evidence"])
    for key in ["commands", "tools", "environment", "cumulative_operation_seconds", "absolute_phase_cutoffs_seconds", "output_bounds", "lock_acceptance", "control_byte_binding", "signal_cutoff", "resolver_policy"]:
        assert plan[key] == old_plan[key]
    assert len(plan["commands"]) == 5 and plan["cumulative_operation_seconds"] == 55
    assert (CURRENT / "inetrc").read_bytes() == (PREVIOUS / "inetrc").read_bytes() == b"{lookup,[dns,file]}.\n"
    source = (CURRENT / "controller.py").read_text()
    functions = function_sources(source)
    old_functions = function_sources((PREVIOUS / "controller.py").read_text())
    changed_functions = sorted(name for name in old_functions if functions[name][0] != old_functions[name][0])
    assert changed_functions == ["child_exited", "close_child", "group_absent", "main", "run_command"]
    new_functions = sorted(functions.keys() - old_functions.keys())
    assert new_functions == ["error_evidence", "observe_reaped_group", "reap_exited_without_signals", "syscall"]
    unchanged_functions = sorted(old_functions.keys() - set(changed_functions))
    assert len(unchanged_functions) == 12
    reap = functions["reap_exited_without_signals"][1]
    assert '"subprocess.Popen.wait(timeout=0)"' in reap and 'owned["reaped"] = True' in reap
    assert "killpg" not in reap and "observe_reaped_group(owned, deadline)" in reap
    observe = functions["observe_reaped_group"][1]
    assert "group_absent(" in observe and "killpg" not in observe
    close = functions["close_child"][1]
    assert close.index('if evidence.get("cleanup_refused")') < close.index('if owned.get("reaped")') < close.index('if child_exited(process)') < close.index('if abort_reason not in ["cancellation", "timeout"]') < close.index('for sig, grace in')
    loop = close.split("for sig, grace in", 1)[1]
    assert loop.index('if child_exited(process)') < loop.index('"os.killpg(abort_unreaped_running_group)"')
    assert 'evidence["cleanup_refused"] = True' in close
    wrapper = functions["syscall"][1]
    assert 'del STATE["syscall_trace"][:-32]' in wrapper
    assert 'errno.EPERM' in wrapper and 'CHILD["evidence"]["cleanup_refused"] = True' in wrapper
    assert 'encoded[-8192:]' in functions["error_evidence"][1]
    assert '"traceback_truncated": len(encoded) > 8192' in functions["error_evidence"][1]
    # Every process control/launch API occurs only inside the selected evidence wrapper.
    tree = ast.parse(source)
    raw_process_calls = [ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)
                         and ast.unparse(node.func) in {"os.killpg", "os.waitid", "os.getpgid", "os.getsid", "subprocess.Popen", "process.wait"}]
    assert raw_process_calls == []
    release = read(CURRENT / "preparation-receipt-v4.json")["root_release_command"]
    assert release == ["python3", "-B", "verification/hosted-dependency-advisory-correction/resolution-v4/controller.py", "--root-release", "--plan-sha256", PLAN]
    for directory in [PACKET, PACKET / "resolution-v2", PREVIOUS, CURRENT]:
        assert not (directory / "attempts").exists()
    result = {"schema": 1, "status": "focused-source-review-passed-recommend-exact-v4-root-operation",
        "created_at": datetime.now(timezone.utc).isoformat(), "python": sys.version,
        "command": "python3 -B verification/hosted-dependency-advisory-correction-independent/review-3/audit_sources.py",
        "script_sha256": sha(Path(__file__)), "controller_sha256": CONTROLLER, "plan_sha256": PLAN, "producer_seal_sha256": SEAL,
        "source_revision": preparation["source_revision"], "source_tree": preparation["source_tree"],
        "verified_counts": {"v4_members": 6, "v3_members": 6, "v2_members": 5, "original_members": 16,
            "packet_pins": len(plan["packet_inputs"]), "additional_pins": len(plan["additional_pinned_sources"]),
            "canonical_pins": len(preparation["selected_inputs"]), "tool_pins": len(preparation["tool_files"]),
            "Hex_archive_pins": len(archive["files"]), "prior_advisory_pins": len(prior["entries"])},
        "preserved_independent_reviews": previous_reviews, "changed_plan_keys": changed_keys,
        "changed_existing_functions": changed_functions, "new_functions": new_functions,
        "unchanged_function_ASTs": unchanged_functions, "findings": [],
        "normal_exit_rule": "WNOWAIT witness -> wait(timeout=0) without TERM/KILL -> observe group absence only",
        "forced_rule": "confirmed custody, unreaped and last observed running; controller cancellation/timeout; exit recheck before every signal; no nonzero signal after reap",
        "EPERM_rule": "latch refusal; preserve uncertainty and scratch; no cleanup retry or alternative kill method",
        "error_evidence": "exact Python process-control API labels/arguments and errno; 32-call ring; traceback retained to 8192 bytes with truncation flag",
        "scope_note": "Source correction motivated by root-reported separate Swift failure; exact failing syscall/cause was not established or independently audited here.",
        "supersedes_review2_readiness": True, "root_release_argv": release,
        "recommend_exact_root_five_command_55s_operation": True,
        "controller_imported_or_executed": False, "Mix_compiler_native_network_DNS_process_probe_invocations": 0,
        "source_only_completeness_is_not_runtime_proof": True,
        "qualification": "Actual lock, operation timing/closure and upgrade functional/CI/HTTP2 acceptance remain pending.",
        "elapsed_seconds": round(time.monotonic() - START, 6)}
    (OUT / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
