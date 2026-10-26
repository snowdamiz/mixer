#!/usr/bin/env python3
"""Freeze only selected contracts and accepted Git inputs before candidate access."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
REVISION = "559858810e133640d52730972a6610e98442be6d"
SELECTION = "verification/android-copied-sdk-appearance-contract-root-review/implementation-selection.json"
SELECTION_SHA = "cb191b996f00752c4cad3a4c1df7314bcfe72b00b1f75be29a2f6e4301821917"
COMMANDS: list[dict] = []


def identity(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save(relative: str, data: bytes) -> None:
    path = PACKET / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def command(label: str, argv: list[str]) -> bytes:
    completed = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30, check=False)
    save(f"commands/{label}.stdout", completed.stdout)
    save(f"commands/{label}.stderr", completed.stderr)
    COMMANDS.append({"label": label, "argv": argv, "cwd": str(ROOT), "timeout_seconds": 30,
                     "exit_code": completed.returncode,
                     "stdout": identity(completed.stdout), "stderr": identity(completed.stderr)})
    if completed.returncode:
        raise RuntimeError(f"{label}: {completed.returncode}")
    return completed.stdout


def main() -> None:
    if (PACKET / "seal.json").exists():
        raise SystemExit("preaccess baseline already sealed; do not overwrite")
    selection_bytes = (ROOT / SELECTION).read_bytes()
    assert identity(selection_bytes)["sha256"] == SELECTION_SHA
    selection = json.loads(selection_bytes)
    assert selection["source_revision"] == REVISION
    contract_paths = [
        "AGENTS.md", "PLAN.md", "mixer-product-plan.md", SELECTION,
        "docs/android-copied-sdk-appearance-contract.md",
        "docs/android-copied-sdk-appearance-contract-correction.md",
        "docs/android-copied-sdk-appearance-contract-correction-review.md",
        "verification/android-copied-sdk-appearance-contract/proposed-profile-observation.json",
        "verification/android-copied-sdk-appearance-contract-correction-review/handoff.json",
        "verification/android-copied-sdk-appearance-contract-correction-review/seal.json",
        "verification/android-copied-sdk-appearance-contract-correction-review/filesystem-probe.json",
        "verification/android-copied-sdk-appearance-contract-root-review/correction-review-admission.json",
    ]
    contracts = {}
    for relative in contract_paths:
        data = (ROOT / relative).read_bytes()
        contracts[relative] = identity(data)
        save("selected-inputs/" + relative, data)
    assert contracts[selection["independent_review"]]["sha256"] == selection["independent_review_sha256"]
    observation = json.loads((ROOT / selection["profile_source_observation"]).read_bytes())
    assert contracts[selection["profile_source_observation"]]["sha256"] == selection["profile_source_observation_sha256"]
    command("python-version", ["python3", "--version"])
    command("git-version", ["git", "--version"])
    tree = command("accepted-tree", ["git", "rev-parse", REVISION + "^{tree}"]).decode().strip()
    head = command("current-head", ["git", "rev-parse", "HEAD"]).decode().strip()
    source_paths: dict[str, dict | None] = {}
    for relative, expected in observation["sdk_files"].items():
        source_paths["sdk/" + relative] = expected
    for relative, expected in observation["adapter_files"].items():
        source = "native/android/" + ("engine/" if relative.startswith("Sources/") else "") + relative
        source_paths[source] = expected
    supplemental = [
        "cli/Package.swift", "cli/Sources/MixerCLI/main.swift",
        "cli/Sources/MixerBuild/Configuration.swift", "cli/Sources/MixerBuild/ProjectGenerator.swift",
        "cli/Sources/MixerBuild/AndroidProject.swift", "cli/Sources/MixerBuild/Resources/android-build.py",
        "cli/Tests/MixerBuildTests/AndroidProjectTests.swift", "cli/Tests/MixerBuildTests/ProjectGeneratorTests.swift",
        "cli/build-tests/test_android_appearance.py", "cli/build-tests/test_android_staging.py",
        "native/android/engine/Tests/MixerAndroidRuntimeTests/RuntimeTests.swift",
        "native/android/engine/Tests/MixerAndroidRuntimeTests/TransactionTests.swift",
        "sdk/Tests/MixerUITests/AppearanceDescriptorV2Tests.swift", "contracts/ui-v1.json",
    ]
    for relative in supplemental:
        source_paths.setdefault(relative, None)
    accepted = {}
    for index, (relative, expected) in enumerate(sorted(source_paths.items())):
        data = command(f"accepted-source-{index:02}", ["git", "show", REVISION + ":" + relative])
        actual = identity(data)
        if expected is not None:
            assert actual == expected, relative
        save("accepted-source/" + relative, data)
        accepted[relative] = actual
    def projection(mapping: dict[str, dict]) -> str:
        encoded = "".join(f"{path}\0{entry['sha256']}\n" for path, entry in sorted(mapping.items())).encode()
        return hashlib.sha256(encoded).hexdigest()
    assert projection(observation["sdk_files"]) == selection["sdk_projection_sha256"]
    assert projection(observation["adapter_files"]) == selection["adapter_projection_sha256"]
    save("input-manifest.json", json.dumps({"schema": 1, "selected_contracts": contracts,
        "accepted_source_revision": REVISION, "accepted_source_tree": tree, "observed_current_head": head,
        "accepted_source_files": accepted, "sdk_projection_sha256": projection(observation["sdk_files"]),
        "adapter_projection_sha256": projection(observation["adapter_files"]),
        "candidate_accessed": False, "native_processes_started": False}, indent=2).encode() + b"\n")
    save("commands.json", json.dumps(COMMANDS, indent=2).encode() + b"\n")
    save("prepared.json", json.dumps({"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
        "status": "accepted-git-baseline-copied-before-candidate-access",
        "candidate_accessed": False, "source_files": len(accepted),
        "source_bytes": sum(item["bytes"] for item in accepted.values()),
        "scope": "contract and accepted Git data only; no compilation, product import, native runtime, process discovery or UI/capture",
        "scratch_created": False, "cleanup": "No temporary scratch or child process remains; bounded Git/Python metadata commands completed."}, indent=2).encode() + b"\n")
    print(json.dumps({"accepted_source_files": len(accepted), "source_revision": REVISION,
        "accepted_tree": tree, "candidate_accessed": False}, indent=2))


if __name__ == "__main__":
    main()
