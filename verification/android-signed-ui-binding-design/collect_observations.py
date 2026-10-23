#!/usr/bin/env python3
"""Record design inspection inputs/tools; does not build or qualify a binding."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
INPUTS = [
    "AGENTS.md",
    "docs/android-signed-guest-ui-design.md",
    "docs/android-guest-ui-transport-design.md",
    "capability-activation/Package.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIRuntime.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIPresentation.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIApple.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIDiagnostics.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartControl.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartRuntime.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartWorker.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityAttemptReservation.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityInstalledExecutionMode.swift",
    "sdk/Sources/MixerGuest/GuestUIExchangeV1.swift",
    "sdk/Sources/MixerGuest/GuestUIWakeV1.swift",
    "sdk/Sources/MixerUI/Reconciliation.swift",
    "native/android/bridge/jni.c",
    "native/android/bridge/mixer_android.h",
    "native/android/engine/Sources/MixerAndroidEngine/Bridge.swift",
    "native/android/engine/Sources/MixerAndroidRuntime/SessionRegistry.swift",
    "native/android/app/src/dev/mixer/android/NativeRenderer.java",
    "native/android/app/src/dev/mixer/android/UiPacket.java",
    "native/android/app/src/dev/mixer/android/MixerActivity.java",
    "native/android/signed-guest-ui/transport/include/mixer_ui_transport.h",
    "native/android/signed-guest-ui/transport/internal.h",
    "native/android/signed-guest-ui/transport/transport.c",
    "native/android/signed-guest-ui/transport/platform_android.c",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    return {name: digest(ROOT / name) for name in INPUTS}


def run(argv, name, required=True):
    result = subprocess.run(argv, cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=30, check=False)
    log = OUT / (name + ".log")
    log.write_text(result.stdout)
    return {"argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
            "required": required,
            "output": str(log.relative_to(ROOT)), "output_sha256": digest(log)}


before = manifest()
commands = [
    run(["git", "rev-parse", "HEAD"], "source-revision"),
    run(["git", "status", "--short"], "source-status"),
    run([sys.executable, "--version"], "python-version"),
    run(["git", "--version"], "git-version"),
    run(["swift", "--version"], "swift-version"),
    run(["clang", "--version"], "clang-version"),
    run(["javac", "-version"], "javac-default-version", required=False),
    run(["/opt/homebrew/opt/openjdk/bin/javac", "-version"], "javac-installed-version"),
]
after = manifest()
manifest_path = OUT / "source-manifest.sha256"
manifest_path.write_text("".join(f"{value}  {name}\n" for name, value in after.items()))
tree_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
proposal = ROOT / "docs/android-signed-ui-binding-design.md"
receipt = {
    "status": "proposal_only_awaiting_root_review",
    "collected_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision": (OUT / "source-revision.log").read_text().strip(),
    "selected_source_manifest": str(manifest_path.relative_to(ROOT)),
    "selected_source_manifest_sha256": tree_digest,
    "selected_sources_unchanged_during_observation": before == after,
    "changed_selected_sources": [p for p in INPUTS if before[p] != after[p]],
    "proposal": str(proposal.relative_to(ROOT)),
    "proposal_sha256": digest(proposal),
    "collector_sha256": digest(Path(__file__).resolve()),
    "commands": commands,
    "observations": [
        "Apple-only facade and @MainActor binding inspected; non-Apple bind currently throws presentationInvariant.",
        "Worker binds before construction/startup; observation finish really awaits presentation Task.value.",
        "Current reservation has store and adapter obligations, without a presentation obligation.",
        "C request sets its own hint and schedules immediate work, not a passive future-change wait.",
        "C callback advances return fence on next callback entry; no existing fence-progress hook.",
        "C required drain/complete hooks carry only numeric identities; fixed16 slots and singleton pipe baseline.",
        "Compiled Android reducer/JNI Activity is synchronous and separate from proposed signed binding.",
        "Existing Java renderer captures packet in listeners; proposed signed listeners require scalar identities.",
    ],
    "official_sources_read": [
        "https://developer.android.com/reference/android/os/Looper",
        "https://developer.android.com/ndk/guides/jni-tips",
        "https://developer.android.com/reference/android/view/Choreographer.FrameCallback",
        "https://developer.android.com/reference/android/view/ViewTreeObserver.OnDrawListener",
    ],
    "scope": "Selected source inspection and installed host tool version inventory only.",
    "limitations": [
        "No production source, public contract, dependency, status/gate or release authorization changed.",
        "No new binding implementation, build, executable test, JNI or Android Looper execution.",
        "The default javac launcher has no selected Java runtime; installed Homebrew OpenJDK version is recorded separately.",
        "Existing C test/review receipts are referenced context, not rerun or binding qualification.",
        "No physical phone discovery, query, run or reconnect request; no emulator execution either.",
        "No package/tool download, signature validation, publication, customer message, commit or push.",
    ],
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
if before != after:
    raise SystemExit("Selected sources changed; inspect receipt before accepting snapshot")
if any(command["exit_code"] and command["required"] for command in commands):
    raise SystemExit("One or more observations failed; inspect command logs")
print("Proposal inspection recorded; no binding acceptance tests executed.")
