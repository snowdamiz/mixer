"""Inert controls for the managed v74 runner's nested wrapper custody."""

import base64
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import live
import run
import v74


class CustodyUnknown(RuntimeError):
    pass


class WrapperCustody(unittest.TestCase):
    hold = b'{ "custody": "UNKNOWN", "command": "signer", "pgid": 4031 }\n'

    def run_fixture(self, *, exit_code=0, nested_hold=False, outer_timeout=False, mode="--v74-attest"):
        # All processes and ports are doubles. Scratch contains only inert test files.
        repo = Path(self.enterContext(TemporaryDirectory(prefix="l07-runner-control-"))).resolve()
        (repo / "verification").mkdir()

        receipt = repo / "receipt.json"
        stop = Mock()
        group_absent = Mock(return_value=True)
        verify_ports = Mock()
        commands = []
        hold = self.hold

        class Process:
            def __init__(self, argv, *, cwd, **kwargs):
                self.args = argv
                self.cwd = cwd
                self.pid = 300 + len(commands)
                self.returncode = None
                self.observations = []
                commands.append(self)

            def poll(self):
                self.observations.append("poll")
                return self.returncode

            def wait(self, timeout=None):
                self.observations.append("wait")
                if self.args == ["wrapper"]:
                    if nested_hold:
                        (self.cwd / "HOLD.json").write_bytes(hold)
                    if outer_timeout:
                        raise subprocess.TimeoutExpired(self.args, timeout)
                    self.returncode = exit_code
                else:
                    self.returncode = 0
                return self.returncode

        kit = dict(require=live.require, CustodyUnknown=CustodyUnknown,
                   write=lambda path, data: path.write_text(json.dumps(data)),
                   sha=lambda _: "test-digest", record_custody=Mock(),
                   group_absent=group_absent, wait=lambda predicate, _: predicate(),
                   verify_port_reuse=verify_ports)
        with patch.object(v74, "OwnedProcess", Process):
            kit["owned"] = v74.owned_runner(kit)

            def drive(root, kit, env, pg, result, recipe, *, operator, v74_preflight):
                result["ports"] = [12345]
                (root / "settlement.json").write_text("retained database and build inputs")
                if operator is None:
                    return
                (operator / "credentials" / "session").write_text("inert session")
                with ExitStack() as services:
                    for name in ("postgres", "api"):
                        services.enter_context(kit["owned"](
                            root, name, [name], root, env, result["commands"], stop=stop,
                        ))
                    result["attestationPending"] = True
                    v74.command(root, kit, result, "attest-settled", ["wrapper"], env, timeout=1)
                    result["attestationPending"] = False

            argv = ["run.py", "--receipt", str(receipt)]
            if mode:
                argv += [mode, "--export", "unused", "--cli", "unused",
                         "--stage-receipt", "unused", "--stage-sha256", "0" * 64]
            with (
                patch.object(run, "REPO", repo),
                patch.object(sys, "argv", argv),
                patch.object(run.os, "umask"),
                patch.object(run, "provision", return_value=kit),
                patch.object(run, "drive", drive),
                patch.object(run, "environment", return_value={"PAIR25_CANCEL": "1"}),
                patch.object(live, "stage_recipe", return_value=None),
            ):
                try:
                    status = run.main()
                except (RuntimeError, subprocess.TimeoutExpired) as error:
                    status = type(error).__name__
        return status, json.loads(receipt.read_bytes()), commands, stop, group_absent, verify_ports

    def assert_held(self, *, exit_code=0, nested_hold=False, timeout=False):
        status, result, commands, stop, group_absent, verify_ports = self.run_fixture(
            exit_code=exit_code, nested_hold=nested_hold, outer_timeout=timeout,
        )
        self.assertEqual([(process.args[0], process.observations) for process in commands],
                         [("postgres", []), ("api", []), ("wrapper", ["wait"])])
        group_absent.assert_not_called()
        stop.assert_not_called()
        verify_ports.assert_not_called()
        self.assertEqual(status, 74)
        self.assertFalse(result["passed"])
        self.assertFalse(result["scratchRemoved"])
        self.assertFalse(result["operatorScratchRemoved"])
        root, operator = (Path(result[key]) for key in ("scratch", "operatorScratch"))
        self.assertEqual(result["custodyHold"]["preserved"], str(root))
        self.assertEqual(result["custodyHold"]["operatorScratch"], str(operator))
        self.assertEqual(result["custodyHold"]["nestedHoldPath"], str(root / "HOLD.json"))
        self.assertTrue((root / "settlement.json").is_file())
        self.assertTrue((root / "attest-settled.log").is_file())
        self.assertFalse((root / "attest-settled.terminal.json").exists())
        self.assertTrue((operator / "credentials" / "session").is_file())
        if nested_hold:
            self.assertEqual((root / "HOLD.json").read_bytes(), self.hold)
        else:
            self.assertFalse((root / "HOLD.json").exists())
        self.assertEqual(result["commands"]["attest-settled"].get("exit"), None if timeout else exit_code)

    def test_nested_hold_overrides_success_or_exit(self):
        for exit_code in (0, 1, 74):
            with self.subTest(exit_code=exit_code):
                self.assert_held(exit_code=exit_code, nested_hold=True)

    def test_exit_74_without_nested_record_is_unresolved(self):
        self.assert_held(exit_code=74)

    def test_outer_timeout_without_nested_record_cannot_use_group_absence(self):
        self.assert_held(timeout=True)

    def test_verified_terminal_closure_removes_both_scratch_roots(self):
        status, result, commands, stop, group_absent, verify_ports = self.run_fixture()
        self.assertEqual(status, 0)
        self.assertTrue(result["passed"])
        self.assertTrue(result["scratchRemoved"])
        self.assertTrue(result["operatorScratchRemoved"])
        self.assertNotIn("custodyHold", result)
        wrapper = result["commands"]["attest-settled"]
        self.assertEqual((wrapper["exit"], wrapper["directChildReaped"], wrapper["groupAbsent"]),
                         (0, True, True))
        self.assertEqual([item.args[0] for item in commands], ["postgres", "api", "wrapper"])
        self.assertEqual(group_absent.call_count, 3)
        self.assertEqual(stop.call_count, 2)
        verify_ports.assert_called_once()

    def test_managed_enrollment_passes_both_ports_as_process_arguments(self):
        scratch = Path(self.enterContext(TemporaryDirectory(prefix="l07-enroll-control-")))
        root = scratch / "run"
        operator = scratch / "operator"
        root.mkdir()
        operator.mkdir()
        closed = {"exit": 0, "groupAbsent": True, "directChildReaped": True}
        result = {
            "commands": {name: closed for name in ("processor", "worker", "independent-parent")},
            "liveCustodyPending": False, "xcodeInvocations": 1, "liveClosure": {"xcodeExit": 0},
            "ports": [54321],
        }

        def sha(data):
            return hashlib.sha256(data).hexdigest()

        class WrapperReached(Exception):
            pass

        def launch(_root, _kit, _result, name, argv, _env, **_options):
            if name == "keygen":
                argv[-1].touch()
            elif name == "public-key":
                argv[-1].write_bytes(b"header\n" + base64.b64encode(v74.PREFLIGHT_SPKI) + b"\n")
            else:
                self.assertEqual(name, "attest-settled")
                args = [os.fspath(value) for value in argv]
                self.assertEqual(args[args.index("--api-port") + 1], "61234")
                self.assertEqual(args[args.index("--pg-port") + 1], "54321")
                raise WrapperReached

        ready = Mock(return_value={
            "origin": "http://127.0.0.1:61234", "spkiSHA256": sha(v74.PREFLIGHT_SPKI),
            "role": "mixer_native_attestation_writer", "missingBuildHTTP": 404,
            "missingScopeHTTP": 403, "rows": 0, "browserStorageReady": True,
            "freshBrowserSession": True,
        })
        with patch.object(v74, "command", side_effect=launch), self.assertRaises(WrapperReached):
            v74.enroll(root, {"require": live.require, "sha": sha}, {}, scratch, result, None,
                       {"port": 61234, "wrapper": scratch / "wrapper.py"}, operator, ready,
                       preflight=False)

    def test_default_and_v55_keep_terminal_cleanup(self):
        for mode in ("", "--live"):
            with self.subTest(mode=mode):
                status, result, commands, _, _, verify_ports = self.run_fixture(mode=mode)
                self.assertEqual(status, 0)
                self.assertTrue(result["scratchRemoved"])
                self.assertFalse(commands)
                self.assertNotIn("custodyHold", result)
                verify_ports.assert_called_once()


if __name__ == "__main__":
    unittest.main()
