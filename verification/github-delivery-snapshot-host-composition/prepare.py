"""Prepare exact delivery only after root accepts the frozen source146 review."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "f678177785accb9e74dbdcb7bbc84222b81c9448"
PARENT = ROOT / "verification/github-delivery-snapshot-admission-composition"
REVIEW = ROOT / "verification/swift-semantic-adapter-root-review"


def identity(path):
    assert stat.S_ISREG(path.lstat().st_mode), path
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def save(path, value, exclusive=True):
    with path.open("x" if exclusive else "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


assert not (OUT / "release-selection.json").exists(), "One-shot preparation"
acceptance_path = REVIEW / "guarded-snapshot-host-composition-host-acceptance.json"
assert len(sys.argv) == 2 and identity(acceptance_path)["sha256"] == sys.argv[1]
accepted = json.loads(acceptance_path.read_bytes())
assert accepted["status"] == "accepted-bounded-private-source146-composition"
assert accepted["source_members"] == 146
assert not accepted["whole_host_grant_accepted"]
assert not accepted["native_OTA_GA_accepted"]

seals = {
    "host-account-entry": "6e8c8e2d8dde62e2e35fe2e8fb1a851a342d8d95f8c71facd938416ac3e153e3",
    "host-account-independent": "afd315366d4b85b103f5cb616a54429e515fffec0ed821f5a7a77acbe02e9780",
    "host-account-inventory-independent": "a41ff779d707d246997ddcbb36d5b157edc1d6fc01be27b6f80dc210e3cf2295",
    "host-composition": "2fc002b2598effdc70a74ecfa3da775b4aa82f2572cbbb93650207925238dc2e",
    "host-composition-independent": accepted["independent"]["seal_sha256"],
}
packets = []
for suffix, digest in seals.items():
    name = "swift-guarded-snapshot-" + suffix
    folder = ROOT / "verification" / name
    assert identity(folder / "seal.json")["sha256"] == digest
    seal = json.loads((folder / "seal.json").read_bytes())
    for row in seal["members"]:
        observed = identity(folder / row["path"])
        assert all(observed[key] == row[key] for key in ("bytes", "sha256"))
    packets.append({"path": name, "seal_sha256": digest})

receipts = {
    "guarded-snapshot-host-account-independent-release.json": "0ff404a5075827db7e055f16c75a5ec48da09902caa85b594a0cd171d370588f",
    "guarded-snapshot-host-account-host-acceptance.json": "8bb780193f9039174b7f1dd503f6572f8cca9bf6ec01f81722ed3f25aa9d927a",
    "guarded-snapshot-host-composition-next-source-release.json": "2f112a66bb382c7bce38866ac993acf95be01a939cf0d863cf9b98c60e3597ad",
    "guarded-snapshot-host-fixture-source-selection.json": "5d7b4d01727c6163b25a309633f6952aa5625d14a124a0bc33c27737a51774e2",
    "guarded-snapshot-host-composition-independent-release.json": "2d3170946aca8385fd5cb147b653ac26e7813f19be5a801337834366753fee51",
    "guarded-snapshot-host-composition-host-acceptance.json": sys.argv[1],
}
rows = []
for name, digest in receipts.items():
    row = identity(REVIEW / name)
    assert row["sha256"] == digest
    rows.append(row)
rows.append(identity(Path(__file__).resolve()))
terminal = json.loads((PARENT / "terminal-ci-status.json").read_bytes())
assert terminal["commit"] == BASE and terminal["conclusion"] == "success"
assert terminal["jobs_passed"] == 6 and terminal["steps_passed"] == 64
parent_files = [identity(path) for path in sorted(PARENT.rglob("*")) if path.is_file()]

work = json.loads((ROOT / "work-graph.json").read_bytes())
gates = json.loads((ROOT / "gates/ga.json").read_bytes())
candidate = work["packages"][7]["fixtureCacheStateContractCandidate"]
candidate["guarded_snapshot_host_composition_delivery"] = {
    "status": "prepared-exact-allowlist-delivery", "base": BASE, "packets": 5,
    "canonical_product_changed": False,
    "scope": "Accepted private account and source146 composition; full host funding and runtime remain pending.",
    "excluded": ["loader-work proposal and independent review", "parent-work proposal", "protected hosted changes"],
    "native_OTA_GA_accepted": False,
}
gates["gates"][1]["fixtureCacheStateContractCandidate"] = candidate
save(ROOT / "work-graph.json", work, exclusive=False)
save(ROOT / "gates/ga.json", gates, exclusive=False)

script = (PARENT / "deliver.py").read_text()
replacements = {
    '"""One-shot delivery of bounded work admission, composition and bootstrap preparation."""':
        '"""One-shot delivery of accepted private host account and source146 composition."""',
    'BASE = "32b5075a5f203cb25ae357492b70f0f724f3ea19"': f'BASE = "{BASE}"',
    'assert len(release["packets"]) == 7': 'assert len(release["packets"]) == 5',
    'verification/github-delivery-snapshot-funding-retention/':
        'verification/github-delivery-snapshot-admission-composition/',
    '"verification/swift-guarded-snapshot-host-account-entry/",\n    "verification/swift-guarded-snapshot-host-account-independent/",\n    "verification/swift-guarded-snapshot-host-account-inventory-independent/",\n    "verification/swift-guarded-snapshot-loader-work/",\n    "verification/swift-guarded-snapshot-loader-work-independent/",':
        '"verification/swift-guarded-snapshot-parent-work/",\n    "verification/swift-guarded-snapshot-loader-work/",\n    "verification/swift-guarded-snapshot-loader-work-independent/",',
    'Record reviewed snapshot admission and source composition':
        'Compose isolated snapshot host account and typed entry',
    'host_account_and_loader_work_lanes_excluded': 'parent_and_loader_work_lanes_excluded',
}
for old, new in replacements.items():
    assert script.count(old) == 1, old
    script = script.replace(old, new)
ast.parse(script)
with (OUT / "deliver.py").open("x") as stream:
    stream.write(script)
save(OUT / "release-selection.json", {
    "schema": 1, "ready": True, "base": BASE, "packets": packets,
    "root_and_source_files": rows, "parent_delivery_files": parent_files,
    "canonical_paths": [],
    "scope": "Accepted private host account, typed entry, source-object inventory and isolated source146 composition. Preserved original findings and fresh independent compiler/layout/synthetic evidence; immutable future fixture source selection only. No canonical product change, complete P0/child quote, selected host policy, real loader/writer runtime, healthy cleanup, native, OTA, FieldLog or GA acceptance.",
})
assert [p["id"] for p in work["packages"]] == [f"W{i:02}" for i in range(1, 19)]
assert [g["id"] for g in gates["gates"]] == [f"G{i:02}" for i in range(1, 39)]
assert sum(g["status"] == "running" for g in gates["gates"]) == 8
assert sum(g["status"] == "planned" for g in gates["gates"]) == 30
assert work["packages"][4]["privateOwnerEffectContractCandidate"] == gates["gates"][4]["privateOwnerEffectContractCandidate"]
assert work["packages"][7]["fixtureCacheStateContractCandidate"] == gates["gates"][1]["fixtureCacheStateContractCandidate"]
assert all(f"D{i}" in (ROOT / "mixer-product-plan.md").read_text() for i in range(9))
save(OUT / "metadata-validation.json", {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(), "passed": True,
    "python": sys.version, "command": [sys.executable, str(Path(__file__).resolve()), sys.argv[1]],
    "scope": "Frozen member custody, exact root acceptance, W01-W18/G01-G38/D0-D8 identities and mirrors, eight running/thirty planned/no passed gates, delivery exclusions and wrapper syntax only",
    "metadata_files": [identity(ROOT / name) for name in ("PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json")],
    "packages": 18, "gates": 38, "dogfood_milestones": 9,
})
print(json.dumps({"prepared_packets": len(packets), "parent_files": len(parent_files), "canonical_paths": []}))
