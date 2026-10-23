#!/usr/bin/env python3
"""Read-only independent verification of the sealed owner service candidate."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
owner = root / "verification/release-v3-service/2026-10-23-candidate-2"
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
r = json.loads((owner / "receipt.json").read_text())
source = Path(r["frozenSourceExport"])
for name, expected in r["source"].items():
    assert digest(root / name) == expected and digest(source / name) == expected, name
for command in r["commands"]:
    assert command["exitCode"] == 0
    assert digest(owner / (command["name"] + ".log")) == command["logSHA256"]
for name, info in r["subreceipts"].items():
    path = owner / name / "receipt.json"
    assert digest(path) == info["sha256"]
    sub = json.loads(path.read_text()); assert sub["status"] == "passed"
    for command in sub["commands"]:
        expected = 1 if name == "old-binary" and command["name"] == "old-rejection" else 0
        assert command["exitCode"] == expected, (name, command["name"])
        if "logSHA256" in command:
            log = path.parent / (command["name"] + ".log")
            assert digest(log) == command["logSHA256"]
            if expected == 1: assert "unknown durable store schema" in log.read_text()
        for stream in ["stdout", "stderr"]:
            value = command.get(stream)
            if isinstance(value, dict):
                assert digest(path.parent / value["path"]) == value["sha256"]
print(json.dumps({"result": "PASS", "owner_receipt_sha256": digest(owner / "receipt.json"),
    "source_manifest_sha256": r["sourceManifestSHA256"], "current_and_export_source_files": len(r["source"]),
    "commands": len(r["commands"]), "subreceipts": r["subreceipts"]}, indent=2))
