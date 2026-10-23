#!/usr/bin/env python3
"""Read-only root audit of frozen owner inputs and retained evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(path, expected):
    if digest(path) != expected:
        raise SystemExit(f"digest mismatch: {path}")


def manifest(path, base):
    rows = path.read_text().splitlines()
    for row in rows:
        expected, name = row.split("  ", 1)
        check(base / name, expected)
    return len(rows)


reports = {}
for name, relative, source_key, local_logs in [
    ("swift_host", "verification/release-v3-swift/2026-10-23-candidate-1/receipt.json", "source_files", False),
    ("swift_cross", "verification/release-v3-swift/2026-10-23-candidate-1-cross/receipt.json", None, False),
    ("identity", "verification/runtime-identity-v2/2026-10-23-final-v2-snapshot/receipt.json", "inputs", True),
    ("go_review", "verification/release-v3-go-review/2026-10-23-final/receipt.json", "inputs", True),
]:
    path = ROOT / relative
    receipt = json.loads(path.read_text())
    if source_key:
        for file, expected in receipt[source_key].items():
            check(ROOT / file, expected)
    for command in receipt["commands"]:
        if command["exit_code"] != command.get("expected_exit", 0):
            raise SystemExit(f"unexpected command result in {relative}: {command}")
        log = command.get("log", command.get("label", "") + ".log")
        expected = command.get("sha256", command.get("log_sha256"))
        check((path.parent if local_logs else ROOT) / log, expected)
    if name == "swift_cross":
        for artifacts in receipt["artifacts"].values():
            for artifact in artifacts:
                check(Path(artifact["path"]), artifact["sha256"])
    if name == "swift_host":
        check(Path(receipt["public_client"]["path"]), receipt["public_client"]["sha256"])
    if name == "identity":
        for file, expected in receipt["artifacts"].items():
            check(path.parent / file, expected)
    reports[name] = {"receipt": relative, "sha256": digest(path),
                     "commands": len(receipt["commands"]),
                     "current_source_files": len(receipt.get(source_key, {}))}

swift = ROOT / "verification/release-v3-swift"
reports["swift_source_manifest_files"] = manifest(swift / "qualification-source.sha256", ROOT)
reports["swift_evidence_manifest_files"] = manifest(swift / "evidence-manifest.sha256", swift)
print(json.dumps(reports, indent=2, sort_keys=True))
