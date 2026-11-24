#!/usr/bin/env python3
"""Build the UP4 host replay and signed Android APK pair without accessing devices."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LOCAL = ROOT / "verification/local"
MODULE = "native/android/compose"
BRIDGE = "sdk/Sources/MixerAndroid/AndroidComposePresentation.swift"
TARGET = "aarch64-unknown-linux-android28"
HOME = Path.home()


class CustodyUnknown(RuntimeError):
    pass


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class Build:
    def __init__(self, work, mode):
        self.work = work
        self.payload = work / "payload"
        self.tmp = self.payload / "tmp"
        self.cache = self.payload / "cache"
        self.logs = work / "commands"
        for directory in (self.tmp, self.cache, self.logs):
            directory.mkdir(parents=True)

        self.swift = Path(os.environ.get("MIXER_SWIFT", HOME /
            "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"))
        self.sdks = Path(os.environ.get("MIXER_SWIFT_SDKS", HOME / ".swiftpm/swift-sdks"))
        self.artifact = self.sdks / "swift-6.3.3-RELEASE_android.artifactbundle/swift-android"
        self.ndk = self.artifact / "android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64"
        self.jdk = Path(os.environ.get("MIXER_JDK",
            "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home"))
        self.gradle_seed = Path(os.environ.get("MIXER_GRADLE_SEED", HOME / ".gradle"))
        self.installed_sdk = Path(os.environ.get("ANDROID_HOME", "/opt/homebrew/share/android-commandlinetools"))
        self.env = dict(os.environ, TMPDIR=str(self.tmp), XDG_CACHE_HOME=str(self.cache),
                        JAVA_HOME=str(self.jdk), PYTHONDONTWRITEBYTECODE="1")
        for name in ("JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS"):
            self.env.pop(name, None)
        self.android_env = dict(self.env)
        self.android_env.setdefault("DEVELOPER_DIR", "/Applications/Xcode_26.6.app/Contents/Developer")
        self.receipt = {
            "mode": mode,
            "scope": "macOS JVM/Swift JNI replay and/or APK build and static verification, no device operations",
            "fixture_sha256": {str(path.relative_to(HERE)): digest(path) for path in sorted(HERE.rglob("*"))
                               if path.is_file() and path.suffix in {".kt", ".swift", ".py", ".gradle", ".c"}},
            "commands": [],
        }
        self.persist()

    def persist(self):
        temp = self.work / "receipt.tmp"
        temp.write_text(json.dumps(self.receipt, indent=2) + "\n")
        temp.replace(self.work / "receipt.json")

    def command(self, label, *argv, timeout=90, cwd=ROOT, env=None, gradle_daemon_dir=None):
        stdout = self.logs / f"{label}.stdout"
        stderr = self.logs / f"{label}.stderr"
        args = list(map(str, argv))
        print(f"+ {label}: {subprocess.list2cmdline(args)}", flush=True)
        record = {"label": label, "argv": args, "cwd": str(cwd), "timeout_seconds": timeout,
                  "stdout": str(stdout), "stderr": str(stderr)}
        self.receipt["commands"].append(record)
        self.persist()
        try:
            with stdout.open("xb") as out, stderr.open("xb") as err:
                process = subprocess.Popen(args, cwd=cwd, env=env or self.env, stdin=subprocess.DEVNULL,
                                           stdout=out, stderr=err, start_new_session=True)
                record.update(pid=process.pid, pgid=process.pid)
                self.persist()
                record["exit"] = process.wait(timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise CustodyUnknown(f"{label}: {error}") from error
        record.update(direct_child_reaped=True, parent_output_fds_closed=True)
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            record["owned_group_termination"] = "ESRCH"
        except OSError as error:
            raise CustodyUnknown(f"{label}: {error}") from error
        else:
            raise CustodyUnknown(f"{label}: owned group still observable after direct child exit")
        if gradle_daemon_dir is not None:
            self.observe_gradle_daemon(gradle_daemon_dir, record, stdout)
        self.persist()
        if record["exit"]:
            tail = "\n".join((stderr.read_text(errors="replace") + "\n" +
                              stdout.read_text(errors="replace")).splitlines()[-45:])
            raise RuntimeError(f"{label} exited {record['exit']}\n{tail}")
        return stdout.read_text(errors="replace")

    def observe_gradle_daemon(self, directory, record, stdout):
        # Gradle 9.8.1 starts a separate session for its single-use daemon.
        logs = list(directory.glob("daemon-*.out.log"))
        if not logs and "single-use Daemon process will be forked" not in stdout.read_text():
            return
        if len(logs) != 1:
            raise CustodyUnknown(f"Expected one daemon identity in {directory}")
        daemon = int(logs[0].name.removeprefix("daemon-").removesuffix(".out.log"))
        query = ["/bin/ps", "-g", str(daemon), "-o", "pid=,pgid="]
        termination = {"pid": daemon, "pgid": daemon, "log_identity": logs[0].name, "query": query}
        record["gradle_single_use_daemon"] = termination
        self.persist()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                observed = subprocess.run(query, env=self.env, capture_output=True, timeout=2, text=True)
            except (OSError, subprocess.TimeoutExpired) as error:
                raise CustodyUnknown(f"Gradle daemon {daemon}: {error}") from error
            if observed.returncode == 1 and not observed.stdout and not observed.stderr:
                termination["group_absence"] = "ps returned 1 with no matching process rows"
                return
            if observed.returncode != 0 or not observed.stdout or observed.stderr:
                raise CustodyUnknown(f"Unexpected ps observation of Gradle daemon {daemon}: {observed}")
            time.sleep(0.1)
        raise CustodyUnknown(f"Gradle daemon group {daemon} still observable")

    def unpack(self, name, pin, directory, *paths):
        archive = self.payload / f"{name}.tar"
        self.command(f"archive-{name}", "git", "archive", "-o", archive, pin, *paths)
        with tarfile.open(archive) as entries:
            entries.extractall(directory, filter="data")
        archive.unlink()

    def prepare(self):
        revision = self.command("source-revision", "git", "rev-parse", "--verify", "HEAD^{commit}").strip()
        paths = ("sdk/Sources/MixerCore", "sdk/Sources/MixerUI", BRIDGE, MODULE)
        objects = self.command("source-objects", "git", "rev-parse",
                               *(f"{revision}:{path}" for path in paths)).splitlines()
        self.receipt.update(source_revision=revision, source_objects=dict(zip(paths, objects, strict=True)))
        self.source = self.payload / "source"
        self.source.mkdir()
        self.unpack("join-source", revision, self.source, *paths)
        self.module = self.source / MODULE
        self.jni = HERE / "transport/editor_jni.c"
        self.receipt["jni_sha256"] = digest(self.jni)
        if self.receipt["mode"] != "host":
            self.command("swift-version", self.swift, "--version")
        self.command("java-version", self.jdk / "bin/java", "-version")
        self.persist()

    def host(self):
        build = self.payload / "host"
        build.mkdir()
        sources = self.source / "sdk/Sources"
        xcrun = ("/usr/bin/xcrun", "--sdk", "macosx")
        self.command("host-swift-version", *xcrun, "swiftc", "--version")
        self.command("host-clang-version", *xcrun, "clang", "--version")
        swift = [*xcrun, "swiftc", "-swift-version", "6", "-package-name", "Mixer",
                 "-module-cache-path", self.cache / "host-clang", "-I", build]
        for name in ("MixerCore", "MixerUI", "MixerAndroid"):
            self.command(f"host-{name}", *swift, "-emit-module", "-emit-module-path",
                build / f"{name}.swiftmodule", "-emit-library", "-static", "-module-name", name,
                *sorted((sources / name).glob("*.swift")), "-o", build / f"lib{name}.a")
        self.command("host-jni", *xcrun, "clang", "-I", self.jdk / "include",
            "-I", self.jdk / "include/darwin", "-c", self.jni, "-o", build / "editor_jni.o")
        library = build / "libMixerUP4Join.dylib"
        self.command("host-link", *swift, "-emit-library", "-module-name", "MixerUP4Join", "-L", build,
            HERE / "Join.swift", build / "editor_jni.o", "-lMixerAndroid", "-lMixerUI", "-lMixerCore", "-o", library)

        kotlin = self.module / "src/main/kotlin/dev/mixer/compose"
        source = (kotlin / "ComposeDocumentHost.kt").read_text()
        interface = source.split("public interface ComposeSwiftBridge {\n", 1)[1].split("\n}\n", 1)[0]
        bridge = build / "ComposeSwiftBridge.kt"
        bridge.write_text("package dev.mixer.compose\n\npublic interface ComposeSwiftBridge {\n" + interface + "\n}\n")

        def jar(group, artifact, version):
            root = self.gradle_seed / "caches/modules-2/files-2.1"
            path, = (root / group / artifact / version).glob(f"*/{artifact}-{version}.jar")
            self.receipt.setdefault("host_jars_sha256", {})[path.name] = digest(path)
            return str(path)

        stdlib = jar("org.jetbrains.kotlin", "kotlin-stdlib", "2.3.0")
        json_library = jar("org.json", "json", "20251224")
        compiler = [stdlib] + [jar("org.jetbrains.kotlin", name, "2.3.0") for name in
                               ("kotlin-compiler-embeddable", "kotlin-script-runtime", "kotlin-daemon-embeddable")]
        compiler += [jar("org.jetbrains.kotlin", "kotlin-reflect", "1.6.10"),
                     jar("org.jetbrains.kotlinx", "kotlinx-coroutines-core-jvm", "1.8.0"),
                     jar("org.jetbrains", "annotations", "13.0")]
        java = self.jdk / "bin/java"
        compiler_command = (java, f"-Djava.io.tmpdir={self.tmp}", "-cp", os.pathsep.join(compiler),
                            "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler")
        self.command("kotlin-version", *compiler_command, "-version")
        runtime = os.pathsep.join((stdlib, json_library))
        classes = build / "classes"
        self.command("kotlin-host", *compiler_command, "-no-stdlib", "-no-reflect", "-classpath", runtime,
            "-d", classes, bridge, *(kotlin / name for name in ("FrameAuthority.kt", "Document.kt", "DocumentReader.kt")),
            *(HERE / name for name in ("SwiftSession.kt", "SDKEvent.kt", "Replay.kt")))
        output = self.command("jvm-swift-replay", java, f"-Djava.io.tmpdir={self.tmp}", "-Xcheck:jni",
            "--enable-native-access=ALL-UNNAMED", "-cp", f"{classes}{os.pathsep}{runtime}",
            "dev.mixer.compose.ReplayKt", library)
        print(output, end="")
        passes = [line for line in output.splitlines() if line.startswith("PASS ")]
        require(len(passes) == 5, "Expected five JVM / Swift replay observations")
        self.receipt["host_replay"] = passes
        self.persist()

    def android(self):
        package = self.source / "sdk"
        shutil.copy2(HERE / "Package.swift", package)
        fixture_swift = package / "Sources/MixerComposeEditor"
        fixture_swift.mkdir()
        shutil.copy2(HERE / "Join.swift", fixture_swift)
        swift_build = self.payload / "android-swift"
        self.command("swift-arm64-api28", self.swift, "build", "--package-path", package,
            "--scratch-path", swift_build, "--cache-path", self.cache / "swift", "--disable-dependency-cache",
            "--disable-index-store", "--jobs", "8", "--swift-sdks-path", self.sdks, "--swift-sdk", TARGET,
            "-Xlinker", "--no-undefined", "--product", "MixerComposeEditor", env=self.android_env, timeout=480)
        engine, = swift_build.glob("*/debug/libMixerComposeEditor.so")
        libs = self.payload / "jni/arm64-v8a"
        libs.mkdir(parents=True)
        self.bundle(engine, libs)

        android = self.payload / "android-sdk"
        (android / "platforms").mkdir(parents=True)
        (android / "build-tools").mkdir()
        platform = self.installed_sdk / "platforms/android-37.1"
        tools = self.installed_sdk / "build-tools/37.0.0"
        require("Pkg.Revision=1" in (platform / "source.properties").read_text().splitlines(),
                "Expected Android SDK Platform 37.1 revision 1")
        (android / "platforms" / platform.name).symlink_to(platform)
        (android / "build-tools" / tools.name).symlink_to(tools)
        shutil.copytree(self.installed_sdk / "licenses", android / "licenses")
        work = self.payload / "gradle"
        seed = work / "gradle-home/caches"
        seed.mkdir(parents=True)
        self.command("copy-gradle-dependencies", "/bin/cp", "-cR",
                     self.gradle_seed / "caches/modules-2", seed, timeout=120)
        env = dict(self.env, ANDROID_HOME=str(android), ANDROID_SDK_ROOT=str(android),
                   MIXER_UP4_JNI_LIBS=str(libs.parent))
        self.install_overlay()
        gradle = env.get("MIXER_GRADLE", "gradle")
        self.command("gradle-version", gradle, "--version", env=dict(env, GRADLE_USER_HOME=str(work / "gradle-home")))
        self.command("assemble-signed-apks", "/bin/sh", self.module / "build.sh", work, env=env, timeout=600,
                     gradle_daemon_dir=work / "gradle-home/daemon/9.8.1")
        app, = (work / "build/outputs/apk/debug").glob("*.apk")
        test, = (work / "build/outputs/apk/androidTest/debug").glob("*.apk")
        self.verify_apks(app, test, libs, tools, seed)

    def install_overlay(self):
        def install(source, target, name):
            shutil.copy2(source, self.module / f"src/{target}/kotlin/dev/mixer/compose" / name)

        install(HERE / "SwiftSession.kt", "debug", "SwiftSession.kt")
        install(HERE / "SDKEvent.kt", "androidTest", "SDKEvent.kt")
        install(HERE / "android/debug/RuntimeActivity.kt", "debug", "RuntimeActivity.kt")
        install(HERE / "android/androidTest/RuntimeSmoke.kt", "androidTest", "RuntimeSmoke.kt")
        shutil.copy2(HERE / "android/link.gradle", self.module / "up4-runtime-fixture.gradle")
        with (self.module / "build.gradle").open("a") as output:
            output.write("\napply from: 'up4-runtime-fixture.gradle'\n")
        manifest = self.module / "src/debug/AndroidManifest.xml"
        text = manifest.read_text()
        original = 'android:name="dev.mixer.compose.SmokeActivity"'
        require(text.count(original) == 1, "Debug manifest changed")
        addition = ('        <activity android:name="dev.mixer.compose.RuntimeActivity" android:exported="false"\n'
                    '            android:hardwareAccelerated="true" android:windowSoftInputMode="adjustResize" />\n')
        manifest.write_text(text.replace("    </application>", addition + "    </application>"))

    def bundle(self, engine, libs):
        llvm = self.ndk / "bin"
        jni = libs / "libmixer_compose_editor_jni.so"
        self.command("ndk-version", llvm / "aarch64-linux-android28-clang", "--version")
        self.command("link-unchanged-s5-jni", llvm / "aarch64-linux-android28-clang", "-shared", "-O2",
            "-Wall", "-Wextra", "-Werror", self.jni, "-L", engine.parent, "-lMixerComposeEditor",
            "-Wl,--no-undefined,-z,max-page-size=16384", "-o", jni)
        shutil.copy2(engine, libs)
        system = {"libc.so", "libdl.so", "libm.so", "liblog.so", "libandroid.so", "libz.so"}
        sysroot = self.ndk / "sysroot/usr/lib/aarch64-linux-android"
        runtime = self.artifact / "swift-resources/usr/lib/swift-aarch64/android"
        pending = [jni, libs / engine.name]
        inventory = {}
        while pending:
            binary = pending.pop()
            meta = self.command(f"elf-{binary.name}", llvm / "llvm-readelf", "-h", "-d", "-n", binary)
            require(re.search(r"Machine:\s+AArch64\b", meta), f"{binary.name} is not AArch64")
            require(re.search(r"Class:\s+ELF64\b", meta), f"{binary.name} is not ELF64")
            needed = re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", meta)
            inventory[binary.name] = {"sha256": digest(binary), "needed": needed}
            if binary.name in {jni.name, engine.name}:
                require(re.search(r"NT_ANDROID_TYPE_IDENT\s+description data: 1c 00 00 00\b", meta),
                        f"{binary.name} lacks the API 28 Android ELF note")
            for name in needed:
                if name in system:
                    require((sysroot / "28" / name).is_file(), f"No public NDK API 28 stub for {name}")
                elif not (libs / name).is_file():
                    candidates = (runtime / name, sysroot / name)
                    source = next((path for path in candidates if path.is_file()), None)
                    require(source is not None, f"{binary.name} needs missing {name}")
                    shutil.copy2(source, libs)
                    pending.append(libs / name)
        self.receipt["native_libraries"] = inventory
        for binary, symbols in (
            (jni, ["Java_dev_mixer_compose_SwiftSession_" + name + "Native" for name in ("open", "call", "close")]),
            (libs / engine.name, [f"mixer_compose_editor_{name}_v1" for name in ("open", "call", "close")]),
        ):
            output = self.command(f"exports-{binary.name}", llvm / "llvm-nm", "-D", "--defined-only", binary)
            exports = {line.split()[-1] for line in output.splitlines() if line.strip()}
            require(set(symbols) <= exports, f"Missing S5 exports in {binary.name}")

    def verify_apks(self, app, test, libs, tools, seed):
        graphics = "libandroidx.graphics.path.so"
        coordinate = seed / "modules-2/files-2.1/androidx.graphics/graphics-path/1.1.0"
        aar, = coordinate.glob("*/graphics-path-1.1.0.aar")
        with zipfile.ZipFile(aar) as archive:
            native = archive.read(f"jni/arm64-v8a/{graphics}")
        graphics_lib = self.payload / graphics
        graphics_lib.write_bytes(native)
        llvm = self.ndk / "bin/llvm-readelf"
        metadata = self.command(f"elf-{graphics}", llvm, "-h", "-d", "-n", graphics_lib)
        needed = re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", metadata)
        require(re.search(r"Machine:\s+AArch64\b", metadata), f"{graphics} is not AArch64")
        for name in needed:
            api28 = self.ndk / "sysroot/usr/lib/aarch64-linux-android/28" / name
            require((libs / name).is_file() or api28.is_file(), f"{graphics} needs missing {name}")
        self.receipt["native_libraries"][graphics] = {"sha256": digest(graphics_lib),
            "aar_sha256": digest(aar), "needed": needed}
        self.receipt["apks"] = {}
        certificates = set()
        artifacts = self.work / "signed"
        artifacts.mkdir()
        for label, path, package in (("app", app, "dev.mixer.compose.up4"),
                                     ("test", test, "dev.mixer.compose.up4.test")):
            with zipfile.ZipFile(path) as apk:
                require(apk.testzip() is None, f"Corrupt {label} APK entry")
                actual = {name: hashlib.sha256(apk.read(name)).hexdigest() for name in apk.namelist()
                          if name.startswith("lib/") and name.endswith(".so")}
            expected = {f"lib/arm64-v8a/{lib}": entry["sha256"]
                        for lib, entry in self.receipt["native_libraries"].items()} if label == "app" else {}
            require(actual == expected, f"Unexpected {label} native library contents: {actual}")
            metadata = self.command(f"badging-{label}", tools / "aapt2", "dump", "badging", path)
            require(f"package: name='{package}'" in metadata and "minSdkVersion:'28'" in metadata,
                    f"Unexpected {label} APK package or API floor")
            if label == "test":
                manifest = self.command("test-runner", tools / "aapt2", "dump", "xmltree",
                                        "--file", "AndroidManifest.xml", path)
                require("dev.mixer.compose.RuntimeSmoke" in manifest and
                        'android:targetPackage(0x01010021)="dev.mixer.compose.up4"' in manifest,
                        "Instrumentation manifest runner or target differs")
            self.command(f"zipalign-{label}", tools / "zipalign", "-c", "-P", "4", "4", path)
            report = self.command(f"signature-{label}", tools / "apksigner", "verify",
                                  "--min-sdk-version", "28", "--verbose", "--print-certs", path)
            matches = re.findall(r"^(?:V2 Signer:|Signer #1) certificate SHA-256 digest: ([a-f0-9]{64})$",
                                 report, re.M)
            require(len(matches) == 1, f"Unexpected {label} signing certificate output")
            certificates.add(matches[0])
            destination = artifacts / path.name
            shutil.copy2(path, destination)
            self.receipt["apks"][label] = {"path": str(destination), "bytes": destination.stat().st_size,
                                           "sha256": digest(destination), "min_sdk": 28, "package": package}
        require(len(certificates) == 1, "App and instrumentation use different signers")
        self.receipt["certificate_sha256"] = certificates.pop()
        self.persist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("--mode", choices=("host", "apk", "both"), default="both")
    args = parser.parse_args()
    work = args.work.resolve()
    if not work.is_relative_to(LOCAL) or work == LOCAL or work.exists():
        parser.error("Choose a new work directory below verification/local")
    build = Build(work, args.mode)
    print(f"Receipt: {work / 'receipt.json'}", flush=True)
    try:
        build.prepare()
        if args.mode != "apk":
            build.host()
        if args.mode != "host":
            build.android()
        build.receipt["result"] = "PASS"
    except CustodyUnknown as error:
        build.receipt.update(result="HOLD", reason=str(error), retained=str(build.payload))
        raise
    except Exception as error:
        build.receipt.update(result="FAIL", reason=str(error))
        raise
    finally:
        build.persist()
        if build.receipt.get("result") in {"PASS", "FAIL"}:
            try:
                shutil.rmtree(build.payload)
            except OSError as error:
                build.receipt.update(disposable_payload_removed=False, cleanup_error=str(error),
                                     retained=str(build.payload))
                raise
            else:
                build.receipt["disposable_payload_removed"] = True
            finally:
                build.persist()


if __name__ == "__main__":
    main()
