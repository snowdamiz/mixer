#!/usr/bin/env python3
"""Read-only contract packet audit; no model, layout binary or compiler execution."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "verification/swift-ordered-retention-analyzer-fsm-contract"
EXPECTED = "bde96e5f4f1b0ad5bc6366fee79a47f7a375247959191b206d8e7799ed4da193"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check(row, path=None):
    path = path or ROOT / row["path"]
    assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    raw = path.read_bytes()
    assert len(raw) == row["bytes"] and digest(raw) == row["sha256"], str(path)


def seal(path, expected):
    raw = path.read_bytes()
    assert digest(raw) == expected
    value = json.loads(raw)
    assert len({row["path"] for row in value["members"]}) == len(value["members"])
    for row in value["members"]:
        check(row)
    return value


packet = seal(BASE / "seal.json", EXPECTED)
assert (BASE / "seal.sha256").read_text().strip() == EXPECTED
actual = {str(p.relative_to(ROOT)) for p in BASE.rglob("*") if p.is_file()}
actual.add("docs/swift-ordered-retention-analyzer-fsm-contract.md")
assert actual == {row["path"] for row in packet["members"]} | set(packet["excluded"])
assert len(packet["members"]) == 245
assert sum(row["bytes"] for row in packet["members"]) == 10_117_781
result = json.loads((BASE / "result.json").read_bytes())
run_path = BASE / result["final_run"]
run = json.loads(run_path.read_bytes())
assert run["passed"] is True and run["upstream_before"] == run["upstream_after"]
assert digest(json.dumps(run["source_snapshot"], sort_keys=True, separators=(",", ":")).encode()) == result["external_source_tree_digest"]
assert digest(json.dumps(run["finite_sources"], sort_keys=True, separators=(",", ":")).encode()) == result["finite_tree_digest"]
for row in run["source_snapshot"]:
    check(row, BASE / "inputs/run-8" / row["path"].replace("/", "__"))
for row in run["finite_sources"]:
    check(row)
for command in run["commands"]:
    assert command["exit"] == 0
    for stream in ("stdout", "stderr"):
        assert digest((run_path.parent / (command["name"] + "." + stream)).read_bytes()) == command[stream + "_sha256"]
assert "Ran 24 tests" in (run_path.parent / "finite-model.stderr").read_text()
assert "\nOK\n" in (run_path.parent / "finite-model.stderr").read_text()
assert digest((ROOT / run["layout_binary"]["path"]).read_bytes()) == run["layout_binary"]["sha256"]
for name in ("python", "rustc"):
    assert digest(Path(run[name]["path"]).read_bytes()) == run[name]["sha256"]
for row in run["upstream_after"]:
    assert len(seal(ROOT / row["seal"], row["sha256"])["members"]) == row["members"]
assert sum(row["members"] for row in run["upstream_after"]) == 845
for row in run["wire_original_equality"]:
    assert digest((ROOT / row["copy"]).read_bytes()) == digest((ROOT / row["original"]).read_bytes()) == row["sha256"]
for key in ("fullReplayAccepted", "storedPrefixValidated", "semanticMetricsValid", "rust_integration_selected", "combined_8192_preflight_qualified", "complete_composed_lifetime_inventory_qualified"):
    assert result[key] is False
archive_results = []
for relative, archive_hash, seal_name, seal_hash, count in [
    ("history/first-freeze/packet.tar.gz", "ee5bfd08111a0bd0993b91814add86948622e041d003eb85a6cad678edabdbdc", "verification/swift-ordered-retention-analyzer-fsm-contract/seal.json", "a8cf795a8226fed9facf654b05d0ef6cf7146a289eb3c8df8946c5306f9b73b6", 139),
    ("history/findings-freeze-1/packet.tar.gz", "4d1a0f8ea4ae290831059e3cf3cd54e5e53c6701eb43d5a56397bd1de5c8282c", "verification/swift-ordered-retention-analyzer-fsm-contract-review/findings-freeze1-seal.json", "31460ea35508acfc5b0093f5f32874b1baa69f4377285ce4060c503f98d765e6", 210),
]:
    path = BASE / relative
    assert digest(path.read_bytes()) == archive_hash
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        assert len(members) == count
        assert len({m.name for m in members}) == count
        assert all(m.isfile() and not Path(m.name).is_absolute() and ".." not in Path(m.name).parts for m in members)
        seal_raw = archive.extractfile(seal_name).read()
        assert digest(seal_raw) == seal_hash
        old = json.loads(seal_raw)
        for row in old["members"]:
            raw = archive.extractfile(row["path"]).read()
            assert len(raw) == row["bytes"] and digest(raw) == row["sha256"]
        assert {m.name for m in members} == {r["path"] for r in old["members"]} | {seal_name, seal_name.replace(".json", ".sha256")}
        assert archive.extractfile(seal_name.replace(".json", ".sha256")).read().decode().strip() == seal_hash
    archive_results.append({"path": str(path.relative_to(ROOT)), "sha256": archive_hash, "members": count, "all_member_bytes_verified": True, "extracted_or_executed": False})
assert result["leaf_setup_debit"] == 534 and result["leaf_record_debit"] == 128
assert result["initialization_named_roles"] == 4728 and result["closed_leaf_named_roles"] == 4536
assert result["closed_leaf_reservation"] == 5120
print(json.dumps({
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "python": platform.python_version(),
    "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "script_sha256": digest(Path(__file__).read_bytes()),
    "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
    "producer_seal_sha256": EXPECTED,
    "producer_members": len(packet["members"]),
    "producer_bytes": sum(row["bytes"] for row in packet["members"]),
    "external_source_tree_digest": result["external_source_tree_digest"],
    "finite_tree_digest": result["finite_tree_digest"],
    "final_commands_verified": len(run["commands"]),
    "recorded_finite_methods": 24,
    "upstream_members_unchanged": 845,
    "preserved_archives": archive_results,
    "setup_debit": 534,
    "record_debit": 128,
    "init_named_roles": 4728,
    "call_named_roles": 4536,
    "scope": "Read-only amended preparatory fixture FSM contract integrity; independent review pending, no implementation selection",
    "model_layout_or_compiler_executed": False,
    "storedPrefixValidated": False,
    "fullReplayAccepted": False,
}, indent=2))
