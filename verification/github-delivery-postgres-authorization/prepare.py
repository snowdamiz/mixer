#!/usr/bin/env python3
"""Prepare an exact validated delivery allowlist; no staging or publication."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "cb56d4b9d979ffc02554be991466a180e7882cd3"
SEALS = {
    "verification/hosted-customer-authorization-postgres/final-seal.json":
        "61c25aad3dc31050f6a196950a7a51fc21bad158f9f8936e884f568a36b8b6ff",
    "verification/hosted-customer-authorization-postgres-review/seal.json":
        "c51cdbe91de691a35edd387bbef0239de361f5738f58999d7e4434b3bfabfdae",
    "verification/swift-cost-retention-candidate/seal.json":
        "a71d7d9b4405b37e2130c464e0e149d82b2a1ff57f9f75f36cc0e8401bb50702",
    "verification/swift-cost-retention-candidate-review/seal.json":
        "0993e18e6aeb41246fe84dbfacaf74d8068286857dbbc5824b30e93e5f6da676",
}
selected = {}


def add(name, expected=None):
    p = ROOT / name
    assert p.resolve().is_relative_to(ROOT)
    assert not any(x in str(p) for x in ["hosted-catalog-inspector", "hosted-authority-driver", "outbound-worker-transport-v2"])
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size < 100_000_000
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    if expected is not None:
        assert digest == expected, name
    selected[str(p.relative_to(ROOT))] = {"sha256": digest, "bytes": s.st_size}


assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == BASE
assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT).strip()
for name, expected in SEALS.items():
    add(name, expected)
    path = ROOT / name
    seal = json.loads(path.read_text())
    for member, digest in seal.get("files", {}).items():
        add(member, digest)
    for member, digest in seal.get("live_input_bindings", {}).items():
        add(member, digest)
    for member, entry in seal.get("members", {}).items():
        add(str((path.parent / member).relative_to(ROOT)), entry["sha256"])
    if "docSHA256" in seal:
        add(seal.get("docPath", "docs/swift-cost-retention-candidate.md"), seal["docSHA256"])

for name in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]:
    add(name)
for folder in ["hosted-customer-authorization-postgres-root-acceptance", "swift-cost-retention-root-acceptance"]:
    for name in ["verify.py", "acceptance.json"]:
        add(f"verification/{folder}/{name}")
for name in ["record.py", "observation-1/receipt.json", "observation-1/phoenix.json",
             "observation-1/phoenix.stderr", "observation-1/engine.json", "observation-1/engine.stderr"]:
    add("verification/github-ci-cb56d4b9/" + name)
for name in ["commit.stdout", "commit.stderr", "push.stdout", "push.stderr", "delivery-receipt.json",
             "ci-initial.json", "ci-initial-receipt.json", "phoenix-current.json", "engine-current.json",
             "phoenix-observation-2.json", "engine-observation-2.json", "ci-observation-2-receipt.json"]:
    add("verification/github-delivery-retention-authorization/" + name)

for name, key, field, count in [("work-graph.json", "packages", "state", 18), ("gates/ga.json", "gates", "status", 38)]:
    before = json.loads(subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT))
    after = json.loads((ROOT / name).read_text())
    assert len(after[key]) == count
    assert [(x["id"], x[field], x.get("reviewer")) for x in before[key]] == [(x["id"], x[field], x.get("reviewer")) for x in after[key]]
ci = json.loads((ROOT / "verification/github-ci-cb56d4b9/observation-1/receipt.json").read_text())
assert ci["sourceRevision"] == BASE
assert all(x["status"] == "completed" and x["conclusion"] == "success" for x in ci["workflows"])
assert all(j["skippedSteps"] == 0 for x in ci["workflows"] for j in x["jobs"])

argv = ["python3", "scripts/check-policy.py"]
check = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=90)
(OUT / "policy.stdout").write_bytes(check.stdout)
(OUT / "policy.stderr").write_bytes(check.stderr)
assert check.returncode == 0 and json.loads(check.stdout)["status"] == "passed"
(OUT / "policy-receipt.json").write_text(json.dumps({"argv": argv, "exitCode": check.returncode,
    "scope": "manifest-and-gate-guardrail-only", "scriptSHA256": hashlib.sha256((ROOT / argv[1]).read_bytes()).hexdigest(),
    "python": subprocess.check_output(["python3", "--version"], text=True).strip()}, indent=2) + "\n")
for name in ["prepare.py", "policy.stdout", "policy.stderr", "policy-receipt.json"]:
    add(str((OUT / name).relative_to(ROOT)))
manifest = {"schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "baseRevision": BASE, "seals": SEALS, "files": dict(sorted(selected.items())),
    "scope": "Reviewed local PostgreSQL lookup and selected CI fixture/migration integration; audited rejected finite cache experiment. No live VM, public route, native, provider or GA acceptance."}
(OUT / "selection.json").write_text(json.dumps(manifest, indent=2) + "\n")
paths = sorted([*selected, str((OUT / "selection.json").relative_to(ROOT))])
(OUT / "paths.nul").write_bytes(b"".join(os.fsencode(x) + b"\0" for x in paths))
print(json.dumps({"selectedFiles": len(paths), "selectedBytes": sum(x["bytes"] for x in selected.values()),
    "sealedPackets": len(SEALS), "gateStatesUnchanged": True}))
