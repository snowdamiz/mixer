#!/usr/bin/env python3
"""Independent data-only joins inside the exact released input manifest."""
import collections
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKAGE = REPO / "verification/android-editor-membership-compiled-boundary-qualification/state-qualification/offline-reconciler-v1"
MANIFEST_SHA = "deef4efeae2adf4d358036f31e60c8802bba1135128ca1a72622ed1f38bdfd93"
CONTEXT = "1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd"
STATES = ("clean", "terminal-at-entry", "terminal-before-return", "dirty-at-entry", "dirty-before-return", "ordinary-throw-after-callback", "fatal-throw-after-callback")

def need(value, message):
    if not value:
        raise ValueError(message)

def same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(same(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right

def ident(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def main():
    need(ident(PACKAGE / "input-manifest.json")["sha256"] == MANIFEST_SHA, "released manifest identity")
    manifest = json.loads((PACKAGE / "input-manifest.json").read_bytes())
    members = {item["path"]: {key: item[key] for key in ("bytes", "sha256")} for item in manifest["files"]}
    def named(relative):
        need(relative in members, "unreleased input: " + relative)
        path = REPO / relative
        need(same(ident(path), members[relative]), "changed released input: " + relative)
        return path
    def load(relative):
        return json.loads(named(relative).read_bytes())
    parent, recovery = manifest["data_parent"], manifest["recovery"]
    receipt = load(parent + "/receipt.json")
    commands = load(parent + "/commands.json")
    need(same(receipt["commands"], commands), "terminal parent commands equal retained command file")
    bylabel = {item["label"]: item for item in commands}
    need(len(bylabel) == len(commands) == 327, "unique original327 command labels")
    failures = [item for item in commands if item["exit"] != 0 or item["timeout"]]
    need(len(failures) == 1 and failures[0]["label"] == "boundary-019", "only exact retained parent timeout")
    need(receipt["all_commands_passed"] is False and failures[0]["timeout"] is True and failures[0]["reaped"] is True, "failed parent remains failed and child reaped")
    for item in commands:
        for suffix in ("stdout", "stderr"):
            need(same(members[parent + "/" + item["label"] + "." + suffix], item[suffix]), "parent command output hash: " + item["label"])
        need(item["reaped"] is True and type(item["timeout_seconds"]) is int and item["timeout_seconds"] == 60, "bounded terminal command")
    roster = load(parent + "/selected-original-behavior-roster.json")
    cases = roster["cases"]
    need(len(cases) == roster["unique_behavior_invocations"] == 98 and sum(len(case["historical_aliases"]) for case in cases) == roster["historical_passed_aliases"] == 99, "exact local98/99 roster accounting")
    need(len({(case["variant"], case["class"], tuple(case["args"])) for case in cases}) == 98, "98 distinct variant/class/argument invocations")
    freeze = load(parent + "/source-freeze.json")
    need(freeze["product_context_id"] == CONTEXT and len(freeze["sources"]) == 143, "actual143-source context")
    need(len({Path(item["path"]).name for item in freeze["sources"]}) == 143, "source-copy basenames are unambiguous")
    for item in freeze["sources"]:
        local = parent + "/" + Path(item["path"]).name
        need(same(members[local], {key: item[key] for key in ("bytes", "sha256")}), "exact143 source copy: " + local)
    original_rows, missing_authority = [], {}
    for index, case in enumerate(cases):
        label = "original-" + str(index).zfill(3) + "-" + case["case_id"]
        command = bylabel[label]
        need(type(command["exit"]) is int and command["exit"] == 0 and command["timeout"] is False, "original invocation must pass: " + label)
        argv = command["argv"]
        need(argv[2:6] == ["-ea", "-Xmx512m", "-cp", argv[5]], "original JVM flags")
        need(argv[6] == case["class"], "exact original main class")
        actual_args = argv[7:]
        need(len(actual_args) == len(case["args"]), "exact original argument count")
        for expected, actual in zip(case["args"], actual_args):
            need(actual.endswith("/passive-return-probe-v4/descriptor.json") if expected == "<descriptor>" else actual == expected, "exact original argument")
        parts = argv[5].split(":")
        need(len(parts) == (2 if case["variant"] == "frozen-focus" else 1), "exact original classpath variant")
        need(parts[-1].endswith("/classes") and "/run-33/owned-full-state-" in parts[-1], "actual parent classpath")
        if case["variant"] == "frozen-focus":
            need(parts[0].endswith("/frozen-focus-classes"), "frozen focus precedes unchanged parent classes")
        local = parent + ("/frozen-focus/" if case["variant"] == "frozen-focus" else "/") + Path(case["source"]["path"]).name
        need(same(members[local], {key: case["source"][key] for key in ("bytes", "sha256")}), "original source-copy join")
        for alias in case["historical_aliases"]:
            relative = alias["command_roster"]
            missing_authority[relative] = {"path": relative, "bytes": alias["bytes"], "sha256": alias["sha256"]}
        original_rows.append({"case_id": case["case_id"], "variant": case["variant"], "command_label": label, "class": case["class"], "args": actual_args, "source_copy": local, "source_identity": members[local], "historical_alias_count": len(case["historical_aliases"]), "exit": 0, "timed_out": False})
    need({name for name in bylabel if name.startswith("original-")} == {row["command_label"] for row in original_rows}, "no missing/extra original command")
    refbase = "verification/android-editor-membership-compiled-boundary-qualification/semantic-review-candidate-v1"
    context = load(refbase + "/product-context.json")
    classmap = load(parent + "/class-map.json")
    need(len(context["source_map"]) == 16 and len(context["class_map"]) == 209, "reference exact16/209 identities")
    for name, expected in context["source_map"].items():
        need(same(members[parent + "/" + name], expected), "exact selected product source identity")
    for relative, expected in context["class_map"].items():
        need(same(classmap[relative], expected) and same(members[parent + "/classes/" + relative], expected), "exact209 emitted product class")
    recovery_receipt = load(recovery + "/receipt.json")
    need(len(recovery_receipt["commands"]) == 10 and recovery_receipt["failed_parent_promoted"] is False and recovery_receipt["all_commands_passed"] is True, "separate10-command recovery")
    driver = load(recovery + "/driver-class-map.json")
    need(set(driver) == {"dev/mixer/android/LegacyBoundarySingleState.class"} and not set(driver) & set(classmap), "one distinct driver, no original class shadow")
    closure = load(recovery + "/execution-closure.json")
    need(same(closure["parent_class_map"], classmap) and same(closure["additional_driver_class_map"], driver), "unchanged original class closure")
    recovered_rows = []
    for state in STATES:
        relative = recovery + "/boundary-019-" + state + ".rows.jsonl.gz"
        with gzip.open(named(relative), "rt", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream]
        need(len(rows) == 1 and rows[0]["state"] == state and rows[0]["historical_id"] == "NativeRenderer:L352:C63:1", "one exact recovered state")
        need(rows[0]["status"] == "passed-callback-scope-state; outcome-review-required" and rows[0]["validation_failure"] is None and rows[0]["outcome_probe_clean"] is True, "actual selected recovered state")
        recovered_rows.append({"state": state, "input_path": relative, "identity": members[relative], "historical_id": rows[0]["historical_id"], "scope": "actual unchanged-body callback state; helper outcomes remain pending"})
    runtime = load(parent + "/runtime-git-context.json")
    runtime_head = runtime["git_context"][0]["stdout"].strip()
    need(runtime_head == "1734ea490c7c65c0086a6c60dd20c3687131c26b", "actual mid-run checkout context")
    result = {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "local-released-run33-joins-pass; historical-authority-and-final-output-review-pending",
        "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version, "platform": platform.platform(),
        "review_script": ident(Path(__file__)), "source_revision_context": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip(),
        "manifest_sha256": MANIFEST_SHA, "product_context": CONTEXT, "actual_mid_run_git_context": runtime_head,
        "run33_commands": 327, "run33_passed": 326, "run33_failed": failures, "parent_promoted": False,
        "original_invocations": original_rows, "locally_retained_aliases": 99,
        "historical_alias_authority": "pending precise frozen upstream release and independent join",
        "missing_historical_rosters": [entry for relative, entry in missing_authority.items() if relative not in members],
        "selected_review_seal_without_path": roster["selected_review_seal"],
        "product_sources": 16, "emitted_product_classes": 209, "compiled_source_copies": 143,
        "bounded_recovery": recovered_rows, "additional_driver_map": driver,
        "failed_parent_raw_and_compact": {"raw": {"path": parent + "/boundary-019.rows.jsonl.gz", **members[parent + "/boundary-019.rows.jsonl.gz"]}, "compact": {"path": parent + "/boundary-019.rows.jsonl.gz.compact.jsonl", **members[parent + "/boundary-019.rows.jsonl.gz.compact.jsonl"]}, "disposition": "retained failed partial pair; forbidden for selected row credit"},
        "limits": ["Original descriptor argv paths joined; full runtime/input execution admission remains pending.", "All observations are host evidence. Final ledger/raw/public/receiver disposition review is pending.", "No producer/product code executed; no native/UI/capture/process inventory or unreleased output read."],
        "qualified": False,
    }
    target = OUT / "run33-local-joins.json"
    need(not target.exists(), "retain earlier independent join output")
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"original_invocations_joined": len(original_rows), "aliases_locally_retained_authority_pending": 99, "source_copies": 143, "product_sources": 16, "product_classes": 209, "recovery_rows": len(recovered_rows), "parent_remains_failed": True, "qualified": False}))

if __name__ == "__main__":
    main()
