"""Independent bounded source-only controls and one compact-data review pass."""
import ast
import collections
import copy
import datetime
import difflib
import hashlib
import io
import json
from pathlib import Path
import signal
import sys
import textwrap
import time
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
CORRECTED = ROOT / "verification/android-editor-generic-descriptor-correction"
ORIGINAL = ROOT / "verification/android-editor-generic-descriptor-joins"
PREACCESS = ROOT / "verification/android-generic-descriptor-join-independent"
USED = {}
sys.dont_write_bytecode = True

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path, expected=None):
    assert not path.is_symlink()
    raw = path.read_bytes()
    if expected:
        assert sha(raw) == expected, str(path)
    USED[str(path.relative_to(ROOT))] = {"bytes": len(raw), "sha256": sha(raw)}
    return raw

def write(name, value):
    (OWN / name).write_text(json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n")

def source_module(name, raw, path):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module

def load():
    d = source_module("check_descriptor_joins", read(CORRECTED / "check_descriptor_joins.py", "40e7a4c40b5b11a7147666fb1257f184d8a786ab5dd31804b7dada7d3d62e34e"), CORRECTED / "check_descriptor_joins.py")
    inputs = d.Inputs()
    j = d.Joiner(inputs)
    return d, inputs, j

def suite(d, path, label):
    module = source_module("_independent_" + label, read(path), path)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    (OWN / (label + ".txt")).write_text(stream.getvalue())
    out = {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
           "skipped": len(result.skipped), "failure_details": [{"case": str(test), "trace": trace} for test, trace in result.failures],
           "error_details": [{"case": str(test), "trace": trace} for test, trace in result.errors]}
    write(label + ".json", out)
    return out

def check_migration():
    before = read(ORIGINAL / "test_descriptor_joins.py")
    preserved = read(CORRECTED / "original_producer_tests.py")
    after = read(CORRECTED / "test_descriptor_joins.py")
    assert before == preserved
    # Exact selected migration, including its explanatory source comment.
    expected = before.decode().replace(
        "        for text in ['()V', '(ZBCSIJFD)Ljava/lang/Object;', '([[I[Ljava/lang/String;)J', '(' + 'I' * 255 + ')V']:",
        "        # F2 migration: JVMS17 4.2.1/4.2.2 permits '(' in a ClassName segment.\n        # Exact original24 source remains unchanged in original_producer_tests.py.\n        for text in ['()V', '(ZBCSIJFD)Ljava/lang/Object;', '([[I[Ljava/lang/String;)J', '(' + 'I' * 255 + ')V', '()Lfoo/(Bar;']:").replace(
        "'()[' + '[' * 255 + 'I', '()Lfoo/(Bar;']:", "'()[' + '[' * 255 + 'I']:")
    assert after.decode() == expected
    diff = "".join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True), fromfile="original24", tofile="selected-migrated24"))
    (OWN / "verified-test-migration.patch").write_text(diff)
    return {"original24_preserved_exactly": True, "only_selected_expectation_migration": True, "original_sha256": sha(before), "migrated_sha256": sha(after)}

