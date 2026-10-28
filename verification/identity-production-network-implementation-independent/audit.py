#!/usr/bin/env python3
"""Offline source and focused failure review. Never executes a child or product."""
from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANONICAL = (
    "hosted/scripts/test-identity-network.py",
    "hosted/scripts/test_identity_network_collector.py",
    ".github/workflows/identity-network.yml",
    "docs/hosted-identity-production-network-ci-contract.md",
    "THIRD_PARTY.yml",
)
ROOT_SELECTED = {
    "hosted/scripts/test-identity-network.py": (None, "3162131bddc05d25755f5c3e8f494f86715e8b997ecc2b7205f7e50aac22c5ca"),
    "hosted/scripts/test_identity_network_collector.py": (50119, "e27b8f53d68b6ac3525d768224af7739aae87cadc78b2997f5409620a3561f1a"),
    ".github/workflows/identity-network.yml": (2067, "e38b59d175e8c7297bfb5b576e61ba73c291ef827ce668d63b0f042b81114ef2"),
    "docs/hosted-identity-production-network-ci-contract.md": (5797, "f1b605f1945966c37cc815867b785a9d5af3a40981da3a69e5cf51376c07e3ed"),
    "THIRD_PARTY.yml": (25171, "ccff4019df3e8b70c744d937c8687fd4b6df217001401cda16146b9ea5654bc3"),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def entry(data):
    return {"bytes": len(data), "sha256": digest(data)}


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def focused_cases(controls):
    subject = controls.collector

    class FocusedReview(unittest.TestCase):
        def make_subject(self, directory, fake, cls=None):
            root = Path(directory) / "repository"
            root.mkdir()
            with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "100", "GITHUB_RUN_ATTEMPT": "1"}):
                return (cls or subject.Collector)(root, Path(directory) / "evidence", "a" * 40, runner=fake)

        def assert_sticky_cleanup(self, instance, fake, record):
            self.assertEqual("identity_lost", record.state)
            before = len(fake.calls)
            self.assertFalse(instance.cleanup())
            self.assertEqual(before, len(fake.calls))

        def test_denied_copy_marks_unknown_and_never_retries_cleanup(self):
            class DeniedCopy(controls.FakeDocker):
                def __call__(self, argv, timeout, input_bytes):
                    if argv[:2] == ["docker", "cp"]:
                        self.calls.append(list(argv))
                        return 1, b"", b"permission denied"
                    return super().__call__(argv, timeout, input_bytes)
            fake = DeniedCopy()
            with tempfile.TemporaryDirectory(prefix="review-copy-") as directory:
                instance = self.make_subject(directory, fake)
                record = instance.create("test")
                with self.assertRaises(subject.CollectorError):
                    instance.copy_in(record, b"a bounded synthetic archive")
                self.assert_sticky_cleanup(instance, fake, record)

        def test_denied_check_false_exec_never_becomes_readiness_retry(self):
            fake = controls.FakeDocker()
            with tempfile.TemporaryDirectory(prefix="review-ready-") as directory:
                instance = self.make_subject(directory, fake)
                record = instance.create("test")
                fake.deny_exec = True
                with self.assertRaises(subject.CollectorError):
                    instance.execute(record, ["fixture-readiness"], check=False)
                self.assert_sticky_cleanup(instance, fake, record)

        def test_denied_log_capture_never_proceeds_to_remove(self):
            class DeniedLogs(controls.FakeDocker):
                def __call__(self, argv, timeout, input_bytes):
                    if argv[:2] == ["docker", "logs"]:
                        self.calls.append(list(argv))
                        return 1, b"", b"operation not permitted"
                    return super().__call__(argv, timeout, input_bytes)
            fake = DeniedLogs()
            with tempfile.TemporaryDirectory(prefix="review-logs-") as directory:
                instance = self.make_subject(directory, fake)
                record = instance.create("test")
                self.assertFalse(instance.cleanup())
                self.assertFalse(any(argv[:2] == ["docker", "rm"] for argv in fake.calls))
                self.assert_sticky_cleanup(instance, fake, record)

        def oom_subject(self, directory, fake):
            class LateOOM(subject.Collector):
                def collect(self):
                    record = self.create("test")
                    fake.documents[record.cid]["State"]["OOMKilled"] = True
            return self.make_subject(directory, fake, LateOOM)

        def test_terminal_oom_refuses_qualification_and_still_removes_exact_cid(self):
            fake = controls.FakeDocker()
            with tempfile.TemporaryDirectory(prefix="review-oom-") as directory:
                instance = self.oom_subject(directory, fake)
                self.assertEqual(1, instance.run())
                self.assertEqual("FAILED-terminal-runtime-state", instance.state["status"])
                self.assertEqual({}, fake.documents)
                self.assertTrue(all(row.state == "removed" for row in instance.registry.records))
                self.assertEqual("verified-exact-created-IDs-absent", instance.state["cleanup"]["status"])
                self.assertEqual("terminal OOMKilled", instance.state["qualification_failures"][0]["failure"])

        def test_finalizer_preserves_terminal_oom_failure_after_verified_cleanup(self):
            fake = controls.FakeDocker()
            with tempfile.TemporaryDirectory(prefix="review-finalizer-") as directory:
                instance = self.oom_subject(directory, fake)
                self.assertEqual(1, instance.run())
                # Simulate a saved outcome before its terminal-failure downgrade.
                instance.state["status"] = "two-methods-passed-pending-owned-cleanup-and-independent-acceptance"
                instance.persist()
                identity = {"GITHUB_RUN_ID": instance.run_id, "GITHUB_RUN_ATTEMPT": instance.attempt, "GITHUB_SHA": instance.sha}
                with mock.patch.dict(os.environ, identity):
                    self.assertEqual(0, subject.finalize(instance.root, instance.output))
                final = json.loads((instance.output / "state.json").read_bytes())
                self.assertEqual("FAILED-terminal-runtime-state", final["status"])
                self.assertEqual("verified-exact-created-IDs-absent", final["cleanup"]["status"])

        def test_cancelled_collect_return_cannot_become_success(self):
            class Cancelled(subject.Collector):
                def collect(self):
                    self.cancelled = True
            with tempfile.TemporaryDirectory(prefix="review-cancel-") as directory:
                instance = self.make_subject(directory, controls.FakeDocker(), Cancelled)
                self.assertEqual(1, instance.run())
                self.assertEqual("FAILED-cancelled", instance.state["status"])
                self.assertTrue(instance.state["primary_outcome_frozen"])

    return unittest.defaultTestLoader.loadTestsFromTestCase(FocusedReview)


