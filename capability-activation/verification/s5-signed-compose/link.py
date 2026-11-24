#!/usr/bin/env python3
"""Link the S5 Compose wire and signed activation dependencies for ARM64 API 28."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
COMPOSE = "18fef233e694ad9613a7427c81bdc89e9bc062dc"
PINS = {
    "swift-crypto": ("swift-crypto-7e0614ea", "c2cbadd7263439d8015189668f96ff5b5be565ce"),
    "swift-asn1": ("swift-asn1-7065ad2c", "3b6410f7dee09eb33cdd26260c5fd47fda19b0e2"),
}
TARGET = "aarch64-unknown-linux-android28"
MANIFEST = """// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "S5SignedCompose", platforms: [.macOS(.v14)],
    products: [.library(name: "S5SignedLink", type: .dynamic, targets: ["S5SignedLink"]),
               .library(name: "MixerComposeEditor", type: .dynamic, targets: ["MixerComposeEditor"])],
    dependencies: [.package(path: "../capability-activation"), .package(path: "../sdk"),
                   .package(path: "../updates"), .package(path: "../runtime-identity"),
                   .package(path: "../../swift-crypto")],
    targets: [.target(name: "S5SignedLink", dependencies: [
        .product(name: "MixerCapabilityActivation", package: "capability-activation"),
        .product(name: "MixerUpdates", package: "updates"),
        .product(name: "MixerGuest", package: "sdk"),
        .product(name: "MixerAndroid", package: "sdk"),
        .product(name: "MixerUI", package: "sdk"),
    ]), .target(name: "MixerComposeEditor", dependencies: [
        .product(name: "MixerAndroid", package: "sdk"),
        .product(name: "MixerUI", package: "sdk"),
        .product(name: "MixerCapabilityActivation", package: "capability-activation"),
        .product(name: "MixerCapabilities", package: "sdk"),
        .product(name: "MixerUpdates", package: "updates"),
    ]), .executableTarget(name: "SignFixture", dependencies: [
        .product(name: "Crypto", package: "swift-crypto"),
        .product(name: "MixerCapabilities", package: "sdk"),
        .product(name: "MixerUpdates", package: "updates"),
        .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
    ]), .executableTarget(name: "Replay", dependencies: [
        .product(name: "MixerCapabilityActivation", package: "capability-activation"),
        .product(name: "MixerCapabilities", package: "sdk"),
        .product(name: "MixerUI", package: "sdk"),
        .product(name: "MixerUpdates", package: "updates"),
    ])], swiftLanguageModes: [.v6])
