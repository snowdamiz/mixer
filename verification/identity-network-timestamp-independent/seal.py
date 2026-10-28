#!/usr/bin/env python3
"""Bind the review packet and recheck its immutable input readset."""
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def deny_runtime(event, args):
    if event.startswith(("subprocess.", "socket.", "pty.")) or event in {
        "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.spawn"
    }:
        raise AssertionError("child/socket action denied while sealing: " + event)


sys.addaudithook(deny_runtime)


def binding(body):
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}


readset = json.loads((BASE / "readset.json").read_bytes())
for path, expected in readset["files"].items():
    assert binding((ROOT / path).read_bytes()) == expected, "readset drift: " + path
files = {}
for path in sorted(BASE.rglob("*")):
    if path.is_dir():
        continue
    assert path.is_file() and not path.is_symlink()
    name = str(path.relative_to(BASE))
    if name != "packet-manifest.json":
        files[name] = binding(path.read_bytes())
encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
seal = {
    "schema": 1,
    "packet": hashlib.sha256(encoded).hexdigest(),
    "seal_algorithm": "sha256 of canonical JSON files map; packet-manifest.json excluded",
    "readset_rechecked": True,
    "files": files,
}
(BASE / "packet-manifest.json").write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
print(json.dumps({"packet": seal["packet"], "files": len(files), "readset_rechecked": True}))
