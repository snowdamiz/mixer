"""Read-only verification of explicitly released input packets; never run producers."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PACKETS = {
    "verification/swift-retained-profile-stdio-read-boundary-correction/seal.json": "c79bd64dc0019c17f03b17df0a6bd5dc8879334d64fbf74f92507d75a5e81f54",
    "verification/swift-retained-profile-stdio-read-boundary-independent/seal.json": "a10b46f06b54e3bd3e940c7cf403cac7f80faed4814347f2c38616ab447006e1",
    "verification/swift-retained-profile-composition-stdio-correction/seal.json": "01fde6f81a88a35fe734f66991324e2518967e2890a8485cf13a679fd01eeeb2",
    "verification/swift-retained-profile-composition-stdio-independent/seal.json": "af9f20a00000cdbac6f772e19088e0c9ce078530386cb62d41d693954b832040",
    "verification/swift-retained-profile-composition-preparation/seal.json": "c7a8ead8257b8e13543c4fb3bb3ed385513f83080c960a58333b617d05c44860",
    "verification/swift-profile-header-preparation/seal.json": "aee8ffbe028f9fe3084a62a81fe0946dc6a21cc132e16d83915917cf6657515f",
    "verification/swift-initial-profile-construction-protocol/seal.json": "eee07facb219eaba5e135f3970d2f508a0acd20b3eb81f47f0dd9771412d5e91",
    "verification/swift-initial-profile-construction-implementation/seal.json": "50d1c32174ee4cbcade6095039261ea0ff8eed05680322bfb59b5de0dd4cd8b1",
    "verification/swift-initial-profile-construction-independent/actual-review/seal.json": "caf14158ab6bbf681d18684ac206f4e97284644b307064271d72e86e59a3217b",
}
RECEIPTS = {
    "verification/swift-semantic-adapter-root-review/retained-composition-stdio-host-acceptance.json": "d5326f39cf49f796149fea2ebb7f0e602f6dd7df202c9540a82891bec20d823e",
    "verification/swift-semantic-adapter-root-review/initial-profile-component-acceptance.json": "77287c9659d8033450571f0a1aef4ccb02eacc513999cd6fdaa34f7746431a71",
    "verification/swift-semantic-adapter-root-review/initial-profile-implementation-selection.json": "be4b74efe70d5d009658eb6207f20457dbbe31537dab86a869d3cb5f17ede864",
    "verification/swift-semantic-adapter-root-review/initial-profile-foundation-configuration-correction.json": "d4d4ea1a4d4a5e7715e1fffdf9f20bfabed41ddcf9f43bb89b2f657a2383f2c3",
    "verification/swift-semantic-adapter-root-review/initial-profile-source-action-scope-selection.json": "7185ac67c7742f7142f4f7aca44628411da56b92dbfb1c56615c4a776d3991c9",
}

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    result = {"scope": "released immutable packet custody only; no behavior rerun", "packets": [], "receipts": []}
    for relative, expected in PACKETS.items():
        seal = ROOT / relative
        actual = digest(seal)
        assert actual == expected, (relative, actual, expected)
        data = json.loads(seal.read_text())
        count = total = 0
        seen = set()
        for member in data["members"]:
            name = member["path"]
            rel = Path(name)
            assert not rel.is_absolute() and ".." not in rel.parts and name not in seen
            seen.add(name)
            file = seal.parent / rel
            assert not file.is_symlink() and file.is_file(), file
            assert file.stat().st_size == member["bytes"], file
            assert digest(file) == member["sha256"], file
            count += 1
            total += member["bytes"]
        assert count == data.get("member_count", count)
        assert total == data.get("member_bytes", data.get("total_bytes", total))
        result["packets"].append({"path": relative, "sha256": actual, "members_verified": count, "bytes_verified": total})
    for relative, expected in RECEIPTS.items():
        actual = digest(ROOT / relative)
        assert actual == expected, (relative, actual, expected)
        result["receipts"].append({"path": relative, "sha256": actual})
    (HERE / "input-custody.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"packets": len(result["packets"]), "receipts": len(result["receipts"]), "members_verified": sum(p["members_verified"] for p in result["packets"]), "bytes_verified": sum(p["bytes_verified"] for p in result["packets"])}))

if __name__ == "__main__":
    main()
