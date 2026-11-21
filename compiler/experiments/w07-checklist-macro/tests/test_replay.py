import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


source = Path(os.environ.get("W07_REPLAY_UNDER_TEST", Path(__file__).resolve().parents[1] / "replay.py"))
spec = importlib.util.spec_from_file_location("macro_replay", source)
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


class ReplayCustodyTests(unittest.TestCase):
    def setUp(self):
        workspace = self.enterContext(tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent))
        self.root = Path(workspace)
        self.scratch_parent = self.root / "verification/local"
        self.scratch_parent.mkdir(parents=True)
        self.destination = self.root / "new-receipt.json"
        self.addCleanup(os.chdir, Path.cwd())
        self.enterContext(patch.object(replay, "ROOT", self.root))
        self.set_limit = self.enterContext(patch.object(replay.resource, "setrlimit"))
        self.enterContext(patch.object(replay, "campaign", side_effect=self.launch_control))
        self.spawn = self.enterContext(patch.object(replay.os, "posix_spawn",
                                                  side_effect=OSError("injected launch/log setup error")))
        self.stderr = self.enterContext(patch.object(sys, "stderr", io.StringIO()))

    def launch_control(self, run):
        run.command("inert-launch", "/usr/bin/true")

    def run_main(self):
        with patch.object(sys, "argv", [str(source), str(self.destination)]):
            return replay.main()

    def assert_setup_failure(self, message):
        self.assertEqual(self.run_main(), 1)
        self.spawn.assert_not_called()
        report = json.loads(self.destination.read_text())
        self.assertEqual(report["status"], "incomplete")
        self.assertIn(message, report["failure"])
        scratch = Path(report["scratch"])
        self.assertEqual(scratch.parent, self.scratch_parent)
        self.assertFalse(scratch.exists())
        self.assertEqual(list(self.scratch_parent.iterdir()), [])

    def read_only_hold(self):
        scratch, = self.scratch_parent.iterdir()
        hold_path = scratch / "HOLD.json"
        hold = json.loads(hold_path.read_text())
        self.assertEqual(hold["status"], "HOLD")
        self.assertEqual(hold["scratch"], str(scratch))
        self.assertEqual(hold["receipt"], str(self.destination))
        self.assertEqual(hold["command"]["label"], "inert-launch")
        self.assertEqual(hold["command"]["custody"], "launch-unresolved")
        self.assertNotIn("pidPgid", hold["command"])
        return hold_path

    def test_constructor_failure_records_receipt_and_removes_owned_scratch(self):
        mkdir = Path.mkdir

        def fail_plugin_directory(path, *args, **kwargs):
            if path.name == "plugin":
                raise OSError("injected plugin directory failure")
            return mkdir(path, *args, **kwargs)

        with patch.object(Path, "mkdir", autospec=True, side_effect=fail_plugin_directory):
            self.assert_setup_failure("injected plugin directory failure")

    def test_limit_failure_records_receipt_and_removes_owned_scratch(self):
        self.set_limit.side_effect = OSError("injected size-limit failure")
        self.assert_setup_failure("injected size-limit failure")

    def test_missing_receipt_parent_refuses_before_launch(self):
        self.destination = self.root / "missing" / "new-receipt.json"
        with self.assertRaises(FileNotFoundError):
            self.run_main()
        self.spawn.assert_not_called()
        self.assertFalse(self.destination.parent.exists())
        self.assertEqual(list(self.scratch_parent.iterdir()), [])

    def test_existing_receipt_is_preserved(self):
        self.destination.write_bytes(b"historical receipt")
        with self.assertRaises((FileExistsError, ValueError)):
            self.run_main()
        self.spawn.assert_not_called()
        self.assertEqual(self.destination.read_bytes(), b"historical receipt")
        self.assertEqual(list(self.scratch_parent.iterdir()), [])

    def test_dangling_receipt_symlink_is_refused(self):
        target = self.root / "uncreated-target.json"
        self.destination.symlink_to(target)
        with self.assertRaises(FileExistsError):
            self.run_main()
        self.spawn.assert_not_called()
        self.assertTrue(self.destination.is_symlink())
        self.assertFalse(target.exists())
        self.assertEqual(list(self.scratch_parent.iterdir()), [])

    def test_unknown_launch_has_reserved_receipt_and_hold_before_spawn(self):
        def fail_launch(*args, **kwargs):
            self.assertTrue(self.destination.is_file())
            self.read_only_hold()
            raise OSError("injected launch/log setup error")

        self.spawn.side_effect = fail_launch
        self.assertEqual(self.run_main(), 1)
        self.spawn.assert_called_once()
        hold_path = self.read_only_hold()
        report = json.loads(self.destination.read_text())
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["hold"], str(hold_path))
        self.assertIn("injected launch/log setup error", report["failure"])
        self.assertEqual(report["commands"][0]["custody"], "launch-unresolved")

    def test_receipt_write_failure_leaves_prelaunch_hold_and_scratch(self):
        dump = json.dump

        def fail_final_write(obj, file, *args, **kwargs):
            if file.name == str(self.destination):
                raise OSError("injected final receipt write failure")
            return dump(obj, file, *args, **kwargs)

        with patch.object(replay.json, "dump", side_effect=fail_final_write):
            with self.assertRaisesRegex(OSError, "injected final receipt write failure"):
                self.run_main()
        self.spawn.assert_called_once()
        hold_path = self.read_only_hold()
        self.assertIn(str(hold_path), self.stderr.getvalue())
        self.assertTrue(self.destination.is_file())


if __name__ == "__main__":
    unittest.main()
