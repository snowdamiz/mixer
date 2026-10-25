#!/usr/bin/env python3
"""Select only completed identity/observer packets and root-owned indexes."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = "6b8aba350224ed19f678669bdbea6b359d8de68b"

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert git("rev-parse", "HEAD").decode().strip() == BASE
assert not git("diff", "--cached", "--name-only").strip()
selected = {"PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"}

def add(path, expected=None):
    p = ROOT / path
    assert p.is_file() and not p.is_symlink(), path
    assert p.resolve().is_relative_to(ROOT)
    if expected:
        assert sha(p) == expected, path
    selected.add(str(p.relative_to(ROOT)))

for name in ["swift-cache-current-attribution-observer", "swift-cache-attribution-independent-review"]:
    base = ROOT / "verification" / name
    seal = base / "seal.json"
    data = json.loads(seal.read_text())
    add(str(seal.relative_to(ROOT)))
    for path, digest in data["files"].items():
        add(str((base / path).relative_to(ROOT)), digest)
    for path, digest in data["externalFiles"].items():
        add(path, digest)

for name in ["apple-reference-focus-lifecycle-diagnosis", "apple-passive-lifecycle-observer", "apple-passive-lifecycle-review"]:
    seal = ROOT / "verification" / name / "handoff.json"
    add(str(seal.relative_to(ROOT)))
    for path, info in json.loads(seal.read_text())["members"].items():
        add(path, info["sha256"])

for name in ["hosted-bearer-identity-transport", "hosted-bearer-identity-review"]:
    seal = ROOT / "verification" / name / "handoff-sha256.json"
    add(str(seal.relative_to(ROOT)))
    for path, digest in json.loads(seal.read_text()).items():
        add(path, digest)

# The next full-runtime packet is completed preparation, explicitly not accepted
# for execution. Its active independent review is outside this selection.
base = ROOT / "verification/swift-current-attribution-full-preparation"
seal = base / "prepared-seal.json"
data = json.loads(seal.read_text())
add(str(seal.relative_to(ROOT)))
for path, info in data["files"].items():
    add(str((base / path).relative_to(ROOT)), info if isinstance(info, str) else info["sha256"])
for path, digest in data.get("externalFiles", {}).items():
    add(path, digest)
add("docs/swift-current-attribution-full-preparation.md")

for name in ["current-observer-root-review", "github-ci-6b8aba35-engine", "github-delivery-runtime-diagnostics"]:
    for path in sorted((ROOT / "verification" / name).rglob("*")):
        if path.is_file():
            add(str(path.relative_to(ROOT)))

for path in selected:
    assert "swift-current-attribution-preparation-review" not in path
    assert "apple-passive-lifecycle-generic-build" not in path

for filename, key, state in [("work-graph.json", "packages", "state"), ("gates/ga.json", "gates", "status")]:
    current = json.loads((ROOT / filename).read_text())
    previous = json.loads(git("show", "HEAD:" + filename))
    project = lambda data: [(r["id"], r[state], r.get("reviewer")) for r in data[key]]
    assert project(current) == project(previous)

add(str(Path(__file__).relative_to(ROOT)))
manifest = {path: {"sha256": sha(ROOT / path), "bytes": (ROOT / path).stat().st_size} for path in sorted(selected)}
(HERE / "selected-files.json").write_text(json.dumps({"base": BASE, "files": manifest}, indent=2) + "\n")
selected.add(str((HERE / "selected-files.json").relative_to(ROOT)))
(HERE / "paths.nul").write_bytes(b"\0".join(path.encode() for path in sorted(selected)) + b"\0")
print(json.dumps({"selectedPaths": len(selected), "selectedBytes": sum(p["bytes"] for p in manifest.values()), "base": BASE, "activeLanesExcluded": True}))
