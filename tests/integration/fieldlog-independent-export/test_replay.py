"""Check the verified APK handoff without building or launching an app."""

import contextlib
import hashlib
import io
import json
import os
import stat
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import replay


class APKHandoffTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "verification").mkdir()
        self.apk = self.root / "fieldlog.apk"
        self.receipt = self.root / "receipt.json"
        self.data = b"verified APK bytes"

    def run_replay(self, *, output=True, changed=False, race=False):
        def completed_build(run):
            artifact = run.scratch / "app-unsigned.apk"
            artifact.write_bytes(b"changed APK" if changed else self.data)
            run.receipt["artifact"] = {"sha256": hashlib.sha256(self.data).hexdigest()}
            if race:
                self.apk.write_bytes(b"existing output")
            return artifact

        argv = ["replay.py", "--receipt", str(self.receipt)]
        if output:
            argv.extend(("--apk-output", str(self.apk)))
        with (
            patch.object(replay, "REPO", self.root),
            patch.object(replay.Replay, "execute", completed_build),
            patch.object(sys, "argv", argv),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = replay.main()
        receipt = json.loads(self.receipt.read_bytes())
        self.assertTrue(receipt["cleanup"]["scratchRemoved"])
        self.assertEqual(list((self.root / "verification/local").iterdir()), [])
        return result, receipt

    def test_publishes_verified_apk_after_build(self):
        result, receipt = self.run_replay()
        self.assertEqual(result, 0)
        self.assertEqual(self.apk.read_bytes(), self.data)
        self.assertEqual(receipt["artifact"]["output"], str(self.apk))

    def test_default_discards_apk_with_build_scratch(self):
        result, receipt = self.run_replay(output=False)
        self.assertEqual(result, 0)
        self.assertFalse(self.apk.exists())
        self.assertNotIn("output", receipt["artifact"])

    def test_copy_with_different_bytes_fails_without_publishing(self):
        result, receipt = self.run_replay(changed=True)
        self.assertEqual(result, 1)
        self.assertFalse(self.apk.exists())
        self.assertIn("SHA-256", receipt["failure"])

    def test_a_destination_created_during_the_build_is_preserved(self):
        result, receipt = self.run_replay(race=True)
        self.assertEqual(result, 1)
        self.assertNotIn("output", receipt["artifact"])
        self.assertEqual(self.apk.read_bytes(), b"existing output")
        self.assertEqual(set(path.name for path in self.root.iterdir()),
                         {"fieldlog.apk", "receipt.json", "verification"})

    def test_link_uses_verified_private_staging_directory(self):
        source = self.root / "unsigned.apk"
        source.write_bytes(self.data)
        real_link = os.link

        def link(old, new, *, src_dir_fd=None, **kwargs):
            if src_dir_fd is None:
                # Model a directory writer substituting the public staging name.
                Path(old).unlink()
                Path(old).write_bytes(b"different bytes")
                real_link(old, new, **kwargs)
                return

            self.assertEqual(stat.S_IMODE(os.fstat(src_dir_fd).st_mode), 0o700)
            staged = next(self.root.glob(".fieldlog-apk-*"))
            moved = staged.with_suffix(".moved")
            staged.rename(moved)
            staged.mkdir()
            (staged / old).write_bytes(b"different bytes")
            try:
                real_link(old, new, src_dir_fd=src_dir_fd, **kwargs)
            finally:
                (staged / old).unlink()
                staged.rmdir()
                moved.rename(staged)

        with patch.object(replay.os, "link", side_effect=link):
            replay.publish_apk(source, self.apk, hashlib.sha256(self.data).hexdigest())
        self.assertEqual(self.apk.read_bytes(), self.data)
        self.assertEqual(sorted(path.name for path in self.root.iterdir()),
                         ["fieldlog.apk", "unsigned.apk", "verification"])

    def test_existing_path_refuses_before_build(self):
        self.apk.symlink_to(self.root / "absent")
        with (
            patch.object(replay.Replay, "execute") as execute,
            patch.object(sys, "argv", ["replay.py", "--receipt", str(self.receipt), "--apk-output", str(self.apk)]),
            contextlib.redirect_stderr(io.StringIO()) as errors,
            self.assertRaises(SystemExit) as raised,
        ):
            replay.main()
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("already exists", errors.getvalue())
        execute.assert_not_called()
        self.assertTrue(self.apk.is_symlink())


if __name__ == "__main__":
    unittest.main()
