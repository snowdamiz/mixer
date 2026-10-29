#!/usr/bin/env python3
"""Bounded filesystem-only review checks. Never imports or executes source inputs.

These checks record source facts and corruption-control sensitivity. They do not
compile Java, prove class emission, authorize Android runtime or release, or
replace the focused hosted executable acceptance selected by root.
"""
import os
import sys
import signal
import socket
import subprocess
import threading
import time


def denied(*args, **kwargs):
    raise RuntimeError("independent source review denies nested runtime/process/network activity")


# Install denials before importing filesystem/hash/JSON subjects. Do not patch
# infrastructure, REPL timers, or any process other than this bounded checker.
for name in tuple(dir(os)):
    if name.startswith(("exec", "spawn")) or name in {
        "system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp",
        "kill", "killpg", "setpgid", "setsid", "getpgid", "getpgrp",
        "wait", "waitpid", "waitid", "wait3", "wait4", "startfile",
    }:
        setattr(os, name, denied)
for name in ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
    setattr(subprocess, name, denied)
for name in ("socket", "socketpair", "fromfd", "create_connection", "create_server"):
    if hasattr(socket, name):
        setattr(socket, name, denied)
for name in ("signal", "raise_signal", "pthread_kill", "alarm", "setitimer", "pause", "sigwait", "sigtimedwait", "sigwaitinfo"):
    if hasattr(signal, name):
        setattr(signal, name, denied)
threading.Thread.start = denied
threading.Timer.start = denied
threading.Event.wait = denied
threading.Condition.wait = denied
time.sleep = denied


def audit(event, args):
    if event.startswith(("socket.", "subprocess.", "os.exec", "os.spawn", "os.posix_spawn")) or event in {
        "os.fork", "os.forkpty", "os.system", "os.kill", "os.killpg", "os.setpgid", "os.setsid",
    }:
        denied()


sys.addaudithook(audit)

