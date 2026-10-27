"""Fresh independent exact-source review; owns this directory only.

No candidate/frozen runner import or execution. Reconstructs the released
compiler preimage, then adds independent observation tests in owned scratch.
"""
from __future__ import annotations
import datetime
import difflib
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREACCESS = HERE.parent / "preaccess"
CANDIDATE = ROOT / "verification/swift-guarded-snapshot-export-admission-correction"
ORIGINAL = ROOT / "verification/swift-guarded-snapshot-export-admission-design"
PREVIOUS = ROOT / "verification/swift-guarded-snapshot-export-admission-independent/actual-review"
ACCEPTED = ROOT / "verification/swift-guarded-snapshot-export-preparation/inputs/accepted-source/vm"
SOURCE_MANIFEST = ACCEPTED.parents[1] / "source-manifest.json"
RELEASE = ROOT / "verification/swift-semantic-adapter-root-review/guarded-snapshot-admission-correction-independent-release.json"
RUSTC = "/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc"
FEATURES = ["experimental-swift-reactor", "experimental-swift-wasi", "experimental-stream-validation", "experimental-function-cache"]
CONTROL = "src/experimental_swift_reactor/control.rs"
INITIAL = "src/experimental_swift_reactor/cache/initial_profile_v1.rs"
ACCEPTED_TREE = "9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb"

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
def content_hash(data): return hashlib.sha256(data).hexdigest()
def inventory(tree):
    return [{"path": str(path.relative_to(tree)), "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in sorted(tree.rglob("*")) if path.is_file()]
def commitment(members):
    return content_hash("".join(f"{m['path']}\0{m['bytes']}\0{m['sha256']}\n" for m in members).encode())

def verify_members(base, manifest):
    seen = set()
    for row in manifest["members"]:
        path = pathlib.PurePosixPath(row["path"])
        assert not path.is_absolute() and ".." not in path.parts
        assert row["path"] not in seen
        seen.add(row["path"])
        member = base / path
        assert not member.is_symlink() and member.stat().st_size == row["bytes"]
        assert sha(member) == row["sha256"], row["path"]
    return {"members_verified": len(seen), "bytes_verified": sum(row["bytes"] for row in manifest["members"])}

def custody():
    assert sha(RELEASE) == "71fc1630a07620cb3e97c5f978f6863e11d281a777d1a77d470b6f998360c1bb"
    rows = []
    for base, expected, count in [
        (CANDIDATE, "3812896d87c86c9fe70446494ca48d57d4a848ea4da885e41b877b47388049f5", 63),
        (PREACCESS, "cb58a2bc71dc997d50547df32e0945c2a451777bc4041e4fd99ccf85fbad0c96", 46),
        (ORIGINAL, "b60d1ba0790076b35b6df30dd8df407486f89144e6914f40d2d0d55e4e20e1f5", 70),
        (PREVIOUS, "4356c1f7b8adde46dca0b661171d9ad935773a3ecfe47ac153581b2fb4a3e896", 35),
    ]:
        assert sha(base / "seal.json") == expected
        manifest = json.loads((base / "seal.json").read_text())
        checked = verify_members(base, manifest)
        assert checked["members_verified"] == count
        rows.append({"path": str(base.relative_to(ROOT)), "seal_sha256": expected, **checked})
    assert sha(SOURCE_MANIFEST) == "f17270c23f09cef85bf1aa5254f94e0355d11678702a876f00ac8520b7d186f3"
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    assert manifest["tree_sha256"] == ACCEPTED_TREE
    rows.append({"path": str(ACCEPTED.relative_to(ROOT)), "tree_sha256": ACCEPTED_TREE,
                 "manifest_sha256": sha(SOURCE_MANIFEST), **verify_members(ACCEPTED, manifest)})
    return {"at": now(), "root_release_sha256": sha(RELEASE), "inputs": rows,
            "active_encoder_read": False, "frozen_runners_or_wrappers_replayed": False}

def replace_once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new, 1)

def admission_probe(accepted):
    start = accepted.index("    pub(super) fn adopt_body(")
    stop = accepted.index("    fn check_budget(", start)
    method = accepted[start:stop]
    substitutions = [
        ("fn adopt_body(", "fn correction_probe_adopt_body_v1("),
        ("        cancellation: Cancellation,\n", "        cancellation: Cancellation,\n        boundary:CorrectionBoundaryV1,\n        storage:CorrectionEarlyStorageV1,\n"),
        (") -> Result<(Self, AdoptedProof), SwiftRunFailure> {", ") -> CorrectionCoreReturnV1 {"),
        ("let construction = foundation_construction_bytes().ok_or_else(|| {", "let construction = foundation_construction_bytes().and_then(|base|base.checked_add(size_of::<CorrectionPreScopePlacesV1>())).ok_or_else(|| {"),
        ("            control.check(cursor)\n        })();", "            // Test-only event at the exact original post-Construction final check.\n            match boundary {\n                CorrectionBoundaryV1::FinalCancel=>control.cancellation.cancel(),\n                CorrectionBoundaryV1::FinalDeadline=>control.deadline=Instant::now(),\n                CorrectionBoundaryV1::None=>{},\n            }\n            control.check(cursor)\n        })();"),
        ("            drop(body);", "            drop(body);\n            let retirement=storage.retire(&mut control);"),
        ("            return Err(failure);", "            return Err(CorrectionPreScopeFailureV1 {primary:failure,retirement});"),
    ]
    for old, new in substitutions:
        method = replace_once(method, old, new)
    generated = "// Derived by exact recorded replacements from accepted original adopt_body.\n#[cfg(test)]\nimpl RuntimeControl {\n" + method + "}\n"
    assert generated.encode() == (CANDIDATE / "prototype/generated_admission_probe.rs").read_bytes()
    return generated, substitutions

def reconstruct(tree):
    shutil.copytree(ACCEPTED, tree)
    accepted_control = (tree / CONTROL).read_text()
    generated, substitutions = admission_probe(accepted_control)
    proof_source = (ACCEPTED / "src/experimental_swift_reactor/control_tests.rs").read_text()
    proof = proof_source[proof_source.index("fn uint("):proof_source.index("fn adopt(budget:")]
    assert content_hash(proof.encode()) == "8e3028e959504791ff493a0c2b5fb7b6d6ccb96e791c79654d30bc24a281913c"
    for relative, appendix, tests in [(CONTROL, "control_append.rs", "control_tests_append.rs"),
                                     (INITIAL, "initial_append.rs", "initial_tests_append.rs")]:
        path = tree / relative
        text = path.read_text() + "\n" + (ORIGINAL / "prototype" / appendix).read_text()
        text += "\n" + (CANDIDATE / "prototype" / appendix).read_text()
        text += "\n" + (CANDIDATE / "prototype" / tests).read_text().replace("/* ACCEPTED_PROOF_BUILDER */", proof)
        path.write_text(text)
    control = tree / CONTROL
    control.write_text(control.read_text() + "\n" + generated)
    initial = tree / INITIAL
    text = initial.read_text()
    begin = text.index("    // Sole guard literal. No prepare/acquisition/callback/reentry follows it.")
    finish = text.index("\n}\nfn write_initial_profile_rows_v1", begin)
    original_guarded = text[begin:finish]
    replacement = "    // Compiler-only ABI adapter. Never executed by this packet.\n    correction_compose_signature_v1(cache,control,wasi,scalars,claims,row_output).primary"
    initial.write_text(text[:begin] + replacement + text[finish:])
    actual = inventory(tree)
    manifest = json.loads((CANDIDATE / "compile-source-manifest.json").read_text())
    assert actual == manifest["members"]
    assert commitment(actual) == json.loads((CANDIDATE / "receipt.json").read_text())["compiler_source_tree_sha256"]
    positive = initial.read_text()
    negative = replace_once(positive, "control:access.shared_control(),wasi,scalars", "control:control,wasi,scalars")
    initial.write_text(negative)
    assert inventory(tree) == json.loads((CANDIDATE / "negative-source-manifest.json").read_text())["members"]
    initial.write_text(positive)
    diffs = []
    for relative in (CONTROL, INITIAL):
        diffs.extend(difflib.unified_diff((ACCEPTED / relative).read_text().splitlines(True),
                                        (tree / relative).read_text().splitlines(True),
                                        fromfile="accepted/" + relative, tofile="candidate/" + relative))
    (HERE / "positive-source.patch").write_text("".join(diffs))
    dump(HERE / "source-reconstruction.json", {
        "accepted_tree_sha256": ACCEPTED_TREE, "candidate_source_members_verified": 144,
        "candidate_source_tree_sha256": commitment(actual), "negative_source_members_verified": 144,
        "changed_accepted_paths": [CONTROL, INITIAL], "untouched_accepted_paths": 142,
        "candidate_generated_probe_byte_exact": True, "proof_builder_sha256": content_hash(proof.encode()),
        "generated_probe_substitutions": [{"old": old, "new": new} for old, new in substitutions],
        "original_guarded_block_sha256": content_hash(original_guarded.encode()),
        "compiler_only_adapter": replacement, "real_guard_literal_count": positive.count("let initial=InitialProfileBorrowV1 {"),
        "manifest_members": actual,
        "unchanged_original_scope": "RuntimeControl fields, original admit/refund/check/finish bodies, budgets and original eight outcome enum remain in unchanged accepted source; wrapper guarded block relocation is the sole edit to original text"})
    return proof

def decode_layout(path, expected_count):
    definition = path.read_text().strip()
    content = definition.split('c"', 1)[1].split('"', 1)[0]
    raw = bytearray()
    index = 0
    while index < len(content):
        if content[index] == "\\":
            raw.append(int(content[index + 1:index + 3], 16)); index += 3
        else:
            raw.append(ord(content[index])); index += 1
    assert len(raw) == expected_count * 8
    return [int.from_bytes(raw[index:index + 8], "little") for index in range(0, len(raw), 8)]

def audit_recorded():
    results = json.loads((CANDIDATE / "results.json").read_text())
    audited = []
    for receipt_path in sorted((CANDIDATE / "commands").glob("*/receipt.json")):
        receipt = json.loads(receipt_path.read_text()); folder = receipt_path.parent
        assert sha(folder / "stdout") == receipt["stdout_sha256"]
        assert sha(folder / "stderr") == receipt["stderr_sha256"]
        errors = []
        if folder.name.startswith("negative-"):
            for line in (folder / "stderr").read_text().splitlines():
                diagnostic = json.loads(line)
                if diagnostic.get("level") == "error" and diagnostic.get("code"):
                    errors.append(diagnostic["code"]["code"])
            assert errors == ["E0502"] and receipt["exit_code"] == 1
        else:
            assert receipt["exit_code"] == 0
        # Only the two named correction groups were executed by the producer;
        # compiling original fixture callsites is not executing those wrappers.
        if folder.name.startswith("run-"):
            assert receipt["argv"][1] in ["correction_early_tests", "correction_reborrow_tests"]
        audited.append({"name": folder.name, "receipt_sha256": sha(receipt_path),
                        "exit_code": receipt["exit_code"], "coded_errors": errors,
                        "stdout_bytes": (folder / "stdout").stat().st_size,
                        "stderr_bytes": (folder / "stderr").stat().st_size})
    decoded = []
    for context in results["configurations"]:
        name = context["configuration"]; row = {"configuration": name, "layouts": {}}
        for symbol, words in [("MIXER_CORRECTION_EARLY_LAYOUT_V1", 24), ("MIXER_CORRECTION_REBORROW_LAYOUT_V1", 18)]:
            path = CANDIDATE / "commands" / ("compile-" + name) / (symbol + ".llvm.txt")
            values = decode_layout(path, words)
            assert values == context["layouts"][symbol]
            row["layouts"][symbol] = values
        decoded.append(row)
    assert len(audited) == 13 and len(decoded) == 4
    dump(HERE / "recorded-evidence-audit.json", {"commands_audited": audited, "decoded_contexts": decoded,
         "compiler_constants_decoded": 8, "all_63_candidate_members_read_and_verified": True,
         "unit_compile_warnings": ["3 private-interface warnings in test-only probe", "2 unchanged accepted-source Copy-drop warnings"],
         "recorded_command_scope": "real control/access probes; compiler-only original ABI adapter and full wrapper unexecuted",
         "layouts_are_partial_named_place_inventories": True})
    return {context["configuration"]: context["layouts"] for context in decoded}

def main():
    assert not (HERE / "seal.json").exists()
    dump(HERE / "input-custody-before.json", custody())
    layouts = audit_recorded()
    commands = []
    def run(name, argv, *, tree=None, expected_code=0, expected_errors=None):
        folder = HERE / "commands" / name; folder.mkdir(parents=True, exist_ok=False)
        started = now(); tick = time.monotonic()
        print("starting " + name, flush=True)
        environment = {key: value for key, value in os.environ.items() if not key.startswith("MIXER_LOADER_")}
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        if tree: environment["CARGO_MANIFEST_DIR"] = str(tree)
        completed = subprocess.run([str(arg) for arg in argv], cwd=ROOT, env=environment,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        (folder / "stdout").write_bytes(completed.stdout); (folder / "stderr").write_bytes(completed.stderr)
        coded = []
        for line in completed.stderr.decode(errors="replace").splitlines():
            try: diagnostic = json.loads(line)
            except json.JSONDecodeError: continue
            if diagnostic.get("level") == "error" and diagnostic.get("code"):
                coded.append(diagnostic["code"]["code"])
        passed = completed.returncode == expected_code and (expected_errors is None or coded == expected_errors)
        receipt = {"schema": 1, "started": started, "finished": now(), "duration_seconds": time.monotonic() - tick,
                   "argv": [str(arg) for arg in argv], "cwd": str(ROOT), "exit_code": completed.returncode,
                   "expected_exit_code": expected_code, "coded_errors": coded, "expected_errors": expected_errors,
                   "expectation_met": passed, "runner_sha256": sha(pathlib.Path(__file__)),
                   "accepted_source_tree_sha256": ACCEPTED_TREE, "root_release_sha256": sha(RELEASE),
                   "stdout_sha256": sha(folder / "stdout"), "stderr_sha256": sha(folder / "stderr"),
                   "source_tree_sha256": commitment(inventory(tree)) if tree else None,
                   "CARGO_MANIFEST_DIR": str(tree) if tree else None,
                   "scope": "fresh targeted independent host/source control only; no wrapper/exporter execution"}
        dump(folder / "receipt.json", receipt)
        commands.append({"name": name, "receipt_sha256": sha(folder / "receipt.json"), "expectation_met": passed})
        print("finished " + name + ": " + str(completed.returncode), flush=True)
        assert passed, name
        return completed.stdout.decode(errors="replace")

    run("python-version", [sys.executable, "--version"])
    run("rustc-version", [RUSTC, "-vV"])
    run("source-revision", ["git", "rev-parse", "HEAD"])
    scratch_name = None
    try:
        with tempfile.TemporaryDirectory(prefix="independent-correction-", dir=HERE) as directory:
            scratch = pathlib.Path(directory); scratch_name = scratch.name
            tree = scratch / "vm"; proof = reconstruct(tree)
            positive_control = (tree / CONTROL).read_text()
            positive_initial = (tree / INITIAL).read_text()
            # An observation-only hook records the actual original primary at
            # the start of its cleanup branch. It does not alter control state.
            generated = (CANDIDATE / "prototype/generated_admission_probe.rs").read_text()
            instrumented = replace_once(generated, "        if let Err(mut failure) = result {",
                "        if let Err(mut failure) = result {\n            *INDEPENDENT_ORIGINAL_PRIMARY_V1.lock().unwrap()=Some(failure);")
            control_text = replace_once(positive_control, generated, instrumented)
            control_text += "\n" + (HERE / "control-tests.rs").read_text().replace("/* ACCEPTED_PROOF_BUILDER */", proof)
            initial_text = positive_initial + "\n" + (HERE / "initial-tests.rs").read_text().replace("/* ACCEPTED_PROOF_BUILDER */", proof)
            (tree / CONTROL).write_text(control_text); (tree / INITIAL).write_text(initial_text)
            dump(HERE / "independent-test-source-manifest.json", {"members": inventory(tree),
                "candidate_preimage_verified_before_adaptation": True,
                "adaptation": "actual primary copy captured immediately before consuming cleanup; two new independent test modules and unchanged accepted proof builder appended",
                "candidate_tests_or_original_wrappers_executed": False})
            measured = []
            for unit in [False, True]:
                for mode, opt in [("debug", "0"), ("optimized", "3")]:
                    name = ("unit-" if unit else "production-") + mode
                    ll = scratch / (name + ".ll"); binary = scratch / name
                    argv = [RUSTC, "--crate-name", "mixer_vm", "--edition=2021", "--target", "aarch64-apple-darwin",
                            "-C", "overflow-checks=yes", "-C", "opt-level=" + opt, "--error-format=json"]
                    argv += ["--test", "--emit", f"link={binary},llvm-ir={ll}"] if unit else ["--crate-type", "lib", "--emit", f"metadata={binary}.rmeta,llvm-ir={ll}"]
                    for feature in FEATURES: argv += ["--cfg", f'feature="{feature}"']
                    argv += [tree / "src/lib.rs"]
                    run("compile-" + name, argv, tree=tree)
                    actual_layouts = {}
                    folder = HERE / "commands" / ("compile-" + name)
                    for symbol, words in [("MIXER_CORRECTION_EARLY_LAYOUT_V1", 24), ("MIXER_CORRECTION_REBORROW_LAYOUT_V1", 18)]:
                        definition = next(line for line in ll.read_text().splitlines() if line.startswith("@" + symbol + " "))
                        retained = folder / (symbol + ".llvm.txt"); retained.write_text(definition + "\n")
                        actual_layouts[symbol] = decode_layout(retained, words)
                    assert actual_layouts == layouts[name]
                    measured.append({"configuration": name, "layouts": actual_layouts, "match_recorded": True})
                    if unit:
                        output = run("run-" + name, [binary, "independent_correction_", "--nocapture", "--test-threads=1"], tree=tree)
                        assert "4 passed; 0 failed;" in output
            dump(HERE / "fresh-layout-comparison.json", {"configurations": measured, "all_eight_constants_match": True,
                "limits": "Named partial inventories match; no sum across overlapping inventories or complete floor is selected"})
            # Restore the exact candidate preimage for the fresh compiler-only
            # negative controls. No independent hook/test adaptation survives.
            (tree / CONTROL).write_text(positive_control)
            (tree / INITIAL).write_text(positive_initial)
            for variant in ["direct-control", "live-view"]:
                if variant == "direct-control":
                    changed = replace_once(positive_initial, "control:access.shared_control(),wasi,scalars", "control:control,wasi,scalars")
                    expected = ["E0502"]
                else:
                    changed = replace_once(positive_initial, "    let primary='guarded: {", "    let leaked_control;\n    let primary='guarded: {")
                    changed = replace_once(changed, "        let control_view=initial.control;", "        let control_view=initial.control;\n        leaked_control=control_view;")
                    changed = replace_once(changed,
                        "    let phase_completion=access.complete(CorrectionPhaseStorageV1 {plan:None,temporary_output:None});",
                        "    let phase_completion=access.complete(CorrectionPhaseStorageV1 {plan:None,temporary_output:None});\n    let _=leaked_control.usage(wasi.map(AccountedWasi::usage));")
                    expected = ["E0505"]
                (tree / INITIAL).write_text(changed)
                (HERE / (variant + "-source.patch")).write_text("".join(difflib.unified_diff(positive_initial.splitlines(True), changed.splitlines(True), fromfile="candidate/" + INITIAL, tofile=variant + "/" + INITIAL)))
                dump(HERE / (variant + "-source-manifest.json"), {"members": inventory(tree), "expected_errors": expected})
                for mode, opt in [("debug", "0"), ("optimized", "3")]:
                    argv = [RUSTC, "--crate-name", "mixer_vm", "--edition=2021", "--target", "aarch64-apple-darwin",
                            "--crate-type", "lib", "--emit", f"metadata={scratch}/{variant}-{mode}.rmeta",
                            "-C", "overflow-checks=yes", "-C", "opt-level=" + opt, "--error-format=json"]
                    for feature in FEATURES: argv += ["--cfg", f'feature="{feature}"']
                    argv += [tree / "src/lib.rs"]
                    run("negative-" + variant + "-" + mode, argv, tree=tree, expected_code=1, expected_errors=expected)
            (tree / INITIAL).write_text(positive_initial)
            assert inventory(tree) == json.loads((CANDIDATE / "compile-source-manifest.json").read_text())["members"]
    finally:
        dump(HERE / "cleanup.json", {"at": now(), "scratch": scratch_name,
             "scratch_removed": scratch_name is not None and not (HERE / scratch_name).exists(),
             "all_subprocesses_completed": True, "native_ui_capture_process_inventory_started": False,
             "unrelated_processes_changed": False})
    dump(HERE / "input-custody-after.json", custody())
    dump(HERE / "execution-receipt.json", {"schema": 1, "at": now(), "commands": commands,
         "candidate_seal_sha256": sha(CANDIDATE / "seal.json"), "root_release_sha256": sha(RELEASE),
         "accepted_source_tree_sha256": ACCEPTED_TREE, "independent_host_methods": 8,
         "independent_host_boundaries": 20, "fresh_positive_compiler_contexts": 4,
         "fresh_negative_compiles": 4, "fresh_constants_matched": 8,
         "candidate_or_canonical_changed": False, "preaccess_immutable": True,
         "frozen_wrapper_or_runner_replay": False, "no_full_writer_or_actual_scope": True,
         "complete_floor_or_grant_selected": False, "ga_gates_verified": 0})
    print("Independent targeted execution complete; write and freeze scoped findings next.", flush=True)

if __name__ == "__main__": main()
