"""Root custody check and explicit bounded implementation selection; no product execution."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
BASE = "559858810e133640d52730972a6610e98442be6d"
PACKETS = {
    "android-copied-sdk-appearance-contract": ("e08abcacc8421eb2415daa259cf0f9d67a9e2fafa7a879f0b95f574866f62ffb", 87, 971695),
    "android-copied-sdk-appearance-contract-review": ("24d998719e2c5be67fd55a3426340bc8294b07aa78bbf0a8b9ac05bf0de287a9", 156, 1681087),
    "android-copied-sdk-appearance-contract-correction": ("08841ed0fd50b5ee0f42b98dbcd5a8751d36ca4712ce0792f929ee933ee3fbdb", 140, 752291),
    "android-copied-sdk-appearance-contract-correction-review": ("021da51d7a154c0dc030b019df4a8b29ecd9c858c858df989c8e19556d98eb40", 161, 1447633),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")


errors = []
packets = []
for packet, (seal_sha, count, byte_count) in PACKETS.items():
    seal_path = ROOT / "verification" / packet / "seal.json"
    raw = seal_path.read_bytes()
    assert sha(raw) == seal_sha, packet
    files = json.loads(raw)["files"]
    total = 0
    for name, meta in files.items():
        rel = pathlib.PurePosixPath(name)
        assert not rel.is_absolute() and ".." not in rel.parts
        data = (ROOT / name).read_bytes()
        total += len(data)
        if len(data) != meta["bytes"] or sha(data) != meta["sha256"]:
            errors.append(name)
    assert len(files) == count and total == byte_count
    packets.append({"packet": packet, "seal_sha256": seal_sha, "members": count, "bytes": total})

observation_path = ROOT / "verification/android-copied-sdk-appearance-contract/proposed-profile-observation.json"
observation = json.loads(observation_path.read_text())
sources = []
for key in ("sdk_files", "adapter_files"):
    for name, meta in observation[key].items():
        if key == "sdk_files":
            path = "sdk/" + name
        elif name.startswith("Sources/"):
            path = "native/android/engine/" + name
        else:
            path = "native/android/" + name
        data = (ROOT / path).read_bytes()
        git_data = subprocess.run(["git", "show", BASE + ":" + path], cwd=ROOT,
                                  capture_output=True, check=True, timeout=15).stdout
        assert len(data) == meta["bytes"] and sha(data) == meta["sha256"] and data == git_data, path
        sources.append({"path": path, **meta})
assert len(sources) == 42
audit = {
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python_version": sys.version,
    "checker_sha256": sha(pathlib.Path(__file__).read_bytes()),
    "source_revision": BASE,
    "git_command": ["git", "show", "<source_revision>:<named source path>"],
    "packets": packets,
    "total_members": sum(x["members"] for x in packets),
    "total_bytes": sum(x["bytes"] for x in packets),
    "profile_sources_equal_accepted_git_and_live": sources,
    "errors": errors,
    "product_executed": False,
}
write("correction-review-admission.json", audit)
assert not errors
selection = {
    "schema": 1,
    "at": audit["at"],
    "status": "corrected-contract-with-ascii-root-amendment-selected-for-implementation",
    "source_revision": BASE,
    "root_admission": "verification/android-copied-sdk-appearance-contract-root-review/correction-review-admission.json",
    "contract": "docs/android-copied-sdk-appearance-contract.md",
    "correction": "docs/android-copied-sdk-appearance-contract-correction.md",
    "independent_review": "docs/android-copied-sdk-appearance-contract-correction-review.md",
    "independent_review_sha256": "801b275ebebc917022907de7f49307dfb985c225539f6fcba44643ea642378e7",
    "selected_profile_id": "mixer.android-source-pair.1",
    "profile_source_observation": str(observation_path.relative_to(ROOT)),
    "profile_source_observation_sha256": sha(observation_path.read_bytes()),
    "sdk_projection_sha256": observation["sdk_compatibility_sha256"],
    "adapter_projection_sha256": observation["adapter_compatibility_sha256"],
    "default_descriptor": observation["default_descriptor"],
    "explicit_amendments": [
        "Reject every non-ASCII SDK-root entry name before any selector classification, transformation, entry following, copying or generic hashing. Then reserve the ASCII case-insensitive Package prefix and allow only exact ordinary pinned Package.swift. Applies to selected input, staged/generated SDK, common Swift project admission, rendered Python build and linked-SDK consistency. Unrelated Unicode root names are deliberately rejected; no recursive ASCII rule is added to excluded inner trees.",
        "Android-required is true for a requested Android operation OR configuration.targets containing android OR an Android lock. Missing locks/profiles, legacy records, unknown or mismatched profiles fail before generic required-source reads, tools and export output. Existing iOS-only contract remains unchanged.",
        "The internal compiled Swift value is the sole expected policy. Render its JSON as hexadecimal into exactly one driver template marker. Decode only at Python build entry; raw import/inspect must remain usable. No mutable source, lock or bundle metadata refreshes policy.",
    ],
    "ownership": [
        "cli/Sources/MixerBuild/AndroidSDKCompatibility.swift",
        "cli/Sources/MixerBuild/AndroidProject.swift",
        "cli/Sources/MixerBuild/ProjectGenerator.swift",
        "cli/Sources/MixerBuild/Resources/android-build.py",
        "cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift",
        "cli/Tests/MixerBuildTests/AndroidProjectTests.swift",
        "cli/Tests/MixerBuildTests/ProjectGeneratorTests.swift",
        "cli/build-tests/test_android_sdk_compatibility.py",
        "cli/build-tests/test_android_staging.py",
        "cli/build-tests/test_android_appearance.py",
        "docs/android-copied-sdk-appearance-implementation.md",
        "verification/android-copied-sdk-appearance-implementation/**",
    ],
    "ownership_note": "Additive Android lock profile lives with AndroidToolchainLock in AndroidProject.swift. Coordinate before modifying any additional file, tests or public contract. Preserve all six accepted packaging files' unrelated behavior.",
    "acceptance_requirements": [
        "Debug and Release actual create/common verifyLock/run/direct Android build/export admission tests; exact maps and directories; case/type/length/hidden/symlink/special-file/manifest aliases; lock and config-based Android detection; failure cleanup and no-output/tool/read ordering.",
        "Both Kelvin manifest aliases and unrelated Unicode SDK-root names through input and generated Swift/Python entrypoints, independent local lock recomputation, ordinary identical relocation positive. Retain earlier SwiftPM redirection evidence; do not evaluate unadmitted fixtures during product work.",
        "Actual CLI create, one-marker render, installed official raw inspect and generated driver build admission; raw import/inspect works, raw build refuses, malformed/missing/duplicate markers refuse. Existing asset/source locks, containment, resource refusal, typed codec and final archive byte checks remain covered.",
        "Fresh copied consumer executes default canonical roundtrip, session, prepare/commit/abort, schema/successor/identity/full UInt64 and rejection cases; production pure Java codecs receive actual copied Swift output. Bind sources/classes/outputs and separately pin contracts/ui-v1.json. No repository SDK fallback.",
        "Use bounded host-only subprocess groups/deadlines; preserve failed attempts and partial output; reap owned children then remove owned scratch. Rerun changed target compilation only when inputs require it. No whole APK is necessary when native target inputs remain identical.",
        "Independent implementation review and root acceptance are required before delivery. Root owns metadata, exact staging, commit/push and CI observation.",
    ],
    "contract_selected": True,
    "implementation_selected": True,
    "implementation_accepted": False,
    "public_v2_or_native_runtime_changed": False,
    "GA_qualified": False,
    "limits": [
        "Exact first-party source-pair development admission, no compatibility range or stable native ABI claim.",
        "Local drivers and locks remain mutable/unauthenticated. No hostile-writer race-free guarantee or broad filesystem hardening beyond the specified closure.",
        "Native/UI/capture testing remains paused; physical phones disconnected. Installed runtime, API28 support, resources/fonts/OS/input/accessibility/design, signing, immutable FieldLog packages, release/store/operational and accountable GA gates remain pending.",
        "No SDK, Java/JNI/runtime, public Activity, ProcessRunner, dependency, hosted, production publication or credential changes are selected.",
    ],
}
write("implementation-selection.json", selection)
print(json.dumps({"members": audit["total_members"], "bytes": audit["total_bytes"],
                  "matched_sources": len(sources), "selection_sha256": sha((OUT / "implementation-selection.json").read_bytes()),
                  "errors": errors}))
