#!/usr/bin/env python3
"""Independent byte/source-scope audit only; no producer/tool/runtime replay."""
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PREACCESS = OUT.parent
LANE = REPO / "verification/console-key-owner-fixture-cleanup-ci-correction"
PACKET = LANE / "prepared-1"
ACCEPTED = REPO / "verification/console-key-owner-lifecycle-implementation/prepared-3"


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            assert time.monotonic() - START < 55
            chunk = stream.read(262144)
            if not chunk:
                return value.hexdigest()
            value.update(chunk)


def pairs(values):
    result = {}
    for key, value in values:
        assert key not in result
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def verify(items, root=None):
    seen = set()
    for item in items:
        relative = item["path"]
        assert relative not in seen
        seen.add(relative)
        if root:
            parsed = PurePosixPath(relative)
            assert str(parsed) == relative and not parsed.is_absolute() and ".." not in parsed.parts
        path = root / relative if root else Path(relative)
        assert path.is_file() and path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    return seen


def tree(items):
    return hashlib.sha256("".join(v["path"] + "\0" + str(v["bytes"]) + "\0" + v["sha256"] + "\n" for v in items).encode()).hexdigest()


def main():
    assert sha(PREACCESS / "preaccess-seal.json") == "aa319fb7181e5fafb75c0433e593d557d059757b6c51452f6b3a7ca82945ffd5"
    verify(read(PREACCESS / "preaccess-seal.json")["files"], PREACCESS)
    assert sha(PACKET / "freeze.json") == "34ab3c96238e0e8100331d42109d834d313b39bec9b86582e7ffd78080f97019"
    assert sha(PACKET / "execution-plan.json") == "a5f9d6393385ab28ba3579ba4f0fd6e3a900099cc341ed8c53263b467940abcf"
    seal = read(PACKET / "freeze.json")
    plan = read(PACKET / "execution-plan.json")
    members = verify(seal["files"], PACKET)
    actual = set()
    for path in PACKET.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and path.relative_to(PACKET).as_posix() != "freeze.json":
            actual.add(path.relative_to(PACKET).as_posix())
    assert len(members) == 221 and members == actual and tree(seal["files"]) == seal["tree_sha256"]
    assert len(verify(plan["prepared_files"], PACKET)) == 220
    assert {v["path"] for v in plan["prepared_files"]} | {"execution-plan.json"} == members
    assert len(verify(plan["canonical_inputs"], REPO)) == 25
    assert tree(plan["canonical_inputs"]) == plan["source_tree_sha256"]
    assert len(verify(plan["tools"])) == 980
    accepted_plan = read(ACCEPTED / "execution-plan.json")
    assert plan["source_roster"] == accepted_plan["source_roster"] and len(plan["source_roster"]) == 18
    assert plan["dependencies"] == accepted_plan["dependencies"]
    for relative in plan["source_roster"]:
        assert (PACKET / "inputs" / relative).read_bytes() == (ACCEPTED / "inputs" / relative).read_bytes()
        assert relative not in {v["path"] for v in plan["canonical_inputs"]}
    for relative in plan["test_support"] + [plan["test_source"]]:
        assert (PACKET / "inputs" / relative).read_bytes() == (REPO / relative).read_bytes()
    assert len(plan["test_support"]) == 3
    before = PACKET / "beforeimages" / plan["test_source"]
    after = PACKET / "inputs" / plan["test_source"]
    assert sha(before) == "b31c249da0fc37743afe328e0232a0c347e8489094fbaaf50b9c813b9e368e33"
    assert before.read_bytes() == (PREACCESS / "inputs/key_owner_test.before.exs").read_bytes()
    diff = "".join(difflib.unified_diff(before.read_text().splitlines(True), after.read_text().splitlines(True), fromfile="before/" + plan["test_source"], tofile="after/" + plan["test_source"]))
    assert diff == (PACKET / "canonical-change.diff").read_text()
    names = [line.strip().split('"')[1] for line in after.read_text().splitlines() if line.startswith('  test "')]
    expected_names = read(PREACCESS / "source-evidence-bindings.json")["selected_existing_test_names"]
    assert len(names) == 29 and plan["selection"]["tests"] == expected_names
    assert len(set(expected_names)) == 7 and all(name in names for name in expected_names)
    schemas = read(PACKET / "required-artifact-schemas.json")
    assert schemas["required_artifacts"] == 8 and len(schemas["schemas"]) == 4 and len(schemas["openssl_commands"]) == 4
    assert [name for name in plan["phases"][0]["required_artifacts"] if name.startswith('openssl-')] == ['openssl-%02d.json' % i for i in range(1, 5)]
    expected_values = {"total": 29, "failures": 0, "skipped": 0, "excluded": 22}
    assert {k:v["value"] for k,v in schemas["schemas"]["corrected/exunit-result.json"].items()} == expected_values
    for name in ("runner.py", "prepare.py", "tools/openssl"):
        ast.parse((PACKET / name).read_text(), filename=name)
    controls_path = LANE / "offline-validator-controls.json"
    controls = read(controls_path)
    assert controls["plan_sha256"] == sha(PACKET / "execution-plan.json") and controls["valid_control_accepted"] is True
    assert len(controls["invalid_controls"]) == 14 and all(v["rejected"] is True for v in controls["invalid_controls"])
    assert controls["compiler_or_runtime_invocations"] == 0
    result = {
        "schema": 1,
        "status": "passed-independent-CI-fixture-candidate-source-custody-runtime-unrun",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": "python3 -B verification/console-key-owner-fixture-cleanup-ci-independent/review-1/audit_candidate.py",
        "python": sys.version,
        "review_script_sha256": sha(Path(__file__)),
        "preaccess_seal_sha256": sha(PREACCESS / "preaccess-seal.json"),
        "producer_freeze_sha256": sha(PACKET / "freeze.json"),
        "producer_plan_sha256": sha(PACKET / "execution-plan.json"),
        "source_revision": plan["source_revision"],
        "selected_source_tree_sha256": plan["source_tree_sha256"],
        "verified": {"packet_members": 221, "prepared_pins": 220, "canonical_pins": 25, "tool_pins": 980, "accepted_product_source_files": 18, "support_modules": 3, "source_declared_methods": 29, "selected_existing_methods": 7, "unselected_methods": 22, "dependency_apps": 5, "active_canonical_product_source_not_in_closure": True, "beforeimage_matches_delivered_source": True, "exact_recorded_diff": True, "preaccess_three_members_unchanged": True},
        "producer_offline_controls_not_replayed": {"receipt_sha256": sha(controls_path), "inside_producer_freeze": False, "plan_bound": True, "valid_accepted": 1, "malformed_refused": 14},
        "recommend_root_single_exact_host_release": False,
        "blocking_release_findings": [{"id": "R01", "priority": "P2", "classification": "artifact-directory evidence-validator robustness", "required_fix": "Check actual phase directory exact ten-file membership before constructing eight-artifact map; preserve unexpected files on failure"}],
        "runtime_verified": False,
        "producer_code_imported_or_replayed": False,
        "runtime_compiler_formatter_OpenSSL_TLS_or_process_inventory_invocations": 0,
        "elapsed_seconds": round(time.monotonic() - START, 6),
        "scope": "Review and custody only; future targeted pass cannot accept full KeyOwnerTest/Phoenix suite or GA."
    }
    (OUT / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
