#!/usr/bin/env python3
"""Read-only producer custody review and independent host replay.

All generated outputs are confined to this independent directory or reaped
TemporaryDirectory compiler outputs. Never runs a native Android process.
"""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import runpy
import subprocess
import sys
import tempfile
import copy

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / "verification/android-editor-cleanup-contract"
JDK = Path("/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin")
EXPECTED = "060347101b96ecb7a5ee180828cf3437d47179fbb82e8c8ba8457a96859023b7"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_index(base, index_name, expected):
    raw = (base / index_name).read_bytes()
    assert sha(raw) == expected
    index = json.loads(raw)
    members = index.get("members", index.get("files"))
    if isinstance(members, dict):
        members = [dict(path=k, **v) for k, v in members.items()]
    assert len({m["path"] for m in members}) == len(members)
    for member in members:
        path = base / member["path"]
        assert path.is_relative_to(base) and not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == member["bytes"] and sha(data) == member["sha256"], path
    return {"path": str((base / index_name).relative_to(ROOT)), "sha256": expected,
            "members": len(members), "bytes": sum(m["bytes"] for m in members)}


def main():
    custody = [checked_index(PRODUCER, "seal.json", EXPECTED)]
    custody.append(checked_index(ROOT / "verification/android-editor-api-boundary-proposal", "manifest.json",
                                 "4ad1b8edebf913308484c4600282c5d8af0af00efbc67fa4f75962967b4cc08e"))
    custody.append(checked_index(ROOT / "verification/android-inputconnection-authority-audit", "seal.json",
                                 "c7fa78e51d301418479c0d2eab214211ac653800a9c747126e89a0b3b7756e82"))
    collection = json.loads((PRODUCER / "collection.json").read_text())
    assert sha(json.dumps(collection["inputs"], sort_keys=True, separators=(",", ":")).encode()) == collection["source_tree_digest"]
    for name, meta in collection["inputs"].items():
        for path in (ROOT / name, PRODUCER / "inputs" / name):
            raw = path.read_bytes()
            assert sha(raw) == meta["sha256"] and len(raw) == meta["bytes"], path
    anchors = json.loads((PRODUCER / "source-map.json").read_text())["anchors"]
    for item in anchors:
        text = (PRODUCER / item["path"]).read_text()
        begin = text.index(item["begin"])
        end = text.index(item["end"], begin + len(item["begin"]))
        assert sha(text[begin:end].encode()) == item["sha256"]
        assert text[:begin].count("\n") + 1 == item["line_start"]
        assert text[:end].count("\n") == item["line_end"]
    fragments = json.loads((PRODUCER / "source-fragments.json").read_text())
    owner = (ROOT / "native/android/app/src/dev/mixer/android/NativeOwnerV2.java").read_text()
    coordinator = (ROOT / "native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java").read_text()
    owner_names = {"Work", "post", "removeWork", "closePending", "settle"}
    for name, fragment in fragments.items():
        assert sha(fragment["source"].encode()) == fragment["sha256"]
        assert fragment["source"] in (owner if name in owner_names else coordinator), name
    actual = (PRODUCER / "probe-source/actual/DisposalProbe.java").read_text()
    candidate = (PRODUCER / "probe-source/candidate/DisposalProbe.java").read_text()
    normalized = candidate.replace("AMENDED = true", "AMENDED = false").replace(
        "return active || cancellation || fence.rendererReportActive || renderer.editorDisposalBusyV2();",
        "return active || cancellation || fence.rendererReportActive;").replace(
        "if (disposed || busyForOwnerDisposal()) return;", "if (disposed) return;")
    assert normalized == actual, "candidate has more than the specified three textual substitutions"
    for fragment in fragments.values():
        assert fragment["source"] in actual

    commands = []
    def command(argv, label):
        result = subprocess.run(argv, text=True, capture_output=True)
        (BASE / f"{label}.stdout.txt").write_text(result.stdout)
        (BASE / f"{label}.stderr.txt").write_text(result.stderr)
        commands.append({"argv": argv, "exit": result.returncode,
                         "stdout": f"{label}.stdout.txt", "stderr": f"{label}.stderr.txt"})
        assert result.returncode == 0, label
        return result

    command([sys.executable, str(PRODUCER / "scripts/transitions.py")], "producer-transitions")
    command([str(JDK / "java"), "-version"], "independent-java-version")
    command([str(JDK / "javac"), "-version"], "independent-javac-version")
    for variant in ("actual", "candidate"):
        with tempfile.TemporaryDirectory(prefix="mixer-independent-contract-") as classes:
            command([str(JDK / "javac"), "--release", "17", "-Xlint:all", "-Werror", "-d", classes,
                     str(PRODUCER / f"probe-source/{variant}/DisposalProbe.java")], f"producer-{variant}-compile")
            result = command([str(JDK / "java"), "-cp", classes, "DisposalProbe"], f"producer-{variant}-run")
            if variant == "candidate":
                assert "20 disposal/ordinary-admission checks passed" in result.stdout
            else:
                assert "both owner predicate omission and coordinator leave disposal bypass" in result.stdout

    # Execute only the pure producer validator definition, never its mutating main.
    # These are schema consistency controls, not ten implementation mutations.
    validator = runpy.run_path(str(PRODUCER / "scripts/check_packet.py"))["validate"]
    contract = json.loads((PRODUCER / "contract.json").read_text())
    validator(contract)
    negative_mutations = [
        lambda c: c["root_selected_design"].update(creation="newest_nested_wins"),
        lambda c: c["root_selected_design"].update(native_key_transport="delegate"),
        lambda c: c["root_selected_design"].update(editor_action="all_actions"),
        lambda c: c["root_selected_design"].update(getHandler="main_then_delegate"),
        lambda c: c.update(owner_core_changes=True),
        lambda c: c.update(scheduler_rejection="guaranteed_complete"),
        lambda c: c["nontriggers"].remove("temporary_owner_seal"),
        lambda c: c.update(editor_disposal_busy="all_deferred_records"),
        lambda c: c.update(no_native_work_in_successful_commit_to_finish=False),
        lambda c: c.update(proposed_coordinator_amendment="busy_predicate_only"),
    ]
    for mutate in negative_mutations:
        mutant = copy.deepcopy(contract); mutate(mutant)
        try:
            validator(mutant)
        except AssertionError:
            pass
        else:
            raise AssertionError("producer schema negative accepted")
    checked_index(PRODUCER, "seal.json", EXPECTED)
    report = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "python": sys.version, "platform": platform.platform(), "custody": custody,
              "producer_source_tree_digest": collection["source_tree_digest"],
              "canonical_inputs_current": len(collection["inputs"]), "anchors_verified": len(anchors),
              "actual_fragments_verified": len(fragments), "producer_schema_negative_controls_rejected": len(negative_mutations),
              "commands": commands, "scope": "Independent custody, exact-source control replay and finite authored models only",
              "cleanup": "Every host subprocess reaped; both TemporaryDirectory compiler outputs removed; no native/capture/UI/process inventory"}
    (BASE / "producer-review-receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"custody_members": [x["members"] for x in custody], "anchors": len(anchors),
                      "fragments": len(fragments), "producer_model": 24, "actual_witnesses": 2,
                      "candidate_checks": 20, "schema_negatives": len(negative_mutations)}))


if __name__ == "__main__":
    main()
