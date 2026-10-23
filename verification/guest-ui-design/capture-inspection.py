#!/usr/bin/env python3
"""Capture read-only source observations for the guest UI design; runs no tests."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name("inspection.json")
SEAL = Path(__file__).with_name("root-accepted.json")
if SEAL.exists():
    raise SystemExit("Design receipt is sealed; preserve it and use a separate receipt for future work.")
if sys.argv[1:] not in ([], ["--seal"]):
    raise SystemExit("Usage: capture-inspection.py [--seal]")
SHOULD_SEAL = sys.argv[1:] == ["--seal"]
FILES = [
    "AGENTS.md", "mixer-product-plan.md",
    "sdk/Sources/MixerGuest/GuestUICodec.swift",
    "sdk/Sources/MixerUI/Protocol.swift",
    "sdk/Sources/MixerUI/Validation.swift",
    "sdk/Sources/MixerUI/Reconciliation.swift",
    "sdk/Sources/MixerApple/MixerNativeView.swift",
    "vm/include/mixer_vm.h", "vm/include/mixer_vm_capability.h",
    "vm/src/experimental_capability_guest/mod.rs",
    "vm/src/capability_ffi/api.rs",
    "vm/src/capability_ffi/error.rs",
    "vm/src/capability_ffi/exports.rs",
    "vm/src/ffi.rs",
    "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Session.swift",
    "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Native.swift",
    "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Ownership.swift",
    "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Failure.swift",
    "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Validation.swift",
    "capability-activation/Sources/MixerCapabilityActivation/InstalledCapabilityExecution.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityConcreteAttempt.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityAttemptSignals.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartControl.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartConfiguration.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartRuntime.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartWorker.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityRecoveryStore.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityRecoverySelection.swift",
    "docs/guest-ui-event-integration-design.md",
]
FILES += sorted(str(p.relative_to(ROOT)) for p in (ROOT / "contracts").glob("*.json"))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


observed = {}
for name in FILES:
    path = ROOT / name
    content = path.read_bytes()
    observed[name] = {
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "git_status": git("status", "--short", "--", name),
    }

receipt = {
    "schema": 1,
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "command": "python3 verification/guest-ui-design/capture-inspection.py" + (" --seal" if SHOULD_SEAL else ""),
    "tool": {"python": platform.python_version(), "git": git("--version")},
    "source_revision": git("rev-parse", "HEAD"),
    "source_tree": git("rev-parse", "HEAD^{tree}"),
    "captured_files": observed,
    "scope": "Read-only source inspection supporting a proposed design. No implementation tests, ABI validation, renderer/device runs, publication, or health qualification executed.",
    "limitations": [
        "Concurrent root coordinator files may be untracked or changing; captured SHA-256 values identify the inspected bytes, not a frozen integration commit.",
        "Requirements in the design acceptance matrix are pending implementation and execution.",
    ],
}
OUTPUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(f"Captured {len(observed)} source files at {receipt['source_revision']}; no tests run.")
if SHOULD_SEAL:
    design = "docs/guest-ui-event-integration-design.md"
    accepted = {
        "schema": 1,
        "status": "root_accepted",
        "accepted_on": "2026-10-23",
        "reviewer": "root integration agent",
        "design_path": design,
        "design_sha256": observed[design]["sha256"],
        "inspection_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "source_revision": receipt["source_revision"],
        "source_tree": receipt["source_tree"],
        "scope": "Root accepted this design and exact interfaces only. Implementation is separately coordinated; no runtime, compiler, renderer, device, publication, or GA qualification is established.",
    }
    with SEAL.open("x") as sealed:
        sealed.write(json.dumps(accepted, indent=2, sort_keys=True) + "\n")
    print(f"Sealed root-accepted design SHA-256 {accepted['design_sha256']}.")
