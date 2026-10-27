"""Independent read-only verifier of the declared frozen inputs; no old code imported."""
import hashlib
import json
from pathlib import Path
import stat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-affine-refusal"
RELEASE = ROOT / "verification/swift-semantic-adapter-root-review/guarded-snapshot-prepaid-input-owner-affine-refusal-frozen-release.json"
BINDING = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-correction-independent/correction-contract.json"
RETURN = ROOT / "verification/swift-semantic-adapter-root-review/guarded-snapshot-prepaid-input-owner-correction-return.json"
EXPECTED_SEAL = "2270f59809b80c49df907a7ea9c20faf4dd45735cabad275ae61065efc19c50b"
EXPECTED_TREE = "414e52ca03e3e1aab03a234287ad0bea32e499de021817bc8b5a456dd94d3a6f"
EXPECTED_MODEL = "e18bdf16f9de346d3ab553a525d49b735c240ce86c0bdf9717b7a175767fed7f"


def row(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def tree(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def verify_packet(base, expected_sha=None):
    seal_path = base / "seal.json"
    if expected_sha is not None:
        assert row(seal_path)["sha256"] == expected_sha
    seal = json.loads(seal_path.read_bytes())
    members = seal["members"]
    names = {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file() and p != seal_path}
    assert names == {e["path"] for e in members}, str(base)
    assert len(names) == seal["member_count"]
    assert sum(e["bytes"] for e in members) == seal["member_bytes"]
    assert tree(members) == seal["tree_sha256"]
    paths = []
    for member in members:
        path = base / member["path"]
        actual = row(path)
        assert (actual["bytes"], actual["sha256"]) == (member["bytes"], member["sha256"]), str(path)
        paths.append(path)
    return seal, paths + [seal_path]


def custody():
    # The candidate's declared 479 inputs, plus its own full 68-file packet and
    # the separately supplied frozen root release. No mutable PLAN/HEAD inputs.
    seal, packet_paths = verify_packet(CANDIDATE, EXPECTED_SEAL)
    assert (seal["member_count"], seal["member_bytes"], seal["tree_sha256"]) == (67, 1728034, EXPECTED_TREE)
    assert row(CANDIDATE / "model.py")["sha256"] == EXPECTED_MODEL
    assert row(CANDIDATE / "interface.inc.rs")["sha256"] == "4be6917189b7e37e660ff77e62535d6902be9c3bb320ae7140cb3ff4f19a5e4a"
    frozen = json.loads((CANDIDATE / "final-custody.json").read_bytes())
    earlier = frozen["before"]
    assert len(earlier) == 479 and earlier == frozen["after"] and frozen["unchanged"]
    paths = set(packet_paths)
    for entry in earlier:
        path = ROOT / entry["path"]
        assert row(path) == entry, entry["path"]
        paths.add(path)
    # Complete membership, not just listed hashes, for every earlier declared seal.
    for entry in earlier:
        if entry["path"].endswith("/seal.json"):
            _, members = verify_packet((ROOT / entry["path"]).parent, entry["sha256"])
            assert all(p in paths for p in members)
    assert row(BINDING)["sha256"] == "b023b8e816c5a68cfe565f0cf901676998ec50b189aca1ead0bb49dbce142d51"
    assert row(RETURN)["sha256"] == "97aa4d370d6c490e37302ad036e2af029cb6607972147c40c7dd63c410a28c9c"
    assert row(RELEASE)["sha256"] == "ef722611a7318031cdf656622263096f629741eb93008405688ce827aa631d39"
    paths.add(RELEASE)
    assert all(stat.S_IMODE(p.stat().st_mode) & 0o222 == 0 for p in packet_paths)
    return sorted((row(p) for p in paths), key=lambda e: e["path"])


def review_sources():
    return [row(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix == ".py"]
