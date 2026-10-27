"""R1-R3 executable regressions. Every number/owner is synthetic host data."""
from dataclasses import asdict, replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

import model as m
from helpers import (admitted_owner, complete_owner, handle, own_handle, policy,
                     reservation, selected_result)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class RetirementRegressions(unittest.TestCase):
    def test_cleanup_finite_separate_reservation_precedes_every_input_effect(self):
        for cleanup in (0, -1, True, m.U64_MAX + 1):
            root = m.TestRoot(policy(), startup_already_provisioned=True)
            with self.assertRaises(m.Refused): root.reserve(1, 1, cleanup_work=cleanup)
            self.assertEqual((root.used_work, root.used_storage, root.trace), (0, 0, []))
        root, paid = reservation(work=39)
        slots = [handle(inode=i) for i in range(13)]
        m.adopt_slots(paid, slots, **m.SLOT_ARGS)
        self.assertEqual((paid.work_left, paid.cleanup_left), (0, 1000))
        self.assertEqual(root.trace[0], ("reserve-operation-cleanup-storage", 39, 1000, 1000000))
        with self.assertRaises(m.Refused): paid.operation("unfunded", 1)
        self.assertEqual(paid.cleanup_left, 1000)
        token = paid.destroy()
        self.assertTrue(token.complete)
        self.assertEqual(root.used_storage, 1000000)
        token.release()
        self.assertEqual(root.used_storage, 0)

    def test_every_adoption_refusal_returns_exact_partial_outcome_and_raw_obligations(self):
        for failure in range(13):
            root, paid = reservation()
            hs = [handle(inode=i + 1) for i in range(13)]
            hs[failure].slot_valid = False
            with self.assertRaises(m.Refused) as caught:
                m.adopt_slots(paid, hs, **m.SLOT_ARGS)
            self.assertIs(caught.exception.outcome, paid.outcome)
            self.assertIs(paid.diagnostics[-1], caught.exception)
            self.assertEqual([h for h in paid.owned if type(h) is m.TestHandle], hs[:failure])
            self.assertEqual([s.state for s in paid.outcome.slots], ["adopted"] * failure + ["raw"] * (13 - failure))
            self.assertEqual([s.adoption_bit for s in paid.outcome.slots], [True] * failure + [False] * (13 - failure))
            token = paid.destroy()
            self.assertFalse(token.complete)
            self.assertTrue(all(not h.live for h in hs[:failure]))
            self.assertTrue(all(h.live for h in hs[failure:]))
            self.assertFalse(any(row[0] == "cleanup-effect" and row[1].startswith("retire-model-file:" + str(failure))
                                 for row in root.trace))
            with self.assertRaises(m.Refused): token.release()
            self.assertEqual(root.used_storage, 1000000)
            self.assertTrue(paid.outcome.carrier_live)
            self.assertFalse(paid.outcome.native_healthy_close_claim)

    def test_each_operation_exhaustion_preserves_states_roster_and_cleanup_partition(self):
        for allowed in range(39):
            # reserve insists on positive operations; consume one harmless unit
            # first for the zero-input-operation case.
            root, paid = reservation(work=allowed + 1)
            paid.operation("test-before-acquisition", 1)
            hs = [handle(inode=i) for i in range(13)]
            with self.assertRaises(m.Refused) as caught:
                m.adopt_slots(paid, hs, **m.SLOT_ARGS)
            self.assertIs(caught.exception.outcome, paid.outcome)
            adopted = allowed // 3
            self.assertEqual([h for h in paid.owned if type(h) is m.TestHandle], hs[:adopted])
            self.assertEqual(paid.cleanup_left, 1000)
            self.assertEqual(sum(s.adoption_bit for s in paid.outcome.slots), adopted)
            if allowed % 3:
                self.assertEqual(paid.outcome.slots[adopted].state, "validated")
            token = paid.destroy()
            self.assertFalse(token.complete)
            with self.assertRaises(m.Refused): token.release()
            self.assertEqual(root.used_storage, 1000000)

    def test_each_retirement_failure_retains_charge_original_failure_and_no_healthy_claim(self):
        root, paid = reservation()
        _, _, view = admitted_owner(paid)
        m.correlate_before_leaf(paid, view, selected_result(paid, view))
        count = len(paid.retirement_plan())
        self.assertEqual(count, 47)
        for failure in range(count):
            root, paid = reservation()
            _, _, view = admitted_owner(paid)
            selected = selected_result(paid, view)
            m.correlate_before_leaf(paid, view, selected)
            original = OSError(5, "retirement index " + str(failure))
            token = paid.destroy(fail_at=failure, original=original)
            self.assertFalse(token.complete)
            self.assertIs(paid.diagnostics[-1], original)
            with self.assertRaises(m.Refused): token.release()
            with self.assertRaises(m.Refused): paid.destroy()
            self.assertEqual(root.used_storage, 1000000)
            self.assertFalse(paid.outcome.native_healthy_close_claim)
            self.assertTrue(paid.outcome.carrier_live)
        print(json.dumps({"full_retirement_failure_indices": count}))

    def test_each_retirement_unwind_and_cleanup_exhaustion_retains_charge(self):
        for failure in range(47):
            root, paid = reservation()
            _, _, view = admitted_owner(paid)
            m.correlate_before_leaf(paid, view, selected_result(paid, view))
            with self.assertRaisesRegex(RuntimeError, "unwind"):
                paid.destroy(unwind_at=failure)
            self.assertIsNone(paid.outcome.complete_token)
            self.assertEqual(root.used_storage, 1000000)
            self.assertFalse(paid.outcome.native_healthy_close_claim)
        root, paid = reservation(cleanup=1)
        complete_owner(paid)
        token = paid.destroy()
        self.assertFalse(token.complete)
        self.assertEqual(paid.cleanup_left, 0)
        with self.assertRaises(m.Refused): token.release()
        self.assertEqual(root.used_storage, 1000000)

    def test_successful_complete_retirement_closes_model_files_and_destroys_all_places_once(self):
        root, paid = reservation()
        bodies, paths, view = admitted_owner(paid)
        selected = selected_result(paid, view)
        m.correlate_before_leaf(paid, view, selected)
        files = view.files + selected.files
        backing = bodies + paths[0] + paths[1] + (view.packet,) + selected.buffers
        self.assertTrue(all(h.live for h in files))
        self.assertTrue(all(b.live for b in backing))
        token = paid.destroy()
        self.assertTrue(token.complete)
        self.assertFalse(any(h.live for h in files))
        self.assertFalse(any(b.live for b in backing))
        self.assertFalse(selected.live or paid.outcome.carrier_live)
        self.assertEqual(paid.cleanup_left, 1000 - 47)
        self.assertEqual(root.used_storage, 1000000)
        self.assertTrue(all(s.adoption_bit and s.state == "retired" for s in paid.outcome.slots))
        token.release()
        self.assertEqual((root.used_storage, root.used_work), (0, 1001000))
        with self.assertRaises(m.Refused): token.release()
        self.assertFalse(paid.outcome.native_healthy_close_claim)

    def test_double_owner_adoption_close_release_and_forged_tokens_fail(self):
        root, paid = reservation()
        hs = [handle(inode=i) for i in range(13)]
        m.adopt_slots(paid, hs, **m.SLOT_ARGS)
        _, other = reservation()
        with self.assertRaises(m.Refused): m.adopt_slots(other, hs, **m.SLOT_ARGS)
        self.assertEqual(other.outcome.slots, [])
        with self.assertRaises(m.Refused): m.adopt_slots(paid, hs, **m.SLOT_ARGS)
        with self.assertRaises(AttributeError): hs[0].adopted = True
        with self.assertRaises(m.Refused): hs[0].close()
        with self.assertRaises(m.Refused): hs[0].close()
        with self.assertRaises(m.Refused): m.TestDestroyed(paid, True).release()
        with self.assertRaises(m.Refused): paid.release(None)
        self.assertEqual(root.used_storage, 1000000)
        token = paid.destroy()
        token.release()
        with self.assertRaises(m.Refused): hs[0].close()
        with self.assertRaises(m.Refused): m.acquire_body(other, hs[0], "source", 10)

    def test_path_packet_file_buffer_and_final22_retained_until_complete_retirement(self):
        root, paid = reservation()
        bodies, paths, view = admitted_owner(paid)
        self.assertEqual(len(bodies + paths[0] + paths[1]), 22)
        self.assertIs(view.packet.source_handle, view.files[12])
        self.assertIn(view.packet, paid.owned)
        for item in (view.packet, view.files[12], bodies[0], paths[0][0], paid.outcome):
            with self.assertRaises(m.Refused): paid.release(None)
            self.assertEqual(root.used_storage, 1000000)
        # Path packet may later retire early only with a reviewed extra protocol;
        # this model conservatively retains it through correlation/whole retirement.
        m.correlate_before_leaf(paid, view, selected_result(paid, view))
        self.assertTrue(view.packet.live and view.files[12].live)

    def test_original_read_and_allocation_error_identity_survives_failure_and_no_token(self):
        for where in ("read", "eof", "allocation"):
            root, paid = reservation()
            original = OSError(7, "same original " + where)
            h = handle(responses=[original] if where == "read" else [3, original])
            own_handle(paid, h)
            with self.assertRaises(m.Refused) as caught:
                if where == "allocation":
                    paid.allocate("failed", 3, m.AllocationContract(3, 2, 7), failure=original)
                else:
                    m.acquire_body(paid, h, "source", 100)
            self.assertIn(original, paid.diagnostics)
            self.assertIs(next(x for x in paid.diagnostics if x is original), original)
            self.assertEqual(root.used_storage, 1000000)
            self.assertTrue(h.live)
            self.assertIsNone(paid.outcome.complete_token)

    def test_allocation_requested_slack_and_original_error_backing_prepaid_atomically(self):
        contract = m.AllocationContract(3, 4, 5)
        root, paid = reservation(storage=11)
        with self.assertRaises(m.Refused): paid.allocate("denied", 3, contract)
        self.assertNotIn("allocate:denied", paid.effects)
        self.assertEqual(paid.storage_left, 11)
        root, paid = reservation(storage=12)
        body = paid.allocate("allowed", 3, contract)
        self.assertEqual((body.allocation_bound, paid.storage_left), (12, 0))
        for invalid in (m.AllocationContract(2, 9), m.AllocationContract(3, -1),
                        m.AllocationContract(m.U64_MAX, 1), 3, {"capacity": 3}):
            _, trial = reservation()
            with self.assertRaises(m.Refused): trial.allocate("invalid", 3, invalid)
            self.assertNotIn("allocate:invalid", trial.effects)


