#!/usr/bin/env python3
"""Read-only packet audit; no producer code, compiler, target or native execution."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "verification/swift-ordered-retention-analyzer-library"
EXPECTED = "777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify_row(row):
    path = ROOT / row["path"]
    assert path.is_file() and not path.is_symlink(), row["path"]
    assert path.resolve().is_relative_to(ROOT), row["path"]
    raw = path.read_bytes()
    assert len(raw) == row["bytes"] and digest(raw) == row["sha256"], row["path"]


def verify_seal(path, expected):
    raw = path.read_bytes()
    assert digest(raw) == expected, str(path)
    seal = json.loads(raw)
    names = [row["path"] for row in seal["members"]]
    assert len(names) == len(set(names)), str(path)
    for row in seal["members"]:
        verify_row(row)
    return seal


seal = verify_seal(BASE / "seal.json", EXPECTED)
assert (BASE / "seal.sha256").read_text().split()[0] == EXPECTED
actual = {str(p.relative_to(ROOT)) for p in BASE.rglob("*") if p.is_file()}
actual.add("docs/swift-ordered-retention-analyzer-library.md")
assert actual == {r["path"] for r in seal["members"]} | set(seal["excluded"])
assert len(seal["members"]) == 270
assert sum(row["bytes"] for row in seal["members"]) == 44_356_309
final = json.loads((BASE / "final-receipt.json").read_bytes())
for row in final["source_manifest"]:
    verify_row(row)
assert digest(json.dumps(final["source_manifest"], sort_keys=True, separators=(",", ":")).encode()) == final["source_tree_sha256"]
run_path = ROOT / final["final_test_receipt"]
run = json.loads(run_path.read_bytes())
assert run["passed"] is True
assert run["source_tree_sha256"] == final["tested_library_tree_sha256"]
assert run["sources_before"] == run["sources_after"]
for row in run["sources_after"]:
    verify_row(row)
for command in run["commands"]:
    assert command["returncode"] == 0
    for stream in ("stdout", "stderr"):
        output = run_path.parent / (command["name"] + "." + stream)
        assert digest(output.read_bytes()) == command[stream + "_sha256"], str(output)
assert "20 passed; 0 failed" in (run_path.parent / "test-execute.stdout").read_text()
assert final["upstream_before"] == final["upstream_after"]
upstream = []
for row in final["upstream_after"]:
    old = verify_seal(ROOT / "verification" / row["packet"] / "seal.json", row["seal_sha256"])
    assert len(old["members"]) == row["members"]
    upstream.append(row)
assert sum(row["members"] for row in upstream) == 845
for row in run["historical"]:
    assert row["original_status"] == "invalid" and row["original_failure"] == 15
    verify_row(row["sidecar"])
    verify_row(row["stream"])
assert len(run["historical"]) == 17
for tool in final["tools"].values():
    assert digest(Path(tool["path"]).read_bytes()) == tool["sha256"]
for key in ("fullReplayAccepted", "storedPrefixValidated", "semantic_metrics_available", "real_adapters_available", "self_acceptance"):
    assert final[key] is False
assert final["cleanup"]["owned_scratch_remaining"] is False
assert not any(p.is_file() for p in (BASE / "scratch").rglob("*"))
print(json.dumps({
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "python": platform.python_version(),
    "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "script_sha256": digest(Path(__file__).read_bytes()),
    "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
    "producer_seal_sha256": EXPECTED,
    "producer_members": len(seal["members"]),
    "producer_bytes": sum(row["bytes"] for row in seal["members"]),
    "source_tree_sha256": final["source_tree_sha256"],
    "tested_library_tree_sha256": final["tested_library_tree_sha256"],
    "final_commands_verified": len(run["commands"]),
    "recorded_producer_methods": 20,
    "upstream": upstream,
    "upstream_members": 845,
    "historical_sidecars_unchanged_invalid_failure15": 17,
    "owned_scratch_files": 0,
    "scope": "Read-only integrity audit of frozen fixture framing foundation; independent implementation acceptance pending",
    "code_or_compiler_executed": False,
    "storedPrefixValidated": False,
    "fullReplayAccepted": False,
}, indent=2))
