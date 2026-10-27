"""C1/C2 desired properties and adjacent branches; synthetic host owners only."""
from dataclasses import asdict, replace
import json
import unittest

import model as m
from helpers import admitted_owner, complete_owner, reservation

TRUST = dict(trusted_local_launch_contract=True, all_actual_correspondence=True,
             review_provenance=True)


def selected(paid, view, *, files=None, count=4):
    if files is None:
        files = [m.TestHandle(b.data, h.identity) for b, h in zip(view.bodies[:4], view.files[:4])]
    buffers = []
    for index, h in enumerate(files[:count]):
        body = paid.allocate("focused-loader:" + str(index), len(h.body))
        body.set_once(h.body)
        buffers.append(body)
    return m.TestSelectedResult(view.correspondence.mapping(), files, buffers)


class AffineRefusalControls(unittest.TestCase):
    def prepared(self):
        root, paid = reservation()
        _, _, view = admitted_owner(paid)
        return root, paid, view

    def refuse(self, paid, view, result, *extra):
        with self.assertRaises(m.Refused) as caught:
            m.correlate_before_leaf(paid, view, result, *extra)
        self.assertIs(caught.exception.outcome, paid.outcome)
        self.assertIs(paid.diagnostics[-1], caught.exception)
        self.assertEqual(paid.state, "consumed")
        self.assertNotIn("leaf-model-only", paid.effects)
        self.assertIs(paid.outcome.correlation.supplied, result)
        return caught.exception

    def test_four_files_three_buffers_retire_before_any_release(self):
        root, paid, view = self.prepared()
        result = selected(paid, view, count=3)
        original = self.refuse(paid, view, result)
        self.assertIs(result.owner, paid)
        self.assertEqual(paid.outcome.correlation.files, list(result.files))
        self.assertTrue(all(h.owner is paid and h.live for h in result.files))
        self.assertEqual(root.used_storage, 1000000)
        self.assertFalse(paid.outcome.correlation.unresolved)
        self.assertIs(paid.outcome.correlation.original_refusal, original)
        token = paid.destroy()
        self.assertTrue(token.complete)
        self.assertFalse(result.live or any(h.live for h in result.files) or any(b.live for b in result.buffers))
        self.assertIsNone(paid.outcome.correlation.original_refusal)
        self.assertIsNone(paid.outcome.correlation.replay_refusal)
        self.assertIsNone(paid.outcome.correlation.supplied)
        token.release()
        self.assertEqual(root.used_storage, 0)

    def test_three_buffer_refusal_cannot_retry_to_leaf_or_forget_later_owners(self):
        root, paid, view = self.prepared()
        bad = selected(paid, view, count=3)
        original = self.refuse(paid, view, bad)
        good = selected(paid, view)
        with self.assertRaises(m.Refused) as second: m.correlate_before_leaf(paid, view, good)
        self.assertIs(second.exception, original)
        self.assertIsNone(good.owner)
        self.assertTrue(all(h.owner is None and h.live and not h.adopted for h in good.files))
        self.assertTrue(paid.outcome.correlation.unresolved)
        token = paid.destroy()
        self.assertFalse(token.complete)
        with self.assertRaises(m.Refused): token.release()
        self.assertEqual(root.used_storage, 1000000)
        self.assertNotIn("leaf-model-only", paid.effects)

    def test_forbidden_expected_argument_is_consuming_owning_and_preserves_original(self):
        root, paid, view = self.prepared()
        result = selected(paid, view)
        original = self.refuse(paid, view, result, {})
        self.assertEqual(str(original), "caller expected dictionaries forbidden")
        with self.assertRaises(m.Refused) as retry: m.correlate_before_leaf(paid, view, result)
        self.assertIs(retry.exception, original)
        self.assertFalse(paid.outcome.correlation.unresolved)
        self.assertEqual(len(paid.retirement_plan()), 47)
        paid.destroy().release()
        self.assertEqual(root.used_storage, 0)

    def test_wrong_selected_type_has_explicit_owning_unresolved_refusal(self):
        for result in ({"files": []}, None, object(), [], "selected"):
            root, paid, view = self.prepared()
            self.refuse(paid, view, result)
            self.assertTrue(paid.outcome.correlation.unresolved)
            self.assertEqual(paid.outcome.correlation.files, [])
            token = paid.destroy()
            self.assertFalse(token.complete)
            with self.assertRaises(m.Refused): token.release()
            self.assertEqual(root.used_storage, 1000000)

    def test_adjacent_file_shape_counts_and_duplicates_are_safely_captured(self):
        for count in (0, 1, 3, 5):
            root, paid, view = self.prepared()
            files = [m.TestHandle(view.bodies[i % 4].data, view.files[i % 4].identity) for i in range(count)]
            result = selected(paid, view, files=files, count=min(count, 4))
            self.refuse(paid, view, result)
            self.assertEqual(len(paid.outcome.correlation.files), min(count, 4))
            token = paid.destroy()
            self.assertEqual(token.complete, count < 5)
            self.assertTrue(all(not h.live for h in files[:4]))
            if count == 5:
                self.assertTrue(files[4].live and files[4].owner is None)
                with self.assertRaises(m.Refused): token.release()
            else: token.release()
        root, paid, view = self.prepared()
        h = m.TestHandle(view.bodies[0].data, view.files[0].identity)
        result = selected(paid, view, files=[h] * 4)
        self.refuse(paid, view, result)
        self.assertEqual(paid.outcome.correlation.files, [h])
        paid.destroy().release()
        self.assertEqual(sum(row == ("cleanup-effect", "retire-model-loader-file") for row in root.trace), 1)

    def test_invalid_foreign_raw_dead_and_malformed_files_never_adopt_or_steal(self):
        for mode in ("invalid", "foreign", "raw", "dead", "adopted", "identity", "nonregular", "wrong-type"):
            root, paid, view = self.prepared()
            _, other = reservation()
            result = selected(paid, view)
            item = result.files[0]
            if mode == "invalid": item.slot_valid = False
            elif mode == "foreign": item.owner = other
            elif mode == "raw": item.raw_controller = other
            elif mode == "dead": item.live = False
            elif mode == "adopted": item._adopted = True
            elif mode == "identity": item.identity = replace(item.identity, inode=1.0)
            elif mode == "nonregular": item.identity = replace(item.identity, mode=0)
            else:
                item = object()
                result.files = (item,) + result.files[1:]
            before = (item.owner, item.raw_controller, item.adopted, item.live) if type(item) is m.TestHandle else None
            self.refuse(paid, view, result)
            self.assertTrue(paid.outcome.correlation.unresolved)
            self.assertFalse(any(item is h for h in paid.outcome.correlation.files))
            token = paid.destroy()
            self.assertFalse(token.complete)
            if before is not None:
                self.assertEqual((item.owner, item.raw_controller, item.adopted, item.live), before)
            self.assertTrue(all(not h.live for h in paid.outcome.correlation.files))
            with self.assertRaises(m.Refused): token.release()
            with self.assertRaises(m.Refused): paid.destroy()
            self.assertEqual(root.used_storage, 1000000)

    def test_buffer_counts_duplicates_shared_uninitialized_and_foreign_backing(self):
        for mode in ("empty", "three", "five", "duplicate", "shared", "uninitialized", "foreign", "forged", "wrong-type"):
            root, paid, view = self.prepared()
            result = selected(paid, view, count=3 if mode == "three" else 4)
            foreign = None
            if mode == "empty": result.buffers = ()
            elif mode == "five":
                body = paid.allocate("fifth", 1)
                body.set_once(b"x")
                result.buffers += (body,)
            elif mode == "duplicate": result.buffers = (result.buffers[0],) * 4
            elif mode == "shared": result.buffers = view.bodies[:4]
            elif mode == "uninitialized": result.buffers = (paid.allocate("empty-data", 1),) + result.buffers[1:]
            elif mode == "foreign":
                _, other = reservation()
                foreign = other.allocate("foreign", 1)
                foreign.set_once(b"x")
                result.buffers = (foreign,) + result.buffers[1:]
            elif mode == "forged":
                foreign = m.TestBody("unregistered", 1, 1, paid)
                foreign.set_once(b"x")
                result.buffers = (foreign,) + result.buffers[1:]
            elif mode == "wrong-type": result.buffers = (object(),) + result.buffers[1:]
            self.refuse(paid, view, result)
            unresolved = mode in ("five", "foreign", "forged", "wrong-type")
            self.assertEqual(paid.outcome.correlation.unresolved, unresolved)
            token = paid.destroy()
            self.assertEqual(token.complete, not unresolved)
            if unresolved:
                with self.assertRaises(m.Refused): token.release()
                self.assertEqual(root.used_storage, 1000000)
            else: token.release()
            if foreign is not None: self.assertTrue(foreign.live)

    def test_foreign_owned_or_dead_selected_carrier_is_not_stolen_or_resurrected(self):
        for mode in ("foreign", "dead"):
            root, paid, view = self.prepared()
            result = selected(paid, view)
            _, other = reservation()
            if mode == "foreign": result.owner = other
            else: result.live = False
            self.refuse(paid, view, result)
            token = paid.destroy()
            self.assertFalse(token.complete)
            self.assertTrue(all(h.owner is None and h.live for h in result.files))
            self.assertIs(result.owner, other if mode == "foreign" else None)
            self.assertEqual(result.live, mode != "dead")
            with self.assertRaises(m.Refused): token.release()
            self.assertEqual(root.used_storage, 1000000)

    def test_copied_foreign_and_replaced_view_refusal_consumes_actual_admission(self):
        for mode in ("copy", "foreign", "generation"):
            root, paid, view = self.prepared()
            result = selected(paid, view)
            _, other, foreign_view = self.prepared()
            original_foreign_files = tuple((h.owner, h.live) for h in foreign_view.files)
            supplied_view = replace(view) if mode == "copy" else foreign_view if mode == "foreign" else view
            if mode == "generation": paid.replace_generation_model_only()
            original = self.refuse(paid, supplied_view, result)
            with self.assertRaises(m.Refused) as retry: m.correlate_before_leaf(paid, view, result)
            self.assertIs(retry.exception, original)
            self.assertEqual(tuple((h.owner, h.live) for h in foreign_view.files), original_foreign_files)
            self.assertIs(foreign_view.paid, other)
            paid.destroy().release()
            self.assertEqual(root.used_storage, 0)

    def test_ingress_ticket_survives_operation_and_storage_exhaustion(self):
        root, paid, view = self.prepared()
        result = selected(paid, view)
        paid.operation("drain-ordinary-provisions", paid.work_left, paid.storage_left)
        original = self.refuse(paid, view, result)
        self.assertEqual(str(original), "operation before work prepay")
        self.assertEqual(paid.cleanup_left, 1000)
        self.assertEqual(paid.outcome.correlation.tickets_left, 1)
        self.assertEqual(len(paid.retirement_plan()), 47)
        paid.destroy().release()
        self.assertEqual(root.used_storage, 0)

    def test_admission_cannot_publish_an_unfunded_ingress_ticket(self):
        for dimension in ("work", "storage"):
            root, paid = reservation()
            bodies, paths = complete_owner(paid)
            if dimension == "work":
                before_ingress = 64 + sum(b.length for b in paths[0]) + bodies[2].length
                paid.operation("drain-before-ingress", paid.work_left - before_ingress - (m.INGRESS_UNITS - 1))
            else:
                paid.operation("drain-before-ingress", 1, paid.storage_left - (m.INGRESS_UNITS - 1))
            with self.assertRaises(m.Refused): m.admit_model_only(paid, bodies, paths, **TRUST)
            self.assertIsNone(paid.outcome.admission)
            self.assertFalse(paid.outcome.correlation.funded)
            self.assertNotIn("admit-model-only", paid.effects)
            self.assertFalse(any(row[0] == "funded-custody-effect" for row in root.trace))
            self.assertEqual(root.used_storage, 1000000)

    def test_replays_have_one_fixed_slot_and_no_collection_walk_or_new_ownership(self):
        class NeverWalk:
            def __iter__(self): raise AssertionError("caller collection iterated")
            def __len__(self): raise AssertionError("caller collection measured")
        root, paid, view = self.prepared()
        first = selected(paid, view, count=3)
        original = self.refuse(paid, view, first)
        late = NeverWalk()
        before = (paid.work_left, paid.storage_left, paid.cleanup_left, len(paid.owned))
        for index in range(100):
            with self.assertRaises(m.Refused) as caught: m.correlate_before_leaf(paid, view, late if index == 0 else NeverWalk())
            self.assertIs(caught.exception, original)
        self.assertEqual((paid.work_left, paid.storage_left, paid.cleanup_left, len(paid.owned)), before)
        self.assertEqual(paid.diagnostics, [original])
        self.assertIs(paid.outcome.correlation.late_supplied, late)
        self.assertEqual(paid.outcome.correlation.tickets_left, 0)
        effects = [r for r in root.trace if r[0] == "funded-custody-effect"]
        self.assertEqual(len(effects), m.INGRESS_UNITS)
        paid.replace_generation_model_only()
        with self.assertRaises(m.Refused): m.correlate_before_leaf(paid, view, first)
        self.assertEqual(len([r for r in root.trace if r[0] == "funded-custody-effect"]), m.INGRESS_UNITS)
        token = paid.destroy()
        self.assertFalse(token.complete)
        with self.assertRaises(m.Refused): token.release()
        self.assertEqual(root.used_storage, 1000000)

    def test_first_attempt_unknown_collections_retain_without_enumerating(self):
        class NeverWalk:
            def __iter__(self): raise AssertionError("unknown collection iterated")
            def __len__(self): raise AssertionError("unknown collection measured")
        for field in ("files", "buffers"):
            root, paid, view = self.prepared()
            result = selected(paid, view)
            unknown = NeverWalk()
            setattr(result, field, unknown)
            self.refuse(paid, view, result)
            self.assertIs(getattr(paid.outcome.correlation.supplied, field), unknown)
            self.assertTrue(paid.outcome.correlation.unresolved)
            token = paid.destroy()
            self.assertFalse(token.complete)
            with self.assertRaises(m.Refused): token.release()
            self.assertEqual(root.used_storage, 1000000)

    def test_exact_47_cleanup_boundary_and_post_retirement_no_resurrection(self):
        for cleanup in (46, 47):
            root, paid = reservation(cleanup=cleanup)
            _, _, view = admitted_owner(paid)
            result = selected(paid, view)
            self.assertTrue(all(a is not b for a, b in zip(view.files[:4], result.files)))
            m.correlate_before_leaf(paid, view, result)
            self.assertEqual(len(paid.retirement_plan()), 47)
            token = paid.destroy()
            self.assertEqual(token.complete, cleanup == 47)
            before = (paid.generation, paid.outcome.carrier_live, len(paid.diagnostics), paid.outcome.correlation.tickets_left)
            with self.assertRaises(m.Refused): m.correlate_before_leaf(paid, view, result)
            self.assertEqual((paid.generation, paid.outcome.carrier_live, len(paid.diagnostics), paid.outcome.correlation.tickets_left), before)
            if cleanup == 47:
                self.assertIsNone(paid.outcome.correlation.replay_refusal)
                self.assertIsNone(paid.outcome.correlation.supplied)
                token.release()
                self.assertEqual(root.used_storage, 0)
            else:
                with self.assertRaises(m.Refused): token.release()
                self.assertEqual(root.used_storage, 1000000)


