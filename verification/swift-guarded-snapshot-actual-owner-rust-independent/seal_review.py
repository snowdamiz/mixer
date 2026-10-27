"""Author packet seal after all owned command receipts are terminal."""
import datetime
import hashlib
import json
from pathlib import Path
import stat

HERE = Path(__file__).resolve().parent
assert not (HERE / "seal.json").exists()
rows = []
for path in sorted(HERE.rglob("*")):
    if path.is_file():
        data = path.read_bytes()
        rows.append({"path": str(path.relative_to(HERE)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
seal = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "frozen-independent-review-returned-for-IR01", "member_count": len(rows), "member_bytes": sum(r["bytes"] for r in rows), "tree_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "members": rows, "candidate_accepted": False, "native_or_GA_acceptance": False, "all_owned_commands_terminal": True, "compiler_lane_released": True}
data = (json.dumps(seal, indent=2, sort_keys=True)+"\n").encode()
(HERE / "seal.json").write_bytes(data)
for path in HERE.rglob("*"):
    if path.is_file():
        path.chmod(path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
print(json.dumps({"seal_sha256": hashlib.sha256(data).hexdigest(), "member_count": seal["member_count"], "member_bytes": seal["member_bytes"], "tree_sha256": seal["tree_sha256"], "candidate_accepted": False}, sort_keys=True))
