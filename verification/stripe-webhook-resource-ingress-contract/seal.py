#!/usr/bin/env python3
"""Seal authored packet and retain contract checker output; no runtime harness."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHECKS = HERE / "contract-checks.json"
CHECKS.write_text("{}\n")


def seal():
    paths = [p for p in HERE.rglob("*") if p.is_file() and p.name != "seal.json"]
    paths.append(ROOT / "docs/stripe-webhook-resource-ingress-contract.md")
    bindings = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    (HERE / "seal.json").write_text(json.dumps({"schema": 1, "scope": "proposal packet only; no runtime behavior",
                                               "files": bindings}, indent=2, sort_keys=True) + "\n")


receipt_path = HERE / "authoring-receipt.json"
receipt = json.loads(receipt_path.read_text())
receipt["status"] = "authored-contract-verification-pending"
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
seal()
argv = [sys.executable, "-B", str(HERE / "verify.py"), "--live"]
run = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=30)
CHECKS.write_text(json.dumps({"argv": argv, "cwd": str(ROOT), "exitCode": run.returncode,
                            "stdout": run.stdout, "stderr": run.stderr,
                            "scope": "contract/evidence validation only; zero runtime cases"}, indent=2, sort_keys=True) + "\n")
receipt["status"] = "passed-contract-and-evidence-checks-only" if run.returncode == 0 else "failed-contract-checks"
receipt["contractCheckCommand"] = argv
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
seal()
print(run.stdout, end="")
if run.stderr:
    print(run.stderr, file=sys.stderr, end="")
raise SystemExit(run.returncode)
