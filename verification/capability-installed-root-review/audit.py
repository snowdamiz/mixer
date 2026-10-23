#!/usr/bin/env python3
"""Read-only source/evidence audit of the reviewed material candidate."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root / "verification/capability-installed-material/2026-10-23-candidate-2/receipt.json"
receipt = json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(path, expected):
    if digest(path) != expected:
        raise SystemExit(f"mismatch: {path}")


for name, expected in receipt["source_files"].items():
    check(root / name, expected)
    check(Path(receipt["immutable_source_export"]) / name, expected)
for name, expected in receipt["native_files"].items():
    check(Path(receipt["native_copy"]) / name, expected)
for command in receipt["commands"]:
    if command["exit_code"] != command.get("expected_exit", 0):
        raise SystemExit("unexpected command result: " + command["name"])
    check(root / command["log"], command["sha256"])
check(Path(receipt["public_client"]["path"]), receipt["public_client"]["sha256"])
owner = root / "verification/capability-installed-material"
seal = json.loads((owner / "final-receipt.json").read_text())
for field in ("host_receipt", "cross_receipt", "normative_freeze", "earlier_candidate"):
    check(root / seal[field]["path"], seal[field]["sha256"])
for name, expected in seal["preserved_legacy_production_sources"].items():
    check(root / name, expected)
counts = {}
for name, field in (("qualification-source.sha256", "qualification_source_manifest_sha256"),
                    ("evidence-manifest.sha256", "evidence_manifest_sha256")):
    manifest = owner / name
    check(manifest, seal[field])
    lines = manifest.read_text().splitlines()
    for line in lines:
        expected, filename = line.split("  ", 1)
        check(root / filename, expected)
    counts[name] = len(lines)
cross = json.loads((root / seal["cross_receipt"]["path"]).read_text())
for command in cross["commands"]:
    if command["exit_code"] != 0:
        raise SystemExit("unexpected cross command result: " + command["name"])
    check(root / command["log"], command["sha256"])
for artifacts in cross["artifacts"].values():
    for artifact in artifacts:
        check(Path(artifact["path"]), artifact["sha256"])
        if Path(artifact["path"]).stat().st_size != artifact["bytes"]:
            raise SystemExit("artifact size mismatch")
print(json.dumps({"owner_receipt_sha256": digest(path),
                  "final_receipt_sha256": digest(owner / "final-receipt.json"),
                  "source_manifest_sha256": receipt["source_manifest_sha256"],
                  "current_and_export_source_files": len(receipt["source_files"]),
                  "native_export_files": len(receipt["native_files"]),
                  "commands": len(receipt["commands"]),
                  "cross_commands": len(cross["commands"]),
                  "cross_artifacts": sum(map(len, cross["artifacts"].values())),
                  "sealed_manifests": counts,
                  "result": "PASS"}, indent=2, sort_keys=True))
