#!/usr/bin/env python3
"""Capture exact proposal/source inspection evidence; execute no product tests."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
COMMANDS = []
SOURCES = [
    "AGENTS.md", "mixer-product-plan.md",
    "docs/android-signed-ui-binding-contract.md",
    "docs/android-signed-ui-binding-design.md",
    "docs/android-guest-ui-transport-design.md",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityAttemptReservation.swift",
    "capability-activation/Tests/MixerCapabilityActivationTests/CapabilityAttemptReservationTests.swift",
    "updates/Sources/MixerUpdates/CanonicalValue.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartControl.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartWorker.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartRuntime.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIRuntime.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIPresentation.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityConcreteRetirement.swift",
    "sdk/Sources/MixerGuest/GuestUIWakeV1.swift",
    "sdk/Sources/MixerGuest/GuestUIExchangeV1.swift",
    "native/android/signed-guest-ui/transport/include/mixer_ui_transport.h",
    "native/android/signed-guest-ui/transport/transport.c",
    "native/android/signed-guest-ui/transport/platform_android.c",
    "verification/android-binding-design-review/review.md",
    "verification/android-binding-design-review/receipt.json",
    "verification/android-binding-design-review/source-before.sha256",
    "verification/android-binding-design-review/source-after.sha256",
    "verification/android-binding-design-review/ContinuationLifetimeProbe.swift",
    "verification/android-binding-design-review/verify.py",
    "verification/android-binding-contract/reservation-review.md",
    "verification/android-binding-contract/collect.py",
]

def manifest(name):
    content = "".join(sha(ROOT / path) + "  " + path + "\n" for path in SOURCES)
    target = HERE / name
    target.write_text(content)
    return content

def run(name, argv):
    result = subprocess.run(argv, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=30)
    target = HERE / (name + ".log")
    target.write_text(result.stdout)
    COMMANDS.append({"argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
                     "output": str(target.relative_to(ROOT)), "output_sha256": sha(target)})
    if result.returncode:
        raise RuntimeError(name + " failed")
    return result.stdout.strip()

before = manifest("source-before.sha256")
revision_before = run("source-revision-before", ["git", "rev-parse", "HEAD"])
run("source-status-before", ["git", "status", "--short"])
run("git-version", ["git", "--version"])
run("python-version", [os.sys.executable, "--version"])
run("swift-version", [shutil.which("swiftc"), "--version"])

# Validate frozen review artifacts, not its historic source paths against the
# now intentionally advanced reservation prerequisite.
frozen = ROOT / "verification/android-binding-design-review"
old = json.loads((frozen / "receipt.json").read_text())
frozen_checks = []
for command in old["commands"]:
    frozen_checks.append({"path": command["output"],
                          "matches": sha(ROOT / command["output"]) == command["output_sha256"]})
historic_changes = []
for line in (frozen / "source-before.sha256").read_text().splitlines():
    expected, path = line.split("  ", 1)
    actual = sha(ROOT / path)
    if path.startswith("verification/android-binding-design-review/"):
        frozen_checks.append({"path": path, "matches": actual == expected})
    elif actual != expected:
        historic_changes.append({"path": path, "historic_sha256": expected,
                                 "current_sha256": actual})
frozen_checks.append({"path": "verification/android-binding-design-review/source-before.sha256",
                      "matches": sha(frozen / "source-before.sha256") == old["selected_source_manifest_sha256"]})
(HERE / "frozen-review-artifact-checks.json").write_text(json.dumps(frozen_checks, indent=2) + "\n")
(HERE / "historic-review-source-advancement.json").write_text(json.dumps(historic_changes, indent=2) + "\n")
assert all(check["matches"] for check in frozen_checks)

after = manifest("source-after.sha256")
revision_after = run("source-revision-after", ["git", "rev-parse", "HEAD"])
run("source-status-after", ["git", "status", "--short"])
receipt = {
    "status": "corrected_contract_proposal_awaiting_final_root_review",
    "collected_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision_before": revision_before,
    "source_revision_after": revision_after,
    "selected_source_manifest": str((HERE / "source-before.sha256").relative_to(ROOT)),
    "selected_source_manifest_sha256": sha(HERE / "source-before.sha256"),
    "selected_source_count": len(SOURCES),
    "selected_sources_unchanged": before == after,
    "contract_sha256": sha(ROOT / "docs/android-signed-ui-binding-contract.md"),
    "commands": COMMANDS,
    "frozen_review_artifacts_match": all(check["matches"] for check in frozen_checks),
    "frozen_review_artifact_check_count": len(frozen_checks),
    "historic_review_source_advancements": historic_changes,
    "reservation_review": {
        "result": "no_new_defect_found_in_bounded_source_test_review",
        "scope": "Trusted single retirement-owner contract; no product test execution by this lane.",
        "note": "Root independently owns reservation prerequisite source/tests and its active runner. This receipt does not claim that runner's outcome.",
    },
    "official_sources_previously_read_in_this_review_session": [
        "https://developer.android.com/ndk/reference/group/looper",
        "https://developer.android.com/reference/android/os/Looper",
        "https://developer.android.com/ndk/guides/jni-tips",
    ],
    "scope": "Corrected staged contract authoring, selected source binding, preservation of frozen review artifacts and bounded independent root reservation source/test inspection only.",
    "limitations": [
        "No new product implementation, executable binding test, C transport test rerun, full activation linkage, JNI, Java widget or Android Looper execution.",
        "Frozen host Swift continuation/Task semantics evidence remains historic and unchanged; Android toolchain/runtime qualification remains pending.",
        "No phone discovery/query/run/reconnection, emulator, dependency/download, commit/push, publication, customer message, release or GA authorization.",
        "Final C/Swift/JNI APIs and implementation assignments await root contract acceptance. Only stage-1 reservation prerequisite was already assigned to root.",
    ],
}
(HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
assert before == after, "selected source changed during capture"
print(json.dumps({"status": receipt["status"], "selected_sources": len(SOURCES),
                  "sources_unchanged": before == after,
                  "frozen_review_artifact_checks": len(frozen_checks),
                  "historic_source_advancements": [c["path"] for c in historic_changes]}, indent=2))
