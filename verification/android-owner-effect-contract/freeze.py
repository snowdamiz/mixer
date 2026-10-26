#!/usr/bin/env python3
"""Freeze this source-only proposal. Never import or execute product/harness code."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
PROPOSAL = "docs/android-owner-effect-contract.md"
INPUTS = [
    "AGENTS.md",
    "mixer-product-plan.md",
    "PLAN.md",
    "docs/android-public-owner-contract.md",
    "docs/android-public-owner-core.md",
    "docs/android-public-owner-core-independent-review.md",
    "verification/android-public-owner-core-root-review/implementation-acceptance.json",
    "native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java",
    "native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java",
    "native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java",
    "native/android/app/src/dev/mixer/android/NativeRenderer.java",
    "native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java",
    "native/android/app/src/dev/mixer/android/MixerActivity.java",
    "cli/Sources/MixerBuild/AndroidSDKCompatibility.swift",
    "cli/Sources/MixerBuild/AndroidProject.swift",
    "cli/Sources/MixerBuild/ProjectGenerator.swift",
    "cli/Sources/MixerBuild/Resources/android-build.py",
    "cli/build-tests/test_android_sdk_compatibility.py",
    "native/android/build.py",
]
EXPECTED_CORE = "4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6"
EXPECTED_ACCEPTANCE = "a838023993c01ec52248f7750c3234726af5f8135341666e8f8768ce38f0d096"
EXPECTED_REVISION = "4e48ac1a3c1593d46c0dcbaf207053ff5e1b6d5d"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    if (PACKET / "receipt.json").exists() or (PACKET / "inputs").exists():
        raise SystemExit("Refusing to replace an existing frozen packet")
    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    commands = []

    def git(label, arguments):
        argv = [shutil.which("git"), *arguments]
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=15, check=False)
        commands.append({"label": label, "argv": argv, "cwd": str(ROOT),
                         "timeout_seconds": 15, "exit_code": result.returncode,
                         "stdout": result.stdout.decode(), "stderr": result.stderr.decode()})
        if result.returncode:
            raise SystemExit("Source-only git command failed")
        return result.stdout.decode().strip()

    revision = git("context", ["rev-parse", "HEAD"])
    git_version = git("git-version", ["--version"])
    if revision != EXPECTED_REVISION:
        raise SystemExit("Context revision changed; obtain a new root selection")
    selected = {}
    for relative in INPUTS:
        source = ROOT / relative
        if source.is_symlink() or not source.is_file():
            raise SystemExit("Selected source must be an ordinary file: " + relative)
        data = source.read_bytes()
        selected[relative] = {**identity(data), "snapshot": "inputs/" + relative}
    core = "native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java"
    acceptance = "verification/android-public-owner-core-root-review/implementation-acceptance.json"
    if selected[core]["sha256"] != EXPECTED_CORE or selected[acceptance]["sha256"] != EXPECTED_ACCEPTANCE:
        raise SystemExit("Accepted core/receipt identity differs")
    proposal = (ROOT / PROPOSAL).read_bytes()
    whitespace = [index for index, line in enumerate(proposal.decode().splitlines(), 1)
                  if line.rstrip() != line]
    if whitespace or not proposal.endswith(b"\n"):
        raise SystemExit("Proposal whitespace diagnostic failed")
    tree_records = b"".join((path + "\0" + selected[path]["sha256"] + "\n").encode()
                            for path in sorted(selected))
    for relative, record in selected.items():
        data = (ROOT / relative).read_bytes()
        if identity(data) != {key: record[key] for key in ("bytes", "sha256")}:
            raise SystemExit("Selected source changed while freezing: " + relative)
        destination = PACKET / record["snapshot"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (PACKET / "proposal.md").write_bytes(proposal)
    python_binary = Path(sys.executable).resolve()
    git_binary = Path(shutil.which("git")).resolve()
    command = [sys.executable, "-B", str(Path(__file__).resolve())]
    write(PACKET / "command-results.json", {
        "at": at, "invocation": command, "cwd": str(ROOT),
        "python_version": sys.version, "git_version": git_version,
        "tool_binaries": {str(python_binary): identity(python_binary.read_bytes()),
                          str(git_binary): identity(git_binary.read_bytes())},
        "subprocess_commands": commands,
        "file_operation": "Read exactly the allowlisted ordinary files; hash and copy bytes; no product imports or execution",
        "proposal_whitespace_diagnostic": {"trailing_whitespace_lines": whitespace, "final_newline": True},
        "exit_code": 0,
    })
    write(PACKET / "selected-inputs.json", {
        "schema": 1, "context_revision": revision, "members": len(selected),
        "tree_digest_rule": "SHA256 of sorted UTF-8 relative path + NUL + lowercase SHA256 + LF",
        "tree_sha256": hashlib.sha256(tree_records).hexdigest(), "inputs": selected,
    })
    write(PACKET / "receipt.json", {
        "schema": 1, "at": at, "command": command, "context_revision": revision,
        "status": "source-contract-proposal-for-root-selection",
        "delegation": {"requested_model": "gpt-6.1-sol", "requested_reasoning_effort": "xhigh",
                       "fresh_context": True, "bounded_ownership": [PROPOSAL, "verification/android-owner-effect-contract/**"]},
        "selected_input_count": len(selected), "selected_input_tree_sha256": hashlib.sha256(tree_records).hexdigest(),
        "proposal": {"path": PROPOSAL, "snapshot": "proposal.md", **identity(proposal)},
        "accepted_core_identity_verified": True, "accepted_root_receipt_identity_verified": True,
        "all_42_profile_members_reverified": False,
        "recommended_next_slice": "Repair concrete observer listener lifecycle with root-selected successor source-pair migration",
        "implementation_selected_by_this_packet": False,
        "product_source_edited": False, "profile_or_lock_changed": False,
        "product_or_harness_code_imported_or_executed": False,
        "compilation_or_tests_executed": False,
        "native_runtime_or_capture_started_or_queried": False,
        "unrelated_processes_queried_or_changed": False,
        "network_or_platform_document_fetch_performed": False,
        "new_dependencies": [], "public_V2_selected": False, "GA_qualified": False,
        "cleanup": {"owned_git_children_returned_and_reaped": True, "scratch_created": False,
                    "native_or_capture_instances_created": False},
        "pending": ["Root implementation/profile/control selection", "Actual observer repair and executable host tests",
                    "Cross-compilation", "Private effect runner and terminal/native integration",
                    "Paused Android native runtime matrix", "Final physical-phone matrix",
                    "API28-35 and unsupported accessibility/resources/fonts", "Saved-state continuity",
                    "Immutable separately published FieldLog packages", "Signing/store/operational/accountable GA acceptance"],
        "scope": "File-byte inspection, contract proposal, frozen selected input snapshots and source-only packet diagnostics; no execution evidence",
    })
    members = {}
    for path in sorted(PACKET.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            members[path.relative_to(PACKET).as_posix()] = identity(path.read_bytes())
    write(PACKET / "manifest.json", {"schema": 1, "members": len(members),
                                    "bytes": sum(item["bytes"] for item in members.values()), "files": members})
    print(json.dumps({"status": "source-contract-proposal-frozen", "selected_inputs": len(selected),
                      "packet_members": len(members), "selected_tree_sha256": hashlib.sha256(tree_records).hexdigest(),
                      "manifest_sha256": identity((PACKET / "manifest.json").read_bytes())["sha256"],
                      "proposal_sha256": identity(proposal)["sha256"], "product_execution": False}, sort_keys=True))


if __name__ == "__main__":
    main()
