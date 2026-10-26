#!/usr/bin/env python3
"""Freeze only this lane's preparation files, after offline consistency checks."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


if (HERE / "seal.json").exists() or (HERE / "seal.sha256").exists():
    raise SystemExit("frozen packet: refusing to overwrite")
assert json.loads((HERE / "preparation-check-receipt.json").read_text())["exit"] == 0
members = []
for path in sorted(HERE.rglob("*")):
    assert not path.is_symlink(), path
    if path.is_file():
        data = path.read_bytes()
        members.append({"path": str(path.relative_to(HERE)), "bytes": len(data), "sha256": sha(data)})
rows = "".join(f"{x['path']}\t{x['bytes']}\t{x['sha256']}\n" for x in members)
seal = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Read-only next-integration preparation; source snapshots and proposal only",
        "member_count": len(members), "total_bytes": sum(x["bytes"] for x in members),
        "tree_sha256": sha(rows.encode()), "members": members,
        "excluded": ["seal.json", "seal.sha256"],
        "product_implementation_or_gate_accepted": False}
data = (json.dumps(seal, indent=2, sort_keys=True) + "\n").encode()
(HERE / "seal.json").write_bytes(data)
(HERE / "seal.sha256").write_text(sha(data) + "  seal.json\n")
print(json.dumps({"members": len(members), "bytes": seal["total_bytes"],
                  "seal_sha256": sha(data), "tree_sha256": seal["tree_sha256"]}, sort_keys=True))
