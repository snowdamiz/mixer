#!/usr/bin/env python3
"""Original bounded SDK checks; reuse host scratch, emit mobile modules only."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OFFICIAL = Path("/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc")
ANDROID = Path("/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android")
PINS = {
    "contracts/guest-ui-event-v1.json": "34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024",
    "vm/include/mixer_vm_guest_ui.h": "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5",
    "docs/guest-ui-event-integration-design.md": "7b7b3a8a70757349330b1f7d898be4db297b888b9cf606464e210494905a44f4",
}
NEW_SDK_FILES = {
    "sdk/Sources/MixerGuest/GuestUIProtocolV1.swift",
    "sdk/Sources/MixerGuest/GuestUIEventCodecV1.swift",
    "sdk/Sources/MixerGuest/GuestUIExchangeV1.swift",
    "sdk/Sources/MixerGuest/GuestUIWakeV1.swift",
    "sdk/Tests/MixerUITests/GuestUIEventCodecTests.swift",
    "sdk/Tests/MixerUITests/GuestUIExchangeTests.swift",
    "sdk/Tests/MixerUITests/GuestUIWakeTests.swift",
}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def require(value, message):
    if not value:
        raise RuntimeError(message)

def manifest():
    paths = sorted(set((ROOT / "sdk/Sources").rglob("*.swift")) |
                   set((ROOT / "sdk/Tests").rglob("*.swift")) |
                   {ROOT / "sdk/Package.swift"} |
                   {ROOT / relative for relative in PINS})
    return {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in paths}

def main():
    name = sys.argv[1] if len(sys.argv) == 2 else "2026-10-23-candidate-1"
    out = HERE / name
    out.mkdir(exist_ok=False)
    sources = manifest()
    require(all(sources[path] == digest for path, digest in PINS.items()), "frozen inputs")
    for relative in sources:
        if relative.startswith("sdk/") and relative not in NEW_SDK_FILES:
            previous = subprocess.run(["git", "show", "HEAD:" + relative], cwd=ROOT,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
            require(sha(previous) == sources[relative], "existing SDK input changed: " + relative)
    receipt = {
        "status": "running", "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "head_at_start": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_files": sources,
        "source_manifest_sha256": sha(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()),
        "driver_sha256": sha(Path(__file__).read_bytes()), "commands": [],
        "scope": "Full SDK host Debug/Release tests; scoped GuestUI ThreadSanitizer tests; official iOS arm64 and Android API28 arm64 module compilation. No app link, simulator/device execution, native first-frame receipt, signing, publication, or GA claim.",
        "approved_clarifications": [
            "Root approved finishReadyWithoutInvocation(GuestUITurnClaimV1): exact issuer/generation/current ready claim only, no invocation, harvest, frame/event success or turn counter increment. Stale/closed/foreign attempts remain local rejection. Frozen wire/header/design unchanged."
        ],
        "existing_sdk_inputs_unchanged_from_head": True,
    }
    def save():
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    def run(name, argv, env=None, timeout=360):
        start = time.monotonic()
        result = subprocess.run([str(arg) for arg in argv], cwd=ROOT, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        log = out / (name + ".log")
        log.write_bytes(result.stdout)
        row = {"name": name, "argv": [str(arg) for arg in argv], "cwd": str(ROOT),
               "exit_code": result.returncode, "elapsed_seconds": time.monotonic() - start,
               "log": str(log.relative_to(ROOT)), "log_sha256": sha(result.stdout)}
        if env:
            row["environment_overrides"] = {key: env[key] for key in ["DEVELOPER_DIR"] if key in env}
        receipt["commands"].append(row)
        save()
        print(name + ": " + str(result.returncode), flush=True)
        require(manifest() == sources, "SDK source changed during " + name)
        if result.returncode != 0:
            receipt["status"] = "failed: " + name + "; preserved log"
            save()
            raise RuntimeError(receipt["status"])
        return result.stdout.decode(errors="replace").strip()
    save()
    apple = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
    android = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode_26.6.app/Contents/Developer")
    run("host-swift-version", ["swift", "--version"], apple)
    run("host-clang-version", ["clang", "--version"], apple)
    run("official-swift-version", [OFFICIAL, "--version"], android)
    ios_sdk = run("iphoneos-sdk", ["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], apple)
    run("sdk-debug", ["swift", "test", "--package-path", "sdk", "-Xswiftc", "-warnings-as-errors"], apple)
    run("sdk-release", ["swift", "test", "--package-path", "sdk", "-c", "release", "-Xswiftc", "-warnings-as-errors"], apple)
    run("sdk-guest-ui-tsan", ["swift", "test", "--package-path", "sdk", "--sanitize", "thread", "--filter", "guestUI", "-Xswiftc", "-warnings-as-errors"], apple)
    metadata = [ANDROID / "swift-sdk.json", ANDROID / "swift-toolset.json"]
    receipt["android_sdk_metadata"] = {str(path): sha(path.read_bytes()) for path in metadata}
    artifacts = {}
    for platform, compiler, flags, env in [
        ("ios", "swiftc", ["-target", "arm64-apple-ios17.0", "-sdk", ios_sdk], apple),
        ("android", OFFICIAL, ["-target", "aarch64-unknown-linux-android28", "-sdk", str(ANDROID / "ndk-sysroot"),
                              "-resource-dir", str(ANDROID / "swift-resources/usr/lib/swift-aarch64")], android),
    ]:
        folder = out / ".build" / platform
        folder.mkdir(parents=True)
        artifacts[platform] = []
        for module in ["MixerCore", "MixerUI", "MixerGuest"]:
            output = folder / (module + ".swiftmodule")
            inputs = sorted((ROOT / "sdk/Sources" / module).glob("*.swift"))
            run(platform + "-" + module, [compiler, "-swift-version", "6", "-warnings-as-errors", "-parse-as-library",
                "-emit-module", "-module-name", module, "-emit-module-path", output, "-module-cache-path", folder / "cache",
                "-I", folder] + flags + inputs, env)
            require(output.is_file(), "actual module output " + module)
            artifacts[platform].append({"path": str(output), "sha256": sha(output.read_bytes()), "bytes": output.stat().st_size})
    require(manifest() == sources, "final unchanged SDK sources")
    receipt.update(artifacts=artifacts, source_unchanged_through_checks=True,
                   completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   status="SDK Debug Release scoped TSan and official mobile module compilation passed")
    save()
    print(json.dumps({"receipt": str((out / "receipt.json").relative_to(ROOT)),
                      "sha256": sha((out / "receipt.json").read_bytes()), "status": receipt["status"]}), flush=True)

if __name__ == "__main__":
    main()
