#!/usr/bin/env python3
"""Bind the independently audited rejection to unchanged retained/live bytes."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SEALS = {
    "verification/swift-cost-retention-candidate/seal.json":
        "a71d7d9b4405b37e2130c464e0e149d82b2a1ff57f9f75f36cc0e8401bb50702",
    "verification/swift-cost-retention-candidate-review/seal.json":
        "0993e18e6aeb41246fe84dbfacaf74d8068286857dbbc5824b30e93e5f6da676",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


bindings = {}
for name, expected in SEALS.items():
    path = ROOT / name
    assert digest(path) == expected
    packet = json.loads(path.read_text())
    for member, entry in packet["members"].items():
        p = path.parent / member
        assert p.resolve().is_relative_to(path.parent.resolve()) and not p.is_symlink()
        assert p.stat().st_size == entry["bytes"] and digest(p) == entry["sha256"]
        bindings[str(p.relative_to(ROOT))] = entry["sha256"]
    doc = ROOT / packet.get("docPath", "docs/swift-cost-retention-candidate.md")
    assert digest(doc) == packet["docSHA256"]
    bindings[str(doc.relative_to(ROOT))] = packet["docSHA256"]

review = json.loads((ROOT / "verification/swift-cost-retention-candidate-review/stdout.json").read_text())
assert review["verdict"] == "accept-recorded-rejection" and not review["findings"]
assert len(review["pairedRawTraces"]) == 6
assert all(x["candidate"]["traceWork"] > x["baseline"]["traceWork"] for x in review["pairedRawTraces"])
manifest = ROOT / "verification/swift-cost-retention-candidate/live-baseline-source-manifest.json"
assert digest(manifest) == "16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd"
live = json.loads(manifest.read_text())
assert len(live) == 132
assert all(digest(ROOT / "vm" / name) == expected for name, expected in live.items())
assert not (ROOT / "verification/swift-cost-retention-candidate/.scratch").exists()
assert review["cleanup"]["historicalReceipt"]["removed"]
receipt = {"schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "command": [sys.executable, str(Path(__file__).resolve())], "python": sys.version,
           "verifierSHA256": digest(Path(__file__)), "seals": SEALS,
           "verifiedBindings": len(bindings), "bindings": bindings,
           "liveClosureFiles": len(live), "liveClosureUnchanged": True,
           "decision": "Reject integration and full-target selection based on all six finite work regressions.",
           "scope": "Accept retained rejection evidence only; no candidate correctness, full-workload or GA pass."}
assert not (OUT / "acceptance.json").exists()
(OUT / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"verifiedBindings": len(bindings), "liveFiles": len(live), "decision": "reject"}))
