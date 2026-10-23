#!/usr/bin/env python3
"""Check the retained evidence set against the completed receipt."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
receipt = json.loads((ROOT / "receipt.json").read_text())
entries = receipt["artifacts"]
assert hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == receipt["artifactCollectionSHA256"]
actual = set()
for path in ROOT.rglob("*"):
    relative = path.relative_to(ROOT)
    if path.is_file() and relative.parts[0] != "build" and relative.name != "receipt.json" and "xcuserdata" not in relative.parts:
        actual.add(str(relative))
assert actual == {e["path"] for e in entries}, "Evidence file set changed after sealing"
for entry in entries:
    path = ROOT / entry["path"]
    assert path.stat().st_size == entry["bytes"], entry["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], entry["path"]
print(f"PASS: sealed {len(entries)} retained artifacts; collection {receipt['artifactCollectionSHA256']}")
print("Receipt SHA-256: " + hashlib.sha256((ROOT / "receipt.json").read_bytes()).hexdigest())
