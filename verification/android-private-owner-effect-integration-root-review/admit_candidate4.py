"""Verify corrected private owner custody and admit independent review; CLI remains held."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "verification/android-private-owner-integration-implementation/candidate-4"
SEAL_SHA = "69fcd445119c0ea311c11cf97587d591d87ba1c5bd2d5b3c0a722116f66231c5"
PROFILE_SHA = "fa20572d64d0cec8e2bbfd959df6a2993b4e231cca6f3f8009761bd0b2678d62"


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    require(path.is_file() and not path.is_symlink(), "Nonregular path: " + str(path))
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def safe_relative(name):
    path = Path(name)
    require(not path.is_absolute() and ".." not in path.parts, "Unsafe path")
    return path


require(identity(CANDIDATE / "manifest.json")["sha256"] == SEAL_SHA, "Candidate seal changed")
manifest = json.loads((CANDIDATE / "manifest.json").read_bytes())
for name, row in manifest["files"].items():
    require(identity(CANDIDATE / safe_relative(name)) == row, "Candidate member changed: " + name)
require(len(manifest["files"]) == manifest["members"] == 1246, "Candidate member count")
require(sum(row["bytes"] for row in manifest["files"].values()) == manifest["bytes"] == 11884760, "Candidate bytes")
actual = {path.relative_to(CANDIDATE).as_posix() for path in CANDIDATE.rglob("*") if path.is_file()}
require(actual == set(manifest["files"]) | {"manifest.json"}, "Candidate closure differs")
source_map = json.loads((CANDIDATE / "source-map.json").read_bytes())
require(len(source_map) == 309, "Source count differs")
for name, row in source_map.items():
    relative = safe_relative(name)
    require(identity(ROOT / relative) == identity(CANDIDATE / "source" / relative) == row, "Current source differs: " + name)

require(identity(CANDIDATE / "profile-proposal.json") == {"bytes": 7844, "sha256": PROFILE_SHA}, "Profile differs")
profile = json.loads((CANDIDATE / "profile-proposal.json").read_bytes())
require(profile["id"] == "mixer.android-source-pair.3", "Wrong profile")
for kind in ("sdk", "adapter"):
    files = profile[kind + "_files"]
    require(len(files) == 22, "Wrong profile member count")
    for name, row in files.items():
        if kind == "sdk":
            source = "sdk/" + name
        else:
            source = "native/android/" + ("engine/" if name.startswith("Sources/") else "") + name
        require(source_map[source] == row, "Profile source identity differs")
    projection = hashlib.sha256("".join(name + "\0" + files[name]["sha256"] + "\n" for name in sorted(files)).encode()).hexdigest()
    require(projection == profile[kind + "_compatibility_sha256"], "Projection differs")
require(profile["adapter_compatibility_sha256"] == "57606aa94648f3b43f1bd84cc5d7479be133e3ff3c948d4830b1645466f348f6", "Adapter literal differs")
require(profile["sdk_compatibility_sha256"] == "4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7", "SDK literal differs")
compiled = (ROOT / "cli/Sources/MixerBuild/AndroidSDKCompatibility.swift").read_text()
require(compiled.count('Data(#"""') == 1, "Ambiguous compiled data literal")
partial = json.loads(compiled.split('Data(#"""', 1)[1].split('"""#.utf8)', 1)[0])
require(partial == json.loads((ROOT / "verification/android-private-owner-integration-implementation/candidate-3/profile-proposal.json").read_bytes()), "Partial root profile3 edits changed")
old = json.loads((ROOT / "verification/android-private-owner-profile3-integration/before/profile2.json").read_bytes())
require(old["id"] == "mixer.android-source-pair.2", "Prior compiled policy changed")
for key in ("sdk_files", "sdk_compatibility_sha256", "wire", "default_descriptor"):
    require(old[key] == profile[key], "Unselected policy change: " + key)
require(set(profile["adapter_files"]) - set(old["adapter_files"]) == {
    "app/src/dev/mixer/android/NativeOwnerV2.java", "app/src/dev/mixer/android/OwnerLifecycleV2.java"}, "Unexpected added adapter member")
require(not set(old["adapter_files"]) - set(profile["adapter_files"]), "Removed adapter member")
core = "native/android/app/src/dev/mixer/android/OwnerLifecycleV2.java"
require(source_map[core] == {"bytes": 12473, "sha256": "4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6"}, "Core bytes changed")
require(not (ROOT / "native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java").exists(), "Old core path remains")
leaf_path = ROOT / "verification/android-private-owner-integration-implementation/leaf-candidate-3/manifest.json"
require(identity(leaf_path)["sha256"] == "d772bfae9febf9106b1338be259cb026e4293d8e287fa792939340754ccdda38", "Leaf3 seal differs")
leaf = json.loads(leaf_path.read_bytes())
require(len(leaf["files"]) == 74, "Leaf count differs")
for name, row in leaf["files"].items():
    require(source_map[name] == row, "Reviewed mechanical leaf differs")

receipt = json.loads((CANDIDATE / "receipt.json").read_bytes())
require(not receipt["compiled_profile_literals_changed_by_this_lane"] and not receipt["CLI_consumer_qualification_run"], "Unexpected consumer claim")
for label in receipt["final_evidence"]:
    evidence = json.loads((CANDIDATE / "evidence" / label / "receipt.json").read_bytes())
    require(evidence["status"] in ("passed-host-only", "passed-crosscompile-only", "pass"), "Final command failure")
    require(evidence.get("source_stable", True), "Source instability")
