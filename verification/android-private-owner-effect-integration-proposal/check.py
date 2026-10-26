#!/usr/bin/env python3
"""Supplemental proposal/custody checks only; not product behavior or release proof."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    receipt = json.loads((PACKET / "receipt.json").read_text())
    checks = []

    def check(name, value):
        checks.append({"name": name, "passed": bool(value)})

    for name, expected in receipt["inputs"].items():
        check("frozen input: " + name, identity((PACKET / "inputs" / name).read_bytes()) == expected)
    for name in [
        "native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java",
        "native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java",
        "native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java",
        "native/android/app/src/dev/mixer/android/NativeRenderer.java",
        "native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java",
    ]:
        check("current exact seam: " + name, identity((ROOT / name).read_bytes()) == receipt["inputs"][name])
    core = "native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java"
    check("accepted core exact bytes", receipt["inputs"][core] == {
        "bytes": 12473, "sha256": "4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6"})
    observer = "native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java"
    check("frozen observer candidate exact bytes", receipt["inputs"][observer] == {
        "bytes": 14318, "sha256": "814b00b91b458c1287cb9c924c099fc2e647e42501b09e09acd711fbe5b54dac"})
    contract = "docs/android-owner-effect-contract.md"
    check("root-provided broad contract digest", receipt["inputs"][contract]["sha256"] ==
          "30031a9827d7c1b494c73586b71dc7052ccca8f542febf1bb7fbbe95829e3e35")
    proposal = (ROOT / receipt["proposal"]["path"]).read_bytes()
    check("frozen proposal", identity(proposal) == {k: receipt["proposal"][k] for k in ["bytes", "sha256"]})
    text = proposal.decode()
    for term in ["void register()", "void bindRenderer", "interface Sink", "Fence", "probeWindow()",
                 "fence.operation", "sealScalarV2", "closeFromOwner", "core-completion-unreported",
                 "WindowIdentity", "REFRESH_COMMITTED", "committedPacket = packet", "one subsequent drain",
                 "same bound observer's `invalidate()`", "source-pair.3", "exact accepted bytes",
                 "not run", "Source inspection guards supplement behavior", "first fatal"]:
        check("proposal coverage only: " + term, term in text)
    check("proposal whitespace", all(line.rstrip() == line for line in text.splitlines()) and text.endswith("\n"))
    profile_text = (PACKET / "inputs/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift").read_text()
    profile = json.loads(profile_text.split('Data(#"""', 1)[1].split('"""#.utf8)', 1)[0])
    check("input profile2, no successor selected", profile["id"] == "mixer.android-source-pair.2")
    check("input profile closure counts", len(profile["sdk_files"]) == 22 and len(profile["adapter_files"]) == 20)
    check("input profile binds observer", profile["adapter_files"]["app/src/dev/mixer/android/NativeEnvironmentV2.java"] == receipt["inputs"][observer])
    projected = "".join(name + "\0" + receipt["inputs"][name]["sha256"] + "\n" for name in sorted(receipt["inputs"])).encode()
    check("selected input projection digest", hashlib.sha256(projected).hexdigest() == receipt["selected_input_projection_sha256"])
    result = {"schema": 1, "scope": "supplemental-source-custody-and-proposal-coverage-only",
              "command": [sys.executable, "-B", str(Path(__file__).resolve())],
              "python_version": sys.version, "checks": checks,
              "passed": sum(item["passed"] for item in checks),
              "failed": sum(not item["passed"] for item in checks),
              "product_tests_run": False, "implementation_or_native_acceptance": False}
    (PACKET / "source-only-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in ["scope", "passed", "failed", "product_tests_run"]}, sort_keys=True))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
