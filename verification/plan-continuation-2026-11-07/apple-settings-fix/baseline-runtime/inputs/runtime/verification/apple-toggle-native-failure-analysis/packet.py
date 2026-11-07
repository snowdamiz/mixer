"""Read-only diagnostics/comparator sealing and exact archive restore.

Archive and Mach-O guards are adapted from the reviewed frozen runtime wrapper.
No subprocess, compiler, simulator, UI, or physical-device operation belongs here.
"""
import hashlib
import json
import pathlib
import plistlib
import struct
import tarfile

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
CONFIGS = {
    "comparator": {"folder": "sdk26-comparator", "app": "MixerAuthoredToggle.app", "executable": "MixerAuthoredToggle", "bundle": "dev.mixer.verification.authoredtoggle", "source": "04f91d8abf20e3401a916b8ab03c6d638eefd53f2e8aa8fcded31ef9706e5b9d"},
    "diagnostic": {"folder": "diagnostic-candidate-2-standalone-pan", "app": "MixerToggleDiagnostics.app", "executable": "MixerToggleDiagnostics", "bundle": "dev.mixer.verification.authoredtoggle.diagnostics", "source": "0ddb00a4ecbe73012bd4cef167696bdbbd9827f3edb99677a9a7b04f07a8de3f"}}
