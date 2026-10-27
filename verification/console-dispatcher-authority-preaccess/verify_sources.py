#!/usr/bin/env python3
"""Offline byte integrity only; imports no product and starts no child process."""
import hashlib
import json
from pathlib import Path


def main():
    packet = Path(__file__).resolve().parent
    root = packet.parent.parent
    manifest = json.loads((packet / "source-manifest.json").read_text())
    mismatches = []
    for item in manifest["inputs"]:
        path = root / item["path"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != item["sha256"]:
            mismatches.append(item["path"])
    print(json.dumps({
        "status": "passed" if not mismatches else "failed",
        "scope": "offline selected input byte integrity only; no runtime authority proven",
        "checked": len(manifest["inputs"]),
        "mismatches": mismatches,
    }, sort_keys=True))
    return bool(mismatches)


if __name__ == "__main__":
    raise SystemExit(main())
