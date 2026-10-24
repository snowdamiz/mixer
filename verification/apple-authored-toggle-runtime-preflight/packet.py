"""Read-only validation and exact archive restore for the frozen candidate.

No compiler, simulator, UI, physical-device, or subprocess calls belong here.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import plistlib
import struct
import tarfile

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
ORIGINAL = ROOT / "verification/apple-authored-toggle-contract/candidate-2-directional-pan"
ORIGINAL_SEAL_SHA256 = "983cc26f8310be9f800e842d96473100e44074d976142f8a5c7ce57fac519333"
APP_NAME = "MixerAuthoredToggle.app"
BUNDLE_ID = "dev.mixer.verification.authoredtoggle"
SOURCE_CLOSURE = "04f91d8abf20e3401a916b8ab03c6d638eefd53f2e8aa8fcded31ef9706e5b9d"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: pathlib.Path) -> str:
    return sha(path.read_bytes())


def read_json(path: pathlib.Path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative_name(name: str) -> pathlib.PurePosixPath:
    path = pathlib.PurePosixPath(name)
    require(not path.is_absolute() and ".." not in path.parts and str(path) == name,
            "Unsafe or noncanonical packet path: " + name)
    return path


def macho(data: bytes) -> dict:
    require(len(data) >= 32 and data[:4] == b"\xcf\xfa\xed\xfe", "Expected thin little-endian Mach-O64")
    _, cpu, _, filetype, count, size, _, _ = struct.unpack_from("<8I", data)
    require(cpu == 0x0100000C, "Expected arm64 executable/library")
    result = {"cpu": "arm64", "fileType": filetype, "dylibs": [], "rpaths": []}
    cursor = 32
    require(cursor + size <= len(data), "Truncated Mach-O load commands")
    for _ in range(count):
        cmd, length = struct.unpack_from("<II", data, cursor)
        require(length >= 8 and cursor + length <= 32 + size, "Invalid Mach-O command size")
        if cmd == 0x32:
            platform, minimum, sdk, _ = struct.unpack_from("<4I", data, cursor + 8)
            version = lambda value: [value >> 16, (value >> 8) & 255, value & 255]
            result.update(platform=platform, minimumOS=version(minimum), sdk=version(sdk))
        elif cmd in (0xC, 0xD, 0x8000001C):
            offset, = struct.unpack_from("<I", data, cursor + 8)
            require(8 <= offset < length, "Invalid Mach-O string offset")
            value = data[cursor + offset:cursor + length].split(b"\0", 1)[0].decode()
            if cmd == 0xD:
                result["installName"] = value
            else:
                result["rpaths" if cmd == 0x8000001C else "dylibs"].append(value)
        cursor += length
    require(result.get("platform") == 7, "Not an iOS Simulator binary")
    require(result.get("minimumOS") == [26, 0, 0], "Unexpected deployment target")
    return result


def archive_payload(archive: pathlib.Path, manifest: dict) -> tuple[dict, dict]:
    """Reject traversal, duplicate/extra files, links, devices, and content drift."""
    require(file_sha(archive) == manifest["archiveSHA256"], "Archive digest mismatch")
    expected = manifest["files"]
    payload = {}
    modes = {}
    seen = set()
    with tarfile.open(archive, "r:gz") as stream:
        for member in stream.getmembers():
            path = relative_name(member.name)
            require(path.parts[0] == APP_NAME, "Archive has an unexpected root")
            require(member.name not in seen, "Duplicate archive member")
            seen.add(member.name)
            require(member.isdir() or member.isfile(), "Archive links/special files are forbidden")
            if member.isdir():
                require(member.name in {APP_NAME, APP_NAME + "/Frameworks", APP_NAME + "/_CodeSignature"},
                        "Unexpected archive directory")
                continue
            key = str(path.relative_to(APP_NAME))
            require(key in expected, "Unexpected archive file: " + key)
            data = stream.extractfile(member).read()
            require(len(data) == expected[key]["bytes"] and sha(data) == expected[key]["sha256"],
                    "Archive manifest mismatch: " + key)
            require(member.mode == (0o755 if key in {"MixerAuthoredToggle", "Frameworks/libMixerCore.dylib", "Frameworks/libMixerUI.dylib"} else 0o644),
                    "Unexpected archived mode: " + key)
            payload[key] = data
            modes[key] = member.mode
    require(set(payload) == set(expected), "Archive omits manifest files")
    return payload, modes


def verify_original(packet: pathlib.Path = ORIGINAL) -> dict:
    require(file_sha(packet / "packet-seal.json") == ORIGINAL_SEAL_SHA256, "Frozen seal anchor changed")
    seal = read_json(packet / "packet-seal.json")
    for name, digest in seal["files"].items():
        relative_name(name)
        path = packet / name
        require(path.is_file() and not path.is_symlink() and file_sha(path) == digest,
                "Frozen file changed: " + name)
    require(file_sha(ROOT / seal["contractDocument"]) == seal["contractDocumentSHA256"], "Frozen contract document changed")
    source = read_json(packet / "source-lock.json")
    hashes = source["sha256"]
    require(sha(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()) == SOURCE_CLOSURE == source["closureSHA256"],
            "Source closure digest changed")
    actual_source = {str(path.relative_to(packet / "source")) for path in (packet / "source").rglob("*") if path.is_file()}
    require(actual_source == set(hashes), "Source closure has extra/missing files")
    for name, digest in hashes.items():
        require(file_sha(packet / "source" / relative_name(name)) == digest, "Source closure file changed")
    policy = read_json(packet / "policy-result.json")
    policy_receipt = read_json(packet / "policy-receipt.json")
    require(policy["pass"] is True and len(policy["checks"]) == 19 and all(item["pass"] is True for item in policy["checks"]),
            "Retained 19 policy cases are not all passing")
    require(policy_receipt["passed"] is True and policy_receipt["checkCount"] == 19
            and policy_receipt["resultSHA256"] == file_sha(packet / "policy-result.json"), "Policy receipt mismatch")
    for name, digest in policy_receipt["sha256"].items():
        require(file_sha(packet / relative_name(name)) == digest, "Policy source receipt mismatch")
    policy_commands = read_json(packet / "policy-commands.json")
    require(all(item["exitCode"] == 0 for item in policy_commands), "Retained policy command failed")
    require(json.loads(policy_commands[-1]["stdout"]) == policy, "Policy executable output mismatch")
    build = read_json(packet / "build-commands.json")
    require(all(item["exitCode"] == 0 for item in build), "Accepted build command failed")
    compile_sources = set()
    for item in build:
        compile_sources.update(value.split("/source/", 1)[1] for value in item["argv"] if "/source/" in value and value.endswith(".swift"))
    require(compile_sources == {name for name in hashes if name.endswith(".swift")}, "Accepted build source closure mismatch")
    manifest = read_json(packet / "built-app-manifest.json")
    payload, _ = archive_payload(packet / "built-app.tar.gz", manifest)
    info = plistlib.loads(payload["Info.plist"])
    require(info["CFBundleIdentifier"] == BUNDLE_ID and info["CFBundleExecutable"] == "MixerAuthoredToggle", "App identity mismatch")
    binaries = {name: macho(payload[name]) for name in ["MixerAuthoredToggle", "Frameworks/libMixerCore.dylib", "Frameworks/libMixerUI.dylib"]}
    executable = binaries["MixerAuthoredToggle"]
    require(executable["fileType"] == 2 and "@executable_path/Frameworks" in executable["rpaths"], "App executable/rpath mismatch")
    require({"@rpath/libMixerCore.dylib", "@rpath/libMixerUI.dylib"}.issubset(executable["dylibs"]), "App module bindings missing")
    for module in ("MixerCore", "MixerUI"):
        require(binaries[f"Frameworks/lib{module}.dylib"].get("installName") == f"@rpath/lib{module}.dylib", "Module install-name mismatch")
    require("@rpath/libMixerCore.dylib" in binaries["Frameworks/libMixerUI.dylib"]["dylibs"], "MixerUI binding missing")
    return {"candidate": "candidate-2-directional-pan", "frozenSealSHA256": ORIGINAL_SEAL_SHA256,
            "sealedFileCount": len(seal["files"]), "sourceClosureSHA256": SOURCE_CLOSURE,
            "archiveSHA256": manifest["archiveSHA256"], "archiveFileCount": len(payload),
            "retainedPolicyChecksPassed": 19, "acceptedBuildCommandCount": len(build),
            "acceptedCompiler": next(item["stdout"].strip() for item in build if item["argv"] == ["xcodebuild", "-version"]),
            "executableBindings": binaries, "scope": "Read-only seal/content/proof validation; no new compiler or native execution"}


def verify_restored(app: pathlib.Path, packet: pathlib.Path = ORIGINAL) -> dict:
    require(app.name == APP_NAME and app.is_dir() and not app.is_symlink(), "Invalid restored app root")
    manifest = read_json(packet / "built-app-manifest.json")
    actual = {}
    for path in app.rglob("*"):
        require(not path.is_symlink(), "Restored app contains a link")
        if path.is_file():
            actual[str(path.relative_to(app))] = {"sha256": file_sha(path), "bytes": path.stat().st_size}
    require(actual == manifest["files"], "Restored app manifest mismatch")
    require((app / "MixerAuthoredToggle").stat().st_mode & 0o111 == 0o111, "Restored executable is not executable")
    return {"path": str(app), "archiveSHA256": manifest["archiveSHA256"], "fileCount": len(actual), "exactManifest": True}


def restore(destination: pathlib.Path, packet: pathlib.Path = ORIGINAL) -> dict:
    verify_original(packet)
    require(not destination.is_symlink(), "Refusing linked restore destination")
    app = destination / APP_NAME
    if app.exists():
        return verify_restored(app, packet)
    require(not destination.exists(), "Restore destination exists without a valid app")
    manifest = read_json(packet / "built-app-manifest.json")
    payload, modes = archive_payload(packet / "built-app.tar.gz", manifest)
    destination.mkdir(parents=True)
    for name, data in payload.items():
        target = app / relative_name(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(modes[name])
    return verify_restored(app, packet)
