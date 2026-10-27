"""Read-only self packet membership/hash check; no test/model import."""
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
seal = json.loads((here / "seal.json").read_bytes())
rows = []
for path in sorted(here.rglob("*")):
    if path.is_file() and path != here / "seal.json":
        raw = path.read_bytes()
        rows.append({"path": str(path.relative_to(here)), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
assert rows == seal["members"]
assert len(rows) == seal["member_count"]
assert sum(row["bytes"] for row in rows) == seal["member_bytes"]
assert hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == seal["tree_sha256"]
print(json.dumps({"status": "own sealed packet intact", "members": len(rows), "seal_sha256": hashlib.sha256((here / "seal.json").read_bytes()).hexdigest()}, sort_keys=True))