SOURCE_CLOSURE = hashlib.sha256(json.dumps({key: value["source"] for key, value in CONFIGS.items()}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def relative_name(name):
    path = pathlib.PurePosixPath(name)
    require(not path.is_absolute() and ".." not in path.parts and str(path) == name,
            "Unsafe or noncanonical packet path: " + name)
    return path


def macho(data):
    require(len(data) >= 32 and data[:4] == b"\xcf\xfa\xed\xfe", "Expected thin little-endian Mach-O64")
    _, cpu, _, filetype, count, size, _, _ = struct.unpack_from("<8I", data)
    require(cpu == 0x0100000C and 32 + size <= len(data), "Expected complete arm64 load commands")
    cursor = 32
    result = {"cpu": "arm64", "fileType": filetype}
    for _ in range(count):
        cmd, length = struct.unpack_from("<II", data, cursor)
        require(length >= 8 and cursor + length <= 32 + size, "Invalid Mach-O command size")
        if cmd == 0x32:
            require(length >= 24, "Truncated build version")
            platform, minimum, sdk, _ = struct.unpack_from("<4I", data, cursor + 8)
            result.update(platform=platform, minimumOS=minimum, sdk=sdk)
        cursor += length
    require(result.get("platform") == 7 and result.get("minimumOS") == 26 << 16
            and result.get("sdk") == ((26 << 16) | (5 << 8)), "Expected SDK26.5/minimum26.0 iOS Simulator binary")
    return result


def archive_payload(archive, manifest, config):
    require(file_sha(archive) == manifest["archiveSHA256"], "Archive digest mismatch")
    payload, modes, seen = {}, {}, set()
    app = config["app"]
    expected = manifest["files"]
    executable_names = {config["executable"], "Frameworks/libMixerCore.dylib", "Frameworks/libMixerUI.dylib"}
    with tarfile.open(archive, "r:gz") as stream:
        for member in stream.getmembers():
            path = relative_name(member.name)
            require(path.parts[0] == app, "Archive has an unexpected root")
            require(member.name not in seen, "Duplicate archive member")
            seen.add(member.name)
            require(member.isdir() or member.isfile(), "Archive links/special files are forbidden")
            if member.isdir():
                require(member.name in {app, app + "/Frameworks", app + "/_CodeSignature"}, "Unexpected archive directory")
                continue
            key = str(path.relative_to(app))
            require(key in expected, "Unexpected archive file: " + key)
            data = stream.extractfile(member).read()
            require(len(data) == expected[key]["bytes"] and hashlib.sha256(data).hexdigest() == expected[key]["sha256"], "Archive manifest mismatch: " + key)
            require(member.mode == (0o755 if key in executable_names else 0o644), "Unexpected archived mode: " + key)
            payload[key], modes[key] = data, member.mode
    require(set(payload) == set(expected), "Archive omits manifest files")
    return payload, modes


def verify_history():
    history = BASE / "history/attempt-1"
    require(file_sha(history / "packet-seal.json") == "09fc2dd83a20035243b7dc3b512bb6c334291f3863e6bc31fb1eb7b451c1fb42", "Historical seal anchor changed")
    seal = read_json(history / "packet-seal.json")
    require(len(seal["files"]) == 110, "Historical attempt file count changed")
    for name, digest in seal["files"].items():
        path = history / "files" / relative_name(name)
        require(path.is_file() and not path.is_symlink() and file_sha(path) == digest, "Historical attempt changed: " + name)
    return {"files": 110, "sealSHA256": file_sha(history / "packet-seal.json")}


def verify_packet():
    seal = read_json(BASE / "packet-seal.json")
    require(seal["schema"] == "mixer.apple-toggle-diagnostics-handoff.1" and seal["sourceClosureSHA256"] == SOURCE_CLOSURE,
            "Wrong diagnostic handoff seal")
    require(seal["excludedMutableSubtrees"] == ["verification/apple-toggle-native-failure-analysis/runtime/"], "Unexpected mutable exclusion")
    for name, digest in seal["files"].items():
        path = ROOT / relative_name(name)
        require(path.is_file() and not path.is_symlink() and file_sha(path) == digest, "Sealed file changed: " + name)
    historical = verify_history()
    results = {}
    for key, config in CONFIGS.items():
        folder = BASE / config["folder"]
        lock = read_json(folder / "source-lock.json")
        actual = {str(path.relative_to(folder / "source")): file_sha(path) for path in sorted((folder / "source").rglob("*")) if path.is_file()}
        digest = hashlib.sha256(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        require(actual == lock["sha256"] and digest == config["source"] == lock["sourceClosureSHA256"], "Source closure changed: " + key)
        if key == "comparator":
            original = read_json(ROOT / "verification/apple-authored-toggle-contract/candidate-2-directional-pan/source-lock.json")
            require(actual == original["sha256"], "Comparator is not exact frozen source")
        manifest = read_json(folder / "built-app-manifest.json")
        payload, _ = archive_payload(folder / "built-app.tar.gz", manifest, config)
        info = plistlib.loads(payload["Info.plist"])
        require(info["CFBundleIdentifier"] == config["bundle"] and info["CFBundleExecutable"] == config["executable"], "App identity changed")
        binaries = {name: macho(payload[name]) for name in [config["executable"], "Frameworks/libMixerCore.dylib", "Frameworks/libMixerUI.dylib"]}
        receipt = read_json(folder / "receipt.json")
        commands = read_json(folder / receipt["buildCommands"])
        require(all(item["exitCode"] == 0 for item in commands), "Crosscompile failed")
        compiled = {value.split("/source/", 1)[1] for command in commands for value in command["argv"] if "/source/" in value and value.endswith(".swift")}
        require(compiled == {name for name in actual if name.endswith(".swift")}, "Crosscompile source closure mismatch")
        require(receipt["sourceClosureSHA256"] == digest and receipt["archiveSHA256"] == manifest["archiveSHA256"], "Build receipt changed")
        results[key] = {"sourceClosureSHA256": digest, "archiveSHA256": manifest["archiveSHA256"], "fileCount": len(payload), "binaryBuildVersions": binaries}
    oracle = read_json(BASE / "diagnostic-candidate-2-standalone-pan/oracle-receipt.json")
    oracle_commands = read_json(BASE / "diagnostic-candidate-2-standalone-pan/oracle-commands.json")
    require(oracle["passed"] and oracle["checkCount"] == 17 and all(item["pass"] is True for item in oracle["checks"]), "Retained oracle failed")
    require(all(item["exitCode"] == 0 for item in oracle_commands)
            and json.loads(oracle_commands[-1]["stdout"])["checks"] == oracle["checks"], "Oracle output mismatch")
    host = read_json(BASE / "host-checks.json")
    require(host["exitCode"] == 0 and "Ran 40 tests" in host["stderr"] and host["stderr"].rstrip().endswith("OK"), "Retained mocked guard checks failed")
    return {"sealSHA256": file_sha(BASE / "packet-seal.json"), "files": len(seal["files"]), "candidates": results, "historicalAttempt": historical, "nativeExecuted": False}


def verify_restored(app, key):
    config = CONFIGS[key]
    require(app.name == config["app"] and app.is_dir() and not app.is_symlink(), "Invalid restored app root")
    manifest = read_json(BASE / config["folder"] / "built-app-manifest.json")
    actual = {}
    for path in app.rglob("*"):
        require(not path.is_symlink(), "Restored app contains a link")
        if path.is_file():
            relative = str(path.relative_to(app))
            actual[relative] = {"sha256": file_sha(path), "bytes": path.stat().st_size}
            expected_mode = 0o755 if relative in {config["executable"], "Frameworks/libMixerCore.dylib", "Frameworks/libMixerUI.dylib"} else 0o644
            require(path.stat().st_mode & 0o777 == expected_mode, "Restored mode mismatch")
    require(actual == manifest["files"], "Restored app manifest mismatch")
    return {"path": str(app), "archiveSHA256": manifest["archiveSHA256"], "exactManifest": True}


def restore(destination, key):
    config = CONFIGS[key]
    require(not destination.is_symlink() and destination.resolve() == destination, "Refusing linked restore destination")
    app = destination / config["app"]
    if app.exists():
        return verify_restored(app, key)
    require(not destination.exists(), "Restore destination exists without valid app")
    manifest = read_json(BASE / config["folder"] / "built-app-manifest.json")
    payload, modes = archive_payload(BASE / config["folder"] / "built-app.tar.gz", manifest, config)
    destination.mkdir(parents=True)
    for name, data in payload.items():
        target = app / relative_name(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(modes[name])
    return verify_restored(app, key)
