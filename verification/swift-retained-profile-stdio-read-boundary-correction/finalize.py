"""Seal only this completed owned correction; no test or authoring replay."""
from pathlib import Path
import hashlib
import json

D = Path(__file__).resolve().parent
assert not (D / "seal.json").exists()
receipt = json.loads((D / "receipt.json").read_text())
assert receipt["commands"] == 90 and receipt["owned_scratch_empty"]
members = []
for path in sorted(D.rglob("*")):
    assert not path.is_symlink()
    if path.is_file():
        assert "__pycache__" not in path.parts
        raw = path.read_bytes()
        members.append({"path": path.relative_to(D).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
seal = {"schema": 1, "status": "isolated-R03-read-completion-correction-independent-review-pending",
        "members": members, "member_count": len(members), "member_bytes": sum(row["bytes"] for row in members),
        "source_delta": "One post-loop completion check; no limit or cleanup changes",
        "canonical_real_binding_native_OTA_GA_accepted": False}
(D / "seal.json").write_text(json.dumps(seal, indent=2) + "\n")
for member in members:
    raw = (D / member["path"]).read_bytes()
    assert len(raw) == member["bytes"] and hashlib.sha256(raw).hexdigest() == member["sha256"]
assert {p.relative_to(D).as_posix() for p in D.rglob("*") if p.is_file()} == {row["path"] for row in members} | {"seal.json"}
print(json.dumps({"seal_sha256": hashlib.sha256((D / "seal.json").read_bytes()).hexdigest(), "members": len(members), "bytes": seal["member_bytes"]}))
