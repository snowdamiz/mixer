"""Freeze independent correction controls and verify immutable source custody."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(name, value):
    (OWN / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def verify_packet(path, seal, expected, count):
    base = ROOT / path
    raw = (base / seal).read_bytes()
    assert sha(raw) == expected, (path, "seal hash")
    data = json.loads(raw)
    members = data["members"]
    assert len(members) == count
    assert data.get("member_count", count) == count
    assert len({m["path"] for m in members}) == count
    for item in members:
        rel = Path(item["path"])
        assert not rel.is_absolute() and ".." not in rel.parts
        payload = (base / rel).read_bytes()
        assert len(payload) == item["bytes"] and sha(payload) == item["sha256"], item["path"]
    total_bytes = sum(x["bytes"] for x in members)
    assert data.get("member_bytes", total_bytes) == total_bytes
    return {"path": path + "/" + seal, "sha256": expected, "members": count,
            "member_bytes": total_bytes, "all_manifest_members_match": True,
            "declared_tree_digest_sha256": data.get("tree_digest_sha256")}

def main():
    packets = [
        verify_packet("verification/android-editor-generic-descriptor-correction", "seal.json", "312d47de4ccb37a854583b25d7557fab80e5058e56429927d913e43140869d2d", 52),
        verify_packet("verification/android-editor-generic-descriptor-joins", "seal.json", "e8c7263060a98f05142ac1f31eb5b30d05a921fd8feeeb9d23de798cab4b3ad5", 19),
        verify_packet("verification/android-generic-descriptor-join-independent", "preaccess-seal.json", "e04efcdbeedfea4c8effc99d51bbe4ca63b2b4b1be21f22c7076ee0c89e5f236", 22),
        verify_packet("verification/android-generic-descriptor-join-independent/actual-review", "review-seal.json", "1dca5622d6f8602821e44013f4b5f09ba760f18d8660d0d0961c767c9a5cfd85", 21),
    ]
    inputs = []
    for rel, expected in [
        ("verification/android-editor-generic-descriptor-correction/check_descriptor_joins.py", "40e7a4c40b5b11a7147666fb1257f184d8a786ab5dd31804b7dada7d3d62e34e"),
        ("verification/android-generic-descriptor-join-independent/preaccess-controls.json", "6f7564b12d62921d9a514297ab22a386b96895cb780fabab7fb7b2aa8e21b70e"),
        ("verification/android-editor-membership-compiled-boundary-qualification/state-qualification/offline-reconciler-v3/code/classfile.py", "211ad86c8b0ffd9048d322efbb9e93bc3fc6606dcf745788bb36ec6052adfd2d"),
    ]:
        raw = (ROOT / rel).read_bytes()
        assert sha(raw) == expected, rel
        inputs.append({"path": rel, "bytes": len(raw), "sha256": expected})
    controls = []
    def add(id, descriptor, context, expected):
        controls.append({"id": id, "descriptor": descriptor, "context": context, "expected": expected})
    # JVMS17 4.2.1 and 4.2.2 constrain name segments, not Java identifiers.
    for i, name in enumerate(["foo/(Bar", "foo/)Bar", "foo/(B)ar", "foo/ Bar", "foo/B ar", "foo/B\tar", "foo/B\nar", "foo/B\rar", "foo/B\far", "foo/雪", "foo/<T>"]):
        add("class-name-valid-%02d" % i, "()L" + name + ";", "grammar-only", "accept-grammar-only")
    for i, name in enumerate(["", "/foo", "foo/", "foo//Bar", "foo.Bar", "foo/[Bar", "foo;Bar"]):
        add("class-name-invalid-%02d" % i, "()L" + name + ";", "grammar-only", "refuse")
    for id, params, context, expected in [
        ("static255", "I" * 255, "static", "accept"),
        ("static256", "I" * 256, "static", "refuse"),
        ("instance254", "I" * 254, "instance", "accept"),
        ("instance255", "I" * 255, "instance", "refuse"),
        ("wide-static255", "JD" * 63 + "III", "static", "accept"),
        ("wide-static256", "JD" * 64, "static", "refuse"),
        ("wide-instance254", "JD" * 63 + "II", "instance", "accept"),
        ("wide-instance255", "JD" * 63 + "III", "instance", "refuse"),
        ("arrays-static255", "[J" * 255, "static", "accept"),
        ("arrays-instance254", "[[D" * 254, "instance", "accept"),
        ("arrays-instance255", "[D" * 255, "instance", "refuse"),
        ("grammar255", "I" * 255, "grammar-only", "accept-grammar-only"),
        ("grammar256", "I" * 256, "grammar-only", "refuse"),
    ]:
        add(id, "(" + params + ")V", context, expected)
    context_controls = [
        "all-static-and-instance-invoke-opcodes-with-matching-access",
        "invoke-opcode-and-access-contradiction-refused",
        "unknown-opcode-refused",
        "missing-invocation-and-access-context-refused",
        "invalid-context-types-refused",
        "grammar-default-does-not-silently-select-static",
        "all-production-descriptor-calls-carry-observed-context",
        "hook-exception-unresolved-receiver-retains-exception-and-normal-pending",
        "normal-return-unresolved-receiver-remains-unresolved",
    ]
    plan = {"schema": 1, "status": "frozen-before-corrected-source-code-review-and-execution", "descriptor_cases": controls,
            "context_and_receiver_obligations": context_controls,
            "retained_controls": {"original119_definitions_sha256": inputs[1]["sha256"], "unchanged24": "exactly-one-selected-stale-assertion-failure", "copied24": "only-selected-classname-expectation-migration"},
            "one_compact_pass": {"files": 214, "rows": 1611, "completions": 665, "joined": 663, "normal_joined": 227, "hook_joined": 436, "unresolved_known_inner_returns": 2, "missing": 844, "no_selected": 108},
            "preservation": {"whole_subjects": 280, "whole_required_cases": 2705, "whole_history_bindings": 189},
            "excluded": ["Java/native execution", "UI/capture/process inventories", "stopped v5/interpreter-startup", "forbidden hosted harness", "preexisting bytecode cache import or mutation", "producer wrapper reruns", "full Java225 replay", "runtime or OTA/GA qualification"]}
    write("frozen-independent-controls.json", plan)
    source_id = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
    write("preparation-custody.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "command": "python3 -I -B verification/android-generic-descriptor-correction-independent/prepare_review.py", "python": sys.version,
          "platform": platform.platform(), "git_head": source_id, "packets": packets, "exact_inputs": inputs,
          "controls_sha256": sha((OWN / "frozen-independent-controls.json").read_bytes()),
          "scope": "Host Python source/data verification only; no candidate execution, native or process inventory", "cleanup": "No instances or scratch created"})
    print(json.dumps({"verified_packets": len(packets), "descriptor_cases_prepared": len(controls), "context_receiver_obligations": len(context_controls), "status": "prepared"}))

if __name__ == "__main__":
    main()
