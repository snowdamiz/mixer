"""Exercise the exact replay cleanup path using inert launch/write failures."""
import errno
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from replay import Replay


class CustodyTest(unittest.TestCase):
    def setUp(self):
        # These controls own only inert fixture directories.
        self.fixture = tempfile.TemporaryDirectory()
        self.addCleanup(self.fixture.cleanup)
        self.work = Path(self.fixture.name) / "scratch"
        self.work.mkdir()
        self.marker = self.work / "preserve"
        self.marker.touch()
        self.replay = Replay(self.work)

    def test_group_present_and_receipt_write_fails(self):
        child = Mock(pid=123)
        child.wait.return_value = 0
        with patch("replay.subprocess.Popen", return_value=child), patch("replay.os.killpg") as group:
            with patch.object(Path, "write_text", side_effect=OSError(errno.ENOSPC, "inert receipt failure")):
                with self.assertRaises(OSError) as error:
                    self.replay.run("inert", 1, ["/usr/bin/true"])
            self.assertEqual(error.exception.errno, errno.ENOSPC)
            group.assert_called_once_with(123, 0)
        self.assertFalse(self.replay.cleanup())
        self.assertTrue(self.marker.is_file())

    def test_interrupted_launch_without_identity(self):
        with patch("replay.subprocess.Popen", side_effect=KeyboardInterrupt), patch("replay.os.killpg") as group:
            with self.assertRaises(KeyboardInterrupt):
                self.replay.run("inert", 1, ["/usr/bin/true"])
            group.assert_not_called()
        with self.assertRaisesRegex(RuntimeError, "custody is unresolved"):
            self.replay.run("inert-retry", 1, ["/usr/bin/true"])
        self.assertFalse(self.replay.cleanup())
        self.assertTrue(self.marker.is_file())

    def test_positive_terminal_allows_exact_cleanup(self):
        status, _ = self.replay.run("inert", 5, ["/usr/bin/true"])
        self.assertEqual(status, 0)
        self.assertTrue(self.replay.records["inert"]["ownedGroupAbsent"])
        self.assertTrue(self.replay.cleanup())
        self.assertFalse(self.work.exists())


if __name__ == "__main__":
    unittest.main()
