#!/usr/bin/env python3
"""Integrate the exact reviewed cumulative startup patch and test live source."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
CANDIDATE = ROOT / "verification/hosted-identity-startup-correction"
REVIEW = ROOT / "verification/hosted-identity-startup-correction-review"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


assert not (OUT / "integration.json").exists(), "one-time collector"
decision = json.loads((OUT / "preintegration-decision.json").read_text())
assert decision["rootReviewed"] and decision["unresolvedFindings"] == []
assert sha(REVIEW / "receipt.json") == decision["reviewReceiptSHA256"]
assert sha(CANDIDATE / "receipt.json") == decision["candidateReceiptSHA256"]
bindings = {}
for name in ["hosted-identity-startup-implementation", "hosted-identity-startup-review", "hosted-identity-startup-correction", "hosted-identity-startup-correction-review"]:
    packet = ROOT / "verification" / name
    receipt = json.loads((packet / "receipt.json").read_text())
    for path, digest in receipt["bindings"].items():
        assert sha(packet / path) == digest, (name, path)
        bindings[str((packet / path).relative_to(ROOT))] = digest
    bindings[str((packet / "receipt.json").relative_to(ROOT))] = sha(packet / "receipt.json")
save("accepted-input-bindings.json", bindings)
candidate = json.loads((CANDIDATE / "receipt.json").read_text())
overlay = json.loads((CANDIDATE / "overlay-manifest.json").read_text())
expected = json.loads((CANDIDATE / "tested-source-manifest.json").read_text())["files"]
assert len(overlay["files"]) == 12 and len(expected) == 69
for path, digest in expected.items():
    if path in overlay["changes"]:
        before = overlay["changes"][path]["baseSHA256"]
        assert (sha(ROOT / path) if (ROOT / path).exists() else None) == before, path
        assert sha(CANDIDATE / "overlay" / path) == digest
    else:
        assert sha(ROOT / path) == digest, path
patch = CANDIDATE / "implementation.patch"
assert sha(patch) == candidate["patchSHA256"]
subprocess.run(["git", "apply", "--check", str(patch)], cwd=ROOT, check=True)
subprocess.run(["git", "apply", str(patch)], cwd=ROOT, check=True)
for path, digest in expected.items():
    assert sha(ROOT / path) == digest, path
save("integrated-source-manifest.json", expected)
args = [sys.executable, "-B", "hosted/scripts/test-local.py", "--output", str(OUT / "integrated-host")]
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
with (OUT / "integrated-host-command.log").open("wb") as stream:
    result = subprocess.run(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
save("integrated-host-command.json", {"argv": args, "cwd": str(ROOT), "pythonVersion": sys.version, "startedUTC": started, "finishedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "exitCode": result.returncode, "outputSHA256": sha(OUT / "integrated-host-command.log"), "sourceDigest": candidate["testedSourceDigest"]})
assert result.returncode == 0
host = json.loads((OUT / "integrated-host/receipt.json").read_text())
assert host["status"] == "passed"
assert host["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
assert len(host["inputs"]) == 62
assert all(expected[path] == digest for path, digest in host["inputs"].items())
assert "Result: 93 passed, 2 skipped" in (OUT / "integrated-host/tests.log").read_text()
assert all(sha(ROOT / path) == digest for path, digest in expected.items())
save("integration.json", {"schema": 1, "status": "reviewed-startup-and-strict-endpoint-fix-integrated", "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "sourceDigest": candidate["testedSourceDigest"], "sourceFiles": len(expected), "hostCollectorInputs": len(host["inputs"]), "appliedFiles": sorted(overlay["files"]), "tests": {"passed": 93, "skipped": 2, "skipReason": "Linux network namespace cases; separate corrected-source Linux producer run passes95 with zero skips"}, "release": "build, expected missing-config exit1 and four test-only export exclusions passed", "cleanup": host["cleanup"], "scope": "Configured application startup and exact inherited endpoint grammar fix; no authenticated HTTP/current membership/provider/Neon/native/physical or GA acceptance."})
print("passed: exact 12-file startup integration; 93 host tests, 2 Linux-only skips, release checks and owned PostgreSQL cleanup")
