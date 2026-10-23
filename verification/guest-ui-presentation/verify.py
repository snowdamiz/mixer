#!/usr/bin/env python3
"""Freeze this lane and its SDK inputs; execute host tests and mobile modules."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAPSHOT = ROOT / ".build/guest-ui-presentation"
OWNED = ["capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIPresentation.swift",
         "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIApple.swift",
         "capability-activation/Tests/MixerCapabilityActivationTests/GuestUIPresentationModelTests.swift",
         "capability-activation/Tests/MixerCapabilityActivationTests/GuestUIPresentationWindowTests.swift"]
PACKAGE = '''// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "MixerGuestUIPresentationReview", platforms: [.macOS(.v14), .iOS(.v17)], dependencies: [.package(path: "sdk")], targets: [.target(name: "MixerCapabilityActivation", dependencies: [.product(name: "MixerGuest", package: "sdk"), .product(name: "MixerUI", package: "sdk"), .product(name: "MixerApple", package: "sdk", condition: .when(platforms: [.iOS, .macOS]))]), .testTarget(name: "MixerCapabilityActivationTests", dependencies: ["MixerCapabilityActivation"])], swiftLanguageModes: [.v6])
'''
OFFICIAL = Path("/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc")
ANDROID = Path("/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_manifest():
    paths = [ROOT / p for p in OWNED]
    paths += [ROOT / "sdk/Package.swift", Path(__file__), HERE / "GuestUIPresentationWindowHarness.swift",
              ROOT / "contracts/guest-ui-event-v1.json", ROOT / "docs/guest-ui-event-integration-design.md"]
    paths += sorted(p for p in (ROOT / "sdk/Sources").rglob("*") if p.is_file())
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(paths)}


def main():
    name = sys.argv[1] if len(sys.argv) == 2 else "2026-10-23-candidate-1"
    out = HERE / name
    out.mkdir(exist_ok=False)
    sources = source_manifest()
    sdk_receipt_path = ROOT / "verification/guest-ui-sdk/2026-10-23-candidate-4/receipt.json"
    sdk_receipt = json.loads(sdk_receipt_path.read_text())
    for path, digest in sources.items():
        if path.startswith("sdk/"):
            expected = sdk_receipt["source_files"].get(path)
            if expected is None:
                expected = sha(subprocess.check_output(["git", "show", "HEAD:" + path], cwd=ROOT))
            assert expected == digest, "unreviewed SDK input " + path
    for relative in OWNED:
        p = Path(relative)
        section = "Sources" if "Sources" in p.parts else "Tests"
        target = "MixerCapabilityActivation" if section == "Sources" else "MixerCapabilityActivationTests"
        destination = SNAPSHOT / section / target / p.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    expected_names = {Path(p).name for p in OWNED[:2]}
    assert {p.name for p in (SNAPSHOT / "Sources/MixerCapabilityActivation").glob("*.swift")} == expected_names
    for relative in sources:
        if relative.startswith("sdk/"):
            destination = SNAPSHOT / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
    (SNAPSHOT / "Package.swift").write_text(PACKAGE)
    receipt = {
        "status": "running", "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_files": sources,
        "source_tree_sha256": sha(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()),
        "snapshot_package_sha256": sha(PACKAGE.encode()), "snapshot": str(SNAPSHOT),
        "sdk_receipt": str(sdk_receipt_path.relative_to(ROOT)), "sdk_receipt_sha256": sha(sdk_receipt_path.read_bytes()),
        "commands": [],
        "scope": "Frozen model/Apple wrapper only, excluding mutable signed coordinator and native runtime. Debug/Release have thirteen executed tests and one explicitly skipped visible-native-window qualification. TSan executes twelve model tests. iOS module compilation includes the native wrapper; Android compiles its unsupported-platform binding only. No physical devices, simulator execution, positive native display receipt, signed end-to-end screen, immutable consumer package, compositor or GA claim.",
        "pending": ["Positive visible native Mac window: retained attempts remained occluded and correctly earned no receipt.",
                    "iOS native foreground-scene appearance/layout/CA/display-link execution and screenshots/accessibility.",
                    "Physical iOS/Android, signed facade integration, published package consumer and GA gates."],
    }

    def save():
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def run(name, argv, env=None, timeout=360):
        start = time.monotonic()
        result = subprocess.run([str(x) for x in argv], cwd=ROOT, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        log = out / (name + ".log")
        log.write_bytes(result.stdout)
        receipt["commands"].append({"name": name, "argv": [str(x) for x in argv], "cwd": str(ROOT),
                                    "exit_code": result.returncode, "elapsed_seconds": time.monotonic() - start,
                                    "log": str(log.relative_to(ROOT)), "log_sha256": sha(result.stdout),
                                    "developer_dir": env.get("DEVELOPER_DIR") if env else None,
                                    "visible_window_opt_in": env.get("MIXER_GUEST_UI_VISIBLE_WINDOW") if env else None})
        save()
        print(name + ": " + str(result.returncode), flush=True)
        assert source_manifest() == sources, "source changed during " + name
        assert result.returncode == 0, name + " failed; retained output"
        return result.stdout.decode(errors="replace").strip()

    save()
    apple = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
    apple.pop("MIXER_GUEST_UI_VISIBLE_WINDOW", None)
    android = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode_26.6.app/Contents/Developer")
    run("apple-swift-version", ["xcrun", "swiftc", "--version"], apple)
    run("xcode-version", ["xcodebuild", "-version"], apple)
    run("official-swift-version", [OFFICIAL, "--version"], android)
    ios_sdk = run("iphoneos-sdk", ["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], apple)
    base = ["swift", "test", "--package-path", SNAPSHOT, "--scratch-path", SNAPSHOT / "build", "--jobs", "4"]
    run("debug", base + ["-Xswiftc", "-warnings-as-errors"], apple)
    run("release", base + ["-c", "release", "-Xswiftc", "-warnings-as-errors"], apple)
    run("tsan-model", base + ["--sanitize", "thread", "--filter", "GuestUIPresentationModelTests", "-Xswiftc", "-warnings-as-errors"], apple)
    artifacts = {}
    for platform, compiler, flags, env in [
        ("ios", "swiftc", ["-target", "arm64-apple-ios17.0", "-sdk", ios_sdk], apple),
        ("android", OFFICIAL, ["-target", "aarch64-unknown-linux-android28", "-sdk", ANDROID / "ndk-sysroot",
                               "-resource-dir", ANDROID / "swift-resources/usr/lib/swift-aarch64"], android),
    ]:
        folder = SNAPSHOT / "modules" / platform
        folder.mkdir(parents=True, exist_ok=True)
        artifacts[platform] = []
        modules = ["MixerCore", "MixerUI", "MixerGuest"] + (["MixerApple"] if platform == "ios" else []) + ["MixerCapabilityActivation"]
        for module in modules:
            directory = SNAPSHOT / ("Sources" if module == "MixerCapabilityActivation" else "sdk/Sources") / module
            inputs = sorted(directory.glob("*.swift"))
            output = folder / (module + ".swiftmodule")
            run(platform + "-" + module, [compiler, "-swift-version", "6", "-warnings-as-errors", "-parse-as-library", "-emit-module",
                "-module-name", module, "-emit-module-path", output, "-module-cache-path", folder / "cache", "-I", folder] + flags + inputs, env)
            artifacts[platform].append({"path": str(output), "sha256": sha(output.read_bytes()), "bytes": output.stat().st_size})
    receipt.update(status="Scoped host tests and official mobile module compilation passed; native display qualification remains pending",
                   source_unchanged=True, artifacts=artifacts,
                   android_metadata={str(ANDROID / name): sha((ANDROID / name).read_bytes()) for name in ["swift-sdk.json", "swift-toolset.json"]},
                   completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    save()
    print(json.dumps({"receipt": str((out / "receipt.json").relative_to(ROOT)), "sha256": sha((out / "receipt.json").read_bytes())}), flush=True)


if __name__ == "__main__":
    main()
