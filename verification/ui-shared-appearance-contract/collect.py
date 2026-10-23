#!/usr/bin/env python3
"""Read-only input binding + declaration compilation, not product validation."""
from __future__ import annotations
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
INPUTS = (
    "AGENTS.md", "mixer-product-plan.md", "PLAN.md", "STATUS.md",
    "sdk/Sources/MixerUI/Authoring.swift", "sdk/Sources/MixerUI/Protocol.swift",
    "sdk/Sources/MixerUI/Validation.swift", "sdk/Sources/MixerUI/Reconciliation.swift",
    "sdk/Sources/MixerApple/MixerNativeView.swift",
    "native/android/app/src/dev/mixer/android/Json.java",
    "native/android/app/src/dev/mixer/android/UiPacket.java",
    "native/android/app/src/dev/mixer/android/NativeRenderer.java",
    "contracts/ui-v1.json", "contracts/guest-ui-event-v1.json",
    "contracts/runtime-identity-v2.json", "docs/android-jni-stage5-seams.md",
    "docs/android-signed-ui-binding-contract.md",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIApple.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIPresentation.swift",
)

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def manifest(paths: tuple[str, ...]) -> list[dict[str, object]]:
    return [{"path": p, "bytes": (ROOT / p).stat().st_size,
             "sha256": digest((ROOT / p).read_bytes())} for p in paths]

def run(argv: list[str]) -> dict[str, object]:
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False)
    return {"argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}

def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def main() -> None:
    locked_path = HERE / "input-lock.json"
    inputs = manifest(INPUTS)
    if not locked_path.exists():
        raise SystemExit("Missing explicit input-lock.json; collector cannot bless new inputs")
    locked = json.loads(locked_path.read_text())
    if inputs != locked["inputs"]:
        changed = [a["path"] for a, b in zip(inputs, locked["inputs"], strict=True) if a != b]
        raise SystemExit("Input drift: " + ", ".join(changed))
    java_bin = "/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home/bin"
    commands = [
        run(["git", "rev-parse", "HEAD"]), run(["git", "status", "--short"]),
        run(["swift", "--version"]), run([sys.executable, "--version"]),
        run([java_bin + "/java", "-version"]), run([java_bin + "/javac", "-version"]),
        run(["swiftc", "-swift-version", "6", "-warnings-as-errors", "-typecheck",
             str(HERE / "AppearanceDeclarationProbe.swift")]),
    ]
    owned_paths = (
        "docs/ui-shared-appearance-contract.md",
        "verification/ui-shared-appearance-contract/AppearanceDeclarationProbe.swift",
        "verification/ui-shared-appearance-contract/collect.py",
        "verification/ui-shared-appearance-contract/input-lock.json",
    )
    failed = [r for r in commands if r["exit_code"] != 0]
    receipt = {
        "schema": 1, "recorded_at": datetime.now(timezone.utc).isoformat(),
        "collector_argv": [sys.executable, *sys.argv],
        "collector_optimize": sys.flags.optimize,
        "interpreter_sha256": digest(pathlib.Path(sys.executable).read_bytes()),
        "scope": "design-only input binding and Swift declaration typecheck",
        "source_head_observation": commands[0]["stdout"].strip(),
        "bounded_input_tree_sha256": digest(canonical(inputs)),
        "inputs": inputs, "proposal_files": manifest(owned_paths),
        "commands": commands, "passed": not failed,
        "interpretation": "No product resolver/renderer was implemented or executed; compiler success establishes declaration representability only.",
        "pending": ["root contract acceptance", "Swift/Java shared-value implementation parity",
                    "native screenshot/reference-state review", "signed native configuration consumption",
                    "physical iOS/Android parity and accessibility", "full GA UI inventory",
                    "separate published immutable FieldLog", "release compatibility and GA acceptance"],
        "physical_devices": "disconnected; no discovery, runs or reconnect requests",
    }
    (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": not failed, "scope": receipt["scope"],
                      "input_tree_sha256": receipt["bounded_input_tree_sha256"],
                      "receipt": str(HERE / "receipt.json")}))
    if failed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
