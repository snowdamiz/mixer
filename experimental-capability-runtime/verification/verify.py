#!/usr/bin/env python3
"""Frozen implementer qualification for the isolated experimental Swift bridge."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "experimental-capability-runtime"
parser = argparse.ArgumentParser()
parser.add_argument("--name", required=True)
parser.add_argument("--stage-root", type=Path, default=PACKAGE / "build-verification/local/qualified-final-v3")
args = parser.parse_args()
if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.name):
    raise SystemExit("name must be a short lowercase fresh directory component")
OUT = PACKAGE / "verification" / args.name
OUT.mkdir(exist_ok=False)
SCRATCH = PACKAGE / ".build" / ("qualification-" + args.name)
SOURCE = SCRATCH / "source"
SOURCE.mkdir(parents=True, exist_ok=False)
STAGE = args.stage_root.resolve()
XENV = {"DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer"}
AENV = {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"}
SWIFT = "/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
SDKS = "/Users/andreyyurlov/.swiftpm/swift-sdks"
PIN = "b25e3b7de2391a80d12e7fd75e60903495bec120"

def sha(data): return hashlib.sha256(data).hexdigest()
def digest(path): return sha(path.read_bytes())
def inputs():
    fixed = [PACKAGE / "Package.swift", PACKAGE / "README.md", Path(__file__), PACKAGE / "verification/with-loopback.py", ROOT / "docs/experimental-capability-bridge-design.md"]
    for folder in [PACKAGE / "Sources", PACKAGE / "Tests", PACKAGE / "verification/CrossProbe", ROOT / "sdk"]:
        fixed.extend(p for p in folder.rglob("*") if p.is_file() and not {".build", ".swiftpm", "__pycache__", ".git"}.intersection(p.relative_to(folder).parts) and p.name != ".DS_Store")
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(fixed))}

baseline = inputs()
for name in baseline:
    destination = SOURCE / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes((ROOT / name).read_bytes())
    destination.chmod(0o444)
manifest = "".join(value + "  " + name + "\n" for name, value in baseline.items())
(OUT / "source-manifest.sha256").write_text(manifest)
artifacts = {}
for target in ["host", "ios", "ios-simulator", "android"]:
    stage = STAGE / target
    artifacts[target] = {str(p.relative_to(STAGE)): digest(p) for p in [stage / "include/mixer_vm.h", stage / "include/mixer_vm_capability.h", stage / "lib/libmixer_vm_capability_experimental.a", stage / "receipt.json"]}
    assert artifacts[target][target + "/include/mixer_vm_capability.h"] == "9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6"
    assert artifacts[target][target + "/include/mixer_vm.h"] == "18c2498d0d1deae2c998ef9f4b3f811b2184c45e8169610012b05e99342385fd"
assert artifacts["host"]["host/lib/libmixer_vm_capability_experimental.a"] == "a015ff65980422dd0b9c5cad2e28741d1e5ba478e0f657dcaedf75477d553b72"
receipt = {"status": "running", "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "repositoryHeadAtRun": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "source": baseline, "sourceManifestSHA256": sha(manifest.encode()), "frozenSourceExport": str(SOURCE),
    "nativeRevision": PIN, "nativeArtifacts": artifacts, "stageRoot": str(STAGE), "commands": [],
    "scope": "Implementer Swift bridge qualification, real Wasm concrete storage and normal-trust TLS failure; separate package/single experimental archive",
    "limitations": ["No devices or platform execution; cross compile/link only", "Rust archive/system frameworks are not Swift TSan instrumented", "Logical byte/worker counters exclude allocator backing, DTOs and Task/runtime/framework lifetime", "Process allocator/RSS/CPU observations are not hard bounds, no-OOM/no-abort or reclamation proof", "Cooperative batch/VM cutoff can overrun within one admitted operation", "No verified activation, release, identity, publication or GA claim", "Independent review is separately owned; this receipt is implementer evidence"]}

def save(): (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
def run(name, command, env=None, scope=""):
    began = time.monotonic()
    result = subprocess.run(command, cwd=SOURCE, env=os.environ | (env or XENV), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    (OUT / (name + ".log")).write_bytes(result.stdout)
    record = {"name": name, "command": command, "cwd": str(SOURCE), "environment": env or XENV,
        "scope": scope, "exitCode": result.returncode, "elapsedSeconds": time.monotonic()-began,
        "log": name + ".log", "logSHA256": sha(result.stdout)}
    matches = re.findall(rb"Test run with (\d+) tests? in \d+ suites? passed", result.stdout)
    if matches: record["passedTests"] = [int(n) for n in matches]
    measurement = re.findall(rb"BRIDGE_MEASUREMENT (.+)", result.stdout)
    if measurement: record["measurements"] = [json.loads(n) for n in measurement]
    print(name + ": " + str(result.returncode), flush=True)
    return record

def flags(target):
    return ["-Xcc", "-I" + str(STAGE / target / "include"), "-Xlinker", "-L" + str(STAGE / target / "lib"), "-Xswiftc", "-warnings-as-errors"]

save()
for name, command, env in [("swift-version", ["swift", "--version"], XENV), ("xcode-version", ["xcodebuild", "-version"], XENV), ("official-swift-version", [SWIFT, "--version"], AENV), ("host-version", ["uname", "-a"], XENV), ("python-version", ["python3", "--version"], XENV)]:
    receipt["commands"].append(run(name, command, env)); save()
package = SOURCE / "experimental-capability-runtime"
loopback = ["python3", "-B", str(package / "verification/with-loopback.py")]
for mode, extra in [("debug", []), ("release", ["-c", "release"]), ("tsan", ["--sanitize", "thread"])]:
    command = loopback + ["--output", str(OUT / (mode + "-loopback")), "--", "swift", "test", "--package-path", str(package), "--scratch-path", str(SCRATCH / mode)] + extra + flags("host") + ["-Xswiftc", "-DMIXER_EXPERIMENTAL_LOCAL_TLS_TEST"]
    record = run("bridge-" + mode, command, scope="Full original real-Wasm/concrete-adapter suite with actual normal-trust loopbackTLS failure")
    record["expectedTests"] = 16; record["testCountsMatch"] = record.get("passedTests") == [16]
    receipt["commands"].append(record); save()
record = run("measurement-filtered", ["swift", "test", "--package-path", str(package), "--scratch-path", str(SCRATCH / "debug"), "--filter", "observationsSeparateLogicalPayloadFromAllocatorAndIdleCPU"] + flags("host") + ["-Xswiftc", "-DMIXER_EXPERIMENTAL_LOCAL_TLS_TEST"], scope="Separate filtered process: observational16-idle-owner allocator/RSS/CPU and timer ticks")
record["expectedTests"] = 1; record["testCountsMatch"] = record.get("passedTests") == [1]
receipt["commands"].append(record); save()
probe = str(package / "verification/CrossProbe")
jobs = [("public-host-link", ["swift", "build", "--package-path", probe, "--scratch-path", str(SCRATCH / "probe-host")] + flags("host"), XENV, "Public API consumer compile/link; no guest happy-path claim")]
for target, triple, sdk in [("ios", "arm64-apple-ios17.0", "iPhoneOS"), ("ios-simulator", "arm64-apple-ios17.0-simulator", "iPhoneSimulator")]:
    sdkpath = subprocess.check_output(["xcrun", "--sdk", sdk.lower(), "--show-sdk-path"], env=os.environ | XENV, text=True).strip()
    jobs.append((target + "-public-link", ["swift", "build", "--package-path", probe, "--scratch-path", str(SCRATCH / target), "--triple", triple, "--sdk", sdkpath] + flags(target), XENV, "Official Apple Swift public API consumer compile/link only"))
jobs.append(("android-public-link", [SWIFT, "build", "--package-path", probe, "--scratch-path", str(SCRATCH / "android"), "--swift-sdks-path", SDKS, "--swift-sdk", "aarch64-unknown-linux-android28", "--static-swift-stdlib", "-c", "release"] + flags("android") + ["-Xlinker", "-lssl", "-Xlinker", "-lcrypto", "-Xlinker", "-lz"], AENV, "Official Swift Android API28 aarch64 static public API consumer compile/link only"))
with ThreadPoolExecutor(max_workers=2) as pool:
    for record in pool.map(lambda job: run(*job), jobs): receipt["commands"].append(record); save()
receipt["linkedConsumers"] = {}
for target, folder in [("host", "probe-host"), ("ios", "ios"), ("ios-simulator", "ios-simulator"), ("android", "android")]:
    binaries = sorted({p.resolve() for p in (SCRATCH / folder).rglob("bridge-cross-probe") if p.is_file()})
    if len(binaries) != 1:
        receipt["linkedConsumers"][target] = {"error": "expected exactly one linked consumer", "paths": [str(p) for p in binaries]}
        continue
    binary = binaries[0]
    receipt["linkedConsumers"][target] = {"path": str(binary), "sha256": digest(binary), "bytes": binary.stat().st_size}
    receipt["commands"].append(run(target + "-binary-file", ["file", str(binary)], scope="Identify actual linked public Swift consumer")); save()
    if target == "host":
        receipt["commands"].append(run("public-host-run", [str(binary)], scope="Execute public consumer's expected empty-module C rejection; not a guest-effect test")); save()
receipt["sourceUnchangedDuringRun"] = inputs() == baseline
receipt["exportUnchangedDuringRun"] = all(digest(SOURCE / name) == value for name, value in baseline.items())
receipt["nativeArtifactsUnchangedDuringRun"] = all(digest(STAGE / name) == value for entries in artifacts.values() for name, value in entries.items())
receipt["completedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt["status"] = "scoped_checks_passed" if all(n["exitCode"] == 0 and n.get("testCountsMatch", True) for n in receipt["commands"]) and all("error" not in n for n in receipt["linkedConsumers"].values()) and receipt["sourceUnchangedDuringRun"] and receipt["exportUnchangedDuringRun"] and receipt["nativeArtifactsUnchangedDuringRun"] else "failed_check_preserved"
save()
raise SystemExit(0 if receipt["status"] == "scoped_checks_passed" else 1)
