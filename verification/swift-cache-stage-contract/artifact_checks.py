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

    def test_mutated_contracts_fail_closed(self):
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
            ("whole implementation authorization", lambda p: p.update(whole_cache_implementation_authorized=True)),
            ("freeze status", lambda p: p.update(root_freeze="accepted")),
            ("policy table ceiling", lambda p: p["fixture_contract"].update(table_host_maximum=65536)),
            ("initializer accessor", lambda p: p["descriptor_contract"].update(global_initializer_offset_accessor="GlobalView.offset")),
            ("lost rejected cache", lambda p: p["cleanup_contract"].update(preflight_rejection="drop cache on foreign control")),
            ("temporary-only cleanup charge", lambda p: p["cleanup_contract"].update(permanent_cleanup_envelope="construction phase only")),
            ("cleanup ticket", lambda p: p["cleanup_contract"].update(cleanup_ticket_count=1)),
            ("cleanup admission", lambda p: p["cleanup_contract"].update(cleanup_admission_allowed=True)),
            ("cleanup work", lambda p: p["cleanup_contract"].update(cleanup_work_allowed=True)),
            ("cleanup deadline", lambda p: p["cleanup_contract"].update(cleanup_cancel_deadline_checks_allowed=True)),
            ("tail new reservation", lambda p: p["cleanup_tail_contract"].update(reservation="new ticket")),
            ("tail large return wrapper", lambda p: p["cleanup_tail_contract"].update(completion_returns="Result<Option<SwiftFunctionCache>, Failure>")),
            ("tail early refund", lambda p: p["cleanup_tail_contract"].update(empty_slot_and_large_result_dropped_before_refund=False)),
            ("tail omission refund", lambda p: p["cleanup_tail_contract"].update(omitted_completion="refund header")),
            ("tail invented foundation slack", lambda p: p["cleanup_tail_contract"]["foundation_named_counts"].update(SwiftRunFailure=5)),
            ("foreign counters", lambda p: p["observation_contract"].update(foreign_or_missing_header_usage="actual current WasiUsage")),
            ("missing same-owner counters", lambda p: p["observation_contract"].update(same_owner_ledger_invariant_usage="None")),
            ("weak identity predicate", lambda p: p["observation_contract"].update(identity_predicate="category bytes only")),
            ("pairing checks cancellation", lambda p: p["observation_contract"].update(pairing_admission_work_cancel_deadline_checks_allowed=True)),
            ("changed dispatch", lambda p: p["observation_contract"].update(existing_dispatch_changes=True)),
            ("rewritten history", lambda p: p.update(historical_v1_manifest_sha256="0" * 64)),
        ]
        for label, mutate in cases:
            with self.subTest(label=label):
                candidate = copy.deepcopy(source)
                mutate(candidate)
                with self.assertRaises(ValueError):
                    check_contract.validate_plan(candidate)

    def test_changed_historical_bytes_fail_closed(self):
        plan = check_contract.check()
        with patch.object(Path, "read_bytes", return_value=b"changed historical bytes"):
            with self.assertRaises(ValueError):
                check_contract.check_history(plan)


if __name__ == "__main__":
    unittest.main()
