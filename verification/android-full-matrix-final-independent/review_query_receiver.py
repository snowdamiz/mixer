#!/usr/bin/env python3
"""Independent source-specific query target relation; no producer imports."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MANIFEST = REPO / "verification/android-editor-membership-compiled-boundary-qualification/state-qualification/offline-reconciler-v1/input-manifest.json"
MANIFEST_SHA = "deef4efeae2adf4d358036f31e60c8802bba1135128ca1a72622ed1f38bdfd93"
FAMILIES = ("getCursorCapsMode", "getSelectedText", "getTextBeforeCursor", "getTextAfterCursor", "getExtractedText", "getSurroundingText", "takeSnapshot")
PREFIX = "android.view.inputmethod.BaseInputConnection@"

def need(condition, reason):
    if not condition:
        raise ValueError(reason)

def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def query_target(row, filename):
    family = row.get("family")
    need(type(family) is str and family in FAMILIES and filename == "query-" + family + ".rows.jsonl.gz", "exact source-specific query family/file")
    need("historical_id" not in row and "original_attempt_close" not in row, "no cross-schema receiver fallback")
    authority = row.get("original_authority")
    need(type(authority) is dict, "actual original query authority")
    target = authority.get("receiver")
    need(type(target) is str and target.startswith(PREFIX), "query actual original target identity type/class")
    suffix = target[len(PREFIX):]
    need(suffix.isascii() and suffix.isdecimal() and len(suffix) <= 20 and suffix == str(int(suffix)) and int(suffix) > 0, "canonical actual original query receiver identity")
    attempt = authority.get("attempt")
    need(type(attempt) is dict and type(attempt.get("target")) is str and attempt["target"] == target, "original authority receiver equals actual original attempt target")
    if "original_target" in row:
        need(type(row["original_target"]) is str and row["original_target"] == target, "explicit target cannot disagree with original authority")
    bindings = row.get("native_receiver_bindings")
    need(type(bindings) is list, "actual query receiver bindings")
    byrow = {item["row_identity"]: item["global_identity"] for item in bindings}
    points = row.get("selected_event")
    need(type(points) is list and type(row.get("selected_hook_fired")) is bool and len(points) == (1 if row["selected_hook_fired"] else 0), "query exact selected target count")
    for point in points:
        index = point.get("sequence_index")
        need(type(index) is int and 0 <= index < len(row["native_sequence"]), "query actual event index")
        event = row["native_sequence"][index]
        need(byrow.get(event["receiver_identity"]) == target, "selected actual raw receiver equals original query target")
        need(point["authority"]["receiver"] == target, "selected captured actual authority receiver equals original query target")
        need(event["method"] == "BaseInputConnection." + family, "exact selected query leaf")
        need(type(point["frame_set"]) is int and point["frame_set"] == event["frame_set"], "selected query raw frame association")
    return target

def main():
    need(identity(MANIFEST)["sha256"] == MANIFEST_SHA, "released input manifest")
    manifest = json.loads(MANIFEST.read_bytes())
    inputs = {item["path"]: {key: item[key] for key in ("bytes", "sha256")} for item in manifest["files"]}
    parent = manifest["data_parent"]
    def exact(relative):
        need(relative in inputs and identity(REPO / relative) == inputs[relative], "exact released named input")
        return REPO / relative
    sources = []
    for name in ("QueryBoundaryStates.java", "TraceRunner.java", "DirectBoundaryStates.java"):
        path = parent + "/" + name
        exact(path)
        sources.append({"path": path, **inputs[path]})
    observed = []
    first = None
    for family in FAMILIES:
        name = "query-" + family + ".rows.jsonl.gz"
        with gzip.open(exact(parent + "/" + name), "rt", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream]
        need(len(rows) == 12 and len({row["state"] for row in rows}) == 12, "all unchanged twelve query states")
        for number, row in enumerate(rows, 1):
            target = query_target(row, name)
            need("original_target" not in row, "original query schema remains unchanged")
            observed.append({"file": name, "row": number, "family": family, "state": row["state"], "target": target, "selected_events": len(row["selected_event"]), "scope": "actual source-specific original query receiver relation only"})
        if first is None:
            first = (rows[0], name)
    controls = []
    def refusal(name, mutate, filename=None):
        row = copy.deepcopy(first[0])
        mutate(row)
        try:
            query_target(row, filename or first[1])
        except (ValueError, KeyError, TypeError, IndexError) as error:
            controls.append({"name": name, "refused": True, "reason": str(error)})
            return
        raise AssertionError("unrefused query relation control: " + name)
    refusal("missing-original-authority", lambda row: row.pop("original_authority"))
    refusal("missing-original-receiver", lambda row: row["original_authority"].pop("receiver"))
    refusal("null-original-receiver", lambda row: row["original_authority"].__setitem__("receiver", None))
    refusal("boolean-original-receiver", lambda row: row["original_authority"].__setitem__("receiver", True))
    refusal("same-class-foreign-receiver", lambda row: row["original_authority"].__setitem__("receiver", PREFIX + "999999"))
    refusal("original-attempt-target-disagrees", lambda row: row["original_authority"]["attempt"].__setitem__("target", PREFIX + "999999"))
    refusal("selected-authority-receiver-disagrees", lambda row: row["selected_event"][0]["authority"].__setitem__("receiver", PREFIX + "999999"))
    refusal("explicit-original-target-disagrees", lambda row: row.__setitem__("original_target", PREFIX + "999999"))
    refusal("cross-family-no-fallback", lambda row: row.__setitem__("family", "commitText"))
    refusal("direct-file-no-fallback", lambda row: None, "direct-getCursorCapsMode.rows.jsonl.gz")
    refusal("historical-schema-no-fallback", lambda row: row.__setitem__("historical_id", "NativeRenderer:L352:C63:1"))
    report = {"schema": 1, "status": "source-specific-query-original-target-relation-supported; unreleased-v2-not-reviewed", "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version, "script": identity(Path(__file__)), "source_manifest_sha256": MANIFEST_SHA, "selected_source_files": sources, "source_reason": "QueryBoundaryStates binds target=(BaseInputConnection) edit.lastConnection, snapshots TraceRunner.authority(target) before state changes, and selectedHook requires Event.receiver==that same target through DirectBoundaryStates.targetEvent. TraceRunner.authority records id(receiver) and actual current attempt.target. Derive an internal query-only target alias without modifying raw/compact evidence.", "query_rows": observed, "query_row_count": len(observed), "independent_refusal_controls": controls, "limits": ["Only exact query-family/file schemas may derive target from original_authority.receiver; all other schemas keep their explicit source-specific target contract.", "Empty pre-public refusal traces establish no selected native invocation; they still require a typed original authority/attempt target relation.", "This reviews the released source and actual data relation. Active v2 code and outputs remain unread; no author/product code executed; no qualification promotion."], "qualified": False}
    target = OUT / "query-original-target-review.json"
    need(not target.exists(), "preserve existing independent query review")
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"actual_query_rows": len(observed), "selected_query_events": sum(item["selected_events"] for item in observed), "refused_independent_controls": len(controls), "unreleased_v2_accessed": False, "qualified": False}))

if __name__ == "__main__":
    main()