def check_adapter(d, inputs, j, facets):
    original = read(PREACCESS / "actual-review/review_candidate.py", "2200a47fee590e8e34793bcdc7b403226ba33019f4f853f425060d812a8b4280").decode()
    tree = ast.parse(original)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    functions = [n for n in main.body if isinstance(n, ast.FunctionDef) and n.name in ("fixture", "evaluate")]
    assert [n.name for n in functions] == ["fixture", "evaluate"]
    extracted = textwrap.dedent(original[original.index("    def fixture(name):"):original.index("    results = []")])
    adapter = json.loads(read(CORRECTED / "independent-evaluator-adapter.json"))
    assert sha(extracted.encode()) == adapter["original_extracted_fixture_and_evaluate_sha256"]
    old = adapter["only_evaluator_adaptation"]["old"]
    new = adapter["only_evaluator_adaptation"]["new"]
    assert extracted.count(old) == 1
    translated = extracted.replace(old, new)
    # Only the context input and now-obsolete unchecked-context diagnostic may differ.
    required_new = '''        context = change.get("instance_or_interface")
        receiver_units = 1 if context is True else 0 if context is False else None
        result = d.descriptor(change["method_descriptor"], receiver_units=receiver_units)
        contextual = d.descriptor_context(change["method_descriptor"], opcode=185 if context is True else 184 if context is False else None)
        return control["expected"] != "reject", {"descriptor_result": result, "parameter_context": contextual}, note'''
    assert new == required_new
    delivered_ast = ast.parse(read(CORRECTED / "independent_control_evaluator.py"))
    delivered_functions = [n for n in delivered_ast.body if isinstance(n, ast.FunctionDef)]
    assert [n.name for n in delivered_functions] == ["fixture", "evaluate"]
    assert ast.dump(ast.Module(body=delivered_functions, type_ignores=[]), include_attributes=False) == ast.dump(ast.parse(translated), include_attributes=False)
    assert all(isinstance(n, (ast.FunctionDef, ast.Import, ast.Expr)) for n in delivered_ast.body)
    specimens = json.loads(read(PREACCESS / "frozen-specimens.json"))
    def archive(member):
        assert member.startswith("reference-tree/")
        return inputs.read(member[len("reference-tree/"):])
    env = {"copy": copy, "json": json, "d": d, "j": j, "specimens": specimens, "PREACCESS": PREACCESS,
           "original_facets": facets, "archive": archive}
    exec(compile(translated, "<independently-extracted-translated119-evaluator>", "exec"), env)
    raw = read(PREACCESS / "preaccess-controls.json", "6f7564b12d62921d9a514297ab22a386b96895cb780fabab7fb7b2aa8e21b70e")
    controls = json.loads(raw)["controls"]
    assert len(controls) == 119 and len({c["id"] for c in controls}) == 119
    results = []
    for control in controls:
        try:
            passed, actual, note = env["evaluate"](control)
        except d.Refusal as exc:
            passed = control["expected"].startswith("reject") or control["expected"] == "missing-unresolved-zero-native-credit"
            actual, note = {"refusal": str(exc)}, None
        except Exception as exc:
            passed, actual, note = False, {"harness_error": type(exc).__name__, "message": str(exc)}, None
        results.append({"id": control["id"], "expected": control["expected"], "passed": passed, "actual": actual, "note": note})
    write("original119-fresh-results.json", {"control_definitions_sha256": sha(raw), "passed": sum(r["passed"] for r in results), "count": len(results), "results": results})
    assert all(r["passed"] for r in results), [r["id"] for r in results if not r["passed"]]
    return {"definitions_unchanged": True, "only_documented_context_adapter": True, "passed": 119,
            "translated_evaluator_sha256": sha(translated.encode())}

def replace_exact(value, replacements):
    if isinstance(value, dict):
        return {k: replace_exact(v, replacements) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_exact(v, replacements) for v in value]
    return replacements.get(value, value) if isinstance(value, str) else value

