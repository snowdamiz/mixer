#!/usr/bin/env python3
"""Executable integrity/evidence checks, not a visual parity or GA decision."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
subprocess.run(["python3", str(ROOT / "scripts/freeze-inputs.py")], check=True)
lock = json.loads((ROOT / "input-lock.json").read_text())
assert hashlib.sha256(json.dumps(lock["sourceFiles"], sort_keys=True, separators=(",", ":")).encode()).hexdigest() == lock["sourceCollectionSHA256"]
fixtures = json.loads((ROOT / "fixture-manifest.json").read_text())
for name, item in fixtures.items():
    assert hashlib.sha256((ROOT / item["documentPath"]).read_bytes()).hexdigest() == item["sha256"]
captures = json.loads((ROOT / "capture-manifest.json").read_text())["captures"]
assert len(captures) == 8
observed_sizes = []
for capture in captures:
    directory = ROOT / "captures" / capture["name"]
    for entry in capture["files"]:
        path = directory / entry["path"]
        assert path.stat().st_size == entry["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
    document = (directory / "rendered-document.json").read_bytes()
    assert document == (ROOT / fixtures[capture["fixture"]]["documentPath"]).read_bytes()
    validation = json.loads((directory / "fixture-validation.json").read_text())
    assert validation["allTenKindsValidatedByFrozenSDK"] is True
    assert all(f["hostSnapshotEqualsSourceDocument"] for f in validation["fixtures"])
    environment = json.loads((directory / "environment.json").read_text())
    assert environment["hostSnapshotEqualsSourceDocument"] is True
    assert environment["swiftUIColorScheme"] == capture["requestedAppearance"]
    assert environment["windowTraitUserInterfaceStyle"] == capture["requestedAppearance"]
    assert environment["swiftUILayoutDirection"] == capture["requestedDirection"]
    assert environment["interfaceOrientation"] == 1  # observed portrait
    assert environment["swiftUIDynamicTypeSize"] == ("accessibility1" if capture["fixture"] == "rtl-large" else "large")
    image = (directory / "screenshot.png").read_bytes()
    assert image[:8] == b"\x89PNG\r\n\x1a\n" and image[12:16] == b"IHDR"
    width, height = struct.unpack(">II", image[16:24])
    assert width == environment["screenNativeBoundsPixels"]["width"]
    assert height == environment["screenNativeBoundsPixels"]["height"]
    observed_sizes.append(dict(capture=capture["name"], widthPixels=width, heightPixels=height))
for fixture in fixtures:
    light = ROOT / "captures" / (fixture + "-light/rendered-document.json")
    dark = ROOT / "captures" / (fixture + "-dark/rendered-document.json")
    assert light.read_bytes() == dark.read_bytes()
commands = json.loads((ROOT / "commands.json").read_text())
assert all(c["exitCode"] == 0 for c in commands)
build_log = (ROOT / "logs/build.log").read_text()
assert "** BUILD SUCCEEDED **" in build_log
assert str(ROOT / "frozen/sdk/Sources/MixerApple/MixerNativeView.swift") in build_log
assert "AppearanceDefaultV1.swift" not in build_log
print(json.dumps(dict(result="PASS", scope="input/fixture/native environment/capture integrity only",
    frozenSourceFiles=len(lock["sourceFiles"]), captures=observed_sizes,
    limitation="No physical-device parity, node metrics, accessibility interaction, signed health or GA approval."), indent=2))
