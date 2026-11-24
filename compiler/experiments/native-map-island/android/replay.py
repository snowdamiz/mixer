#!/usr/bin/env python3
"""Build the private GC3 Android fixture and replay exact signed bytes on the host."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXPERIMENT = HERE.parent.relative_to(ROOT)
EXPORTER = "b69525316a0d5ad28fb69ddc22bb152a8bf8a9df"
# Both revisions have identical map experiment and updates trees.
RETAINED_VECTOR_SOURCE = "c618cb7093c1f4a32ee8540adebc32c7ee47b75f"
TARGET = "aarch64-unknown-linux-android28"
COMPOSE = "1.11.2"
KOTLIN = "2.3.0"
DENIALS = (
    "unknown-island", "missing-grant", "grant-for-other-id", "grant-schema", "node-schema",
    "node-version", "grant-manifest-version", "invalid-coordinate-1", "invalid-coordinate-2",
    "invalid-coordinate-3", "invalid-coordinate-4", "grant-inserted-after-signing",
    "coordinate-edited-after-signing", "unpinned-signer", "wrong-platform",
)


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    with path.open("rb") as data:
        return hashlib.file_digest(data, "sha256").hexdigest()


def canonical_cbor(value):
    """Independent fixture oracle for the exporter manifest's JSON profile."""
    def head(major, size):
        if size < 24:
            return bytes([major * 32 + size])
        for tag, width in enumerate((1, 2, 4, 8), start=24):
            if size < 256 ** width:
                return bytes([major * 32 + tag]) + size.to_bytes(width, "big")
        raise ValueError("CBOR size overflow")

    if isinstance(value, bool):
        return bytes([0xF5 if value else 0xF4])
    if isinstance(value, int) and value >= 0:
        return head(0, value)
    if isinstance(value, str):
        text = value.encode("utf-8")
        return head(3, len(text)) + text
    if isinstance(value, list):
        return head(4, len(value)) + b"".join(map(canonical_cbor, value))
    if isinstance(value, dict):
        entries = sorted((canonical_cbor(key), canonical_cbor(item)) for key, item in value.items())
        return head(5, len(entries)) + b"".join(key + item for key, item in entries)
    raise ValueError("Unexpected value in signed fixture manifest")


def stage_vectors(vectors, package, out, allowed_sources):
    fixture = json.loads(vectors.read_bytes())
    trust = fixture["trustRoot"]
    key = base64.b64decode(trust["public_key"], validate=True)
    scope = dict(organization="mixer", project="fieldlog", app="fieldlog",
                 environment="development", platform="android")
    check(fixture["version"] == 1 and fixture["now"] == 100, "Wrong fixture version or clock")
    check(len(key) == 32 and trust["scope"] == scope and trust["key_id"] == "map-replay"
          and trust["artifact"] and not trust["assignment"] and not trust["revoked"]
          and trust["not_before_unix"] == 0 and trust["not_after_unix"] == 0, "Wrong fixture trust root")
    installed = fixture["installedRuntime"]
    check(installed == dict(scope=scope, runtime=installed["runtime"], protocol=3, guest_abi=2, ui_schema=1,
                            capability_hashes={}, state_version=0, max_payload_bytes=4096,
                            limits=dict(memory_bytes=65536, fuel=1000, startup_milliseconds=1000)),
          "Wrong installed runtime profile")
    root_source = package / "Sources/MapAdmission/InstalledFixtureRoot.swift"
    root_source.write_text("enum InstalledFixtureRoot { static let publicKey: [UInt8] = ["
                           + ", ".join(map(str, key)) + "] }\n")

    steps = fixture["steps"]
    names = [f"cold-{name}" for name in DENIALS] + ["mount", "move"] + [f"warm-{name}" for name in DENIALS]
    check([step["name"] for step in steps] == names, "Expected the full ordered signed journey")
    cases = []
    expectations = [[fixture["islandID"], fixture["schemaSHA256"], installed["runtime"],
                     sha(key), fixture["nodeID"], str(fixture["nodeGeneration"])]]
    for cold, warm in zip(steps[:15], steps[17:]):
        check(cold["artifact"] == warm["artifact"] and cold["refusalCode"] == warm["refusalCode"],
              f"Changed artifact or refusal between cold and warm cases for {cold['name']}")
    signed_source = None
    for step in steps:
        name = step["name"]
        artifact = step["artifact"]
        signed = base64.b64decode(artifact["signedManifest"], validate=True)
        payload = base64.b64decode(artifact["payload"], validate=True)
        cases.append([name, artifact["signedManifest"], artifact["payload"]])
        refusal = step.get("refusalCode", "")
        release_id, artifact_sha = "", ""
        if name in ("mount", "move"):
            manifest = json.loads(signed)["manifest"]
            source = manifest["source_commit"]
            check(source in allowed_sources and signed_source in (None, source),
                  f"{name}: unexpected signed source revision")
            signed_source = source
            check(not refusal and manifest["scope"] == scope
                  and manifest["payload_sha256"] == sha(payload), f"{name}: unexpected accepted manifest")
            release_id, artifact_sha = manifest["release_id"], sha(canonical_cbor(manifest))
        else:
            check(refusal, f"{name}: missing expected refusal")
        expectations.append([name, refusal, step.get("acceptedStep", ""), str(step["applyCount"]),
                             release_id, artifact_sha])

    def write_tsv(name, rows):
        file = out / name
        file.write_text("".join("\t".join(row) + "\n" for row in rows), encoding="utf-8")
        return file

    return write_tsv("signed-cases.tsv", cases), write_tsv("expectations.tsv", expectations), signed_source


