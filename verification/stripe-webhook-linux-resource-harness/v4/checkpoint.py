#!/usr/bin/env python3
"""Read-only validation of the immutable v1 checkpoint, including archive bytes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent
ROOT = PACKET.parents[1]
ARCHIVE_SHA256 = "1b48a7bb2c217e3f1307d05056ef93443f34140c286af4106fdc67373f9d0286"
SEAL_SHA256 = "0af22f84b6129b781f7af970cafdc71bf208f86f63275e4584a79875ce1c7dfe"
V2_SEAL_SHA256 = "35813b1f5194eeea3317f3e926ebde0f8a6a589d6f5724c69e27fd4c58a424b3"
REVIEW_SEAL_SHA256 = "f32581490682397d10a26ffbc6250d129cab754782139d4f8b27711d6d209e48"
V3_SEAL_SHA256 = "567139b93da497f8cfce6ce5f34aa5029b357e6b9f28a80cc7d70d077461608f"
V3_REVIEW_SEAL_SHA256 = "63c7da620a9abefa65b2dbe536b25d733d0299bf14aaaaaebef028924065d642"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    original_seal = PACKET / "seal.json"
    archive = PACKET / "checkpoints/v1.tar"
    assert sha(original_seal.read_bytes()) == SEAL_SHA256
    assert (PACKET / "checkpoints/v1-seal.json").read_bytes() == original_seal.read_bytes()
    assert sha(archive.read_bytes()) == ARCHIVE_SHA256
    sealed = json.loads(original_seal.read_bytes())["files"]
    assert len(sealed) == 98
    expected = {**sealed, str(original_seal.relative_to(ROOT)): SEAL_SHA256}
    with tarfile.open(archive, "r:") as tf:
        members = tf.getmembers()
        assert len(members) == len(expected) and {m.name for m in members} == set(expected)
        for member in members:
            assert member.isfile() and not member.issym() and not member.islnk()
            assert sha(tf.extractfile(member).read()) == expected[member.name]
    for name, expected_sha in expected.items():
        path = ROOT / name
        assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
        assert sha(path.read_bytes()) == expected_sha, name
    v2 = PACKET / "v2"
    v2_seal = v2 / "seal.json"
    assert sha(v2_seal.read_bytes()) == V2_SEAL_SHA256
    v2_files = json.loads(v2_seal.read_bytes())["files"]
    assert len(v2_files) == 104
    for name, expected_sha in v2_files.items():
        path = ROOT / name
        assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
        assert sha(path.read_bytes()) == expected_sha, name
    actual = {str(path.relative_to(ROOT)) for path in v2.rglob("*") if path.is_file() and path != v2_seal}
    assert actual == {name for name in v2_files if name.startswith(str(v2.relative_to(ROOT)) + "/")}
    review = ROOT / "verification/stripe-resource-harness-v2-independent-review"
    review_seal = review / "review-seal.json"
    assert sha(review_seal.read_bytes()) == REVIEW_SEAL_SHA256
    review_data = json.loads(review_seal.read_bytes())
    for name, expected_sha in review_data["files"].items():
        path = ROOT / name
        assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
        assert sha(path.read_bytes()) == expected_sha, name
    v3 = PACKET / "v3"
    for seal_path, expected_sha, count in ((v3 / "seal.json", V3_SEAL_SHA256, 90),
            (ROOT / "verification/stripe-resource-harness-v3-independent-review/review-seal.json", V3_REVIEW_SEAL_SHA256, 10)):
        assert sha(seal_path.read_bytes()) == expected_sha
        bound = json.loads(seal_path.read_bytes())["files"]
        assert len(bound) == count
        for name, binding in bound.items():
            path = ROOT / name
            assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
            assert sha(path.read_bytes()) == binding, name
    v3_bound = json.loads((v3 / "seal.json").read_bytes())["files"]
    v3_actual = {str(path.relative_to(ROOT)) for path in v3.rglob("*") if path.is_file() and path != v3 / "seal.json"}
    assert v3_actual == {name for name in v3_bound if name.startswith(str(v3.relative_to(ROOT)) + "/")}
    return {"schema": 1, "status": "passed-immutable-checkpoint-bindings-only", "sealedFiles": 98,
            "archiveMemberFiles": 99, "v2SealedFiles": 104, "v2SealSha256": V2_SEAL_SHA256,
            "independentReviewSealSha256": REVIEW_SEAL_SHA256,
            "v3SealedFiles": 90, "v3SealSha256": V3_SEAL_SHA256, "v3IndependentReviewSealSha256": V3_REVIEW_SEAL_SHA256,
            "runtimeCasesExecuted": 0, "implementationComplete": False}


def load_controller():
    verify()
    spec = importlib.util.spec_from_file_location("mixer_resource_v1_controller", PACKET / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
