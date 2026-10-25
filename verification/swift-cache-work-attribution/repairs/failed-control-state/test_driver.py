#!/usr/bin/env python3
"""Host-only process-observation controls; no guest or native execution."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import subprocess

spec = importlib.util.spec_from_file_location("work_attribution_driver", Path(__file__).with_name("driver.py"))
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class ProcessObservationTests(unittest.TestCase):
    def test_present_killpg_does_not_query_ps(self):
        with patch.object(driver.os, "killpg"), patch.object(driver.subprocess, "run") as query:
            self.assertEqual(driver.observe_group(123)["state"], "present")
            query.assert_not_called()

    def test_esrch_is_absent_without_ps(self):
        with patch.object(driver.os, "killpg", side_effect=ProcessLookupError(3, "No such process")), patch.object(driver.subprocess, "run") as query:
            self.assertEqual(driver.observe_group(123)["state"], "absent")
            query.assert_not_called()

    def probe_eperm(self, stdout, stderr="", code=0):
        with patch.object(driver.os, "killpg", side_effect=PermissionError(1, "Operation not permitted")), patch.object(driver.subprocess, "run", return_value=SimpleNamespace(stdout=stdout, stderr=stderr, returncode=code)):
            return driver.observe_group(123)

    def test_eperm_exact_ps_absence_is_absent(self):
        result = self.probe_eperm(" 456 1 456 S /usr/bin/other\n")
        self.assertEqual(result["state"], "absent")
        self.assertEqual(result["exactGroupRows"], [])
        self.assertTrue(result["psCompleteParse"])

    def test_eperm_exact_ps_member_is_present(self):
        result = self.probe_eperm(" 789 1 123 S /usr/bin/owned\n 456 1 456 S /usr/bin/other\n")
        self.assertEqual(result["state"], "present")
        self.assertEqual(result["exactGroupRows"], [" 789 1 123 S /usr/bin/owned"])

    def test_eperm_malformed_ps_remains_unknown(self):
        self.assertEqual(self.probe_eperm("incomplete output\n")["state"], "unknown")

    def test_eperm_nonzero_ps_remains_unknown(self):
        self.assertEqual(self.probe_eperm("", code=1)["state"], "unknown")

    def test_eperm_ps_stderr_remains_unknown(self):
        self.assertEqual(self.probe_eperm("", stderr="permission denied")["state"], "unknown")

    def test_eperm_ps_timeout_remains_unknown(self):
        with patch.object(driver.os, "killpg", side_effect=PermissionError(1, "Operation not permitted")), patch.object(driver.subprocess, "run", side_effect=subprocess.TimeoutExpired(["/bin/ps"], 2)):
            self.assertEqual(driver.observe_group(123)["state"], "unknown")

    def test_expired_cleanup_envelope_never_waits_for_ps(self):
        with patch.object(driver.os, "killpg", side_effect=PermissionError(1, "Operation not permitted")), patch.object(driver.subprocess, "run") as query:
            result = driver.observe_group(123, driver.time.monotonic() - 1)
            self.assertEqual(result["state"], "unknown")
            self.assertEqual(result["psError"]["type"], "ObservationDeadlineExpired")
            query.assert_not_called()

    def test_non_permission_oserror_is_not_absence(self):
        with patch.object(driver.os, "killpg", side_effect=OSError(22, "invalid")), patch.object(driver.subprocess, "run", side_effect=OSError("ps unavailable")):
            self.assertEqual(driver.observe_group(123)["state"], "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
