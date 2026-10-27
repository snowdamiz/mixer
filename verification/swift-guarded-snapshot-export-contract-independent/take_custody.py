#!/usr/bin/env python3
"""Take an immutable candidate copy only after root released its seal."""
import hashlib
import json
import pathlib
import shutil
from datetime import datetime, timezone

OWN = pathlib.Path(__file__).resolve().parent
REPO = OWN.parents[1]
SOURCE = REPO / "verification/swift-guarded-snapshot-export-preparation"
DEST = OWN / "candidate"
EXPECTED = "7787c8bbd9164ebdd360186f79c5d696739e89d6b08cd2f7cfbc71e9c156a1fe"

def identity(path, name):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def verify(root):
    seal = identity(root / "seal.json", "seal.json")
    assert seal["sha256"] == EXPECTED
    value = json.loads((root / "seal.json").read_text())
    paths = sorted(root.rglob("*"))
    assert not any(p.is_symlink() for p in paths)
    members = [identity(p, p.relative_to(root).as_posix()) for p in paths if p.is_file() and p != root / "seal.json"]
    assert members == value["members"]
    assert len(members) == value["member_count"] == 639
    assert sum(m["bytes"] for m in members) == value["bytes"] == 22970241
    digest = hashlib.sha256(json.dumps(members, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == value["tree_sha256"] == "659a65c7ed097bf2825b9f54509825ac4a966215376cb1fc291fb89644304bd9"
    return {"seal": seal, "members": len(members), "bytes": value["bytes"], "tree_sha256": digest}

assert not DEST.exists()
freeze = identity(OWN / "preaccess-freeze.json", "preaccess-freeze.json")
assert freeze["sha256"] == "716d8c93a5f5dd3ee7e0b5caafb1848e1c4697e2e21a03a77f5ded6ddab4a893"
before = verify(SOURCE)
shutil.copytree(SOURCE, DEST)
copied = verify(DEST)
assert before == copied
value = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
         "root_release": "Root explicitly released seal 7787c8... after independent freeze; message retained in root conversation.",
         "preaccess_freeze": freeze, "original": before, "owned_copy": copied,
         "producer_wrapper_replayed": False, "candidate_copy_path": str(DEST.relative_to(REPO))}
(OWN / "candidate-custody.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
print(json.dumps(value, sort_keys=True))
