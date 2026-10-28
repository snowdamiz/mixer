#!/usr/bin/env python3
"""Guarded independent source and host-transport review; no child/runtime work."""
import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
CANONICAL = ["hosted/scripts/test-identity-network.py", "hosted/scripts/test_identity_network_collector.py", "docs/hosted-identity-production-network-ci-contract.md"]
EXPECTED = ["ee9c047ae628b18df2cd8c7b963910bc573b998358cf76eb27abec81598cb05e", "0a0cca3001af5c01a35b59b7d18bdd090f220aa52218d56f2c9676273f9d1615", "9f7ac0bc7a3e625ae353bc3c3354c1cd0e1efdc1ac06eccc52d8162fcce1ded0"]
PUBLIC = {"/workspace/downloads/hex.ez": "hex", "/workspace/tooling/rebar3": "rebar"}
SCRATCH = BASE / ".scratch"
SCRATCH.mkdir(exist_ok=True)

def binding(path):
    body = path.read_bytes()
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value

def dump(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")

blocked = ("subprocess.Popen", "os.system", "os.popen", "socket.socket", "socket.create_connection")
guards = contextlib.ExitStack()
for target in blocked:
    guards.enter_context(mock.patch(target, side_effect=AssertionError("independent pure-review external-execution guard: " + target)))
subject = load("independent_binary_export_subject", ROOT / CANONICAL[0])
producer = load("independent_producer_controls", ROOT / CANONICAL[1])

class Review(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH, prefix="case-")
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.root = self.dir / "repository"
        self.root.mkdir()

    def collector(self, payload=b"", code=0, stderr=b""):
        with mock.patch.dict("os.environ", {"GITHUB_RUN_ID": "91001", "GITHUB_RUN_ATTEMPT": "1"}):
            result = subject.Collector(self.root, self.dir / "out", "a" * 40, runner=lambda argv, timeout, stdin: (code, payload, stderr))
        result.execute = lambda owned, argv, timeout, **kwargs: result.command(argv, timeout, **kwargs)
        return result

    def owned(self):
        return SimpleNamespace(cid="c" * 64, role="prepare")

    def receipt(self, collector, tool="hex"):
        return json.loads((collector.output / "bootstrap-exports" / (tool + "-actual.json")).read_bytes())

    def test_exact_canonical_and_protected_bindings(self):
        for name, expected in zip(CANONICAL, EXPECTED):
            self.assertEqual(expected, binding(ROOT / name)["sha256"])
        self.assertEqual("fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57", binding(ROOT / ".github/workflows/hosted.yml")["sha256"])
        self.assertEqual("8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299", binding(ROOT / "hosted/lib/mixer_hosted/browser_auth/store.ex")["sha256"])

    def test_no_other_collector_function_or_constant_changes(self):
        before = ast.parse((ROOT / "verification/identity-network-binary-export-correction/implementation/before" / CANONICAL[0]).read_text())
        after = ast.parse((ROOT / CANONICAL[0]).read_text())
        def strip(tree):
            tree.body = [node for node in tree.body if not isinstance(node, ast.FunctionDef) or node.name != "validate_bootstrap_export"]
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == "Collector":
                    node.body = [item for item in node.body if not isinstance(item, ast.FunctionDef) or item.name not in {"copy_file_out", "collect"}]
            return ast.dump(tree, include_attributes=False)
        self.assertEqual(strip(before), strip(after))
        old = ast.parse((ROOT / "verification/identity-network-binary-export-correction/implementation/before" / CANONICAL[1]).read_text())
        new = ast.parse((ROOT / CANONICAL[1]).read_text())
        def tests(tree):
            return {cls.name + "." + fn.name: ast.dump(fn, include_attributes=False) for cls in tree.body if isinstance(cls, ast.ClassDef) for fn in cls.body if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test_")}
        old_tests, new_tests = tests(old), tests(new)
        self.assertEqual(103, len(old_tests))
        self.assertEqual(111, len(new_tests))
        self.assertTrue(all(new_tests[k] == v for k, v in old_tests.items()))

    def test_exact_pinned_public_hex_bytes_and_historical_transcode_are_discriminated(self):
        payload = (ROOT / "verification/github-delivery-runtime-followup/network-review/official/pinned-hex-2.5.1.ez").read_bytes()
        self.assertEqual(set(range(256)), set(payload))
        c = self.collector(payload)
        actual = c.copy_file_out(self.owned(), "/workspace/downloads/hex.ez", 16777216)
        self.assertEqual(payload, subject.validate_bootstrap_export("hex", actual, 1133941))
        self.assertEqual(payload, (c.output / "bootstrap-exports/hex-actual.bin").read_bytes())
        transformed = payload.decode("latin1").encode("utf8")
        self.assertEqual(1693010, len(transformed))
        self.assertEqual("9ec3f63426780b4b34d6486a64785e6e499fec9167ac7c81eaad6de7f0c195f6", hashlib.sha256(transformed).hexdigest())
        with self.assertRaisesRegex(subject.CollectorError, "byte-count mismatch"):
            subject.validate_bootstrap_export("hex", transformed, 1133941)
        self.assertIs(True, self.receipt(c)["stdout_complete"])

    def test_same_length_high_byte_corruption_is_rejected_with_exact_pin(self):
        payload = bytes(range(256))
        pins = copy.deepcopy(subject.BOOTSTRAP)
        pins["rebar"]["sha512"] = hashlib.sha512(payload).hexdigest()
        with mock.patch.object(subject, "BOOTSTRAP", pins):
            self.assertEqual(payload, subject.validate_bootstrap_export("rebar", payload, 256))
            with self.assertRaisesRegex(subject.CollectorError, "digest mismatch"):
                subject.validate_bootstrap_export("rebar", payload[:-1] + b"\x00", 256)

    def test_literal_applies_binary_mode_before_write_for_every_actual_caller(self):
        paths = tuple(PUBLIC) + ("/workspace/prepared.tar", "/workspace/evidence/events.jsonl", "/workspace/evidence/identity/k03.json", "/workspace/evidence/runtime.json")
        payload = b"\x00" + bytes(range(256)) * 17
        for index, path in enumerate(paths):
            c = self.collector(payload)
            self.assertEqual(payload, c.copy_file_out(self.owned(), path, 8192))
            row = json.loads((c.output / "logs/0001.json").read_bytes())
            self.assertEqual(["/usr/local/bin/elixir", "-e", "path = " + json.dumps(path) + "; true = File.stat!(path).size <= 8192; :ok = :io.setopts(:standard_io, encoding: :latin1); :ok = IO.binwrite(File.read!(path))"], row["argv"])
            self.assertEqual(30, row["timeout_seconds"])
            shutil.rmtree(c.output)

    def test_two_public_captures_join_exact_own_command_not_prior_or_next_row(self):
        payload = bytes(range(256))
        c = self.collector(payload)
        c.command(["inert", "prior"])
        for number, (path, tool) in enumerate(PUBLIC.items(), start=2):
            c.copy_file_out(self.owned(), path, 4096)
            r = self.receipt(c, tool)
            row = json.loads((c.output / "logs" / (f"{number:04d}.json")).read_bytes())
            self.assertEqual(number, r["command_number"])
            self.assertEqual(row["stdout_sha256"], r["sha256"])
            self.assertEqual(row["stdout_bytes"], r["bytes"])
            self.assertEqual(row["exit_code"], r["command_exit_code"])
            self.assertEqual(self.owned().cid, r["owned_cid"])
            self.assertEqual(path, r["container_path"])
        c.command(["inert", "next"])
        self.assertEqual(2, self.receipt(c)["command_number"])
        c.seal()
        self.assertFalse((c.output / ".scratch").exists())
        self.assertTrue((c.output / "bootstrap-exports/hex-actual.bin").exists())

    def test_stderr_overflow_retains_bounded_output_and_never_reports_complete(self):
        c = self.collector(bytes(range(256)) * 4, stderr=b"e" * 7)
        with self.assertRaisesRegex(subject.CollectorError, "output incomplete"):
            c.copy_file_out(self.owned(), "/workspace/downloads/hex.ez", 64)
        r = self.receipt(c)
        self.assertEqual(57, r["bytes"])
        self.assertIs(False, r["stdout_complete"])
        self.assertIs(False, r["stderr_complete"])
        self.assertEqual(bytes(range(57)), (c.output / "bootstrap-exports/hex-actual.bin").read_bytes())

    def test_setopts_nonzero_and_zero_length_output_remain_failed_and_retained(self):
        c = self.collector(b"", code=1, stderr=b"setopts failed")
        with self.assertRaises(subject.CollectorError):
            c.copy_file_out(self.owned(), "/workspace/tooling/rebar3", 64)
        r = self.receipt(c, "rebar")
        self.assertEqual(0, r["bytes"])
        self.assertEqual(1, r["command_exit_code"])
        self.assertIs(False, r["stdout_complete"])
        self.assertEqual(hashlib.sha512(b"").hexdigest(), r["sha512"])

    def test_public_retention_does_not_extend_to_prefix_suffix_or_private_paths(self):
        c = self.collector(b"synthetic private marker")
        for path in ("/workspace/downloads/hex.ez/private", "/workspace/downloads/hex.ez.bak", "/workspace/tooling/rebar3-private", "/workspace/downloads/rebar3", "/etc/private"):
            with self.assertRaisesRegex(subject.CollectorError, "unreviewed copy-out"):
                c.copy_file_out(self.owned(), path, 64)
        for path in ("/workspace/evidence/hex.ez", "/workspace/evidence/rebar3", "/workspace/prepared.tar"):
            c.copy_file_out(self.owned(), path, 64)
        self.assertFalse((c.output / "bootstrap-exports").exists())
        self.assertFalse((c.output / ".scratch/copy.bin").exists())

    def test_failed_exact_size_digest_validation_never_deletes_capture(self):
        payload = bytes(range(256))
        c = self.collector(payload)
        body = c.copy_file_out(self.owned(), "/workspace/tooling/rebar3", 4096)
        for expected in (255, 256, 257):
            with self.assertRaises(subject.CollectorError):
                subject.validate_bootstrap_export("rebar", body, expected)
            self.assertEqual(payload, (c.output / "bootstrap-exports/rebar-actual.bin").read_bytes())
        self.assertFalse((c.output / "bootstrap-rebar-3.28.0").exists())

    def test_no_capture_or_stale_success_receipt_is_fabricated_on_precommand_exception(self):
        c = self.collector(b"prior bytes")
        c.command(["inert", "prior"])
        c.execute = mock.Mock(side_effect=subject.CollectorError("exact CID observation refused"))
        with self.assertRaisesRegex(subject.CollectorError, "CID observation refused"):
            c.copy_file_out(self.owned(), "/workspace/downloads/hex.ez", 64)
        self.assertFalse((c.output / "bootstrap-exports/hex-actual.bin").exists())
        self.assertFalse((c.output / "bootstrap-exports/hex-actual.json").exists())
        self.assertEqual(1, c.command_number)

    def test_repeat_and_oversized_public_request_refused_without_replacement(self):
        c = self.collector(b"\xff\x00")
        with self.assertRaisesRegex(subject.CollectorError, "public bootstrap export cap"):
            c.copy_file_out(self.owned(), "/workspace/downloads/hex.ez", 16777217)
        self.assertEqual(0, c.command_number)
        c.copy_file_out(self.owned(), "/workspace/downloads/hex.ez", 64)
        initial = (c.output / "bootstrap-exports/hex-actual.bin").read_bytes()
        with self.assertRaisesRegex(subject.CollectorError, "already retained"):
            c.copy_file_out(self.owned(), "/workspace/downloads/hex.ez", 64)
        self.assertEqual(initial, (c.output / "bootstrap-exports/hex-actual.bin").read_bytes())
        self.assertEqual(1, c.command_number)

def main():
    signal.alarm(50)
    before = {name: binding(ROOT / name) for name in CANONICAL}
    for name in CANONICAL:
        destination = BASE / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    streams = {}
    results = {}
    for label, suite in (("producer", unittest.defaultTestLoader.loadTestsFromModule(producer)), ("independent", unittest.defaultTestLoader.loadTestsFromTestCase(Review))):
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        (BASE / (label + ".log")).write_text(stream.getvalue())
        results[label] = {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped), "passed": result.wasSuccessful()}
    after = {name: binding(ROOT / name) for name in CANONICAL}
    assert before == after, "canonical source drifted during review"
    canonical_root = hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    dump(BASE / "checks.json", {"schema": 1, "source": before, "source_root": canonical_root, "source_stable": True, "results": results, "scope": "guarded pure Python controls, inert transcript runners and source inspection; no Elixir, Docker, compiler, PG, guest/native or UI runtime", "python": sys.version, "guards": list(blocked), "owned_scratch_cleaned": not any(SCRATCH.iterdir())})
    SCRATCH.rmdir()
    print(json.dumps(results, sort_keys=True))
    return 0 if all(r["passed"] for r in results.values()) else 1

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        guards.close()
