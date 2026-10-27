"""Prepare an allowlisted source/review checkpoint; does not commit or push."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "b20cd3bcd83f9110fbbc62ce60a265373f2a85e5"
PARENT = ROOT / "verification/github-delivery-host-constructor-outer-review"
REVIEW = ROOT / "verification/swift-semantic-adapter-root-review"
PACKETS = [
    ("swift-guarded-snapshot-scoped-binding-independent", "e11d9eff0eda83ccf46563526e3c7025172cc8e05513b4a9ba1a5a0d9c13344a"),
    ("swift-guarded-snapshot-owned-binding-provider", "7af047d181125c0e3da36f2d4585d4a31204bedf8f367793300022391aca02de"),
    ("swift-guarded-snapshot-owned-provider-independent", "8138bc61fdcca8662a9a7a3784f4dd8f4db9742db59faeffa872e899fc18e801"),
    ("swift-guarded-snapshot-string-correction-independent", "7c101623fa53d9207c467f196cca729085fff23a195f873a46da7a1369135f65"),
    ("swift-guarded-snapshot-string-exact-binding-correction", "4eb0437b5ed1f7ec056340ffac08a0221cfd5f6f216a9d3aebb6fd4d25cc5f4b"),
    ("swift-guarded-snapshot-prepaid-input-owner-contract", "9c73d3405370a71ad447136ab7a4e56c2d45dbf4fd4627c319a8626f8a53033e"),
    ("swift-guarded-snapshot-owned-provider-work-storage", "28ba8099ce8b57f91cd46baac21f130986000ecbbf7df07b16e6bf061fc342d1"),
]
ACTIVE = ["swift-guarded-snapshot-string-exact-binding-independent",
          "swift-guarded-snapshot-prepaid-input-owner-independent",
          "swift-guarded-snapshot-owned-provider-work-storage-independent"]
ROOT_FILES = [
    "accept-scoped-binding-source.py",
    "guarded-snapshot-owned-binding-provider-frozen-release.json",
    "guarded-snapshot-owned-binding-provider-host-acceptance.json",
    "guarded-snapshot-owned-provider-work-storage-frozen-release.json",
    "guarded-snapshot-prepaid-input-owner-frozen-release.json",
    "guarded-snapshot-scoped-binding-source-host-acceptance.json",
    "guarded-snapshot-string-correction-second-return.json",
    "guarded-snapshot-string-exact-binding-frozen-release.json",
    "release-exact-binding-and-input-owner-candidates.py",
    "release-owned-provider-work-storage.py",
    "scoped-binding-root-check/plan.json", "scoped-binding-root-check/receipt.json",
    "scoped-binding-root-check/stderr", "scoped-binding-root-check/stdout",
]
ACCEPTANCES = {
    "guarded-snapshot-scoped-binding-source-host-acceptance.json": "1bc55306a1f6cf220660efa8ab9e34485d610ae806ebd56a1733d892ddfcd2e1",
    "guarded-snapshot-owned-binding-provider-host-acceptance.json": "998a7f6de2918e6b643360b4e67475fdc9a468d69792eb5cda3bb773272fcba3",
    "guarded-snapshot-string-correction-second-return.json": "9dba765988b0e464fe58245520586696945e9f4bbd87f1ca2b8bc4051cf68440",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def row(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


assert not (OUT / "release-selection.json").exists(), "one-shot preparation"
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, timeout=10, text=True).strip() == BASE
assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, timeout=10)
for name, expected in PACKETS:
    packet = ROOT / "verification" / name
    assert sha((packet / "seal.json").read_bytes()) == expected
for name, expected in ACCEPTANCES.items():
    assert row(REVIEW / name)["sha256"] == expected
assert row(PARENT / "terminal-ci-status.json")["sha256"] == "c1ff6c56c13643e500e2d851639efe36c611ce998a828b7a4fb7cb348a57bb78"
terminal = json.loads((PARENT / "terminal-ci-status.json").read_text())
observation = PARENT / terminal["observation"]
assert row(observation)["sha256"] == terminal["observation_sha256"]
jobs = json.loads(observation.read_text())["jobs"]
assert len(jobs) == 6 and sum(len(j["steps"]) for j in jobs) == 64
assert all(j["conclusion"] == "success" and all(s["conclusion"] == "success" for s in j["steps"]) for j in jobs)

work = json.loads((ROOT / "work-graph.json").read_text())
gates = json.loads((ROOT / "gates/ga.json").read_text())
candidate = work["packages"][7]["fixtureCacheStateContractCandidate"]
assert candidate == gates["gates"][1]["fixtureCacheStateContractCandidate"]
candidate["guarded_snapshot_owned_binding_source_review_delivery"] = {
    "status": "prepared-for-authorized-nonforce-push", "base": BASE,
    "packet_count": 7, "directory": str(OUT.relative_to(ROOT)),
    "scoped_lifetime_and_existing_owner_source_bounded_acceptance": True,
    "new_string_acquisition_and_accounting_candidates_accepted": False,
    "active_review_lanes_excluded": ACTIVE, "canonical_product_changed": False,
    "parent_CI": {"run": terminal["run"], "jobs_passed": 6, "steps_passed": 64},
    "runtime_or_root_funding_or_native_OTA_GA": False,
}
gates["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(candidate)
assert [p["id"] for p in work["packages"]] == [f"W{i:02}" for i in range(1, 19)]
assert [g["id"] for g in gates["gates"]] == [f"G{i:02}" for i in range(1, 39)]
assert sum(g["status"] == "running" for g in gates["gates"]) == 8
assert sum(g["status"] == "planned" for g in gates["gates"]) == 30
assert work["packages"][4]["privateOwnerEffectContractCandidate"] == gates["gates"][4]["privateOwnerEffectContractCandidate"]
for name, value in [("work-graph.json", work), ("gates/ga.json", gates)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
for name in ["PLAN.md", "STATUS.md"]:
    text = (ROOT / name).read_text()
    assert "mixer-product-plan.md" in text
    assert "Three frozen candidates now have complete root custody checks" in text
subprocess.run(["git", "diff", "--check", "--", "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"], cwd=ROOT, timeout=10, check=True)

source = (PARENT / "deliver.py").read_text()
source = source.replace('BASE = "a32d056355ec2f417e9ef7a73788b420176377b6"', 'BASE = "' + BASE + '"')
source = source.replace('release["packet_count"] == 8', 'release["packet_count"] == 7')
source = source.replace('startswith("verification/github-delivery-host-interface-amendment/")', 'startswith("verification/github-delivery-host-constructor-outer-review/")')
source = source.replace('("deliver.py", "release-selection.json", "metadata-validation.json")', '("prepare.py", "deliver.py", "release-selection.json", "metadata-validation.json")')
source = source.replace('    "verification/swift-guarded-snapshot-string-correction-independent/",\n    "verification/swift-guarded-snapshot-scoped-binding-independent/",\n    "verification/swift-guarded-snapshot-owned-binding-provider/",', '\n'.join('    "verification/' + n + '/",' for n in ACTIVE))
source = source.replace("Record reviewed native constructors and outer caller bounds", "Record immutable binding source and provider review candidates")
source = source.replace('"active_string_scoped_review_and_provider_lanes_excluded"', '"active_string_acquisition_and_accounting_review_lanes_excluded"')
with (OUT / "deliver.py").open("x") as stream:
    stream.write(source)
parent_names = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z", "--", str(PARENT.relative_to(ROOT))], cwd=ROOT, timeout=10).decode().split("\0")
release = {
    "schema": 1, "ready": True,
    "packets": [{"path": n, "seal_sha256": s} for n, s in PACKETS], "packet_count": 7,
    "root_and_source_files": [row(REVIEW / n) for n in ROOT_FILES],
    "parent_delivery_files": [row(ROOT / n) for n in parent_names if n],
    "canonical_paths": [],
    "scope": "Bounded accepted scoped-lifetime and unqualified existing-owner source; returned string review; three frozen string/acquisition/accounting candidates awaiting fresh independent review; terminal parent CI. No canonical product integration, runtime, funding or grant.",
    "active_lanes_excluded": ACTIVE,
}
write(OUT / "release-selection.json", release)
write(OUT / "metadata-validation.json", {
    "schema": 1, "passed": True, "at": datetime.now(timezone.utc).isoformat(),
    "command": sys.argv, "python": sys.version,
    "python_executable_sha256": sha(Path(sys.executable).resolve().read_bytes()),
    "script_sha256": sha(Path(__file__).read_bytes()), "source_revision": BASE,
    "metadata_files": [row(ROOT / n) for n in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]],
    "acceptance_and_return_references": [row(REVIEW / n) for n in ACCEPTANCES],
    "gates": {"running": 8, "planned": 30, "passed": 0},
    "scope": "Full package/gate identifiers, paired candidate metadata, root receipt hashes, complete terminal parent CI, authored whitespace; no runtime qualification",
})
print(json.dumps({"prepared": True, "packets": 7, "root_files": len(ROOT_FILES), "parent_receipt_files": len(release["parent_delivery_files"]), "commit_or_push_executed": False}))
