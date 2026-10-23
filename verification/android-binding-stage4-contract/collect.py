#!/usr/bin/env python3
"""Bind a proposed contract to frozen prerequisites; execute no product tests."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
EXPECTED_COMMON = "8d540e60a53c40267e68de822cee181e22f92b69e61fe023d03e05ad6f247f47"
STAGE3 = "d6505acac44ca8de456abb7748a149bf8990b72a"
DOC = "docs/android-binding-stage4-seams.md"
MATRIX = "verification/android-binding-stage4-contract/acceptance-matrix.json"
INPUTS = [
    "AGENTS.md",
    "PLAN.md",
    "docs/android-signed-ui-binding-contract.md",
    "verification/android-binding-contract-acceptance.json",
    "verification/common-presentation-lifetime/final-1/receipt.json",
    "verification/common-presentation-lifetime/portable-1/receipt.json",
    "verification/common-presentation-lifetime-review/review.json",
    "verification/android-facade-transport-root-review/receipt.json",
    "capability-activation/Package.swift",
]
TRANSPORT = [
    "native/android/signed-guest-ui/transport/include/mixer_ui_transport.h",
    "native/android/signed-guest-ui/transport/internal.h",
    "native/android/signed-guest-ui/transport/transport.c",
    "native/android/signed-guest-ui/transport/platform_android.c",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(path: str) -> str:
    return sha((ROOT / path).read_bytes())


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def run(argv: list[str]) -> dict:
    proc = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
    return {"argv": argv, "cwd": str(ROOT), "exit": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr}


def main() -> int:
    commands = [run(["git", "rev-parse", "HEAD"]), run(["git", "--version"]),
                run([sys.executable, "--version"]), run(["xcrun", "swiftc", "--version"]),
                run(["xcrun", "clang", "--version"])]
    acceptance = read_json("verification/android-binding-contract-acceptance.json")
    owner = read_json("verification/common-presentation-lifetime/final-1/receipt.json")
    portable = read_json("verification/common-presentation-lifetime/portable-1/receipt.json")
    review = read_json("verification/common-presentation-lifetime-review/review.json")
    matrix = read_json(MATRIX)
    checked = []
    errors = []
    if digest(acceptance["contract"]) != acceptance["contract_sha256"]:
        errors.append("Accepted binding contract has drifted")
    for name, value in [("owner", owner.get("source_tree_sha256")),
                        ("portable", portable.get("source_tree_sha256")),
                        ("review", review.get("owner_source_tree_sha256"))]:
        if value != EXPECTED_COMMON:
            errors.append(f"{name} common source-tree binding mismatch")
    for path, expected in review["reviewed_activation_source_files"].items():
        actual = digest(path)
        checked.append({"path": path, "expected": expected, "observed": actual,
                        "matches": actual == expected})
        if actual != expected:
            errors.append(f"Frozen common production source changed: {path}")
    for path in TRANSPORT:
        proc = subprocess.run(["git", "show", f"{STAGE3}:{path}"], cwd=ROOT,
                              capture_output=True, check=False)
        actual = digest(path)
        expected = sha(proc.stdout) if proc.returncode == 0 else None
        checked.append({"path": path, "git_revision": STAGE3, "expected": expected,
                        "observed": actual, "matches": actual == expected})
        if actual != expected:
            errors.append(f"Frozen C production source changed: {path}")
    cases = matrix["cases"]
    expected_ids = [f"S4-{i:02d}" for i in range(1, 33)]
    if [case["id"] for case in cases] != expected_ids:
        errors.append("Matrix must contain the 32 ordered unique acceptance IDs")
    if len({case["name"] for case in cases}) != len(cases):
        errors.append("Duplicate acceptance name")
    for case in cases:
        if not case.get("schedule") or not case.get("pass") or not case.get("contract_sections"):
            errors.append(f"Incomplete schedule/oracle/contract mapping: {case['id']}")
    if matrix["status"] != "planned_only_not_executed":
        errors.append("Proposal must not claim implementation execution")
    if matrix.get("proposal_revision") != 2:
        errors.append("Expected standalone host-only v2 proposal")
    if matrix["required_modes"] != ["debug", "release", "tsan"]:
        errors.append("Required host-mode mapping changed")
    doc = (ROOT / DOC).read_text()
    for path in ["CapabilityGuestUIAndroidBinding.swift", "CapabilityGuestUIAndroidRegistry.swift",
                 "CapabilityGuestUIAndroidLifetime.swift", "CapabilityGuestUIAndroidResources.swift",
                 "CapabilityGuestUIAndroidProgress.swift"]:
        if path not in doc:
            errors.append(f"Missing ownership path: {path}")
    if any(command["exit"] for command in commands):
        errors.append("At least one metadata/tool-version command failed")
    inputs = {path: digest(path) for path in INPUTS + [DOC, MATRIX]}
    inputs[str(Path(__file__).relative_to(ROOT))] = digest(str(Path(__file__).relative_to(ROOT)))
    history_paths = [
        "verification/android-binding-stage4-contract/v1/receipt.json",
        "verification/android-binding-stage4-contract/v1/collect.py",
        "verification/android-binding-stage4-contract/v1/acceptance-matrix.json",
        "verification/android-binding-stage4-contract/v1/android-binding-stage4-seams.md",
    ]
    history = {path: digest(path) for path in history_paths}
    v1 = read_json(history_paths[0])
    for original, preserved in [
        (DOC, history_paths[3]),
        (MATRIX, history_paths[2]),
        ("verification/android-binding-stage4-contract/collect.py", history_paths[1]),
    ]:
        if v1["inputs_sha256"][original] != history[preserved]:
            errors.append(f"Preserved v1 artifact mismatch: {preserved}")
    receipt = {
        "schema_version": 1,
        "proposal_revision": 2,
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "executor": "/root/android_binding_stage4_contract",
        "scope": "Contract proposal and exact source binding only; no new product implementation or executable binding tests.",
        "source_revision": commands[0]["stdout"].strip(),
        "frozen_stage3_revision": STAGE3,
        "frozen_stage2_owner_source_tree_sha256": EXPECTED_COMMON,
        "inputs_sha256": inputs,
        "preserved_v1_sha256": history,
        "implementation_boundary": {
            "shared_source_change": "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIPresentationLifetime.swift",
            "assignment": "Root freezes then delegates the one common lifetime file plus five new production files together to one implementation lane",
            "compile_guard": "canImport(CMixerUITransport) && canImport(CMixerUIAndroidHostBridge)",
            "entry": "CapabilityGuestUIAndroidBinding.prepareHost(reservation:)",
            "real_common_authority": "Existing CapabilityGuestUIPresentationLifetime and CapabilityPresentationJoinPermit move/begin/consume cells",
            "host_types": ["CapabilityAndroidHostInstallation", "CapabilityAndroidHostJoinStatus", "CapabilityAndroidHostLifetimeReceipt", "CapabilityAndroidHostFacadeCleanupReceipt", "CapabilityAndroidHostFinalReceipt"],
            "normal_factories_and_gates": "unchanged; no Android/native profile enablement",
            "deferred": "Existing signed core/common Prepared integration, native JNI witness and concrete-attempt fallback ownership",
        },
        "source_bindings": checked,
        "source_binding_count": len(checked),
        "commands": commands,
        "platform": platform.platform(),
        "planned_acceptance_cases": len(cases),
        "executed_binding_acceptance_cases": 0,
        "errors": errors,
        "result": "Proposal inputs and matrix structure match frozen prerequisites" if not errors else "Proposal input audit failed",
        "pending": ["Root coordination/freeze and sole-lane assignment of common lifetime plus newfile ownership", "Stage4 standalone host implementation and all 32 actual Swift/C acceptance cases", "Type-separated host installation/receipt and private-constructor negative compiles; mandatory Apple-backend rejection", "Existing signed core/common Prepared and actual concrete-attempt fallback integration", "JNI/Java native witnesses and actual Android Looper integration", "Physical phones disconnected; no discovery/runs/reconnect requests", "Published FieldLog, signing/store/customer/operational and accountable GA gates"],
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"result": receipt["result"], "source_binding_count": len(checked),
                      "planned_acceptance_cases": len(cases), "executed_binding_acceptance_cases": 0,
                      "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
