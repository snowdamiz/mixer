#!/usr/bin/env python3
"""Exercise replay cleanup with inert command receipts."""
from contextlib import redirect_stderr
import errno
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import replay


class ReplayCleanupTest(unittest.TestCase):
    def run_failure(self, stage, exit_code, *, fail_hold=False):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        base_outputs = [replay.PINS["mixerBaseTree"], replay.PINS["maintainedPairTree"]]
        self.enterContext(patch.object(replay, "REPO", self.root))
        self.enterContext(patch.object(replay, "PAIR", self.root / "engine-pair"))
        self.enterContext(patch.object(replay, "output", side_effect=base_outputs))
        self.enterContext(patch.object(replay, "run"))

        def run_phase(campaign, _custody, label, _argv, _deadline):
            self.campaign = campaign
            row = {"command": [], "minimumFreeBytes": 1024, "exit": exit_code if label == stage else 0,
                   "ownedGroupAbsent": True, "pid": 2345, "pgid": 2345}
            (campaign / f"{label}.json").write_text(json.dumps(row))
            if label == stage:
                raise RuntimeError("injected supervisor failure")

        pair = SimpleNamespace(STOP_FREE=0, Custody=lambda: SimpleNamespace(pending=None),
                               run=run_phase)
        self.enterContext(patch.object(replay.importlib.util, "spec_from_file_location",
                                       return_value=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _: None))))
        self.enterContext(patch.object(replay.importlib.util, "module_from_spec", return_value=pair))
        if fail_hold:
            open_path = Path.open

            def refuse_hold(path, *args, **kwargs):
                if path.name == "HOLD.json":
                    raise OSError(errno.ENOSPC, "injected hold write failure")
                return open_path(path, *args, **kwargs)

            self.enterContext(patch.object(Path, "open", refuse_hold))

        self.stderr = StringIO()
        with redirect_stderr(self.stderr), self.assertRaisesRegex(RuntimeError, "injected supervisor failure"):
            replay.replay(None)

    def assert_hold(self, exit_code):
        self.assertTrue(self.campaign.is_dir(), "unresolved compiler scratch was deleted")
        hold = json.loads((self.campaign / "HOLD.json").read_text())
        self.assertEqual(hold["stage"], "build")
        self.assertIn("compiler", hold["reason"])
        self.assertEqual(hold["wrapper"], {"pid": 2345, "pgid": 2345, "exit": exit_code,
                                           "ownedGroupAbsent": True})

    def test_build_wrapper_nonzero_retains_scratch_and_writes_hold(self):
        self.run_failure("build", 1)
        self.assert_hold(1)

    def test_deadline_with_zero_wrapper_exit_retains_scratch_and_writes_hold(self):
        self.run_failure("build", 0)
        self.assert_hold(0)

    def test_signal_exit_records_unresolved_compiler_custody(self):
        self.run_failure("build", -15)
        self.assert_hold(-15)

    def test_hold_write_failure_preserves_scratch_and_original_error(self):
        self.run_failure("build", 1, fail_hold=True)
        self.assertTrue(self.campaign.is_dir())
        self.assertIn("hold write failure", self.stderr.getvalue())

    def test_closed_prebuild_failure_removes_scratch(self):
        self.run_failure("bind", 1)
        self.assertFalse(self.campaign.exists())


if __name__ == "__main__":
    unittest.main()