class Run:
    def __init__(self, out, scratch, xcode):
        self.out = out
        self.scratch = scratch
        self.env = {**os.environ, "DEVELOPER_DIR": str(xcode), "PYTHONDONTWRITEBYTECODE": "1"}
        self.commands = []

    def __call__(self, name, *args, file=None):
        args = list(map(str, args))
        print(f"{name}: {shlex.join(args)}", flush=True)
        log = self.out / f"{name}.log"
        with log.open("w") as errors:
            errors.write(shlex.join(args) + "\n")
            errors.flush()
            if file is None:
                result = subprocess.run(args, cwd=ROOT, env=self.env, stdout=errors, stderr=subprocess.STDOUT)
            else:
                with file.open("wb") as output:
                    result = subprocess.run(args, cwd=ROOT, env=self.env, stdout=output, stderr=errors)
        self.commands.append(dict(name=name, args=args, exitCode=result.returncode, log=log.name))
        check(result.returncode == 0, f"{name} exited {result.returncode}. See {log}")
        return log.read_text().split("\n", 1)[1]

    def swift_paths(self, name):
        work = self.scratch / name
        tmp = work / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        self.env.update(TMPDIR=str(tmp), CLANG_MODULE_CACHE_PATH=str(work / "modules"),
                        SWIFTPM_MODULECACHE_OVERRIDE=str(work / "modules"))
        return ["--scratch-path", work / "build", "--cache-path", work / "cache",
                "--config-path", work / "config", "--security-path", work / "security",
                "--manifest-cache", "local", "--force-resolved-versions"]


def kotlin_tools(cache):
    def artifact(group, name, version, filename=None):
        candidates = list((cache / group / name / version).glob(f"*/{filename or f'{name}-{version}.jar'}"))
        check(len(candidates) == 1, f"Expected one cached {group}:{name}:{version}")
        path = candidates[0]
        check(hashlib.sha1(path.read_bytes()).hexdigest() == path.parent.name.zfill(40), f"Cache digest mismatch for {path}")
        return path

    def kotlin(name, version=KOTLIN):
        return artifact("org.jetbrains.kotlin", f"kotlin-{name}", version)

    compiler = [kotlin("compiler-embeddable"), kotlin("stdlib"), kotlin("script-runtime"),
                kotlin("reflect", "1.6.10"), kotlin("daemon-embeddable"),
                artifact("org.jetbrains.kotlinx", "kotlinx-coroutines-core-jvm", "1.8.0"),
                artifact("org.jetbrains", "annotations", "13.0")]
    compose = []
    for group, names in (
        ("runtime", ("runtime", "runtime-annotation")),
        ("foundation", ("foundation", "foundation-layout")),
        ("ui", ("ui", "ui-geometry", "ui-graphics", "ui-text", "ui-unit", "ui-util")),
    ):
        compose.extend(artifact(f"androidx.compose.{group}", f"{name}-android", COMPOSE, f"{name}.aar")
                       for name in names)
    return compiler, kotlin("compose-compiler-plugin-embeddable"), compose


