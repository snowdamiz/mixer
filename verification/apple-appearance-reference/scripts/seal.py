#!/usr/bin/env python3
"""Run scoped verification, then bind all retained reference evidence bytes."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
argv = ["python3", str(ROOT / "scripts/verify.py")]
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
with (ROOT / "logs/integrity-verification.log").open("w") as stream:
    result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, cwd=ROOT)
assert result.returncode == 0
lock = json.loads((ROOT / "input-lock.json").read_text())
captures = json.loads((ROOT / "capture-manifest.json").read_text())
entries = []
for path in sorted(ROOT.rglob("*")):
    relative = path.relative_to(ROOT)
    if not path.is_file() or relative.parts[0] == "build" or relative.name == "receipt.json" or "xcuserdata" in relative.parts:
        continue
    entries.append(dict(path=str(relative), bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
evidence_digest = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
receipt = dict(
    format="mixer.apple-appearance-reference.1",
    status="simulator-reference-captured-and-integrity-checked; accountable-design-and-physical-review-pending",
    capturedUTC=json.loads((ROOT / "commands.json").read_text())[-1]["finishedUTC"],
    sealedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceRevision=lock["sourceRevision"], sourceTree=lock["sourceTree"],
    sourceCollectionSHA256=lock["sourceCollectionSHA256"],
    unchangedRenderer="frozen/sdk/Sources/MixerApple/MixerNativeView.swift",
    unchangedSDKPackage="frozen/sdk/Package.swift",
    documentEquality="Each light/dark pair has byte-identical shared UIDocument JSON; host snapshot equality checked by frozen SDK in native app.",
    simulator=json.loads((ROOT / "simulator.json").read_text()),
    environmentSummary=dict(screenPoints=dict(width=402,height=874), nativePixels=dict(width=1206,height=2622), scale=3,
        standardSize="large", rtlSize="accessibility-medium / SwiftUI accessibility1", orientation="portrait"),
    tools=dict(xcode=(ROOT / "logs/xcode-version.log").read_text().strip(),
        swift=(ROOT / "logs/swift-version.log").read_text().strip(),
        simulatorSDK=(ROOT / "logs/sdk-version.log").read_text().strip()),
    coverage=dict(nativeScreenshots=8, fixtures=4, currentKinds=10,
        referenceOnly=True, themeApplied=False, numericNodeMetricsMeasured=False,
        agentVisualQA="All eight original screenshots inspected; see observations.md; no accountable reviewer acceptance."),
    verification=dict(argv=argv, cwd=str(ROOT), startedUTC=started, exitCode=result.returncode,
        output="logs/integrity-verification.log", scope="source/fixture/native environment/capture integrity; no release authorization"),
    pending=["accountable root/human review of candidate tokens against baseline", "shared renderer implementation/qualification",
        "physical iOS and Android side-by-side parity", "native interaction/input/keyboard/accessibility verification",
        "per-node measured geometry and quantitative color/type comparison", "pressed/focused states and all text size/RTL profiles",
        "signed activation/display/health", "immutable published FieldLog consumption", "signing/store/customer/operational/GA evidence"],
    physicalDevices=dict(discovered=False, used=False, reconnectionRequested=False),
    dependencies="Only frozen owned SDK and official Apple toolchain/platform SDK. No third-party engine/assets/dependencies.",
    ownership="Only verification/apple-appearance-reference/**; no production changes, gate/status updates, commits or pushes.",
    captureManifest="capture-manifest.json", builtAppManifest="built-app-manifest.json",
    artifactCollectionRule="SHA-256 of UTF-8 compact sorted-key JSON artifacts array; excludes receipt itself and ignored local build derived data",
    artifactCollectionSHA256=evidence_digest, artifacts=entries)
(ROOT / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(dict(receiptSHA256=hashlib.sha256((ROOT / "receipt.json").read_bytes()).hexdigest(),
    artifactCollectionSHA256=evidence_digest, artifacts=len(entries), sourceCollectionSHA256=lock["sourceCollectionSHA256"]), indent=2))
