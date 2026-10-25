#!/usr/bin/env python3
"""Read-only integrity audit; does not run a model, analyzer, compiler, or target."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "verification/swift-ordered-retention-analyzer-design"
EXPECTED = "c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def audit_seal(path, expected):
    raw = path.read_bytes()
    assert digest(raw) == expected
    seal = json.loads(raw)
    names = set()
    for row in seal["members"]:
        assert row["path"] not in names
        names.add(row["path"])
        p = ROOT / row["path"]
        assert p.is_file() and not p.is_symlink()
        data = p.read_bytes()
        assert len(data) == row["bytes"] and digest(data) == row["sha256"]
    return seal


current = audit_seal(BASE / "seal.json", EXPECTED)
assert (BASE / "seal.sha256").read_text().strip() == EXPECTED
actual = {str(p.relative_to(ROOT)) for p in BASE.rglob("*") if p.is_file()}
actual.add("docs/swift-ordered-retention-analyzer.md")
assert actual == {r["path"] for r in current["members"]} | set(current["excluded"])
result = json.loads((BASE / "result.json").read_bytes())
upstream = []
for row in result["upstream_after"]:
    seal = audit_seal(ROOT / row["seal"], row["sha256"])
    assert len(seal["members"]) == row["members"]
    upstream.append({"seal": row["seal"], "sha256": row["sha256"], "members": len(seal["members"])})
amendment = json.loads((BASE / "amendment.json").read_bytes())
archive = BASE / amendment["prior_archive"]
assert digest(archive.read_bytes()) == amendment["prior_archive_sha256"]
with tarfile.open(archive, "r:gz") as packet:
    entries = packet.getmembers()
    assert len(entries) == amendment["prior_archive_members"]
    assert len({e.name for e in entries}) == len(entries)
    assert all(e.isfile() for e in entries)
    seal_name = "verification/swift-ordered-retention-analyzer-design/seal.json"
    raw = packet.extractfile(seal_name).read()
    assert digest(raw) == amendment["prior_seal_sha256"]
    old = json.loads(raw)
    assert {e.name for e in entries} == {r["path"] for r in old["members"]} | set(old["excluded"])
    for row in old["members"]:
        data = packet.extractfile(row["path"]).read()
        assert len(data) == row["bytes"] and digest(data) == row["sha256"]
    assert packet.extractfile(seal_name.replace(".json", ".sha256")).read().decode().strip() == amendment["prior_seal_sha256"]
carried = result["carried_layout"]
assert carried["actual_compile_or_layout_rerun"] is False
assert digest((ROOT / carried["receipt"]).read_bytes()) == carried["receipt_sha256"]
assert digest((BASE / "layout.rs").read_bytes()) == carried["layout_source_sha256"]
assert digest((ROOT / result["binary"]["path"]).read_bytes()) == carried["binary_sha256"]
assert digest(Path(result["tools"]["rustc"]["path"]).read_bytes()) == carried["compiler_sha256"]
print(json.dumps({
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "python": platform.python_version(),
    "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "design_seal_sha256": EXPECTED,
    "design_members": len(current["members"]),
    "design_bytes": sum(r["bytes"] for r in current["members"]),
    "source_tree_sha256": result["source_tree_sha256"],
    "prior_freeze": {"seal_sha256": amendment["prior_seal_sha256"], "members": len(old["members"]), "archive_members": len(entries), "archive_sha256": amendment["prior_archive_sha256"]},
    "upstream": upstream,
    "upstream_members": sum(r["members"] for r in upstream),
    "carried_layout_verified_without_execution": True,
    "scope": "Read-only corrected-contract and preserved-history integrity audit; independent design review pending",
    "fullReplayAccepted": False,
}, indent=2))
