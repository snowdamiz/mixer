#!/usr/bin/env python3
"""Prepare only reviewed transaction work and bounded proposal evidence."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "d385adf3dd110da44ba290a7221278c48e39b882"
selected = {}


def add(name, expected=None):
    p = ROOT / name
    assert p.resolve().is_relative_to(ROOT) and not p.is_symlink()
    assert stat.S_ISREG(p.stat().st_mode) and p.stat().st_size < 100_000_000
    assert "__pycache__" not in p.parts
    assert not any(part in name for part in ["hosted-catalog-inspector", "hosted-authority-driver", "outbound-worker-transport-v2"])
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if expected:
        assert h == expected, name
    selected[name] = {"sha256": h, "bytes": p.stat().st_size}


assert not (OUT / "selection.json").exists()
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == BASE
assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT).strip()
acceptance_path = "verification/hosted-customer-authorized-transaction-root-acceptance/acceptance.json"
acceptance = json.loads((ROOT / acceptance_path).read_text())
assert acceptance["producerMethodsPassed"] == 18 and acceptance["independentMethodsPassed"] == 21
assert acceptance["ciEquivalentMethodsPassed"] == 18 and acceptance["ordinaryMigrations"] == 6
for section in ["files", "liveInputBindings"]:
    for name, h in acceptance[section].items():
        add(name, h)
add(acceptance_path)
add("verification/hosted-customer-authorized-transaction-root-acceptance/verify.py")
for folder in ["hosted-customer-artifact-transaction-contract", "swift-adaptive-retention-design",
               "swift-adaptive-retention-root-review", "github-ci-d385adf3"]:
    for p in sorted((ROOT / "verification" / folder).rglob("*")):
        if p.is_file():
            add(str(p.relative_to(ROOT)))
for name in ["docs/hosted-customer-artifact-transaction-contract.md", "docs/swift-adaptive-retention-design.md",
             "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]:
    add(name)
for name in ["commit.stdout", "commit.stderr", "push.stdout", "push.stderr", "delivery-receipt.json",
             "ci-initial.json", "ci-initial.stderr", "ci-initial-receipt.json"]:
    add("verification/github-delivery-postgres-authorization/" + name)
for name, group, state, count in [("work-graph.json", "packages", "state", 18), ("gates/ga.json", "gates", "status", 38)]:
    before = json.loads(subprocess.check_output(["git", "show", BASE + ":" + name], cwd=ROOT))
    after = json.loads((ROOT / name).read_text())
    assert len(after[group]) == count
    assert [(x["id"], x[state], x.get("reviewer")) for x in before[group]] == [(x["id"], x[state], x.get("reviewer")) for x in after[group]]
ci = json.loads((ROOT / "verification/github-ci-d385adf3/observation-3/receipt.json").read_text())
assert ci["sourceRevision"] == BASE
assert all(x["status"] == "completed" and x["conclusion"] == "success" for x in ci["workflows"])
assert all(j["skippedSteps"] == 0 for x in ci["workflows"] for j in x["jobs"])
policy = subprocess.run(["python3", "scripts/check-policy.py"], cwd=ROOT, capture_output=True, timeout=90)
(OUT / "policy.stdout").write_bytes(policy.stdout)
(OUT / "policy.stderr").write_bytes(policy.stderr)
assert policy.returncode == 0 and json.loads(policy.stdout)["status"] == "passed"
(OUT / "policy-receipt.json").write_text(json.dumps({
    "argv": ["python3", "scripts/check-policy.py"], "exitCode": 0,
    "scope": "manifest-and-gate-guardrail-only",
    "scriptSHA256": hashlib.sha256((ROOT / "scripts/check-policy.py").read_bytes()).hexdigest(),
    "python": subprocess.check_output(["python3", "--version"], text=True).strip()
}, indent=2) + "\n")
for name in ["prepare.py", "stage.py", "policy.stdout", "policy.stderr", "policy-receipt.json"]:
    add(str((OUT / name).relative_to(ROOT)))
manifest = {
    "schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "baseRevision": BASE, "files": dict(sorted(selected.items())),
    "scope": "Reviewed local transaction prerequisite, CI fixture and ordinary migrations; proposed artifact contract and unselected finite retention model. No domain/HTTP/provider/native/GA acceptance.",
    "previousCI": "Both d385adf3 workflows passed with zero skipped steps.",
    "statesAndReviewersUnchanged": True
}
(OUT / "selection.json").write_text(json.dumps(manifest, indent=2) + "\n")
paths = sorted([*selected, str((OUT / "selection.json").relative_to(ROOT))])
(OUT / "paths.nul").write_bytes(b"".join(os.fsencode(x) + b"\0" for x in paths))
print(json.dumps({"selectedFiles": len(paths), "selectedBytes": sum(x["bytes"] for x in selected.values()), "gateStatesUnchanged": True}))
