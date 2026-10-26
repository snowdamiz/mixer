#!/usr/bin/env python3
"""Freeze this proposal's small named input set; never run prior collectors."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
REVISION = "1f114d8f235e8042c275a2549fef7d4994272360"
NATIVE_BASE = "559858810e133640d52730972a6610e98442be6d"
DOC = "docs/android-public-owner-contract.md"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(name, value):
    (PACKET / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git_blob(revision, path):
    return subprocess.run(["git", "show", f"{revision}:{path}"], cwd=ROOT,
                          check=True, capture_output=True).stdout


def main():
    if (PACKET / "manifest.json").exists():
        raise SystemExit("Frozen packet already exists; do not overwrite evidence")
    commands = []
    for argv in (["git", "rev-parse", "HEAD"], ["git", "--version"],
                 [sys.executable, "--version"]):
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        commands.append({"argv": argv, "exit_code": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            raise SystemExit("Version/context command failed")
    if commands[0]["stdout"].strip() != REVISION:
        raise SystemExit("Context revision changed before freeze")

    profile_path = "cli/Sources/MixerBuild/AndroidSDKCompatibility.swift"
    profile_source = git_blob(REVISION, profile_path).decode()
    # Extract the already selected literal only to check its existing identities.
    # This does not calculate a new source profile or authorize any release.
    profile = json.loads(profile_source.split('Data(#"""', 1)[1].split('"""#.utf8', 1)[0])
    assert profile["id"] == "mixer.android-source-pair.1"
    assert len(profile["sdk_files"]) == 22 and len(profile["adapter_files"]) == 20
    bindings = {}
    for group in ("sdk_files", "adapter_files"):
        for relative, expected in profile[group].items():
            if group == "sdk_files":
                path = f"sdk/{relative}"
            elif relative.startswith("Sources/MixerAndroidRuntime/"):
                path = f"native/android/engine/{relative}"
            else:
                path = f"native/android/{relative}"
            data = git_blob(REVISION, path)
            if identity(data) != expected or data != git_blob(NATIVE_BASE, path):
                raise SystemExit(f"Accepted profile/base identity differs: {path}")
            if data != (ROOT / path).read_bytes():
                raise SystemExit(f"Current mapped source drift: {path}")
            bindings[path] = {**expected, "binding": "product-current-and-git",
                              "profile_group": group, "equal_native_base": True}

    extra = {
        "AGENTS.md": "context-git",
        "PLAN.md": "context-git",
        "mixer-product-plan.md": "context-git",
        "native/android/app/AndroidManifest.xml": "product-current-and-git",
        "cli/Sources/MixerBuild/Resources/android-build.py": "product-current-and-git",
        "native/android/engine/Sources/MixerAndroidEngine/Bridge.swift": "product-current-and-git",
        "native/android/tests/NativeCoordinatorV2IntegrationActivity.java": "product-current-and-git",
        "native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java": "product-current-and-git",
        "cli/Sources/MixerBuild/AndroidProject.swift": "product-current-and-git",
        "cli/Sources/MixerBuild/ProjectGenerator.swift": "product-current-and-git",
        profile_path: "product-current-and-git",
        "docs/android-public-appearance-routing-proposal.md": "context-git",
        "verification/android-copied-sdk-appearance-contract-root-review/implementation-acceptance.json": "context-git"
    }
    for path, mode in extra.items():
        data = git_blob(REVISION, path)
        if mode == "product-current-and-git" and data != (ROOT / path).read_bytes():
            raise SystemExit(f"Current reviewed source drift: {path}")
        bindings[path] = {**identity(data), "binding": mode}
    ordered = dict(sorted(bindings.items()))
    tree = hashlib.sha256(json.dumps(ordered, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write("source-bindings.json", {
        "schema": 1, "context_revision": REVISION, "native_base_revision": NATIVE_BASE,
        "tree_digest_algorithm": "sha256 of UTF-8 JSON(files), sorted keys, compact separators",
        "tree_sha256": tree, "files": ordered,
        "profile_id": profile["id"], "profile_sdk_files": 22, "profile_adapter_files": 20,
        "profile_sdk_digest": profile["sdk_compatibility_sha256"],
        "profile_adapter_digest": profile["adapter_compatibility_sha256"],
        "generated_default_descriptor_expected": profile["default_descriptor"],
        "wire": profile["wire"]
    })
    write("command-results.json", {
        "collector_argv": [sys.executable, "-B", str(Path(__file__).resolve())],
        "cwd": str(ROOT), "python_version": sys.version, "commands": commands,
        "source_commands": {
            "argv_pattern": ["git", "show", "<bound revision>:<bound path>"],
            "exit_code": 0, "output": "Exact blob lengths/hashes retained in source-bindings.json; source bodies are not duplicated",
            "scope": "55 contextual/product bindings and 42 comparisons to accepted native base; no compiler/runtime invocation"
        }
    })
    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write("receipt.json", {
        "schema": 1, "at": at, "status": "frozen-proposal-awaiting-root-selection",
        "context_revision": REVISION, "source_binding_tree_sha256": tree,
        "source_inputs": len(ordered), "accepted_profile_inputs_checked": 42,
        "accepted_native_base_unchanged": True,
        "accepted_upstream_source_binding_tree_sha256": "59b55224378dd2ce2ef2524d35b303f2dae7c913176d112a203541acb2ddd2c4",
        "scope": "Source-bound public-owner prerequisite contract, planned pure Java transition core and future deterministic controls only",
        "public_V2_selected": False, "product_source_changed": False,
        "model_or_behavior_tests": "not implemented or run; matrix is prospective",
        "packet_integrity_check": "verify.py; integrity is not behavioral or runtime acceptance",
        "native_runtime_or_capture_or_process_query": False,
        "pending": ["root contract selection", "pure core implementation and host behavior tests", "Android owner integration and actual native matrix after pause", "API28 support and OS/accessibility/resource/font coverage", "physical design parity", "signed immutable separate-repository FieldLog consumption", "signing, store, operational and accountable GA evidence"]
    })
    members = {DOC: identity((ROOT / DOC).read_bytes())}
    for path in sorted(PACKET.iterdir()):
        if path.is_file():
            members[path.relative_to(ROOT).as_posix()] = identity(path.read_bytes())
    write("manifest.json", {"schema": 1, "scope": "Proposal and minimal packet members; no copied historical packet", "members": members})
    print(json.dumps({"status": "frozen", "source_inputs": len(ordered),
                      "profile_inputs": 42, "sealed_members": len(members),
                      "source_binding_tree_sha256": tree}, sort_keys=True))


if __name__ == "__main__":
    main()
