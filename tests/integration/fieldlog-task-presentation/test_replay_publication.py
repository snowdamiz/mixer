"""Drive the replay entry point with inert subprocesses and publication faults."""
import contextlib
import errno
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import replay


class PublicationTest(unittest.TestCase):
    def setUp(self):
        fixture = tempfile.TemporaryDirectory()
        self.addCleanup(fixture.cleanup)
        self.root = Path(fixture.name).resolve()
        self.work = self.root / "scratch"
        self.receipt = self.root / "receipt.json"
        self.output = io.StringIO()

    def invoke(self, android_exit=None):
        args = ["replay.py", str(self.root), str(self.work), "--receipt", str(self.receipt)]
        if android_exit is not None:
            args += ["--android-swift", "inert-swift", "--android-sdks", "inert-sdk"]
        run = replay.Replay.run

        def run_inert(instance, name, deadline, _argv):
            status = 0
            output = ""
            if name == "initial-package-refusal":
                status = 1
                output = "".join(
                    f"error: '{member}' is inaccessible due to 'package' protection level\n"
                    for member in ("state", "applyEdit", "titleField")
                )
            elif name.endswith("-host-replay"):
                output = "Inert host observation\n"
            elif name.endswith("-toolchain-version"):
                output = "Inert compiler version\n"
            elif name == "scratch-size":
                output = "42\tscratch\n"
            elif name == "candidate-android-AppAndroid":
                status = android_exit
                if status:
                    output = "error: inert Android compile refused\n"
                else:
                    library = instance.work / "android/build/libAppAndroid.so"
                    library.parent.mkdir(parents=True)
                    library.write_bytes(b"\x7fELF\x02\x01" + b"\0" * 12 + b"\xb7\0")
            return run(instance, name, deadline, [
                sys.executable, "-B", "-c",
                "import sys; sys.stdout.write(sys.argv[1]); sys.exit(int(sys.argv[2]))",
                output, str(status),
            ])

        with (
            patch.object(replay.Replay, "run", run_inert),
            patch.object(sys, "argv", args),
            patch.dict(os.environ),
            contextlib.redirect_stdout(self.output),
            contextlib.redirect_stderr(self.output),
        ):
            return replay.main()

    def report(self):
        return json.loads(self.receipt.read_text())

    def assert_retained_terminal_logs(self):
        self.assertIn(str(self.work), self.output.getvalue())
        directory = self.work / "commands"
        self.assertEqual((directory / "candidate-host-replay.log").read_text(), "Inert host observation\n")
        self.assertTrue((directory / "scratch-size.log").is_file())
        for path in directory.glob("*.json"):
            row = json.loads(path.read_bytes())
            self.assertTrue(row["directChildReaped"] and row["ownedGroupAbsent"])

    def test_enospc_before_publish_preserves_terminal_logs(self):
        with patch("replay.os.fsync", side_effect=OSError(errno.ENOSPC, "inert fsync failure")):
            with self.assertRaises(OSError) as failure:
                self.invoke()
        self.assertEqual(failure.exception.errno, errno.ENOSPC)
        self.assertFalse(self.receipt.exists())
        self.assertEqual(len(list(self.root.glob(".receipt.json.*.tmp"))), 1)
        self.assert_retained_terminal_logs()

    def test_interrupted_after_atomic_link_preserves_terminal_logs(self):
        sync = os.fsync

        def interrupt_directory_sync(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise KeyboardInterrupt
            sync(fd)

        with patch("replay.os.fsync", side_effect=interrupt_directory_sync):
            with self.assertRaises(KeyboardInterrupt):
                self.invoke()
        self.assertEqual(self.report()["android"]["status"], "not requested")
        self.assert_retained_terminal_logs()

    def test_prior_receipt_refused_before_scratch_creation(self):
        self.receipt.write_bytes(b"prior evidence")
        with self.assertRaises(SystemExit) as failure:
            self.invoke()
        self.assertEqual(failure.exception.code, 2)
        self.assertEqual(self.receipt.read_bytes(), b"prior evidence")
        self.assertFalse(self.work.exists())

    def test_dangling_receipt_symlink_refused(self):
        absent = self.root / "absent"
        self.receipt.symlink_to(absent)
        with self.assertRaises(SystemExit):
            self.invoke()
        self.assertTrue(self.receipt.is_symlink())
        self.assertFalse(absent.exists())
        self.assertFalse(self.work.exists())

    def test_receipt_created_after_preflight_is_not_clobbered(self):
        link = os.link

        def race(staged, destination):
            self.receipt.write_bytes(b"competing evidence")
            return link(staged, destination)

        with patch("replay.os.link", side_effect=race):
            with self.assertRaises(FileExistsError):
                self.invoke()
        self.assertEqual(self.receipt.read_bytes(), b"competing evidence")
        self.assert_retained_terminal_logs()

    def test_requested_android_failure_publishes_and_returns_one(self):
        self.assertEqual(self.invoke(android_exit=1), 1)
        report = self.report()
        self.assertEqual(report["android"]["status"], "compile failed")
        self.assertEqual(report["commands"]["candidate-android-AppAndroid"]["exit"], 1)
        self.assertEqual(report["retainedScratch"], str(self.work))
        self.assertEqual(
            (self.work / "commands/candidate-android-AppAndroid.log").read_text(),
            "error: inert Android compile refused\n",
        )
        self.assert_retained_terminal_logs()

    def test_requested_android_success_cleans_after_publication(self):
        cleanup = replay.Replay.cleanup

        def check_published(instance):
            self.assertEqual(self.report()["android"]["status"], "compile and link pass")
            self.assertTrue(instance.records["candidate-android-AppAndroid"]["ownedGroupAbsent"])
            return cleanup(instance)

        with patch.object(replay.Replay, "cleanup", check_published):
            self.assertEqual(self.invoke(android_exit=0), 0)
        self.assertFalse(self.work.exists())
        self.assertFalse(list(self.root.glob(".receipt.json.*.tmp")))

    def test_ordinary_no_compile_is_success_and_cleans(self):
        self.assertEqual(self.invoke(), 0)
        report = self.report()
        self.assertEqual(report["android"]["status"], "not requested")
        self.assertNotIn("candidate-android-AppAndroid", report["commands"])
        self.assertIsNone(report["retainedScratch"])
        self.assertFalse(self.work.exists())


if __name__ == "__main__":
    unittest.main()