def main():
    started = time.monotonic()
    signal.alarm(50)
    selected = {path: (ROOT / path).read_bytes() for path in CANONICAL}
    for path, (size, sha) in ROOT_SELECTED.items():
        assert (size is None or len(selected[path]) == size) and digest(selected[path]) == sha, path
    bindings = {path: entry(data) for path, data in selected.items()}
    snapshot = HERE / "inputs"
    for path, data in selected.items():
        target = snapshot / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == data, "review freeze changed: " + path
        else:
            target.write_bytes(data)
    tree = ast.parse(selected[CANONICAL[0]], filename=CANONICAL[0])
    ast.parse(selected[CANONICAL[1]], filename=CANONICAL[1])
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"FROZEN_MANIFEST", "FROZEN_PRODUCT_DIGEST", "FROZEN_LOCK_SHA256", "CONTRACT_SHA256", "CONTRACT_PACKET"}:
                    constants[target.id] = ast.literal_eval(node.value)
    packet_root = ROOT / "verification/identity-production-network-contract"
    packet = json.loads((packet_root / "packet-manifest.json").read_bytes())
    assert canonical(packet["files"]) == packet["tree_digest_sha256"] == constants["CONTRACT_PACKET"]
    for path, expected in packet["files"].items():
        assert entry((packet_root / path).read_bytes()) == expected, path
    manifest = json.loads((packet_root / "inputs/product-source-manifest.json").read_bytes())["files"]
    assert constants["FROZEN_MANIFEST"] == manifest
    assert len(manifest) == 177 and canonical(manifest) == constants["FROZEN_PRODUCT_DIGEST"]
    assert manifest["hosted/mix.lock"]["sha256"] == constants["FROZEN_LOCK_SHA256"]
    assert digest((packet_root / "contract.json").read_bytes()) == constants["CONTRACT_SHA256"]
    scratch = HERE / ".scratch"
    scratch.mkdir(exist_ok=False)
    tempfile.tempdir = str(scratch)
    output = io.StringIO()
    try:
        with mock.patch("subprocess.Popen", side_effect=AssertionError("external child forbidden in review")), \
                mock.patch("os.system", side_effect=AssertionError("shell forbidden in review")), \
                mock.patch.object(socket, "socket", side_effect=AssertionError("socket forbidden in review")), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            controls = load_module("identity_network_review_canonical_controls", ROOT / CANONICAL[1])
            canonical_suite = unittest.defaultTestLoader.loadTestsFromModule(controls)
            canonical_count = canonical_suite.countTestCases()
            canonical_result = unittest.TextTestRunner(stream=output, verbosity=2).run(canonical_suite)
            focused_suite = focused_cases(controls)
            focused_count = focused_suite.countTestCases()
            focused_result = unittest.TextTestRunner(stream=output, verbosity=2).run(focused_suite)
    finally:
        (HERE / "controls.stdout.txt").write_text(output.getvalue())
        shutil.rmtree(scratch)
        tempfile.tempdir = None
    assert all((ROOT / path).read_bytes() == data for path, data in selected.items()), "canonical input changed during review"
    result = {
        "schema": 1,
        "status": "passed-offline-source-and-controls-only" if canonical_result.wasSuccessful() and focused_result.wasSuccessful() else "failed-offline-controls",
        "canonical_inputs": bindings,
        "canonical_input_digest_sha256": canonical(bindings),
        "frozen_product_files": len(manifest),
        "frozen_product_digest_sha256": canonical(manifest),
        "original_contract_packet_files": len(packet["files"]),
        "original_contract_packet_verified": True,
        "python_ast_parsed": list(CANONICAL[:2]),
        "canonical_controls": {"run": canonical_result.testsRun, "selected": canonical_count, "failures": len(canonical_result.failures), "errors": len(canonical_result.errors), "skipped": len(canonical_result.skipped)},
        "focused_controls": {"run": focused_result.testsRun, "selected": focused_count, "failures": len(focused_result.failures), "errors": len(focused_result.errors), "skipped": len(focused_result.skipped)},
        "runtime": {"python": sys.version, "executable": sys.executable, "executable_sha256": digest(Path(sys.executable).read_bytes()), "elapsed_seconds": time.monotonic() - started, "hard_alarm_seconds": 50, "command": "python3 -B verification/identity-production-network-implementation-independent/audit.py"},
        "scratch_cleanup": "removed only owned review .scratch after tests",
        "execution_scope": "Python AST/source/byte and fake-decision controls only; no product/runtime/Docker/CI qualification",
        "external_children": 0,
        "sockets": 0,
        "native_ui_capture_or_device_activity": 0,
    }
    write_json(HERE / "audit.json", result)
    signal.alarm(0)
    print(json.dumps({key: result[key] for key in ("status", "canonical_input_digest_sha256", "canonical_controls", "focused_controls", "scratch_cleanup")}, sort_keys=True))
    return 0 if canonical_result.wasSuccessful() and focused_result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
