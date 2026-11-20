"""Verify the rebuild inputs and seal the complete host-verified handoff."""

import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from package import digest, inventory, pin, read, require, write
from run import size_kib

RECIPE = Path(__file__).resolve().parent
ROOT = RECIPE.parents[3]
BASE = "2e8f505f789c97c0f1330c611f6b0378daabf3d5"
AAPT2 = "Android Asset Packaging Tool (aapt) 2.20-13193326"
STAGES = (
    "preflight", "source-fetch", "source-checkout", "source-check", "mixer-export", "mixer-overlay",
    "appearance-export", "vm-android", "vm-host", "app-build", "java-build", "build-guests", "host-build",
    "package", "replay-host",
)


def capture(*argv, **settings):
    return subprocess.check_output(
        argv, env=os.environ | settings, stderr=subprocess.STDOUT, text=True, timeout=20,
    ).strip()


def verify_recipe():
    lock = RECIPE / "recipe.sha256"
    entries = {}
    for line in lock.read_text().splitlines():
        expected, name = line.split("  ", maxsplit=1)
        entries[name] = expected
        pin(ROOT / name, expected)
    own_files = inventory(ROOT, RECIPE)
    own_files.pop(lock.relative_to(ROOT).as_posix())
    require(own_files == {name: value for name, value in entries.items() if name in own_files},
            "Recipe directory contains an unpinned input")
    require(len(entries) == len(lock.read_text().splitlines()), "Duplicate recipe pin")
    return digest(lock)


def preflight(work):
    require(sys.platform == "darwin" and platform.machine() == "arm64", "Run on arm64 macOS")
    recipe_lock = verify_recipe()
    require(subprocess.run(["git", "-C", ROOT, "merge-base", "--is-ancestor", BASE, "HEAD"],
                           timeout=15).returncode == 0, "Use the pinned public Mixer base or a descendant")
    home = Path.home()
    swift = home / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
    rust = home / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc"
    sdk = Path(os.environ["ANDROID_HOME"])
    java = Path(os.environ["JAVA_HOME"])
    roots = {
        "android": sdk,
        "swift": swift,
        "swiftAndroidSDK": home / ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle",
        "java": java,
    }
    tool_pins = read(RECIPE / "toolchain-pins.json")
    for kind, files in tool_pins.items():
        for name, expected in files.items():
            pin(roots[kind] / name, expected)

    tools = sdk / "build-tools/36.0.0"
    host_xcode = "/Applications/Xcode.app/Contents/Developer"
    build_xcode = "/Applications/Xcode_26.6.app/Contents/Developer"
    versions = {
        "hostOS": capture("/usr/bin/sw_vers").splitlines(),
        "hostArchitecture": platform.machine(),
        "hostXcode": capture("/usr/bin/xcodebuild", "-version", DEVELOPER_DIR=host_xcode).splitlines(),
        "buildXcode": capture("/usr/bin/xcodebuild", "-version", DEVELOPER_DIR=build_xcode).splitlines(),
        "hostSwift": capture("/usr/bin/swift", "--version", DEVELOPER_DIR=host_xcode).splitlines(),
        "swiftAndroid": capture(swift / "swift-frontend", "-version").splitlines(),
        "rust": capture(rust, "--version"),
        "java": capture(java / "bin/javac", "-version"),
        "aapt2": capture("/usr/bin/arch", "-arm64", tools / "aapt2", "version"),
        "aapt2MachOArchitectures": capture("/usr/bin/lipo", "-archs", tools / "aapt2").split(),
        "d8": capture(tools / "d8", "--version"),
        "apksigner": capture(tools / "apksigner", "version").splitlines()[-1],
        "androidBuildTools": "36.0.0",
        "androidPlatform": "android-36",
        "androidNDK": "27.1.12297006",
        "swiftAndroidTarget": "aarch64-unknown-linux-android28",
        "apkABI": "arm64-v8a",
        "git": capture("git", "--version"),
        "python": capture(sys.executable, "--version"),
    }
    require(versions["hostXcode"] == ["Xcode 27.2", "Build version 27B52"]
            and versions["buildXcode"] == ["Xcode 26.6", "Build version 17F113"]
            and versions["rust"] == "rustc 1.99.0 (b940084d7 2026-09-28)"
            and versions["java"] == "javac 25.0.4.1"
            and versions["aapt2"] == AAPT2 and "arm64" in versions["aapt2MachOArchitectures"],
            "Expected the pinned host, Rust, JDK and arm64 AAPT2 tools")
    repos = home / "Library/Caches/org.swift.swiftpm/repositories"
    mirrors = {}
    for entry in read(RECIPE / "Package.resolved")["pins"]:
        name = entry["identity"]
        suffix = {"swift-asn1": "7065ad2c", "swift-crypto": "7e0614ea"}[name]
        repo = repos / f"{name}-{suffix}"
        revision = entry["state"]["revision"]
        mirrors[name] = {"revision": revision, "tree": capture("git", "-C", repo, "rev-parse", revision + "^{tree}")}
    write(work / "preflight.json", {
        "publicBase": BASE, "recipeLockSHA256": recipe_lock,
        "toolchainLockSHA256": digest(RECIPE / "toolchain-pins.json"),
        "toolchainSHA256": tool_pins, "toolVersions": versions, "swiftPMInputs": mirrors,
    })


