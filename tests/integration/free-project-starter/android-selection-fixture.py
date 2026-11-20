"""Prepare inert Android selection bytes for the existing worker verifier."""

import json
from hashlib import sha256
from pathlib import Path
import plistlib
import secrets
import sys


def write(path, data, mode=0o400):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)
    return sha256(data).hexdigest()


def tree_digest(files):
    return sha256(b"".join(f"{path}\0{pin}\n".encode() for path, pin in sorted(files.items()))).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def fixture(root, organization, project, app, port):
    export = root / "export"
    cli = root / "mixer"
    swift = Path("/usr/bin/swift")
    python = Path(sys.executable).resolve(strict=True)
    inert_tool = b"#!/bin/sh\nexit 97\n"
    tools = {str(cli): write(cli, inert_tool, 0o500),
             **{str(path): sha256(path.read_bytes()).hexdigest() for path in (swift, python)}}
    lock = {"android": {"toolchain": {"tools": {"python": {"path": str(python), "sha256": tools[str(python)]}}}}}
    files = {
        "mixer.lock": write(export / "mixer.lock", encode(lock)),
        "Generated/MixerAndroid/android-build.py": write(
            export / "Generated/MixerAndroid/android-build.py", b"raise SystemExit(97)\n"),
    }
    for directory in (export / "Generated/MixerAndroid", export / "Generated", export):
        directory.chmod(0o500)

    mirrors = {}
    for package in ("swift-crypto", "swift-asn1"):
        mirror = root / f"{package}.git"
        pin = write(mirror / "HEAD", b"selection-only mirror fixture\n")
        mirrors[package] = {"url": mirror.as_uri(), "tree_sha256": tree_digest({"HEAD": pin})}

    xcode_pins = {}
    developer_dirs = {}
    for role in ("host", "android"):
        bundle = root / f"{role}.app"
        developer_dirs[role] = str(bundle / "Contents/Developer")
        contents = {
            "Contents/Info.plist": plistlib.dumps({"CFBundleIdentifier": "com.apple.dt.Xcode"}),
            "Contents/version.plist": plistlib.dumps({"ProductBuildVersion": "inert-fixture"}),
            "Contents/Developer/usr/bin/xcodebuild": inert_tool,
        }
        if role == "host":
            contents["Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"] = inert_tool
        xcode_pins[role] = {
            path: write(bundle / path, data, 0o400 if path.endswith(".plist") else 0o500)
            for path, data in contents.items()
        }

    environment = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "DEVELOPER_DIR": developer_dirs["host"]}
    recipe = {
        "argv": [str(cli), "build", "--platform", "android", "--directory", str(export)],
        "cwd": str(export), "environment": environment, "inputs": files, "tools": tools,
        "profile": "unsigned-android-local-v1", "timeout_seconds": 1800,
        "package_policy": "exact-locked-android-file-mirrors-v1",
        "android_host_swift": str(swift), "android_python": str(python),
        "android_developer_dir": developer_dirs["android"], "android_xcode_pins": xcode_pins,
        "android_mirrors": mirrors,
    }
    recipe_path = root / "recipe.json"
    definition = write(recipe_path, encode(recipe))
    tree = tree_digest(files)
    spec = {
        "organization_id": organization, "project_id": project, "application_id": app,
        "platform": "android", "source": {"kind": "revision", "reference": "starter-" + tree, "sha256": tree},
        "toolchain_lock_sha256": files["mixer.lock"], "build_definition_sha256": definition,
    }
    worker = {
        "tenant": organization, "port": int(port), "worker_id": "local-android-selection-fixture",
        "token": secrets.token_hex(32),
        "registration": {"root": str(export), "recipe": str(recipe_path), "spec": spec, "files": files},
        "policy": {"cli": str(cli), "recipe_sha256": definition,
                   "environment": environment, "inputs": files, "tools": tools},
    }
    print(write(root / "worker.json", encode(worker)))


if __name__ == "__main__":
    fixture(Path(sys.argv[1]), *sys.argv[2:])
