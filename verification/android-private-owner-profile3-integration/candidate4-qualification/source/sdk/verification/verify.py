#!/usr/bin/env python3
"""Reproduce SDK host verification and optional unsigned iOS cross-compilation."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import platform
import subprocess
import sys


SDK = pathlib.Path(__file__).resolve().parents[1]
ROOT = SDK.parent
OUTPUT = SDK / "verification" / "current"


def timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def source_receipt() -> dict:
    paths = [SDK / "Package.swift", pathlib.Path(__file__).resolve(), ROOT / "contracts" / "ui-v1.json"]
    paths += sorted((SDK / "Sources").rglob("*.swift"))
    paths += sorted((SDK / "Tests").rglob("*.swift"))
    digest = hashlib.sha256()
    files = []
    for path in sorted(paths):
        data = path.read_bytes()
        relative = path.relative_to(ROOT).as_posix()
        digest.update(relative.encode() + b"\0" + str(len(data)).encode() + b"\0" + data)
        files.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    return {"algorithm": "sha256(relative_path + NUL + decimal_byte_length + NUL + bytes), sorted by path",
            "digest": digest.hexdigest(), "files": files}


def output_of(command: list[str]) -> str:
    process = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return process.stdout.strip()


def execute(name: str, command: list[str], scope: str) -> dict:
    started = timestamp()
    process = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUTPUT / f"{name}.log").write_text(process.stdout)
    print(f"{name}: exit {process.returncode}; output sdk/verification/current/{name}.log", flush=True)
    return {"name": name, "command": command, "cwd": str(ROOT), "startedAt": started, "endedAt": timestamp(),
            "exitCode": process.returncode, "output": f"sdk/verification/current/{name}.log", "scope": scope}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ios", action="store_true", help="also compile the libraries for unsigned iOS arm64")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = source_receipt()
    revision = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    receipt = {
        "schemaVersion": 1, "createdAt": timestamp(),
        "implementationAgent": {"model": "gpt-6.1-sol", "reasoningEffort": "xhigh"},
        "verificationOwner": "implementation lane; independent verification remains required",
        "sourceRevisionBeforeRun": revision.stdout.strip() if revision.returncode == 0 else None,
        "source": source,
        "toolchain": {"swift": output_of(["swift", "--version"]), "xcode": output_of(["xcodebuild", "-version"]),
                      "python": sys.version, "host": platform.platform()},
        "commands": [],
        "excludedEvidence": ["physical iOS", "physical Android", "Swift guest execution", "native/guest parity",
                             "signing", "store distribution", "published package consumer", "GA gate approval"],
    }
    receipt["commands"].append(execute("swift-test", ["swift", "test", "--package-path", "sdk"],
        "macOS Swift Testing suites and native SwiftUI ImageRenderer smoke only"))
    if args.ios:
        sdk_path = output_of(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"])
        receipt["commands"].append(execute("ios-build", ["swift", "build", "--package-path", "sdk", "--triple",
            "arm64-apple-ios17.0", "--sdk", sdk_path, "--scratch-path", "sdk/.build/ios"],
            "unsigned iOS arm64 library cross-compilation only; no linking app, simulator or device run"))
    receipt["sourceUnchangedDuringRun"] = source_receipt() == source
    receipt["passed"] = receipt["sourceUnchangedDuringRun"] and all(item["exitCode"] == 0 for item in receipt["commands"])
    (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"source digest: {source['digest']}")
    print(f"passed scoped commands: {receipt['passed']}; receipt sdk/verification/current/receipt.json")
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
