"""Finite C5 stream/export authority controls; no Docker calls."""
import json
import unittest

import run_container as candidate


class ExportControls(unittest.TestCase):
    def test_exact_selected_fixed_artifacts(self):
        selected = json.loads(candidate.SELECTION.read_text())
        self.assertEqual(candidate.EXPORTS, selected["fixedExports"])
        self.assertEqual(candidate.EXPORT_TOTAL, selected["selectedBounds"]["fixedExportAggregateBytes"])
        self.assertEqual(candidate.sha(candidate.SELECTION), candidate.SELECTION_SHA)

    def test_glob_path_traversal_and_unlisted_export_refuse(self):
        for name in ("*", "../compiler-payload.tar", "/tmp/compiler-payload/compiler-payload.tar", "entries.tsv", "image.tar"):
            with self.assertRaises(ValueError):
                candidate.export_limit(name)

    def test_per_artifact_aggregate_and_ordinary_caps(self):
        self.assertEqual(candidate.output_allowance("compiler-payload.tar", 268435455, 268435455, 0), 1)
        self.assertEqual(candidate.output_allowance("payload-manifest.json", 16777216, 0, 0), 0)
        self.assertEqual(candidate.output_allowance("control-inventory.json", 0, candidate.EXPORT_TOTAL, 0), 0)
        self.assertEqual(candidate.output_allowance(None, 0, 0, candidate.LIMIT-65536), 0)
        self.assertEqual(candidate.output_allowance(None, 0, 0, candidate.LIMIT-65536, True), 65536)


if __name__ == "__main__":
    unittest.main()
