#!/usr/bin/env python3
"""Read-only contract packet audit; no model, layout binary or compiler execution."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "verification/swift-ordered-retention-analyzer-fsm-contract"
EXPECTED = "a8cf795a8226fed9facf654b05d0ef6cf7146a289eb3c8df8946c5306f9b73b6"


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
assert len(packet["members"]) == 137
assert sum(row["bytes"] for row in packet["members"]) == 3_927_907
result = json.loads((BASE / "result.json").read_bytes())
run_path = BASE / result["final_run"]
run = json.loads(run_path.read_bytes())
assert run["passed"] is True and run["upstream_before"] == run["upstream_after"]
assert digest(json.dumps(run["source_snapshot"], sort_keys=True, separators=(",", ":")).encode()) == result["external_source_tree_digest"]
assert digest(json.dumps(run["finite_sources"], sort_keys=True, separators=(",", ":")).encode()) == result["finite_tree_digest"]
for row in run["source_snapshot"]:
    check(row, BASE / "inputs/run-5" / row["path"].replace("/", "__"))
for row in run["finite_sources"]:
    check(row)
for command in run["commands"]:
    assert command["exit"] == 0
    for stream in ("stdout", "stderr"):
        assert digest((run_path.parent / (command["name"] + "." + stream)).read_bytes()) == command[stream + "_sha256"]
assert "Ran 18 tests" in (run_path.parent / "finite-model.stderr").read_text()
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
    "recorded_finite_methods": 18,
    "upstream_members_unchanged": 845,
    "scope": "Read-only preparatory fixture FSM contract integrity; independent review pending, no implementation selection",
    "model_layout_or_compiler_executed": False,
    "storedPrefixValidated": False,
    "fullReplayAccepted": False,
}, indent=2))
