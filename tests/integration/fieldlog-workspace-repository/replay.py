#!/usr/bin/env python3
"""Reconstruct, apply, build, and compare the FieldLog repository change."""
import argparse
import json
import os
from pathlib import Path
import sys

from collect import REVIEWED, summarize
from existing_tests import run_tests
from native_build import build_native
from replay_host import run_host
from run import OwnedCommands, publish_receipt

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mixer", type=Path, help="Mixer history checkout with local commit 062aaf116b")
    parser.add_argument("work", type=Path, help="Fresh disposable scratch directory")
    parser.add_argument("output", type=Path, help="Fresh directory for the receipt and designed afterimages")
    parser.add_argument("--host-only", action="store_true", help="Run both disk replays and focused host checks")
    args = parser.parse_args()
    mixer, work, output = map(Path.resolve, (args.mixer, args.work, args.output))
    if work == output or work.is_relative_to(output) or output.is_relative_to(work):
        parser.error("output and work must use separate paths")
    if work.exists() or output.exists():
        parser.error("both work and output must be absent")
    work.mkdir()
    output.mkdir()
    temporary = work / "tmp"
    temporary.mkdir()
    env = os.environ.copy()
    env["TMPDIR"] = str(temporary)
    python = [sys.executable, "-B"]

    commands = OwnedCommands(work)

    def step(name, seconds, *command, overrides=None):
        command_env = dict(env, **(overrides or {}))
        commands.run(name, work, seconds, [str(item) for item in command], command_env)

    publishing_report = False
    cleaned = False
    try:
        step("prepare", 70, *python, HERE / "prepare.py", mixer, work)
        step("deps", 55, *python, HERE / "deps.py", work)
        step("mixer-public-pin", 30, "/usr/bin/curl", "-fsSL", "--max-time", "20",
             "https://api.github.com/repos/snowdamiz/mixer/git/commits/6bc461f4fc7c29771718c7c5ce5a2a39b78f4d2d")
        public = json.loads((work / "commands/mixer-public-pin.log").read_text())
        assert public["sha"] == "6bc461f4fc7c29771718c7c5ce5a2a39b78f4d2d"
        assert public["tree"]["sha"] == "d888b6a1ef9331079b98a0dc21c3a1b8ee482894"
        app = work / "fieldlog"
        patch = HERE / "fieldlog-workspace-repository.patch"
        step("apply-product", 12, "git", "-C", app, "apply", "--index", patch)
        step("candidate-tree", 12, "git", "-C", app, "write-tree")
        tree = (work / "commands/candidate-tree.log").read_text().strip()
        assert tree == (HERE / "candidate-tree.txt").read_text().strip()
        for arm, identity in (("baseline", REVIEWED), ("final", tree)):
            step("materialize-" + arm, 25, *python, HERE / "materialize.py", work, arm, identity)
            for platform in ("apple", "export"):
                run_host(commands, arm, platform)
            run_tests(commands, arm, "android")
        run_tests(commands, "final", "apple")
        build_native(commands, "final", "standalone-export")
        if not args.host_only:
            rust = Path.home() / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
            step("ios-vm", 150, rust / "cargo", "build", "--manifest-path", work / "mixer/vm/Cargo.toml",
                 "--offline", "--locked", "--release", "--features", "experimental-capability-native",
                 "--lib", "--target", "aarch64-apple-ios", "--target-dir", work / "ios-cargo",
                 "--jobs", "6", overrides={"PATH": f"{rust}:{env['PATH']}", "RUSTC": str(rust / "rustc")})
            lib = work / "ios-cargo/aarch64-apple-ios/release"
            os.link(lib / "libmixer_vm.a", lib / "libmixer_vm_capability_experimental.a")
            build_native(commands, "final", "android")
            build_native(commands, "final", "iphoneos")
            ndk = Path(os.environ.get("ANDROID_HOME", "/opt/homebrew/share/android-commandlinetools"))
            ndk = ndk / "ndk/27.1.12297006/toolchains/llvm/prebuilt/darwin-x86_64/bin"
            elf = work / "final-android/build/aarch64-unknown-linux-android28/release/libAppAndroid.so"
            ios = work / "final-iphoneos/derived/Build/Products/Debug-iphoneos"
            step("read-android-elf", 12, ndk / "llvm-readelf", "-h", "-lW", elf)
            step("read-android-symbols", 12, ndk / "llvm-nm", "--defined-only", elf)
            step("read-ios-macho", 12, "/usr/bin/otool", "-hv", "-l", ios / "FieldLog.app/FieldLog")
            step("read-ios-storage-symbols", 12, "/usr/bin/nm", ios / "FieldLogStorage.o")
        result = summarize(work, output, commands.checked_receipts(), args.host_only)
        publishing_report = True
        publish_receipt(output / "receipt.json", result)
        publishing_report = False
    finally:
        if publishing_report:
            print(f"Preserving scratch after replay receipt publication failed: {work}", file=sys.stderr)
        else:
            cleaned = commands.cleanup()
    if not cleaned:
        raise SystemExit(74)
    print(f"Matched both full disk replays. Evidence in {output}")

if __name__ == "__main__":
    main()