def compile_kotlin(run, args, package, cases, expectations, host_libs):
    java = args.jdk / "bin/java"
    compiler, plugin, compose = kotlin_tools(args.cache)
    stdlib = compiler[1]
    def classpath(files):
        return os.pathsep.join(map(str, files))

    command = [java, "--enable-native-access=ALL-UNNAMED", f"-Djava.io.tmpdir={run.env['TMPDIR']}",
               "-cp", classpath(compiler),
               "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler",
               "-no-stdlib", "-no-reflect", "-jvm-target", "17", "-Werror"]
    kotlin = package / "kotlin"
    shared = [kotlin / "Placement.kt", kotlin / "ReplayCases.kt"]
    host_classes = run.scratch / "host-classes.jar"
    run("kotlin-version", *command, "-version")
    run("kotlin-host", *command, "-classpath", stdlib, "-d", host_classes, *shared, kotlin / "HostReplay.kt")
    observed = run("host-replay", java, "--enable-native-access=ALL-UNNAMED", "-Xcheck:jni",
                   f"-Djava.io.tmpdir={run.env['TMPDIR']}",
                   f"-Djava.library.path={host_libs}", "-cp", classpath([host_classes, stdlib]),
                   "dev.mixer.gc3.HostReplayKt", cases, expectations)
    check(observed.splitlines()[-1] == "PASS: 32 signed cases, one surface, 2 size-bound controls",
          "Missing complete JNI host replay")

    android_jar = args.sdk / "platforms/android-37.1/android.jar"
    class_jars = []
    for aar in compose:
        jar = run.scratch / (aar.stem + ".jar")
        with zipfile.ZipFile(aar) as archive:
            jar.write_bytes(archive.read("classes.jar"))
        class_jars.append(jar)
    android_classes = run.scratch / "android-classes.jar"
    run("kotlin-compose", *command, f"-Xplugin={plugin}", "-classpath",
        classpath([stdlib, android_jar, *class_jars]), "-d", android_classes,
        *shared, kotlin / "ComposePlacement.kt", kotlin / "ComposeFixture.kt")
    dex = run.scratch / "dex"
    dex.mkdir()
    d8 = args.sdk / "build-tools/37.0.0/d8"
    dex_classpath = [option for jar in [stdlib, *class_jars] for option in ("--classpath", jar)]
    run("dex-api28", "env", f"JAVA_HOME={args.jdk}", f"JAVA_TOOL_OPTIONS=-Djava.io.tmpdir={run.env['TMPDIR']}",
        d8, "--min-api", "28", "--lib", android_jar, *dex_classpath, "--output", dex, android_classes)
    check((dex / "classes.dex").read_bytes().startswith(b"dex\n"), "Missing API 28 DEX output")
    return android_classes, [*compiler, plugin, *compose, android_jar]


def gather_android_libraries(run, sdk, ndk, libdir):
    readelf = ndk / "bin/llvm-readelf"
    swift_runtime = sdk / "swift-resources/usr/lib/swift-aarch64/android"
    ndk_runtime = ndk / "sysroot/usr/lib/aarch64-linux-android"
    system = {"libc.so", "libdl.so", "libm.so", "liblog.so", "libandroid.so"}
    pending = sorted(libdir.glob("*.so"))
    sources = {}
    exports = {"libGC3MapAdmission.so": "gc3_map_admit",
               "libgc3_map_jni.so": "Java_dev_mixer_gc3_NativeMap_admit"}
    while pending:
        file = pending.pop()
        info = run(f"elf-{file.stem}", readelf, "-h", "-l", "-d", "--wide", file)
        check(re.search(r"Machine:\s+AArch64", info) and re.search(r"Type:\s+DYN", info),
              f"Expected an AArch64 shared object for {file.name}")
        dependencies = re.findall(r"\(NEEDED\).*\[([^\]]+)\]", info)
        if name := exports.get(file.name):
            symbols = run(f"exports-{file.stem}", readelf, "--dyn-syms", "--wide", file)
            check(re.search(rf"GLOBAL\s+(DEFAULT|PROTECTED)\s+\d+\s+{name}$", symbols, re.M),
                  f"Missing exported function {name}")
            aligns = re.findall(r"^\s+LOAD\s+.*\s(0x[0-9a-f]+)$", info, re.M)
            check(aligns and all(int(align, 16) >= 16_384 for align in aligns),
                  f"Expected 16 KiB load alignment for {file.name}")
        if file.name == "libgc3_map_jni.so":
            check("libGC3MapAdmission.so" in dependencies, "JNI library lacks a Swift admission dependency")
        for name in dependencies:
            check(re.fullmatch(r"lib[A-Za-z0-9_+.-]+\.so", name), f"Unexpected Android dependency {name}")
            destination = libdir / name
            if name in system or destination.exists():
                continue
            source = next((directory / name for directory in (swift_runtime, ndk_runtime)
                           if (directory / name).is_file()), None)
            check(source is not None, f"Unresolved Android library {name}")
            sources[name] = str(source)
            shutil.copyfile(source, destination)
            pending.append(destination)
    return sources


