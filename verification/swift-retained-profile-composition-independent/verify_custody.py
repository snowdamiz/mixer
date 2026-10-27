#!/usr/bin/env python3
"""Independently verify exact closed, regular-file-only producer packet."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

BASE = Path(__file__).resolve().parent
PACKET = BASE.parent / "swift-retained-profile-composition-preparation"
EXPECTED_SEAL = "c7a8ead8257b8e13543c4fb3bb3ed385513f83080c960a58333b617d05c44860"

def read_regular(path):
    relative = path.relative_to(PACKET)
    current = PACKET
    assert stat.S_ISDIR(current.lstat().st_mode)
    for component in relative.parts[:-1]:
        current = current / component
        assert stat.S_ISDIR(current.lstat().st_mode), str(current)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode), str(path)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read()
        after = os.fstat(fd)
        assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size,
                                      after.st_mtime_ns, after.st_ctime_ns)
        return data
    finally:
        os.close(fd)

seal_bytes = read_regular(PACKET / "seal.json")
assert hashlib.sha256(seal_bytes).hexdigest() == EXPECTED_SEAL
seal = json.loads(seal_bytes)
assert seal["member_count"] == len(seal["members"]) == 41
paths = [entry["path"] for entry in seal["members"]]
assert len(set(paths)) == len(paths)
for path in paths:
    assert not Path(path).is_absolute()
    assert all(part not in ("", ".", "..") for part in path.split("/"))
actual = set()
for parent, dirs, files in os.walk(PACKET, followlinks=False):
    for name in dirs:
        assert stat.S_ISDIR((Path(parent) / name).lstat().st_mode)
    for name in files:
        relative = (Path(parent) / name).relative_to(PACKET).as_posix()
        actual.add(relative)
assert actual == set(paths) | {"seal.json", "seal.sha256"}, (actual - set(paths), set(paths) - actual)
sidecar = read_regular(PACKET / "seal.sha256")
assert sidecar == (EXPECTED_SEAL + "  seal.json\n").encode("ascii")
observations = []
for entry in seal["members"]:
    data = read_regular(PACKET / entry["path"])
    digest = hashlib.sha256(data).hexdigest()
    assert len(data) == entry["bytes"], entry["path"]
    assert digest == entry["sha256"], entry["path"]
    observations.append({"path": entry["path"], "bytes": len(data), "sha256": digest})
result = {"schema": 1, "seal_sha256": EXPECTED_SEAL, "closed_member_count": len(paths),
          "regular_no_follow_reads": True,
          "seal_metadata": {"seal.sha256": {"bytes": len(sidecar),
                "sha256": hashlib.sha256(sidecar).hexdigest(),
                "selection": "Root explicitly selected exact self-seal sidecar only"}},
          "members": observations}
(BASE / "input-custody.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(f"verified {len(paths)} closed members; seal {EXPECTED_SEAL}")