class StrictSessionControls(unittest.TestCase):
    def reject_record(self, change, reason):
        root, paid = reservation()
        bodies, paths = complete_owner(paid, record_change=change)
        with self.assertRaisesRegex(m.Refused, reason) as caught:
            m.admit_model_only(paid, bodies, paths, **TRUST)
        self.assertIs(caught.exception.outcome, paid.outcome)
        self.assertIs(paid.diagnostics[-1], caught.exception)
        self.assertIsNone(paid.outcome.admission)
        self.assertFalse(paid.outcome.correlation.funded)
        self.assertNotIn("admit-model-only", paid.effects)
        self.assertNotIn("leaf-model-only", paid.effects)
        self.assertEqual(root.used_storage, 1000000)

    def test_all_three_float_witnesses_refuse_before_admission_or_expected(self):
        self.reject_record(lambda r: r.update(extent=float(r["extent"])), "session positive u64 extent")
        for field in ("inode", "mtime_ns"):
            self.reject_record(lambda r, f=field: r["source_identity"].update({f: float(r["source_identity"][f])}),
                               "session identity integer domains")

    def test_extent_adjacent_primitive_types_and_domains(self):
        for bad in (True, False, 0, -1, m.U64_MAX + 1, "6", None, [], {}):
            self.reject_record(lambda r, v=bad: r.update(extent=v), "session positive u64 extent")

    def test_every_nested_identity_field_rejects_float_bool_and_non_integer(self):
        for field in m.TestFileIdentity.__dataclass_fields__:
            for bad in (1.0, True, False, "0", None, [], {}):
                with self.subTest(field=field, bad=bad):
                    self.reject_record(lambda r, f=field, v=bad: r["source_identity"].update({f: v}),
                                       "session identity integer domains")

    def test_exact_nested_and_top_level_keys_and_object_types(self):
        for field in m.TestFileIdentity.__dataclass_fields__:
            self.reject_record(lambda r, f=field: r["source_identity"].pop(f), "session complete eight-field identity")
        self.reject_record(lambda r: r["source_identity"].update(extra=0), "session complete eight-field identity")
        for value in ([], None, 1, "identity"):
            self.reject_record(lambda r, v=value: r.update(source_identity=v), "session complete eight-field identity")
        for key in ("source", "manifest", "build", "executable", "nonce", "validation", "extent", "source_identity"):
            self.reject_record(lambda r, k=key: r.pop(k), "complete model session")
        self.reject_record(lambda r: r.update(extra=0), "complete model session")

    def test_unsigned_signed_domains_and_regular_shape(self):
        for field in ("device", "inode", "length", "mode"):
            for bad in (-1, m.U64_MAX + 1):
                self.reject_record(lambda r, f=field, v=bad: r["source_identity"].update({f: v}), "session identity integer domains")
        for field in ("mtime", "mtime_ns", "ctime", "ctime_ns"):
            for bad in (-(1 << 63) - 1, 1 << 63):
                self.reject_record(lambda r, f=field, v=bad: r["source_identity"].update({f: v}), "session identity integer domains")
        for bad in (0, 0o040700, 0o120600):
            self.reject_record(lambda r, v=bad: r["source_identity"].update(mode=v), "session regular-file identity")

    def test_digest_nonce_and_all_five_validation_fields_remain_strict(self):
        for field in ("source", "manifest", "build", "executable", "nonce"):
            for bad in (None, 0, True, "a" * 63, "a" * 65, "g" * 64, " " * 64):
                self.reject_record(lambda r, f=field, v=bad: r.update({f: v}), "session full digest/nonce")
        for index in range(5):
            for bad in (0, -1, True, 1.0, m.U64_MAX + 1, "1", None):
                self.reject_record(lambda r, i=index, v=bad: r["validation"].__setitem__(i, v), "session all five validator limits")
        for bad in (None, {}, 5, [], [1] * 4, [1] * 6):
            self.reject_record(lambda r, v=bad: r.update(validation=v), "session all five validator limits")

    def test_typed_valid_but_different_identity_and_extent_still_refuse(self):
        self.reject_record(lambda r: r.update(extent=r["extent"] + 1), "actual source identity/extent correspondence")
        for field in m.TestFileIdentity.__dataclass_fields__:
            self.reject_record(lambda r, f=field: r["source_identity"].update({f: r["source_identity"][f] + 1}),
                               "actual source identity/extent correspondence")

    def test_valid_negative_signed_timestamp_full_identity_remains_positive(self):
        identity = m.TestFileIdentity(0, m.U64_MAX, 6, 0o100640, -(1 << 63), -1, -17, (1 << 63) - 1)
        root, paid = reservation(cleanup=47)
        bodies, paths = complete_owner(paid, source_identity=identity)
        view = m.admit_model_only(paid, bodies, paths, **TRUST)
        self.assertEqual(asdict(view.correspondence.actual4[0]), asdict(identity))
        result = selected(paid, view)
        m.correlate_before_leaf(paid, view, result)
        self.assertEqual(paid.effects.count("leaf-model-only"), 1)
        paid.destroy().release()
        self.assertEqual(root.used_storage, 0)

    def test_duplicate_nested_key_refuses_synthetic_json_parser(self):
        _, paid = reservation()
        bodies, _ = complete_owner(paid)
        raw = bodies[2].data.replace(b'"inode":1,', b'"inode":1,"inode":1,')
        self.assertNotEqual(raw, bodies[2].data)
        with self.assertRaises(m.Refused): m._session_decode(raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
