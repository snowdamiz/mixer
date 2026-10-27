#!/usr/bin/env python3
"""Execute bounded copied offline utilities only; never invoke producer wrappers."""
import copy
import datetime
import gzip
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
PACKETS = {
    "offline-reconciler-v3": "969fb9ce4b3dbe806debb2b5124b6c0d9b176e89b55955b3c0fd72eda78d0c1f",
    "original98-offline-join-addendum-v1": "b0639fa3722986e480fb5e6c9476f306d0ddbadd7f1825aa5140d5e879fd0ab4",
}
FORBIDDEN = ("execution-closure-v5", "execution_closure_v5", "catalog-inspector", "authority-driver", "rejectedworkerv2", "broadhostedharness")

def need(value, reason):
    if not value:
        raise ValueError(reason)

def ident(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for value in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(value)
            size += len(value)
    return {"bytes": size, "sha256": digest.hexdigest()}

def verify():
    reports = []
    for name, expected in PACKETS.items():
        packet = STATE / name
        need(ident(packet / "seal.json")["sha256"] == expected, "root-selected exact packet seal")
        seal = json.loads((packet / "seal.json").read_bytes())
        for item in seal["members"]:
            need(not any(word in item["path"].lower() for word in FORBIDDEN), "forbidden sealed member")
            need(ident(packet / item["path"]) == {key: item[key] for key in ("bytes", "sha256")}, "sealed source/input identity")
        manifest = json.loads((packet / "input-manifest.json").read_bytes())
        paths = [item["path"] for item in manifest["files"]]
        need(len(paths) == len(set(paths)), "unique input roster")
        for relative in paths:
            path = Path(relative)
            need(not path.is_absolute() and ".." not in path.parts and not any(word in relative.lower() for word in FORBIDDEN), "forbidden or unbounded input")
        for item in manifest["files"]:
            path = REPO / item["path"]
            need(not path.is_symlink() and ident(path) == {key: item[key] for key in ("bytes", "sha256")}, "exact named input identity: " + item["path"])
        reports.append({"packet": str(packet.relative_to(REPO)), "seal_sha256": expected, "members": len(seal["members"]), "inputs": len(paths), "input_bytes": sum(item["bytes"] for item in manifest["files"]), "manifest": ident(packet / "input-manifest.json")})
    return reports

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value

def main():
    started = time.monotonic()
    signal.alarm(55)
    reports = verify()
    copies = OUT / "bounded-v3-source-copies"
    need(not copies.exists(), "preserve prior bounded source copies")
    copies.mkdir()
    copied = []
    for packet_name in PACKETS:
        destination = copies / packet_name
        destination.mkdir()
        seal = json.loads((STATE / packet_name / "seal.json").read_bytes())
        for member in seal["members"]:
            if not member["path"].startswith("code/"):
                continue
            source = STATE / packet_name / member["path"]
            target = destination / Path(member["path"]).name
            target.write_bytes(source.read_bytes())
            need(ident(target) == ident(source), "exact independent utility source copy")
            copied.append({"from": str(source.relative_to(REPO)), "to": str(target.relative_to(REPO)), **ident(target)})
    oldargv, oldpath = sys.argv[:], sys.path[:]
    try:
        auditdir = copies / "offline-reconciler-v3"
        sys.path.insert(0, str(auditdir))
        audit = module("audit_selected_replay_v2", auditdir / "audit_selected_replay_v2.py")
        # Exact copied code assumes its producer checkout ancestry; only data-root
        # globals are rebound. No source or source identity is rewritten.
        audit.S, audit.Q, audit.R = STATE, STATE.parent, REPO
        retained = module("independent_copied_auditor_tests", auditdir / "test_observation_auditor_v2.py")
        tests_path = OUT / "v3-copied-retained-controls.json"
        need(not tests_path.exists(), "new retained control output")
        sys.argv = [str(auditdir / "test_observation_auditor_v2.py"), "--run", str(STATE / "full-candidate-v1/run-33"), "--recovery", str(STATE / "run33-single-state-recovery"), "--output", str(tests_path)]
        retained.main()
        signal.alarm(55)
        parent = STATE / "full-candidate-v1/run-33"
        path = parent / "query-getTextBeforeCursor.rows.jsonl.gz"
        with gzip.open(path, "rt", encoding="utf-8") as raw, Path(str(path) + ".compact.jsonl").open() as compact:
            actual = [(json.loads(a), json.loads(b)) for a, b in zip(raw, compact)]
        pre_raw, pre_compact = next(pair for pair in actual if pair[0]["state"] == "terminal")
        need(pre_raw["selected_event"] == [] and pre_raw["selected_hook_fired"] is False, "actual pre-public refusal state")
        extra = []
        for name, value in (("noncanonical-query-receiver", "not-an-object-identity"), ("wrong-class-query-receiver", "java.lang.Object@1"), ("leading-zero-query-receiver", "android.view.inputmethod.BaseInputConnection@01")):
            raw, compact = copy.deepcopy(pre_raw), copy.deepcopy(pre_compact)
            for row in (raw, compact):
                row["original_authority"]["receiver"] = value
                row["original_authority"]["attempt"]["target"] = value
            checker = audit.Audit(parent, STATE / "run33-single-state-recovery")
            try:
                outcome = checker.row(raw, compact, {"file": path.name, "row": 3})
            except (ValueError, KeyError, TypeError, IndexError) as failure:
                extra.append({"name": name, "refused": True, "reason": str(failure)})
            else:
                extra.append({"name": name, "refused": False, "accepted_result": outcome, "scope": "malformed synthetic copy of actual zero-selected-event pre-public refusal row"})
        sys.path[:] = oldpath
        joindir = copies / "original98-offline-join-addendum-v1"
        sys.path.insert(0, str(joindir))
        join = module("join_original98", joindir / "join_original98.py")
        join.REPO, join.RUN, join.RELEASE = REPO, parent, REPO / "verification/android-editor-boundary-root-review/original98-alias-authority-release.json"
        join_tests = module("independent_copied_original98_tests", joindir / "test_join_original98.py")
        controls = join_tests.controls()
        joined = join.validate(join.load_inputs())
        own = json.loads((OUT / "original98-99-authority-join.json").read_bytes())
        own_by_id = {item["case_id"]: item for item in own["joined_cases"]}
        need(joined["unique_actual_commands"] == own["unique_invocations"] == 98 and joined["historical_passed_aliases"] == own["historical_passing_aliases"] == 99, "same original98/99 independent authority result")
        for row in joined["rows"]:
            earlier = own_by_id[row["case_id"]]
            need(row["variant"] == earlier["variant"] and row["class"] == earlier["class"] and row["args"] == earlier["args"], "same exact independently joined original invocation")
            need({(item["command_roster"], item["name"]) for item in row["historical_aliases"]} == {(item["roster"], item["name"]) for item in earlier["actual_passing_aliases"]}, "same original alias set")
        (OUT / "original98-copied-retained-controls.json").write_text(json.dumps(controls, indent=2) + "\n")
        (OUT / "original98-copied-fresh-join.json").write_text(json.dumps(joined, indent=2) + "\n")
        signal.alarm(55)
        exit_reports = verify()
        need(reports == exit_reports, "entry/exit input closure identities equal")
        result = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "bounded-offline-input-review; query-refusal-gap-retained", "command": [sys.executable, "-B", str(Path(__file__).resolve())], "script": ident(Path(__file__)), "python": sys.version, "platform": platform.platform(), "entry_inputs": reports, "exit_inputs": exit_reports, "exact_code_copies": copied, "adaptation": ["Copied v3 auditor globals S/Q/R rebound to exact released data roots.", "Copied original98 module globals REPO/RUN/RELEASE rebound to exact released data roots.", "No source bytes, producer wrappers, corpus assertions or input files changed."], "retained_v3_controls": {"path": str(tests_path.relative_to(REPO)), **ident(tests_path)}, "independent_prepublic_query_controls": extra, "original98_retained_refusals": len(controls["refusal_controls"]), "original98_author_fresh_join_equals_own98_99_case_alias_identities": True, "children_started": 0, "Java_executed": False, "unreleased_outputs_read": False, "limits": ["Generic public-result/compiled-callee descriptor gaps remain pending.", "Query malformed identity acceptance is demonstrated only on synthetic copies; all84 released actual query rows passed the earlier stricter independent source-specific relation.", "No original behavior, execution closure, native, OTA or GA qualification is inferred."], "elapsed_seconds": time.monotonic() - started, "qualified": False}
        (OUT / "v3-and-original98-bounded-review.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"v3_retained_controls": len(json.loads(tests_path.read_bytes())["controls"]), "independent_query_controls_not_refused": sum(not item["refused"] for item in extra), "original98_refusals": len(controls["refusal_controls"]), "author_join_matches_independent98_99": True, "children_started": 0, "qualified": False}))
    finally:
        signal.alarm(0)
        sys.argv[:] = oldargv
        sys.path[:] = oldpath

if __name__ == "__main__":
    main()
