"""Copy an exact root-specified producer freeze after immutable preparation."""
import datetime
import hashlib
import json
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
PRODUCER = "verification/swift-ordered-retention-analyzer-fsm-contract"
EXPECTED = "a8cf795a8226fed9facf654b05d0ef6cf7146a289eb3c8df8946c5306f9b73b6"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("nonregular " + str(path))
    return path.read_bytes()


def main():
    prep = regular(OWN / "preparation-seal.json")
    assert digest(prep) == "316040e19aa5d029ef1d885d59ba23f6557debce719f9f79125a227718250649"
    for r in json.loads(prep)["members"]:
        raw = regular(ROOT / r["path"])
        assert len(raw) == r["bytes"] and digest(raw) == r["sha256"], r["path"]
    at = datetime.datetime.now(datetime.UTC).isoformat()
    seal_raw = regular(ROOT / PRODUCER / "seal.json")
    assert digest(seal_raw) == EXPECTED
    seal = json.loads(seal_raw)
    assert len(seal["members"]) == 137
    snapshot = OWN / "producer-freeze-1" / "repository"
    snapshot.mkdir(parents=True, exist_ok=False)
    seen = set()
    for row in seal["members"]:
        rel = Path(row["path"])
        assert not rel.is_absolute() and ".." not in rel.parts and str(rel) not in seen
        seen.add(str(rel))
        assert str(rel) == "docs/swift-ordered-retention-analyzer-fsm-contract.md" or str(rel).startswith(PRODUCER + "/")
        raw = regular(ROOT / rel)
        assert len(raw) == row["bytes"] and digest(raw) == row["sha256"], str(rel)
        destination = snapshot / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    for name in ("seal.json", "seal.sha256"):
        destination = snapshot / PRODUCER / name
        destination.write_bytes(regular(ROOT / PRODUCER / name))
    receipt = {"schema": 1, "started_at": at,
               "finished_at": datetime.datetime.now(datetime.UTC).isoformat(),
               "preparation_seal_sha256": digest(prep),
               "producer_seal_sha256": EXPECTED, "members": len(seen),
               "bytes": sum(r["bytes"] for r in seal["members"]),
               "source_tree_sha256": digest(json.dumps(seal["members"], sort_keys=True, separators=(",", ":")).encode()),
               "snapshot": str(snapshot.relative_to(ROOT)),
               "executed_or_imported": False}
    (OWN / "producer-preflight-1.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    print("\n".join(r["path"] for r in seal["members"] if "/inputs/" not in r["path"]))


if __name__ == "__main__":
    main()
