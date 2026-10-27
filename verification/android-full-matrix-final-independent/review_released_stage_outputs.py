#!/usr/bin/env python3
"""Review only three root-released sealed historical/stage output packets."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import sys

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
STATE = REPO / "verification/android-editor-membership-compiled-boundary-qualification/state-qualification"
RELEASED = {
    "original98-offline-join-run1": "7c768a22ca814983a585b7bc29c1aa6f5e4c933a0fba7059d335513fcb4bdb41",
    "offline-reconciler-run1": "63e998c7c9c93705d04abbbf24c7389b9d719cccfe941dd990d77ea9d2e363a2",
    "offline-reconciler-run2": "6f050f23645eb4db9d03b639a4ca961401a4da6526b94d968ef01e8a89813024",
}

def need(value, reason):
    if not value:
        raise ValueError(reason)

def ident(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def same(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(same(a[key], b[key]) for key in a)
    if type(a) is list:
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b

def main():
    reports = []
    documents = {}
    for name, expected in RELEASED.items():
        packet = STATE / name
        need(ident(packet / "seal.json")["sha256"] == expected, "root-released output seal")
        seal = json.loads((packet / "seal.json").read_bytes())
        names = [item["path"] for item in seal["members"]]
        need(len(names) == len(set(names)), "unique sealed output roster")
        for member in seal["members"]:
            path = Path(member["path"])
            need(not path.is_absolute() and ".." not in path.parts, "bounded sealed output member")
            need(ident(packet / path) == {key: member[key] for key in ("bytes", "sha256")}, "exact sealed output bytes")
            if path.suffix == ".json":
                documents[(name, str(path))] = json.loads((packet / path).read_bytes())
        reports.append({"packet": str(packet.relative_to(REPO)), "seal_sha256": expected, "member_count": len(names), "member_bytes": sum(item["bytes"] for item in seal["members"]), "status": seal["status"]})
    author_join = documents[("original98-offline-join-run1", "original98-joined.json")]
    own_join = json.loads((OUT / "original98-copied-fresh-join.json").read_bytes())
    need(same(author_join, own_join), "entire author original98 output equals independent copied-code replay")
    author_controls = documents[("original98-offline-join-run1", "fresh-controls.json")]
    own_controls = json.loads((OUT / "original98-copied-retained-controls.json").read_bytes())
    need(same(author_controls, own_controls), "entire author original98 control result equals independent replay")
    original_receipt = documents[("original98-offline-join-run1", "receipt.json")]
    need(original_receipt["closure_entry_verified"] is True and original_receipt["closure_exit_verified"] is True and original_receipt["source_seal_sha256"] == "b0639fa3722986e480fb5e6c9476f306d0ddbadd7f1825aa5140d5e879fd0ab4" and original_receipt["manifest_sha256"] == "62c540b9f8f610918ccd5dbab598bb463875584f72530955241f41ab0bc2e0f4" and original_receipt["Java_reexecuted"] is False and original_receipt["children_started"] == 0 and original_receipt["qualified"] is False, "original output exact immutable provenance and offline scope")
    failed_receipt = documents[("offline-reconciler-run1", "receipt.json")]
    failed_explanation = documents[("offline-reconciler-run1", "failure-explanation.json")]
    need(failed_receipt["status"] == "failed" and failed_receipt["utility_data_closure_entry_verified"] is True and failed_receipt["utility_data_closure_exit_verified"] is True, "failed v1 retains failure and verified custody")
    need((STATE / "offline-reconciler-run1/audit.stderr").stat().st_size == 0, "outer traceback must not be relabeled audit.stderr")
    superseded_receipt = documents[("offline-reconciler-run2", "receipt.json")]
    ledger = documents[("offline-reconciler-run2", "complete-proved-unresolved-ledger.json")]
    need(len(ledger["subjects"]) == 280 and len(ledger["historical189"]) == 189 and ledger["execution_closure_and_native_OTA_GA_accepted"] is False, "superseded diagnostic keeps full inventory and no admission")
    need(all(len(item["actual_state_observations"]) == 7 for item in ledger["historical189"]), "superseded diagnostic historical189 by7 counts only")
    report = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "released-stage-output-custody-and-original98-join-verified; strict-final-output-unreleased", "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version, "platform": platform.platform(), "script": ident(Path(__file__)), "verified_outputs": reports, "entire_author_original98_join_and15_control_result_equal_independent_replay": True, "original98_provenance": original_receipt, "v1_failed_receipt": failed_receipt, "v1_failure_explanation": failed_explanation, "v1_outer_traceback_attribution": "Author explanation identifies outer tool output; retained audit.stderr is empty. No absent outer traceback is invented as a packet log.", "v2_superseded_diagnostic": {"receipt": superseded_receipt, "subjects": 280, "historical_ids": 189, "historical_observation_counts": 1323, "disposition": "superseded diagnostic only; not selected final ledger"}, "qualified": False}
    target = OUT / "released-stage-output-review.json"
    need(not target.exists(), "preserve prior stage output review")
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output_packets_verified": 3, "original98_entire_result_and_controls_equal_fresh_review": True, "failed_v1_preserved": True, "superseded_v2_retained_diagnostic": True, "strict_v3_output_read": False, "qualified": False}))

if __name__ == "__main__":
    main()