def focused(d, inputs, j):
    plan = json.loads(read(OWN / "frozen-independent-controls.json"))
    results = []
    for case in plan["descriptor_cases"]:
        context = case["context"]
        try:
            if context == "grammar-only":
                value = d.descriptor(case["descriptor"])
                state = d.descriptor_context(case["descriptor"])
                assert state["status"] == "unresolved-receiver-context" and state["receiver_units"] is None
            else:
                value = d.descriptor_context(case["descriptor"], access=8 if context == "static" else 1, opcode=184 if context == "static" else 185)
                assert value["status"] == "passed"
            passed = case["expected"] != "refuse"
        except d.Refusal as exc:
            value, passed = {"refusal": str(exc)}, case["expected"] == "refuse"
        results.append({"id": case["id"], "expected": case["expected"], "passed": passed, "actual": value})
    def check(id, fn):
        try:
            value = fn()
            passed = True
        except Exception as exc:
            value, passed = {"error": type(exc).__name__, "message": str(exc)}, False
        results.append({"id": id, "passed": passed, "actual": value})
    def refuse(fn):
        try:
            fn()
        except d.Refusal as exc:
            return {"refusal": str(exc)}
        raise AssertionError("expected refusal")
    for opcode in [182, 183, 184, 185]:
        for access in [0, 1, 8, 9, 1025]:
            static = opcode == 184
            matches = bool(access & 8) == static
            def run(opcode=opcode, access=access, static=static, matches=matches):
                text = "(" + "I" * (255 if static else 254) + ")V"
                if not matches:
                    return refuse(lambda: d.descriptor_context(text, access=access, opcode=opcode))
                actual = d.descriptor_context(text, access=access, opcode=opcode)
                assert actual["status"] == "passed" and actual["receiver_units"] == (0 if static else 1)
                return actual
            check("opcode-access-%s-%s" % (opcode, access), run)
    for kwargs in [{}, {"opcode": 186}, {"opcode": 0}, {"opcode": 999}, {"access": 9, "opcode": 186}, {"access": 1, "opcode": -1}]:
        def unknown(kwargs=kwargs):
            value = d.descriptor_context("(" + "I" * 255 + ")V", **kwargs)
            assert value["status"] == "unresolved-receiver-context" and value["receiver_units"] is None
            return value
        check("unknown-context-" + json.dumps(kwargs, sort_keys=True), unknown)
    for kwargs in [{"access": True}, {"access": False}, {"access": -1}, {"access": "8"}, {"opcode": True}, {"opcode": "184"}]:
        check("bad-context-" + json.dumps(kwargs), lambda kwargs=kwargs: refuse(lambda: d.descriptor_context("()V", **kwargs)))
    for units in [True, False, -1, 2, "1"]:
        check("bad-receiver-units-" + repr(units), lambda units=units: refuse(lambda: d.descriptor("()V", receiver_units=units)))
    # Context is present on every retained declaration and public binding.
    assert all(m["parameter_context"]["status"] == "passed" and m["parameter_context"]["evidence"] == {"access": m["access"]} for m in j.methods.values())
    assert all(c["parameter_context"]["status"] == "passed" and c["parameter_context"]["receiver_units"] == 1 for c in j.contract.values())
    specimens = json.loads(read(PREACCESS / "frozen-specimens.json"))
    base = specimens["direct-commitText/current"]["row"]
    frame = base["selected_actual_native_completions"][0]["production_frames"][0]
    key, _, _, _ = j.compiled_call(frame)
    # These private metadata clones test the join gate, never replace source authority.
    for opcode in [0, 186, 999]:
        private = copy.copy(j)
        private.instructions = j.instructions.copy()
        private.instructions[key] = {**j.instructions[key], "opcode": opcode}
        check("unsupported-invocation-cannot-join-" + str(opcode), lambda private=private: refuse(lambda: private.completion(base, base["selected_actual_native_completions"][0])))
    private = copy.copy(j)
    private.methods = j.methods.copy()
    target = j.instructions[key]["target"]
    owner, method = j.resolve(target["owner"], target["name"], target["descriptor"])
    private.methods[(owner, method["name"], method["descriptor"])] = {**method, "access": method["access"] | 8}
    check("contradictory-static-access-cannot-join", lambda: refuse(lambda: private.completion(base, base["selected_actual_native_completions"][0])))
    file = next(f for f in j.ledger["files"] if f["file"] == "boundary-162.rows.jsonl.gz")
    rows = [d.loads(x) for x in inputs.read(file["input_path"] + ".compact.jsonl").splitlines()]
    receiver_results = []
    for number in [6, 7]:
        original = rows[number - 1]
        comp = original["selected_actual_native_completions"][0]
        binding = next(b for b in original["native_receiver_bindings"] if b["global_identity"] == comp["receiver_identity"])
        changes = {binding["global_identity"]: "independent.UnknownSwitch@custody", binding["row_identity"]: "independent.UnknownSwitch@row-" + str(binding["ordinal"])}
        row = replace_exact(original, changes)
        next(b for b in row["native_receiver_bindings"] if b["global_identity"] == changes[binding["global_identity"]])["class"] = "independent.UnknownSwitch"
        actual = j.row(row, file["rows"][number - 1], file["file"])["native_completions"][0]
        assert actual["receiver"]["status"] == "unresolved" and actual["status"].startswith("unresolved-")
        assert actual["value"]["normal_return"] == "pending"
        assert actual["value"]["actual"] == {"kind": "exception", "class": comp["original_exception_class"], "identity": comp["original_exception_identity"]}
        assert d.same(actual["original_completion"], row["selected_actual_native_completions"][0])
        receiver_results.append({"row": number, "exact_identity_replacements": changes, "actual": actual})
    # Unknown receiver on a normal interface call receives no joined credit.
    normal = copy.deepcopy(base)
    binding = next(b for b in normal["native_receiver_bindings"] if b["global_identity"] == normal["selected_actual_native_completions"][0]["receiver_identity"])
    binding["class"] = "independent.UnknownConnection"
    actual = j.completion(normal, normal["selected_actual_native_completions"][0])
    assert actual["receiver"]["status"] == "unresolved" and not actual["status"].startswith("joined-")
    write("focused-independent-results.json", {"count": len(results), "passed": sum(r["passed"] for r in results), "results": results,
          "F1_coherent_receiver_controls": receiver_results, "normal_unknown_receiver": actual,
          "retained_declarations_context_passed": len(j.methods), "public_bindings_context_passed": len(j.contract),
          "private_metadata_mutations": "Synthetic negative API controls only; immutable source/class bytes unchanged"})
    assert all(r["passed"] for r in results)
    return {"descriptor_and_context_cases": len(results), "passed": len(results), "coherent_hook_receiver_cases": len(receiver_results), "normal_unresolved_receiver_cases": 1,
            "retained_declarations": len(j.methods), "public_bindings": len(j.contract)}

