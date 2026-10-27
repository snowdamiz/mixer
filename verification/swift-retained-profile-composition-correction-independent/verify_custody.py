"""Closed no-follow custody before any correction member use."""
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parent
PACKET = ROOT.parent / "swift-retained-profile-composition-correction"
EXPECTED = "57591c504fadfb0c22e44e37d6333cab53b8d62e39da14e97f0cdfd2fed455f1"

def read(path):
    here = PACKET
    assert stat.S_ISDIR(here.lstat().st_mode)
    for part in path.relative_to(PACKET).parts[:-1]:
        here /= part
        assert stat.S_ISDIR(here.lstat().st_mode)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode)
        data = bytearray()
        while True:
            block = os.read(fd, 65536)
            if not block: break
            data.extend(block)
        after = os.fstat(fd)
        assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) == (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
        return bytes(data)
    finally:
        os.close(fd)

raw = read(PACKET / "seal.json")
assert hashlib.sha256(raw).hexdigest() == EXPECTED
seal = json.loads(raw)
entries = seal["members"]
assert len(entries) == seal["member_count"] == 476
paths = [entry["path"] for entry in entries]
assert len(paths) == len(set(paths))
for path in paths:
    assert not Path(path).is_absolute()
    assert all(part not in ("", ".", "..") for part in path.split("/"))
actual = set()
for parent, dirs, files in os.walk(PACKET, followlinks=False):
    for name in dirs: assert stat.S_ISDIR((Path(parent) / name).lstat().st_mode)
    for name in files: actual.add((Path(parent) / name).relative_to(PACKET).as_posix())
assert actual == set(paths) | {"seal.json", "seal.sha256"}
sidecar = read(PACKET / "seal.sha256")
assert sidecar == (EXPECTED + "  seal.json\n").encode() and len(sidecar) == 76
for entry in entries:
    data = read(PACKET / entry["path"])
    assert len(data) == entry["bytes"], entry["path"]
    assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["path"]
selection = ROOT.parent / "swift-semantic-adapter-root-review/retained-composition-lifecycle-correction-selection.json"
selection_raw = selection.read_bytes()
(ROOT / "root-selection.json").write_bytes(selection_raw)
(ROOT / "input-custody.json").write_text(json.dumps({"schema": 1, "seal_sha256": EXPECTED, "member_count": len(entries), "members": entries, "exact76_byte_self_seal": True, "root_selection_sha256": hashlib.sha256(selection_raw).hexdigest(), "regular_no_follow_checks": True}, indent=2, sort_keys=True) + "\n")
print(f"verified {len(entries)} closed members plus exact self-seal metadata; {EXPECTED}")
