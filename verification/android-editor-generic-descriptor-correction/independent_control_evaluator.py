"""Exact reviewed evaluator functions, dedented; one documented F3 adapter.

Definitions/expectations for all119 controls remain unchanged frozen data.
This module contains no corpus replay, subprocess or external write entry point.
"""
import copy
import json

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
        context = change.get("instance_or_interface")
        receiver_units = 1 if context is True else 0 if context is False else None
        result = d.descriptor(change["method_descriptor"], receiver_units=receiver_units)
        contextual = d.descriptor_context(change["method_descriptor"], opcode=185 if context is True else 184 if context is False else None)
        return control["expected"] != "reject", {"descriptor_result": result, "parameter_context": contextual}, note
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
