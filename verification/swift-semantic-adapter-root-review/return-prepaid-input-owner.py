"""Record the independently reproduced model defects without replaying tests."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
out = Path(__file__).with_name("guarded-snapshot-prepaid-input-owner-return.json")
assert not out.exists(), "one-shot root disposition"
sha = lambda data: hashlib.sha256(data).hexdigest()
specs = [
    ("swift-guarded-snapshot-prepaid-input-owner-contract", "9c73d3405370a71ad447136ab7a4e56c2d45dbf4fd4627c319a8626f8a53033e", 36, 448460),
    ("swift-guarded-snapshot-prepaid-input-owner-independent", "0d9c3d4eb6e99a9daa34f2a8ee798c739b0c6e9c41b35b6ef54c2e900684caa2", 42, 928074),
]
custody = []
for name, expected, count, size in specs:
    packet = root / "verification" / name
    raw = (packet / "seal.json").read_bytes()
    assert sha(raw) == expected
    seal = json.loads(raw)
    names = [m["path"] for m in seal["members"]]
    assert len(names) == len(set(names)) == seal["member_count"] == count
    assert sum(m["bytes"] for m in seal["members"]) == seal["member_bytes"] == size
    assert all(not p.is_symlink() for p in packet.rglob("*"))
    assert {str(p.relative_to(packet)) for p in packet.rglob("*") if p.is_file()} == set(names) | {"seal.json"}
    for m in seal["members"]:
        relative = Path(m["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        data = (packet / relative).read_bytes()
        assert len(data) == m["bytes"] and sha(data) == m["sha256"], m["path"]
    custody.append({"path": str(packet.relative_to(root)), "seal_sha256": expected, "members": count, "bytes": size})

review = root / "verification/swift-guarded-snapshot-prepaid-input-owner-independent"
review_seal = json.loads((review / "seal.json").read_text())
for cmd in review_seal["commands"]:
    p = review / cmd["path"] / "receipt.json"
    assert sha(p.read_bytes()) == cmd["receipt_sha256"]
    r = json.loads(p.read_text())
    assert r["exit"] == cmd["exit"] and not r["timed_out"]
    assert r["inputs_unchanged"] and r["child_reaped"] and r["owned_group_absent"]
    for output in r["outputs"]:
        data = (root / output["path"]).read_bytes()
        assert len(data) == output["bytes"] and sha(data) == output["sha256"]
assert "FAILED (failures=4)" in (review / "commands/candidate-desired-properties/stderr").read_text()
report = json.loads((review / "report.json").read_text())
assert report["candidate_desired_property_tests"] == {"methods": 4, "exit": 1, "failures": 4, "accepted": False}
contract = review / "correction-contract.json"
assert [r["id"] for r in json.loads(contract.read_text())["requirements"]] == ["R1", "R2", "R3"]
receipt = {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "status": "returned-host-model-evidence-for-R1-R3-correction",
    "root_HEAD": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, timeout=10, text=True).strip(),
    "custody": custody, "complete_membership_and_command_output_checks": True,
    "candidate_desired_properties_failed": 4, "independent_controls_passed": 16,
    "exhaustive_read_schedules": 100842,
    "correction_contract": str(contract.relative_to(root)), "correction_contract_sha256": sha(contract.read_bytes()),
    "root_source_inspection": {"file": "verification/swift-guarded-snapshot-prepaid-input-owner-contract/model.py", "lines": [78, 112, 127, 166, 181, 293, 317],
                               "findings": ["adopted handles absent from retirement roster", "storage release ignores live handles", "admission detached from reservation and live owners", "equality of caller dictionaries accepts incomplete provenance"]},
    "minimum_existing_open_plus_correlation_direction_retained": True,
    "same_handle_route_selected": False, "new_threat_model_or_native_authority": False,
    "original_failed_candidate_and_reviewer_attempts_preserved": True,
    "candidate_model_accepted": False, "root_policy_or_funding_or_operational_OTA_GA": False,
    "tool": {"argv": sys.argv, "python": sys.version,
             "executable_sha256": sha(Path(sys.executable).resolve().read_bytes()), "script_sha256": sha(Path(__file__).read_bytes())},
    "scope": "pure host root custody and source inspection; no compiler/test/runtime replay",
}
with out.open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
print(json.dumps({"path": str(out.relative_to(root)), "sha256": sha(out.read_bytes()), "correction_contract_sha256": sha(contract.read_bytes()), "accepted": False}))