def build(run, args, vectors, receipt):
    scratch = run.scratch
    out = run.out
    stage = scratch / "tree"
    stage.mkdir()
    archive = scratch / "source.tar"
    run.swift_paths("export")
    run("git-export", "git", "archive", EXPORTER, EXPERIMENT, "sdk", "updates", file=archive)
    with tarfile.open(archive) as tar:
        tar.extractall(stage, filter="data")
    package = stage / EXPERIMENT / HERE.name
    shutil.copytree(HERE, package, ignore=shutil.ignore_patterns(".build", "__pycache__"))
    receipt["exporterTree"] = run("exporter-tree", "git", "rev-parse", f"{EXPORTER}:{EXPERIMENT}").strip()
    receipt["updatesTree"] = run("updates-tree", "git", "rev-parse", f"{EXPORTER}:updates").strip()
    receipt["sourceRevision"] = run("worktree-revision", "git", "rev-parse", "HEAD").strip()
    receipt["experimentSources"] = {str(path.relative_to(package)): digest(path)
                                     for path in sorted(package.rglob("*")) if path.is_file()}
    run("host-swift-version", args.host_swift, "--version")
    run("android-swift-version", args.swift, "--version")
    run("java-version", args.jdk / "bin/java", "--version")
    run("xcode-version", "xcodebuild", "-version")
    if vectors:
        shutil.copyfile(vectors, out / "android-vectors.json")
    else:
        run("export-vectors", args.host_swift, "run", "--package-path", stage / EXPERIMENT,
            *run.swift_paths("export"), "-j", args.jobs, "NativeMapReplay", EXPORTER,
            "--android-vectors", out / "android-vectors.json")
    allowed_sources = (EXPORTER, RETAINED_VECTOR_SOURCE) if vectors else (EXPORTER,)
    cases, expectations, signed_source = stage_vectors(out / "android-vectors.json", package, out, allowed_sources)
    receipt["vectorSourceCommit"] = signed_source
    receipt["generatedRootSha256"] = digest(package / "Sources/MapAdmission/InstalledFixtureRoot.swift")
    receipt["installed"] = json.loads((out / "android-vectors.json").read_bytes())["installedRuntime"]

    host_libs = scratch / "host-libs"
    host_libs.mkdir()
    run("swift-host", args.host_swift, "build", "--package-path", package, *run.swift_paths("host"),
        "--product", "GC3MapAdmission", "-j", args.jobs)
    host_dir = (scratch / "host/build/debug").resolve()
    shutil.copyfile(host_dir / "libGC3MapAdmission.dylib", host_libs / "libGC3MapAdmission.dylib")
    c_sources = ["-std=c11", "-Wall", "-Wextra", "-Werror",
                 "-I", package / "Sources/CGC3", package / "bridge/map_jni.c"]
    mac_sdk = run("macos-sdk", "xcrun", "--sdk", "macosx", "--show-sdk-path").strip()
    run("jni-host", "xcrun", "--sdk", "macosx", "clang", "-isysroot", mac_sdk, "-dynamiclib",
        "-I", args.jdk / "include", "-I", args.jdk / "include/darwin", *c_sources,
        "-L", host_libs, "-lGC3MapAdmission", "-Wl,-rpath,@loader_path",
        "-o", host_libs / "libgc3_map_jni.dylib")
    kotlin_classes, dependencies = compile_kotlin(run, args, package, cases, expectations, host_libs)
    receipt["jvmInputsSha256"] = {path.name: digest(path) for path in dependencies}
    receipt["hostReplay"] = {"cases": 32, "coldRefusals": 15, "accepted": 2, "warmRefusals": 15,
                             "surfaces": 1, "sizeControls": 2, "platform": "macOS JVM and Swift"}
    sdk = args.swift_sdks / "swift-6.3.3-RELEASE_android.artifactbundle/swift-android"
    ndk = sdk / "android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64"
    run("ndk-version", ndk / "bin/aarch64-linux-android28-clang", "--version")
    run("swift-android", args.swift, "build", "--package-path", package, *run.swift_paths("android"),
        "--swift-sdks-path", args.swift_sdks, "--swift-sdk", TARGET, "--product", "GC3MapAdmission",
        "-c", "release", "-j", args.jobs, "-Xlinker", "-z", "-Xlinker", "max-page-size=16384")
    libdir = scratch / "arm64-v8a"
    libdir.mkdir()
    source = scratch / "android/build" / TARGET / "release/libGC3MapAdmission.so"
    shutil.copyfile(source, libdir / source.name)
    run("jni-android", ndk / "bin/aarch64-linux-android28-clang", "-shared", "-fPIC", *c_sources,
        "-L", libdir, "-lGC3MapAdmission", "-Wl,-z,defs,-z,max-page-size=16384",
        "-o", libdir / "libgc3_map_jni.so")
    receipt["android"] = {"target": TARGET, "compose": COMPOSE, "runtimeExecuted": False,
                          "sdkLibrarySources": gather_android_libraries(run, sdk, ndk, libdir)}
    receipt["android"]["toolchainInputsSha256"] = {
        file.name: digest(file) for file in (sdk / "swift-sdk.json", sdk / "swift-toolset.json",
                                            ndk.parents[3] / "source.properties")
    }
    receipt["android"]["libraries"] = {file.name: digest(file) for file in sorted(libdir.iterdir())}
    aar = out / "GC3ComposeFixture.aar"
    with zipfile.ZipFile(aar, "w", compression=zipfile.ZIP_DEFLATED) as fixture:
        fixture.writestr("AndroidManifest.xml",
                         '<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
                         'package="dev.mixer.gc3"><uses-sdk android:minSdkVersion="28"/></manifest>')
        fixture.write(kotlin_classes, "classes.jar")
        fixture.write(cases, "assets/gc3/signed-cases.tsv")
        for file in sorted(libdir.iterdir()):
            fixture.write(file, "jni/arm64-v8a/" + file.name)
        crypto = scratch / "android/build/checkouts/swift-crypto"
        for file in (crypto / "LICENSE.txt", crypto / "NOTICE.txt"):
            fixture.write(file, "META-INF/swift-crypto/" + file.name)
        for name in ("NOTICE", "NOTICE.toolchain"):
            fixture.write(ndk.parents[3] / name, "META-INF/android-ndk/" + name)
    with zipfile.ZipFile(aar) as fixture:
        check(fixture.testzip() is None, "Corrupt AAR")
        for name, expected in receipt["android"]["libraries"].items():
            check(sha(fixture.read("jni/arm64-v8a/" + name)) == expected, f"AAR changed {name}")
        check(fixture.read("assets/gc3/signed-cases.tsv") == cases.read_bytes(), "AAR changed the signed cases")
    receipt["artifactsSha256"] = {file.name: digest(file) for file in (aar, cases, expectations, out / "android-vectors.json")}