"""


def run(*argv, **kwargs):
    argv = list(map(str, argv))
    print("+", subprocess.list2cmdline(argv), flush=True)
    return subprocess.run(argv, check=True, **kwargs)


def archive(work, repository, revision, into, *paths):
    run("git", "-C", repository, "archive", "-o", work / "archive.tar", revision, *paths)
    into.mkdir(parents=True, exist_ok=True)
    with tarfile.open(work / "archive.tar") as contents:
        contents.extractall(into, filter="data")
    (work / "archive.tar").unlink()


def prepare(work, revision, swift_cache):
    source = work / "source"
    archive(work, ROOT, revision, source,
            "capability-activation", "experimental-capability-runtime/Package.swift",
            "experimental-capability-runtime/Sources", "experimental-capability-runtime/Tests",
            "updates", "runtime-identity", "sdk", "vm")
    archive(work, ROOT, COMPOSE, source, "native/android/compose", "cli/Sources/MixerBuild/AndroidPublicHost.swift")
    path = "sdk/Sources/MixerAndroid/AndroidUIHost.swift"
    pinned = run("git", "-C", ROOT, "show", f"{COMPOSE}:{path}", capture_output=True, text=True).stdout
    compose = pinned.split("/// Version 1 of the asynchronous Compose presentation boundary.", 1)[1]
    with (source / path).open("a") as target:
        target.write("\n/// Version 1 of the asynchronous Compose presentation boundary." + compose)
    for name, (repo, pin) in PINS.items():
        archive(work, swift_cache / repo, pin, work / name)
    for name in ("sdk", "updates"):
        manifest = source / name / "Package.swift"
        remote = '.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")'
        contents = manifest.read_text()
        if contents.count(remote) != 1:
            raise ValueError(f"Unexpected dependency in {manifest}")
        manifest.write_text(contents.replace(remote, '.package(path: "../../swift-crypto")'))
    return source


def digest(path):
    with path.open("rb") as contents:
        return hashlib.file_digest(contents, "sha256").hexdigest()


def add_runtime(source, work):
    run("git", "apply", HERE / "runtime.patch", cwd=source,
        env={**os.environ, "GIT_CEILING_DIRECTORIES": str(work)})
    module = source / "capability-activation/Sources/MixerCapabilityActivation"
    for name in ("S5SignedPresentation.swift", "S5SignedProfile.swift"):
        shutil.copy2(HERE / name, module)
    header = source / "experimental-capability-runtime/Sources/CMixerVMCapability/include/MixerVMCapability.h"
    with header.open("a") as contents:
        contents.write('\n#include <mixer_vm_guest_ui_v2.h>\n')


def guests(work, swift):
    out = work / "guests"
    out.mkdir()
    for name in ("prior", "candidate"):
        obj = out / (name + ".o")
        wasm = out / (name + ".wasm")
        define = ["-DPRIOR"] if name == "prior" else []
        run(swift.parent / "clang", "--target=wasm32-unknown-none", "-ffreestanding", "-Oz",
            "-Wall", "-Wextra", "-Werror", *define, "-c", HERE / "guest.c", "-o", obj)
        run(swift.parent / "wasm-ld", "--no-entry", "--gc-sections", "--strip-all",
            "-z", "stack-size=4096", "--initial-memory=1179648", "--max-memory=1179648",
            "--export=mixer_guest_ui_start_v2", "--export=mixer_guest_ui_event_v2",
            "--export=mixer_guest_capability_ready_v1", obj, "-o", wasm)
        print(name, wasm.stat().st_size, digest(wasm), flush=True)
    return out


def build_vm(source, work, rust, cross):
    target = ["--target", "aarch64-linux-android"] if cross else []
    run(rust / "cargo", "build", "--manifest-path", source / "vm/Cargo.toml", "--offline", "--locked",
        *target, "--release", "--lib", "--features", "experimental-guest-ui-v2-native",
        "--target-dir", work / "vm-build")
    output = work / "vm-build"
    if cross:
        output /= "aarch64-linux-android"
    output /= "release"
    (output / "libmixer_vm_capability_experimental.a").symlink_to("libmixer_vm.a")
    return output


def make_package(source):
    package = source / "link"
    targets = {
        "S5SignedLink": ("Link.swift",),
        "MixerComposeEditor": ("EditorFixture.swift", "SignedJourney.swift"),
        "Replay": ("Replay.swift", "SignedJourney.swift"),
        "SignFixture": ("SignFixture.swift",),
    }
    for name, files in targets.items():
        target = package / "Sources" / name
        target.mkdir(parents=True)
        for file in files:
            shutil.copy2(HERE / file, target)
    template = (source / "cli/Sources/MixerBuild/AndroidPublicHost.swift").read_text()
    snippet = template.split('static let composeEditorBridgeV1 = #"""\n', 1)[1].split('\n    """#', 1)[0]
    snippet = dedent(snippet).replace(
        'Set(editor.properties.keys) == ["value", "label"]',
        'Set(editor.properties.keys) == ["value", "label", "axis"], editor.properties["axis"] == .string("horizontal")')
    (package / "Sources/MixerComposeEditor/ComposeEditorWireV1.swift").write_text(snippet + "\n")
    (package / "Package.swift").write_text(MANIFEST)
    return package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("--revision", default="ebbc4735a234d42622b435acd2ddc9ff430c1d20")
    parser.add_argument("--mode", choices=("link", "host", "android"), default="host")
    args = parser.parse_args()
    work = args.work.resolve()
    if not work.is_relative_to(ROOT / "verification/local") or work.exists():
        parser.error("Choose a new directory below verification/local")
    for name in ("tmp", "cache", "cargo-home"):
        (work / name).mkdir(parents=True)
    home = Path.home()
    swift = home / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
    rust = home / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
    sdk_dir = home / ".swiftpm/swift-sdks"
    ndk = (sdk_dir / "swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d"
           / "toolchains/llvm/prebuilt/darwin-x86_64")
    llvm = ndk / "bin"
    os.environ.update(TMPDIR=str(work / "tmp"), XDG_CACHE_HOME=str(work / "cache"),
        CLANG_MODULE_CACHE_PATH=str(work / "cache/clang"), CARGO_HOME=str(work / "cargo-home"),
        DEVELOPER_DIR="/Applications/Xcode_26.6.app/Contents/Developer",
        SWIFTCI_USE_LOCAL_DEPS="1", GIT_ALLOW_PROTOCOL="file", GIT_NO_LAZY_FETCH="1",
        RUSTC=str(rust / "rustc"), CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER=str(llvm / "aarch64-linux-android28-clang"))
    run("git", "-C", ROOT, "show", "-s", "--format=%H %T", args.revision)
    source = prepare(work, args.revision, home / "Library/Caches/org.swift.swiftpm/repositories")
    run(swift, "--version")
    run(rust / "rustc", "--version")
    cross = args.mode != "host"
    if args.mode != "link":
        add_runtime(source, work)
    output = build_vm(source, work, rust, cross)
    package = make_package(source)
    build = [swift, "build", "--package-path", package, "--scratch-path", work / "swift-build",
             "--cache-path", work / "cache/swift", "--disable-dependency-cache", "--disable-index-store",
             "--jobs", "8", "-Xcc", f"-I{source / 'vm/include'}", "-Xlinker", f"-L{output}"]
    if args.mode != "link":
        build += ["-Xswiftc", "-DMIXER_S5_SIGNED_COMPOSE"]
    if not cross:
        run(*build, "--product", "SignFixture")
        run(*build, "--product", "Replay")
        binaries = Path(run(*build, "--show-bin-path", capture_output=True, text=True).stdout.strip())
        run(binaries / "SignFixture", source / "capability-activation/Tests/MixerCapabilityActivationTests/Fixtures",
            guests(work, swift), work / "assets", args.revision, digest(output / "libmixer_vm.a"), digest(binaries / "Replay"))
        run(binaries / "Replay", work / "assets", work / "app-private")
        return
    product = "MixerComposeEditor" if args.mode == "android" else "S5SignedLink"
    run(*build, "--swift-sdks-path", sdk_dir, "--swift-sdk", TARGET,
        "-Xlinker", "--no-undefined", "--product", product)
    matches = list((work / "swift-build").glob(f"*/debug/lib{product}.so"))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one Android library, found {matches}")
    run(llvm / "llvm-readelf", "-h", "-d", matches[0])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
