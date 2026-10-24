#!/usr/bin/env python3
"""Select correction requirements from frozen independent PostgreSQL evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert not (OUT / "correction-selection.json").exists()
checks = []
for packet in ["hosted-atomic-storage-preflight", "hosted-atomic-storage-review"]:
    args = [sys.executable, "-B", f"verification/{packet}/check.py"]
    result = subprocess.run(args, cwd=ROOT, capture_output=True)
    output = OUT / (packet + "-selection-check.log")
    output.write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0
    checks.append({"argv": args, "exitCode": result.returncode, "output": str(output.relative_to(ROOT)), "outputSHA256": sha(output)})
files = [
    "docs/hosted-atomic-storage-preflight.md",
    "docs/hosted-atomic-storage-review.md",
    "docs/hosted-atomic-storage-corrections.md",
    "verification/hosted-atomic-storage-preflight/receipt.json",
    "verification/hosted-atomic-storage-review/receipt.json",
    "verification/hosted-atomic-storage-review/run-3/receipt.json",
    "verification/hosted-atomic-storage-preflight/contract-manifest.json",
]
value = {
    "schema": 1,
    "status": "mechanics-evidence-reviewed-corrections-required-before-repository-acceptance",
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "observedHEAD": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "pythonVersion": sys.version,
    "producer": {"cases": 41, "bindings": 239, "sourceDigest": "0f72c5b18c333f74b27f58ff17707fc909175a0c9ea4cf974c3015fb65007d7e"},
    "review": {"cases": 61, "independentCases": 20, "bindings": 134, "sourceDigest": "82279360945406d1fa4bce8391a81a4bd1eb4f6b5c081f75e1f4a633c810c79d", "gapReproductionsAreNotSecurityPasses": True},
    "selectedCorrectionContract": "docs/hosted-atomic-storage-corrections.md",
    "requiredGroups": [f"AS{i:02d}" for i in range(1, 8)],
    "checks": checks,
    "bindings": {name: sha(ROOT / name) for name in files},
    "fullTypedValidationAccepted": False,
    "repositoryAccepted": False,
    "migrationApplied": False,
    "gaAcceptance": False,
    "scope": "Root selects bounded corrections after manual source/contract review and frozen evidence verification. No new PostgreSQL execution claimed. Original failure/gap evidence preserved; next isolated corrected specimen and independent review required.",
}
(OUT / "correction-selection.json").write_text(json.dumps(value, indent=2) + "\n")
print(value["status"])
