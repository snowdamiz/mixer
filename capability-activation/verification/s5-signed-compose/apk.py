#!/usr/bin/env python3
"""Package the signed S5 Android library and the root-only instrumentation replay."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import sys

from link import HERE, ROOT, digest, guests, run

PATCHES = {
    "prior-hw-os-ime.patch": "fd0a839a5fa9526256214b09f4558e5c3ae9915c44aa7e3052e0d180a1e7ea67",
    "s5-ime-bootstrap.patch": "66523709e1693d63fedd571bbd0674cb131af77e79ee3fc3fe6eff1c9c954a1a",
}


def compose_builder(path):
    spec = importlib.util.spec_from_file_location("pinned_compose_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("android_link", type=Path)
    parser.add_argument("signer", type=Path)
    parser.add_argument("ime_delivery", type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    linked = args.android_link.resolve(strict=True)
    signer = args.signer.resolve(strict=True)
    delivery = args.ime_delivery.resolve(strict=True)
    if not work.is_relative_to(ROOT / "verification/local") or work.exists():
        parser.error("Choose a new directory below verification/local")
    for name in ("tmp", "cache", "android-user", "gradle-home", "jni/arm64-v8a"):
        (work / name).mkdir(parents=True)
    home = Path.home()
    source = linked / "source"
    swift = home / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
    artifact = home / ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android"
    installed = Path(os.environ.get("ANDROID_HOME", "/opt/homebrew/share/android-commandlinetools"))
    jdk = os.environ.get("MIXER_JDK", "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home")
    os.environ.update(TMPDIR=str(work / "tmp"), XDG_CACHE_HOME=str(work / "cache"),
        ANDROID_USER_HOME=str(work / "android-user"), GRADLE_USER_HOME=str(work / "gradle-home"),
        JAVA_HOME=jdk, MIXER_S5_BUILD_DIR=str(work / "apk"), MIXER_S5_JNI_LIBS=str(work / "jni"),
        GIT_CEILING_DIRECTORIES=str(work), PYTHONDONTWRITEBYTECODE="1")
    projection = work / "projection"
    project = projection / "native/android/compose"
    shutil.copytree(source / "native/android/compose", project)
    patches = []
    for name, expected in PATCHES.items():
        patch = delivery / name
        if digest(patch) != expected:
            raise ValueError(f"Unrecognized proven Compose patch: {name}")
        patches.append(patch)
    run("git", "apply", *patches, cwd=projection)
    run("git", "apply", HERE / "compose.patch", cwd=projection)
    native = list((linked / "swift-build").glob("*/debug/libMixerComposeEditor.so"))
    if len(native) != 1:
        raise RuntimeError(f"Expected one linked Android library, found {native}")
    vm = linked / "vm-build/aarch64-linux-android/release/libmixer_vm.a"
    assets = project / "src/main/assets/s5-signed"
    revision = run("git", "rev-parse", "ebbc4735a234d42622b435acd2ddc9ff430c1d20",
                   cwd=ROOT, capture_output=True, text=True).stdout.strip()
    run(signer, source / "capability-activation/Tests/MixerCapabilityActivationTests/Fixtures",
        guests(work, swift), assets, revision, digest(vm), digest(native[0]))

    builder = compose_builder(project / "build.py")
    ndk = artifact / "android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64"
    # FoundationNetworking requires Android's public API 28 zlib. An NDK
    # stub proves an OS library is available and must never enter the APK.
    if not (ndk / "sysroot/usr/lib/aarch64-linux-android/28/libz.so").is_file():
        raise RuntimeError("Expected Android API 28 zlib stub")
    builder.SYSTEM_LIBRARIES.add("libz.so")
    builder.bundle_libraries(
        ndk,
        artifact / "swift-resources/usr/lib/swift-aarch64/android",
        native[0], work / "jni/arm64-v8a",
    )
    android_sdk = builder.prepare_sdk(work, installed)
    os.environ.update(ANDROID_HOME=str(android_sdk), ANDROID_SDK_ROOT=str(android_sdk))
    gradle = os.environ.get("MIXER_GRADLE", "gradle")
    run(gradle, "--version")
    run(gradle, "--no-daemon", "--console=plain", "--project-dir", project,
        "--project-cache-dir", work / "project-cache",
        f"-Pkotlin.project.persistent.dir={work / 'kotlin'}", "assembleDebug", "assembleDebugAndroidTest")
    run("bash", project / "sign-os-ime.sh", work / "apk/outputs/apk", work / "signed")
    shutil.copy2(project / "replay-os-ime.sh", work / "signed")
    apks = sorted((work / "signed").glob("*.apk"))
    if len(apks) != 2:
        raise RuntimeError("Expected a signed app and its instrumentation")
    for apk in apks:
        run("unzip", "-tq", apk)
        print(apk, apk.stat().st_size, digest(apk), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        sys.exit(str(error))
