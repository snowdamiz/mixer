#!/usr/bin/env python3
"""Audit a proposed boundary. Never execute or qualify product JNI/device code."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = "61c5c8b2e0af59ea98d3ff85f208ad97df069411"
ACCEPTANCE = "verification/android-binding-stage4-root-review/acceptance.json"
ACCEPTANCE_SHA = "69bd4ab51dc8ebe7eb968baade461114dad48e35040da527dc946953575bfe79"
SECTION_SHA = "184934dd462f0f46d42fb13d1076433f0d538c37770e991f49812ddbbd323ef4"
DOC = "docs/android-jni-stage5-seams.md"
EXPECTED_NAMES = [
    "native_scope_isolation", "native_actual_task_return", "sdk_snapshot_native_packet",
    "signed_node_depth_byte_limits", "unsigned_utf8_transport", "closed_raw_json",
    "validate_before_view_mutation", "closed_property_action_subset",
    "successor_identity_lifetime", "scalar_listener_ownership",
    "interaction_overlay_exact_gates", "shared_theme_required", "install_fixed_cache_once",
    "actual_main_looper_install", "counted_ingress_before_lookup", "no_jnienv_attach_storage",
    "weak_prepublication_obligation", "attach_close_exception_race", "attachment_exact_reference",
    "published_weak_collected", "bounded_locals_exceptions", "fixed_apply_slot_postcondition",
    "nested_native_callback_busy", "reentrant_scalar_close_postcheck", "native_input_full_tuple",
    "s4_21_stale_jni_event_fallback", "s4_21_stale_probe_attachment", "single_event_busy_no_replay",
    "detach_cleanup_leased", "attempt_retire_weak_retained", "final_cleanup_real_weak_delete",
    "native_slot_reuse_after_final_fences", "reserved_never_slot_setup_rollback",
    "late_final_terminal_endpoint", "fault_join_admission_orderings", "held_return_fences",
    "final_alias_destructor_capacity", "draw_origin_marker_experiment", "real_draw_return_later_frame",
    "manual_offscreen_draw_no_observation", "window_visibility_lifecycle_probe",
    "current_ticket_effects_health_boundary", "strict_link_required_symbols",
    "android_full_boundary_closure", "accepted_host_apple_regressions",
    "s4_29_optimized_lifetime_exhaustion", "design_parity_reference_states",
    "physical_ios_android_design_parity", "signed_core_vm_kv_health_integration",
    "published_fieldlog_external_gates",
]
JNI_METHODS = {
    "nativeInstall": "()I",
    "nativeAttach": "(JJLdev/mixer/android/SignedGuestScreen;)I",
    "nativeActivate": "(JJJJ[BJ)I",
    "nativeObserve": "(JJJJJ)I",
    "nativeRequestClose": "(JI)I",
    "nativeDetachUI": "(JJ)I",
}
JAVA_CALLS = {
    "applySigned": "(JJJ[B)I", "setInteraction": "(I)I",
    "retireSigned": "(I)I", "consumeObservation": "(JJJJ)I",
}
BOUNDS = {
    "facades": 16, "weak_globals_per_facade": 1, "class_globals": 2,
    "local_refs_per_helper": 16, "packet_bytes": 1048576, "guest_bytes": 65536,
    "nodes": 256, "depth": 16, "children": 64, "string_utf8_bytes": 4096,
    "identifier_utf8_bytes": 128,
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(path: Path) -> str:
    return sha(path.read_bytes())


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def normalized_c(value: str) -> str:
    # Declaration consistency only. Never a validation or release authorization.
    return re.sub(r"\s+", "", value)


def validate_api(api: dict, document: str, current_header: str) -> list[str]:
    errors = []
    if api.get("status") != "proposal_only_not_implementation_authorization":
        errors.append("API scope must remain a proposal")
    methods = api.get("java_origin_methods", [])
    if len(methods) != len(JNI_METHODS) or {m.get("name"): m.get("descriptor") for m in methods} != JNI_METHODS:
        errors.append("Fixed Java/JNI descriptor inventory changed")
    for m in methods:
        if m.get("jni_symbol") != "Java_dev_mixer_android_SignedGuestScreen_" + m.get("name", ""):
            errors.append("Unexpected JNI symbol")
        if m.get("jni_return") != "jint" or m.get("access") != "private static native":
            errors.append("Unexpected JNI return/access")
        if m.get("descriptor", "") not in document:
            errors.append("JNI descriptor missing from proposal")
    calls = api.get("native_to_java_methods", [])
    if len(calls) != len(JAVA_CALLS) or {m.get("name"): m.get("descriptor") for m in calls} != JAVA_CALLS:
        errors.append("Cached native-to-Java method inventory changed")
    if api.get("bounds") != BOUNDS:
        errors.append("Closed resource or codec bounds changed")
    if api.get("constructor_descriptor") != "(Landroid/app/Activity;JJ)V":
        errors.append("Fixed constructor descriptor changed")
    for decl in api.get("fixed_c_declarations", []):
        if normalized_c(decl) not in normalized_c(document):
            errors.append("API declaration missing from proposal: " + decl)
    symbols = api.get("unchanged_c_symbols", [])
    if symbols != ["mxis_apply", "mxis_interaction", "mxis_retire"]:
        errors.append("Immutable bridge symbol inventory changed")
    for symbol in symbols:
        matches = [d for d in api.get("fixed_c_declarations", []) if symbol + "(" in d]
        if len(matches) != 1 or normalized_c(matches[0]) not in normalized_c(current_header):
            errors.append("Existing immutable bridge declaration drift: " + symbol)
    current = api.get("current_scope", {})
    if current.get("owned_paths") != [DOC, "verification/android-jni-stage5-contract/**"]:
        errors.append("Proposal ownership escaped bounded paths")
    if any(current.get(k) is not False for k in ["commits_or_pushes", "production_mutation"]):
        errors.append("Proposal must not authorize mutation/publication")
    if current.get("native_acceptance_cases_executed") != 0:
        errors.append("Proposal cannot claim native execution")
    return errors


def validate_matrix(matrix: dict) -> list[str]:
    errors = []
    cases = matrix.get("cases", [])
    if matrix.get("status") != "planned_only_not_executed":
        errors.append("Matrix may not claim execution")
    if matrix.get("executed_native_acceptance_cases") != 0:
        errors.append("No native case executes in this proposal")
    if any(matrix.get(k) is not False for k in ["native_android_authority", "full_original_dynamic32_pass", "ga_gate_pass"]):
        errors.append("Matrix may not promote native/dynamic32/GA authority")
    if matrix.get("case_count") != len(EXPECTED_NAMES) or len(cases) != len(EXPECTED_NAMES):
        errors.append("Matrix case count mismatch")
    if [c.get("id") for c in cases] != [f"J5-{i:02d}" for i in range(1, len(EXPECTED_NAMES) + 1)]:
        errors.append("Missing/duplicate/out-of-order matrix ID")
    if [c.get("name") for c in cases] != EXPECTED_NAMES:
        errors.append("Executable named case inventory changed")
    for c in cases:
        if not str(c.get("status", "")).startswith("pending_"):
            errors.append("Proposal case may only be pending: " + str(c.get("id")))
        if not all(c.get(k) for k in ["prerequisites", "schedule", "pass", "contract_sections"]):
            errors.append("Missing prerequisite/schedule/oracle/clause: " + str(c.get("id")))
        runner = c.get("runner")
        if c.get("scope") in ["physical", "external"]:
            if runner is not None or c.get("required_modes") != []:
                errors.append("Physical/external gate must have no runnable action here")
        elif not isinstance(runner, str) or not runner.startswith("verification/android-jni-stage5-") or not runner.endswith("/verify.py"):
            errors.append("Unexpected proposed runner path")
        elif not c.get("required_modes"):
            errors.append("Executable case missing build modes")
    return errors


def validate_lock(lock: dict, root: Path = ROOT) -> tuple[list[dict], list[str]]:
    checks, errors = [], []
    if lock.get("accepted_host_revision") != BASE or lock.get("stage4_acceptance_sha256") != ACCEPTANCE_SHA:
        errors.append("Frozen host prerequisite identity changed")
    for path, expected in lock.get("files_sha256", {}).items():
        relative = Path(path)
        if relative.is_absolute() or ".." in relative.parts:
            errors.append("Invalid input path: " + path)
            continue
        target = root / relative
        try:
            actual = digest(target) if target.is_file() and not target.is_symlink() else None
        except OSError:
            actual = None
        checks.append({"path": path, "expected": expected, "observed": actual, "matches": actual == expected})
        if actual != expected:
            errors.append("Locked input drift/missing/symlink: " + path)
    if not checks:
        errors.append("Empty input lock")
    expected_tree = sha("".join(path + "\0" + value + "\n"
                                for path, value in sorted(lock.get("files_sha256", {}).items())).encode())
    if lock.get("input_tree_sha256") != expected_tree:
        errors.append("Input manifest content digest mismatch")
    return checks, errors


def run(argv: list[str]) -> dict:
    try:
        p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False, timeout=30)
        return {"argv": argv, "cwd": str(ROOT), "exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"argv": argv, "cwd": str(ROOT), "exit": None, "error": str(e)}


def network_specs(specs: dict) -> tuple[list[dict], list[str]]:
    checks, errors = [], []
    for spec in specs["sources"]:
        url = spec["url"]
        if not url.startswith(("https://developer.android.com/", "https://docs.oracle.com/")):
            errors.append("Nonofficial spec URL")
            continue
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                body = response.read(8_388_609)
                actual = sha(body) if len(body) <= 8_388_608 else None
            check = {"url": url, "expected": spec["retrieved_body_sha256"], "observed": actual,
                     "matches": actual == spec["retrieved_body_sha256"]}
            checks.append(check)
            if not check["matches"]:
                errors.append("Official spec page drift: " + url)
        except OSError as e:
            checks.append({"url": url, "error": str(e)})
            errors.append("Unable to re-fetch official spec: " + url)
    return checks, errors


def planned_commands(matrix: dict) -> list[dict]:
    result = []
    for c in matrix["cases"]:
        if c["runner"] is None:
            result.append({"id": c["id"], "name": c["name"], "status": c["status"], "argv": None})
        else:
            for mode in c["required_modes"]:
                result.append({"id": c["id"], "name": c["name"], "status": c["status"], "argv": [
                    "python3", c["runner"], "--case", c["name"], "--mode", mode,
                    "--output", f"verification/android-jni-stage5-integration/runs/{c['name']}/{mode}"]})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="Print unexecuted future runner commands only")
    parser.add_argument("--check-network-specs", action="store_true", help="Re-fetch exact official pages; fail on drift")
    args = parser.parse_args()
    errors = []
    lock = read_json(OUT / "input-lock.json")
    api = read_json(OUT / "api.json")
    matrix = read_json(OUT / "acceptance-matrix.json")
    specs = read_json(OUT / "spec-inputs.json")
    document = (ROOT / DOC).read_text()
    checks, locked_errors = validate_lock(lock)
    errors.extend(locked_errors)
    errors.extend(validate_matrix(matrix))
    header = (ROOT / "native/android/signed-guest-ui/binding/include/mixer_ui_binding.h").read_text()
    errors.extend(validate_api(api, document, header))
    if digest(ROOT / ACCEPTANCE) != ACCEPTANCE_SHA:
        errors.append("Stage4 root acceptance bytes changed")
    acceptance = read_json(ROOT / ACCEPTANCE)
    if acceptance.get("decision") != "accepted_private_host_implementation_and_local_fresh_CI_scope_only":
        errors.append("Stage4 scope must remain accepted host-only")
    if any(acceptance.get(k) is not False for k in ["full_original_dynamic_matrix_pass", "native_android_authority", "release_authority", "ga_gate_pass"]):
        errors.append("Stage4 cannot be promoted by this proposal")
    product = (ROOT / "mixer-product-plan.md").read_text()
    section = product.split("### 8.3 UI instruction contract\n", 1)[1].split("### 8.4 Performance design", 1)[0]
    section_with_heading = "### 8.3 UI instruction contract\n" + section
    section_digests = {sha(section_with_heading.encode()), sha(section_with_heading.rstrip().encode())}
    if SECTION_SHA not in section_digests:
        errors.append("Updated product-plan8.3 design-parity section changed")
    commands = [run(["git", "rev-parse", "HEAD"]), run(["git", "status", "--porcelain=v1"]),
                run(["git", "--version"]), run([sys.executable, "--version"]),
                run(["clang", "--version"]), run(["swiftc", "--version"])]
    if any(c["exit"] != 0 for c in commands):
        errors.append("Required metadata/tool-version command failed")
    spec_checks = []
    if args.check_network_specs:
        spec_checks, spec_errors = network_specs(specs)
        errors.extend(spec_errors)
    own_paths = [Path(DOC)] + [p.relative_to(ROOT) for p in sorted(OUT.iterdir())
                              if p.is_file() and (p.suffix in [".py", ".json", ".md"])
                              and not p.name.startswith("receipt")]
    own = {str(p): digest(ROOT / p) for p in own_paths}
    tools = {}
    for name in ["git", "clang", "swiftc"]:
        path = shutil.which(name)
        tools[name] = {"path": path, "sha256": digest(Path(path).resolve()) if path else None}
    tools["python"] = {"path": sys.executable, "sha256": digest(Path(sys.executable).resolve()),
                       "optimization": sys.flags.optimize}
    receipt = {
        "schema_version": 1, "observed_utc": datetime.now(timezone.utc).isoformat(),
        "executor": "/root/android_jni_stage5_contract", "argv": sys.argv,
        "scope": "Proposal source/API/spec input binding and inventory only; no JNI implementation, native delivery, device or release acceptance.",
        "source_revision_observed": commands[0].get("stdout", "").strip(),
        "accepted_host_revision": BASE, "input_tree_sha256": lock["input_tree_sha256"],
        "input_lock_sha256": digest(OUT / "input-lock.json"), "proposal_files_sha256": own,
        "source_bindings": checks, "source_binding_count": len(checks),
        "tool_commands": commands, "tools": tools, "platform": platform.platform(),
        "official_spec_network_checked": args.check_network_specs, "official_spec_network_results": spec_checks,
        "proposal_case_count": len(matrix["cases"]), "executed_native_acceptance_cases": 0,
        "native_android_authority": False, "full_original_dynamic32_pass": False,
        "release_authority": False, "ga_gate_pass": False,
        "result": "proposal_inputs_and_inventory_bound" if not errors else "proposal_audit_failed",
        "errors": errors,
        "pending": ["Root review and explicit implementation assignments", "5N actual sealed native backend prerequisite",
                    "5T root-frozen additive shared appearance contract", "All50 proposed implementation cases",
                    "S4-21 actual stale JNI delivery", "S4-29 optimized Release lifetime-counter injection",
                    "Stage6 signed core/Prepared/factory and health integration", "Actual Window/manual-draw exclusion proof",
                    "Physical iOS/Android design parity; phones disconnected", "Published separate-repo FieldLog and external GA gates"],
    }
    suffix = "-plan" if args.plan else ("-optimized" if sys.flags.optimize else "")
    (OUT / f"receipt{suffix}.json").write_text(json.dumps(receipt, indent=2) + "\n")
    summary = {k: receipt[k] for k in ["result", "source_binding_count", "proposal_case_count", "executed_native_acceptance_cases", "errors"]}
    if args.plan:
        summary["planned_commands_not_executed"] = planned_commands(matrix)
    print(json.dumps(summary, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
