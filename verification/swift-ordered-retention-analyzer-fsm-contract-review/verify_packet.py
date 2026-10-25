"""Read-only verification of this review's final immutable member closure."""
import hashlib
import json
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while raw := f.read(65536):
            h.update(raw)
    return h.hexdigest()


def main():
    seal = OWN / "seal.json"
    expected = (OWN / "seal.sha256").read_text().strip()
    assert sha(seal) == expected, "review seal digest mismatch"
    rows = json.loads(seal.read_bytes())["members"]
    seen = set()
    for row in rows:
        rel = Path(row["path"])
        assert not rel.is_absolute() and ".." not in rel.parts
        assert str(rel) not in seen
        seen.add(str(rel))
        assert str(rel) == "docs/swift-ordered-retention-analyzer-fsm-contract-review.md" or str(rel).startswith(str(OWN.relative_to(ROOT)) + "/")
        path = ROOT / rel
        assert stat.S_ISREG(path.lstat().st_mode), str(rel)
        assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], str(rel)
    print(json.dumps({"seal_sha256": expected, "verified_members": len(rows),
                      "verified_bytes": sum(row["bytes"] for row in rows),
                      "mutation_or_execution": False}, sort_keys=True))


if __name__ == "__main__":
    main()
