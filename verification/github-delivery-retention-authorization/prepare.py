#!/usr/bin/env python3
"""Exact reviewed delivery allowlist; no staging or Git publication here."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "b375e55ded9e3e10c327891ab681beff2a471e26"
SEALS = {
    "verification/swift-retention-runtime-review/seal.json": "546c7f39a85c40e48449faf35b8facb9f4ad3966c2bd3c6246ddb5c308a684f3",
    "verification/hosted-customer-authorization/seal.json": "9f8c9019b00fb0e3190362b3ed142ebe0bcc64bed59593b76c61860da803b97b",
    "verification/hosted-customer-authorization-review/seal.json": "5095744f44f7155ae2d4210dd6e50a0fc1bae73a8a09fbbafc8b75fe30982a7b",
    "verification/hosted-customer-authorization-correction/seal.json": "f4e57c20a9bde0a9d3066fb93594a7038d05e54dc8a22b106d369d7aee2cef4e",
    "verification/hosted-customer-authorization-correction-review/seal.json": "2896eab29c748fa65513c3596028db5e0ceef6f61723fa3b402e4e95ad038b51",
    "verification/swift-cache-retention-candidate/seal.json": "6507e85f869d0f1a052b9e8e5356ac07910c67813f87b309fa6a5b348e803c13",
    "verification/swift-cache-retention-review/seal.json": "0d9c15a69baff78ff097f50c0fa8edaa402a6147811742407bdb76fd04c1868f",
    "verification/swift-retention-target-preparation/prepared-seal.json": "1411f9d65c9e74193707378e044436a2152f451b41b6ac86429cf1a362ca4bea",
    "verification/swift-retention-target-preparation-review/seal.json": "30e79244baaa28432e976fba2d6d396827d0dec12941e02ab4c35c0800f5c60b",
    "verification/swift-retention-runtime/seal.json": "e2fe9807c8ff83d1bea08f62b1504e7b50b9e9801af24ca57beb766398f97e64",
}
selected = {}


def add(path, expected=None):
    p = ROOT / path
    assert p.resolve().is_relative_to(ROOT)
    assert not any(x in str(p) for x in ["hosted-catalog-inspector", "hosted-authority-driver", "outbound-worker-transport-v2"])
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size < 100_000_000, path
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    if expected is not None:
        assert digest == expected, (path, digest, expected)
    selected[str(p.relative_to(ROOT))] = {"sha256": digest, "bytes": s.st_size}


assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == BASE
assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True).strip()
for path, expected in SEALS.items():
    add(path, expected)
    p = ROOT / path
    packet = json.loads(p.read_text())
    entries = packet.get("entries", packet.get("files"))
    if isinstance(entries, list):
        for member in entries:
            # The earlier rejected producer source is retained in exact run-3 snapshots.
            historical = (path == "verification/hosted-customer-authorization/seal.json"
                          and member["path"] in ["hosted/lib/mixer_hosted/authorization/policy.ex",
                            "hosted/lib/mixer_hosted/authorization/repository.ex",
                            "hosted/test/mixer_hosted/authorization/policy_test.exs"])
            name = ("verification/hosted-customer-authorization/run-3/inputs/" + member["path"]
                    if historical else member["path"])
            add(name, member["sha256"])
    else:
        for name, digest in packet.get("members", packet.get("files", {})).items():
            add(str((p.parent / name).relative_to(ROOT)), digest)
        for name, digest in packet.get("externalMembers", packet.get("externalFiles", {})).items():
            add(name, digest)

for name in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json",
             "verification/customer-authorization-policy-root-selection/selection.json",
             "verification/hosted-customer-authorization-root-acceptance/acceptance.json",
             "verification/swift-retention-runtime-root-acceptance/acceptance.json"]:
    add(name)

prior_delivery = "verification/github-delivery-diagnostic-corrections/"
for name in ["delivery-receipt.json", "push.stdout", "push.stderr", "ci-first-observation.json",
             "ci-latest.json", "ci-latest-receipt.json", "ci-current-observation.json", "ci-terminal-receipt.json"]:
    add(prior_delivery + name)
prep = ROOT / "verification/swift-retention-target-preparation"
for name in ["root-selection.json", "target-attempt-started.json", "target-once-events.json", "target-once-result.json"]:
    add(str((prep / name).relative_to(ROOT)))
for p in sorted((prep / "commands/target-once").iterdir()):
    add(str(p.relative_to(ROOT)))
for name, key, field, count in [("work-graph.json", "packages", "state", 18), ("gates/ga.json", "gates", "status", 38)]:
    prior = json.loads(subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT, text=True))
    now = json.loads((ROOT / name).read_text())
    assert len(now[key]) == count
    assert [(x["id"], x[field], x.get("reviewer")) for x in prior[key]] == [(x["id"], x[field], x.get("reviewer")) for x in now[key]]
assert len(json.loads((ROOT / "dogfood/receipts/milestones.json").read_text())["milestones"]) == 9
ci = json.loads((ROOT / prior_delivery / "ci-terminal-receipt.json").read_text())
assert ci["conclusion"] == "success" and ci["head_sha"] == BASE and ci["skipped_steps"] == 0
add(str(Path(__file__).relative_to(ROOT)))
manifest = {"schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "baseRevision": BASE, "seals": SEALS, "files": dict(sorted(selected.items())),
            "scope": "Reviewed pure customer authorization and original failed review; isolated rejected cache candidate and audited same-budget failure. Live VM unchanged; all gate states/reviewers unchanged."}
(OUT / "selection.json").write_text(json.dumps(manifest, indent=2) + "\n")
paths = sorted([*selected, str((OUT / "selection.json").relative_to(ROOT))])
(OUT / "paths.nul").write_bytes(b"".join(os.fsencode(x) + b"\0" for x in paths))
print(json.dumps({"selectedFiles": len(paths), "selectedBytes": sum(x["bytes"] for x in selected.values()),
                  "sealedPackets": len(SEALS), "gateStatesUnchanged": True, "liveVMUnchanged": True}))
