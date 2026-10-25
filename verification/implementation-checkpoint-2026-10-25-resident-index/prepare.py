#!/usr/bin/env python3
"""Curate frozen candidates, independent finding and next-format contract only."""
from pathlib import Path
import datetime
import hashlib
import json
import stat
import subprocess

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (BASE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT)
names = {
    "STATUS.md", "PLAN.md", "work-graph.json", "gates/ga.json",
    "docs/swift-cache-resident-index.md",
    "docs/swift-cache-resident-index-review.md",
    "docs/swift-cache-resident-index-integration.md",
    "docs/apple-settings-fixed-chunk-contract.md",
    "docs/hosted-worker-pending-entry-integration-contract.md",
    "docs/hosted-worker-pending-registry-track-recheck.md",
    "docs/hosted-worker-pending-registry-track-review.md",
    "docs/hosted-worker-pending-terminal-consistency.md",
}
checks = []
path = ROOT / "verification/swift-cache-resident-index/seal.json"
assert sha(path) == "fc45e20ca74edc4d435b1d9d82ed8b01bb68a55b42801501901356ab530b39d7"
seal = json.loads(path.read_text())
names.add(str(path.relative_to(ROOT)))
for name, expected in seal["members"].items():
    member = path.parent / name
    assert sha(member) == expected, member
    names.add(str(member.relative_to(ROOT)))
checks.append({"packet": str(path.relative_to(ROOT)), "verifiedMembers": len(seal["members"]), "sha256": sha(path)})
path = ROOT / "verification/swift-cache-resident-index-review/seal.json"
assert sha(path) == "0a2f41abff2d3efb3aa89185fbd432bac99237fce181495414bc627dbc2b1547"
seal = json.loads(path.read_text())
names.add(str(path.relative_to(ROOT)))
for name, expected in seal["members"].items():
    member = path.parent / name
    assert sha(member) == expected, member
    names.add(str(member.relative_to(ROOT)))
checks.append({"packet": str(path.relative_to(ROOT)), "verifiedMembers": len(seal["members"]), "sha256": sha(path)})
manifest = json.loads((ROOT / "verification/swift-cache-resident-index/candidate-source-manifest.json").read_text())
assert {name: sha(ROOT / "vm" / name) for name in manifest} == manifest
candidate_receipt = json.loads((ROOT / "verification/swift-cache-resident-index/receipt.json").read_text())
names.update("vm/" + name for name in candidate_receipt["changedFiles"])
integration = json.loads((ROOT / "verification/swift-cache-resident-index-root-integration/receipt.json").read_text())
assert integration["status"] == "accepted-live-private-resident-index-integration" and integration["ownedTargetRemoved"]
assert sum(c["expectedTests"] for c in integration["commands"]) == 32
for name, expected in [
    ("hosted-worker-pending-registry-track-recheck", "d9bd48d069746b24ed3386e9842a1693e5aba44c33ffd4e095646acaef7cff5c"),
    ("hosted-worker-pending-registry-track-review", "f9b18c8fe622e14964abcb7e41ba046e1ef4e48cf81b80c22c457fa7bb7f13d1"),
    ("hosted-worker-pending-terminal-consistency", "e4afac5866c26ffd96c460bbdd54e3cf0098bc1d378601ba7e542d6f819e677b"),
]:
    path = ROOT / "verification" / name / "receipt.json"
    assert sha(path) == expected, path
    receipt = json.loads(path.read_text())
    for item in receipt["artifacts"]:
        member = ROOT / item["path"]
        assert sha(member) == item["sha256"] and member.stat().st_size == item["bytes"], member
        names.add(item["path"])
    names.add(str(path.relative_to(ROOT)))
    for member in path.parent.iterdir():
        if member.is_file():
            names.add(str(member.relative_to(ROOT)))
    checks.append({"packet": str(path.relative_to(ROOT)), "verifiedMembers": len(receipt["artifacts"]), "sha256": sha(path)})
path = ROOT / "verification/apple-settings-chunk-deadline-diagnosis/handoff.json"
assert sha(path) == "019746fbd6344209c69ffde35a7a0933378943c280bbc3a69147b2afb532c40b"
handoff = json.loads(path.read_text())
for name, item in handoff["members"].items():
    member = ROOT / name
    assert sha(member) == item["sha256"] and member.stat().st_size == item["bytes"], member
    names.add(name)
names.add(str(path.relative_to(ROOT)))
checks.append({"packet": str(path.relative_to(ROOT)), "verifiedMembers": len(handoff["members"]), "sha256": sha(path)})
for directory in [
    "apple-settings-fixed-chunk-root-selection", "implementation-progress-2026-10-25-fixed-chunks",
    "github-ci-4a4d8b73-engine", "github-ci-ee390cbf-engine", "github-delivery-settings-result",
    "swift-cache-resident-index-root-integration",
]:
    for member in (ROOT / "verification" / directory).rglob("*"):
        assert not member.is_symlink(), member
        if member.is_file():
            names.add(str(member.relative_to(ROOT)))
for name in names:
    member = ROOT / name
    info = member.lstat()
    assert stat.S_ISREG(info.st_mode) and not member.is_symlink() and info.st_size < 50_000_000, member
    assert not {"node_modules", "owned-build", "owned-source", "owned-review", "target", "tmp"}.intersection(member.relative_to(ROOT).parts), member
    assert "native-run-v6-" not in name, name
packages = json.loads((ROOT / "work-graph.json").read_text())["packages"]
gates = json.loads((ROOT / "gates/ga.json").read_text())["gates"]
assert [p["id"] for p in packages] == [f"W{i:02}" for i in range(1, 19)]
assert [g["id"] for g in gates] == [f"G{i:02}" for i in range(1, 39)]
for gate in gates:
    if gate["status"] == "passed":
        assert gate["evidence"] and gate["reviewer"]
save("verification.json", {
    "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "parentRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "checks": checks, "trackerIntegrity": "passed",
    "scope": "Accepted live resident-index integration and independent review, failed worker review and frozen correction, selected fixed upload format and host CI. Active implementation, review and reactor preparation lanes excluded.",
    "liveIntegrationAccepted": True, "liveIntegrationTestsPassed": 32,
    "nativeAccepted": False, "gaAccepted": False,
})
names.update(str(p.relative_to(ROOT)) for p in BASE.iterdir() if p.is_file())
manifest = str(BASE.relative_to(ROOT) / "selected-files.json")
hashes = str(BASE.relative_to(ROOT) / "source-hashes.json")
names.update([manifest, hashes])
names = sorted(names)
save("selected-files.json", names)
save("source-hashes.json", {name: sha(ROOT / name) for name in names if name not in (manifest, hashes)})
print(json.dumps({"selectedFiles": len(names), "bytes": sum((ROOT / name).stat().st_size for name in names), "frozenPackets": len(checks)}))
