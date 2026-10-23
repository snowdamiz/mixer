#!/usr/bin/env python3
"""Original read-only native-preimage helper tests, independent of generator imports."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "capabilities/tools/export-native-preimage.py"
spec = importlib.util.spec_from_file_location("owned_native_preimage_export", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class NativePreimageTests(unittest.TestCase):
    def test_exact_real_preimage_and_repeat_without_source_writes(self):
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for directory in ["sdk/Sources/MixerCapabilities", "capabilities/java/mixer/capabilities", "capabilities/schema"] for p in (ROOT / directory).rglob("*") if p.is_file()}
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "preimage.json"
            for _ in range(2):
                result = subprocess.run([sys.executable, str(HELPER), "--check", "--output", str(output)], capture_output=True, check=True)
                report = json.loads(result.stdout)
                self.assertEqual(report["nativeImplementationSHA256"], "4fcc770e62d39b415e657ce03aa11fa7fb83ee8bfe1a99567716e9b4372d1c59")
                self.assertEqual(report["sources"], 17)
                self.assertFalse(report["finalLF"])
                expected = (ROOT / "capability-activation/Tests/MixerCapabilityActivationTests/Fixtures/native-preimage.json").read_bytes()
                self.assertEqual(output.read_bytes(), expected)
                self.assertFalse(expected.endswith(b"\n"))
                self.assertEqual(hashlib.sha256(expected).hexdigest(), report["nativeImplementationSHA256"])
        self.assertEqual(before, {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before})

    def test_preimage_normalization_exclusions_and_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ["sdk/Sources/MixerCapabilities", "capabilities/java/mixer/capabilities", "capabilities/schema"]:
                shutil.copytree(ROOT / directory, root / directory)
            baseline = helper.preimage(root)
            self.assertEqual(baseline, helper.preimage(ROOT))
            records = json.loads(baseline)
            self.assertEqual([r["path"] for r in records], sorted(r["path"] for r in records))
            for excluded in ["sdk/Sources/MixerCapabilities/GeneratedIdentity.swift", "capabilities/java/mixer/capabilities/CapabilityNativeIdentity.java", "capabilities/java/mixer/capabilities/CapabilityProbe.java"]:
                (root / excluded).write_text("excluded fixture mutation\n")
                self.assertEqual(baseline, helper.preimage(root))
            schema = root / "capabilities/schema/v1.json"
            schema.write_text(json.dumps(json.loads(schema.read_text()), indent=3) + "\n")
            self.assertEqual(baseline, helper.preimage(root))
            source = root / "sdk/Sources/MixerCapabilities/Host.swift"
            source.write_bytes(source.read_bytes().replace(b"\n", b"\r\n"))
            self.assertEqual(baseline, helper.preimage(root))
            source.write_text(source.read_text() + "// copied-input mutation\n")
            self.assertNotEqual(baseline, helper.preimage(root))

    def test_production_export_location_refused_without_write(self):
        target = ROOT / "sdk/forbidden-native-preimage-test.json"
        self.assertFalse(target.exists())
        result = subprocess.run([sys.executable, str(HELPER), "--output", str(target)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"refusing to export", result.stderr)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
