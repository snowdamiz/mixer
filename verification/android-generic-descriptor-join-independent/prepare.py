"""Freeze source-derived observations and adversarial test declarations before candidate access.

This does not implement result/descriptor validation and never loads candidate code.
"""
import gzip
import json
import platform
import time
from pathlib import Path
from custody import OWN, RUN33, STATE, read, json_member, digest
from classfile_data import parse, invocation_at


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def write(name, value):
    (OWN / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    started = time.monotonic()
    # Manually transcribed from exact DirectBoundaryStates.java:22 and QueryBoundaryStates.java:7.
    direct = {
        "performContextMenuAction": "(I)Z", "reportFullscreenMode": "(Z)Z", "requestCursorUpdates": "(I)Z",
        "requestCursorUpdatesFiltered": "(II)Z", "beginBatchEdit": "()Z", "endBatchEdit": "()Z",
        "clearMetaKeyStates": "(I)Z", "commitText": "(Ljava/lang/CharSequence;I)Z",
        "commitTextWithAttributes": "(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z",
        "setComposingText": "(Ljava/lang/CharSequence;I)Z",
        "setComposingTextWithAttributes": "(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z",
        "setComposingRegion": "(II)Z", "setComposingRegionWithAttributes": "(IILandroid/view/inputmethod/TextAttribute;)Z",
        "finishComposingText": "()Z", "deleteSurroundingText": "(II)Z", "deleteSurroundingTextInCodePoints": "(II)Z",
        "setSelection": "(II)Z", "performEditorAction": "(I)Z", "setImeConsumesInput": "(Z)Z",
        "commitCompletion": "(Landroid/view/inputmethod/CompletionInfo;)Z",
    }
    query = {"getCursorCapsMode": "(I)I", "getSelectedText": "(I)Ljava/lang/CharSequence;",
             "getTextBeforeCursor": "(II)Ljava/lang/CharSequence;", "getTextAfterCursor": "(II)Ljava/lang/CharSequence;",
             "getExtractedText": "(Landroid/view/inputmethod/ExtractedTextRequest;I)Landroid/view/inputmethod/ExtractedText;",
             "getSurroundingText": "(III)Landroid/view/inputmethod/SurroundingText;", "takeSnapshot": "()Landroid/view/inputmethod/TextSnapshot;"}
    renames = {"commitTextWithAttributes": "commitText", "setComposingTextWithAttributes": "setComposingText",
               "setComposingRegionWithAttributes": "setComposingRegion", "requestCursorUpdatesFiltered": "requestCursorUpdates"}
    interface = parse(read(RUN33 + "classes/android/view/inputmethod/InputConnection.class"))
    assert len(interface["methods"]) == 38
    hierarchy = {}
    for suffix in ["Base", "Api31", "Api33", "Api34"]:
        parsed = parse(read(RUN33 + "classes/dev/mixer/android/NativeEditorConnectionV2$" + suffix + ".class"))
        hierarchy[parsed["name"]] = parsed
    class_map = json_member(RUN33 + "class-map.json")
    assert len(class_map) == 464 and not any(p.startswith("java/") for p in class_map)
    source_obligations = []
    for source in ["DirectBoundaryStates.java", "QueryBoundaryStates.java", "CloseBoundaryStates.java", "OutcomeCapture.java",
                   "NativeOutcomeProbe.java", "CompactEvidence.java", "NativeEditorConnectionV2.java", "BaseInputConnection.java"]:
        raw = read(RUN33 + source)
        lines = raw.decode().splitlines()
        interesting = [(i, line) for i, line in enumerate(lines, 1)
                       if any(token in line for token in ["operation(InputConnection", "hookException(", "actual_enclosing_outcome",
                                                          "enclosing_actual_outcome", "static Object actual(", "selected_actual_native_completions",
                                                          "selected-original-delegated", "selectedOuter=", "public boolean setComposingRegion("])]
        source_obligations.append({"member": RUN33 + source, "sha256": digest(raw), "exact_lines": interesting})
    retained_headers = []
    for name in ["android/text/Editable", "android/text/Spanned", "android/view/inputmethod/ExtractedText",
                 "android/view/inputmethod/SurroundingText", "android/view/inputmethod/TextSnapshot", "android/view/inputmethod/BaseInputConnection"]:
        parsed = parse(read(RUN33 + "classes/" + name + ".class"))
        retained_headers.append({**{k: parsed[k] for k in ["name", "super", "interfaces", "access"]}, "retained": True})
    methods = {(m["name"], m["descriptor"]) for m in interface["methods"]}
    table, summaries, specimens = [], [], {}
    selected_names = {"direct-commitText", "direct-commitTextWithAttributes", "direct-setComposingRegionWithAttributes",
                      "query-getCursorCapsMode", "query-getTextBeforeCursor", "query-getExtractedText",
                      "query-takeSnapshot", "direct-close", "boundary-000"}
    families = [("direct-" + f, f, d, "DirectBoundaryStates.java", 22) for f, d in direct.items()]
    families += [("query-" + f, f, d, "QueryBoundaryStates.java", 7) for f, d in query.items()]
    families += [("direct-close", "closeConnection", "()V", "CloseBoundaryStates.java", 9)]
    for file, family, descriptor, source, line in families:
        public_name = renames.get(family, family)
        assert (public_name, descriptor) in methods
        cls = "dev/mixer/android/NativeEditorConnectionV2$Api34"
        while not any(m["name"] == public_name and m["descriptor"] == descriptor for m in hierarchy[cls]["methods"]):
            cls = hierarchy[cls]["super"]
        table.append({"file": file, "family": family, "method": public_name, "descriptor": descriptor,
                      "declaring_product_class": cls, "dispatch_source": RUN33 + source, "line": line})
        path = RUN33 + file + ".rows.jsonl.gz.compact.jsonl"
        for index, raw in enumerate(read(path).splitlines(), 1):
            row = json.loads(raw)
            completions = row["selected_actual_native_completions"]
            observation = {"file": path, "row": index, "row_bytes_sha256": digest(raw), "state": row["state"],
                           "family": family, "public": row.get("actual_operation_outcome", row.get("actual_enclosing_outcome")),
                           "selected_event_count": len(row["selected_immutable_event_points"]), "completions": []}
            for completion in completions:
                frame = completion["production_frames"][0]
                parsed = parse(read(RUN33 + "classes/" + frame["class"].replace(".", "/") + ".class"))
                invocation = invocation_at(parsed, frame["method"], frame["descriptor"], frame["bci"])
                observation["completions"].append({"descriptor": completion["descriptor"], "completion": completion["completion"],
                                                   "value": completion["value"], "first_frame": frame, "compiled_invocation": invocation,
                                                   "association": completion["native_outcome_association"]})
            summaries.append(observation)
            if file in selected_names and row["state"] in {"current", "successor", "terminal", "ordinary-throw-after-callback", "fatal-throw-after-callback", "clean"}:
                specimens[file + "/" + row["state"]] = {"source": observation, "row": row}
    # Original historical enclosing void is separately observed, with no inferred normal native completion.
    historical_path = RUN33 + "boundary-000.rows.jsonl.gz.compact.jsonl"
    historical = [json.loads(x) for x in read(historical_path).splitlines()]
    for row in historical:
        specimens["boundary-000/" + row["state"]] = {"source": {"file": historical_path, "historical_id": row["historical_id"], "state": row["state"]}, "row": row}
    # Derive exact raw-row identities only for bounded specimen files; do not rerun the 225-file auditor.
    raw_identities = []
    for file in sorted(selected_names):
        member = RUN33 + file + ".rows.jsonl.gz"
        for index, raw in enumerate(gzip.decompress(read(member)).splitlines(), 1):
            row = json.loads(raw)
            key = file + "/" + row["state"]
            if key in specimens:
                raw_identities.append({"specimen": key, "member": member, "row": index, "row_bytes_sha256": digest(raw),
                                       "actual_native_outcome_count": len(row.get("actual_native_outcomes", [])),
                                       "selected_event_indexes": [p["sequence_index"] for p in specimens[key]["row"]["selected_immutable_event_points"]]})
    ledger = json_member("complete-unresolved-ledger.json")
    assert len(ledger["subjects"]) == 280 and sum(len(s["original_case_obligations"]) for s in ledger["subjects"]) == 2705
    assert len(ledger["historical189"]) == 189
    v3 = json_member(STATE + "offline-reconciler-run3/complete-proved-unresolved-ledger.json")
    # Preserve entire original records, not a derived field subset or count-only invariant.
    preservation = {"archive_ledger_sha256": digest(read("complete-unresolved-ledger.json")),
                    "whole_v3_ledger_sha256": digest(read(STATE + "offline-reconciler-run3/complete-proved-unresolved-ledger.json")),
                    "v3_top_level_keys": list(v3), "subject_count": 280, "case_count": 2705,
                    "subject_record_hashes": [{"id": s["subject_id"], "canonical_sha256": digest(canonical(s))} for s in ledger["subjects"]],
                    "historical189_canonical_sha256": digest(canonical(ledger["historical189"])),
                    "historical_binding_count": 189, "historical_state_observation_count": 189 * 7}
    write("public-family-source-map.json", table)
    write("source-obligations.json", source_obligations)
    write("selected-retained-hierarchy.json", retained_headers)
    write("focused351-source-observations.json", summaries)
    write("frozen-specimens.json", specimens)
    write("raw-specimen-identities.json", raw_identities)
    write("whole-record-preservation.json", preservation)
    counts = {"focused_rows": len(summaries), "selected_events": sum(s["selected_event_count"] for s in summaries),
              "recorded_native_completions": sum(len(s["completions"]) for s in summaries),
              "normal_native_returns": sum(c["completion"] == "return" for s in summaries for c in s["completions"]),
              "hook_exception_observations": sum(c["descriptor"] == "hook-exception" for s in summaries for c in s["completions"]),
              "rows_without_native_completion": sum(not s["completions"] for s in summaries)}
    assert counts["focused_rows"] == 351
    write("preparation-run.json", {"schema": 1, "command": ["python3", "verification/android-generic-descriptor-join-independent/prepare.py"],
                                  "python": platform.python_version(), "elapsed_seconds": time.monotonic() - started,
                                  "counts": counts, "candidate_accessed": False,
                                  "archive_execution": False, "native_process_or_inventory_actions": False})
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