swift_map = json.loads((CANDIDATE / "evidence/swift-jni-final-1/source-map.json").read_bytes())
swift_inputs = {name: row for name, row in swift_map.items() if name.startswith(("sdk/", "native/android/engine/", "native/android/bridge/"))}
require(len(swift_inputs) == 76, "Swift/JNI input count")
for name, row in swift_inputs.items():
    require(identity(ROOT / name) == row, "Swift/JNI input drift")

review_root = ROOT / "verification/android-private-owner-independent-review/implementation-review-2"
review_manifest = review_root / "manifest.json"
review_sha = "f9f1b610a6a7bfb7918be64f27b19b95a44682348168407c5af079405ca289ab"
require(identity(review_manifest)["sha256"] == review_sha, "Candidate3 independent rejection changed")
review = json.loads(review_manifest.read_bytes())
require(len(review["files"]) == review["members"] == 464, "Independent rejected review member count")
require(sum(m["bytes"] for m in review["files"].values()) == review["bytes"] == 9232067, "Independent rejected review bytes")
for name, row in review["files"].items():
    require(name.startswith("verification/android-private-owner-independent-review/implementation-review-2/") or name == "docs/android-private-owner-candidate3-review.md", "Review path outside scope")
    require(identity(ROOT / safe_relative(name)) == row, "Independent rejection member changed: " + name)
old_candidate = ROOT / "verification/android-private-owner-integration-implementation/candidate-3/manifest.json"
require(identity(old_candidate)["sha256"] == "c5bed3d89498abe0f9d9ee2547e74f4b26d2f29a05c9744e09b61d47259ecb6b", "Old candidate seal changed")
old_manifest = json.loads(old_candidate.read_bytes())
for name, row in old_manifest["files"].items():
    require(identity(old_candidate.parent / safe_relative(name)) == row, "Old candidate changed: " + name)
proof = json.loads((CANDIDATE / "source/verification/android-private-owner-integration-implementation/source-and-boundary-proof.json").read_bytes())
barriers = json.loads((CANDIDATE / "source/verification/android-private-owner-integration-implementation/barrier-map.json").read_bytes())
require(len(barriers["records"]) == 189, "New barrier inventory")

result = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
    "script_sha256": identity(Path(__file__))["sha256"],
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "corrected-private-owner-candidate-admitted-for-independent-host-review-CLI-held",
    "candidate": CANDIDATE.relative_to(ROOT).as_posix(), "candidate_manifest_sha256": SEAL_SHA,
    "candidate_members": 1246, "candidate_bytes": 11884760, "current_source_members_verified": 309,
    "profile_proposal_sha256": PROFILE_SHA, "profile_id": profile["id"],
    "adapter_members": 22, "adapter_projection_sha256": profile["adapter_compatibility_sha256"],
    "sdk_members": 22, "sdk_projection_sha256": profile["sdk_compatibility_sha256"],
    "default_descriptor": profile["default_descriptor"], "wire_unchanged": True,
    "accepted_core_move_exact": True, "accepted_leaf3_members_unchanged": 74,
    "Swift_JNI_unchanged_inputs_verified": 76,
    "independent_review_ownership": ["verification/android-private-owner-independent-review/implementation-review-3/**", "docs/android-private-owner-candidate4-review.md"],
    "independent_review_scope": "Read admitted immutable candidate, accepted contracts and own sealed preaccess/leaf review. Author independent tests against exact actual subjects and mechanical leaves; verify descriptor/BCI/source/caller/barrier and cleanup obligations; bounded direct host Java compilation/execution only. Never execute producer runners as independent evidence.",
    "CLI_implementation_ownership": ["cli/Sources/MixerBuild/AndroidSDKCompatibility.swift", "cli/Sources/MixerBuild/Resources/android-build.py", "cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift", "cli/Tests/MixerBuildTests/AndroidProjectTests.swift", "verification/android-private-owner-profile3-integration/**", "docs/android-private-owner-profile3-integration.md"],
    "CLI_implementation_scope": "Future scope only, not authorized by this receipt. Profile literal migration remains held until corrected independent findings and exact source qualification are assessed.",
    "source_contract_only_not_product_acceptance": True,
    "prior_candidate3_rejection_manifest_sha256": review_sha,
    "prior_candidate3_review_members_verified": 464,
    "prior_candidate3_review_bytes_verified": 9232067,
    "candidate3_unchanged_members_verified": 1215,
    "producer_selected_sites": 189, "producer_matrix_rows": 1323,
    "producer_matrix_assertions": 14477, "producer_orchestration_cases": 216,
    "producer_orchestration_assertions": 1101,
    "profile_literal_migration_authorized": False,
    "candidate3_hold_remains_for_CLI": True,
    "candidate3_gate_hold_sha256": "e215582b755848778b125c77dc73eb64e0195db33d8768e5e936c02daecb79cb",
    "root_preflight": "First check stopped before admission at renamed producer receipt field compiled_profile_literals_changed_by_this_lane; corrected schema name without changing candidate bytes or expected value.",
    "source_mutations_authorized": False,
    "implementation_accepted": False, "CLI_consumer_qualification_accepted": False,
    "native_runtime_or_capture_started": False, "physical_phone_tests_pending": True,
    "literal_allocation_exhaustion_induced": False, "public_V2_enabled": False, "GA_qualified": False,
}
destination = OUT / "candidate-4-admission.json"
require(not destination.exists(), "Admission already exists")
destination.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"path": destination.relative_to(ROOT).as_posix(), **identity(destination)}))
