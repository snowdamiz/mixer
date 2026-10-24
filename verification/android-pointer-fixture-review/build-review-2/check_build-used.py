#!/usr/bin/env python3
"""Independent host-only frozen pointer build replay. Never invokes adb/emulator."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / (sys.argv[1] if len(sys.argv) > 1 else "build-review-2")
CANDIDATE = ROOT / "verification/android-pointer-fixture/candidate-3"
BASE = ROOT / "verification/android-coordinator-apk-packaging/candidate-1"
JAVA_HOME = Path("/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home")
BUILD_TOOLS = Path("/opt/homebrew/share/android-commandlinetools/build-tools/37.0.0")
ANDROID_JAR = Path("/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def read(path):
    return json.loads(path.read_text())


def exact_seal(directory):
    expected = read(directory / "artifact-seal.json")
    found = {}
    for path in sorted(directory.rglob("*")):
        assert not path.is_symlink(), path
        if path.is_file() and path != directory / "artifact-seal.json":
            data = path.read_bytes()
            found[str(path.relative_to(directory))] = {"bytes": len(data), "sha256": sha(data)}
    assert found == expected, directory
    return len(found)


def archive(directory):
    expected = read(directory / "built-artifacts.json")
    found = {}
    apk = None
    with tarfile.open(directory / "built-artifacts.tar.gz", "r:gz") as stream:
        members = stream.getmembers()
        assert len(members) == len({m.name for m in members})
        assert {m.name for m in members} == set(expected)
        for member in members:
            assert member.isfile() and not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
            data = stream.extractfile(member).read()
            found[member.name] = {"bytes": len(data), "sha256": sha(data)}
            assert found[member.name] == expected[member.name], member.name
            if member.name == "coordinator-join.apk":
                apk = data
    assert apk is not None
    return found, apk


def elf_loads(data):
    assert data[:6] == b"\x7fELF\x02\x01"
    assert struct.unpack_from("<H", data, 18)[0] == 183
    start = struct.unpack_from("<Q", data, 32)[0]
    width, count = struct.unpack_from("<HH", data, 54)
    assert width >= 56
    loads = []
    for i in range(count):
        kind, flags, offset, virtual, _, size, memory, alignment = struct.unpack_from("<IIQQQQQQ", data, start + i * width)
        if kind == 1:
            assert alignment >= 16384 and alignment & (alignment - 1) == 0
            assert offset % 16384 == virtual % 16384
            assert offset + size <= len(data) and memory >= size
            loads.append({"offset": offset, "virtualAddress": virtual, "bytes": size, "alignment": alignment})
    assert loads
    return loads


def apk_entries(data):
    entries = {}
    spans = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        infos = archive.infolist()
        assert len(infos) == len({v.filename for v in infos})
        for info in infos:
            assert not info.is_dir() and not Path(info.filename).is_absolute() and ".." not in Path(info.filename).parts
            header = struct.unpack_from("<IHHHHHIIIHH", data, info.header_offset)
            signature, version, flags, compression, _, _, crc, csize, usize, nlen, elen = header
            assert signature == 0x04034B50 and not flags & (1 | 8)
            assert flags == info.flag_bits and compression == info.compress_type
            assert (crc, csize, usize) == (info.CRC, info.compress_size, info.file_size)
            start = info.header_offset + 30
            assert data[start:start + nlen].decode("utf-8") == info.filename
            offset = start + nlen + elen
            spans.append((info.header_offset, offset + csize))
            body = archive.read(info)
            row = {"sha256": sha(body), "bytes": len(body), "compressionMethod": compression, "localHeaderOffset": info.header_offset, "localDataOffset": offset}
            if compression == 0:
                assert offset % 4 == 0
            if info.filename == "resources.arsc":
                assert compression == 0 and offset % 4 == 0
            if info.filename.startswith("lib/"):
                assert info.filename.startswith("lib/arm64-v8a/") and info.filename.endswith(".so")
                assert compression == 0 and offset % 16384 == 0
                row["elfLoads"] = elf_loads(body)
            entries[info.filename] = row
    assert all(a[1] <= b[0] for a, b in zip(sorted(spans), sorted(spans)[1:]))
    assert len([name for name in entries if name.startswith("lib/")]) == 18
    return entries


def dex_classes(data):
    assert data[:4] == b"dex\n" and data[7] == 0
    strings_size, strings_off, types_size, types_off = struct.unpack_from("<IIII", data, 56)
    class_size, class_off = struct.unpack_from("<II", data, 96)
    strings = []
    for i in range(strings_size):
        at = struct.unpack_from("<I", data, strings_off + 4 * i)[0]
        while data[at] & 0x80:
            at += 1
        at += 1
        strings.append(data[at:data.index(0, at)].decode("utf-8", errors="replace"))
    types = [strings[struct.unpack_from("<I", data, types_off + 4 * i)[0]] for i in range(types_size)]
    return sorted(types[struct.unpack_from("<I", data, class_off + 32 * i)[0]] for i in range(class_size))


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    scratch = OUT / ".scratch"
    scratch.mkdir()
    commands = []
    tools = {}
    result = {"schema": 1, "command": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))], "pythonVersion": sys.version, "reviewScriptSHA256": sha(Path(__file__).read_bytes()), "nativeInstancesStarted": 0, "physicalQueries": False, "nativeRuntime": "NOT RUN"}

    def run(name, argv):
        started = time.time()
        executable = Path(argv[0])
        if executable.is_absolute() and executable.is_file():
            tools[str(executable)] = {"sha256": sha(executable.read_bytes()), "realPath": str(executable.resolve())}
        completed = subprocess.run([str(x) for x in argv], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, env={**os.environ, "JAVA_HOME": str(JAVA_HOME)}, start_new_session=True)
        data = completed.stdout
        (OUT / (name + ".log")).write_bytes(data)
        commands.append({"argv": [str(x) for x in argv], "cwd": str(ROOT), "exitCode": completed.returncode, "output": name + ".log", "outputSHA256": sha(data), "startedUnix": started, "finishedUnix": time.time()})
        assert completed.returncode == 0, (name, completed.returncode, data[-1000:])

    try:
        result["candidateSealFiles"] = exact_seal(CANDIDATE)
        result["baselineSealFiles"] = exact_seal(BASE)
        receipt, base_receipt = read(CANDIDATE / "receipt.json"), read(BASE / "receipt.json")
        result["sourceRevision"] = receipt["sourceRevision"]
        result["sourceTree"] = receipt["sourceTree"]
        result["sourceClosureSHA256"] = receipt["sourceClosureSHA256"]
        locked, base_locked = read(CANDIDATE / "source-lock.json")["files"], read(BASE / "source-lock.json")["files"]
        assert len(locked) == 105 and set(locked) == set(base_locked)
        assert sha(json.dumps(locked, sort_keys=True, separators=(",", ":")).encode()) == receipt["sourceClosureSHA256"]
        for name, value in locked.items():
            assert sha((CANDIDATE / "inputs" / name).read_bytes()) == value, name
            assert sha((BASE / "inputs" / name).read_bytes()) == base_locked[name], name
        changed_inputs = sorted(name for name in locked if locked[name] != base_locked[name])
        assert changed_inputs == ["verification/android-coordinator-join/" + name for name in ("CoordinatorJoinActivity.java", "CoordinatorJoinInstrumentation.java", "operations.json")]
        native_sdk = [name for name in locked if name.startswith(("native/", "sdk/"))]
        assert len(native_sdk) == 88 and all(locked[name] == base_locked[name] for name in native_sdk)
        result.update({"inputs": len(locked), "changedInputs": changed_inputs, "unchangedNativeAndSDKInputs": len(native_sdk), "nativeAndSDKTestInputs": sum("/Tests/" in name for name in native_sdk)})
        built, apk = archive(CANDIDATE)
        base_built, base_apk = archive(BASE)
        assert sha(apk) == receipt["apkSHA256"] == "ef5dded4276df3b278d90a5c7c770db884c3b8ff341d51480df7b78f405ae15a"
        assert sha(base_apk) == base_receipt["apkSHA256"] == "78af8c5df197fb6f163f3010825648a1b1a50427c9ab963b1c5aeca1e513b3ba"
        production = [name for name in built if name.startswith("production-classes/")]
        assert len(production) == 155 and all(built[name] == base_built[name] for name in production)
        unchanged = [name for name in built if name in base_built and built[name] == base_built[name]]
        assert len(unchanged) == 173
        changed = sorted(name for name in built if built[name] != base_built.get(name))
        assert len(changed) == 6
        current_entries, baseline_entries = apk_entries(apk), apk_entries(base_apk)
        assert set(current_entries) == set(baseline_entries)
        changed_entries = sorted(name for name in current_entries if current_entries[name]["sha256"] != baseline_entries[name]["sha256"])
        assert changed_entries == ["META-INF/DEBUG.RSA", "META-INF/DEBUG.SF", "META-INF/MANIFEST.MF", "assets/CoordinatorJoin/operations.json", "classes.dex"]
        with zipfile.ZipFile(io.BytesIO(apk)) as apk_zip, zipfile.ZipFile(io.BytesIO(base_apk)) as old_zip:
            classes, old_classes = dex_classes(apk_zip.read("classes.dex")), dex_classes(old_zip.read("classes.dex"))
        new_classes = set(classes) - set(old_classes)
        assert new_classes == {"Ldev/mixer/android/CoordinatorJoinActivity$Observer;", *[f"Ldev/mixer/android/CoordinatorJoinInstrumentation${i};" for i in range(19, 23)]}
        assert not set(old_classes) - set(classes)
        result.update({"apkSHA256": sha(apk), "builtArchiveSHA256": sha((CANDIDATE / "built-artifacts.tar.gz").read_bytes()), "artifactCount": len(built), "unchangedArtifacts": len(unchanged), "unchangedProductionClasses": len(production), "changedArtifacts": changed, "changedAPKEntries": changed_entries, "apkEntries": len(current_entries), "dexClassDefinitions": len(classes), "newDexDefinitions": sorted(set(classes) - set(old_classes))})
        save(OUT / "independent-apk-layout.json", current_entries)
        with tarfile.open(CANDIDATE / "built-artifacts.tar.gz", "r:gz") as stream:
            for member in stream.getmembers():
                target = scratch / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(stream.extractfile(member).read())
        (scratch / "recompiled-tests").mkdir()
        (scratch / "empty-sourcepath").mkdir()
        (scratch / "recompiled-dex").mkdir()
        run("javac-version", [JAVA_HOME / "bin/javac", "--version"])
        run("d8-version", [BUILD_TOOLS / "d8", "--version"])
        run("apksigner-version", [BUILD_TOOLS / "apksigner", "version"])
        harness = CANDIDATE / "inputs/verification/android-coordinator-join"
        run("harness-recompile", [JAVA_HOME / "bin/javac", "--release", "17", "-Xlint:all", "-Werror", "-sourcepath", scratch / "empty-sourcepath", "-classpath", str(scratch / "production-classes") + ":" + str(ANDROID_JAR), "-d", scratch / "recompiled-tests", harness / "CoordinatorJoinActivity.java", harness / "CoordinatorJoinInstrumentation.java"])
        test_classes = sorted((scratch / "recompiled-tests").rglob("*.class"))
        assert len(test_classes) == 4
        for path in test_classes:
            name = "test-classes/" + str(path.relative_to(scratch / "recompiled-tests"))
            assert sha(path.read_bytes()) == built[name]["sha256"], name
        run("dex-recompile", [BUILD_TOOLS / "d8", "--min-api", "36", "--lib", ANDROID_JAR, "--output", scratch / "recompiled-dex", *sorted((scratch / "production-classes").rglob("*.class")), *test_classes])
        assert sha((scratch / "recompiled-dex/classes.dex").read_bytes()) == built["dex/classes.dex"]["sha256"]
        run("official-zipalign", [BUILD_TOOLS / "zipalign", "-c", "-P", "16", "-v", "4", scratch / "coordinator-join.apk"])
        run("official-apksigner", [BUILD_TOOLS / "apksigner", "verify", "--verbose", "--print-certs", scratch / "coordinator-join.apk"])
        signature = (OUT / "official-apksigner.log").read_text()
        assert "Verifies" in signature and "e7065ca3199e92f2afcaeab7fbf9bbff845993f726409f104d4be6d4366b220f" in signature
        for directory in [CANDIDATE, BASE]:
            exact_seal(directory)
        result.update({"status": "passed-independent-host-only-build-parity-and-packaging", "harnessClassesRecompiledByteExact": 4, "dexRecompiledByteExact": True, "nativeLibrariesStored16KiBAligned": 18, "resourcesStored4ByteAligned": True, "debugCertificateSHA256": receipt["debugCertificateSHA256"], "nativeRuntimeQualified": False, "gaAccepted": False})
    finally:
        size = sum(path.stat().st_size for path in scratch.rglob("*") if path.is_file())
        count = sum(path.is_file() for path in scratch.rglob("*"))
        holder = subprocess.run(["/usr/sbin/lsof", "-nP", "+D", str(scratch)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        (OUT / "scratch-open-holders.log").write_bytes(holder.stdout)
        assert holder.returncode == 1 and holder.stdout == b"", "own scratch still held"
        shutil.rmtree(scratch)
        result["scratchCleanup"] = {"files": count, "bytes": size, "holderCheckExitCode": holder.returncode, "holderOutputSHA256": sha(holder.stdout), "pathAbsent": not scratch.exists(), "scope": "only review-owned extraction/recompile scratch; unrelated processes untouched"}
        result["commands"] = commands
        result["tools"] = tools
        save(OUT / "receipt.json", result)
        save(OUT / "artifact-seal.json", {str(p.relative_to(OUT)): {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(OUT.rglob("*")) if p.is_file() and p != OUT / "artifact-seal.json"})
    print(json.dumps({key: result[key] for key in ("status", "apkSHA256", "inputs", "unchangedProductionClasses", "nativeLibrariesStored16KiBAligned", "harnessClassesRecompiledByteExact", "dexRecompiledByteExact", "scratchCleanup")}))


if __name__ == "__main__":
    main()
