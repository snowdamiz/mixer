#!/usr/bin/env python3
"""Audit and replay the finite proposal; do not select a VM implementation."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / "verification/swift-adaptive-retention-design"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not (OUT / "acceptance.json").exists()
seal = json.loads((PACKET / "seal.json").read_text())
assert len(seal["members"]) == 8
for member in seal["members"]:
    p = ROOT / member["path"]
    assert p.resolve().is_relative_to(ROOT) and not p.is_symlink()
    assert p.stat().st_size == member["bytes"] and digest(p) == member["sha256"]
for member in json.loads((PACKET / "source-manifest.json").read_text()):
    assert digest(ROOT / member["path"]) == member["sha256"]
manifest = ROOT / "verification/swift-cost-retention-candidate/live-baseline-source-manifest.json"
assert digest(manifest) == "16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd"
live = json.loads(manifest.read_text())
assert len(live) == 132
assert all(digest(ROOT / "vm" / n) == h for n, h in live.items())
console = ROOT / "verification/console-build-overview-root-review/final-source-manifest.json"
console_files = json.loads(console.read_text())["files"]
assert len(console_files) == 40
assert all(digest(ROOT / n) == h for n, h in console_files.items())
argv = [sys.executable, str(PACKET / "model.py")]
result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
(OUT / "model.stdout").write_bytes(result.stdout)
(OUT / "model.stderr").write_bytes(result.stderr)
assert result.returncode == 0
observed = json.loads(result.stdout)
assert observed == json.loads((PACKET / "stdout.json").read_text())
assert observed["checks_passed"] == 17 and len(observed["traces"]) == 7
receipt = {
    "schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "sourceRevision": "d385adf3dd110da44ba290a7221278c48e39b882",
    "verifierSHA256": digest(Path(__file__)), "python": sys.version,
    "sealSHA256": digest(PACKET / "seal.json"), "sealedMembers": 8,
    "command": argv, "exitCode": result.returncode,
    "stdoutSHA256": digest(OUT / "model.stdout"), "stderrSHA256": digest(OUT / "model.stderr"),
    "modelControls": 17, "modelSequences": 7, "exactModelReplay": True,
    "liveVMClosureFiles": 132, "liveVMUnchanged": True,
    "consoleSourceBindings": 40, "consoleUnchanged": True,
    "decision": "Withhold candidate implementation selection. Retain the model proposal only.",
    "reason": "The model trades fewer decodes on some traces for added per-hit/miss work and more phase-change misses; VM benefit is unproved.",
    "scope": "Root packet integrity/replay and unchanged-source audit; no new VM correctness/performance, full-target, browser/native or GA acceptance."
}
(OUT / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({k: receipt[k] for k in ["sealedMembers", "modelControls", "modelSequences", "liveVMUnchanged", "consoleUnchanged", "decision"]}))