class AdmissionRegressions(unittest.TestCase):
    def attempt(self, mutator):
        root, paid = reservation()
        _, _, view = admitted_owner(paid)
        provenance = view.correspondence.mapping()
        mutator(provenance)
        selected = selected_result(paid, view, provenance)
        with self.assertRaises(m.Refused) as caught:
            m.correlate_before_leaf(paid, view, selected)
        self.assertNotIn("leaf-model-only", paid.effects)
        self.assertIs(caught.exception.outcome, paid.outcome)
        self.assertIs(paid.diagnostics[-1], caught.exception)
        self.assertIs(paid.outcome.loader_results[-1], selected)
        self.assertTrue(selected.live and all(h.live for h in selected.files))
        self.assertTrue(all(h.live for h in view.files))
        self.assertEqual(root.used_storage, 1000000)
        return paid, view, selected

    def test_closed_expected_value_is_derived_from_actual_admitted_bodies_and_full_identities(self):
        _, paid = reservation()
        bodies, _, view = admitted_owner(paid)
        expected = view.correspondence
        for field, index in (("source", 0), ("manifest", 6), ("build", 1), ("session", 2), ("executable", 3)):
            self.assertEqual(getattr(expected, field), hashlib.sha256(bodies[index].data).digest())
        self.assertEqual((expected.nonce, expected.validation, expected.extent),
                         (b"n" * 32, (1947, 1000000, 65536, 1000000, 10000), bodies[0].length))
        self.assertEqual(expected.actual4, tuple(h.identity for h in view.files[:4]))
        self.assertEqual(len(asdict(expected.actual4[0])), 8)

    def test_equal_empty_incomplete_extra_and_caller_expected_dictionaries_refuse(self):
        self.attempt(lambda p: p.clear())
        self.attempt(lambda p: p.update(extra=b"x"))
        for payload in ({}, {"source": b"s" * 32}):
            _, paid = reservation()
            _, _, view = admitted_owner(paid)
            with self.assertRaises(m.Refused): m.correlate_before_leaf(paid, view, payload, payload)
            self.assertNotIn("leaf-model-only", paid.effects)

    def test_every_provenance_field_omission_and_substitution_has_no_leaf(self):
        names = tuple(m.AdmittedLoaderCorrespondence.__dataclass_fields__)
        for key in names:
            self.attempt(lambda p, key=key: p.pop(key))
            self.attempt(lambda p, key=key: p.update({key: None}))
        for key in ("source", "manifest", "build", "session", "executable", "nonce"):
            self.attempt(lambda p, key=key: p.update({key: b"?" * 32}))
        self.attempt(lambda p: p.update(extent=p["extent"] + 1))

    def test_every_validator_limit_substitution_and_malformed_shape_has_no_leaf(self):
        for index in range(5):
            def change(p, index=index):
                value = list(p["validation"])
                value[index] += 1
                p["validation"] = tuple(value)
            self.attempt(change)
        for malformed in ((), (1,) * 4, (1,) * 6, [1] * 5, (1, 1, True, 1, 1), (1, 1, 0, 1, 1)):
            self.attempt(lambda p, malformed=malformed: p.update(validation=malformed))

    def test_every_full_identity_member_in_each_of_four_records_has_no_leaf(self):
        count = 0
        for slot in range(4):
            for field in m.TestFileIdentity.__dataclass_fields__:
                def change(p, slot=slot, field=field):
                    value = list(p["actual4"])
                    value[slot] = replace(value[slot], **{field: getattr(value[slot], field) + 1})
                    p["actual4"] = tuple(value)
                self.attempt(change)
                count += 1
        for malformed in ((), (None,) * 4, (m.TestFileIdentity(1, 1, 1),) * 3, [{}] * 4):
            self.attempt(lambda p, malformed=malformed: p.update(actual4=malformed))
        print(json.dumps({"full_identity_field_substitutions": count}))

    def test_digest_nonce_extent_shapes_fail_closed(self):
        for field in ("source", "manifest", "build", "session", "executable", "nonce"):
            for invalid in (b"", b"x" * 31, b"x" * 33, "a" * 64, bytearray(32), 0):
                self.attempt(lambda p, field=field, invalid=invalid: p.update({field: invalid}))
        for invalid in (0, -1, True, m.U64_MAX + 1, "6"):
            self.attempt(lambda p, invalid=invalid: p.update(extent=invalid))

    def test_second_reservation_retires_replacement_and_consumed_generation_cannot_dispatch(self):
        for change in ("second-reservation", "retired", "replaced", "consumed-success", "consumed-refusal"):
            root, paid = reservation()
            _, _, view = admitted_owner(paid)
            selected = selected_result(paid, view)
            target = paid
            if change == "second-reservation":
                _, target = reservation()
            elif change == "retired":
                paid.destroy().release()
            elif change == "replaced":
                paid.replace_generation_model_only()
            elif change == "consumed-success":
                m.correlate_before_leaf(paid, view, selected)
                selected = selected_result(paid, view)
            else:
                selected.provenance["source"] = b"?" * 32
                with self.assertRaises(m.Refused): m.correlate_before_leaf(paid, view, selected)
                selected = selected_result(paid, view)
            before = target.effects.count("leaf-model-only")
            with self.assertRaises(m.Refused): m.correlate_before_leaf(target, view, selected)
            self.assertEqual(target.effects.count("leaf-model-only"), before)

    def test_exact_body_path_packet_and_file_owners_are_required_through_consumption(self):
        for missing in ("identity-body", "native-body", "retained-body", "packet-body", "file", "replacement-body"):
            _, paid = reservation()
            _, _, view = admitted_owner(paid)
            selected = selected_result(paid, view)
            if missing == "identity-body": view.bodies[0].live = False
            elif missing == "native-body": view.native[0].live = False
            elif missing == "retained-body": view.retained[0].live = False
            elif missing == "packet-body": view.packet.live = False
            elif missing == "file": view.files[12].live = False
            else: paid.owned.remove(view.bodies[0])
            with self.assertRaises(m.Refused): m.correlate_before_leaf(paid, view, selected)
            self.assertNotIn("leaf-model-only", paid.effects)

    def test_detached_constructed_view_and_admission_replay_fail(self):
        _, paid = reservation()
        bodies, paths, view = admitted_owner(paid)
        detached = replace(view)
        with self.assertRaises(m.Refused): m.correlate_before_leaf(paid, detached, selected_result(paid, view))
        with self.assertRaises(m.Refused): m.admit_model_only(paid, bodies, paths,
            trusted_local_launch_contract=True, all_actual_correspondence=True, review_provenance=True)
        self.assertNotIn("leaf-model-only", paid.effects)

    def test_distinct_loader_handles_same_immutable_objects_are_valid_and_both_sets_remain_live(self):
        root, paid = reservation()
        bodies, paths, view = admitted_owner(paid)
        selected = selected_result(paid, view)
        self.assertTrue(all(a is not b and a.identity == b.identity for a, b in zip(view.files, selected.files)))
        before = paid.storage_left
        result = m.correlate_before_leaf(paid, view, selected)
        self.assertEqual(selected.leaf_result, result)
        self.assertEqual(paid.effects.count("leaf-model-only"), 1)
        self.assertTrue(selected.live and all(h.live for h in view.files + selected.files))
        self.assertTrue(all(b.live for b in bodies + paths[0] + paths[1] + selected.buffers))
        self.assertEqual(root.used_storage, 1000000)
        self.assertEqual(paid.storage_left, before)

    def test_actual_selected_handles_and_content_must_match_even_with_complete_equal_labels(self):
        for change in ("identity", "body", "final-metadata", "aliased-file"):
            _, paid = reservation()
            _, _, view = admitted_owner(paid)
            selected = selected_result(paid, view)
            if change == "identity": selected.files[0].identity = replace(selected.files[0].identity, inode=999)
            elif change == "body": selected.files[0].body = b"different bytes"
            elif change == "final-metadata": selected.files[0].final_identity = replace(selected.files[0].identity, ctime_ns=99)
            else: selected.files = (selected.files[0],) * 4
            with self.assertRaises(m.Refused): m.correlate_before_leaf(paid, view, selected)
            self.assertNotIn("leaf-model-only", paid.effects)

    def test_work_exhaustion_after_selected_move_retains_both_owner_sets_and_original_error(self):
        root, paid = reservation()
        _, _, view = admitted_owner(paid)
        selected = selected_result(paid, view)
        paid.operation("consume-rest-operation-work", paid.work_left)
        with self.assertRaises(m.Refused) as caught: m.correlate_before_leaf(paid, view, selected)
        self.assertIs(paid.outcome.loader_results[0], selected)
        self.assertIs(paid.diagnostics[-1], caught.exception)
        self.assertNotIn("leaf-model-only", paid.effects)
        self.assertEqual(paid.cleanup_left, 1000)
        token = paid.destroy()
        self.assertTrue(token.complete)
        token.release()
        self.assertEqual(root.used_storage, 0)

    def test_session_verification_rejects_substitution_before_building_expected_value(self):
        for key in ("source", "manifest", "build", "executable", "nonce", "validation", "extent", "source_identity"):
            _, paid = reservation()
            bodies, paths = complete_owner(paid, record_change=lambda r, key=key: r.update({key: None}))
            with self.assertRaises(m.Refused): m.admit_model_only(paid, bodies, paths,
                trusted_local_launch_contract=True, all_actual_correspondence=True, review_provenance=True)
            self.assertIsNone(paid.outcome.admission)
        _, other = reservation()
        bodies, paths = complete_owner(other, record_change=lambda r: r.update(extra="substitution"))
        with self.assertRaises(m.Refused): m.admit_model_only(other, bodies, paths,
            trusted_local_launch_contract=True, all_actual_correspondence=True, review_provenance=True)


