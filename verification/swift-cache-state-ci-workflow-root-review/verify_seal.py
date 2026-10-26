#!/usr/bin/env python3
"""Verify this workflow proposal's exact frozen roster and file bytes."""
import hashlib
import json
from pathlib import Path


here = Path(__file__).resolve().parent
seal = json.loads((here / "seal.json").read_text())
actual = {}
for path in sorted(here.rglob("*")):
    if path.is_symlink():
        raise SystemExit(f"Refused symlink: {path.relative_to(here)}")
    if path.is_file() and path != here / "seal.json":
        data = path.read_bytes()
        actual[path.relative_to(here).as_posix()] = {
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        }
if actual != seal["files"]:
    raise SystemExit("Workflow proposal seal mismatch")
print(f"Verified {len(actual)} exact workflow proposal files; scope remains preparation only.")