def finish(work, output):
    provenance = read(work / "preflight.json")
    require(verify_recipe() == provenance["recipeLockSHA256"], "Recipe changed during rebuild")
    require(tuple(sorted(path.stem for path in (work / "logs").glob("*.json"))) == tuple(sorted(STAGES)),
            "Expected exactly the rebuild stages")
    runs = {name: read(work / "logs" / f"{name}.json") for name in STAGES}
    require(all(value["custody"] == "closed" and value["exit"] == 0 and "interrupted" not in value
                for value in runs.values()), "Incomplete build stage")
    engines = {}
    for target in ("android", "host"):
        for name, expected in provenance["swiftPMInputs"].items():
            checkout = work / f"{target}-build/checkouts" / name
            git = ("git", "-C", checkout)
            require(capture(*git, "log", "-1", "--format=%H %T") == f'{expected["revision"]} {expected["tree"]}'
                    and not capture(*git, "status", "--porcelain", "--untracked-files=all"),
                    f"{target} SwiftPM checkout differs: {name}")
        engine = read(work / f"{target}-engine/receipt.json")
        require(engine["commands"] and all(command["exit_code"] == 0 and command["problem"] is None
                                          for command in engine["commands"]), "Incomplete VM builder command")
        engines[target] = {
            "revision": engine["source_revision"], "target": engine["rust_target"],
            "sourceManifestSHA256": engine["source_manifest_sha256"], "archiveSHA256": engine["library"]["sha256"],
            "closedCommands": [command["name"] for command in engine["commands"]],
        }
    build = read(output / "build-receipt.json")
    host = read(output / "host-receipt.json")
    require(host["status"] == "passed" and host["runtime"] == build["androidRuntime"], "Host replay did not close")
    require(inventory(output, output / "delivery-android") == read(output / "materials.sha256.json"),
            "Delivery changed after host replay")
    require(all(digest(output / "delivery-android/Installed" / name) == value
                for name, value in read(output / "installed.sha256.json").items())
            and digest(output / build["apk"]) == build["apkSHA256"], "Packaged inputs changed after host replay")
    for original, name in ((RECIPE / "handoff.md", "README.md"), (RECIPE / "origin.py", "origin.py"),
                           (work / "calculation-distributor.py", "calculation-distributor.py")):
        shutil.copyfile(original, output / name)
    write(output / "rebuild-receipt.json", provenance | {
        "scope": "source-only Android debug APK and macOS host replay",
        "historicalAPKInputs": [],
        "runs": runs, "verifiedSwiftPMCheckouts": ["android", "host"], "engines": engines,
        "apkSHA256": build["apkSHA256"], "apkSignerSHA256": build["apkSignerSHA256"],
        "androidRuntime": build["androidRuntime"], "buildReceiptSHA256": digest(output / "build-receipt.json"),
        "hostReceiptSHA256": digest(output / "host-receipt.json"),
        "peakSampledScratchKiB": max(size_kib(work, output), *(value["peakSampledScratchKiB"] for value in runs.values())),
    })
    hashes = inventory(output, output)
    expected = set(read(output / "materials.sha256.json")) | {
        build["apk"], "README.md", "build-receipt.json", "host-receipt.json", "installed.sha256.json",
        "materials.sha256.json", "origin.py", "calculation-distributor.py", "rebuild-receipt.json",
    }
    require(set(hashes) == expected, "Unexpected handoff file set")
    with (output / "SHA256SUMS").open("x") as stream:
        stream.writelines(f"{value}  {name}\n" for name, value in sorted(hashes.items()))
    print(f"Verified source-built handoff: {output}")


if __name__ == "__main__":
    action, scratch, packet = sys.argv[1:]
    if action == "check":
        preflight(Path(scratch))
    elif action == "finish":
        finish(Path(scratch), Path(packet))
    else:
        raise SystemExit(f"Unknown action: {action}")
