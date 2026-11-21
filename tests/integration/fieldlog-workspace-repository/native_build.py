import os
from pathlib import Path


def build_native(commands, arm, platform):
    work = commands.root
    root = work / arm
    label = arm + "-" + platform
    env = os.environ.copy()
    env.update(TMPDIR=str(work / "tmp"), SWIFTCI_USE_LOCAL_DEPS="1",
               SWIFTPM_MODULECACHE_OVERRIDE=str(work / f"{platform}-module-cache"),
               CLANG_MODULE_CACHE_PATH=str(work / f"{platform}-clang-cache"))
    builder = "/usr/bin/swift"
    p = work / label
    args = ["build", "--scratch-path", str(p / "build"), "--cache-path", str(p / "cache"),
            "--config-path", str(p / "config"), "--security-path", str(p / "security"),
            "--disable-dependency-cache", "--disable-prefetching", "--disable-index-store",
            "--jobs", "6", "--product", "AppAndroid", "-v"]
    if platform == "android":
        env["DEVELOPER_DIR"] = "/Applications/Xcode_26.6.app/Contents/Developer"
        builder = str(Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift")
        package = root / "App/Platforms/Android"
        args.extend(["--swift-sdks-path", str(Path.home() / ".swiftpm/swift-sdks"),
                     "--swift-sdk", "aarch64-unknown-linux-android28", "-c", "release",
                     "-Xlinker", "-z", "-Xlinker", "max-page-size=16384"])
    elif platform == "standalone-export":
        env["FIELDLOG_MIXER_SDK"] = str(work / "mixer/sdk")
        package = root / "fieldlog/Integrations/GeneratedReport"
        args.extend(["--build-system", "native"])
    elif platform == "iphoneos":
        lib = work / "ios-cargo/aarch64-apple-ios/release"
        assert (lib / "libmixer_vm_capability_experimental.a").is_file()
        builder = "/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild"
        args = ["-project", str(root / "fieldlog/ios/FieldLog.xcodeproj"),
                "-scheme", "FieldLog", "-configuration", "Debug", "-sdk", "iphoneos",
                "-destination", "generic/platform=iOS", "-derivedDataPath", str(p / "derived"),
                "-clonedSourcePackagesDirPath", str(p / "packages"), "-packageCachePath", str(p / "cache"),
                "-resultBundlePath", str(p / "build.xcresult"), "-disableAutomaticPackageResolution",
                "-skipPackageUpdates", "-disablePackageRepositoryCache", "-jobs", "6",
                "CODE_SIGNING_ALLOWED=NO", "ARCHS=arm64", "ONLY_ACTIVE_ARCH=NO",
                "ENABLE_DEBUG_DYLIB=NO", f"HEADER_SEARCH_PATHS=$(inherited) {work}/mixer/vm/include",
                f"LIBRARY_SEARCH_PATHS={lib}", "LD_GENERATE_MAP_FILE=YES",
                "COMPILER_INDEX_STORE_ENABLE=NO", "build"]
    else:
        raise ValueError(platform)
    if platform != "iphoneos":
        args.extend(["--package-path", str(package)])
    else:
        p.mkdir()
    commands.run(label, root, 175, [builder, *args], env)