def controls():
    d, inputs, j = load()
    original = read(ORIGINAL / "check_descriptor_joins.py").decode()
    corrected = read(CORRECTED / "check_descriptor_joins.py").decode()
    diff = "".join(difflib.unified_diff(original.splitlines(True), corrected.splitlines(True), fromfile="original19/check_descriptor_joins.py", tofile="correction/check_descriptor_joins.py"))
    assert diff.encode() == read(CORRECTED / "selected-source-diff.patch")
    migration = check_migration()
    original24 = suite(d, ORIGINAL / "test_descriptor_joins.py", "unchanged24")
    assert original24["run"] == 24 and original24["failures"] == 1 and original24["errors"] == 0 and original24["skipped"] == 0
    assert "test_full_descriptor_grammar" in original24["failure_details"][0]["case"] and "()Lfoo/(Bar;" in original24["failure_details"][0]["case"]
    migrated24 = suite(d, CORRECTED / "test_descriptor_joins.py", "migrated24")
    assert migrated24["run"] == 24 and migrated24["failures"] == migrated24["errors"] == migrated24["skipped"] == 0
    facets = json.loads(read(CORRECTED / "facets-run1/descriptor-facets.json"))
    adapter = check_adapter(d, inputs, j, facets)
    independent = focused(d, inputs, j)
    write("controls-inputs.json", {"source_data_reads": USED, "candidate_pinned_reads": inputs.used, "cache_loader_used": False})
    return {"migration": migration, "unchanged24": {k: original24[k] for k in ("run", "failures", "errors", "skipped")}, "migrated24": migrated24, "original119": adapter, "independent": independent}

