import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "capture.py"
ROOT = SCRIPT.parents[2]
spec = importlib.util.spec_from_file_location("capture", SCRIPT)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A real public CLI supplies descriptor validation and canonical hashing.
        # Tests never replace it with a function that mirrors the capture code.
        configured = os.environ.get("MIXER_IDENTITY_TOOL")
        if configured:
            cls.tool = Path(configured).absolute()
        else:
            binary_path = subprocess.check_output(["swift", "build", "--package-path", str(ROOT / "runtime-identity"), "--show-bin-path"], text=True).strip()
            cls.tool = Path(binary_path) / "mixer-identity"
        if not cls.tool.is_file():
            raise RuntimeError("Build mixer-identity before running capture tests")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mixer-input-tests-")
        self.root = Path(self.temporary.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        (self.inputs / "native.a").write_bytes(b"original independently authored input\x00\xff")
        (self.inputs / "other.txt").write_bytes(b"second input\n")
        self.descriptor = json.loads((ROOT / "activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json").read_text())
        self.descriptor_path = self.root / "descriptor.json"
        self.descriptor_path.write_bytes(capture.canonical(self.descriptor))
        self.bindings = {"schema": 1, "bindings": [
            {"pointer": pointer, "kind": "file", "files": [{"name": "native.a", "path": "native.a"}]}
            for pointer in sorted(capture.digest_paths(self.descriptor))]}
        self.bindings_path = self.root / "bindings.json"

    def tearDown(self):
        self.temporary.cleanup()

    def run_capture(self, name="snapshot"):
        self.bindings_path.write_bytes(capture.canonical(self.bindings))
        return capture.capture(self.descriptor_path, self.bindings_path, self.inputs, self.root / name, self.tool)

    def verify(self, result, name="snapshot"):
        return capture.verify(self.root / name, result["fingerprint"], self.tool)

    def mutate_report(self, change):
        path = self.root / "snapshot/inputs.json"
        report = json.loads(path.read_bytes())
        change(report)
        path.chmod(0o600)
        path.write_bytes(capture.canonical(report))

    def test_real_cli_round_trip_every_digest_bound_to_copied_bytes(self):
        result = self.run_capture()
        checked = self.verify(result)
        self.assertEqual(checked["fingerprint"], result["fingerprint"])
        self.assertEqual(checked["snapshotSHA256"], result["snapshotSHA256"])
        self.assertFalse(result["buildAttested"])
        self.assertFalse(result["completeGraphProven"])
        expected = capture.sha((self.inputs / "native.a").read_bytes())
        descriptor = json.loads((self.root / "snapshot/descriptor.json").read_bytes())
        self.assertEqual(set(capture.digest_paths(descriptor).values()), {expected})
        self.assertEqual((self.root / "snapshot/objects" / expected).read_bytes(), (self.inputs / "native.a").read_bytes())
        self.assertEqual((self.root / "snapshot/objects" / expected).stat().st_mode & 0o777, 0o400)
        self.assertEqual((self.root / "snapshot").stat().st_mode & 0o777, 0o700)

    def test_snapshot_survives_source_mutation_and_relocation_changes_no_identity(self):
        first = self.run_capture("one")
        second = self.run_capture("two")
        self.assertEqual(first, second)
        (self.inputs / "native.a").write_bytes(b"different source")
        self.verify(first, "one")
        third = self.run_capture("three")
        self.assertNotEqual(first["fingerprint"], third["fingerprint"])
        self.assertNotEqual(first["snapshotSHA256"], third["snapshotSHA256"])

    def test_collection_hash_commits_names_order_sizes_and_empty_representation(self):
        self.bindings["bindings"][0].update(kind="collection", files=[])
        self.bindings["bindings"][1].update(kind="collection", files=[
            {"name": "a/native.a", "path": "native.a"}, {"name": "b/other.txt", "path": "other.txt"}])
        first = self.run_capture()
        self.verify(first)
        report = json.loads((self.root / "snapshot/inputs.json").read_bytes())
        empty = report["bindings"][0]
        self.assertEqual(empty["sha256"], capture.sha(b'{"files":[],"schema":1}\n'))
        self.bindings["bindings"][1]["files"][1]["name"] = "c/other.txt"
        changed = self.run_capture("renamed")
        self.assertNotEqual(first["fingerprint"], changed["fingerprint"])

    def test_missing_extra_duplicate_and_unknown_bindings_are_rejected(self):
        original = copy.deepcopy(self.bindings)
        variants = []
        v = copy.deepcopy(original); v["bindings"].pop(); variants.append(v)
        v = copy.deepcopy(original); v["bindings"][0] = v["bindings"][1]; variants.append(v)
        v = copy.deepcopy(original); v["bindings"][0]["pointer"] = "/execution/fuel"; variants.append(v)
        v = copy.deepcopy(original); v["bindings"][0]["ignored"] = True; variants.append(v)
        v = copy.deepcopy(original); v["schema"] = True; variants.append(v)
        for variant in variants:
            with self.subTest(variant=variant):
                self.bindings = variant
                with self.assertRaises(capture.CaptureError): self.run_capture()
                self.assertFalse((self.root / "snapshot").exists())

    def test_input_path_escapes_symlinks_directories_and_fifos_rejected(self):
        (self.inputs / "link").symlink_to(self.inputs / "native.a")
        (self.inputs / "parent-link").symlink_to(self.inputs, target_is_directory=True)
        (self.inputs / "directory").mkdir()
        os.mkfifo(self.inputs / "pipe")
        for name in ["../native.a", "/native.a", "./native.a", "x//y", "\ud800", "é", "link", "parent-link/native.a", "directory", "pipe"]:
            with self.subTest(name=name):
                self.bindings["bindings"][0]["files"][0]["path"] = name
                with self.assertRaises((capture.CaptureError, OSError)): self.run_capture()
                self.assertFalse((self.root / "snapshot").exists())

    def test_ambiguous_json_and_excess_structure_rejected(self):
        for raw in [b'{"schema":1,"schema":1,"bindings":[]}', b'\xff', b'{"a":NaN}',
                    b"[" * 18 + b"0" + b"]" * 18]:
            with self.subTest(raw=raw), self.assertRaises(capture.CaptureError): capture.decode(raw)
        bad = copy.deepcopy(self.descriptor)
        bad["execution"]["fuel"] = True
        self.descriptor_path.write_bytes(capture.canonical(bad))
        with self.assertRaises(capture.CaptureError): self.run_capture()
        self.assertFalse((self.root / "snapshot").exists())

    def test_existing_output_is_preserved(self):
        output = self.root / "snapshot"
        output.mkdir()
        (output / "user.txt").write_text("keep me")
        with self.assertRaises(FileExistsError): self.run_capture()
        self.assertEqual((output / "user.txt").read_text(), "keep me")

    def test_per_file_aggregate_and_count_boundaries(self):
        size = (self.inputs / "native.a").stat().st_size
        with patch.object(capture, "MAX_FILE_BYTES", size):
            self.run_capture("exact")
        with patch.object(capture, "MAX_FILE_BYTES", size - 1), self.assertRaises(capture.CaptureError):
            self.run_capture("large")
        self.bindings["bindings"][0]["files"][0]["path"] = "other.txt"
        total = size + (self.inputs / "other.txt").stat().st_size
        with patch.object(capture, "MAX_TOTAL_BYTES", total): self.run_capture("total-exact")
        with patch.object(capture, "MAX_TOTAL_BYTES", total - 1), self.assertRaises(capture.CaptureError):
            self.run_capture("total-large")
        with patch.object(capture, "MAX_FILES", len(self.bindings["bindings"]) - 1), self.assertRaises(capture.CaptureError):
            self.run_capture("too-many")

    def test_changed_regular_file_is_rejected_and_private_partial_output_removed(self):
        original_read = os.read
        changed = False
        def mutate(fd, size):
            nonlocal changed
            result = original_read(fd, size)
            if result and not changed:
                # Target only input bytes, not descriptor/manifest reads.
                if result.startswith(b"original independently"):
                    changed = True
                    with open(self.inputs / "native.a", "ab") as stream: stream.write(b"growth")
            return result
        with patch.object(capture.os, "read", mutate), self.assertRaises(capture.CaptureError):
            self.run_capture()
        self.assertTrue(changed)
        self.assertFalse((self.root / "snapshot").exists())

    def test_partial_capture_wrong_identity_and_corrupted_object_never_verify(self):
        result = self.run_capture()
        with self.assertRaises(capture.CaptureError):
            capture.verify(self.root / "snapshot", "0" * 64, self.tool)
        report = json.loads((self.root / "snapshot/inputs.json").read_bytes())
        digest = next(iter(report["objects"]))
        path = self.root / "snapshot/objects" / digest
        path.chmod(0o600); path.write_bytes(b"corrupt")
        with self.assertRaises(capture.CaptureError): self.verify(result)
        (self.root / "partial").mkdir()
        with self.assertRaises(FileNotFoundError):
            capture.verify(self.root / "partial", result["fingerprint"], self.tool)

    def test_manifest_cannot_hide_missing_binding_or_add_unbound_object(self):
        result = self.run_capture()
        self.mutate_report(lambda r: r["bindings"].pop())
        with self.assertRaises(capture.CaptureError): self.verify(result)
        result = self.run_capture("extra")
        snapshot = self.root / "extra"
        report_path = snapshot / "inputs.json"
        report = json.loads(report_path.read_bytes())
        digest = capture.sha(b"unbound")
        (snapshot / "objects" / digest).write_bytes(b"unbound")
        report["objects"][digest] = 7
        report_path.chmod(0o600); report_path.write_bytes(capture.canonical(report))
        with self.assertRaises(capture.CaptureError): self.verify(result, "extra")

    def test_snapshot_object_symlink_and_collection_record_tamper_rejected(self):
        self.bindings["bindings"][0].update(kind="collection", files=[{"name": "native.a", "path": "native.a"}])
        result = self.run_capture()
        self.mutate_report(lambda r: r["bindings"][0]["files"][0].update(name="renamed.a"))
        with self.assertRaises(capture.CaptureError): self.verify(result)
        result = self.run_capture("linked")
        digest = capture.sha((self.inputs / "native.a").read_bytes())
        path = self.root / "linked/objects" / digest
        path.unlink(); path.symlink_to(self.inputs / "native.a")
        with self.assertRaises(OSError): self.verify(result, "linked")

    def test_public_command_checks_exit_status_and_no_shell_interpolation(self):
        self.inputs.rename(self.root / "inputs $(never-execute)")
        self.inputs = self.root / "inputs $(never-execute)"
        self.bindings_path.write_bytes(capture.canonical(self.bindings))
        command = [os.sys.executable, str(SCRIPT), "capture", "--descriptor", str(self.descriptor_path),
                   "--bindings", str(self.bindings_path), "--input-root", str(self.inputs),
                   "--output", str(self.root / "snapshot"), "--identity-tool", str(self.tool)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.verify(output)
        duplicate = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(duplicate.returncode, 1)
        self.assertNotIn("Traceback", duplicate.stderr)


if __name__ == "__main__":
    unittest.main()