class PreservedBoundaryRegressions(unittest.TestCase):
    def test_four_original_defects_still_exist_in_unchanged_old_model(self):
        # New narrow witnesses, no historical runner/test replay. This confirms
        # the old/new behavioral delta without altering any retained failure.
        old_path = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-contract/model.py"
        spec = importlib.util.spec_from_file_location("old_prepaid_witness", old_path)
        old = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = old
        spec.loader.exec_module(old)
        def paid_old():
            root = old.TestRoot(old.TestPolicy(1000000, 1000000, (100000,) * 12,
                (10000,) * 5, 60000), startup_already_provisioned=True)
            return root, root.reserve(1000000, 1000000)
        _, old_paid = paid_old()
        slots = [old.TestHandle(b"x", old.TestFileIdentity(1, i, 1)) for i in range(13)]
        slots[2].slot_valid = False
        with self.assertRaises(old.Refused): old.adopt_slots(old_paid, slots, **m.SLOT_ARGS)
        self.assertEqual(sum(h.adopted for h in slots), 2)
        self.assertFalse(any(type(h) is old.TestHandle for h in old_paid.owned))
        root, old_paid = paid_old()
        slots = [old.TestHandle(b"x", old.TestFileIdentity(1, i, 1)) for i in range(13)]
        old.adopt_slots(old_paid, slots, **m.SLOT_ARGS)
        old_paid.destroy().release()
        self.assertEqual(root.used_storage, 0)
        self.assertTrue(all(h.slot_valid and h.adopted for h in slots))
        def view_old(paid):
            bodies = []
            for index, role in enumerate(old.ROLES):
                h = old.TestHandle(role.encode(), old.TestFileIdentity(1, index, len(role)))
                h.adopted = True
                bodies.append(old.acquire_body(paid, h, role, 100000)[0])
            paths = old.acquire_native_paths(paid, (b"/x",) * 5)
            return old.admit_model_only(paid, bodies, paths, trusted_local_launch_contract=True,
                all_actual_correspondence=True, review_provenance=True)
        _, old_paid = paid_old()
        view = view_old(old_paid)
        self.assertIn("model leaf", old.correlate_before_leaf(old_paid, view, {}, {}))
        old_paid.destroy().release()
        _, other = paid_old()
        self.assertIn("model leaf", old.correlate_before_leaf(other, view, {}, {}))
        print(json.dumps({"old_model_defect_witnesses_reproduced": 4,
                          "old_model_sha256": hashlib.sha256(old_path.read_bytes()).hexdigest()}))

    def test_minimum_interface_sequence_existing_opens_correlation_leaf_and_optional_route(self):
        interface = (HERE / "interface.inc.rs").read_text()
        sequence = interface.split("// Entry source sequence", 1)[1]
        self.assertLess(sequence.index("existing setup/loader opens"), sequence.index("private admitted-owner correlation"))
        self.assertLess(sequence.index("private admitted-owner correlation"), sequence.index("leaf only after complete correlation"))
        self.assertIn("SAME-handle loading above is OPTIONAL, a larger unselected route", sequence)
        self.assertNotIn("-> SAME-handle loader/leaf", sequence)

    def test_all_original_method_names_and_all16_independent_controls_retained(self):
        import ast
        def names(path, cls=None):
            tree = ast.parse(path.read_text())
            return [node.name for parent in tree.body if isinstance(parent, ast.ClassDef) and
                    (cls is None or parent.name == cls) for node in parent.body
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
        original = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-contract/test_model.py"
        review = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-independent/review_controls.py"
        self.assertEqual(names(original), names(HERE / "test_legacy.py"))
        self.assertEqual(len(names(original)), 28)
        self.assertEqual(names(review, "IndependentControls"), names(HERE / "test_independent_migrated.py", "IndependentControls"))
        self.assertEqual(len(names(review, "IndependentControls")), 16)


if __name__ == "__main__":
    unittest.main(verbosity=2)
