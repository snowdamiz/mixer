"""Inert controls for the F02 runner's receipt and scratch custody."""
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, call, patch

import replay


class CustodyTests(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix="f02-inert-"))).resolve()
        self.scratch = root / "scratch"
        self.scratch.mkdir()
        self.sentinel = self.scratch / "sentinel"
        self.sentinel.write_bytes(b"preserve exact scratch")
        self.output = root / "receipt.json"
        self.argv = ["replay.py", "--mixer", str(root), "--fieldlog", str(root),
                     "--receipt", str(self.output)]

    def run_control(self, launch, observe):
        with (patch.object(sys, "argv", self.argv),
              patch.object(replay.tempfile, "mkdtemp", return_value=str(self.scratch)),
              patch.object(replay.subprocess, "Popen", side_effect=launch) as popen,
              patch.object(replay.os, "killpg", side_effect=observe) as killpg,
              patch.object(replay.Replay, "git", side_effect=RuntimeError("End of inert control"))):
            try:
                status = replay.main()
            except KeyboardInterrupt:
                status = 130
        result = json.loads(self.output.read_bytes())
        self.assertEqual(result["scratch"], str(self.scratch))
        self.assertEqual(result["status"], "INCOMPLETE")
        return status, result, popen, killpg

    def child(self):
        child = Mock(spec=subprocess.Popen, pid=43210, returncode=0,
                     stdout=BytesIO(), stderr=BytesIO())
        child.communicate.return_value = (b"inert stdout", b"")
        return child

    def test_interrupted_launch_preserves_scratch_without_child_identity(self):
        status, result, popen, killpg = self.run_control(KeyboardInterrupt, AssertionError)
        self.assertEqual(status, 130)
        self.assertEqual(self.sentinel.read_bytes(), b"preserve exact scratch")
        self.assertFalse(result["scratchRemoved"])
        self.assertFalse(result["processGroupsClosed"])
        self.assertEqual(result["reapedGroups"], 0)
        record = result["unresolvedCustody"]
        self.assertEqual(record["argv"], ["swift", "--version"])
        self.assertIsNone(record["pid"])
        self.assertIsNone(record["pgid"])
        self.assertFalse(record["groupAbsent"])
        popen.assert_called_once()
        killpg.assert_not_called()

    def test_group_still_present_preserves_scratch_after_direct_exit(self):
        status, result, popen, killpg = self.run_control([self.child()], [None])
        self.assertEqual(status, 1)
        self.assertEqual(self.sentinel.read_bytes(), b"preserve exact scratch")
        self.assertFalse(result["scratchRemoved"])
        self.assertFalse(result["processGroupsClosed"])
        self.assertEqual(result["reapedGroups"], 0)
        self.assertEqual(result["commands"][-1]["exit"], 0)
        self.assertFalse(result["commands"][-1]["groupAbsent"])
        popen.assert_called_once()
        killpg.assert_called_once_with(43210, 0)

    def test_confirmed_absence_allows_removal(self):
        status, result, popen, killpg = self.run_control(
            [self.child(), self.child()], [ProcessLookupError, ProcessLookupError])
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "End of inert control")
        self.assertTrue(result["scratchRemoved"])
        self.assertTrue(result["processGroupsClosed"])
        self.assertEqual(result["reapedGroups"], 2)
        self.assertNotIn("unresolvedCustody", result)
        self.assertFalse(self.scratch.exists())
        self.assertEqual(popen.call_count, 2)
        self.assertEqual(killpg.call_args_list, [call(43210, 0), call(43210, 0)])


if __name__ == "__main__":
    unittest.main()
