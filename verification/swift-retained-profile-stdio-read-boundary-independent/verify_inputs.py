"""Independent exact-member custody; honor each packet's actual seal schema."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PACKETS = {
    "correction": ("swift-retained-profile-stdio-read-boundary-correction", "c79bd64dc0019c17f03b17df0a6bd5dc8879334d64fbf74f92507d75a5e81f54", 201, 757707, False),
    "original_candidate": ("swift-retained-profile-composition-stdio-correction", "01fde6f81a88a35fe734f66991324e2518967e2890a8485cf13a679fd01eeeb2", 659, 2590057, True),
    "original_independent": ("swift-retained-profile-composition-stdio-independent", "af9f20a00000cdbac6f772e19088e0c9ce078530386cb62d41d693954b832040", 340, 1177321, True),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify():
    records = {}
    for key, (name, expected, expected_count, expected_bytes, sidecar) in PACKETS.items():
        base = REPO / "verification" / name
        raw = (base / "seal.json").read_bytes()
        assert sha(raw) == expected
        seal = json.loads(raw)
        paths = set()
        total = 0
        for member in seal["members"]:
            relative = Path(member["path"])
            assert not relative.is_absolute() and ".." not in relative.parts and str(relative) not in paths
            paths.add(str(relative))
            file = base / relative
            assert file.is_file() and not file.is_symlink()
            data = file.read_bytes()
            assert len(data) == member["bytes"] and sha(data) == member["sha256"]
            total += len(data)
        assert len(paths) == seal["member_count"] == expected_count and total == expected_bytes
        allowed = paths | {"seal.json"}
        if sidecar:
            assert (base / "seal.sha256").read_bytes() == (expected + "  seal.json\n").encode()
            allowed.add("seal.sha256")
        assert {str(file.relative_to(base)) for file in base.rglob("*") if file.is_file()} == allowed
        records[key] = {"path": str(base.relative_to(REPO)), "seal_sha256": expected, "members": len(paths), "member_bytes": total, "selfseal_sidecar_declared": sidecar, "exact_directory_coverage": True}
    return records


if __name__ == "__main__":
    result = verify()
    dump(ROOT / "input-custody.json", {"schema": 1, "verified": result})
    print(json.dumps(result, sort_keys=True))
