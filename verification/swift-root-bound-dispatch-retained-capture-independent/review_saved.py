"""Independent source/hash review; never import or execute either controller."""
from pathlib import Path
import ast
import copy
import datetime
import difflib
import hashlib
import json
import stat
import time

ROOT = Path("/Users/andreyyurlov/Documents/dev/mixer")
OWN = ROOT / "verification/swift-root-bound-dispatch-retained-capture-independent"
NEW = ROOT / "verification/swift-root-bound-dispatch-retained-capture-v1"
OLD = ROOT / "verification/swift-root-bound-dispatch-physical-capture-v1"
OLD_BASE = ROOT / "verification/swift-root-bound-dispatch-physical-plan/capture-plan.json"
PYTHON = "/opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14/bin/python3.14"
RELEASE = ROOT / "verification/swift-semantic-adapter-root-review/dispatch-retained-physical-capture-release.json"
SUBJECT = {
    "base_capture_plan_sha256": "15413684daf6815fbc9773c7fecf669f035768116524e567a841bd571c3f31c8",
    "controller_plan_sha256": "1a7eb62837ade6b2f8256f64111bb11bc57fb216308b0131785a3990d744a601",
    "controller_sha256": "0f5787fad45bbe26db6273faa4d541224f3ffd65c84ba2cf01a7f2aff4ddae01",
    "capture_packet_seal_sha256": "df44b2b8f1cb54a873440f266756fcc84e72dc5e23a2b3e001766788ef261cb6",
}
ARGV_SHA = "799f61fd0bff3d5eba3849b784e7bc7b699a5ee84a2a814f298f407befb28e75"
OLD_BASE_SHA = "bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184"
OLD_PLAN_SHA = "3534a9d4bc5428335b3dec4cc295f0b55b1a8ea1c778e265fabdcb9fefb6743e"
OLD_CONTROLLER_SHA = "1c8036e0dcd5e173c2e379ee6e711c06644638f6fb2caad312c4d41f29ddd98f"
OLD_ARGV_SHA = "4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa"
START = time.monotonic()


def require(value, message):
    if not value:
        raise RuntimeError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def path_for(name, base=ROOT):
    path = Path(name)
    require(path.is_absolute() or all(x not in ("", ".", "..") for x in name.split("/")), "escaping relative path")
    return path if path.is_absolute() else base / path


def row(path, base=ROOT):
    require(time.monotonic() - START < 55, "source review 55-second ceiling")
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and path.resolve(strict=True) == path, "nonregular/redirected input")
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        opened = handle.fileno()
        # Read and hash immutable files only; no module imports or subprocesses.
        while raw := handle.read(262144):
            require(time.monotonic() - START < 55, "source review hash deadline")
            h.update(raw)
            size += len(raw)
    after = path.lstat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and size == before.st_size,
            "input changed during hash")
    return {"path": str(path.relative_to(base)) if path.is_relative_to(base) else str(path),
            "bytes": size, "sha256": h.hexdigest()}


def read(path, expected=None):
    item = row(path)
    if expected is not None:
        require(item["sha256"] == expected, "unexpected pinned hash: " + str(path))
    return json.loads(path.read_text())


def verify_seal(folder, expected):
    seal = read(folder / "seal.json", expected)
    require(len(seal["members"]) == seal["member_count"] <= 64, "seal count")
    require(len({r["path"] for r in seal["members"]}) == seal["member_count"], "duplicate seal member")
    require(sha(canonical(seal["members"])) == seal["tree_sha256"], "seal aggregate")
    for member in seal["members"]:
        require(row(path_for(member["path"], folder), folder) == member, "sealed member changed")
    return seal


