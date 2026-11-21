"""Inert refusal controls for the maintained allocation replay."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True

from run import checked_observations, publish_completed, verify_vm_archive


SCRIPT = Path(__file__).resolve().with_name("run.py")
EXACT_VM_HASH = "6a9ef08edafb9a3f9c35d3a98197584987a3b70cb429fddba6e1c562a927b822"
NO_RESULT = 4294967295


def exact_rows():
    fields = ("phase", "pages", "fuel", "hostCalls", "enomem", "fillAttempts", "fillResult",
              "retryResult", "live", "checkedBeforeRelease", "survivorsChecked",
              "replacementChecked", "sameAddress", "freed")
    session = [
        dict(zip(fields, values, strict=True)) for values in (
            (0, 1, 36, 0, 48, 0, NO_RESULT, NO_RESULT, 0, 0, 0, 0, 0, 0),
            (1, 1, 6785, 0, 48, 10, 48, NO_RESULT, 9, 0, 0, 0, 0, 0),
            (2, 1, 4535, 0, 48, 10, 48, 0, 9, 9, 8, 1, 1, 1),
            (3, 1, 4553, 0, 48, 10, 48, 0, 0, 9, 8, 1, 1, 10),
        )
    ]
    session.append(dict(closeStatus=0, retiredStartupStatus=3))
    reopen = dict(sameRegistrySlot=True, newGeneration=True, retiredAfterReopenStatus=3,
                  identicalFreshFrame=True)
    return [dict(guestUiV1ValidationStatus=0), *session, reopen, *copy.deepcopy(session)]


def stdout(rows):
    return "\n".join(map(json.dumps, rows)) + "\n"


class OutcomeControls(unittest.TestCase):
    def test_exact_outcome(self):
        rows = exact_rows()
        self.assertEqual(checked_observations(stdout(rows)), rows)

    def reject_repeatable_alternative(self, phase, changes):
        rows = exact_rows()
        for index in (phase + 1, phase + 7):
            rows[index].update(changes)
        self.assertEqual(rows[1:6], rows[7:12])
        with self.assertRaisesRegex(ValueError, "differs from the exact allocation"):
            checked_observations(stdout(rows))

    def test_wrong_count_in_both_sessions(self):
        self.reject_repeatable_alternative(1, dict(fillAttempts=9, live=8))

    def test_retry_enomem_in_both_sessions(self):
        self.reject_repeatable_alternative(2, dict(retryResult=48, live=8,
                                                   replacementChecked=0, sameAddress=0))

    def test_retry_different_address_in_both_sessions(self):
        self.reject_repeatable_alternative(2, dict(sameAddress=0))

    def test_independently_agreeing_wrong_vm_digest(self):
        wrong = "0" * 64
        verify_vm_archive({"sha256": EXACT_VM_HASH}, EXACT_VM_HASH)
        with self.assertRaisesRegex(ValueError, "reviewed VM archive SHA-256 mismatch"):
            verify_vm_archive({"sha256": wrong}, wrong)
        with self.assertRaisesRegex(ValueError, "reviewed VM archive SHA-256 mismatch"):
            verify_vm_archive({"sha256": EXACT_VM_HASH}, wrong)


class OutputControls(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="output-control-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.scratch = self.root / "scratch"
        self.output = self.root / "output.json"
        self.receipt = {
            "commands": [{"label": "inert", "exit": 0}],
            "custody": {"unknown": None, "reapedWithGroupAbsent": 1},
        }

    def assert_output_refused_before_launch(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--checkout", str(self.root),
             "--scratch", str(self.scratch), "--output", str(self.output)],
            text=True, capture_output=True, timeout=5, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("output already exists", result.stderr)
        self.assertFalse(self.scratch.exists())

    def test_existing_file_refused_before_launch(self):
        self.output.write_text("original")
        self.assert_output_refused_before_launch()
        self.assertEqual(self.output.read_text(), "original")

    def test_dangling_symlink_refused_before_launch(self):
        target = self.root / "missing"
        self.output.symlink_to(target)
        self.assert_output_refused_before_launch()
        self.assertEqual(self.output.readlink(), target)
        self.assertFalse(target.exists())

    def test_late_output_preserves_original_and_scratch(self):
        self.scratch.mkdir()
        log = self.scratch / "inert.out"
        log.write_text("custody evidence")
        self.output.write_text("late claimant")
        with self.assertRaises(FileExistsError):
            publish_completed(self.receipt, self.output, self.scratch)
        self.assertEqual(self.output.read_text(), "late claimant")
        self.assertEqual(log.read_text(), "custody evidence")
        self.assertTrue((self.scratch / "completed-receipt.json").is_file())

    def test_uncertain_publication_preserves_scratch(self):
        self.scratch.mkdir()
        log = self.scratch / "inert.out"
        log.write_text("custody evidence")
        with patch("run.os.fsync", side_effect=[None, OSError("directory sync failed")]):
            with self.assertRaisesRegex(OSError, "directory sync failed"):
                publish_completed(self.receipt, self.output, self.scratch)
        self.assertEqual(json.loads(self.output.read_text()), self.receipt)
        self.assertEqual(log.read_text(), "custody evidence")
        self.assertTrue((self.scratch / "completed-receipt.json").is_file())

    def test_incomplete_terminal_observation_preserves_scratch(self):
        self.scratch.mkdir()
        log = self.scratch / "inert.out"
        log.write_text("incomplete custody evidence")
        self.receipt["custody"]["unknown"] = {"label": "inert", "pid": None}
        with self.assertRaisesRegex(ValueError, "complete terminal command observations"):
            publish_completed(self.receipt, self.output, self.scratch)
        self.assertFalse(self.output.exists())
        self.assertEqual(log.read_text(), "incomplete custody evidence")

    def test_closed_publication_cleans_scratch(self):
        self.scratch.mkdir()
        publish_completed(self.receipt, self.output, self.scratch)
        self.assertEqual(json.loads(self.output.read_text()), self.receipt)
        self.assertFalse(self.scratch.exists())


if __name__ == "__main__":
    unittest.main()
