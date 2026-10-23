import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
import embed
sys.path.pop(0)


class EmbeddingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.swift = os.environ.get("MIXER_SWIFT", "swift")
        configured = os.environ.get("MIXER_IDENTITY_TOOL")
        binary = subprocess.check_output([cls.swift, "build", "--package-path", str(ROOT / "runtime-identity"), "--show-bin-path"], text=True).strip()
        cls.tool = Path(configured) if configured else Path(binary) / "mixer-identity"
        if not cls.tool.is_file():
            raise RuntimeError("Build mixer-identity before running embedding tests")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mixer-embed-tests-")
        self.root = Path(self.temporary.name)
        inputs = self.root / "inputs"
        inputs.mkdir()
        (inputs / "native.a").write_bytes(b"original embedding input fixture")
        descriptor = json.loads((ROOT / "activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json").read_text())
        # A valid Wasm export spelling must stay data, never become Swift syntax.
        descriptor["execution"]["startup_export"] = '\U0001f680"); fatalError("injection") //'
        self.descriptor = self.root / "descriptor.json"
        self.descriptor.write_bytes(embed.capture.canonical(descriptor))
        bindings = {"schema": 1, "bindings": [
            {"pointer": pointer, "kind": "file", "files": [{"name": "native.a", "path": "native.a"}]}
            for pointer in sorted(embed.capture.digest_paths(descriptor))]}
        path = self.root / "bindings.json"
        path.write_bytes(embed.capture.canonical(bindings))
        self.snapshot = self.root / "snapshot"
        self.captured = embed.capture.capture(self.descriptor, path, inputs, self.snapshot, self.tool)
        self.fingerprint = self.captured["fingerprint"]

    def tearDown(self):
        self.temporary.cleanup()

    def emit(self, name="generated"):
        return embed.emit(self.snapshot, self.fingerprint, self.tool, self.root / name)

    def test_deterministic_source_and_exact_descriptor_bytes(self):
        a, b = self.emit(), self.emit("relocated")
        self.assertEqual(a, b)
        source = (self.root / "generated/MixerInstalledRuntime.swift").read_bytes()
        self.assertEqual(embed.capture.sha(source), a["source_sha256"])
        self.assertEqual(len(source), a["source_bytes"])
        self.assertEqual((self.root / "relocated/MixerInstalledRuntime.swift").read_bytes(), source)
        self.assertNotIn(b'fatalError("injection")', source)
        self.assertNotIn(str(self.root).encode(), source)
        descriptor = (self.snapshot / "descriptor.json").read_bytes()
        encoded = source.split(b'private static let descriptorBase64 = "')[1].split(b'"')[0]
        self.assertEqual(base64.b64decode(encoded, validate=True), descriptor)
        for key in ("build_attested", "complete_graph_proven", "compiled", "signed"):
            self.assertIs(a[key], False)

    def test_wrong_identity_corruption_partial_and_existing_output_reject(self):
        with self.assertRaises(embed.capture.CaptureError):
            embed.emit(self.snapshot, "0" * 64, self.tool, self.root / "wrong")
        self.assertFalse((self.root / "wrong").exists())
        self.emit()
        source = (self.root / "generated/MixerInstalledRuntime.swift").read_bytes()
        with self.assertRaises(FileExistsError): self.emit()
        self.assertEqual((self.root / "generated/MixerInstalledRuntime.swift").read_bytes(), source)
        digest = next(iter(json.loads((self.snapshot / "inputs.json").read_bytes())["objects"]))
        obj = self.snapshot / "objects" / digest
        obj.chmod(0o600); obj.write_bytes(b"corrupt")
        with self.assertRaises(embed.capture.CaptureError): self.emit("corrupt")
        self.assertFalse((self.root / "corrupt").exists())
        (self.snapshot / "inputs.json").unlink()
        with self.assertRaises(FileNotFoundError): self.emit("partial")

    def test_descriptor_is_not_reopened_after_verification(self):
        original = embed.capture.verified_descriptor
        before = (self.snapshot / "descriptor.json").read_bytes()
        def replace_after_verify(*args):
            result = original(*args)
            path = self.snapshot / "descriptor.json"
            path.unlink(); path.write_bytes(b"untrusted replacement")
            return result
        with patch.object(embed.capture, "verified_descriptor", replace_after_verify):
            receipt = self.emit()
        self.assertEqual(receipt["descriptor_sha256"], embed.capture.sha(before))
        source = (self.root / "generated/MixerInstalledRuntime.swift").read_bytes()
        self.assertIn(base64.b64encode(before), source)
        self.assertNotIn(base64.b64encode(b"untrusted replacement"), source)

    def test_sync_failure_removes_only_new_output(self):
        with patch.object(embed.capture, "sync_directory", side_effect=OSError("injected sync failure")):
            with self.assertRaises(OSError): self.emit()
        self.assertFalse((self.root / "generated").exists())
        self.assertTrue((self.snapshot / "inputs.json").is_file())

    def test_cli_uses_explicit_arguments_and_preserves_existing_output(self):
        output = self.root / "generated $(literal)"
        command = [sys.executable, str(TOOLS / "embed.py"), "--snapshot", str(self.snapshot),
                   "--expected-fingerprint", self.fingerprint, "--identity-tool", str(self.tool),
                   "--output", str(output)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["fingerprint"], self.fingerprint)
        before = (output / "MixerInstalledRuntime.swift").read_bytes()
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual((output / "MixerInstalledRuntime.swift").read_bytes(), before)

    def test_compiled_consumer_recovers_policy_without_snapshot_and_rejects_mismatch(self):
        self.emit()
        package = self.root / "consumer"
        sources = package / "Sources/Consumer"
        sources.mkdir(parents=True)
        # JSON quoted paths use no shell; escaping is also valid in Swift strings
        # for the ASCII temporary/repository paths used by this host test.
        package_path = json.dumps(str(ROOT / "runtime-identity"))
        (package / "Package.swift").write_text('''// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "EmbeddedConsumer", platforms: [.macOS(.v14)],
    dependencies: [.package(path: ''' + package_path + ''')],
    targets: [.executableTarget(name: "Consumer", dependencies: [
        .product(name: "MixerRuntimeIdentity", package: "runtime-identity")])])
''')
        source = sources / "MixerInstalledRuntime.swift"
        shutil.copyfile(self.root / "generated/MixerInstalledRuntime.swift", source)
        (sources / "main.swift").write_text('''import Foundation
do {
let identity = try MixerInstalledRuntime.load()
let encoder = JSONEncoder()
encoder.outputFormatting = [.sortedKeys]
print(String(decoding: try encoder.encode(identity.installedRuntime), as: UTF8.self))
print(identity.execution.startupExport)
print(identity.execution.profile)
} catch {
    FileHandle.standardError.write(Data(String(describing: error).utf8))
    exit(3)
}
''')
        expected = json.loads(subprocess.check_output([str(self.tool), "inspect", str(self.snapshot / "descriptor.json")]))["installedRuntime"]
        descriptor = json.loads((self.snapshot / "descriptor.json").read_bytes())
        shutil.rmtree(self.snapshot)
        shutil.rmtree(self.root / "inputs")
        self.descriptor.unlink()
        command = [self.swift, "run", "--package-path", str(package), "Consumer"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=240)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(json.loads(lines[0]), expected)
        self.assertEqual(lines[1], descriptor["execution"]["startup_export"])
        self.assertEqual(lines[2], descriptor["engine"]["profile"])
        # Recompile one altered constant: compiled policy cannot silently claim
        # a different pinned fingerprint, even with a still-valid descriptor.
        source.chmod(0o600)
        changed = ("0" if self.fingerprint[0] != "0" else "1") + self.fingerprint[1:]
        source.write_text(source.read_text().replace('fingerprint = "' + self.fingerprint + '"', 'fingerprint = "' + changed + '"'))
        result = subprocess.run(command, capture_output=True, text=True, timeout=240)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fingerprintMismatch", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
