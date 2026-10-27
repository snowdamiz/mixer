"""Read-only selective custody of released frozen data. Never executes archives."""
import hashlib
import json
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
ARCHIVE = REPO / "verification/android-editor-membership-compiled-boundary-qualification/selected-v4-composed-replay-review"
SEAL_SHA = "c06e384c26568f50be149a819bdf08259c03ab3e65ce867f1dc8477933bf8423"
RUN33 = "reference-tree/verification/android-editor-membership-compiled-boundary-qualification/state-qualification/full-candidate-v1/run-33/"
STATE = "reference-tree/verification/android-editor-membership-compiled-boundary-qualification/state-qualification/"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _sealed_members():
    raw = (ARCHIVE / "seal.json").read_bytes()
    assert digest(raw) == SEAL_SHA, "archive seal changed"
    seal = json.loads(raw)
    assert len(seal["members"]) == 3339
    return {m["path"]: m for m in seal["members"]}


def read(member):
    name = PurePosixPath(member)
    assert not name.is_absolute() and ".." not in name.parts
    assert str(name) == member and member in _sealed_members()
    current = ARCHIVE
    for part in name.parts:
        current = current / part
        assert not current.is_symlink(), "symlink member or ancestor"
    assert current.is_file() and current.resolve().is_relative_to(ARCHIVE.resolve())
    raw = current.read_bytes()
    expected = _sealed_members()[member]
    assert len(raw) == expected["bytes"] and digest(raw) == expected["sha256"], member
    record_path = OWN / "selected-inputs.json"
    records = json.loads(record_path.read_text()) if record_path.exists() else {}
    records[member] = expected
    record_path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
    return raw


def json_member(member):
    return json.loads(read(member))
