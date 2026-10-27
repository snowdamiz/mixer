#!/usr/bin/env python3
"""Join the exact four newly released historical authority data files only."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import sys

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RELEASE = "verification/android-editor-boundary-root-review/original98-alias-authority-release.json"
RELEASE_SHA = "310c58cdd9af4ee9f9a326bce6a6f6b88d66c0de44fa65439d0fd437619e7055"
PARENT = "verification/android-editor-membership-compiled-boundary-qualification/state-qualification/full-candidate-v1/run-33"
ROSTER_SHA = "a268e4b3843ad75a6517022e925b6dcb9db5f4ecf04043cb7c00e7abb19bc477"

def need(value, message):
    if not value:
        raise ValueError(message)

def ident(path):
    value = path.read_bytes()
    return {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}

def main():
    need(ident(REPO / RELEASE)["sha256"] == RELEASE_SHA, "exact root authority release")
    release = json.loads((REPO / RELEASE).read_bytes())
    need(len(release["members"]) == 4, "exact four released authority files")
    documents = {}
    for item in release["members"]:
        path = REPO / item["path"]
        need(ident(path) == {key: item[key] for key in ("bytes", "sha256")}, "exact released historical member")
        documents[item["path"]] = json.loads(path.read_bytes())
    seal_path = release["members"][0]["path"]
    seal = documents[seal_path]
    seal_members = {item["path"]: {key: item[key] for key in ("bytes", "sha256")} for item in seal["members"]}
    need(ident(REPO / (PARENT + "/selected-original-behavior-roster.json"))["sha256"] == ROSTER_SHA, "immutable local98 roster")
    roster = json.loads((REPO / (PARENT + "/selected-original-behavior-roster.json")).read_bytes())
    need(ident(REPO / seal_path) == roster["selected_review_seal"], "local roster's exact historical authority seal")
    expected_passed = {}
    failed = []
    for relative, commands in documents.items():
        if relative == seal_path:
            continue
        seal_relative = str(Path(relative).relative_to(Path(seal_path).parent))
        need(ident(REPO / relative) == seal_members[seal_relative], "historical roster is an exact accepted-seal member")
        for command in commands:
            if Path(command["argv"][0]).name != "java" or command["argv"][1:] == ["-version"]:
                continue
            if command["exit"] != 0 or command["timed_out"]:
                failed.append({"roster": relative, "command": command})
                continue
            key = (relative, command["name"])
            need(key not in expected_passed and command["reaped"] is True, "unique terminal historical JVM command")
            expected_passed[key] = command
    seen, joined = set(), []
    for case in roster["cases"]:
        source_identity = {key: case["source"][key] for key in ("bytes", "sha256")}
        source_members = [relative for relative, value in seal_members.items() if value == source_identity and relative.endswith("/" + Path(case["source"]["path"]).name)]
        need(source_members, "exact original control source exists in selected historical seal: " + case["case_id"])
        aliases = []
        for alias in case["historical_aliases"]:
            relative = alias["command_roster"]
            need(relative in documents and ident(REPO / relative) == {key: alias[key] for key in ("bytes", "sha256")}, "exact alias roster identity")
            key = (relative, alias["name"])
            need(key in expected_passed and key not in seen, "alias joins exactly one actual passing historical JVM invocation")
            command = expected_passed[key]
            main_index = command["argv"].index("-cp") + 2
            need(command["argv"][main_index] == case["class"], "historical original main class")
            args = command["argv"][main_index + 1:]
            need(len(args) == len(case["args"]), "historical original argument count")
            for expected, actual in zip(case["args"], args):
                need(actual.endswith("/descriptor.json") if expected == "<descriptor>" else actual == expected, "historical original argument literal")
            seen.add(key)
            aliases.append({"roster": relative, "name": alias["name"], "exit": command["exit"], "timed_out": command["timed_out"]})
        joined.append({"case_id": case["case_id"], "variant": case["variant"], "class": case["class"], "args": case["args"], "source_identity": source_identity, "historical_source_seal_members": source_members, "actual_passing_aliases": aliases})
    need(len(joined) == 98 and len(seen) == len(expected_passed) == 99 and seen == set(expected_passed), "all and only original99 passing aliases map to original98 unique invocations")
    need(len(failed) == len(roster["historical_failed_excluded"]) == 1, "one retained superseded failed historical JVM invocation")
    excluded = roster["historical_failed_excluded"][0]
    need(failed[0]["command"]["name"] == excluded["command"] and failed[0]["command"]["exit"] == 1, "original historical failure remains excluded")
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "complete98-invocation99-alias-authority-data-join-passed", "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version, "platform": platform.platform(), "script": ident(Path(__file__)), "root_release_sha256": RELEASE_SHA, "local_roster_sha256": ROSTER_SHA, "historical_review_seal": {"path": seal_path, **ident(REPO / seal_path)}, "unique_invocations": 98, "historical_passing_aliases": 99, "joined_cases": joined, "excluded_original_failure": failed, "upstream_seal_members_not_opened": True, "original_code_executed": False, "limits": ["Exact historical source membership and Java argv identities are joined; the earlier review is not rerun.", "Run33 local command/output/source-copy joins are separate in run33-local-joins.json.", "Descriptor path placeholders are matched as descriptor argv paths; full input/runtime execution admission remains pending."], "qualified": False}
    path = OUT / "original98-99-authority-join.json"
    need(not path.exists(), "preserve earlier authority receipt")
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"unique_invocations": 98, "all_actual_passing_aliases": len(seen), "historical_failed_excluded": len(failed), "source_membership_joined": 98, "qualified": False}))

if __name__ == "__main__":
    main()
