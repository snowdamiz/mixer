#!/usr/bin/env python3
"""Compile only the proposed C layouts; no native capability functions exist yet."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/capability-native-abi-proposal.md"
OUT = ROOT / "verification/capability-native-layout-proposal"
ENV = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
NDK = Path.home() / ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="capability-native-layout-", dir=ROOT / "verification/local"))
    commands = []

    def run(name, argv):
        argv = list(map(str, argv))
        p = subprocess.run(argv, cwd=ROOT, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = OUT / (name + ".log")
        log.write_bytes(p.stdout)
        commands.append({"name": name, "command": argv, "exitCode": p.returncode,
                         "output": str(log.relative_to(ROOT)), "outputSHA256": sha(p.stdout)})
        if p.returncode:
            raise RuntimeError(f"{name} failed; see {log}")
        return p.stdout.decode().strip()

    document = DOC.read_text()
    declarations = document.split("```c\n", 1)[1].split("```", 1)[0]
    layouts = {
        "MixerVmCapabilityLimitsV1": (32, {"struct_size": 0, "abi_version": 4, "maximum_requests": 8, "timeout_milliseconds": 12, "turn_milliseconds": 16, "reserved": 20, "reservation_bytes": 24}),
        "MixerVmCapabilityMessageV1": (40, {"struct_size": 0, "abi_version": 4, "kind": 8, "operation": 12, "token": 16, "remaining_milliseconds": 24, "payload_length": 28, "reserved": 32}),
        "MixerVmCapabilityResultV1": (24, {"struct_size": 0, "abi_version": 4, "kind": 8, "remaining_milliseconds": 12, "reserved": 16}),
    }
    source = "#include <stdint.h>\n#include <stddef.h>\n" + declarations
    source += '\n_Static_assert(sizeof(void*) == 8, "LP64 pointer width");\n'
    source += '_Static_assert(sizeof(size_t) == 8, "LP64 size_t width");\n'
    for name, (size, offsets) in layouts.items():
        source += f'_Static_assert(sizeof({name}) == {size}, "{name} size");\n'
        source += f'_Static_assert(_Alignof({name}) == 8, "{name} alignment");\n'
        for field, offset in offsets.items():
            source += f'_Static_assert(offsetof({name}, {field}) == {offset}, "{name}.{field}");\n'
    source += "int main(void) { return 0; }\n"
    source_path = OUT / "proposed-layout.c"
    source_path.write_text(source)
    clang = run("apple-clang-path", ["xcrun", "--find", "clang"])
    run("apple-clang-version", [clang, "--version"])
    run("xcode-version", ["xcodebuild", "-version"])
    run("android-clang-version", [NDK / "bin/aarch64-linux-android28-clang", "--version"])
    mac_sdk = run("macos-sdk", ["xcrun", "--sdk", "macosx", "--show-sdk-path"])
    ios_sdk = run("ios-sdk", ["xcrun", "--sdk", "iphoneos", "--show-sdk-path"])
    flags = ["-std=c11", "-Wall", "-Wextra", "-Werror"]
    host = scratch / "host-layout"
    run("host-build", [clang, *flags, source_path, "-o", host])
    run("host-execute", [host])
    run("macos-x86_64-compile", [clang, *flags, "-target", "x86_64-apple-macos14", "-isysroot", mac_sdk, "-c", source_path, "-o", scratch / "x86_64.o"])
    run("ios-arm64-compile", [clang, *flags, "-target", "arm64-apple-ios17.0", "-isysroot", ios_sdk, "-c", source_path, "-o", scratch / "ios.o"])
    run("android-arm64-compile", [NDK / "bin/aarch64-linux-android28-clang", *flags, "-c", source_path, "-o", scratch / "android.o"])
    run("android-object-header", [NDK / "bin/llvm-readelf", "-h", scratch / "android.o"])
    if DOC.read_text() != document:
        raise RuntimeError("Proposal changed during layout checks")
    receipt = {
        "schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "sourceNote": "Proposal and runner were uncommitted; exact file hashes below identify these inputs",
        "inputs": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in [DOC, Path(__file__).resolve(), source_path]},
        "environment": {"DEVELOPER_DIR": ENV["DEVELOPER_DIR"]}, "commands": commands,
        "assertions": {name: {"size": size, "alignment": 8, "offsets": offsets} for name, (size, offsets) in layouts.items()},
        "artifacts": {str(p): sha(p.read_bytes()) for p in scratch.iterdir()},
        "result": "Proposed C layouts compile with all size/alignment/offset assertions; native host program exits0",
        "limitations": ["No public header or capability C functions implemented", "No Rust repr(C) parity, native registry, pointer validation, archive linking, Swift bridge or protocol execution", "iOS/Android objects cross-compiled only; no device command, install or run", "No ABI/release/activation or GA gate closed"]
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"result": receipt["result"], "commands": len(commands), "artifactDirectory": str(scratch)}))


if __name__ == "__main__":
    main()
