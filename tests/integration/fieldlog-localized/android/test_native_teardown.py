"""Verify the final checkpoints with disposable processes and canned ADB output."""

import errno
import os
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

import native_teardown


class NativeTeardownTests(unittest.TestCase):
    def test_successful_blank_reverse_listing(self):
        for output in (b"", b"\n", b" \t\r\n"):
            with self.subTest(output=output):
                self.assertTrue(native_teardown.reverse_is_empty(
                    subprocess.CompletedProcess(["adb", "reverse", "--list"], 0, output)
                ))

    def test_reverse_mapping_blocks_offline_checkpoint(self):
        self.assertFalse(native_teardown.reverse_is_empty(
            subprocess.CompletedProcess(["adb", "reverse", "--list"], 0, b"usb tcp:6100 tcp:6100\n")
        ))

    def test_failed_reverse_command_cannot_qualify(self):
        with self.assertRaises(subprocess.CalledProcessError):
            native_teardown.reverse_is_empty(
                subprocess.CompletedProcess(["adb", "reverse", "--list"], 1, b"\n")
            )

    def test_observes_real_group_until_member_exits_after_child_reap(self):
        worker = """
import os

if os.fork() != 0:
    os._exit(0)
os.read(0, 1)
"""
        process = subprocess.Popen(
            [sys.executable, "-IB", "-c", worker], stdin=subprocess.PIPE, start_new_session=True,
        )
        killpg = os.killpg
        seen_present = False

        def observe(pgid, sig):
            nonlocal seen_present
            self.assertEqual((pgid, sig, process.returncode), (process.pid, 0, 0))
            killpg(pgid, sig)
            if not seen_present:
                seen_present = True
                process.stdin.close()

        try:
            with patch.object(native_teardown.os, "killpg", side_effect=observe):
                self.assertEqual(native_teardown.reap_owned_session(process), 0)
            self.assertTrue(seen_present, "the first observation must catch a remaining member")
        finally:
            process.stdin.close()

    def test_direct_child_timeout_does_not_observe_group(self):
        process = Mock(pid=219, **{"wait.side_effect": subprocess.TimeoutExpired("emulator", 16)})
        with patch.object(native_teardown.os, "killpg") as observe:
            with self.assertRaisesRegex(native_teardown.UnknownCustody, "not reaped"):
                native_teardown.reap_owned_session(process)
            observe.assert_not_called()

    def test_observation_error_keeps_custody_unknown(self):
        process = Mock(pid=219, **{"wait.return_value": 0})
        with patch.object(native_teardown.os, "killpg", side_effect=PermissionError(errno.EPERM, "denied")):
            with self.assertRaisesRegex(native_teardown.UnknownCustody, "Could not observe"):
                native_teardown.reap_owned_session(process)

    def test_group_past_deadline_keeps_custody_unknown(self):
        process = Mock(pid=219, **{"wait.return_value": 0})
        with (
            patch.object(native_teardown.os, "killpg") as observe,
            patch.object(native_teardown.time, "monotonic", side_effect=(0, 0, 0, 4)),
            patch.object(native_teardown.time, "sleep"),
        ):
            with self.assertRaisesRegex(native_teardown.UnknownCustody, "remained after child exit 0"):
                native_teardown.reap_owned_session(process)
            observe.assert_called_with(219, 0)


if __name__ == "__main__":
    unittest.main()
