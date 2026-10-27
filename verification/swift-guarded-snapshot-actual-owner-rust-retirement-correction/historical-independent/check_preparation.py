"""Independent frozen-input custody check only; no implementation or compiler."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def packet(name, expected):
    base = ROOT / "verification" / name
    raw = (base / "seal.json").read_bytes()
    assert sha(raw) == expected
    seal = json.loads(raw)
    rows = []
    for path in sorted(base.rglob("*")):
        if path.is_file() and path != base / "seal.json":
            data = path.read_bytes()
            rows.append({"path": str(path.relative_to(base)), "bytes": len(data), "sha256": sha(data)})
    assert rows == seal["members"]
    assert len(rows) == seal["member_count"]
    assert sum(r["bytes"] for r in rows) == seal["member_bytes"]
    assert sha(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()) == seal["tree_sha256"]
    return {"seal_sha256": sha(raw), "members": len(rows), "member_bytes": sum(r["bytes"] for r in rows)}


selection = packet("swift-guarded-snapshot-actual-owner-rust-selection", "1b0c3234a22f559280f5eb461bab5bf367a2ee0b7acda45c744b1da92b10d0f7")
preaccess = packet("swift-guarded-snapshot-actual-owner-rust-preaccess", "050d4920ee51014748d0c62aec832c13a65bef09673fff41bbc62310635e4a66")
frozen = ROOT / "verification/swift-guarded-snapshot-actual-owner-rust-preaccess"
oracles = json.loads((frozen / "oracles.json").read_bytes())
cases = json.loads((frozen / "cases.json").read_bytes())
compiler = json.loads((frozen / "compiler-cases.json").read_bytes())
assert [c["id"] for c in cases["cases"]] == [f"H{i:02}" for i in range(1, 14)]
assert [c["id"] for c in compiler["cases"]] == [f"C{i:02}" for i in range(1, 9)]
assert len(oracles["correlation_mutations"]) == 230
assert len(oracles["read_schedules"]) == 12
assert sum(len(v["mutations"]) for v in oracles["binary"].values()) == 51
assert not oracles["production_authority"]
plan = json.loads((HERE / "review-plan.json").read_bytes())
assert not plan["producer_source_accessed"]
root = ROOT / "verification/swift-semantic-adapter-root-review"
bindings = {
    "guarded-snapshot-actual-owner-Rust-implementation-selection.json": "9551f5e447c600af27aa96146a757ea1452027c465baf76fd3c1d8c31b88ce61",
    "guarded-snapshot-actual-owner-Rust-contract-amendment.json": "b07ea4fc8cbd1e30581d2de7b2512c8e5a3057c101a24cd6ea26239fa92d0e5f",
    "guarded-snapshot-actual-owner-Rust-H09-H10-amendment.json": "0f97f16f6c910fba8fc6cb46884cd80d8c37b1513840805bb52be88ff4d12414",
}
for name, expected in bindings.items():
    assert sha((root / name).read_bytes()) == expected
print(json.dumps({"status": "prepared frozen custody and unchanged independent vectors", "selection": selection, "preaccess": preaccess, "root_bindings": bindings, "host_cases": 13, "compiler_categories_unexecuted": 8, "binary_mutations": 51, "provenance_mutations": 230, "read_schedules": 12, "producer_source_accessed": False, "compiler_test_binary_native_or_UI_executed": False}, sort_keys=True))
