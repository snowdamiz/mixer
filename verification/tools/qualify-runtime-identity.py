#!/usr/bin/env python3
"""Frozen runtime-identity/activation checks. No physical-device commands."""
import argparse
import concurrent.futures
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("qualification", ROOT / "compiler/qualification_support.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if not args.name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.name):
        parser.error("name must be lowercase ASCII letters, digits or hyphens")
    revision = subprocess.check_output(["git", "rev-parse", args.revision + "^{commit}"], cwd=ROOT, text=True).strip()
    output = ROOT / "verification" / ("runtime-identity-" + args.name)
    work = ROOT / "verification/local" / ("runtime-identity-" + args.name)
    output.mkdir(parents=True, exist_ok=False)
    work.mkdir(parents=True, exist_ok=False)
    commands = []
    recorder = helper.CommandRecorder(output, commands, ROOT)
    env = helper.clean_environment()
    apple = "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
    cross = "/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
    cross_env = env | {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"}
    receipt = dict(schema=1, sourceRevision=revision, startedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(), commands=commands, status="running",
        runnerSHA256=helper.digest(Path(__file__)), helperSHA256=helper.digest(ROOT / "compiler/qualification_support.py"),
        limitations=["Build descriptor validates declared inputs; no complete graph attestation, signed binary embedding or published immutable native distribution",
                     "Original small Wasm fixtures, not full Swift/FieldLog/capability guest execution",
                     "iOS simulator execution and Android/iOS compilation do not qualify physical device lifecycle or performance; phones disconnected"])

    def run(name, command, *, environment=env, timeout=600):
        result = recorder.run(name, command, env=environment, timeout=timeout)
        print(name + " passed", flush=True)
        return result

    try:
        source = work / "source"; source.mkdir()
        archive = work / "source.tar"
        packages = ["runtime-identity", "activation", "runtime", "updates", "contracts"]
        run("source-export", ["/usr/bin/git", "archive", "--format=tar", "--output=" + str(archive), revision, *packages])
        with tarfile.open(archive) as stream:
            stream.extractall(source, filter="data")
        receipt["sourceArchiveSHA256"] = helper.digest(archive)
        manifest = {str(p.relative_to(source)): helper.digest(p) for p in sorted(source.rglob("*")) if p.is_file()}
        receipt["sourceFiles"] = manifest
        receipt["sourceDigest"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        receipt["toolVersions"] = dict(appleSwift=run("apple-swift-version", [apple, "--version"]),
            crossSwift=run("cross-swift-version", [cross, "--version"], environment=cross_env),
            xcode=run("xcode-version", ["/usr/bin/xcodebuild", "-version"]), macOS=run("host-os", ["/usr/bin/sw_vers"]))
        libraries = {}
        receipts = {}
        for label, folder in [("host", "native-host-reclamation"), ("simulator", "native-ios-simulator"), ("android", "native-android")]:
            base = ROOT / "runtime/.build" / folder
            r = json.loads((base / "receipt.json").read_text())
            library = base / "lib/libmixer_vm.a"
            if helper.digest(library) != r["static_library_sha256"] or helper.digest(source / "runtime/Sources/CMixerVM/include/mixer_vm.h") != r["header_sha256"]:
                raise ValueError("Native archive/header identity mismatch: " + label)
            if r["source_revision"] != "64123c509e861ddd522631b293eadebdaca11341":
                raise ValueError("Unexpected native VM revision")
            libraries[label] = library; receipts[label] = r
        receipt["nativeVM"] = receipts

        def host():
            run("canonical-vectors", [sys.executable, "-B", source / "runtime-identity/tools/vectors.py", "--check"])
            run("identity-host", [apple, "test", "--package-path", source / "runtime-identity"])
            inspected = run("identity-cli", [apple, "run", "--package-path", source / "runtime-identity", "mixer-identity", "inspect", source / "activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json"])
            result = json.loads(inspected)
            vector = json.loads((source / "runtime-identity/Tests/MixerRuntimeIdentityTests/Fixtures/vectors.json").read_text())[0]
            if result["fingerprint"] != vector["fingerprint"] or result["buildAttested"] is not False:
                raise ValueError("CLI descriptor result mismatch")
            receipt["cliResult"] = result
            run("activation-release", [apple, "test", "--package-path", source / "activation", "-c", "release", "-Xlinker", "-L" + str(libraries["host"].parent)])

        def ios_compile():
            run("ios-arm64-compile", [apple, "build", "--package-path", source / "activation", "--target", "MixerActivation", "--triple", "arm64-apple-ios17.0", "--sdk", "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.1.sdk", "--scratch-path", work / "ios-compile", "-Xswiftc", "-warnings-as-errors"])

        def android_compile():
            run("android-tests-compile", [cross, "build", "--package-path", source / "activation", "--swift-sdks-path", "/Users/andreyyurlov/.swiftpm/swift-sdks", "--swift-sdk", "aarch64-unknown-linux-android28", "-c", "release", "--build-tests", "-Xswiftc", "-enable-testing", "--scratch-path", work / "android-compile", "-Xlinker", "-L" + str(libraries["android"].parent)], environment=cross_env)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(job) for job in [host, ios_compile, android_compile]]
            for future in futures:
                future.result()

        simulator = work / "simulator"
        run("prepare-ios-simulator", [sys.executable, "-B", ROOT / "verification/tools/prepare-ios-updater.py", "--package", "activation", "--revision", revision, "--vm-library", libraries["simulator"], "--output", simulator])
        receipt["simulatorPreparation"] = json.loads((simulator / "prepared.json").read_text())
        receipt["preparerSHA256"] = helper.digest(ROOT / "verification/tools/prepare-ios-updater.py")
        result = simulator / "result.xcresult"
        run("ios-simulator-tests", ["/usr/bin/xcodebuild", "-project", simulator / "app/UpdaterHost.xcodeproj", "-scheme", "UpdaterHost", "-configuration", "Debug", "-destination", "platform=iOS Simulator,id=463F0C3C-63BC-42C4-A17C-0908C07D341D", "-derivedDataPath", simulator / "build", "-resultBundlePath", result, "CODE_SIGNING_ALLOWED=NO", "test"])
        summary = json.loads(run("ios-simulator-summary", ["/usr/bin/xcrun", "xcresulttool", "get", "test-results", "summary", "--path", result, "--format", "json"]))
        receipt["simulatorSummary"] = summary
        if (summary.get("result") != "Passed" or summary.get("failedTests") != 0
                or summary.get("skippedTests") != 0 or summary.get("testFailures")
                or summary.get("totalTestCount") != 13 or summary.get("passedTests") != 13
                or sum(item.get("passedTests", 0) for item in summary.get("devicesAndConfigurations", [])) != 14):
            raise ValueError("Simulator failure, skip or unexpected test count (expected13 functions/14 cases)")
        # All exported inputs, including older immutable receipts, remain intact.
        if any(helper.digest(source / name) != digest for name, digest in manifest.items()):
            raise ValueError("Exported source changed during qualification")
        receipt["sourceUnchangedAfterChecks"] = True
        receipt["status"] = "passed scoped host, simulator and cross-compilation"
    except Exception as error:
        receipt["status"] = "failed"
        receipt["error"] = str(error)
        raise
    finally:
        receipt["completedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
