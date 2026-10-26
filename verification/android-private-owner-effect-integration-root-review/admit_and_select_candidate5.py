"""Admit the immutable F09 repair and select exact bounded CLI rebinding."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
CANDIDATE = ROOT / "verification/android-private-owner-integration-implementation/candidate-5"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def require(path, row):
    assert path.is_file() and not path.is_symlink(), path
    assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], path


def save(name, data):
    path = OUT / name
    assert not path.exists(), "One-shot receipt already exists"
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(path.relative_to(ROOT), sha(path))
    return path


assert sha(CANDIDATE / "manifest.json") == "59a820bd3cd7e01ead02114293028985f64a42eebc36094cef9d76f516eee1f1"
manifest = load(CANDIDATE / "manifest.json")
assert len(manifest["files"]) == manifest["members"] == 1772
assert sum(row["bytes"] for row in manifest["files"].values()) == manifest["bytes"] == 11787752
assert {p.relative_to(CANDIDATE).as_posix() for p in CANDIDATE.rglob("*") if p.is_file()} == set(manifest["files"]) | {"manifest.json"}
for name, row in manifest["files"].items():
    require(CANDIDATE / name, row)
sources = load(CANDIDATE / "source-map.json")
assert len(sources) == 311
assert sha(CANDIDATE / "source-map.json") == "da250cd1e7560f8d702753769a132b70f60ea05477d133c32afd0c7372c542a1"
for name, row in sources.items():
    require(ROOT / name, row)
    require(CANDIDATE / "source" / name, row)
old_sources = load(CANDIDATE.parent / "candidate-4/source-map.json")
changed = [name for name in old_sources if old_sources[name] != sources[name]]
assert changed == ["native/android/app/src/dev/mixer/android/NativeOwnerV2.java", "native/android/tests/NativeOwnerV2HostTests.java"]
added = sorted(set(sources) - set(old_sources))
assert len(added) == 2 and all("candidate-5/driver-source/" in name for name in added)
assert not set(old_sources) - set(sources)
profile_path = CANDIDATE / "profile-proposal.json"
assert sha(profile_path) == "6bcf2c6b0b0936522e3a6f5297765b6e4f795203b55721aabe7a82c4ba216a8f"
profile = load(profile_path)
old_profile = load(CANDIDATE.parent / "candidate-4/profile-proposal.json")
assert [name for name in old_profile["adapter_files"] if old_profile["adapter_files"][name] != profile["adapter_files"][name]] == ["app/src/dev/mixer/android/NativeOwnerV2.java"]
expected = dict(old_profile)
expected.update(adapter_files=profile["adapter_files"], adapter_compatibility_sha256=profile["adapter_compatibility_sha256"])
assert expected == profile
for prefix, key in [("native/android", "adapter"), ("sdk", "sdk")]:
    rows = profile[key + "_files"]
    assert len(rows) == 22
    for name, row in rows.items():
        source_name = "engine/" + name if key == "adapter" and name.startswith("Sources/") else name
        require(ROOT / prefix / source_name, row)
    projection = hashlib.sha256("".join(name + "\0" + rows[name]["sha256"] + "\n" for name in sorted(rows)).encode()).hexdigest()
    assert projection == profile[key + "_compatibility_sha256"]

common = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python": sys.version,
    "script_sha256": sha(pathlib.Path(__file__)),
    "context_revision_only": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "candidate_manifest_sha256": sha(CANDIDATE / "manifest.json"),
    "source_map_sha256": sha(CANDIDATE / "source-map.json"),
    "canonical_delivery_authorized_by_this_receipt": False,
    "implementation_accepted": False,
    "native_runtime_capture_or_inventory_started": False,
    "GA_qualified": False,
}
admission = save("candidate-5-admission.json", {
    **common,
    "status": "Exact immutable candidate5 admitted for independent host/source review",
    "candidate": CANDIDATE.relative_to(ROOT).as_posix(),
    "members": 1772,
    "bytes": 11787752,
    "source_inputs_verified": 311,
    "changed_product_and_test_sources": changed,
    "new_evidence_driver_inputs": added,
    "selected_owner_sha256": "056aa51d07e765b59a3859ce76090477a24211c973b63336406ff4b0d4102269",
    "producer_A": {"cases": 222, "assertions": 1180},
    "producer_B": {"checks": 14477, "mechanical_callback_rows": 1323},
    "producer_compilation": "Fresh strict --release17 Java, official Android37 SDK and D8 minimum API28 pass; no runtime qualification",
    "historical_Swift_JNI_input_reuse": 76,
    "negative_control": "Same strengthened tests against frozen candidate4 fail expected F09 outer-primary assertion",
    "review_baseline": "Immutable rejected review3 f4afff4105d08642e74f1e5a3255015828e57c2a703b023bdd91ce709be18bc2; all earlier findings/results preserved",
    "required_independent_scope": ["Exact repair and first primary/fatal identities with earlier-owner and repeated-close controls", "Seven pending direct measure-helper rows; reconcile complete189-site timing/source bindings", "Finish preaccess historical, cancellation, IME, decoder and cause-family obligations with exact remaining scope", "Preserve no-callback successful commit/finish interval and actual core/gates"],
    "mechanical_leaf_reuse": "Unchanged prior independently reviewed leaf3 and its admitted class/source identities only; no producer oracle reuse",
})
save("candidate-5-profile-selection.json", {
    **common,
    "status": "Exact frozen5 profile selected for CLI rebinding and bounded host validation",
    "candidate_admission": admission.relative_to(ROOT).as_posix(),
    "candidate_admission_sha256": sha(admission),
    "profile_proposal": profile_path.relative_to(ROOT).as_posix(),
    "profile_proposal_sha256": sha(profile_path),
    "profile_id": profile["id"],
    "adapter_members": 22,
    "sdk_members": 22,
    "adapter_projection_sha256": profile["adapter_compatibility_sha256"],
    "sdk_projection_sha256": profile["sdk_compatibility_sha256"],
    "selected_scope": "Only compiled NativeOwnerV2 identity and adapter projection change from candidate4; preserve profile3 ID, SDK, default descriptor, wire and fail-closed old locks. Fresh Debug/Release CLI, direct rendered driver, preaccess refusal and copied consumer qualification required.",
    "CLI_validation_authorized": True,
    "native_source_mutations_authorized": False,
    "independent_owner_review_pending": True,
})
