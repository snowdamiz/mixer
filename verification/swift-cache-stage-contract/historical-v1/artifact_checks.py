#!/usr/bin/env python3
"""Original tests of the contract-artifact checker, not the VM implementation."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import check_contract


class ContractArtifactChecks(unittest.TestCase):
    def test_consistent_contract_reports_pending(self):
        plan = check_contract.check()
        self.assertEqual(len(plan["tests"]), 18)
        self.assertFalse(plan["target_execution_authorized"])
        self.assertTrue(all(test["status"] == "pending" for test in plan["tests"]))

    def test_eight_mutated_contracts_fail_closed(self):
        source = json.loads((Path(__file__).parent / "acceptance.json").read_text())
        cases = [
            ("target guard", lambda p: p.update(target_execution_authorized=True)),
            ("device guard", lambda p: p.update(device_runs_authorized=True)),
            ("root freeze", lambda p: p.update(root_freeze_required=False)),
            ("missing test", lambda p: p["tests"].pop()),
            ("duplicate test", lambda p: p["tests"].__setitem__(0, p["tests"][1])),
            ("false implementation pass", lambda p: p["tests"][0].update(status="passed")),
            ("raised ticket ceiling", lambda p: p["fixed_inventory"].update(runtime_ticket_maximum=87)),
            ("fixture instantiation", lambda p: p["fixture_contract"].update(instantiation_permitted_by_this_cache_suite=True)),
        ]
        for label, mutate in cases:
            with self.subTest(label=label):
                candidate = copy.deepcopy(source)
                mutate(candidate)
                with patch.object(Path, "read_text", return_value=json.dumps(candidate)):
                    with self.assertRaises(ValueError):
                        check_contract.check()


if __name__ == "__main__":
    unittest.main()
