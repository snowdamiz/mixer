#!/usr/bin/env python3
"""Verify this preparation's seal without changing files or checking live state."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


data = (HERE / "seal.json").read_bytes()
seal = json.loads(data)
assert (HERE / "seal.sha256").read_text() == sha(data) + "  seal.json\n"
for item in seal["members"]:
    relative = Path(item["path"])
    assert not relative.is_absolute() and ".." not in relative.parts
    path = HERE / relative
    assert path.is_file() and not path.is_symlink()
    content = path.read_bytes()
    assert len(content) == item["bytes"] and sha(content) == item["sha256"], item["path"]
actual = {str(p.relative_to(HERE)) for p in HERE.rglob("*") if p.is_file()}
assert actual == {x["path"] for x in seal["members"]} | set(seal["excluded"])
assert len(seal["members"]) == seal["member_count"]
assert sum(x["bytes"] for x in seal["members"]) == seal["total_bytes"]
rows = "".join(f"{x['path']}\t{x['bytes']}\t{x['sha256']}\n" for x in seal["members"])
assert sha(rows.encode()) == seal["tree_sha256"]
print(json.dumps({"result": "pass", "members": seal["member_count"], "bytes": seal["total_bytes"],
                  "seal_sha256": sha(data), "scope": "frozen preparation bytes only; no implementation acceptance"}, sort_keys=True))
