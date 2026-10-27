#!/usr/bin/env python3
"""Focused copied canonical gate replay and immutable v3 ledger composition."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import signal
import sys
import time

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
STATE = REPO / "verification/android-editor-membership-compiled-boundary-qualification/state-qualification"
SOURCE = STATE / "canonical-query-offline-addendum-v1"
SOURCE_SHA = "10665c5e5efb5e93d6534eda17e57d2c7a239cca08a55c5508d87185087aa4b7"
MANIFEST_SHA = "da5e35acf808154a71615db4c161c2a9bb4fa10e6e94e7dc9230a9476c5210c9"
AUTHOR_OUT = STATE / "canonical-query-offline-run1"
AUTHOR_SHA = "47440523b4cd892ef47a4a4b4c2b7d6f2680d58871049c2d6cb5c319f1566d8a"
V3_SHA = "969fb9ce4b3dbe806debb2b5124b6c0d9b176e89b55955b3c0fd72eda78d0c1f"
LEDGER_SHA = "e14e2fbeed50a822584f0c1a6e2418a300712c31df431789548e31ce84f4e85e"
FORBIDDEN = ("execution-closure-v5", "execution_closure_v5", "catalog-inspector", "authority-driver", "rejectedworkerv2", "broadhostedharness")

def need(value, message):
    if not value:
        raise ValueError(message)

def ident(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"bytes": size, "sha256": digest.hexdigest()}

def same(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(same(a[key], b[key]) for key in a)
    if type(a) is list:
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b

def selected(packet, expected):
    need(ident(packet / "seal.json")["sha256"] == expected, "released exact sealed packet")
    seal = json.loads((packet / "seal.json").read_bytes())
    for item in seal["members"]:
        name = item["path"]
        need(not Path(name).is_absolute() and ".." not in Path(name).parts and not any(word in name.lower() for word in FORBIDDEN), "bounded permitted packet member")
        need(ident(packet / name) == {key: item[key] for key in ("bytes", "sha256")}, "exact selected member")
    return seal

def verify():
    seal = selected(SOURCE, SOURCE_SHA)
    selected(AUTHOR_OUT, AUTHOR_SHA)
    need(ident(SOURCE / "input-manifest.json")["sha256"] == MANIFEST_SHA, "exact focused input manifest")
    manifest = json.loads((SOURCE / "input-manifest.json").read_bytes())
    paths = [item["path"] for item in manifest["files"]]
    need(len(paths) == len(set(paths)) == 3256, "exact unique3256 focused input members")
    # Screen every named path before descendant input bytes are read.
    for relative in paths:
        need(not Path(relative).is_absolute() and ".." not in Path(relative).parts and not any(word in relative.lower() for word in FORBIDDEN), "permitted exact named input")
    for item in manifest["files"]:
        path = REPO / item["path"]
        need(not path.is_symlink() and ident(path) == {key: item[key] for key in ("bytes", "sha256")}, "named input hash: " + item["path"])
    need(seal["composition"]["v3_source_seal_sha256"] == V3_SHA and seal["composition"]["v3_ledger_sha256"] == LEDGER_SHA, "explicit frozen-v3 composition")
    return {"source_seal_sha256": SOURCE_SHA, "manifest_sha256": MANIFEST_SHA, "manifest_members": len(paths), "manifest_member_bytes": sum(item["bytes"] for item in manifest["files"]), "author_output_seal_sha256": AUTHOR_SHA}

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded

def main():
    started = time.monotonic()
    signal.alarm(55)
    entry = verify()
    copies = OUT / "canonical-gate-source-copies"
    need(not copies.exists(), "new own source-copy directory")
    copies.mkdir()
    for name in ("canonical_query.py", "test_canonical_query.py"):
        source = SOURCE / "code" / name
        (copies / name).write_bytes(source.read_bytes())
        need(ident(copies / name) == ident(source), "exact focused source copy")
    auditcopies = OUT / "bounded-v3-source-copies/offline-reconciler-v3"
    audit_source = STATE / "offline-reconciler-v3/code/audit_selected_replay_v2.py"
    need(ident(auditcopies / "audit_selected_replay_v2.py") == ident(audit_source), "unchanged previously copied exactv3 utility")
    oldpath, oldargv = sys.path[:], sys.argv[:]
    try:
        sys.path.insert(0, str(auditcopies))
        audit = module("audit_selected_replay_v2", auditcopies / "audit_selected_replay_v2.py")
        audit.S, audit.Q, audit.R = STATE, STATE.parent, REPO
        gate = module("canonical_query", copies / "canonical_query.py")
        gate.RUN, gate.RECOVERY = STATE / "full-candidate-v1/run-33", STATE / "run33-single-state-recovery"
        gate.OUTPUT3 = STATE / "offline-reconciler-run3"
        # Replace only the original-path module loader with the independently
        # hash-verified byte-identical copied module. Predicates remain unchanged.
        gate.load_audit = lambda: audit
        tests = module("independent_focused_canonical_tests", copies / "test_canonical_query.py")
        controls_path = OUT / "canonical10-independent-controls.json"
        need(not controls_path.exists(), "new focused control result")
        sys.argv = [str(copies / "test_canonical_query.py"), str(controls_path)]
        tests.main()
        signal.alarm(55)
        retained = module("independent_canonical_retained40", auditcopies / "test_observation_auditor_v2.py")
        retained_path = OUT / "canonical-retained40-independent-controls.json"
        need(not retained_path.exists(), "new retained40 result")
        sys.argv = [str(auditcopies / "test_observation_auditor_v2.py"), "--run", str(gate.RUN), "--recovery", str(gate.RECOVERY), "--output", str(retained_path)]
        retained.main()
        signal.alarm(55)
        result = gate.run_gate()
        need(result["actual_query_rows"] == 84 and result["selected_event_rows"] == 56 and result["zero_selected_event_rows"] == 28 and result["qualified"] is False, "focused84 actual query counts/scope")
        author_result = json.loads((AUTHOR_OUT / "canonical84-query-join.json").read_bytes())
        need(same(result, author_result), "entire author canonical84 result equals independent focused replay")
        focused = json.loads(controls_path.read_bytes())
        need(same(focused, json.loads((AUTHOR_OUT / "canonical10-controls.json").read_bytes())), "all author10 focused controls equal independent replay")
        retained_result = json.loads(retained_path.read_bytes())
        author_retained = json.loads((AUTHOR_OUT / "retained40-controls.json").read_bytes())
        need(same(retained_result["controls"], author_retained["controls"]), "all author40 retained refusal results equal independent replay")
        (OUT / "canonical84-independent-join.json").write_text(json.dumps(result, indent=2) + "\n")
        ledger_path = gate.OUTPUT3 / "complete-proved-unresolved-ledger.json"
        need(ident(ledger_path)["sha256"] == LEDGER_SHA, "exact completed v3 ledger")
        ledger = json.loads(ledger_path.read_bytes())
        reference = STATE.parent / "semantic-review-candidate-v1"
        original = json.loads((reference / "active-semantic-obligations.json").read_bytes())
        history = json.loads((reference / "historical189-current-bindings.json").read_bytes())
        subjects = {item["id"]: item for item in original["subjects"]}
        need(len(ledger["subjects"]) == len(subjects) == 280 and len({item["original_subject"]["id"] for item in ledger["subjects"]}) == 280, "all280 exact unique subjects")
        for item in ledger["subjects"]:
            subject = subjects[item["original_subject"]["id"]]
            need(same(item["original_subject"], subject) and same(item["original_required_cases_retained"], subject["required_semantic_cases"]), "entire original subject and cases preserved")
            need(item["qualification_status"] == "pending-source-specific-required-case-and-outcome-review", "all original subject qualification still pending")
        original_history = {item["historical_id"]: item for item in history["records"]}
        states = {"clean", "terminal-at-entry", "terminal-before-return", "dirty-at-entry", "dirty-before-return", "ordinary-throw-after-callback", "fatal-throw-after-callback"}
        need(len(ledger["historical189"]) == len(original_history) == 189, "all189 original history identities")
        for item in ledger["historical189"]:
            need(same(item["original_binding"], original_history[item["historical_id"]]), "whole original history binding preserved")
            observations = item["actual_state_observations"]
            need(len(observations) == 7 and {row["state"] for row in observations} == states, "exactseven unique canonical historical states")
            need(item["status"] == "pending-disposition-and-outcome-review", "historical behavior not promoted")
        need(len(ledger["separate_five_V1_positives"]) == 5 and ledger["execution_closure_and_native_OTA_GA_accepted"] is False, "five separateV1 sites and no runtime admission")
        need(all(item["file"] != "boundary-019.rows.jsonl.gz" for item in ledger["files"]), "failed partial gzip not consumed")
        receipt = json.loads((AUTHOR_OUT / "receipt.json").read_bytes())
        need(receipt["closure_entry_verified"] is True and receipt["closure_exit_verified"] is True and receipt["source_seal_sha256"] == SOURCE_SHA and receipt["manifest_sha256"] == MANIFEST_SHA and receipt["all_owned_children_reaped"] is True and receipt["qualified"] is False, "author focused immutable provenance/no qualification")
        need(len(receipt["commands"]) == 2 and all(command["exit"] == 0 and command["timeout"] is False and command["reaped"] is True and command["maximum_seconds"] == 60 for command in receipt["commands"]), "two terminal bounded offline author controls")
        signal.alarm(55)
        exit_result = verify()
        need(entry == exit_result, "entry/exit exact source/data custody")
        report = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "independent-finite-canonical84-v3-composition-and98join-accepted; full-matrix-qualification-pending", "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version, "platform": platform.platform(), "script": ident(Path(__file__)), "closure_entry": entry, "closure_exit": exit_result, "copied_source_hashes": {name: ident(copies / name) for name in ("canonical_query.py", "test_canonical_query.py")}, "adaptation": "Exact copied v3 auditor data roots rebound; exact copied canonical gate data roots rebound and load_audit returns independently hash-verified copied module. No source bytes or predicates changed.", "focused_refusals": len(focused["refusal_controls"]), "retained_refusals": len(retained_result["controls"]), "three_previous_v3_acceptance_witnesses_now_refused": sum(item["v3_row_accepts_coherent_witness"] for item in focused["refusal_controls"]) == 3, "entire_author_canonical84_result_and10_control_result_equal_independent_replay": True, "author40_refusal_results_equal_independent_replay": True, "actual_query_rows": 84, "selected_event_rows": 56, "zero_selected_event_rows": 28, "original280_whole_records_equal": True, "original_required_case_count": sum(len(item["required_semantic_cases"]) for item in subjects.values()), "original189_whole_bindings_equal": True, "exact189by7_state_keys": 1323, "separate_V1_sites": 5, "failed_partial_consumed": False, "ledger_file_count": len(ledger["files"]), "original98_99_authority_receipt": ident(OUT / "original98-99-authority-join.json"), "original98_author_output_review": ident(OUT / "released-stage-output-review.json"), "author_gate_receipt": receipt, "children_started": 0, "Java_executed": False, "full225_file_replay_performed": False, "limits": ["Accepted correction is canonical authority serialization and exact84-row v3 report composition only; zero-selected rows receive no native identity/completion credit.", "Original98/99 is the separately verified receipt/source/log/alias join, not a full execution admission.", "Generic public-result/public-descriptor and native-completion/compiled-callee descriptor joins remain pending.", "All280 original required semantic cases, helper/enclosing/exceptional allocation outcomes, execution closure, canonical integration, native runtime, OTA and GA remain pending beyond separately accepted finite facets.", "Final composed bundle remains unreleased and unread."], "elapsed_seconds": time.monotonic() - started, "qualified": False}
        (OUT / "canonical84-composition-independent-review.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"actual_query_rows": 84, "selected": 56, "zero_selected": 28, "retained_refusals": 40, "focused_refusals": 10, "whole280_subjects_preserved": True, "original_cases": report["original_required_case_count"], "exact189by7": 1323, "scoped_canonical_correction_accepted": True, "qualified": False}))
    finally:
        signal.alarm(0)
        sys.path[:], sys.argv[:] = oldpath, oldargv

if __name__ == "__main__":
    main()
