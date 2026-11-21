"""Exercise the active custody boundary with inert launches and one real true control."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

import replay
from run import OwnedCommands, UnresolvedCustody, publish_receipt

ROOT = Path(sys.argv.pop(1))


class TerminalStub:
    pid = 424242
    returncode = 0

    def poll(self):
        return self.returncode


class CleanupControls(unittest.TestCase):
    def setUp(self):
        self.work = ROOT / self._testMethodName
        self.work.mkdir()
        self.commands = OwnedCommands(self.work)
        self.receipt = self.commands.directory / "first.json"
        self.marker = self.work / "marker"
        self.marker.write_text("owned scratch")
        self.real_launch_count = 0
        self.addCleanup(self.remove_inert_scratch)

    def remove_inert_scratch(self):
        # Fault controls never create a process, and the real positive control
        # cleans itself only after observing terminal custody.
        if self.real_launch_count == 0 and self.work.exists():
            shutil.rmtree(self.work)

    def run_inert(self, name="first", output=b""):
        def inert_launch(args, *, stdout, **kwargs):
            stdout.write(output)
            return TerminalStub()

        with (patch("run.subprocess.Popen", side_effect=inert_launch) as launch,
              patch("run.absent", return_value=True)):
            self.commands.run(name, self.work, 2, ["never-executed"])
        self.assertEqual(launch.call_count, 1)

    def assert_retained(self, reason):
        message = io.StringIO()
        with contextlib.redirect_stderr(message):
            self.assertFalse(self.commands.cleanup())
        self.assertIn(reason, message.getvalue())
        self.assertEqual(self.marker.read_text(), "owned scratch")

    def test_scan_eacces(self):
        self.run_inert()
        self.commands.directory.chmod(0)
        try:
            self.assert_retained("Permission denied")
        finally:
            self.commands.directory.chmod(0o700)

    def test_scan_io_error(self):
        self.run_inert()
        with patch("run.os.scandir", side_effect=OSError(5, "injected scan failure")):
            self.assert_retained("injected scan failure")

    def test_unreadable_log_refuses_reporting_and_cleanup(self):
        self.run_inert(output=b"recorded output\n")
        log = self.commands.directory / "first.log"
        log.chmod(0)
        try:
            with self.assertRaises(PermissionError) as blocked:
                log.read_bytes()
            self.assertEqual(blocked.exception.errno, 13)
            with self.assertRaises(PermissionError):
                self.commands.checked_receipts()
            self.assert_retained("Permission denied")
        finally:
            log.chmod(0o600)

    def test_truncated_log_refuses_reporting_and_cleanup(self):
        self.run_inert(output=b"recorded output\n")
        log = self.commands.directory / "first.log"
        log.write_bytes(b"")
        with self.assertRaisesRegex(UnresolvedCustody, "first.log digest mismatch"):
            self.commands.checked_receipts()
        self.assert_retained("first.log digest mismatch")
        self.assertTrue(self.receipt.is_file())

    def test_log_stat_and_digest_errors_refuse_reporting_and_cleanup(self):
        self.run_inert(output=b"recorded output\n")
        for target in ("run.os.fstat", "run.hashlib.file_digest"):
            with self.subTest(target=target), patch(target, side_effect=OSError(5, target)):
                with self.assertRaisesRegex(OSError, target):
                    self.commands.checked_receipts()
                self.assert_retained(target)

    def test_top_level_truncated_pin_log_preserves_parse_failure_evidence(self):
        work = self.work / "replay-scratch"
        output = self.work / "replay-output"
        argv = ["replay.py", str(self.work), str(work), str(output), "--host-only"]
        pin = work / "commands/mixer-public-pin.log"
        original_run = OwnedCommands.run

        def inert_launch(args, *, stdout, **kwargs):
            if Path(stdout.name) == pin:
                stdout.write(b'{"sha":"pin"}')
            return TerminalStub()

        def truncate_after_recording(ledger, name, *args, **kwargs):
            original_run(ledger, name, *args, **kwargs)
            if name == "mixer-public-pin":
                pin.write_bytes(b'{"sha":')

        errors = io.StringIO()
        with (patch.object(sys, "argv", argv),
              patch.object(OwnedCommands, "run", truncate_after_recording),
              patch("run.subprocess.Popen", side_effect=inert_launch) as launch,
              patch("run.absent", return_value=True),
              contextlib.redirect_stderr(errors)):
            with self.assertRaises(json.JSONDecodeError):
                replay.main()
        self.assertEqual(launch.call_count, 3)
        self.assertTrue(work.is_dir())
        self.assertEqual(pin.read_bytes(), b'{"sha":')
        self.assertTrue(pin.with_suffix(".json").is_file())
        self.assertIn("mixer-public-pin.log digest mismatch", errors.getvalue())
        self.assertFalse((output / "receipt.json").exists())

    def test_missing_receipt_after_terminal_observation(self):
        self.run_inert()
        self.receipt.unlink()
        self.assert_retained("files differ")

    def test_partial_receipt_set_cannot_cover_two_commands(self):
        self.run_inert()
        self.run_inert("second")
        (self.commands.directory / "second.json").unlink()
        self.assertTrue(self.receipt.is_file())
        self.assert_retained("files differ")

    def test_corrupt_receipt(self):
        self.run_inert()
        self.receipt.write_bytes(b"{\xff")
        self.assert_retained("no matching positive terminal receipt")

    def test_valid_json_with_invalid_custody_state(self):
        self.run_inert()
        row = json.loads(self.receipt.read_text())
        row["groupAbsent"] = False
        self.receipt.write_text(json.dumps(row))
        self.assert_retained("no matching positive terminal receipt")

    def test_interrupted_launch_even_if_pending_receipt_disappears(self):
        def interrupted(*args, **kwargs):
            self.assertEqual(json.loads(self.receipt.read_text())["custody"], "launch pending")
            self.receipt.unlink()
            raise KeyboardInterrupt()

        with patch("run.subprocess.Popen", side_effect=interrupted) as launch:
            with self.assertRaises(KeyboardInterrupt):
                self.commands.run("first", self.work, 2, ["never-executed"])
        self.assertEqual(launch.call_count, 1)
        self.assert_retained("first has no confirmed terminal receipt")

    def test_pending_write_failure_prevents_launch_and_cleanup(self):
        with patch("run.write_receipt", side_effect=OSError(28, "injected unwritten receipt")),              patch("run.subprocess.Popen") as launch:
            with self.assertRaisesRegex(OSError, "injected unwritten receipt"):
                self.commands.run("first", self.work, 2, ["never-executed"])
            launch.assert_not_called()
        self.assertFalse(self.receipt.exists())
        self.assert_retained("first has no confirmed terminal receipt")

    def test_identity_write_failure_keeps_pending(self):
        with patch("run.publish_receipt", side_effect=OSError(28, "injected identity write")),              patch("run.subprocess.Popen", return_value=TerminalStub()),              patch("run.absent") as observer:
            with self.assertRaisesRegex(OSError, "injected identity write"):
                self.commands.run("first", self.work, 2, ["never-executed"])
            observer.assert_not_called()
        self.assertEqual(json.loads(self.receipt.read_text())["custody"], "launch pending")
        self.assert_retained("first has no confirmed terminal receipt")

    def test_terminal_write_failure_keeps_running_receipt(self):
        def refuse_terminal(path, row):
            if row.get("groupAbsent"):
                raise OSError(28, "injected final publication failure")
            publish_receipt(path, row)

        with patch("run.publish_receipt", side_effect=refuse_terminal),              patch("run.subprocess.Popen", return_value=TerminalStub()),              patch("run.absent", return_value=True):
            with self.assertRaisesRegex(OSError, "injected final publication failure"):
                self.commands.run("first", self.work, 2, ["never-executed"])
        self.assertEqual(json.loads(self.receipt.read_text())["custody"], "running")
        self.assert_retained("first has no confirmed terminal receipt")

    def test_extra_receipt_rejected(self):
        self.run_inert()
        (self.commands.directory / "unknown.json").write_bytes(self.receipt.read_bytes())
        self.assert_retained("files differ")

    def test_positively_empty_campaign_can_clean(self):
        with patch("run.subprocess.Popen") as launch:
            self.assertEqual(self.commands.checked_receipts(), {})
            self.assertTrue(self.commands.cleanup())
        launch.assert_not_called()
        self.assertFalse(self.work.exists())

    def test_top_level_interrupt_retains_pending_attempt(self):
        work = self.work / "replay-scratch"
        output = self.work / "replay-output"
        argv = ["replay.py", str(self.work), str(work), str(output), "--host-only"]
        with patch.object(sys, "argv", argv), \
             patch("run.subprocess.Popen", side_effect=KeyboardInterrupt()) as launch, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(KeyboardInterrupt):
                replay.main()
        self.assertEqual(launch.call_count, 1)
        receipt = work / "commands/prepare.json"
        self.assertEqual(json.loads(receipt.read_text())["custody"], "launch pending")
        self.assertTrue(work.is_dir())

    def test_top_level_routes_every_helper_through_one_ledger(self):
        self.inert_replay(fail_report=False)

    def test_top_level_replay_receipt_write_failure_retains_scratch(self):
        self.inert_replay(fail_report=True)

    def inert_replay(self, *, fail_report):
        work = self.work / "replay-scratch"
        output = self.work / "replay-output"
        argv = ["replay.py", str(self.work), str(work), str(output)]
        expected = {
            "prepare", "deps", "mixer-public-pin", "apply-product", "candidate-tree",
            "materialize-baseline", "materialize-final", "baseline-apple-build",
            "baseline-apple-disk", "baseline-export-build", "baseline-export-disk",
            "baseline-android-existing-tests", "final-apple-build", "final-apple-disk",
            "final-export-build", "final-export-disk", "final-android-existing-tests",
            "final-apple-existing-tests", "final-standalone-export", "ios-vm",
            "final-android", "final-iphoneos", "read-android-elf", "read-android-symbols",
            "read-ios-macho", "read-ios-storage-symbols",
        }
        observed = set()

        def inert_launch(args, *, stdout, **kwargs):
            name = Path(stdout.name).stem
            receipt = work / "commands" / f"{name}.json"
            row = json.loads(receipt.read_text())
            self.assertEqual(row["custody"], "launch pending")
            self.assertEqual(row["argv"], args)
            self.assertNotIn(name, observed)
            observed.add(name)
            if name == "mixer-public-pin":
                stdout.write(json.dumps({
                    "sha": "6bc461f4fc7c29771718c7c5ce5a2a39b78f4d2d",
                    "tree": {"sha": "d888b6a1ef9331079b98a0dc21c3a1b8ee482894"},
                }).encode())
            elif name == "candidate-tree":
                stdout.write((replay.HERE / "candidate-tree.txt").read_bytes())
            elif name == "ios-vm":
                lib = work / "ios-cargo/aarch64-apple-ios/release"
                lib.mkdir(parents=True)
                (lib / "libmixer_vm.a").touch()
            return TerminalStub()

        def validate_collector(checked_work, checked_output, receipts, host_only):
            self.assertEqual(checked_work, work)
            self.assertEqual(checked_output, output)
            self.assertFalse(host_only)
            self.assertEqual(set(receipts), expected)
            return {"observed": len(receipts)}

        def publish_report(path, row):
            if fail_report:
                raise OSError(28, "injected aggregate receipt failure")
            publish_receipt(path, row)

        errors = io.StringIO()
        with patch.object(sys, "argv", argv), \
             patch("run.subprocess.Popen", side_effect=inert_launch), \
             patch("run.absent", return_value=True), \
             patch("replay.summarize", side_effect=validate_collector), \
             patch("replay.publish_receipt", side_effect=publish_report), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
            if fail_report:
                with self.assertRaisesRegex(OSError, "injected aggregate receipt failure"):
                    replay.main()
            else:
                replay.main()
        self.assertEqual(observed, expected)
        if fail_report:
            self.assertTrue(work.is_dir())
            self.assertFalse((output / "receipt.json").exists())
            self.assertIn("replay receipt publication failed", errors.getvalue())
        else:
            self.assertFalse(work.exists())
            self.assertEqual(json.loads((output / "receipt.json").read_text()), {"observed": 26})

    def test_real_terminal_command_and_complete_set_can_clean(self):
        self.real_launch_count += 1
        self.commands.run("first", self.work, 3, ["/usr/bin/true"])
        checked = self.commands.checked_receipts()
        row = checked["first"]
        for field in ("groupAbsent", "childReaped", "logClosed"):
            self.assertIs(row[field], True)
        self.assertEqual(row["exit"], 0)
        self.assertTrue(self.commands.cleanup())
        self.assertFalse(self.work.exists())
        print(f"positive real command PID/PGID {row['pgid']}: exited 0, reaped, absent, log closed, scratch removed")


if __name__ == "__main__":
    ROOT.mkdir()
    unittest.main(verbosity=2)
