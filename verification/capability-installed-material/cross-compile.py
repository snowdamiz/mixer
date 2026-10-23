#!/usr/bin/env python3
"""Compile frozen material module/objects for official mobile SDKs; no app/device run."""
import concurrent.futures
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE_PIN = "cd9f855902ee2221516c8aafcdd88ddbab138f57cddc2c6489361e9f2869abd9"
RECEIPT_PIN = "0c3b8df6a04fabda6ad0f8301832d7679dc216c1a5a4bf23983ebb332f29db31"
OFFICIAL = "/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def require(value, message):
    if not value: raise RuntimeError(message)


def main():
    out = HERE / "2026-10-23-candidate-2-cross"; out.mkdir(exist_ok=False)
    raw = (HERE / "2026-10-23-candidate-2/receipt.json").read_bytes()
    require(sha(raw) == RECEIPT_PIN, "exact final host receipt")
    host = json.loads(raw); require(host["source_manifest_sha256"] == SOURCE_PIN, "final source pin")
    source = Path(host["immutable_source_export"]); work = source.parent
    def unchanged():
        for relative, digest in host["source_files"].items():
            require(sha((ROOT / relative).read_bytes()) == digest, "live source " + relative)
            require(sha((source / relative).read_bytes()) == digest, "export source " + relative)
    unchanged()
    receipt = dict(status="running", started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), source_manifest_sha256=SOURCE_PIN,
        host_receipt_sha256=RECEIPT_PIN, immutable_source_export=str(source), driver_sha256=sha(Path(__file__).read_bytes()), commands=[],
        scope="Official iOS and Android target module/object compilation only, no final native application link, mobile execution, physical lifecycle, graph attestation, signing or publication")
    def save(): (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    apple = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
    android = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode_26.6.app/Contents/Developer")
    def run(name, argv, env):
        start = time.monotonic()
        try:
            result = subprocess.run(argv, cwd=source, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=360)
            raw, code = result.stdout, result.returncode
        except subprocess.TimeoutExpired as error: raw, code = (error.stdout or b"") + b"\ncross compile timeout\n", 124
        log = out / (name + ".log"); log.write_bytes(raw)
        return dict(name=name, argv=argv, cwd=str(source), environment={"DEVELOPER_DIR":env["DEVELOPER_DIR"]}, exit_code=code,
                    elapsed_seconds=time.monotonic() - start, log=str(log.relative_to(ROOT)), sha256=sha(raw))
    save()
    for job in [("official-swift-version", [OFFICIAL, "--version"], android), ("iphoneos-sdk", ["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], apple),
                ("android-sdk-list", [OFFICIAL, "sdk", "list", "--swift-sdks-path", "/Users/andreyyurlov/.swiftpm/swift-sdks"], android)]:
        row = run(*job); receipt["commands"].append(row); save(); require(row["exit_code"] == 0, row["name"])
    sdk = (out / "iphoneos-sdk.log").read_text().strip()
    native = Path(host["native_copy"])
    flags = ["-Xswiftc", "-warnings-as-errors", "-Xcc", "-I" + str(native / "include")]
    package = str(source / "capability-activation")
    jobs = [
        ("ios-module", ["swift", "build", "--package-path", package, "--scratch-path", str(work / "ios-module"), "--triple", "arm64-apple-ios17.0", "--sdk", sdk,
                         "-c", "release", "--target", "MixerCapabilityActivation"] + flags, apple),
        ("android-module", [OFFICIAL, "build", "--package-path", package, "--scratch-path", str(work / "android-module"),
                             "--swift-sdks-path", "/Users/andreyyurlov/.swiftpm/swift-sdks", "--swift-sdk", "aarch64-unknown-linux-android28", "-c", "release", "--target", "MixerCapabilityActivation"] + flags, android),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for row in pool.map(lambda job: run(*job), jobs):
            receipt["commands"].append(row); save(); print(row["name"] + ": " + str(row["exit_code"]), flush=True)
    unchanged(); artifacts = {}
    for platform in ["ios", "android"]:
        folder = work / (platform + "-module")
        modules = sorted(p for p in folder.rglob("*.swiftmodule") if p.is_file() and (p.parent.name == "MixerCapabilityActivation.swiftmodule" or p.name == "MixerCapabilityActivation.swiftmodule"))
        objects = sorted(p for p in folder.rglob("*.o") if p.name in ["MixerCapabilityActivation.o", "MaterialJSON.swift.o", "MaterialJSON.o", "InstalledCapabilityExecution.swift.o", "InstalledCapabilityExecution.o"])
        require(modules and objects, platform + " actual target module/object output")
        artifacts[platform] = [dict(path=str(p), sha256=sha(p.read_bytes()), bytes=p.stat().st_size) for p in sorted(set(modules + objects))]
    receipt.update(artifacts=artifacts, source_and_export_unchanged=True, completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   status="official SDK target module/object compilation passed" if all(row["exit_code"] == 0 for row in receipt["commands"]) else "failed cross check preserved")
    save(); require(receipt["status"].endswith("passed"), "cross compile failed")
    print(json.dumps({"receipt_sha256":sha((out / "receipt.json").read_bytes()), "status":receipt["status"]}))


if __name__ == "__main__": main()