from pathlib import Path
import hashlib
import json
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OWNED = ROOT / "verification/android-view-api-boundary-independent"
BASE = ROOT / "verification/android-editor-preservation-membership-correction/source"
CANDIDATE = ROOT / "verification/android-view-api-boundary-candidate/source"
TEST = CANDIDATE.parent / "tests/ViewApiBoundaryTests.java"
HOST_LEAVES = CANDIDATE.parent / "tests/host-leaves"
HOST_LEAVES_BASE = BASE.parent / "runs/cross-2/inputs/host-leaves"
DESCRIPTOR = CANDIDATE.parent / "tests/descriptor.json"
MANIFEST = CANDIDATE.parent / "manifest.json"
FREEZE = CANDIDATE.parent / "freeze.json"
CONTRACT = ROOT / "verification/android-view-api-boundary-selection-2026-10-29/contract.json"
OBSERVATION = ROOT / "verification/android-next-source-selection-2026-10-29/source-observation.json"
EXPECTED_CONTRACT = "a2f0c84ea91e5df9424a702fcb4a355632b99f66f9fce8f98e4204498840adc2"
RECORDED_BASE_TREE = "a5e4888b96995bf768062bd9c2f1573dc440a4fe22270a205ab5550e79f625e4"
EXPECTED_BASE_PROJECTION = "669d3b5ae0059e00aa51d2017723985bb94a22757c436db24c2950da0e2fe95c"
EXPECTED_MANIFEST = "e52dd5bd9c415a68c843724a24fec03c72c64dbce7fae2d18377c646a4b35834"
EXPECTED_FREEZE = "c458497920a6cf454433f2f96bbcdf42fbf8b6945e55e5a76c813dddb00af8ff"
CHANGED = {"NativeAppearanceViewsV2.java", "NativeRenderer.java"}
DRAWABLE_METHODS = (
    "setTextCursorDrawable", "setTextSelectHandle", "setTextSelectHandleLeft", "setTextSelectHandleRight",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_tree(folder):
    paths = sorted(folder.glob("*.java"))
    if len(paths) != 16:
        raise ValueError(f"expected exactly sixteen direct Java sources: {folder}")
    return {p.name: p.read_bytes() for p in paths}


def tree_digest(tree):
    return sha(b"".join(name.encode() + b"\0" + sha(data).encode() + b"\n" for name, data in sorted(tree.items())))


def historical_tree_digest(tree):
    rows = {name: {"bytes": len(data), "sha256": sha(data)} for name, data in tree.items()}
    return sha(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode())


def masked(text):
    # Keep offsets and braces stable while excluding strings/comments from the
    # small source-localization controls. This is not a Java semantic parser.
    pattern = r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(pattern, lambda m: "".join("\n" if c == "\n" else " " for c in m.group()), text)


def class_span(text, name):
    clean = masked(text)
    matches = list(re.finditer(r"\bclass\s+" + re.escape(name) + r"\s*\{", clean))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one source class {name}")
    begin = clean.index("{", matches[0].start())
    depth = 1
    for end in range(begin + 1, len(clean)):
        depth += (clean[end] == "{") - (clean[end] == "}")
        if depth == 0:
            return begin + 1, end
    raise ValueError(f"unbalanced source class {name}")


def source_checks(tree):
    views = tree["NativeAppearanceViewsV2.java"].decode()
    renderer = tree["NativeRenderer.java"].decode()
    checks = {}
    a29 = class_span(views, "Api29")
    a30 = class_span(views, "Api30")
    r30 = class_span(renderer, "Api30")
    for file_name, text, methods, span in (
        ("views", views, DRAWABLE_METHODS, a29),
        ("views", views, ("setStateDescription",), a30),
        ("renderer", renderer, ("setStateDescription",), r30),
    ):
        clean = masked(text)
        for method in methods:
            refs = list(re.finditer(r"\." + method + r"\s*\(", clean))
            checks[f"{file_name}.{method}.one_source_reference_in_helper"] = len(refs) == 1 and span[0] <= refs[0].start() < span[1]
    helper = views[a29[0]:a29[1]]
    positions = [helper.find("." + name + "(") for name in DRAWABLE_METHODS]
    checks["api29.source_setter_order"] = all(p >= 0 for p in positions) and positions == sorted(positions)
    for method in DRAWABLE_METHODS:
        match = re.search(r"\." + method + r"\([^;]*;\s*mutation\.require\(\);", helper)
        checks[f"api29.{method}.immediate_original_mutation_postcheck"] = match is not None
    helper30 = views[a30[0]:a30[1]]
    checks["api30.immediate_original_mutation_postcheck"] = bool(re.search(r"\.setStateDescription\([^;]*;\s*mutation\.require\(\);", helper30))
    # Shape check only; manual review verifies the surrounding preflight/branch
    # ordering and actual SDK_INT relation before source-only acceptance.
    checks["views.actual_sdk29_selector_present"] = bool(re.search(r"(?:android\.os\.)?Build\.VERSION\.SDK_INT\s*[<>]=?\s*29", views))
    checks["views.actual_sdk30_selector_present"] = bool(re.search(r"(?:android\.os\.)?Build\.VERSION\.SDK_INT\s*[<>]=?\s*30", views))
    checks["renderer.actual_sdk30_selector_present"] = bool(re.search(r"Build\.VERSION\.SDK_INT\s*[<>]=?\s*30", renderer))
    checks["views.accessibility_presence_predicate_present"] = 'properties.containsKey("accessibilityValue")' in views
    checks["renderer.v1_accessibility_presence_predicate_present"] = 'n.properties.containsKey("accessibilityValue")' in renderer
    checks["constructor.authority_before_pure_capability_preflight"] = bool(re.search(r"Record\(Context context, UiPacket.Node source, Input input, Mutation mutation\)\s*\{\s*mutation\.requireMutation\(\);\s*requireViewOperations\(source\);", views))
    checks["bind.authority_before_pure_capability_preflight"] = bool(re.search(r"void bind\(Binding next, Geometry measured, boolean preserveEditor, Mutation mutation\)\s*\{\s*mutation\.requireMutation\(\);\s*requireViewOperations\(next\.node,next\.source\);", views))
    return checks


def controls(candidate):
    cases = []
    def run(label, filename, transform, expected_key):
        changed = dict(candidate)
        before = changed[filename].decode()
        after = transform(before)
        if before == after:
            raise ValueError(f"control did not modify input: {label}")
        changed[filename] = after.encode()
        observed = source_checks(changed)
        cases.append({"control": label, "rejected_by": expected_key, "rejected": observed[expected_key] is False})
    for method in DRAWABLE_METHODS:
        run("remove_" + method + "_postcheck", "NativeAppearanceViewsV2.java",
            lambda s, m=method: re.sub(r"(\." + m + r"\([^;]*;)\s*mutation\.require\(\);", r"\1", s, count=1),
            f"api29.{method}.immediate_original_mutation_postcheck")
    run("remove_state_postcheck", "NativeAppearanceViewsV2.java",
        lambda s: re.sub(r"(\.setStateDescription\([^;]*;)\s*mutation\.require\(\);", r"\1", s, count=1),
        "api30.immediate_original_mutation_postcheck")
    run("extra_unguarded_outer_state_call", "NativeAppearanceViewsV2.java",
        lambda s: s.replace("private NativeAppearanceViewsV2() {}", "private NativeAppearanceViewsV2() {}\n    static void badOuter(android.view.View v){v.setStateDescription(null);}", 1),
        "views.setStateDescription.one_source_reference_in_helper")
    run("remove_presence_predicates", "NativeAppearanceViewsV2.java",
        lambda s: s.replace('properties.containsKey("accessibilityValue")', 'properties.containsKey("differentProperty")'),
        "views.accessibility_presence_predicate_present")
    run("swap_cursor_and_center_setters", "NativeAppearanceViewsV2.java",
        lambda s: s.replace("setTextCursorDrawable(", "__TEMP_CURSOR__(").replace("setTextSelectHandle(", "setTextCursorDrawable(").replace("__TEMP_CURSOR__(", "setTextSelectHandle("),
        "api29.source_setter_order")
    run("capability_before_constructor_authority", "NativeAppearanceViewsV2.java",
        lambda s: re.sub(r"mutation\.requireMutation\(\);\s*requireViewOperations\(source\);", "requireViewOperations(source);mutation.requireMutation();", s, count=1),
        "constructor.authority_before_pure_capability_preflight")
    run("capability_before_bind_authority", "NativeAppearanceViewsV2.java",
        lambda s: re.sub(r"mutation\.requireMutation\(\);\s*requireViewOperations\(next\.node,next\.source\);", "requireViewOperations(next.node,next.source);mutation.requireMutation();", s, count=1),
        "bind.authority_before_pure_capability_preflight")
    run("remove_v1_presence_predicate", "NativeRenderer.java",
        lambda s: s.replace('n.properties.containsKey("accessibilityValue")', 'n.properties.containsKey("differentProperty")'),
        "renderer.v1_accessibility_presence_predicate_present")
    return cases


def between(text, first, last):
    return text[text.index(first):text.index(last, text.index(first))]


def seal_review(result, stdout):
    if not result["all_data_checks_pass"] or not (OWNED / "REVIEW.md").is_file():
        raise ValueError("cannot seal absent or failed source-only review")
    command = result["command"] + " --seal-reviewed-source-only"
    receipt = {
        "schema": 1,
        "at": datetime.now(timezone.utc).isoformat(),
        "verdict": "accepted-source-and-focused-test-design-only",
        "open_findings_in_selected_scope": 0,
        "root_contract": {"path": str(CONTRACT.relative_to(ROOT)), "sha256": result["contract_sha256"]},
        "producer_freeze": result["producer_freeze"],
        "producer_manifest": result["producer_manifest"],
        "accepted_input_product_tree": RECORDED_BASE_TREE,
        "derivative_product_tree": result["candidate_product_tree_sha256"],
        "derivative_source_projection": result["candidate_source_projection_sha256"],
        "product_tree_algorithm": result["recorded_product_tree_algorithm"],
        "source_projection_algorithm": result["source_projection_algorithm"],
        "git_revision": {"observed": False, "reason": "Git prohibited; exact source tree digests bind this review"},
        "tool": dict(result["tool"], executable_identity={"bytes": len(Path(sys.executable).read_bytes()), "sha256": sha(Path(sys.executable).read_bytes())}, script_identity={"bytes": len(Path(__file__).read_bytes()), "sha256": sha(Path(__file__).read_bytes())}),
        "command": command,
        "observed_stdout": stdout,
        "stderr_bytes": 0,
        "exit_code": 0,
        "data_source_checks": len(result["source_checks"]),
        "corruption_controls": len(result["corruption_controls"]),
        "all_data_checks_and_controls_pass": True,
        "focused_test_source": result["focused_test_source"],
        "prepared_design": {"named_groups": 13, "setter_interruption_invocations": 152, "stale_cleanup_constructor_bind_invocations": 20, "host_javac_inputs": 103, "cross_javac_inputs": 17, "executed": False},
        "closed_finding": {"kind": "original Mutation authority validation precedence", "initial_product_projection": "ddbc1ebb65bbe30db962d1d99a095b0d49acc3c8017e17a9fdd0d2e481236a15", "correction": "original authority check first, pure capability preflight second, effects after both", "prepared_regression_group": "original-authority-entry-refusals", "local_preservation": "ignored local/authority-order-original-finding.json"},
        "source_pair_boundary": json.loads(CONTRACT.read_text())["sourcePairBoundary"],
        "runtime_compiler_product_test_or_node_oracle_runs": 0,
        "native_ui_capture_phone_runs": 0,
        "held_v5_or_equivalent_experiment_rerun_or_delegated": False,
        "held_cleanup": "unverified; no inventory, probe, signals or cleanup attempted",
        "canonical_global_source_pair_workflow_edits": False,
        "future_runtime_dispatch_authorized": False,
        "future_exact_pair_reconciliation_required": True,
        "pending": ["Java syntax and focused JVM assertions", "new helper emitted-class/constant-pool/instruction evidence", "pinned official SDK37 and D8 min-api28 evidence", "new exact source-pair selection", "old 189 V2 dispositions and 280-subject matrix", "native/ART/class-loading/IME/TalkBack/OEM/physical acceptance"],
        "holds": "all existing custody, native, Unit A and broad hosted holds preserved",
        "scope": "Independent manual source/test-design review plus bounded Python filesystem/hash/JSON/source-shape and in-memory corruption controls. No source subject imported/executed. No canonical/public V2/pre36 runtime/OTA/release/GA authority. VM integration outside this lane.",
    }
    (OWNED / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    members = (".gitignore", "REVIEW.md", "inspect_source.py", "source-checks.json", "receipt.json")
    seal = {
        "schema": 1,
        "verdict": receipt["verdict"],
        "producer_freeze_sha256": result["producer_freeze"]["sha256"],
        "producer_manifest_sha256": result["producer_manifest"]["sha256"],
        "derivative_product_tree": result["candidate_product_tree_sha256"],
        "scope": "Lean independent export; local/ failed baseline excluded; seal excludes itself",
        "members": [{"path": name, "bytes": len((OWNED / name).read_bytes()), "sha256": sha((OWNED / name).read_bytes())} for name in members],
        "runtime_or_canonical_authority": False,
    }
    (OWNED / "seal.json").write_text(json.dumps(seal, indent=2) + "\n")


def main():
    baseline = load_tree(BASE)
    candidate = load_tree(CANDIDATE)
    contract_hash = sha(CONTRACT.read_bytes())
    base_hash = tree_digest(baseline)
    changed = sorted(name for name in baseline if baseline[name] != candidate[name])
    observed_baseline = json.loads(OBSERVATION.read_text())["checks"]["frozen_editor16"]["rows"]
    observed_hashes = {Path(row["path"]).name: row["sha256"] for row in observed_baseline}
    leaves = {str(p.relative_to(HOST_LEAVES)): p.read_bytes() for p in sorted(HOST_LEAVES.rglob("*.java"))}
    leaves_baseline = {str(p.relative_to(HOST_LEAVES_BASE)): p.read_bytes() for p in sorted(HOST_LEAVES_BASE.rglob("*.java"))}
    manifest = json.loads(MANIFEST.read_text())
    freeze = json.loads(FREEZE.read_text())
    member_paths = [row["path"] for row in manifest["members"]]
    safe_members = all(not Path(name).is_absolute() and ".." not in Path(name).parts and not (CANDIDATE.parent / name).is_symlink() for name in member_paths)
    if not safe_members:
        raise ValueError("unsafe frozen member path")
    manifest_rows_match = all(len((CANDIDATE.parent / row["path"]).read_bytes()) == row["bytes"] and sha((CANDIDATE.parent / row["path"]).read_bytes()) == row["sha256"] for row in manifest["members"])
    actual_members = {str(p.relative_to(CANDIDATE.parent)) for p in CANDIDATE.parent.rglob("*") if p.is_file() and "local" not in p.relative_to(CANDIDATE.parent).parts and p not in (MANIFEST, FREEZE)}
    result = {
        "schema": 1,
        "at": datetime.now(timezone.utc).isoformat(),
        "scope": "filesystem/hash/JSON/source-shape and in-memory corruption controls only; no Java compilation or execution",
        "tool": {"executable": sys.executable, "version": sys.version},
        "command": "/opt/homebrew/opt/python@3.14/bin/python3.14 -I verification/android-view-api-boundary-independent/inspect_source.py",
        "source_inputs_imported_or_executed": False,
        "denials_installed_before_subject_imports": ["nested process", "process session/group", "signals", "timer/sleep/wait", "socket/network", "threads"],
        "contract_sha256": contract_hash,
        "recorded_accepted_baseline_tree_sha256": RECORDED_BASE_TREE,
        "source_projection_algorithm": "SHA256 of sorted basename + NUL + SHA256 + LF",
        "recorded_product_tree_algorithm": "SHA256 of {basename:{bytes,sha256}} JSON, sorted keys and compact separators",
        "baseline_source_projection_sha256": base_hash,
        "candidate_source_projection_sha256": tree_digest(candidate),
        "candidate_product_tree_sha256": historical_tree_digest(candidate),
        "baseline_observation_sha256": sha(OBSERVATION.read_bytes()),
        "focused_test_source": {"path": str(TEST.relative_to(ROOT)), "bytes": len(TEST.read_bytes()), "sha256": sha(TEST.read_bytes())},
        "descriptor": {"bytes": len(DESCRIPTOR.read_bytes()), "sha256": sha(DESCRIPTOR.read_bytes())},
        "host_leaf_custody": {"members": len(leaves), "baseline": str(HOST_LEAVES_BASE.relative_to(ROOT)), "projection_sha256": tree_digest(leaves), "all_byte_identical": leaves == leaves_baseline},
        "producer_freeze": {"path": str(FREEZE.relative_to(ROOT)), "bytes": len(FREEZE.read_bytes()), "sha256": sha(FREEZE.read_bytes())},
        "producer_manifest": {"path": str(MANIFEST.relative_to(ROOT)), "bytes": len(MANIFEST.read_bytes()), "sha256": sha(MANIFEST.read_bytes()), "member_count": len(member_paths), "member_bytes": sum(row["bytes"] for row in manifest["members"])},
        "changed_sources": changed,
        "unchanged_sources": sorted(set(baseline) - set(changed)),
        "source_checks": source_checks(candidate),
        "corruption_controls": controls(candidate),
        "source_rows": [{"name": name, "bytes": len(data), "sha256": sha(data)} for name, data in sorted(candidate.items())],
    }
    result["source_checks"].update({
        "exact_selected_contract": contract_hash == EXPECTED_CONTRACT,
        "exact_accepted_baseline_same_algorithm_projection": base_hash == EXPECTED_BASE_PROJECTION,
        "exact_accepted_baseline_recorded_product_tree": historical_tree_digest(baseline) == RECORDED_BASE_TREE,
        "accepted_baseline_matches_all_named_observation_rows": len(observed_hashes) == len(baseline) and all(observed_hashes.get(name) == sha(data) for name, data in baseline.items()),
        "exact_86_mechanical_leaves_byte_custody": len(leaves) == 86 and leaves == leaves_baseline,
        "exact_9587_byte_descriptor": len(DESCRIPTOR.read_bytes()) == 9587 and sha(DESCRIPTOR.read_bytes()) == "1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3",
        "exact_producer_freeze": sha(FREEZE.read_bytes()) == EXPECTED_FREEZE,
        "exact_producer_manifest": sha(MANIFEST.read_bytes()) == EXPECTED_MANIFEST,
        "frozen_manifest_all_115_unique_members_match": len(member_paths) == len(set(member_paths)) == 115 and manifest_rows_match and actual_members == set(member_paths),
        "frozen_manifest_size_totals_match": manifest["member_count"] == freeze["member_count"] == len(member_paths) and manifest["member_bytes"] == freeze["member_bytes"] == sum(row["bytes"] for row in manifest["members"]),
        "frozen_product_tree_matches_reviewed_bytes": freeze["derivative_product_tree"] == historical_tree_digest(candidate),
        "freeze_manifest_identity_matches": freeze["manifest"]["sha256"] == sha(MANIFEST.read_bytes()) and freeze["manifest"]["bytes"] == len(MANIFEST.read_bytes()),
        "only_allowed_product_edits": set(changed) == CHANGED,
        "coordinator_unchanged_including_commit_finish_interval": candidate["NativeCoordinatorV2.java"] == baseline["NativeCoordinatorV2.java"],
        "observer_unchanged_including_api36_guard": candidate["NativeEnvironmentV2.java"] == baseline["NativeEnvironmentV2.java"],
        "renderer_finishV2_exact": between(candidate["NativeRenderer.java"].decode(), "    void finishV2(", "    void validateAttachedV2(") == between(baseline["NativeRenderer.java"].decode(), "    void finishV2(", "    void validateAttachedV2("),
        "renderer_requireV2Live_exact": between(candidate["NativeRenderer.java"].decode(), "    private void requireV2Live(){", "    private void faultV2(){") == between(baseline["NativeRenderer.java"].decode(), "    private void requireV2Live(){", "    private void faultV2(){"),
    })
    result["all_data_checks_pass"] = all(result["source_checks"].values()) and all(c["rejected"] for c in result["corruption_controls"])
    output = OWNED / "source-checks.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    stdout = json.dumps({"output": str(output.relative_to(ROOT)), "checks": len(result["source_checks"]), "controls": len(result["corruption_controls"]), "all_data_checks_pass": result["all_data_checks_pass"], "candidate_source_projection_sha256": result["candidate_source_projection_sha256"], "candidate_product_tree_sha256": result["candidate_product_tree_sha256"]}) + "\n"
    if sys.argv[1:] == ["--seal-reviewed-source-only"]:
        seal_review(result, stdout)
    elif sys.argv[1:]:
        raise ValueError("unknown arguments")
    print(stdout, end="")
    return 0 if result["all_data_checks_pass"] else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--verify-review-seal"]:
        seal_bytes = (OWNED / "seal.json").read_bytes()
        seal = json.loads(seal_bytes)
        expected_paths = {".gitignore", "REVIEW.md", "inspect_source.py", "source-checks.json", "receipt.json"}
        rows = seal["members"]
        matched = {r["path"] for r in rows} == expected_paths and len(rows) == len(expected_paths)
        matched = matched and all(len((OWNED / r["path"]).read_bytes()) == r["bytes"] and sha((OWNED / r["path"]).read_bytes()) == r["sha256"] for r in rows)
        print(json.dumps({"independent_seal_members_match": matched, "members": len(rows), "seal_sha256": sha(seal_bytes), "producer_freeze_sha256": seal["producer_freeze_sha256"]}))
        raise SystemExit(0 if matched else 1)
    raise SystemExit(main())
