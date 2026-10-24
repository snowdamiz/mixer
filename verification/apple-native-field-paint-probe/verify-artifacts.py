#!/usr/bin/env python3
"""Offline integrity check; does not grant native operation or release support."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
seal = json.loads((ROOT / "seal.json").read_text())
for name, expected in seal["files"].items():
    path = ROOT / name
    assert path.is_file(), f"missing artifact: {name}"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, f"changed artifact: {name}"
for name, expected in seal["ownedDocumentation"].items():
    assert hashlib.sha256((REPO/name).read_bytes()).hexdigest() == expected, f"changed probe documentation: {name}"
locked = json.loads((ROOT / "evidence/source-lock.json").read_text())
for name, expected in locked["inputSHA256"].items():
    if name.startswith("verification/apple-native-field-paint-probe/"):
        assert hashlib.sha256((REPO/name).read_bytes()).hexdigest() == expected, f"changed native-run input: {name}"
observations = json.loads((ROOT / "evidence/observations.json").read_text())
assert len(observations) == 25
assert all(item["after"]["os"] == "26.5" for item in observations)
assert all(item["after"]["fieldIdentity"] == observations[0]["after"]["fieldIdentity"] for item in observations)
receipt = json.loads((ROOT / "evidence/receipt.json").read_text())
assert not receipt["iOS17RuntimeQualified"] and not receipt["physicalDeviceTested"]
assert not receipt["completeNativeFieldSupport"] and not receipt["gaAcceptance"]
print(f"PASS: {len(seal['files'])} sealed artifacts; 25 iOS26.5 simulator stages; scope remains bounded feasibility")
