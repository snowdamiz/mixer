#!/usr/bin/env python3
"""Read-only binding check for the reviewed validation candidate and probes."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root / "experimental-capability-runtime/verification"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(path, expected):
    if digest(path) != expected:
        raise SystemExit(f"mismatch: {path}")


result = {}
for label in ["2026-10-23-validation-candidate-1", "2026-10-23-validation-probes-1", "2026-10-23-validation-public-1"]:
    directory = base / label
    receipt = json.loads((directory / "receipt.json").read_text())
    source = receipt.get("source", receipt.get("baseSource"))
    for path, expected in source.items():
        check(root / path, expected)
    commands = receipt.get("commands", [receipt])
    for command in commands:
        if command["exitCode"] != 0:
            raise SystemExit(f"failed command: {label}")
        check(directory / command.get("log", "public-debug.log"), command["logSHA256"])
    for artifact in receipt.get("linkedConsumers", {}).values():
        check(Path(artifact["path"]), artifact["sha256"])
    if "derivedSource" in receipt:
        for path, expected in receipt["derivedSource"].items():
            check(Path(receipt["sourceExport"]) / path, expected)
    if "stageRoot" in receipt:
        for artifacts in receipt["nativeArtifacts"].values():
            for path, expected in artifacts.items():
                check(Path(receipt["stageRoot"]) / path, expected)
    if "nativeArtifact" in receipt:
        check(Path(receipt["nativeArtifact"]["path"]), receipt["nativeArtifact"]["sha256"])
    result[label] = {"receipt_sha256": digest(directory / "receipt.json"),
                     "current_inputs": len(source), "successful_commands": len(commands)}
print(json.dumps(result, indent=2, sort_keys=True))
