#!/usr/bin/env python3
"""Original adversarial probes against the actual frozen capture/embed module."""
import base64
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SOURCE = Path(os.environ["EMBED_REVIEW_SOURCE"])
TOOL = Path(os.environ["EMBED_REVIEW_TOOL"])
sys.path.insert(0, str(SOURCE / "runtime-identity/build-tools"))
import embed
sys.path.pop(0)
C = embed.capture
SEED = json.loads((SOURCE / "activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json").read_bytes())


class Review(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mixer-embedding-independent-")
        self.root = Path(self.tmp.name)
        self.inputs = self.root / "inputs"; self.inputs.mkdir()
        (self.inputs / "engine.bin").write_bytes(bytes(range(256)) * 13)
        self.raw = copy.deepcopy(SEED)
        self.raw["engine"]["profile"] = "mixer-table-memory-v3"
        self.raw["execution"].update(startup_export='😺\"; fatalError(\"executed\") //\u2028cafe\u0301',
                                     state_schema=18446744073709551615, operand_stack=71,
                                     call_depth=9, host_calls=3, fuel=51, memory_bytes=65536,
                                     startup_ms=99, max_payload_bytes=8192)
        self.descriptor = self.root / "original.json"; self.descriptor.write_bytes(C.canonical(self.raw))
        self.bindings = self.root / "bindings.json"
        self.bindings.write_bytes(C.canonical({"schema": 1, "bindings": [
            {"pointer": p, "kind": "file", "files": [{"name": "engine.bin", "path": "engine.bin"}]}
            for p in sorted(C.digest_paths(self.raw))]}))
        self.snapshot = self.root / "snapshot"
        self.captured = C.capture(self.descriptor, self.bindings, self.inputs, self.snapshot, TOOL)
        self.fingerprint = self.captured["fingerprint"]
        self.output = self.root / "generated"

    def tearDown(self): self.tmp.cleanup()
    def emit(self): return embed.emit(self.snapshot, self.fingerprint, TOOL, self.output)
    def stored(self): return (self.snapshot / "descriptor.json").read_bytes()
    def write_descriptor(self, value):
        path = self.snapshot / "descriptor.json"; path.chmod(0o600); path.write_bytes(value)
        report = self.snapshot / "inputs.json"; report.chmod(0o600)
        contents = json.loads(report.read_bytes()); contents["descriptor_sha256"] = C.sha(value)
        report.write_bytes(C.canonical(contents))
    def emitted_bytes(self):
        text = (self.output / "MixerInstalledRuntime.swift").read_bytes()
        return base64.b64decode(text.split(b'private static let descriptorBase64 = "', 1)[1].split(b'"', 1)[0], validate=True)

    def test_raw_bytes_are_preserved_including_noncanonical_whitespace(self):
        raw = b" \n\t" + self.stored() + b"\r\n "
        self.write_descriptor(raw)
        result = self.emit()
        self.assertEqual(self.emitted_bytes(), raw)
        self.assertEqual(result["descriptor_sha256"], C.sha(raw))
        self.assertEqual(result["source_sha256"], C.sha((self.output / "MixerInstalledRuntime.swift").read_bytes()))
        self.assertFalse(any(result[k] for k in ["compiled", "signed", "complete_graph_proven", "build_attested"]))

    def test_descriptor_replaced_during_trusted_final_inspect_cannot_retarget_source(self):
        original = self.stored(); real = C.inspect
        def swap(tool, path):
            result = real(tool, path)
            self.write_descriptor(b'{"replacement":true}\n')
            return result
        with patch.object(C, "inspect", swap): self.emit()
        self.assertEqual(self.emitted_bytes(), original)

    def test_entire_snapshot_path_replaced_after_root_open_cannot_retarget_source(self):
        original = self.stored(); real = C.open_root; done = False
        def swap(path):
            nonlocal done
            fd = real(path)
            if Path(path) == self.snapshot and not done:
                done = True
                self.snapshot.rename(self.root / "pinned-original")
                self.snapshot.mkdir()
                (self.snapshot / "descriptor.json").write_bytes(b"replacement path")
            return fd
        with patch.object(C, "open_root", swap): self.emit()
        self.assertTrue(done); self.assertEqual(self.emitted_bytes(), original)

    def test_postverification_bytes_are_not_reopened_even_if_original_root_is_removed(self):
        original = self.stored(); real = C.verified_descriptor
        def remove(*args):
            result = real(*args); shutil.rmtree(self.snapshot); return result
        with patch.object(C, "verified_descriptor", remove): self.emit()
        self.assertEqual(self.emitted_bytes(), original)

    def test_invalid_and_policy_edited_descriptors_fail_before_output(self):
        for value in [b"\xff", b'{"schema":1,"schema":1}', b'{"schema":null}',
                      self.stored().replace(b'"host_calls":3', b'"host_calls":4')]:
            with self.subTest(value=value[:40]):
                self.write_descriptor(value)
                with self.assertRaises(C.CaptureError): self.emit()
                self.assertFalse(self.output.exists())

    def test_pinned_fingerprint_cannot_be_taken_from_edited_snapshot(self):
        wrong = "0" * 64
        with self.assertRaises(C.CaptureError): embed.emit(self.snapshot, wrong, TOOL, self.output)
        self.assertFalse(self.output.exists())
        for value in [None, 1, "A" * 64, self.fingerprint + "\n", '";fatalError()//']:
            with self.subTest(value=value), self.assertRaises(C.CaptureError):
                embed.emit(self.snapshot, value, TOOL, self.output)

    def test_exact_descriptor_limit_accepts_and_limit_plus_one_rejects(self):
        exact = self.stored() + b" " * (C.MAX_DESCRIPTOR - len(self.stored()))
        self.write_descriptor(exact); result = self.emit()
        self.assertEqual(len(self.emitted_bytes()), 131072)
        self.assertGreater(result["source_bytes"], 174762)
        shutil.rmtree(self.output); self.write_descriptor(exact + b" ")
        with self.assertRaises(C.CaptureError): self.emit()
        self.assertFalse(self.output.exists())

    def test_existing_outputs_and_symlink_targets_survive(self):
        target = self.root / "witness"; target.mkdir(); witness = target / "private"; witness.write_bytes(b"private witness")
        for kind in ["file", "directory", "symlink", "dangling"]:
            with self.subTest(kind=kind):
                if kind == "file": self.output.write_bytes(b"original file")
                elif kind == "directory": self.output.mkdir(); (self.output / "user").write_bytes(b"original directory")
                else: self.output.symlink_to(target if kind == "symlink" else self.root / "absent", target_is_directory=True)
                with self.assertRaises(FileExistsError): self.emit()
                self.assertEqual(witness.read_bytes(), b"private witness")
                if self.output.is_symlink() or self.output.is_file(): self.output.unlink()
                else:
                    self.assertEqual((self.output / "user").read_bytes(), b"original directory")
                    shutil.rmtree(self.output)

    def test_write_and_sync_failures_remove_only_new_private_output(self):
        real = C.write_new
        for failing_name in ["MixerInstalledRuntime.swift", "embedding.json"]:
            def fail(path, data):
                if Path(path).name == failing_name: raise OSError("independent injected write failure")
                return real(path, data)
            with self.subTest(name=failing_name), patch.object(C, "write_new", fail):
                with self.assertRaises(OSError): self.emit()
                self.assertFalse(self.output.exists()); self.assertTrue((self.snapshot / "inputs.json").is_file())
        real_sync = C.sync_directory
        for failing_path in [self.output, self.output.parent]:
            def fail_sync(path):
                if Path(path) == failing_path: raise OSError("independent injected sync failure")
                return real_sync(path)
            with self.subTest(path=failing_path), patch.object(C, "sync_directory", fail_sync):
                with self.assertRaises(OSError): self.emit()
                self.assertFalse(self.output.exists()); self.assertTrue((self.snapshot / "inputs.json").is_file())

    def test_partial_snapshot_and_symlinked_descriptor_reject(self):
        original = self.snapshot / "descriptor.json"
        witness = self.root / "witness.json"; witness.write_bytes(self.stored())
        original.unlink(); original.symlink_to(witness)
        with self.assertRaises(OSError): self.emit()
        self.assertFalse(self.output.exists())
        original.unlink(); (self.snapshot / "inputs.json").unlink()
        with self.assertRaises(FileNotFoundError): self.emit()
        self.assertFalse(self.output.exists())

    def test_cli_quoted_names_and_errors_are_data_only(self):
        output = self.root / 'source $(touch witness) " \' `literal`'
        command = [sys.executable, "-B", str(SOURCE / "runtime-identity/build-tools/embed.py"),
                   "--snapshot", str(self.snapshot), "--expected-fingerprint", self.fingerprint,
                   "--identity-tool", str(TOOL), "--output", str(output)]
        result = subprocess.run(command, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["fingerprint"], self.fingerprint)
        before = (output / "MixerInstalledRuntime.swift").read_bytes()
        result = subprocess.run(command, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 1); self.assertNotIn(b"Traceback", result.stderr)
        self.assertEqual((output / "MixerInstalledRuntime.swift").read_bytes(), before)
        self.assertFalse((self.root / "witness").exists())


if __name__ == "__main__": unittest.main(verbosity=2)
