"""Verify immutable candidate/input custody before any replay/import."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PACKETS = {
    "candidate": ("swift-retained-profile-composition-stdio-correction", "01fde6f81a88a35fe734f66991324e2518967e2890a8485cf13a679fd01eeeb2"),
    "prior": ("swift-retained-profile-composition-correction", "57591c504fadfb0c22e44e37d6333cab53b8d62e39da14e97f0cdfd2fed455f1"),
    "prior_independent": ("swift-retained-profile-composition-correction-independent", "108faabdd9e9fdb0037f0fd59863a9782073effaea956753d0c76fed7698b6d3"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    output = {"schema": 1, "packets": {}}
    for key, (name, expected) in PACKETS.items():
        base = REPO / "verification" / name
        raw = (base / "seal.json").read_bytes()
        assert sha(raw) == expected
        seal = json.loads(raw)
        seen = set()
        total = 0
        for member in seal["members"]:
            relative = Path(member["path"])
            assert not relative.is_absolute() and ".." not in relative.parts
            assert str(relative) not in seen
            seen.add(str(relative))
            file = base / relative
            assert file.is_file() and not file.is_symlink()
            data = file.read_bytes()
            assert len(data) == member["bytes"] and sha(data) == member["sha256"]
            total += len(data)
        assert len(seen) == seal["member_count"]
        assert (base / "seal.sha256").read_bytes() == (expected + "  seal.json\n").encode()
        actual = {str(x.relative_to(base)) for x in base.rglob("*") if x.is_file()}
        assert actual == seen | {"seal.json", "seal.sha256"}
        output["packets"][key] = {"path": str(base.relative_to(REPO)), "seal_sha256": expected, "members": len(seen), "member_bytes": total, "self_seal_bytes": 76, "exact_directory_coverage": True}
    selection = REPO / "verification/swift-semantic-adapter-root-review/retained-composition-stdio-correction-selection.json"
    raw = selection.read_bytes()
    assert sha(raw) == "43de06ff9abc96057c2e89aff5e842de81c8419eb92f1ea6a6db13f0486ab911"
    output["selection"] = {"path": str(selection.relative_to(REPO)), "bytes": len(raw), "sha256": sha(raw)}
    candidate = REPO / output["packets"]["candidate"]["path"]
    receipt = json.loads((candidate / "receipt.json").read_text())
    entries = receipt["source_entries"]
    for entry in entries:
        data = (candidate / entry["path"]).read_bytes()
        assert len(data) == entry["bytes"] and sha(data) == entry["sha256"]
    preimage = b"retained-profile-stdio-correction-source-v1\n" + b"".join((e["path"] + "\0" + str(e["bytes"]) + "\0" + e["sha256"] + "\n").encode() for e in entries)
    assert sha(preimage) == receipt["source_tree_sha256"] == "0f7e29d6c7224f2b390bfd586d7e5f4b35cb892624e064910e24a6f844636074"
    output["candidate_source_tree_sha256"] = sha(preimage)
    return output


if __name__ == "__main__":
    observed = verify()
    (ROOT / "input-custody.json").write_text(json.dumps(observed, indent=2, sort_keys=True) + "\n")
    print(json.dumps(observed, sort_keys=True))
