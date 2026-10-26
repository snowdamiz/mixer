#!/usr/bin/env python3
"""Manifest this new source-only packet. Never mutate an older packet."""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
files = []
for path in sorted(HERE.rglob("*")):
    if path.is_file() and path.name != "seal.json":
        data = path.read_bytes()
        files.append({"path": str(path.relative_to(HERE)), "bytes": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})
value = {"schema": 1, "scope": "Exact row-probe source G5 necessary obstruction only",
         "source_sha256": "a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1",
         "members": files, "member_count": len(files), "total_bytes": sum(f["bytes"] for f in files)}
seal = HERE / "seal.json"
if "--verify" in sys.argv:
    if json.loads(seal.read_text()) != value:
        raise ValueError("frozen packet differs from manifest")
else:
    seal.write_text(json.dumps(value, indent=2, sort_keys=True)+"\n")
print(json.dumps({"member_count": value["member_count"], "total_bytes": value["total_bytes"],
                  "seal_sha256": hashlib.sha256(seal.read_bytes()).hexdigest(),
                  "verified": "--verify" in sys.argv}, sort_keys=True))
