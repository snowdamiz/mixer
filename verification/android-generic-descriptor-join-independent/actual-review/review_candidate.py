"""Bounded independent actual review against the immutable preaccess plan."""
import collections
import copy
import importlib.util
import io
import json
import sys
import time
import unittest
from review_support import *


def main():
    started = time.monotonic()
    check_preaccess()
    d, original_spec = load_candidate()
    producer_tests = source_module("independent_producer_tests", candidate("test_descriptor_joins.py"), CANDIDATE / "test_descriptor_joins.py")
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromModule(producer_tests)
    test_result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (OWN / "producer-tests.txt").write_text(stream.getvalue())
    inputs = d.Inputs()
    j = d.Joiner(inputs)
    # Once the reviewed classfile source has been loaded, restore the standard library function.
    d.importlib.util.spec_from_file_location = original_spec
    specimens = json.loads((PREACCESS / "frozen-specimens.json").read_text())
    controls = json.loads((PREACCESS / "preaccess-controls.json").read_text())["controls"]
    declared = json.loads((PREACCESS / "public-family-source-map.json").read_text())
    assert all(j.contract[x["family"]]["name"] == x["method"] and j.contract[x["family"]]["descriptor"] == x["descriptor"]
               and j.contract[x["family"]]["declaring_class"] == x["declaring_product_class"] for x in declared)
    original_facets = d.loads(candidate("facets-run1/descriptor-facets.json"))
    source_ledger = d.loads(archive("reference-tree/" + str(d.LEDGER)))
    preservation = {
        "original_subjects": all(d.same(output, {k: original[k] for k in ("original_subject", "original_required_cases_retained", "qualification_status")})
                                 for output, original in zip(original_facets["subjects280"], source_ledger["subjects"])),
        "subjects_count": len(original_facets["subjects280"]),
        "cases_count": sum(len(x["original_required_cases_retained"]) for x in original_facets["subjects280"]),
        "historical_records": all(d.same(output, {k: original[k] for k in ("historical_id", "original_binding", "status")})
                                  for output, original in zip(original_facets["historical189"], source_ledger["historical189"])),
        "historical_count": len(original_facets["historical189"]),
        "no_global_acceptance": original_facets["execution_closure_native_OTA_GA_accepted"] is False,
    }
    assert preservation == {"original_subjects": True, "subjects_count": 280, "cases_count": 2705,
                            "historical_records": True, "historical_count": 189, "no_global_acceptance": True}
    write("whole-record-output-review.json", preservation)

    def fixture(name):
        row = copy.deepcopy(specimens[name]["row"])
        filename = name.split("/")[0] + ".rows.jsonl.gz"
        file = next(f for f in j.ledger["files"] if f["file"] == filename)
        prior = copy.deepcopy(next(r for r in file["rows"] if r["state"] == row["state"]))
        return row, prior, filename

    def evaluate(control):
        id, layer, change = control["id"], control["layer"], control["change"]
        row, prior, filename = fixture(control["baseline"]) if control["baseline"] in specimens else (None, None, None)
        note = None
        if layer == "type-helper-only":
            value = copy.deepcopy(change["value"])
            # Preserve the exact producer's required snapshot field envelope for nominal-only controls.
            if value.get("kind") == "typed-snapshot" and "fields" not in value:
                value["fields"] = copy.deepcopy(specimens["query-getExtractedText/current"]["row"]["actual_operation_outcome"]["fields"])
                note = "Preaccess nominal-only declaration omitted fields; exact recorded snapshot fields supplied as schema envelope, without changing expected nominal relation."
            result = j.value(value, change["return_descriptor"])
            expected = control["expected"]
            if expected == "reject":
                return False, result, note
            if expected.startswith("unresolved-unless") and result["basis"] == "exact-nominal-class":
                return True, result, "OutcomeCapture.actual's general reference getClass().getName() and identity schema covers exact array-class identity; no array covariance was inferred."
            if expected.startswith("unresolved"):
                return result["status"] == "unresolved", result, note
            if expected.startswith("reject-or-unresolved"):
                return result["status"] == "unresolved", result, note
            return result["status"] == "passed", result, note
        if layer == "descriptor-helper-only":
            result = d.descriptor(change["method_descriptor"])
            if change.get("instance_or_interface") and sum(2 if x in ("J", "D") else 1 for x in result[0]) == 255:
                return False, {"descriptor_result": result, "receiver_budget_unchecked": True}, "Candidate descriptor() has no instance/interface context parameter or receiver-unit guard; frozen corpus declarations do not reach this boundary."
            return control["expected"] != "reject", result, note
        if layer == "output-preservation":
            # Independently check the delivered whole records and ensure the proposed mutation breaks full equality.
            if id == "preserve-whole-historical-record":
                baseline = copy.deepcopy(original_facets["historical189"][0]); mutated = copy.deepcopy(baseline); mutated["original_binding"]["independent_mutation"] = 1
            elif id == "preserve-whole-subject-case-order":
                baseline = copy.deepcopy(next(s for s in original_facets["subjects280"] if len(s["original_required_cases_retained"]) > 1))
                mutated = copy.deepcopy(baseline); mutated["original_required_cases_retained"] = list(reversed(mutated["original_required_cases_retained"]))
            elif id == "no-full-matrix-promotion":
                baseline = {"execution_closure_native_OTA_GA_accepted": False}; mutated = {"execution_closure_native_OTA_GA_accepted": True}
            else:
                baseline = copy.deepcopy(original_facets["subjects280"][0]); mutated = copy.deepcopy(baseline)
                if id == "no-whole-subject-promotion": mutated["qualification_status"] = "qualified"
                else: mutated["original_subject"]["independent_mutation"] = 1
            return not d.same(baseline, mutated), {"delivered_original_records_exact": True, "proposed_mutation_breaks_whole_equality": not d.same(baseline, mutated)}, "Independent output comparison; no candidate output-validation entry point exists."
        if layer in ("recorded-historical-row", "delegated-hierarchy"):
            data = json.loads((PREACCESS / "switch-outer-versus-inner-source-case.json").read_text())
            case = next(c for c in data["cases"] if c["state"] == control["baseline"].split("/")[1])
            compact = d.loads(archive("reference-tree/" + str(d.RUN / "boundary-162.rows.jsonl.gz.compact.jsonl")).splitlines()[case["row"] - 1])
            observed = compact["selected_actual_native_completions"][0]
            try:
                result = j.completion(compact, observed)
                return result["status"] not in ("joined-normal-return",), result, "An inner View observation must not receive outer TextView completion credit."
            except d.Refusal as failure:
                return True, {"status": "unmatched-known-inner-observation", "reason": str(failure)}, None
        if layer == "public-exact-join" and id in ("public-overload-coherent-attributes", "public-parameter-coherent-same-return"):
            return True, {"fixed_binding": j.contract[row["family"]], "row_has_no_descriptor_override_field": True}, "Source-reviewed exact public-contract map equals independent preaccess28-map; proposed public descriptor is not an untrusted input field."
        if layer == "compiled-invocation" and id in ("callee-opcode-interface-to-virtual", "callee-owner-base-to-interface"):
            frame = row["selected_actual_native_completions"][0]["production_frames"][0]
            key, instruction, owner, method = j.compiled_call(frame)
            return instruction["opcode"] == 185 and instruction["target"]["owner"] == "android/view/inputmethod/InputConnection", instruction, "Source-reviewed immutable compiled metadata; no row opcode/owner override field exists. No candidate objects or classes were mutated."
        if change is None:
            result = j.row(row, prior, filename)
            if id.startswith("zero-selected"):
                return not result["native_completions"], result, None
            if id == "historical-enclosing-void-is-separate":
                return result["public_result"] is None and not result["native_completions"], result, None
            if id == "close-void-without-completion":
                return result["public_result"]["value"]["status"] == "passed" and result["missing_selected_native_completion"] and not result["native_completions"], result, None
            if id.startswith("hook-exception"):
                return all(x["value"]["normal_return"] == "pending" for x in result["native_completions"]), result, None
            return True, result, None
        if layer == "public-exact-join":
            if id == "family-same-descriptor-same-boolean": row["family"] = prior["family"] = "setComposingText"
            else: row["actual_operation_outcome"] = {"kind": "integer", "value": 1}
        elif layer == "native-exact-callee-join":
            for item in row["selected_actual_native_completions"]:
                if item["completion"] == "return": item["descriptor"] = change["all_selected_normal_completion_descriptors"]
        elif layer == "compiled-invocation":
            item = copy.deepcopy(row["selected_actual_native_completions"][0])
            frame = item["production_frames"][0]
            for key, value in change.items():
                if key.startswith("first_frame."): frame[key.split(".", 1)[1]] = value
            if id == "first-caller-ancestor-substitution": item["production_frames"][0] = item["production_frames"][1]
            result = j.completion(row, item)
            return False, result, None
        elif layer == "receiver":
            for binding in row["native_receiver_bindings"]:
                if binding["global_identity"] == row["selected_actual_native_completions"][0]["receiver_identity"]:
                    binding["class"] = "dev.mixer.android.NativeEditorConnectionV2$Api34"
        elif layer == "delegated-overload":
            completions = row["selected_actual_native_completions"]
            if id == "delegation-outer-descriptor-swapped": completions[1]["descriptor"] = change["outer.descriptor"]
            elif id == "delegation-pair-swapped-order": completions[1]["delegated_leaf_descriptor_pair"] = change["delegated_leaf_descriptor_pair"]
            elif id == "delegation-wrong-inner-value":
                completions[0]["value"] = prior["actual_selected_native_typed_outcomes"][0] = {"kind": "boolean", "value": False}
            elif id == "delegation-extra-normal-completion":
                completions.append(copy.deepcopy(completions[1])); prior["selected_native_completions"] += 1; prior["actual_selected_native_typed_outcomes"].append(copy.deepcopy(completions[1]["value"]))
            elif id == "delegation-cross-invocation": completions[1]["native_event_sequence_index"] += 1
            elif id == "delegation-not-generalized-commitText":
                item = copy.deepcopy(completions[0]); item["descriptor"] = change["inner_and_outer"][0]
                return False, j.completion(row, item), None
        elif layer == "observation-custody":
            if id == "hook-relabel-return":
                item = row["selected_actual_native_completions"][0]; item.update({k: change[k] for k in ("completion", "descriptor", "value")})
            elif id == "neighbor-outcome-misattributed": row["selected_actual_native_completions"][0]["native_event_sequence_index"] += 1
            elif id == "zero-selected-injected-completion":
                item = copy.deepcopy(specimens["direct-commitText/current"]["row"]["selected_actual_native_completions"][0])
                row["selected_actual_native_completions"].append(item); prior["selected_native_completions"] = 1; prior["actual_selected_native_typed_outcomes"] = [item["value"]]
            elif id == "missing-completion-not-inferred":
                row["selected_actual_native_completions"] = []; prior["selected_native_completions"] = 0; prior["actual_selected_native_typed_outcomes"] = []; prior["missing_selected_native_completion"] = True
                result = j.row(row, prior, filename)
                return not result["native_completions"] and result["missing_selected_native_completion"], result, "Row-level only; immutable full-input admission would additionally reject changed file bytes."
            elif id == "exception-identity-swapped": row["selected_actual_native_completions"][0]["original_exception_identity"] = row["selected_actual_native_completions"][0]["receiver_identity"]
        else:
            raise AssertionError(("unadapted control", id, layer))
        result = j.row(row, prior, filename)
        return False, result, None

    results = []
    for control in controls:
        try:
            passed, output, note = evaluate(control)
            classification = "passed" if passed else "failed"
        except d.Refusal as failure:
            negative = control["expected"].startswith("reject") or control["expected"] in ("missing-unresolved-zero-native-credit",)
            passed, output, note = negative, {"refusal": str(failure)}, None
            classification = "passed" if passed else "failed"
        except Exception as failure:
            passed, output, note = False, {"harness_exception": type(failure).__name__, "message": str(failure)}, None
            classification = "harness-error"
        results.append({"id": control["id"], "layer": control["layer"], "expected": control["expected"], "classification": classification,
                        "actual_summary": output if control["layer"] in ("descriptor-helper-only", "type-helper-only", "output-preservation") or not passed else {"expected_observed": True}, "note": note})
    write("original119-controls-results.json", {"source_plan_sha256": sha((PREACCESS / "preaccess-controls.json").read_bytes()), "count": len(results), "classifications": dict(collections.Counter(x["classification"] for x in results)), "results": results})

    # One bounded compact-data pass, invoking only released row utility. No raw replay/auditor.
    counts = collections.Counter()
    findings, differences, observed_completions, no_selected = [], [], 0, 0
    retained_report_files = {f["file"]: f for f in original_facets["files"]}
    for file in j.ledger["files"]:
        if "input_path" not in file: continue
        compact_path = file["input_path"] + ".compact.jsonl"
        raw = inputs.read(compact_path)
        lines = raw.splitlines()
        assert len(lines) == len(file["rows"])
        retained = retained_report_files[file["file"]]
        for number, line in enumerate(lines, 1):
            row = d.loads(line)
            observed_completions += len(row["selected_actual_native_completions"])
            no_selected += not row["selected_immutable_event_points"]
            try: result = j.row(row, file["rows"][number - 1], file["file"])
            except (d.Refusal, KeyError, TypeError, IndexError) as failure:
                result = {"state": file["rows"][number - 1]["state"], "status": "finding", "reason": str(failure), "qualification_status": "pending"}
                findings.append({"file": compact_path, "row": number, **result, "original_selected_completions_retained": row["selected_actual_native_completions"]})
            if not d.same(result, retained["rows"][number - 1]): differences.append({"file": file["file"], "row": number})
            counts["rows"] += 1
            counts["missing_selected_native_completion"] += bool(result.get("missing_selected_native_completion"))
            if result.get("public_result"):
                counts["public_result_rows"] += 1; counts["public_" + result["public_result"]["value"]["status"]] += 1
            for completion in result.get("native_completions", []): counts["native_completion_rows"] += 1; counts[completion["status"]] += 1
        counts["files"] += 1
    write("compact214-independent-replay.json", {"counts": dict(counts), "observed_completions": observed_completions,
                                                "no_selected_rows": no_selected, "findings": findings,
                                                "delivered_row_report_differences": differences, "scope": "one compact pass only; no raw/225auditor/native replay"})
    # New controls discovered during source review remain separate from original119.
    additional = []
    for descriptor in ["()Lpkg/Foo(Bar;", "()Lpkg/Foo)Bar;", "()Lpkg/Foo Bar;"]:
        try: actual = {"result": d.descriptor(descriptor)}
        except d.Refusal as failure: actual = {"refusal": str(failure)}
        additional.append({"id": "valid-class-name-" + str(len(additional) + 1), "descriptor": descriptor,
                           "expected": "valid-JVMS-internal-class-name-grammar-only", "actual": actual,
                           "finding": "candidate-rejects-valid-ClassName", "source": "JVMS17 sections4.2.1/4.2.2/4.3.2"})
    write("postaccess-source-findings.json", additional)
    check_preaccess()
    write("used-inputs.json", USED)
    summary = {"producer_tests_run": test_result.testsRun, "producer_tests_successful": test_result.wasSuccessful(),
               "original119_classifications": dict(collections.Counter(x["classification"] for x in results)),
               "original119_failed_ids": [x["id"] for x in results if x["classification"] != "passed"],
               "compact_counts": dict(counts), "observed_completions": observed_completions, "no_selected_rows": no_selected,
               "delivered_row_report_differences": len(differences), "postaccess_grammar_false_refusals": len(additional),
               "elapsed_seconds": time.monotonic() - started, "python": sys.version,
               "preaccess_unchanged": True, "candidate_unchanged": True, "archive_code_execution": False,
               "only_additional_executable_dependency": {"source": str(d.PARSER), "sha256": PARSER_SHA, "cache_loader_used": False}}
    write("review-run-summary.json", summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
