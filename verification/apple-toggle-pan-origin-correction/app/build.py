#!/usr/bin/env python3
"""Crosscompile isolated diagnostics only. Does not invoke simctl or Git."""
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tarfile
import time

PACKET = pathlib.Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
SOURCE = PACKET / "source"
BUILD = PACKET / "build"
DEVELOPER = pathlib.Path("/Applications/Xcode_26.6.app/Contents/Developer")
APP = "MixerToggleDiagnostics"
ENV = {**os.environ, "DEVELOPER_DIR": str(DEVELOPER)}
BUILD.mkdir(exist_ok=True)
attempt = len(list(PACKET.glob("build-attempt-*.json"))) + 1
commands = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv):
    argv = list(map(str, argv))
    started = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, env=ENV, text=True, capture_output=True, timeout=180)
    commands.append({"argv": argv, "cwd": str(ROOT), "DEVELOPER_DIR": str(DEVELOPER),
                     "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     "elapsedSeconds": time.monotonic() - started, "exitCode": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
    (PACKET / f"build-attempt-{attempt}.json").write_text(json.dumps(commands, indent=2) + "\n")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


origin = json.loads((ROOT / "verification/apple-authored-toggle-contract/candidate-2-directional-pan/source-lock.json").read_text())
files = {str(p.relative_to(SOURCE)): sha(p) for p in sorted(SOURCE.rglob("*")) if p.is_file()}
closure = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
lock = {"originalFrozenRevision": origin["revision"], "originalFrozenGitTree": origin["gitTree"],
        "originalClosureSHA256": origin["closureSHA256"], "sourceClosureSHA256": closure,
        "scope": "Source-derived diagnostic app only; compile is not native qualification", "sha256": files}
(PACKET / "source-lock.json").write_text(json.dumps(lock, indent=2) + "\n")
version = run([DEVELOPER / "usr/bin/xcodebuild", "-version"])
if not version.startswith("Xcode 26.6\n"):
    raise RuntimeError("Compiler pin changed")
swift_version = run(["/usr/bin/xcrun", "swiftc", "--version"])
sdk = run(["/usr/bin/xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"])
common = ["/usr/bin/xcrun", "swiftc", "-target", "arm64-apple-ios26.0-simulator", "-sdk", sdk,
          "-swift-version", "6", "-I", BUILD, "-L", BUILD]
for module, libs in [("MixerCore", []), ("MixerUI", ["MixerCore"])]:
    run(common + ["-emit-library", "-emit-module", "-module-name", module, "-emit-module-path", BUILD / (module + ".swiftmodule"), "-o", BUILD / ("lib" + module + ".dylib")]
        + sorted((SOURCE / "sdk/Sources" / module).glob("*.swift")) + ["-l" + x for x in libs]
        + ["-Xlinker", "-install_name", "-Xlinker", "@rpath/lib" + module + ".dylib"])
app = BUILD / (APP + ".app")
app.mkdir(exist_ok=True)
(app / "Frameworks").mkdir(exist_ok=True)
shutil.copy2(SOURCE / "Prototype/Info.plist", app / "Info.plist")
for module in ["MixerCore", "MixerUI"]:
    dest = app / "Frameworks" / ("lib" + module + ".dylib")
    shutil.copy2(BUILD / dest.name, dest)
    run(["/usr/bin/codesign", "--force", "--sign", "-", dest])
run(common + sorted((SOURCE / "Prototype").glob("*.swift"))
    + ["-o", app / APP, "-lMixerCore", "-lMixerUI", "-Xlinker", "-rpath", "-Xlinker", "@executable_path/Frameworks", "-framework", "UIKit"])
run(["/usr/bin/codesign", "--force", "--sign", "-", app])
if files != {str(p.relative_to(SOURCE)): sha(p) for p in sorted(SOURCE.rglob("*")) if p.is_file()}:
    raise RuntimeError("App sources changed during crosscompile")
binary_info = run(["/usr/bin/xcrun", "vtool", "-show-build", app / APP])
with tarfile.open(PACKET / "built-app.tar.gz", "w:gz") as archive:
    archive.add(app, arcname=app.name)
manifest = {"archive": "built-app.tar.gz", "archiveSHA256": sha(PACKET / "built-app.tar.gz"),
            "deploymentTarget": "arm64-apple-ios26.0-simulator", "files": {
                str(p.relative_to(app)): {"sha256": sha(p), "bytes": p.stat().st_size}
                for p in sorted(app.rglob("*")) if p.is_file()}}
(PACKET / "built-app-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
receipt = {"scope": lock["scope"], "status": "crosscompiled-native-execution-pending-root-review",
           "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "sourceClosureSHA256": closure,
           "archiveSHA256": manifest["archiveSHA256"], "buildCommands": f"build-attempt-{attempt}.json",
           "xcodeVersion": version, "swiftVersion": swift_version, "sdk": sdk, "binaryBuildVersion": binary_info,
           "toolFiles": {str(p): sha(p) for p in [DEVELOPER / "usr/bin/xcodebuild", DEVELOPER / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc", pathlib.Path("/usr/bin/xcrun"), pathlib.Path("/usr/bin/codesign"), pathlib.Path(sdk) / "SDKSettings.json"]},
           "nativeExecuted": False, "simulatorCreated": False, "physicalDevicesQueried": False,
           "nativeQualification": False, "productionAppleAdapterAcceptance": False}
(PACKET / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