def main():
    home = Path.home()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", type=Path, help="Reuse an exact vector export from an approved source revision.")
    parser.add_argument("--xcode", type=Path, default="/Applications/Xcode_26.6.app/Contents/Developer")
    parser.add_argument("--host-swift", type=Path, default="/usr/bin/swift")
    parser.add_argument("--swift", type=Path, default=home / "Library/Developer/Toolchains"
                        / "swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift")
    parser.add_argument("--swift-sdks", type=Path, default=home / ".swiftpm/swift-sdks")
    parser.add_argument("--jdk", type=Path, default="/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home")
    parser.add_argument("--cache", type=Path, default=home / ".gradle/caches/modules-2/files-2.1")
    parser.add_argument("--sdk", type=Path, default="/opt/homebrew/share/android-commandlinetools")
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()
    check(args.jobs > 0, "Expected a positive compiler job limit")
    local = ROOT / "verification/local"
    local.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="gc3-android-replay.", dir=local))
    print(f"Evidence and fixture in {out}", flush=True)
    receipt = {"exporterCommit": EXPORTER, "status": "failed"}
    with tempfile.TemporaryDirectory(prefix="build.", dir=out) as scratch:
        run = Run(out, Path(scratch), args.xcode)
        try:
            build(run, args, args.vectors, receipt)
            receipt["status"] = "passed"
        finally:
            receipt["commands"] = run.commands
            (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
