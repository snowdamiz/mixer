#!/usr/bin/env python3
"""Build an isolated current-source signed Mac harness. Never launch it."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CRYPTO = ROOT / "verification/local/runtime-embedding-2026-10-22/ios/checkouts/swift-crypto"
NATIVE = ROOT / "experimental-capability-runtime/build-verification/local/guest-ui-1adb25c-v2/host"
NATIVE_SHA = "4d3b6dc36ea034d5604299752d560cbbc0615002b6b5ef4e5c25bbb3cb7c6120"
CRYPTO_REVISION = "c2cbadd7263439d8015189668f96ff5b5be565ce"
DEVELOPER = "/Applications/Xcode.app/Contents/Developer"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    assert args.name and all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.name)
    evidence = HERE / "builds" / args.name
    evidence.mkdir(parents=True, exist_ok=False)
    work = HERE / ".build" / args.name
    work.mkdir(parents=True, exist_ok=False)
    source = work / "source"
    products = work / "products"
    products.mkdir()
    maps = work / "modulemaps"
    maps.mkdir()
    app = work / "MixerSignedGuestUITeardown.app"
    binary = app / "Contents/MacOS/MixerSignedGuestUI"
    dylib = products / "libMixerGuestUITeardownRuntime.dylib"
    receipt = {
        "schema_version": 1,
        "status": "building; app not launched",
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "repair_revision": "5a5b395",
        "driver_sha256": sha(Path(__file__)),
        "source": str(source),
        "commands": [],
        "scope": "Build-only: current owned Swift/C runtime closure independently compiled and linked with the retained immutable native VM archive and existing locally cached Swift Crypto 5.0.3 Apple CryptoKit sources. Exact public signed-window harness and test-only signer/bytecode fixture copies. No launch, UI interaction, display receipt, health injection, storage result, physical device, published consumer, release or GA qualification is claimed.",
        "limitations": [
            "Native VM archive is retained from guest-ui-1adb25c-v2, not rebuilt by this build.",
            "Ad-hoc Mac signing verifies local bundle integrity; no distribution signing or notarization.",
            "Runtime display, Save sample, and close/storage behavior remain pending native interaction.",
        ],
    }

    def save():
        (evidence / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    env = dict(os.environ, DEVELOPER_DIR=DEVELOPER, CLANG_MODULE_CACHE_PATH=str(work / "clang-cache"))

    def run(name, argv, cwd=ROOT, timeout=240):
        argv = [str(x) for x in argv]
        started = time.monotonic()
        try:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
            data, code = result.stdout, result.returncode
        except subprocess.TimeoutExpired as error:
            data, code = error.stdout or b"", 124
        log = evidence / (name + ".log")
        assert not log.exists()
        log.write_bytes(data)
        receipt["commands"].append({"name": name, "argv": argv, "cwd": str(cwd), "environment": {
            "DEVELOPER_DIR": DEVELOPER, "CLANG_MODULE_CACHE_PATH": env["CLANG_MODULE_CACHE_PATH"]},
            "exit_code": code, "elapsed_seconds": time.monotonic() - started,
            "log": str(log.relative_to(ROOT)), "log_sha256": sha(log)})
        save()
        print(name + ": " + str(code), flush=True)
        if code:
            raise RuntimeError(name + " failed; retained log")
        return data.decode(errors="replace").strip()

    try:
        run("repair-ancestry", ["git", "merge-base", "--is-ancestor", "5a5b395", "HEAD"])
        run("git-status", ["git", "status", "--porcelain=v1"])
        run("swift-version", ["xcrun", "swiftc", "--version"])
        run("clang-version", ["xcrun", "clang", "--version"])
        run("xcode-version", ["xcodebuild", "-version"])
        run("macos-version", ["sw_vers"])
        sdk = run("macos-sdk", ["xcrun", "--sdk", "macosx", "--show-sdk-path"])
        run("macos-sdk-version", ["xcrun", "--sdk", "macosx", "--show-sdk-version"])
        assert run("crypto-revision", ["git", "-C", CRYPTO, "rev-parse", "HEAD"]) == CRYPTO_REVISION
        assert not run("crypto-status", ["git", "-C", CRYPTO, "status", "--porcelain=v1"])
        assert sha(NATIVE / "lib/libmixer_vm_capability_experimental.a") == NATIVE_SHA

        paths = []
        folders = ["sdk/Sources", "updates/Sources/MixerUpdates", "updates/Sources/MixerDurableIO",
                   "runtime-identity/Sources/MixerRuntimeIdentity", "experimental-capability-runtime/Sources",
                   "capability-activation/Sources", "capability-activation/Tests/MixerCapabilityActivationTests/Fixtures"]
        for folder in folders:
            paths += [(p, str(p.relative_to(ROOT))) for p in (ROOT / folder).rglob("*") if p.is_file()]
        for filename in ["GuestUISignedFixture.swift", "GuestUISignedProgram.swift"]:
            path = ROOT / "capability-activation/Tests/MixerCapabilityActivationTests" / filename
            paths.append((path, str(path.relative_to(ROOT))))
        for filename in ["SignedWindowHarness.swift", "TestFixtureBundle.swift"]:
            path = ROOT / "verification/guest-ui-activation-window/Sources" / filename
            paths.append((path, "harness/" + filename))
        for relative in ["sdk/Package.swift", "updates/Package.swift", "runtime-identity/Package.swift",
                         "experimental-capability-runtime/Package.swift", "capability-activation/Package.swift", "THIRD_PARTY.yml"]:
            paths.append((ROOT / relative, relative))
        for path in sorted((CRYPTO / "Sources/Crypto").rglob("*")):
            if path.is_file():
                paths.append((path, "dependencies/swift-crypto/" + str(path.relative_to(CRYPTO))))
        for filename in ["Package.swift", "LICENSE.txt", "NOTICE.txt"]:
            path = CRYPTO / filename
            if path.exists():
                paths.append((path, "dependencies/swift-crypto/" + filename))
        for path in sorted(NATIVE.rglob("*")):
            if path.is_file() and ("include" in path.relative_to(NATIVE).parts or path.name in ["receipt.json", "libmixer_vm_capability_experimental.a"]):
                paths.append((path, "native/" + str(path.relative_to(NATIVE))))

        manifest = {}
        origins = {}
        for path, relative in sorted(paths, key=lambda row: row[1]):
            assert relative not in manifest
            destination = source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            expected = sha(path)
            shutil.copyfile(path, destination)
            assert sha(destination) == expected
            destination.chmod(0o444)
            manifest[relative] = expected
            origins[relative] = str(path)
        for directory in sorted((p for p in source.rglob("*") if p.is_dir()), reverse=True):
            directory.chmod(0o555)
        source.chmod(0o555)
        manifest_path = evidence / "source-manifest.json"
        manifest_path.write_text(json.dumps({"sha256": digest(manifest), "files": manifest, "origins": origins}, indent=2) + "\n")
        receipt.update(source_tree_sha256=digest(manifest), source_manifest=str(manifest_path.relative_to(ROOT)),
                       source_manifest_sha256=sha(manifest_path), source_file_count=len(manifest),
                       native_archive_sha256=NATIVE_SHA, crypto_revision=CRYPTO_REVISION)
        save()

        ctargets = [
            ("MixerCapabilityIO", "sdk/Sources/MixerCapabilities/NativeIO"),
            ("MixerDurableIO", "updates/Sources/MixerDurableIO"),
            ("MixerCapabilityDurableIO", "capability-activation/Sources/MixerCapabilityDurableIO"),
            ("CMixerVMCapability", "experimental-capability-runtime/Sources/CMixerVMCapability"),
        ]
        for name, folder in ctargets:
            includes = source / folder / "include"
            (maps / (name + ".modulemap")).write_text('module ' + name + ' { umbrella "' + str(includes) + '" export * }\n')
            files = sorted((source / folder).glob("*.c"))
            assert len(files) == 1
            run("compile-" + name, ["xcrun", "clang", "-target", "arm64-apple-macosx14.0", "-isysroot", sdk,
                "-Wall", "-Wextra", "-Werror", "-fPIC", "-I", includes, "-I", source / "native/include",
                "-c", files[0], "-o", products / (name + ".o")])
        receipt["generated_build_modulemaps"] = {str(p.relative_to(work)): sha(p) for p in sorted(maps.glob("*"))}
        flags = ["-parse-as-library", "-swift-version", "6", "-warnings-as-errors", "-enable-testing",
                 "-target", "arm64-apple-macosx14.0", "-sdk", sdk, "-I", str(products),
                 "-module-cache-path", str(work / "swift-cache")]
        for path in sorted(maps.glob("*.modulemap")):
            flags += ["-Xcc", "-fmodule-map-file=" + str(path)]
        flags += ["-Xcc", "-I" + str(source / "native/include")]
        modules = [
            ("Crypto", "dependencies/swift-crypto/Sources/Crypto"),
            ("MixerCore", "sdk/Sources/MixerCore"),
            ("MixerUI", "sdk/Sources/MixerUI"),
            ("MixerGuest", "sdk/Sources/MixerGuest"),
            ("MixerApple", "sdk/Sources/MixerApple"),
            ("MixerCapabilities", "sdk/Sources/MixerCapabilities"),
            ("MixerUpdates", "updates/Sources/MixerUpdates"),
            ("MixerRuntimeIdentity", "runtime-identity/Sources/MixerRuntimeIdentity"),
            ("MixerExperimentalCapabilityRuntime", "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime"),
        ]
        for name, folder in modules:
            files = sorted((source / folder).rglob("*.swift"))
            extra = ["-DCRYPTO_IN_SWIFTPM", "-enable-experimental-feature", "Lifetimes", "-enable-experimental-feature", "SourceWarningControl",
                     "-enable-experimental-feature", "CheckImplementationOnly"] if name == "Crypto" else []
            run("compile-" + name, ["xcrun", "swiftc", *flags, *extra, "-whole-module-optimization", "-emit-object", "-emit-module",
                "-module-name", name, "-emit-module-path", products / (name + ".swiftmodule"), *files, "-o", products / (name + ".o")])
        objects = [products / (name + ".o") for name, _ in ctargets + modules]
        activation = sorted((source / "capability-activation/Sources/MixerCapabilityActivation").glob("*.swift"))
        run("link-current-runtime", ["xcrun", "swiftc", *flags, "-emit-library", "-emit-module", "-module-name", "MixerCapabilityActivation",
            "-emit-module-path", products / "MixerCapabilityActivation.swiftmodule", *activation, *objects,
            source / "native/lib/libmixer_vm_capability_experimental.a", "-Xlinker", "-install_name", "-Xlinker", "@rpath/" + dylib.name, "-o", dylib])
        run("codesign-runtime", ["codesign", "--force", "--sign", "-", dylib])
        run("verify-runtime-signature", ["codesign", "--verify", "--strict", "--verbose=4", dylib])
        symbols = run("runtime-exported-symbols", ["nm", "-gU", dylib])
        for name in ["_mixer_vm_capability_session_create_v1", "_mixer_vm_capability_guest_ui_validate_v1"]:
            assert sum(line.split()[-1:] == [name] for line in symbols.splitlines()) == 1, name
        for folder in ["MacOS", "Frameworks", "Resources/Fixtures"]:
            (app / "Contents" / folder).mkdir(parents=True, exist_ok=True)
        library_copy = app / "Contents/Frameworks" / dylib.name
        shutil.copyfile(dylib, library_copy)
        fixtures = source / "capability-activation/Tests/MixerCapabilityActivationTests/Fixtures"
        for path in sorted(fixtures.glob("*.json")):
            shutil.copyfile(path, app / "Contents/Resources/Fixtures" / path.name)
        plist = {"CFBundleIdentifier": "dev.mixer.signed-guest-ui-teardown-verification", "CFBundleName": "Mixer Signed Guest UI Teardown",
                 "CFBundleExecutable": binary.name, "CFBundlePackageType": "APPL", "NSPrincipalClass": "NSApplication",
                 "LSMinimumSystemVersion": "14.0", "MixerHarnessEvidenceDirectory": str(HERE)}
        (app / "Contents/Info.plist").write_bytes(plistlib.dumps(plist, sort_keys=True))
        harness = sorted((source / "harness").glob("*.swift")) + [
            source / "capability-activation/Tests/MixerCapabilityActivationTests/GuestUISignedFixture.swift",
            source / "capability-activation/Tests/MixerCapabilityActivationTests/GuestUISignedProgram.swift"]
        run("link-public-window-harness", ["xcrun", "swiftc", *flags, "-module-name", "MixerSignedGuestUIWindowHarness",
            "-L", products, "-lMixerGuestUITeardownRuntime", "-Xlinker", "-rpath", "-Xlinker", "@executable_path/../Frameworks",
            *harness, "-o", binary])
        run("runtime-linked-libraries", ["otool", "-L", dylib])
        run("harness-linked-libraries", ["otool", "-L", binary])
        run("codesign-app", ["codesign", "--force", "--sign", "-", app])
        run("verify-app-signature", ["codesign", "--verify", "--deep", "--strict", "--verbose=4", app])
        run("app-signature-details", ["codesign", "--display", "--verbose=4", app])
        assert sha(library_copy) == sha(dylib)
        assert all(sha(source / relative) == expected for relative, expected in manifest.items())
        bundle_manifest = {str(p.relative_to(app)): sha(p) for p in sorted(app.rglob("*")) if p.is_file()}
        (evidence / "app-manifest.json").write_text(json.dumps({"sha256": digest(bundle_manifest), "files": bundle_manifest}, indent=2) + "\n")
        receipt.update(status="Build, independent link, and ad-hoc signature integrity verified; app not launched",
                       finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), app=str(app), executable=str(binary),
                       executable_sha256=sha(binary), dylib=str(dylib), dylib_sha256=sha(dylib), app_tree_sha256=digest(bundle_manifest),
                       artifacts={str(p.relative_to(work)): sha(p) for p in sorted(products.rglob("*")) if p.is_file()},
                       working_tree_changes_after_snapshot=[relative for relative, expected in manifest.items() if sha(Path(origins[relative])) != expected],
                       launch_arguments=["--output", str(HERE / "runs" / args.name / "progress.json"),
                                         "--run-root", str(HERE / "runs" / args.name / "data")])
        assert not Path(receipt["launch_arguments"][3]).exists()
    except BaseException as error:
        receipt["status"] = "failed; app not launched"
        receipt["failure"] = repr(error)
        raise
    finally:
        save()
    print(json.dumps({"app": str(app), "receipt": str(evidence / "build-receipt.json"),
                      "receipt_sha256": sha(evidence / "build-receipt.json"), "launch_arguments": receipt["launch_arguments"]}, indent=2))


if __name__ == "__main__":
    main()
