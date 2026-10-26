#!/usr/bin/env python3
from pathlib import Path
import datetime
import hashlib
import json
import platform
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def meta(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    source_map = json.loads((BASE / "canonical-source-map.json").read_text())
    for item in source_map["files"]:
        assert meta(ROOT / item["path"]) == {k: item[k] for k in ("bytes", "sha256")}, item["path"]
    assert meta(ROOT / "verification/android-editor-cleanup-contract/seal.json")["sha256"] == "060347101b96ecb7a5ee180828cf3437d47179fbb82e8c8ba8457a96859023b7"
    commands = []
    for script, label in [("transition_review.py", "transition"),
                          ("extract_control_probe.py", "source-controls"),
                          ("review_packet.py", "review-packet")]:
        argv = [sys.executable, str(BASE / script)]
        result = subprocess.run(argv, capture_output=True, text=True)
        (BASE / f"{label}.stdout.txt").write_text(result.stdout)
        (BASE / f"{label}.stderr.txt").write_text(result.stderr)
        commands.append({"argv": argv, "exit": result.returncode,
                         "stdout": f"{label}.stdout.txt", "stderr": f"{label}.stderr.txt"})
        assert result.returncode == 0, script
    receipt = {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Independent contract acceptance with mandatory addendum for isolated candidate preparation only",
        "decision": "ACCEPT_DESIGN_WITH_REQUIRED_ADDENDUM_NO_IMPLEMENTATION_OR_NATIVE_ACCEPTANCE",
        "producer_seal": "060347101b96ecb7a5ee180828cf3437d47179fbb82e8c8ba8457a96859023b7",
        "producer_source_tree_digest": "f93a01001be4636222d287d299bf2c4eb71d7e09c05959a739587fe80df9ed0c",
        "python": sys.version, "platform": platform.platform(),
        "source_revision": "Exact bounded hashes, no Git command used",
        "canonical_source_map": meta(BASE / "canonical-source-map.json"),
        "required_addendum": meta(BASE / "required-addendum.md"),
        "review": meta(BASE / "review.md"), "commands": commands,
        "verified": {"producer_members": 54, "earlier_frozen_members": 203,
                     "canonical_producer_inputs": 7, "anchors": 24, "actual_fragments": 12,
                     "producer_authored_model_groups": 24, "producer_actual_failure_witnesses": 2,
                     "producer_candidate_Java_host_checks": 20, "producer_schema_negative_checks": 10,
                     "independent_authored_model_groups": 24, "independent_actual_source_control_groups": 3},
        "required_corrections": ["standalone lifecycle counted lease before revoke through super and outermost drain",
                                 "loss denials outlast public hooks; no claimed hidden TextView outer-dispatch lease",
                                 "construction and absent Record/View/Editable bootstrap cannot mint cleanup authority",
                                 "plain native throw retires even without earlier retirement; pre-native refusal is separate",
                                 "failure observed before cleanup; first fatal identity retained; inaccessible creator uncertain",
                                 "finite callback depth and no synchronous owner resumption after final busy clear"],
        "pending": ["root selection of producer plus this addendum", "actual complete-source implementation and hostile descriptor/output/callback controls",
                    "pinned SDK cross-compilation", "native IME/editor/lifecycle/cleanup qualification while runtime paused",
                    "scheduler-rejection guaranteed resumption requires separately selected owner amendment",
                    "API28-35 public support, physical phones, TalkBack/design parity, immutable FieldLog, store/signing/OTA/GA"],
        "cleanup": {"host_compiler_JVM_subprocesses": "all reaped; TemporaryDirectory compiler outputs removed including failures",
                    "native_capture_UI_or_process_inventory": "not used, paused",
                    "other_project_processes_and_data": "not inspected or changed",
                    "canonical_Git_root_metadata": "not changed"},
    }
    (BASE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    members = []
    for path in sorted(BASE.rglob("*")):
        assert not path.is_symlink()
        if path.is_file() and path.name != "seal.json":
            members.append({"path": str(path.relative_to(BASE)), **meta(path)})
    seal = {"schema": 1, "scope": receipt["scope"], "producer_seal": receipt["producer_seal"],
            "required_addendum_sha256": receipt["required_addendum"]["sha256"],
            "members": members, "exclusions": ["seal.json (self)"]}
    (BASE / "seal.json").write_text(json.dumps(seal, indent=2) + "\n")
    print(json.dumps({"members": len(members), "seal": meta(BASE / "seal.json"),
                      "addendum": receipt["required_addendum"], "decision": receipt["decision"]}))


if __name__ == "__main__":
    main()