def compact():
    # This is the sole full214 compact pass. Do not call the producer run wrapper.
    d, inputs, j = load()
    delivered = json.loads(read(CORRECTED / "facets-run1/descriptor-facets.json"))
    old = json.loads(read(ORIGINAL / "facets-run1/descriptor-facets.json"))
    counts = collections.Counter()
    findings, mismatches, input_files = [], [], []
    retained = {f["file"]: f for f in delivered["files"]}
    per_row_digest = hashlib.sha256()
    for file in j.ledger["files"]:
        if "input_path" not in file:
            continue
        name = file["input_path"] + ".compact.jsonl"
        assert inputs.allowed[file["input_path"]] == {k: file[k] for k in ("bytes", "sha256")}
        assert inputs.allowed[name] == file["compact"]
        raw = inputs.read(name)
        lines = raw.splitlines()
        assert len(lines) == len(file["rows"])
        for number, line in enumerate(lines, 1):
            row = d.loads(line)
            prior = file["rows"][number - 1]
            counts["rows"] += 1
            counts["recorded_completions"] += len(row["selected_actual_native_completions"])
            counts["selected_events"] += len(row["selected_immutable_event_points"])
            counts["no_selected"] += not row["selected_immutable_event_points"]
            counts["missing"] += prior["missing_selected_native_completion"]
            try:
                actual = j.row(row, prior, file["file"])
            except (d.Refusal, KeyError, TypeError, IndexError) as exc:
                actual = {"state": prior["state"], "status": "finding", "reason": str(exc), "qualification_status": "pending", "original_selected_native_completions_retained": row["selected_actual_native_completions"]}
                findings.append({"file": name, "row": number, "actual": actual})
            assert actual.get("qualification_status", "").startswith("pending")
            if not d.same(actual, retained[file["file"]]["rows"][number - 1]):
                mismatches.append({"file": name, "row": number})
            for completion_index, completion in enumerate(actual.get("native_completions", [])):
                counts["joined_completions"] += 1
                counts[completion["status"]] += 1
                assert completion["status"].startswith("joined-")
                assert all(x["status"] == "passed" for x in completion["parameter_contexts"].values())
                assert d.same(completion["original_completion"], row["selected_actual_native_completions"][completion_index])
            canonical = json.dumps(actual, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
            per_row_digest.update(hashlib.sha256(canonical).digest())
        counts["files"] += 1
        input_files.append({"path": name, **d.identity(raw), "rows": len(lines)})
    expected = {"files": 214, "rows": 1611, "recorded_completions": 665, "joined_completions": 663, "selected_events": 1503,
                "no_selected": 108, "missing": 844, "joined-normal-return": 227,
                "joined-observed-hook-exception; normal-body-return-pending": 436}
    assert dict(counts) == expected, dict(counts)
    assert [(Path(f["file"]).name, f["row"]) for f in findings] == [("boundary-162.rows.jsonl.gz.compact.jsonl", 3), ("boundary-162.rows.jsonl.gz.compact.jsonl", 5)]
    assert not mismatches
    subjects = [{k: s[k] for k in ("original_subject", "original_required_cases_retained", "qualification_status")} for s in j.ledger["subjects"]]
    history = [{k: h[k] for k in ("historical_id", "original_binding", "status")} for h in j.ledger["historical189"]]
    assert len(subjects) == 280 and sum(len(s["original_required_cases_retained"]) for s in subjects) == 2705 and len(history) == 189
    assert d.same(subjects, delivered["subjects280"]) and d.same(subjects, old["subjects280"])
    assert d.same(history, delivered["historical189"]) and d.same(history, old["historical189"])
    assert delivered["execution_closure_native_OTA_GA_accepted"] is False and old["execution_closure_native_OTA_GA_accepted"] is False
    summary = {"counts": dict(counts), "known_findings": findings, "delivered_row_differences": mismatches,
               "fresh_result_row_digest_sha256": per_row_digest.hexdigest(),
               "whole_record_preservation": {"subjects": 280, "required_cases": 2705, "history_bindings": 189, "equal_to_corrected_and_original_reports": True},
               "scope": "Exactly one full214 compact-data pass; accepted raw/compact custody is a premise, raw225 replay not executed; no native or OTA/GA qualification"}
    write("compact214-fresh-results.json", summary)
    write("compact214-inputs.json", {"compact_files": input_files, "source_data_reads": USED, "candidate_pinned_reads": inputs.used, "cache_loader_used": False})
    return summary

def main():
    signal.alarm(50)
    started = time.monotonic()
    assert len(sys.argv) == 2 and sys.argv[1] in ("controls", "compact")
    mode = sys.argv[1]
    receipt = {"command": "python3 -I -B verification/android-generic-descriptor-correction-independent/run_review.py " + mode,
               "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "python": sys.version, "source_sha256": sha(Path(__file__).read_bytes()),
               "git_head": json.loads((OWN / "preparation-custody.json").read_bytes())["git_head"], "timeout_seconds": 50,
               "no_subprocesses_spawned": True, "cache_loader_used": False, "scratch": "In-memory only", "cleanup": "No instances, process inventories, scratch files, or bytecode caches created"}
    try:
        result = controls() if mode == "controls" else compact()
        receipt.update({"status": "passed-with-explicit-retained-limitations", "elapsed_seconds": time.monotonic() - started})
        write(mode + "-command-receipt.json", receipt)
        print(json.dumps({"mode": mode, "status": receipt["status"], "elapsed_seconds": receipt["elapsed_seconds"], "summary": result if mode == "controls" else {"counts": result["counts"], "known_findings": len(result["known_findings"]), "delivered_row_differences": len(result["delivered_row_differences"])}}))
    except BaseException as exc:
        receipt.update({"status": "failed-retained", "elapsed_seconds": time.monotonic() - started, "error": type(exc).__name__, "message": str(exc)})
        write(mode + "-command-receipt-failure.json", receipt)
        raise
    finally:
        signal.alarm(0)

if __name__ == "__main__":
    main()
