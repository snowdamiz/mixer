"""Inert receipt controls against the archived v55 reader. No worker or compiler launch."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
import unittest

import live
from run import ADOPTED, LIVE_OVERLAY, git


def pinned_module(name, revision=ADOPTED):
    path = f"hosted/priv/development/{name}.py"
    module = ModuleType(name)
    exec(compile(git("show", f"{revision}:{path}"), path, "exec"), vars(module))
    sys.modules[name] = module
    return module


for dependency in ("compiler_worker", "starter_package_closure"):
    pinned_module(dependency)
NATIVE = pinned_module("native_artifact_worker")
CUSTODY = pinned_module("ios_build_custody", LIVE_OVERLAY)


class LiveReceiptProof(unittest.TestCase):
    def setUp(self):
        scratch = self.enterContext(TemporaryDirectory(prefix="l07-receipts-"))
        self.output = Path(scratch).resolve()
        self.project = self.output / "project"
        self.tmp = self.output / "tmp"
        self.root = self.tmp / "mixer-command-receipts-00000000-0000-0000-0000-000000000001"
        self.command = self.root / "command-00000000-0000-0000-0000-000000000002"
        self.probe = self.root / "command-00000000-0000-0000-0000-000000000003"
        for directory in (self.project, self.tmp, self.root, self.command, self.probe):
            directory.mkdir(mode=0o700)
        configuration = self.project / "mixer.yml"
        configuration.write_text('{"name":"Starter"}')
        configuration.chmod(0o600)
        self.files = {"mixer.yml": live.file_sha(configuration)}
        self.path = self.command / "receipt.json"
        self.receipt = dict(schema="mixer.owned-command.2", released=True, state="RUNNING",
                            pid=111, ownedPGID=111, ownedSession=111, runtimeStartedNS=100,
                            directory=str(self.project), command=live.xcode_argv(self.project))
        self.receipt.update(dict.fromkeys(live.CLOSED_FACTS, False))
        self.swift = self.receipt | dict.fromkeys(live.CLOSED_FACTS, True) | dict(
            command=live.SWIFT_PROBE, pid=112, ownedPGID=112, ownedSession=112,
            runtimeStartedNS=10, terminalNS=80, exitCode=0, state="TERMINAL")
        self.write_receipt(self.swift, self.probe / "receipt.json")

    def write_receipt(self, data, path=None):
        path = path or self.path
        path.write_text(json.dumps(data))
        path.chmod(0o600)

    def close_xcode(self, **changes):
        self.write_receipt(self.receipt | dict.fromkeys(live.CLOSED_FACTS, True)
                           | dict(state="TERMINAL", terminalNS=250, exitCode=0) | changes)
        ack = self.tmp / "cli-closed"
        ack.write_text(self.root.name)
        ack.chmod(0o600)
        return {"receipt_root": self.root.name,
                "receipt_sha256s": [live.file_sha(self.probe / "receipt.json"), live.file_sha(self.path)]}

    def test_accept_original_exact_xcode_that_closes_during_outage(self):
        self.write_receipt(self.receipt)
        witness = live.running_xcode(self.output, NATIVE)
        self.assertEqual(witness[1][1]["pid"], 111)
        nested = self.close_xcode()
        self.assertEqual(CUSTODY.nested_closure(NATIVE, self.tmp, self.files)[1], nested)
        terminal, digest = live.terminal_xcode(self.tmp, witness, nested, NATIVE, 150)
        self.assertEqual(terminal["state"], "TERMINAL")
        self.assertEqual(nested["receipt_sha256s"], [witness[0][2], digest])

    def test_wait_through_xcode_intent_before_active_witness(self):
        self.write_receipt(self.receipt | dict(state="INTENT", runtimeStartedNS=0))
        self.assertIsNone(live.running_xcode(self.output, NATIVE))
        self.write_receipt(self.receipt)
        self.assertEqual(live.running_xcode(self.output, NATIVE)[1][1]["pid"], 111)

    def test_reject_terminal_without_active_witness(self):
        self.close_xcode()
        with self.assertRaisesRegex(RuntimeError, "missed the Xcode RUNNING"):
            live.running_xcode(self.output, NATIVE)

    def test_reject_incomplete_or_changed_terminal_proof(self):
        self.write_receipt(self.receipt)
        witness = live.running_xcode(self.output, NATIVE)
        for changes in ({"ownedGroupAbsent": False}, {"ownedSession": 112}, {"terminalNS": 149}):
            with self.subTest(changes=changes):
                nested = self.close_xcode(**changes)
                with self.assertRaisesRegex(RuntimeError, "positive terminal custody"):
                    live.terminal_xcode(self.tmp, witness, nested, NATIVE, 150)

    def test_reject_duplicate_xcode_even_when_closed(self):
        self.write_receipt(self.receipt)
        witness = live.running_xcode(self.output, NATIVE)
        nested = self.close_xcode()
        second = self.root / "command-00000000-0000-0000-0000-000000000004"
        second.mkdir(mode=0o700)
        terminal = json.loads(self.path.read_bytes())
        self.write_receipt(terminal | dict(pid=113, ownedPGID=113, ownedSession=113, runtimeStartedNS=120),
                           second / "receipt.json")
        self.assertEqual(len(NATIVE.read_nested_receipts(self.tmp, self.root.name, strict=True)[1]), 3)
        with self.assertRaises(NATIVE.Refusal):
            CUSTODY.nested_closure(NATIVE, self.tmp, self.files)
        with self.assertRaisesRegex(RuntimeError, "lone Xcode invocation"):
            live.terminal_xcode(self.tmp, witness, nested, NATIVE, 150)

    def test_require_swift_closed_before_xcode_and_same_through_closure(self):
        self.write_receipt(self.receipt)
        path = self.probe / "receipt.json"
        for changes in (dict(terminalNS=110), dict(exitCode=1), dict(descriptorsClosed=False)):
            with self.subTest(changes=changes):
                self.write_receipt(self.swift | changes, path)
                with self.assertRaisesRegex(RuntimeError, "positively close before Xcode"):
                    live.running_xcode(self.output, NATIVE)
        self.write_receipt(self.swift, path)
        witness = live.running_xcode(self.output, NATIVE)
        self.write_receipt(self.swift | dict(stdoutBytes=12), path)
        with self.assertRaisesRegex(RuntimeError, "Swift probe receipt changed"):
            live.terminal_xcode(self.tmp, witness, self.close_xcode(), NATIVE, 150)

    def test_reject_hold_and_wrong_destination_before_cut(self):
        self.write_receipt(self.receipt | {"command": [arg.replace("iOS Simulator", "iOS")
                                                      for arg in self.receipt["command"]]})
        with self.assertRaisesRegex(RuntimeError, "unsigned generic build"):
            live.running_xcode(self.output, NATIVE)
        self.write_receipt(self.receipt)
        self.path.with_name("HOLD.json").touch()
        with self.assertRaisesRegex(RuntimeError, "custody hold"):
            live.running_xcode(self.output, NATIVE)

    def test_historical_stage_is_refused_by_exact_input_pin(self):
        stage = self.output / "historical.json"
        stage.write_bytes(git("show", f"{ADOPTED}:verification/receipts/l07-versioned-starter-worker-restart-20261119.json"))
        args = SimpleNamespace(stage_receipt=stage)
        with self.assertRaisesRegex(RuntimeError, "staging receipt differs"):
            live.stage_recipe(self.output, {"sha": NATIVE.digest}, args, {}, "")


if __name__ == "__main__":
    unittest.main()
