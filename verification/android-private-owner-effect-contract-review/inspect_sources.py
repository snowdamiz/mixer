#!/usr/bin/env python3
"""Source-only inventory and excerpts; neither product tests nor release authority."""
from pathlib import Path
import hashlib
import json
import sys

BASE = Path(__file__).resolve().parent
INPUT = BASE / "current-inputs"
PROPOSAL = BASE / "frozen-proposal/docs/android-private-owner-effect-integration-proposal.md"

def excerpt(path, spans):
    lines = path.read_text().splitlines()
    return [{"first": a, "last": min(b, len(lines)), "lines": [
        {"line": i, "text": lines[i - 1]} for i in range(a, min(b, len(lines)) + 1)]} for a, b in spans]

def main():
    custody = json.loads((BASE / "custody.json").read_text())
    for name, expected in custody["captured"].items():
        data = (BASE / name).read_bytes()
        assert len(data) == expected["bytes"] and hashlib.sha256(data).hexdigest() == expected["sha256"]
    literal = (INPUT / "cli/Sources/MixerBuild/AndroidSDKCompatibility.swift").read_text()
    start = literal.index('#"""') + len('#"""')
    end = literal.index('"""#', start)
    profile = json.loads(literal[start:end])
    assert len(profile["sdk_files"]) == 22 and len(profile["adapter_files"]) == 20
    java_prefix = "native/android/app/src/dev/mixer/android/"
    spans = {
        "native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java": [(68,85),(153,197),(213,267)],
        java_prefix + "NativeCoordinatorV2.java": [(8,41),(93,106),(146,205),(213,263)],
        java_prefix + "NativeEnvironmentV2.java": [(50,119),(141,195),(237,242)],
        java_prefix + "NativeRenderer.java": [(65,105),(211,243),(281,364)],
        java_prefix + "NativeAppearanceViewsV2.java": [(88,116),(143,189),(203,222),(431,475),(522,594),(603,710)],
        java_prefix + "MixerActivity.java": [(1,16)],
        "native/android/tests/NativeCoordinatorV2HostLeaves/dev/mixer/android/NativeRenderer.java": [(1,120)],
        "native/android/tests/NativeCoordinatorV2IntegrationActivity.java": [(1,40)],
        "native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java": [(54,116)],
        "native/android/tests/NativeAppearanceV2Instrumentation.java": [(69,76),(139,151),(226,230),(260,270)],
        "cli/Sources/MixerBuild/AndroidProject.swift": [(31,58)]
    }
    result = {"schema": 1, "command": [str(Path(sys.executable).resolve()), "-B", str(Path(__file__).resolve())],
        "scope": "Independent source-only inventory and line excerpts; no producer checker or product code executed.",
        "profile": {"id": profile["id"], "sdk_members": len(profile["sdk_files"]),
            "adapter_members": len(profile["adapter_files"]),
            "sdk_compatibility_sha256": profile["sdk_compatibility_sha256"],
            "adapter_compatibility_sha256": profile["adapter_compatibility_sha256"],
            "default_descriptor": profile["default_descriptor"],
            "owner_core_in_map": "app/src/dev/mixer/android/OwnerLifecycleV2.java" in profile["adapter_files"],
            "owner_adapter_in_map": "app/src/dev/mixer/android/NativeOwnerV2.java" in profile["adapter_files"]},
        "proposal_excerpts": excerpt(PROPOSAL, [(50,130),(185,225),(295,334),(345,389)]),
        "current_source_excerpts": {p: excerpt(INPUT / p, s) for p, s in spans.items()},
        "product_tests_run": False, "semantic_or_runtime_behavior_proven": False,
        "OTA_authorization": False, "implementation_acceptance": False}
    (BASE / "source-inventory.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "source-inventory-pass", "profile": result["profile"],
                      "source_excerpt_files": len(spans), "product_tests_run": False}))

if __name__ == "__main__":
    main()
