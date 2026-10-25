"""Snapshot the root-specified amended freeze; preserve initial evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
PRODUCER = "verification/swift-ordered-retention-analyzer-fsm-contract"
EXPECTED = "bde96e5f4f1b0ad5bc6366fee79a47f7a375247959191b206d8e7799ed4da193"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(p):
    assert stat.S_ISREG(p.lstat().st_mode), str(p)
    return p.read_bytes()


def main():
    for name, expected in (
        ("preparation-seal.json", "316040e19aa5d029ef1d885d59ba23f6557debce719f9f79125a227718250649"),
        ("findings-freeze1-seal.json", "31460ea35508acfc5b0093f5f32874b1baa69f4377285ce4060c503f98d765e6"),
    ):
        raw = regular(OWN / name)
        assert digest(raw) == expected
        for row in json.loads(raw)["members"]:
            content = regular(ROOT / row["path"])
            assert len(content) == row["bytes"] and digest(content) == row["sha256"], row["path"]
    at = datetime.datetime.now(datetime.UTC).isoformat()
    raw = regular(ROOT / PRODUCER / "seal.json")
    assert digest(raw) == EXPECTED
    rows = json.loads(raw)["members"]
    assert len(rows) == 245 and sum(r["bytes"] for r in rows) == 10117781
    target = OWN / "producer-freeze-2" / "repository"
    target.mkdir(parents=True, exist_ok=False)
    seen = set()
    for row in rows:
        rel = Path(row["path"])
        assert not rel.is_absolute() and ".." not in rel.parts and str(rel) not in seen
        seen.add(str(rel))
        assert str(rel) == "docs/swift-ordered-retention-analyzer-fsm-contract.md" or str(rel).startswith(PRODUCER + "/")
        content = regular(ROOT / rel)
        assert len(content) == row["bytes"] and digest(content) == row["sha256"], str(rel)
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    for name in ("seal.json", "seal.sha256"):
        (target / PRODUCER / name).write_bytes(regular(ROOT / PRODUCER / name))
    receipt = {"schema": 1, "started_at": at,
               "finished_at": datetime.datetime.now(datetime.UTC).isoformat(),
               "producer_seal_sha256": EXPECTED, "members": len(rows),
               "bytes": sum(r["bytes"] for r in rows),
               "source_tree_sha256": digest(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()),
               "preserved_preparation_and_findings_verified": True,
               "snapshot": str(target.relative_to(ROOT)), "executed_or_imported": False}
    (OWN / "producer-preflight-2.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
