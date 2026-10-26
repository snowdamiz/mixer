"""Verify frozen private owner sources, select exact profile literals, admit host review."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "verification/android-private-owner-integration-implementation/candidate-2"
SEAL_SHA = "dc75c6544fdc10d25457c00782dcfb8afbcde756988ce0fd742606bb69c8c0e7"
PROFILE_SHA = "fbce4fe52b6a1d26d54fe1b8a1366c3d1558d09ded2c145bee83ab941f9eae27"


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
require(len(manifest["files"]) == manifest["members"] == 1170, "Candidate member count")
require(sum(row["bytes"] for row in manifest["files"].values()) == manifest["bytes"] == 11537811, "Candidate bytes")
actual = {path.relative_to(CANDIDATE).as_posix() for path in CANDIDATE.rglob("*") if path.is_file()}
require(actual == set(manifest["files"]) | {"manifest.json"}, "Candidate closure differs")
source_map = json.loads((CANDIDATE / "source-map.json").read_bytes())
require(len(source_map) == 300, "Source count differs")
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
require(profile["adapter_compatibility_sha256"] == "4c6975e456f248e13f4024235aea6543335d0b9cc1c3418438f639d4d81eefeb", "Adapter literal differs")
require(profile["sdk_compatibility_sha256"] == "4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7", "SDK literal differs")
compiled = (ROOT / "cli/Sources/MixerBuild/AndroidSDKCompatibility.swift").read_text()
require(compiled.count('Data(#"""') == 1, "Ambiguous compiled data literal")
old = json.loads(compiled.split('Data(#"""', 1)[1].split('"""#.utf8)', 1)[0])
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
require(not receipt["compiled_profile_literals_changed"] and not receipt["CLI_consumer_qualification_run"], "Unexpected consumer claim")
for label in receipt["final_evidence"]:
    evidence = json.loads((CANDIDATE / "evidence" / label / "receipt.json").read_bytes())
    require(evidence["status"] in ("passed-host-only", "passed-crosscompile-only", "pass"), "Final command failure")
    require(evidence.get("source_stable", True), "Source instability")
swift_map = json.loads((CANDIDATE / "evidence/swift-jni-final-1/source-map.json").read_bytes())
swift_inputs = {name: row for name, row in swift_map.items() if name.startswith(("sdk/", "native/android/engine/", "native/android/bridge/"))}
require(len(swift_inputs) == 76, "Swift/JNI input count")
for name, row in swift_inputs.items():
    require(identity(ROOT / name) == row, "Swift/JNI input drift")

result = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
    "script_sha256": identity(Path(__file__))["sha256"],
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "frozen-private-owner-candidate-admitted-for-independent-host-review-and-exact-profile3-integration",
    "candidate": CANDIDATE.relative_to(ROOT).as_posix(), "candidate_manifest_sha256": SEAL_SHA,
    "candidate_members": 1170, "candidate_bytes": 11537811, "current_source_members_verified": 300,
    "profile_proposal_sha256": PROFILE_SHA, "profile_id": profile["id"],
    "adapter_members": 22, "adapter_projection_sha256": profile["adapter_compatibility_sha256"],
    "sdk_members": 22, "sdk_projection_sha256": profile["sdk_compatibility_sha256"],
    "default_descriptor": profile["default_descriptor"], "wire_unchanged": True,
    "accepted_core_move_exact": True, "accepted_leaf3_members_unchanged": 74,
    "Swift_JNI_unchanged_inputs_verified": 76,
    "independent_review_ownership": ["verification/android-private-owner-independent-review/implementation-review-1/**", "docs/android-private-owner-implementation-review.md"],
    "independent_review_scope": "Read admitted immutable candidate, accepted contracts and own sealed preaccess/leaf review. Author independent tests against exact actual subjects and mechanical leaves; verify descriptor/BCI/source/caller/barrier and cleanup obligations; bounded direct host Java compilation/execution only. Never execute producer runners as independent evidence.",
    "CLI_implementation_ownership": ["cli/Sources/MixerBuild/AndroidSDKCompatibility.swift", "cli/Sources/MixerBuild/Resources/android-build.py", "cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift", "cli/Tests/MixerBuildTests/AndroidProjectTests.swift", "verification/android-private-owner-profile3-integration/**", "docs/android-private-owner-profile3-integration.md"],
    "CLI_implementation_scope": "Install only exact selected literals; preserve common Swift preaccess and rendered single-profile policy, no local-lock authority. Qualify fresh Debug/Release CLI, Python driver and copied-consumer admission/refusal families. Native candidate source/tests and SDK remain frozen; coordinate extra paths before edits.",
    "source_contract_only_not_product_acceptance": True,
    "implementation_accepted": False, "CLI_consumer_qualification_accepted": False,
    "native_runtime_or_capture_started": False, "physical_phone_tests_pending": True,
    "literal_allocation_exhaustion_induced": False, "public_V2_enabled": False, "GA_qualified": False,
}
destination = OUT / "candidate-2-admission.json"
destination.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"path": destination.relative_to(ROOT).as_posix(), **identity(destination)}))