def write(name, value, raw=False):
    require(Path(name).name == name, "write outside own review")
    with (OWN / name).open("xb") as handle:
        handle.write(value.encode() if raw else (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def main():
    require(not (OWN / "seal.json").exists(), "independent review already frozen")
    packet = verify_seal(NEW, SUBJECT["capture_packet_seal_sha256"])
    old_packet = verify_seal(OLD, "550f6e81fd3abcd5ad74999d953638d99f426f710d48369792922801f753430d")
    require(packet["member_count"] == 18 and packet["member_bytes"] == 209398, "selected packet member/byte count")
    actual_packet_roster = sorted(str(p.relative_to(NEW)) for p in NEW.rglob("*") if p.is_file())
    require(actual_packet_roster == sorted([r["path"] for r in packet["members"]] + ["seal.json"]), "extra packet file")
    require(not (NEW / "command").exists() and not (NEW / "runtime").exists() and not RELEASE.exists(), "capture/release already exists")
    old_base = read(OLD_BASE, OLD_BASE_SHA)
    old_plan = read(OLD / "plan.json", OLD_PLAN_SHA)
    base = read(NEW / "base-capture-plan.json", SUBJECT["base_capture_plan_sha256"])
    plan = read(NEW / "plan.json", SUBJECT["controller_plan_sha256"])
    require(row(NEW / "run-capture.py")["sha256"] == SUBJECT["controller_sha256"], "new controller hash")
    require(row(OLD / "run-capture.py")["sha256"] == OLD_CONTROLLER_SHA, "proven controller hash")
    manifest = read(NEW / "input-manifest.json")
    inputs = manifest["inputs"]
    require(len(inputs) <= 384 and sum(r["bytes"] for r in inputs) <= 4294967296 and
            len({r["path"] for r in inputs}) == len(inputs), "bounded unique approved inputs")
    before = [row(path_for(r["path"])) for r in inputs]
    require(before == inputs, "approved immutable input changed")
    by_path = {r["path"]: r for r in inputs}
    source_manifest = read(path_for(base["source_manifest"]["path"]), base["source_manifest"]["sha256"])
    source_root = Path(base["source_directory"])
    require(len(source_manifest["members"]) == source_manifest["member_count"] == 146 and
            sha(canonical(source_manifest["members"])) == base["source_tree_sha256"] ==
            source_manifest["tree_sha256"] == "91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f", "original source146")
    for item in source_manifest["members"]:
        full = path_for(item["path"], source_root)
        require(by_path[str(full.relative_to(ROOT))] == {**item, "path": str(full.relative_to(ROOT))}, "source pin absent from runtime inputs")
    require(sorted(str(p.relative_to(source_root)) for p in source_root.rglob("*") if p.is_file()) ==
            sorted(r["path"] for r in source_manifest["members"]), "exact source roster changed")
    tools = read(path_for(base["toolchain_manifest"]["path"]), base["toolchain_manifest"]["sha256"])
    require(len(tools["members"]) == 67 and sha(canonical(tools["members"])) == tools["tree_sha256"], "compiler/sysroot manifest")
    for item in tools["members"]:
        full = path_for(item["path"], Path(tools["root"]))
        require(by_path[str(full)] == {**item, "path": str(full)}, "tool pin absent from runtime inputs")

    argv = old_base["argv"][:-1] + ["-C", "link-dead-code=yes",
        "--emit=llvm-ir=" + str(NEW / "command/dispatch.ll") + ",asm=" + str(NEW / "command/dispatch.s")]
    require(sha(canonical(old_base["argv"])) == OLD_ARGV_SHA and sha(canonical(argv)) == ARGV_SHA, "argv pins")
    require(base["argv"] == plan["argv"] == read(NEW / "argv.json")["argv"] == argv, "exact sole option and emit-path delta")
    expected_base = copy.deepcopy(old_base)
    base_delta_keys = {"alternate_diagnostic_configuration_only", "approach", "argv", "argv_sha256_canonical_JSON",
        "complete_capacity_accepted", "environment", "frontier_complete", "inspection_only_settings", "link_dead_code",
        "original_argv_sha256", "original_capture_plan", "original_capture_qualified", "owned_output_directory",
        "root_release_required", "runtime_admission_accepted", "source_reachability_assessment", "status", "target_mapping_may_still_fail"}
    expected_base.update({key: base[key] for key in base_delta_keys})
    require(expected_base == base, "undeclared base-plan field changed")
    plan_delta_keys = base_delta_keys | {"base_capture_plan", "controller_argv", "controller_environment",
        "controller_environment_provenance", "controller_path", "original_controller_plan", "ownership_selection",
        "reference_controller", "verifier_binding"}
    expected_plan = copy.deepcopy(old_plan)
    expected_plan.update({key: plan[key] for key in plan_delta_keys})
    require(expected_plan == plan, "undeclared controller-plan field changed")
    for key in ("argv", "environment", "cwd", "bounds", "source_directory", "source_tree_sha256", "source_manifest", "compiler", "toolchain_manifest", "SDK_manifest"):
        require(base[key] == plan[key], "base/controller field differs: " + key)
    for key in ("bounds", "source_directory", "source_tree_sha256", "source_manifest", "compiler", "toolchain_manifest", "SDK_manifest", "cwd", "stop_without_fallback"):
        require(base[key] == old_base[key], "unchanged capture contract differs: " + key)
    for key in ("environment", "controller_environment"):
        restored = copy.deepcopy(plan[key])
        require(len(restored) == 8 and restored["TMPDIR"] == str(NEW / "command/tmp"), "eight-key new TMPDIR environment")
        restored["TMPDIR"] = old_plan[key]["TMPDIR"]
        require(restored == old_plan[key], "additional environment mutation")
    require(plan["retained_evidence_bounds"] == old_plan["retained_evidence_bounds"], "retained bounds changed")
    require(plan["python_tool"] == old_plan["python_tool"] and plan["python_version_from_this_preparation"] == old_plan["python_version_from_this_preparation"], "saved Python identity changed")
    require(plan["owned_output_directory"] == base["owned_output_directory"] == str(NEW / "command") and
            plan["controller_path"] == str(NEW / "run-capture.py") and plan["controller_argv"] == [PYTHON, "-B", str(NEW / "run-capture.py")] and
            plan["root_release_required"]["path"] == base["root_release_required"]["path"] == str(RELEASE.relative_to(ROOT)), "separate exact owned paths")
    binding = copy.deepcopy(old_plan["verifier_binding"])
    binding.update(alternate_diagnostic_configuration_only=True, link_dead_code=True,
        capture_plan_sha256=SUBJECT["base_capture_plan_sha256"], argv_sha256=ARGV_SHA)
    require(plan["verifier_binding"] == binding, "alternate-build identity binding")
    for data in (packet, base, plan):
        require(data["alternate_diagnostic_configuration_only"] is True and data["original_capture_qualified"] is False and
                data["runtime_admission_accepted"] is False and data["frontier_complete"] is False and data["complete_capacity_accepted"] is False, "alternate scope")

    old_text = (OLD / "run-capture.py").read_text()
    new_text = (NEW / "run-capture.py").read_text()
    inventory = read(NEW / "change-inventory.json")
    expected_text = old_text
    for item in inventory["controller_replacements"]:
        require(expected_text.count(item["before"]) == 1, "ambiguous inventory replacement")
        expected_text = expected_text.replace(item["before"], item["after"], 1)
    require(expected_text == new_text and len(inventory["controller_replacements"]) == 11, "controller differs from exact inventory")
    require(new_text.count('"alternate_diagnostic_configuration_only": True, "original_capture_qualified": False, "runtime_admission_accepted": False,') == 3, "three alternate scope output insertions")
    old_ast, new_ast = ast.parse(old_text), ast.parse(new_text)
    old_functions = {n.name: ast.dump(n, include_attributes=False) for n in old_ast.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    new_functions = {n.name: ast.dump(n, include_attributes=False) for n in new_ast.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    require(old_functions.keys() == new_functions.keys() and all(old_functions[k] == new_functions[k] for k in old_functions if k != "main"), "behavioral function delta outside main scope records")
    for filename, old_source, new_source, old_name, new_name in (
        ("controller-delta.patch", old_text, new_text, "proven-capture-v1/run-capture.py", "retained-capture-v1/run-capture.py"),
        ("base-plan-delta.patch", OLD_BASE.read_text(), (NEW / "base-capture-plan.json").read_text(), "original/capture-plan.json", "retained-capture-v1/base-capture-plan.json"),
        ("controller-plan-delta.patch", (OLD / "plan.json").read_text(), (NEW / "plan.json").read_text(), "original/plan.json", "retained-capture-v1/plan.json")):
        require((NEW / filename).read_text() == "".join(difflib.unified_diff(old_source.splitlines(True), new_source.splitlines(True), fromfile=old_name, tofile=new_name)), "incomplete delta patch")
    for name in ("diagnostic-policy.json", "diagnostic-policy-provenance.json"):
        require((NEW / name).read_bytes() == (OLD / name).read_bytes(), "diagnostic policy/provenance changed")
    policy = read(NEW / "diagnostic-policy.json")
    require(policy["source_tree"] == plan["source_tree_sha256"] and len(policy["records"]) == 4 and
            [r["level"] for r in policy["records"]] == ["warning"] * 4 and policy["records"][-1]["message"] == "3 warnings emitted", "exact three warnings and summary")
    schema = read(NEW / "release-schema.json")
    release_fields = schema["required_fields"]
    require(schema["path"] == str(RELEASE.relative_to(ROOT)) and schema["preparation_does_not_supply_or_authorize_this_release"] is True, "fresh root release location")
    for key in ("base_capture_plan_sha256", "controller_plan_sha256", "controller_sha256"):
        require(release_fields[key] == SUBJECT[key] and release_fields["independent_source_review_subject"][key] == SUBJECT[key], "release exact subject binding")
    require(release_fields["argv_sha256"] == ARGV_SHA and release_fields["compiler_invocations"] == 1 and
            release_fields["automatic_retries"] == 0 and release_fields["semantic_map_approved"] is False and
            release_fields["actual_verifier_input_run_released"] is False and release_fields["independent_source_review_accepted"] is True, "one-shot capture-only release")
    require(set(release_fields["independent_source_review_subject"]) == set(SUBJECT), "exact four review subject fields")
    original_observation = read(OLD / "runtime/capture-observation.json")
    original_receipt = read(OLD / "runtime/receipt.json")
    mapping = read(ROOT / "verification/swift-physical-map-independent/review-result.json")
    assessment = read(ROOT / "verification/swift-physical-source-reachability/inspection.json")
    require(original_receipt["status"] == "captured-artifacts-only" and original_observation["capture_complete"] is True and
            mapping["unresolved_targets"] == ["Caller", "Closure", "Dispatch", "Body"] and mapping["frontier_complete"] is False and
            assessment["capture_cause_proved"] is False, "original capture boundary")

    after = [row(path_for(r["path"])) for r in inputs]
    require(before == after, "approved inputs changed during review")
    require(verify_seal(NEW, SUBJECT["capture_packet_seal_sha256"]) == packet and
            verify_seal(OLD, "550f6e81fd3abcd5ad74999d953638d99f426f710d48369792922801f753430d") == old_packet, "packet changed during review")
    require(not (NEW / "command").exists() and not (NEW / "runtime").exists() and not RELEASE.exists(), "review created capture/release outputs")
    write("review-inputs.json", {"schema": 1, "before": before, "after": after, "equal": True})
    findings = """The selected 18-member packet is sound for a fresh root-selected one-shot raw capture of the alternate diagnostic configuration. No blocking source-review finding was identified. This independent review does not release execution.

The original source146, target, cfg, Debug settings, compiler/sysroot/SDK identity manifests and saved Python identity remain bound. The only added compiler option is `-C link-dead-code=yes`; compiler emit paths, compiler/controller TMPDIR, controller, base plan, release and retained outputs have separate owned paths. All three supplied patches reproduce the actual complete deltas. The declared controller replacements reproduce the entire controller; every function/class except `main` has identical parsed source structure, and `main` adds only the three alternate-configuration scope records shown by the patch.

The unchanged controller retains one exact child and no retry, exact PID/group/session custody, explicit completion before reap, no active signal after completion/reap, sticky permission refusal, before/after input hashing, bounded retention, cleanup, and the one-way final signal cutoff. Bounds remain 44 seconds work, 49 seconds cleanup, 53.5 seconds posthash/cutoff and 55 seconds wall; 64 generated members/256 MiB; 1 MiB stdout/2 MiB stderr; 80 retained members/267 MiB. Eager collection may exceed these bounds and must fail without enlargement or retry.

Diagnostic policy and provenance are byte-identical to the proven capture. Full matching still requires empty stdout, successful compiler exit, exactly the three source-bound warning objects and their exact summary. Alternate diagnostics have not been observed. An extra, missing or changed diagnostic fails; no warning suppression or policy adaptation is accepted.

The new release schema and unchanged release-validation function bind the exact base plan, controller plan, controller, argv, capture seal and independently sealed review. Root must fill the concrete independent review path/size/hash and capture seal hash and accept the exact four-field `independent_source_review_subject` recorded here. Command/runtime directories and the fresh release path remain absent. The root release is still required and is limited to one raw compiler capture; mapping and actual verifier-input execution remain unreleased.

The existing raw capture completed, but its independent mapping review remains incomplete for Caller, Closure, Dispatch and Body. The saved source assessment establishes no selected source root and an unconditional `WholeQuotePending` refusal, while explicitly leaving the compiler nonidentification cause unproved. Its recorded official compiler documentation/source supports optional eager collection as a diagnostic experiment. All four mappings may still fail. Any later geometry must bind only to this alternate build. No admission, original-build qualification, funded quote, prices, physical capacity, product integration, publication, OTA or GA acceptance follows.

This review used stdlib source/JSON reads, immutable-file hashes and Python AST parsing only. Neither controller was imported or run. No compiler/version/link/test/model/native/UI/capture/geometry-verifier/process probe ran. All newly unrun native checks remain pending under the active pause. Review writes are confined to this new independent directory; no global metadata, frozen packet, source, commit or push was changed. No controller-generated child or cleanup was owed by this review.
"""
    write("findings.md", findings, raw=True)
    result = {"schema": 1, "status": "FROZEN_INDEPENDENT_SOURCE_REVIEW_ACCEPTED_ALT_DIAGNOSTIC_RAW_CAPTURE_ONLY",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "findings": [],
        "independent_source_review_subject": SUBJECT, "argv_sha256": ARGV_SHA,
        "command": [PYTHON, "-B", str(OWN / "review_saved.py")], "cwd": str(ROOT),
        "python_version_label_from_saved_plan_only": plan["python_version_from_this_preparation"], "python_tool": plan["python_tool"],
        "version_query_performed": False, "review_source": row(OWN / "review_saved.py"),
        "source_tree_sha256": plan["source_tree_sha256"], "source_members": 146, "compiler_sysroot_members": 67,
        "capture_packet_members": 18, "input_members_hashed_before_and_after": len(inputs),
        "input_bytes_each_pass": sum(r["bytes"] for r in inputs), "before_after_inputs_equal": True,
        "bounds_unchanged": True, "retained_evidence_bounds_unchanged": True, "diagnostic_policy_and_provenance_byte_identical": True,
        "controller_ast_parses": 2, "unchanged_function_or_class_ast_count": len(old_functions) - 1,
        "complete_diffs_verified": 3, "controller_declared_replacements_verified": 11,
        "compiler_controller_import_execution_version_link_test_model_native_geometry_or_process_probes": 0,
        "frozen_packets_modified": False, "canonical_metadata_commit_push_actions": 0,
        "fresh_root_release_required": True, "execution_authorized_by_this_review": False,
        "semantic_map_approved": False, "actual_verifier_input_run_released": False,
        "alternate_diagnostic_configuration_only": True, "original_capture_qualified": False,
        "runtime_admission_accepted": False, "frontier_complete": False, "complete_capacity_accepted": False,
        "all_four_target_mappings_may_still_fail": True, "original_compiler_nonidentification_cause_proved": False,
        "native_checks": "pending under active pause", "owned_child_started": False, "child_cleanup_owed": False,
        "elapsed_seconds": time.monotonic() - START, "review_wall_ceiling_seconds": 55}
    write("review-result.json", result)
    summary = {"status": result["status"], "findings": 0, "source_members": 146,
        "input_members_hashed_before_and_after": len(inputs), "execution_authorized": False}
    write("review.stdout", json.dumps(summary, sort_keys=True) + "\n", raw=True)
    write("review.stderr", "", raw=True)
    members = [row(p, OWN) for p in sorted(OWN.iterdir()) if p.is_file() and p.name != "seal.json"]
    seal = {"schema": 1, "status": result["status"], "members": members, "member_count": len(members),
        "member_bytes": sum(r["bytes"] for r in members), "tree_sha256": sha(canonical(members)),
        "independent_source_review_subject": SUBJECT, "argv_sha256": ARGV_SHA,
        "source_tree_sha256": plan["source_tree_sha256"], "findings": [], "independent_source_review_accepted": True,
        "fresh_root_release_required": True, "execution_authorized": False, "alternate_diagnostic_configuration_only": True,
        "original_capture_qualified": False, "runtime_admission_accepted": False, "frontier_complete": False,
        "complete_capacity_accepted": False, "semantic_map_approved": False, "actual_verifier_input_run_released": False,
        "compiler_controller_import_execution_version_link_test_model_native_geometry_or_process_probes": 0,
        "canonical_metadata_commit_push_actions": 0}
    write("seal.json", seal)
    print(json.dumps({**summary, "independent_review_seal": row(OWN / "seal.json")}, sort_keys=True))


if __name__ == "__main__":
    main()
