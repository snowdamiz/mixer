#!/usr/bin/env python3
"""Exercise S2 scratch cleanup with inert owner exits and a real recorder."""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import compare_row_snapshots as benchmark
import qualification_support


class RowSnapshotCleanupTests(unittest.TestCase):
    def check_owner_cleanup(self, exit_code, *, hash_fault, error, preserve):
        local = benchmark.ROOT / "verification/local"
        local.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="s2-row-cleanup-test-", dir=local))
        run_dir = root / "verification/local/run"
        record_command = qualification_support.CommandRecorder.run
        digest = qualification_support.digest
        records = []

        def cleanup_fixture():
            if any(record["terminalCustody"] == "UNKNOWN" for record in records):
                self.fail(f"Unresolved inert process custody. Preserved {root}")
            # Exit 74 is synthetic. No owner or guest was launched.
            shutil.rmtree(root)

        self.addCleanup(cleanup_fixture)

        def run_inert_owner(recorder, label, command, **options):
            if label.startswith("fixed34-"):
                script = ('print(\'validation=kind: AbiShape, code: "swift_import_count"\'); '
                          'raise SystemExit(10)')
            elif label == "eager-1":
                script = f"raise SystemExit({exit_code})"
            else:
                if label in ("build-eager", "build-deferred"):
                    Path(command[-1]).write_bytes(b"inert wasm placeholder")
                return "fixture\n"
            try:
                return record_command(recorder, label, [sys.executable, "-c", script], **options)
            finally:
                records[:] = recorder.commands

        def hash_log(path):
            if hash_fault and path == run_dir / "logs/eager-1.stdout":
                raise OSError("injected owner log hash failure")
            return digest(path)

        with (patch.object(benchmark, "ROOT", root),
              patch.object(sys, "argv", ["compare_row_snapshots.py", "run"]),
              patch.object(benchmark.shutil, "which", return_value=sys.executable),
              patch.object(qualification_support.CommandRecorder, "run", run_inert_owner),
              patch.object(qualification_support, "digest", side_effect=hash_log)):
            with self.assertRaisesRegex(RuntimeError if hash_fault or preserve else ValueError, error):
                benchmark.main()

        receipt = json.loads((run_dir / "receipt.json").read_text())
        owner = receipt["commands"][-1]
        self.assertEqual(owner["name"], "eager-1")
        self.assertEqual(owner["exitCode"], exit_code)
        self.assertEqual(owner["terminalCustody"], "TERMINAL")
        if hash_fault:
            self.assertEqual(owner["stdout"]["error"], "injected owner log hash failure")
        self.assertFalse(receipt["completed"])
        self.assertEqual((run_dir / "work").is_dir(), preserve)
        self.assertEqual(receipt.get("frozenOwner", False), preserve)
        self.assertIn("Preserve run directory" if preserve else "Disposable work removed",
                      receipt["cleanup"])

    def test_frozen_owner_with_log_hash_failure_preserves_scratch(self):
        self.check_owner_cleanup(74, hash_fault=True, error="could not record command log evidence",
                                 preserve=True)

    def test_frozen_owner_with_recorded_logs_preserves_scratch(self):
        self.check_owner_cleanup(74, hash_fault=False, error="Owner closure unresolved", preserve=True)

    def test_closed_owner_with_log_hash_failure_disposes_scratch(self):
        self.check_owner_cleanup(0, hash_fault=True, error="could not record command log evidence",
                                 preserve=False)

    def test_closed_owner_with_recorded_logs_disposes_scratch(self):
        self.check_owner_cleanup(0, hash_fault=False, error="differed from the six exact Node frames",
                                 preserve=False)


if __name__ == "__main__":
    unittest.main()
