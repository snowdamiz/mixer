#!/usr/bin/env python3
"""Project pinned public inputs and build the stock D6 CLI and VM offline."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
MIXER = "78d25a1b8d4574779457e1f0c1518a56099857b9"
SDK = "584cd1947edd590fd9fc732197f7d737287ab36f"
FIELDLOG = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
FIELDLOG_TREE = "1b62520f35c7e57a01b568291078686574f627c4"
HOSTED = "888c578994df11e21458eb703fbd90c2bc648ecf"
HOSTED_TREE = "ac22272afdbf5efd3e55d3547cd214346b7851ff"
CRYPTO = "c2cbadd7263439d8015189668f96ff5b5be565ce"
ASN1 = "3b6410f7dee09eb33cdd26260c5fd47fda19b0e2"
LIBRARY = "libmixer_vm_capability_experimental.a"
VM_SHA = "f3afa1e76f3d27be572dc7d2f269763c43b6c4331231ecd308eb96ed40d5fae1"
PROJECT_SHA = "1a5468c5951e5a91e1c04778029eb2017b2ef1109e25ff3d9a9b75a29af51233"
PACKAGES = ("sdk", "updates", "runtime-identity", "capability-activation", "experimental-capability-runtime")
HEADERS = ("mixer_vm.h", "mixer_vm_capability.h", "mixer_vm_guest_ui.h", "mixer_vm_guest_ui_deferred.h")
SWIFT = ("Apple Swift version 6.4.2 (swiftlang-6.4.2.1.9 clang-2100.4.1.1)\n"
         "Target: arm64-apple-macosx27.0.0")
XCODE = "Xcode 27.2\nBuild version 27B52"
ORIGIN_PORT = 54811
EXCLUDED = {".git", ".gitignore", ".build", ".swiftpm", "Package.resolved", "verification", "build-verification"}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def roster(root):
    paths = sorted(root.rglob("*"))
    require(all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths),
            f"invalid source member under {root}")
    return {p.relative_to(root).as_posix(): digest(p) for p in paths if p.is_file()}


def tree(files):
    return hashlib.sha256("".join(f"{p}\0{value}\n" for p, value in sorted(files.items())).encode()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(argv, env, *, cwd=None, timeout=30):
    return subprocess.check_output(argv, cwd=cwd, env=env, timeout=timeout, stderr=None)


def private_env(root):
    for name in ("home", "tmp", "modules"):
        (root / name).mkdir(exist_ok=True)
    env = {"PATH": os.environ["PATH"], "HOME": str(root / "home"), "TMPDIR": str(root / "tmp"),
           "CFFIXED_USER_HOME": str(root / "home"), "CLANG_MODULE_CACHE_PATH": str(root / "modules"),
           "LC_ALL": "C", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_NO_LAZY_FETCH": "1", "GIT_ALLOW_PROTOCOL": "file", "PYTHONDONTWRITEBYTECODE": "1"}
    if "DEVELOPER_DIR" in os.environ:
        env["DEVELOPER_DIR"] = os.environ["DEVELOPER_DIR"]
    return env


def git(repo, env, *args):
    return run(["/usr/bin/git", "--no-replace-objects", "-C", repo, *args], env)


def project_git(repo, revision, output, env, *paths):
    payload = git(repo, env, "archive", "--format=tar", revision, *paths)
    output.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        members = archive.getmembers()
        require(all(member.isfile() or member.isdir() for member in members), f"nonregular input in {revision}")
        archive.extractall(output, filter="data")


def change(path, before, after):
    contents = path.read_text()
    require(before in contents, f"pinned text missing in {path.name}")
    path.write_text(contents.replace(before, after))


def swift_flags(work):
    return ["--package-path", work / "cli-source/cli", "--scratch-path", work / "cli-build",
            "--disable-dependency-cache", "--force-resolved-versions", "--skip-update",
            "--disable-sandbox", "-j", "6"]


def prepare(args):
    work = args.output
    work.mkdir(mode=0o700)
    env = private_env(work)
    require(run(["/usr/bin/xcodebuild", "-version"], env).decode().strip() == XCODE, "Xcode pin differs")
    require(run(["/usr/bin/xcrun", "swift", "--version"], env).decode().strip() == SWIFT, "Swift pin differs")
    require(git(args.mixer, env, "rev-parse", f"{HOSTED}:hosted").decode().strip() == HOSTED_TREE,
            "hosted tree pin differs")
    fieldlog, sdk = work / "fieldlog-source", work / "sdk-source"
    project_git(args.fieldlog, FIELDLOG_TREE, fieldlog, env, "Package.swift", "Sources", "Integrations", "Tests", "ios")
    project_git(args.mixer, SDK, sdk, env, *PACKAGES, "vm/Cargo.toml", "vm/Cargo.lock", "vm/src", "vm/include", "vm/examples")
    project_git(args.mixer, MIXER, work / "cli-source", env, "cli", "sdk", "updates", "runtime-identity")
    project_git(args.mixer, HOSTED, work, env, "hosted", "docs/operations",
                "tests/integration/phoenix-release-restore", "tests/integration/free-project-starter/registration-runner.py")
    for root, name in ((fieldlog, "fieldlog.patch"), (sdk, "mixer-sdk.patch")):
        git(root, env, "apply", "--no-index", "--whitespace=nowarn", str(HERE / name))

    cargo = args.rust_bin / "cargo"
    rustc = args.rust_bin / "rustc"
    require(run([rustc, "-V"], env).decode().strip() == "rustc 1.99.0 (b940084d7 2026-09-28)",
            "Rust pin differs")
    sdkroot = run(["/usr/bin/xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], env).decode().strip()
    cargo_home = work / "cargo-home"
    cargo_home.mkdir()
    run([cargo, "build", "--locked", "--offline", "--release", "--lib", "--no-default-features",
         "--features", "experimental-capability-native", "--manifest-path", sdk / "vm/Cargo.toml",
         "--target", "aarch64-apple-ios-sim", "--target-dir", work / "vm-target"],
        dict(env, CARGO_HOME=str(cargo_home), RUSTC=str(rustc), SDKROOT=sdkroot, IPHONEOS_DEPLOYMENT_TARGET="26.0"),
        cwd=sdk, timeout=120)
    library = work / "vm-target/aarch64-apple-ios-sim/release/libmixer_vm.a"
    require(digest(library) == VM_SHA, "VM archive differs from the accepted source/toolchain pin")

    app = work / "RegisteredFieldLog"
    platform = app / "Platforms/iOS"
    platform.mkdir(parents=True)
    for name in ("Sources", "Integrations", "Tests"):
        shutil.copytree(fieldlog / name, app / name, ignore=shutil.ignore_patterns(*EXCLUDED))
    shutil.copyfile(fieldlog / "Package.swift", app / "Package.swift")
    for source in sorted((fieldlog / "ios/FieldLog").glob("*.swift")):
        shutil.copyfile(source, platform / source.name)
    native = platform / "Native"
    native.mkdir()
    shutil.copyfile(library, native / LIBRARY)

    generated = app / "Generated"
    for name in PACKAGES:
        target = "MixerSDK" if name == "sdk" else name
        shutil.copytree(sdk / name, generated / target, ignore=shutil.ignore_patterns(*EXCLUDED))
    bridge = generated / "experimental-capability-runtime/Sources/CMixerVMCapability/include"
    for name in HEADERS:
        shutil.copyfile(sdk / "vm/include" / name, bridge / name)

    for name, checkout, revision in (("swift-crypto", args.crypto, CRYPTO), ("swift-asn1", args.asn1, ASN1)):
        project_git(checkout, revision, generated / "Vendor" / name, env)
    package = app / "Package.swift"
    change(package, "products: [", 'products: [.library(name: "AppFeatures", targets: '
           '["FieldLogFeatures", "FieldLogModels", "FieldLogStorage", "FieldLogInstalledGuest"]), ')
    change(package, "../mixer/sdk", "Generated/MixerSDK")
    change(package, "../mixer/", "Generated/")
    change(package, 'package: "sdk"', 'package: "MixerSDK"')
    for name in ("MixerSDK", "updates"):
        change(generated / name / "Package.swift",
               '.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")',
               '.package(path: "../Vendor/swift-crypto")')
    for name in ("capability-activation", "experimental-capability-runtime"):
        change(generated / name / "Package.swift", '"../sdk"', '"../MixerSDK"')
        change(generated / name / "Package.swift", 'package: "sdk"', 'package: "MixerSDK"')
    change(generated / "experimental-capability-runtime/Package.swift",
           '            .linkedLibrary("mixer_vm_capability_experimental"),\n', '')
    change(generated / "Vendor/swift-crypto/Package.swift",
           '.package(url: "https://github.com/apple/swift-asn1.git", from: "1.2.0")',
           '.package(path: "../swift-asn1")')

    resources = platform / "ChecklistRelease"
    resources.mkdir()
    for name in ("bridge.json", "storage.json", "storage-grant.json"):
        shutil.copyfile(HERE / "fixture" / name, resources / name)
    (resources / "port.txt").write_text(f"{ORIGIN_PORT}\n")
    # The worker receives provisional files only. The separate fixture signer replaces these after download.
    write(resources / "roots.json", [])
    write(resources / "identity.json", {})
    write(app / "mixer.yml", {
        "schema": 1, "name": "FieldLog", "application": "dev.mixer.fieldlog", "language": "swift",
        "targets": ["ios"], "toolchainLock": "mixer.lock", "capabilities": ["storage.files"],
        "updates": {"activation": "cold-start", "compatibility": "exact-runtime-fingerprint",
                    "requireArtifactSignature": True, "requireAssignmentSignature": True},
        "iosNative": {
            "swiftSources": sorted(p.name for p in platform.glob("*.swift") if p.name != "FieldLogApp.swift"),
            "resourceFolders": ["ChecklistRelease"], "allowsLocalNetworking": True,
            "localNetworkUsageDescription": "Connect to the developer checklist service on this local network.",
            "simulatorArchive": f"Native/{LIBRARY}", "simulatorArchiveSHA256": VM_SHA,
        },
    })
    write(app / "mixer.lock", {"schema": 1, "sdkDigest": tree(roster(generated / "MixerSDK")),
                              "sdkDistribution": "bundled-source-snapshot", "swiftVersion": SWIFT + "\nswift-driver version: 1.168.6",
                              "generatedBy": "mixer 0.1.0-dev", "qualification": "local-development-only"})
    require(len(list(platform.glob("*.swift"))) == 7, "FieldLog source roster differs")
    write(work / "source.json", {"fieldLog": FIELDLOG, "fieldLogTree": FIELDLOG_TREE, "sdk": SDK, "mixerCLI": MIXER, "hostedTree": HOSTED_TREE,
                                 "sourceSHA256": tree(roster(app)), "vmSHA256": VM_SHA, "swift": SWIFT, "xcode": XCODE})

    for index, (name, mirror) in enumerate((("swift-crypto", args.crypto), ("swift-asn1", args.asn1))):
        env[f"GIT_CONFIG_KEY_{index}"] = f"url.{mirror.as_uri()}.insteadOf"
        env[f"GIT_CONFIG_VALUE_{index}"] = f"https://github.com/apple/{name}.git"
    env["GIT_CONFIG_COUNT"] = "2"
    run(["/usr/bin/xcrun", "swift", "build", *swift_flags(work), "--product", "mixer"],
        env, cwd=work, timeout=180)
    bin_path = Path(os.fsdecode(run(["/usr/bin/xcrun", "swift", "build", *swift_flags(work), "--show-bin-path"],
                                  env, cwd=work)).strip())
    # Keep the SwiftPM executable with its resource bundles.
    (work / "cli-path").write_text(str(bin_path / "mixer") + "\n")
    print(work / "source.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("mixer", "fieldlog", "crypto", "asn1", "rust-bin", "output"):
        parser.add_argument(f"--{option}", required=True, type=Path)
    args = parser.parse_args()
    for name in ("mixer", "fieldlog", "crypto", "asn1", "rust_bin"):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    args.output = args.output.parent.resolve(strict=True) / args.output.name
    os.umask(0o077)
    prepare(args)
