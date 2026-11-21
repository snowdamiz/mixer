import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "replay.py"
SPEC = importlib.util.spec_from_file_location("foundation_date_replay", SOURCE)
replay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay)


class ReplayPublicationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(dir=SOURCE.parent / "tests")))
        self.output = self.root / "receipt.json"
        self.scratch = None
        self.enterContext(patch.object(sys, "argv", [str(SOURCE), str(self.output)]))
        spawn = self.enterContext(patch.object(replay.os, "posix_spawn"))
        self.addCleanup(spawn.assert_not_called)

    def inert_payload(self, campaign):
        self.scratch = campaign.scratch
        (self.scratch / "probe.err").write_bytes(b"inert diagnostic")

    def test_replaced_destination_preserves_unrelated_evidence(self):
        def replace(campaign):
            self.inert_payload(campaign)
            self.output.rename(self.root / "original.json")
            self.output.write_bytes(b"unrelated evidence")
            campaign.save()

        with patch.object(replay.Campaign, "execute", autospec=True, side_effect=replace):
            with self.assertRaisesRegex(RuntimeError, "receipt destination changed"):
                replay.main()

        self.assertEqual(self.output.read_bytes(), b"unrelated evidence")
        self.assertEqual((self.scratch / "probe.err").read_bytes(), b"inert diagnostic")
        self.assertEqual(json.loads((self.scratch / "journal.json").read_text())["status"], "pass")

    def test_failed_final_serialization_preserves_diagnostics(self):
        dumps = json.dumps

        def fail_final(record, **kwargs):
            if record["status"] == "pass":
                raise OSError("injected final serialization failure")
            return dumps(record, **kwargs)

        with patch.object(replay.Campaign, "execute", autospec=True, side_effect=self.inert_payload):
            with patch.object(replay.json, "dumps", side_effect=fail_final):
                with self.assertRaisesRegex(OSError, "injected final serialization failure"):
                    replay.main()

        self.assertEqual((self.scratch / "probe.err").read_bytes(), b"inert diagnostic")

    def test_failed_final_sync_preserves_diagnostics_and_journal(self):
        with patch.object(replay.Campaign, "execute", autospec=True, side_effect=self.inert_payload):
            with patch.object(replay.os, "fsync", side_effect=OSError("injected final sync failure")):
                with self.assertRaisesRegex(OSError, "injected final sync failure"):
                    replay.main()

        self.assertEqual((self.scratch / "probe.err").read_bytes(), b"inert diagnostic")
        journal = json.loads((self.scratch / "journal.json").read_text())
        self.assertEqual(journal["scratch"]["path"], str(self.scratch))

    def test_published_receipt_exists_when_cleanup_begins(self):
        remove = replay.shutil.rmtree

        def check_receipt(scratch):
            published = json.loads(self.output.read_text())
            self.assertEqual(published["status"], "pass")
            self.assertEqual(published["scratch"]["path"], str(scratch))
            remove(scratch)

        with patch.object(replay.Campaign, "execute", autospec=True, side_effect=self.inert_payload):
            with patch.object(replay.shutil, "rmtree", side_effect=check_receipt):
                replay.main()

        self.assertFalse(os.path.lexists(self.scratch))


if __name__ == "__main__":
    unittest.main()
