"""Finite export authority controls; no Docker or native execution."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

import run_container as candidate


class ExportControls(unittest.TestCase):
    def setUp(self):
        self.addendum = json.loads(candidate.ADDENDUM.read_text())
        self.allowed = candidate.checked_budgets(self.addendum)

    def test_fixed_set_and_declared_bound(self):
        self.assertEqual(len(self.allowed), 15)
        self.assertEqual(sum(x.get("maximumBytes", x.get("bytes", 0)) for x in self.allowed.values()), 929433)

    def test_unlisted_traversal_or_glob_refuses(self):
        for name in ("../base-status", "/tmp/compiler-metadata/base-status", "*", "noble.Packages", "directory.tar", "solver.stdout/../base-status"):
            with self.assertRaises(ValueError):
                candidate.checked_export(name, b"", self.allowed)

    def test_exact_export_length_and_digest(self):
        data = b"exact fixture"
        allowed = {"base-status": {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}}
        candidate.checked_export("base-status", data, allowed)
        for bad in (data[:-1], b"x"+data[1:], data+b"x"):
            with self.assertRaises(ValueError):
                candidate.checked_export("base-status", bad, allowed)

    def test_named_maximum_and_per_command_bound(self):
        candidate.checked_export("solver.stderr", b"x"*65536, self.allowed)
        with self.assertRaises(ValueError):
            candidate.checked_export("solver.stderr", b"x"*65537, self.allowed)
        with self.assertRaises(ValueError):
            candidate.checked_export("solver.stdout", b"x"*(candidate.LIMIT+1), {"solver.stdout": {"maximumBytes": candidate.LIMIT+2}})

    def test_changed_budget_or_export_set_refuses(self):
        for key, value in (("ordinaryStdoutBytes", 1048576), ("ordinaryStderrBytes", 1048576),
                           ("perExportCommandStdoutBytes", 1048576), ("fixedArtifactAggregateBytes", 4194304),
                           ("selectionSHA256", "a"*64)):
            changed = copy.deepcopy(self.addendum)
            changed[key] = value
            with self.assertRaises(ValueError):
                candidate.checked_budgets(changed)
        changed = copy.deepcopy(self.addendum)
        changed["allowedExports"]["extra"] = {"maximumBytes": 1}
        with self.assertRaises(ValueError):
            candidate.checked_budgets(changed)

    def test_exact_retained_metadata_and_config(self):
        candidate.checked_inputs(candidate.HERE/"inputs")
        for name in ("linux-compiler-metadata-v2-selection.json", "linux-compiler-metadata-v2-export-addendum.json"):
            path = candidate.ROOT/"verification/stripe-webhook-resource-ingress-root-review"/name
            expected = candidate.ADDENDUM_SHA if "addendum" in name else candidate.SELECTION_SHA
            self.assertEqual(candidate.sha(path), expected)

    def test_phase_source_retains_only_selected_fixture_repair(self):
        previous = candidate.ROOT/"verification/stripe-resource-linux-compiler-metadata"
        proposed = (previous/"verify-fixture-repair-proposed.sh").read_text()
        authenticate = (candidate.HERE/"inputs/authenticate.sh").read_text()
        resolve = (candidate.HERE/"inputs/resolve.sh").read_text()
        self.assertTrue(authenticate.endswith(proposed[proposed.index("signer="):proposed.index("# Finite negative controls")]))
        suffix = proposed[proposed.index("# Finite negative controls"):].replace("MIXER_METADATA_C2_COMPLETED", "MIXER_METADATA_C3_COMPLETED")
        self.assertTrue(resolve.endswith(suffix))


if __name__ == "__main__":
    unittest.main()
