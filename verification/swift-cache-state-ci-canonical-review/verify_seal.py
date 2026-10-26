#!/usr/bin/env python3
"""Verify the frozen canonical relocation review without running its checks."""
from pathlib import Path
import hashlib
import json

here = Path(__file__).resolve().parent
seal = json.loads((here / "seal.json").read_text())
actual = []
for path in sorted(here.rglob("*")):
    if path.is_symlink():
        raise SystemExit("Refused symlink: " + str(path.relative_to(here)))
    if path.is_file() and path != here / "seal.json":
        data = path.read_bytes()
        actual.append({"path": path.relative_to(here).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
if actual != seal["members"]:
    raise SystemExit("Canonical relocation review seal mismatch")
print(f"Verified {len(actual)} exact review members; no checks or runner executed.")
