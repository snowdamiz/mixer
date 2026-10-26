#!/usr/bin/env python3
"""Freeze a bounded source-only design packet. No product execution or acceptance."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
SOURCES = [
    "AGENTS.md", "PLAN.md", "mixer-product-plan.md",
    "docs/android-owner-effect-contract.md", "docs/android-public-owner-core.md",
    "native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java",
    "native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java",
    "native/android/app/src/dev/mixer/android/NativeRenderer.java",
    "native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java",
    "native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java",
    "native/android/app/src/dev/mixer/android/MixerActivity.java",
    "native/android/tests/NativeCoordinatorV2IntegrationActivity.java",
    "native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java",
    "native/android/tests/NativeAppearanceV2Activity.java",
    "native/android/tests/NativeAppearanceV2Instrumentation.java",
    "native/android/tests/NativeCoordinatorV2HostTests.java",
    "native/android/tests/NativeCoordinatorV2HostLeaves/dev/mixer/android/NativeRenderer.java",
    "native/android/tests/NativeEnvironmentV2ObserverHostTests.java",
    "native/android/tests/NativeEnvironmentV2ObserverHostLeaves/dev/mixer/android/NativeRenderer.java",
    "native/android/tests/run-owner-core-host.py",
    "cli/Sources/MixerBuild/AndroidSDKCompatibility.swift",
    "cli/Sources/MixerBuild/AndroidProject.swift",
    "verification/android-public-owner-core-root-review/implementation-acceptance.json",
    "verification/android-environment-observer-root-review/implementation-selection.json",
    "verification/android-environment-observer-lifecycle/candidate-proposal.json",
]
PROPOSAL = "docs/android-private-owner-effect-integration-proposal.md"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    if (PACKET / "receipt.json").exists():
        raise SystemExit("refuse to replace an existing freeze")
    commands = []
    for label, argv in [
        ("revision", ["git", "rev-parse", "HEAD"]),
        ("git-version", ["git", "--version"]),
    ]:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=10)
        commands.append({"argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
                         "stdout": result.stdout.decode(), "stderr": result.stderr.decode(),
                         "timeout_seconds": 10})
        if result.returncode != 0:
            write(PACKET / "failed-command.json", commands[-1])
            raise SystemExit("source metadata command failed; evidence retained")
    inputs = {}
    for name in SOURCES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise SystemExit("source must be a regular nonsymlink file: " + name)
        data = path.read_bytes()
        snapshot = PACKET / "inputs" / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(data)
        inputs[name] = identity(data)
    projected = "".join(name + "\0" + inputs[name]["sha256"] + "\n" for name in sorted(inputs)).encode()
    tools = {}
    for name, location in [("python", sys.executable), ("git", shutil.which("git"))]:
        path = Path(location).resolve(strict=True)
        tools[name] = {"path": str(path), **identity(path.read_bytes())}
    tools["python"]["version"] = sys.version
    tools["git"]["version"] = commands[1]["stdout"].strip()
    receipt = {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "source-only-proposal-unselected", "context_revision": commands[0]["stdout"].strip(),
        "freeze_command": [sys.executable, "-B", str(Path(__file__).resolve())],
        "cwd": str(ROOT), "tools": tools, "commands": commands, "inputs": inputs,
        "selected_input_projection_sha256": hashlib.sha256(projected).hexdigest(),
        "projection_is_full_repository_tree": False,
        "proposal": {"path": PROPOSAL, **identity((ROOT / PROPOSAL).read_bytes())},
        "new_general_purpose_dependencies": [],
        "product_sources_edited_by_lane": [], "implementation_selected": False,
        "product_tests_run": False, "cross_compilation_run": False,
        "native_runtime_or_capture_started": False, "process_discovery_performed": False,
        "network_install_signing_credentials_or_publication": False,
        "actual_cleanup_or_reclamation_proven": False, "GA_qualified": False,
        "upstream_status_at_read_boundary": {
            "owner_core": "accepted exact host decision implementation",
            "observer": "frozen Slice A candidate; root acceptance pending at lane dispatch",
            "later_root_update": "independent selected-slice pass reported; final seal/root acceptance still pending; not verified or accepted by this proposal",
        },
        "retained_tool_failure": {
            "tool": "apply_patch", "product_mutation": False,
            "operation": "proposal-only documentation refinement",
            "result": "apply_patch verification failed: Failed to find expected lines in /Users/andreyyurlov/Documents/dev/mixer/docs/android-private-owner-effect-integration-proposal.md:\nA token-allocation or\ncompletion failure after commit retires the whole lifetime; there is no retry.",
            "resolution": "Read actual lines; repeated the documentation patch using the exact existing context; succeeded.",
        },
        "limitations": [
            "This packet contains source custody and design checks only, not executable owner implementation or product-test evidence.",
            "Observer snapshots are frozen inputs; they are not accepted by this lane and cannot be changed until root coordinates selection.",
            "Computer use, screen capture, native simulator/emulator tests and physical phones remain unrun under the active pause/disconnection.",
            "Profile ID and hash literals, implementation selection, independent review, root acceptance and delivery remain root-owned.",
        ],
    }
    write(PACKET / "receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "frozen_inputs": len(inputs),
                      "bytes": sum(i["bytes"] for i in inputs.values()),
                      "projection_sha256": receipt["selected_input_projection_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
