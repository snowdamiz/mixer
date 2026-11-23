#!/usr/bin/env python3
"""Compile and verify the host-only S1 naming fixture."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIXTURE = HERE / "Fixture"
ANDROID = "aarch64-unknown-linux-android28"
WASI = "wasm32-unknown-wasip1"
IOS = "arm64-apple-ios17.0"
ALIAS = ("-module-alias", "SwiftUI=MixerSwiftUI")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class Replay:
    def __init__(self, directory):
        self.directory = directory
        self.work = directory / "work"
        self.work.mkdir()
        tmp = self.work / "tmp"
        tmp.mkdir()
        self.env = os.environ.copy()
        for key in ("TOOLCHAINS", "SDKROOT", "SWIFT_EXEC", "SWIFT_DRIVER_SWIFT_FRONTEND_EXEC",
                    "S1_APPLE_ALIAS"):
            self.env.pop(key, None)
        self.env.update({
            "TMPDIR": str(tmp),
            "CLANG_MODULE_CACHE_PATH": str(self.work / "clang-cache"),
            "SWIFTPM_MODULECACHE_OVERRIDE": str(self.work / "manifest-modules"),
            "XDG_CACHE_HOME": str(self.work / "xdg-cache"),
        })
        self.hold = False

    def run(self, name, *args, env=None, limit=90):
        argv = list(map(str, args))
        stdout = self.directory / f"{name}.stdout"
        stderr = self.directory / f"{name}.stderr"
        command = {"name": name, "argv": argv, "deadlineSeconds": limit}
        active_env = self.env | (env or {})
        command["environment"] = {key: active_env[key] for key in
                                  ("DEVELOPER_DIR", "S1_APPLE_ALIAS", "TMPDIR") if key in active_env}
        with stdout.open("wb") as out, stderr.open("wb") as err:
            try:
                child = subprocess.Popen(argv, cwd=ROOT, env=active_env, start_new_session=True,
                                         stdin=subprocess.DEVNULL, stdout=out, stderr=err)
            except (OSError, KeyboardInterrupt) as exc:
                self.record_hold(command, str(exc))
                raise
            command["pid"] = child.pid
            try:
                command["exit"] = child.wait(timeout=limit)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                self.record_hold(command, str(exc))
                # Avoid automatic child polling after a deadline with unverified custody.
                os._exit(74)
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                command["groupAbsent"] = True
            except OSError as exc:
                self.record_hold(command, str(exc))
            else:
                self.record_hold(command, "Process group still present after direct child reap")
        self.record(command)
        require(not self.hold, f"Unknown custody for {name}; see HOLD.json")
        return command["exit"], stdout.read_text(errors="replace"), stderr.read_text(errors="replace")

    def record(self, command):
        with (self.directory / "commands.jsonl").open("a") as receipt:
            receipt.write(json.dumps(command) + "\n")

    def record_hold(self, command, message):
        self.hold = True
        (self.directory / "HOLD.json").write_text(json.dumps(command | {"reason": message}, indent=2))

    def checked(self, name, *args, **kwargs):
        status, stdout, stderr = self.run(name, *args, **kwargs)
        require(status == 0, f"{name} exited {status}\n{stderr[-1800:]}\n{stdout[-900:]}")
        return stdout


def named_graph(path):
    modules = json.loads(path.read_text())["modules"]
    kinds = {"swift", "swiftPrebuiltExternal", "swiftPlaceholder"}
    result = {}
    for key, details in zip(modules[::2], modules[1::2], strict=True):
        if not (key.keys() & kinds):
            continue
        name = next(iter(key.values()))
        result[name] = {
            "modulePath": details["modulePath"],
            "interfacePath": details.get("details", {}).get("swift", {}).get("moduleInterfacePath"),
            "imports": sorted(next(iter(entry.values())) for entry in details.get("directDependencies", [])),
        }
    return result


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_inventory(source):
    return {str(path.relative_to(source)): sha256(path)
            for path in sorted(source.rglob("*.swift"))}


def build(replay, label, source, platform, swiftc, flags, env, inspector, linker=()):
    output = replay.work / label
    output.mkdir()
    common = (*flags, "-swift-version", "6", "-module-cache-path", output / "ModuleCache",
              "-I", output)
    apple = platform == "ios"
    module = "MixerSwiftUI" if apple else "SwiftUI"
    engine = "Engine/Sources"
    support_source = source / engine / "TitleSupport/TitleSupport.swift"
    engine_source = source / engine / "SwiftUI/Text.swift"
    feature_source = source / "Sources/SharedFeature/Title.swift"
    shell = "AppleShell" if apple else "PortableApp"
    shell_source = source / ("Sources/AppleShell/AppleShell.swift" if apple else "Sources/PortableApp/main.swift")
    alias = ALIAS if apple else ()

    objects = []
    for name, file, options in (
        ("TitleSupport", support_source, ()),
        (module, engine_source, alias),
        ("SharedFeature", feature_source, alias),
    ):
        obj = output / f"{name}.o"
        replay.checked(f"{label}-emit-{name}", swiftc, *common, *options, "-parse-as-library",
                       "-emit-module", "-emit-module-path", output / f"{name}.swiftmodule",
                       "-c", "-module-name", name, file, "-o", obj, env=env)
        objects.append(obj)

    scans = {}
    for name, file, options, expected in (
        (module, engine_source, alias, "TitleSupport"),
        ("SharedFeature", feature_source, alias, module),
        (shell, shell_source, (), "SharedFeature"),
    ):
        scan = output / f"{name}.scan.json"
        replay.checked(f"{label}-scan-{name}", swiftc, *common, *options, "-scan-dependencies",
                       "-module-name", name, file, "-o", scan, env=env)
        graph = named_graph(scan)
        require(expected in graph[name]["imports"], f"{label}: {name} did not resolve {expected}")
        dependency_path = graph[expected]["modulePath"]
        require(str(output / f"{expected}.swiftmodule") == dependency_path,
                f"{label}: {name} resolved {expected} from {dependency_path}")
        scans[name] = {"imports": graph[name]["imports"], "expectedDependencyPath": dependency_path}
        if name == "SharedFeature":
            if apple:
                require("SwiftUI" not in graph[name]["imports"], f"{label}: alias also imported Apple SwiftUI")
        if name == "AppleShell":
            require("SwiftUI" in graph[name]["imports"], f"{label}: shell did not resolve Apple SwiftUI")
            dep = graph["SwiftUI"]
            origin = dep["interfacePath"] or dep["modulePath"]
            require("SwiftUI.framework/" in origin, f"{label}: unexpected Apple SwiftUI origin {dep}")
            scans[name]["appleSwiftUIPath"] = origin

    binary = output / (f"{shell}.wasm" if platform == "wasi" else shell)
    main_flags = ("-parse-as-library",) if apple else ()
    replay.checked(f"{label}-link", swiftc, *common, *linker, *main_flags, "-module-name", shell,
                   shell_source, *objects, "-o", binary, env=env)
    observation = inspector(label, binary)
    return {"artifact": binary.name, "size": binary.stat().st_size, "sha256": sha256(binary),
            "scans": scans, "observation": observation}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apple-xcode", type=Path, default=Path("/Applications/Xcode.app"))
    parser.add_argument("--cross-xcode", type=Path, default=Path("/Applications/Xcode_26.6.app"))
    parser.add_argument("--swift-toolchains", type=Path, default=Path.home() / "Library/Developer/Toolchains")
    parser.add_argument("--swift-sdks", type=Path, default=Path.home() / "Library/org.swift.swiftpm/swift-sdks")
    parser.add_argument("--mixer", type=Path, help="Use a CLI already built from this source revision")
    args = parser.parse_args()

    local = ROOT / "verification/local"
    local.mkdir(parents=True, exist_ok=True)
    receipt = Path(tempfile.mkdtemp(prefix="swiftui-module-naming-", dir=local))
    print(receipt, flush=True)
    replay = Replay(receipt)
    try:
        execute(replay, args)
    finally:
        if not replay.hold:
            shutil.rmtree(replay.work)


def execute(replay, args):
    run = replay.checked
    head = run("source-revision", "/usr/bin/git", "rev-parse", "HEAD").strip()
    pin = json.loads((ROOT / "release/toolchain-candidate.json").read_text())
    swift_pin = pin["swift"]
    cross_bin = args.swift_toolchains / f"swift-{swift_pin['version']}-RELEASE.xctoolchain/usr/bin"
    apple_dev = args.apple_xcode / "Contents/Developer"
    apple_bin = apple_dev / "Toolchains/XcodeDefault.xctoolchain/usr/bin"
    apple_env = {"DEVELOPER_DIR": str(apple_dev), "PATH": f"{apple_bin}:/usr/bin:/bin:/usr/sbin:/sbin"}
    cross_env = {"DEVELOPER_DIR": str(args.cross_xcode / "Contents/Developer")}
    cross_version = run("cross-swift-version", cross_bin / "swiftc", "--version", env=cross_env)
    require(f"Swift version {swift_pin['version']} (swift-{swift_pin['version']}-RELEASE)" in cross_version,
            "Swift cross-compiler does not match release pin")
    mac_sdk = run("cross-host-sdk", "/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-version", env=cross_env)
    require(mac_sdk.strip() == pin["crossCompilerHostSDK"]["macOSSDK"], "Wrong cross-compiler host SDK")
    xcode_version = run("apple-xcode-version", "/usr/bin/xcodebuild", "-version", env=apple_env)
    apple_swift = run("apple-swift-version", apple_bin / "swiftc", "--version", env=apple_env)
    ios_sdk = run("ios-sdk", "/usr/bin/xcrun", "--sdk", "iphoneos", "--show-sdk-path", env=apple_env).strip()
    node_version = run("node-version", "node", "--version").strip()

    android = args.swift_sdks / f"{swift_pin['androidSDK']}.artifactbundle/swift-android"
    wasi = args.swift_sdks / f"{swift_pin['wasmSDK']}.artifactbundle/{swift_pin['wasmSDK']}/{WASI}"
    android_metadata = android / "swift-sdk.json"
    android_toolset = android / "swift-toolset.json"
    android_pins = json.loads((ROOT / "tests/integration/fieldlog-task-calculation/android-packaging/toolchain-pins.json").read_text())
    for metadata in (android_metadata, android_toolset):
        require(sha256(metadata) == android_pins["swiftAndroidSDK"][f"swift-android/{metadata.name}"],
                f"Android metadata differs from repository pin: {metadata}")
    ndk = android / "android-ndk-r27d"
    require("Pkg.Revision = 27.3.13750724" in (ndk / "source.properties").read_text(), "Wrong Android NDK")
    ndk_tools = ndk / "toolchains/llvm/prebuilt/darwin-x86_64/bin"
    wasi_metadata = wasi / "swift-sdk.json"
    wasi_toolset = wasi / "toolset.json"
    wasi_target = json.loads(wasi_metadata.read_text())["targetTriples"][WASI]
    wasi_clang = wasi / wasi_target["swiftResourcesPath"] / "clang"
    wasi_tools = wasi / json.loads(wasi_toolset.read_text())["rootPath"]

    def flags(base, metadata, triple):
        target = json.loads(metadata.read_text())["targetTriples"][triple]
        return ("-target", triple, "-sdk", base / target["sdkRootPath"],
                "-resource-dir", base / target["swiftResourcesPath"])

    def verify_android(label, binary):
        elf = run(f"{label}-readelf", ndk_tools / "llvm-readelf", "-h", "-sW", binary)
        require("AArch64" in elf and "ELF64" in elf and "$s7SwiftUI4Text" in elf,
                "Android ELF is missing the linked SwiftUI.Text symbol")
        return "ELF64 AArch64 with SwiftUI.Text symbols"

    def verify_wasi(label, binary):
        output = run(f"{label}-execute", "node", "--no-warnings", HERE / "wasi.mjs", binary)
        require(output.strip() == "Mixer: S1", f"Unexpected WASI output {output!r}")
        return output.strip()

    def verify_ios(label, binary):
        libs = run(f"{label}-otool", "/usr/bin/xcrun", "otool", "-L", binary, env=apple_env)
        require("SwiftUI.framework/SwiftUI" in libs, "Linked iOS shell is missing Apple SwiftUI")
        symbols = run(f"{label}-nm", apple_bin / "nm", binary, env=apple_env)
        require("$s12MixerSwiftUI4Text" in symbols and "$s7SwiftUI4Text" in symbols,
                "Linked iOS shell did not reference both SwiftUI.Text types")
        version = run(f"{label}-vtool", apple_bin / "vtool", "-show-build", binary, env=apple_env)
        require("platform IOS" in version and "minos 17.0" in version, "Unexpected iOS deployment target")
        return "iOS minos 17.0, links Apple SwiftUI and contains MixerSwiftUI.Text"

    if args.mixer:
        mixer = args.mixer.resolve(strict=True)
    else:
        cli = replay.work / "cli-build"
        swift_build = (apple_bin / "swift", "build", "--package-path", ROOT / "cli",
                       "--scratch-path", cli, "--cache-path", replay.work / "spm-cache",
                       "--config-path", replay.work / "spm-config", "--security-path", replay.work / "spm-security",
                       "--disable-index-store")
        run("mixer-build", *swift_build, "--product", "mixer", env=apple_env, limit=180)
        cli_bin = run("mixer-bin-path", *swift_build, "--show-bin-path", env=apple_env).strip()
        mixer = Path(cli_bin) / "mixer"

    source = replay.work / "source"
    exported = replay.work / "exported"
    run("mixer-create", mixer, "create", "NamingSpike", "--platform", "ios", "--sdk-path",
        ROOT / "sdk", "--directory", source, env=apple_env)
    shutil.copytree(FIXTURE, source / "NamingFixture")
    run("mixer-export", mixer, "export", exported, "--directory", source, env=apple_env)
    sources = source_inventory(FIXTURE)
    require(sources == source_inventory(exported / "NamingFixture"), "Export changed fixture source")

    results = {}
    for location, project in (("source", source), ("exported", exported)):
        fixture = project / "NamingFixture"
        results[location] = {
            "android": build(replay, f"{location}-android", fixture, "android", cross_bin / "swiftc",
                             (*flags(android, android_metadata, ANDROID), "-tools-directory", ndk_tools),
                             cross_env, verify_android, ("-Xclang-linker", "-fuse-ld=lld")),
            "wasi": build(replay, f"{location}-wasi", fixture, "wasi", cross_bin / "swiftc",
                          (*flags(wasi, wasi_metadata, WASI), "-static-stdlib", "-tools-directory", wasi_tools),
                          cross_env, verify_wasi, ("-Xclang-linker", "-resource-dir", "-Xclang-linker", wasi_clang)),
            "ios": build(replay, f"{location}-ios", fixture, "ios", apple_bin / "swiftc",
                         ("-target", IOS, "-sdk", ios_sdk), apple_env, verify_ios),
        }
        if location == "source":
            shutil.rmtree(source)
    report = {
        "head": head, "fixtureSources": sources, "crossSwift": cross_version.strip(),
        "crossMacOSSDK": mac_sdk.strip(), "appleXcode": xcode_version.strip(),
        "appleSwift": apple_swift.strip(), "appleCandidateBuild": pin["apple"]["build"],
        "iosSDK": ios_sdk, "mixerCLIHash": sha256(mixer), "node": node_version,
        "sdkMetadata": {str(p): sha256(p) for p in (android_metadata, android_toolset, wasi_metadata, wasi_toolset)},
        "results": results,
    }
    (replay.directory / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: Android ELF, WASI execution, and linked iOS SwiftUI coexistence in source and Mixer export.")


if __name__ == "__main__":
    main()
