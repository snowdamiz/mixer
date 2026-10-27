"""Fresh controls written from the C1/C2 contract and model API, no old fixtures/tests.

All files/allocations are synthetic Python model values. Mutable malformed public
fields are input-shape controls, not hostile Python monkeypatching. No OS File is
opened, adopted, read, or closed; no product/native leaf is executed.
"""
import copy
from dataclasses import asdict, replace
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import unittest
from custody import CANDIDATE, ROOT, custody, row

spec = importlib.util.spec_from_file_location("independent_frozen_affine_model", CANDIDATE / "model.py")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

LIMITS = (97, 1111, 2222, 3333, 4444)
ROLE_NAMES = ("source", "build", "session", "executable", "compiler", "compiler_version",
              "compile_manifest", "compile_argv", "compile_environment", "process_argv",
              "process_environment", "review")
READ_SCHEDULES = 0


def digest(raw):
    return hashlib.sha256(raw).digest()


def policy():
    return m.TestPolicy(10000000, 10000000, (8192,) * 12, (96,) * 5, 1024)


def reservation(*, work=1000000, storage=1000000, cleanup=100):
    root = m.TestRoot(policy(), startup_already_provisioned=True)
    return root.reserve(work, storage, cleanup_work=cleanup)


def packet(paths):
    header = bytearray(64)
    header[:8] = b"MIXPTH01"
    struct.pack_into("<QQ", header, 8, 1, 64 + sum(map(len, paths)))
    for index, path in enumerate(paths):
        struct.pack_into("<Q", header, 24 + 8 * index, len(path))
    return bytes(header) + b"".join(paths)


class Scene:
    def __init__(self, *, cleanup=100, change_session=None, source_times=None, admit=True):
        self.paid = reservation(cleanup=cleanup)
        self.paths = (b"/model/source", b"/model/build", b"/model/session", b"/model/executable", b"/model/output")
        self.raw = [b"s" * 97, b"independent-build-record", b"", b"independent-executable"]
        self.raw += [("independent-" + role).encode() for role in ROLE_NAMES[4:]]
        times = source_times or (3, 101, 5, 202)
        source_id = m.TestFileIdentity(71, 6100, len(self.raw[0]), 0o100640, *times)
        self.record = {"source": digest(self.raw[0]).hex(), "manifest": digest(self.raw[6]).hex(),
            "build": digest(self.raw[1]).hex(), "executable": digest(self.raw[3]).hex(),
            "nonce": bytes(range(32)).hex(), "validation": list(LIMITS), "extent": len(self.raw[0]),
            "source_identity": asdict(source_id)}
        if change_session is not None:
            change_session(self.record)
        self.raw[2] = json.dumps(self.record, sort_keys=True, separators=(",", ":")).encode()
        self.raw.append(packet(self.paths))
        self.ids = [source_id] + [m.TestFileIdentity(71, 6100 + i, len(raw), 0o100640, 3, 101, 5, 202)
            for i, raw in enumerate(self.raw[1:], 1)]
        self.handles = [m.TestHandle(raw, identity) for raw, identity in zip(self.raw, self.ids)]
        m.adopt_slots(self.paid, self.handles, single_threaded=True, no_prior_owners=True, no_close_handlers=True)
        self.bodies = tuple(m.acquire_body(self.paid, h, role, 8192)[0]
            for h, role in zip(self.handles[:12], ROLE_NAMES))
        self.packet_body = m.acquire_body(self.paid, self.handles[12], "path_packet", 1024)[0]
        self.path_bodies = m.acquire_native_paths(self.paid, self.paths)
        self.view = self.admit() if admit else None

    def admit(self):
        return m.admit_model_only(self.paid, self.bodies, self.path_bodies,
            trusted_local_launch_contract=True, all_actual_correspondence=True, review_provenance=True)

    def expected(self):
        return {"source": digest(self.raw[0]), "manifest": digest(self.raw[6]), "build": digest(self.raw[1]),
            "session": digest(self.raw[2]), "executable": digest(self.raw[3]), "nonce": bytes(range(32)),
            "validation": LIMITS, "extent": len(self.raw[0]), "actual4": tuple(self.ids[:4])}

    def selected(self, *, file_count=4, buffer_count=4):
        files = [m.TestHandle(self.raw[i], replace(self.ids[i])) for i in range(file_count)]
        bodies = []
        for i in range(buffer_count):
            body = self.paid.allocate("selected-" + str(i), len(self.raw[i]))
            body.set_once(self.raw[i])
            bodies.append(body)
        return m.TestSelectedResult(self.expected(), files, bodies)


class ContractCase(unittest.TestCase):
    def refused(self, function, *args, **kwargs):
        with self.assertRaises(m.Refused) as caught:
            function(*args, **kwargs)
        return caught.exception

    def no_leaf(self, paid):
        self.assertNotIn("leaf-model-only", paid.effects)

    def complete(self, paid, *, steps=None):
        before = paid.cleanup_left
        token = paid.destroy()
        self.assertTrue(token.complete)
        if steps is not None:
            self.assertEqual(before - paid.cleanup_left, steps)
        self.assertTrue(all(not owner.live for owner in paid.owned))
        self.assertFalse(paid.outcome.carrier_live)
        self.assertEqual(paid.diagnostics, [])
        self.assertIsNone(paid.outcome.correlation.supplied)
        self.assertIsNone(paid.outcome.correlation.original_refusal)
        token.release()
        self.assertEqual(paid.root.used_storage, 0)
        self.assertTrue(paid.released)
        self.refused(token.release)
        self.refused(paid.destroy)
        return token

    def unresolved(self, paid):
        charge = paid.root.used_storage
        token = paid.destroy()
        self.assertFalse(token.complete)
        self.refused(token.release)
        self.assertEqual(paid.root.used_storage, charge)
        self.assertTrue(paid.outcome.carrier_live)
        self.assertIsNone(paid.outcome.complete_token)
        self.refused(paid.destroy)

    def consume_refusal(self, scene, selected, *, view=None, expected=()):
        paid = scene.paid
        error = self.refused(m.correlate_before_leaf, paid, scene.view if view is None else view, selected, *expected)
        custody = paid.outcome.correlation
        self.assertTrue(custody.attempted)
        self.assertEqual(paid.state, "consumed")
        self.assertIs(custody.supplied, selected)
        self.assertIs(custody.original_refusal, error)
        self.assertIs(error.outcome, paid.outcome)
        self.assertTrue(any(x is error for x in paid.diagnostics))
        self.no_leaf(paid)
        repeated = self.refused(m.correlate_before_leaf, paid, scene.view, selected)
        self.assertIs(repeated, error)
        self.assertEqual(sum(x is error for x in paid.diagnostics), 1)
        self.no_leaf(paid)
        return error


class AffineBoundaryControls(ContractCase):
    def test_ordinary_distinct_handle_positive_and_exact_47_retirement(self):
        scene = Scene(cleanup=47)
        chosen = scene.selected()
        self.assertEqual(scene.view.correspondence.mapping(), scene.expected())
        self.assertTrue(all(a is not b and a.identity == b.identity for a, b in zip(chosen.files, scene.handles)))
        before = (scene.paid.work_left, scene.paid.storage_left, scene.paid.cleanup_left)
        self.assertIn("model leaf reached", m.correlate_before_leaf(scene.paid, scene.view, chosen))
        self.assertEqual(before[0] - scene.paid.work_left, 2)
        self.assertEqual(before[1:], (scene.paid.storage_left, scene.paid.cleanup_left))
        self.assertEqual(len(scene.paid.retirement_plan()), 47)
        self.complete(scene.paid, steps=47)
        self.assertFalse(chosen.live)
        self.assertTrue(all(not f.live for f in chosen.files))

    def test_original_four_files_three_buffers_retire_all_represented_owners(self):
        scene = Scene()
        chosen = scene.selected(buffer_count=3)
        files = chosen.files
        self.consume_refusal(scene, chosen)
        self.assertEqual(len(scene.paid.outcome.correlation.files), 4)
        self.assertTrue(all(f.owner is scene.paid and f.adopted for f in files))
        self.assertFalse(scene.paid.outcome.correlation.unresolved)
        self.complete(scene.paid, steps=46)
        self.assertFalse(chosen.live)
        self.assertTrue(all(not f.live for f in files))

    def test_four_files_three_buffers_then_new_valid_result_cannot_leaf_or_release(self):
        scene = Scene()
        first = scene.selected(buffer_count=3)
        original = self.consume_refusal(scene, first)
        later = scene.selected()
        self.assertIs(self.refused(m.correlate_before_leaf, scene.paid, scene.view, later), original)
        self.assertTrue(scene.paid.outcome.correlation.unresolved)
        self.assertIs(scene.paid.outcome.correlation.late_supplied, first)
        self.assertTrue(all(f.owner is None and not f.adopted for f in later.files))
        self.no_leaf(scene.paid)
        self.unresolved(scene.paid)
        self.assertTrue(all(f.live for f in later.files))
        self.assertTrue(all(not f.live for f in first.files))

    def test_forbidden_expected_dictionary_is_owning_consuming_and_same_error(self):
        scene = Scene()
        chosen = scene.selected()
        self.consume_refusal(scene, chosen, expected=(scene.expected(),))
        self.assertFalse(scene.paid.outcome.correlation.unresolved)
        self.complete(scene.paid, steps=47)
        self.assertFalse(chosen.live)

    def test_copied_foreign_stale_and_invalid_views_consume_without_stealing(self):
        foreign = Scene()
        for kind in ("copied", "foreign", "stale", "wrong"):
            with self.subTest(kind=kind):
                scene = Scene()
                chosen = scene.selected()
                view = copy.copy(scene.view) if kind == "copied" else foreign.view if kind == "foreign" else object()
                if kind == "stale":
                    view = scene.view
                    scene.paid.replace_generation_model_only()
                self.consume_refusal(scene, chosen, view=view)
                self.assertTrue(all(h.owner is foreign.paid and h.live for h in foreign.handles))
                self.complete(scene.paid, steps=47)
        self.complete(foreign.paid, steps=39)

    def test_unknown_selected_carrier_is_retained_and_never_complete(self):
        for selected in (None, object(), {"files": [], "buffers": []}, [], 7):
            with self.subTest(kind=type(selected).__name__):
                scene = Scene()
                self.consume_refusal(scene, selected)
                self.assertTrue(scene.paid.outcome.correlation.unresolved)
                self.unresolved(scene.paid)

    def test_adjacent_bounded_counts_and_duplicate_owners_retire_safely(self):
        for kind in ("no-files", "three-files", "three-buffers", "duplicate-file", "duplicate-body", "shared-original-body", "uninitialized-body"):
            with self.subTest(kind=kind):
                scene = Scene()
                selected = scene.selected(file_count=0 if kind == "no-files" else 3 if kind in ("three-files", "duplicate-file") else 4,
                    buffer_count=3 if kind == "three-buffers" else 4)
                if kind == "duplicate-file":
                    # Build a duplicated value from three independently supplied Files.
                    selected = m.TestSelectedResult(scene.expected(), selected.files[:3] + selected.files[:1], selected.buffers)
                if kind == "duplicate-body":
                    selected.buffers = selected.buffers[:3] + selected.buffers[:1]
                if kind == "shared-original-body":
                    selected.buffers = (scene.bodies[0],) + selected.buffers[1:]
                if kind == "uninitialized-body":
                    body = scene.paid.allocate("uninitialized", len(scene.raw[0]))
                    selected.buffers = (body,) + selected.buffers[1:]
                self.consume_refusal(scene, selected)
                self.assertFalse(scene.paid.outcome.correlation.unresolved)
                represented = tuple(scene.paid.owned)
                self.complete(scene.paid)
                self.assertTrue(all(not x.live for x in represented))
                self.assertFalse(selected.live)

    def test_oversized_or_unknown_collections_retain_charge_without_enumeration(self):
        class Unknown:
            calls = 0
            def __iter__(self):
                self.calls += 1
                raise AssertionError("unknown collection enumerated")
            def __len__(self):
                self.calls += 1
                raise AssertionError("unknown collection sized")
            def __getitem__(self, key):
                self.calls += 1
                raise AssertionError("unknown collection indexed")
        for target in ("files", "buffers"):
            for shape in ("oversized", "unknown"):
                with self.subTest(target=target, shape=shape):
                    scene = Scene()
                    selected = scene.selected()
                    unknown = Unknown()
                    if shape == "unknown":
                        setattr(selected, target, unknown)
                    elif target == "files":
                        selected.files += (m.TestHandle(b"extra", m.TestFileIdentity(71, 9999, 5)),)
                    else:
                        extra = scene.paid.allocate("extra", 5)
                        extra.set_once(b"extra")
                        selected.buffers += (extra,)
                    self.consume_refusal(scene, selected)
                    self.assertTrue(scene.paid.outcome.correlation.unresolved)
                    self.assertEqual(unknown.calls, 0)
                    self.unresolved(scene.paid)
                    self.assertEqual(unknown.calls, 0)
                    if shape == "oversized" and target == "files":
                        self.assertTrue(selected.files[4].live)
                        self.assertIsNone(selected.files[4].owner)

    def test_unsafe_invalid_dead_raw_foreign_files_are_never_adopted_or_closed(self):
        for kind in ("invalid", "dead", "foreign", "raw", "already-adopted", "malformed-identity", "wrong-type"):
            with self.subTest(kind=kind):
                scene = Scene()
                selected = scene.selected(file_count=3)
                other = None
                bad = m.TestHandle(scene.raw[3], replace(scene.ids[3]))
                if kind == "invalid": bad.slot_valid = False
                if kind == "dead": bad.live = False
                if kind == "malformed-identity": bad.identity = replace(bad.identity, inode=1.0)
                if kind == "wrong-type": bad = 9001
                if kind in ("foreign", "raw", "already-adopted"):
                    if kind == "raw":
                        # A raw controlled handle from a real refused adoption boundary.
                        raw_paid = reservation()
                        raw_files = [m.TestHandle(b"x", m.TestFileIdentity(81, 7100 + i, 1)) for i in range(13)]
                        raw_files[0].slot_valid = False
                        self.refused(m.adopt_slots, raw_paid, raw_files, single_threaded=True,
                            no_prior_owners=True, no_close_handlers=True)
                        bad = raw_files[3]
                    elif kind == "foreign":
                        other = Scene(admit=False)
                        bad = other.handles[3]
                    else:
                        bad = scene.handles[3]
                selected.files += (bad,)
                before = (getattr(bad, "owner", None), getattr(bad, "adopted", None), getattr(bad, "live", None))
                self.consume_refusal(scene, selected)
                self.assertTrue(scene.paid.outcome.correlation.unresolved)
                self.assertEqual((getattr(bad, "owner", None), getattr(bad, "adopted", None), getattr(bad, "live", None)), before)
                self.assertTrue(all(f is not bad for f in scene.paid.outcome.correlation.files))
                self.unresolved(scene.paid)
                if kind != "already-adopted":
                    self.assertEqual(getattr(bad, "live", None), before[2])
                if other is not None: self.complete(other.paid)
                if kind == "raw":
                    self.unresolved(raw_paid)
                    self.assertTrue(all(h.live and not h.adopted for h in raw_files))

    def test_foreign_unregistered_and_dead_bodies_are_not_laundered(self):
        for kind in ("foreign", "unregistered", "dead", "wrong-type"):
            with self.subTest(kind=kind):
                scene = Scene()
                selected = scene.selected(buffer_count=3)
                other = reservation()
                if kind == "foreign": bad = other.allocate("foreign", 4)
                elif kind == "unregistered": bad = m.TestBody("unregistered", 4, 4, scene.paid)
                elif kind == "dead":
                    bad = scene.paid.allocate("dead", 4)
                    bad.live = False
                else: bad = b"raw"
                selected.buffers += (bad,)
                self.consume_refusal(scene, selected)
                self.assertTrue(scene.paid.outcome.correlation.unresolved)
                self.assertTrue(all(x is not bad for x in scene.paid.outcome.correlation.buffers))
                self.unresolved(scene.paid)
                if kind == "foreign":
                    self.assertTrue(bad.live)
                    self.assertIs(bad.owner, other)

    def test_finite_capture_and_replay_never_mint_budget_or_walk_later_carriers(self):
        scene = Scene()
        selected = scene.selected(buffer_count=3)
        original = self.consume_refusal(scene, selected)
        custody_state = scene.paid.outcome.correlation
        self.assertEqual(custody_state.tickets_left, 0)
        before = (scene.paid.work_left, scene.paid.storage_left, scene.paid.cleanup_left,
            len(scene.paid.owned), len(scene.paid.effects), len(scene.paid.root.trace))
        for _ in range(128):
            scene.paid.replace_generation_model_only()
            self.assertIs(self.refused(m.correlate_before_leaf, scene.paid, scene.view, selected), original)
        self.assertEqual(before, (scene.paid.work_left, scene.paid.storage_left, scene.paid.cleanup_left,
            len(scene.paid.owned), len(scene.paid.effects), len(scene.paid.root.trace)))
        # A later opaque carrier cannot trigger another bounded or unbounded capture.
        later = object()
        self.assertIs(self.refused(m.correlate_before_leaf, scene.paid, scene.view, later), original)
        self.assertEqual(custody_state.tickets_left, 0)
        self.assertTrue(custody_state.unresolved)
        self.unresolved(scene.paid)

    def test_success_replay_has_one_prepaid_error_then_retirement_cannot_resurrect(self):
        scene = Scene()
        selected = scene.selected()
        m.correlate_before_leaf(scene.paid, scene.view, selected)
        error = self.refused(m.correlate_before_leaf, scene.paid, scene.view, selected)
        self.assertIs(error, scene.paid.outcome.correlation.replay_refusal)
        before = (scene.paid.work_left, scene.paid.storage_left, len(scene.paid.root.trace))
        for _ in range(32):
            self.assertIs(self.refused(m.correlate_before_leaf, scene.paid, scene.view, selected), error)
        self.assertEqual(before, (scene.paid.work_left, scene.paid.storage_left, len(scene.paid.root.trace)))
        self.complete(scene.paid, steps=47)
        self.refused(m.correlate_before_leaf, scene.paid, scene.view, selected)
        self.assertFalse(scene.paid.outcome.carrier_live)
        self.assertEqual(scene.paid.root.used_storage, 0)
        self.assertEqual(scene.paid.diagnostics, [])
        self.assertIsNone(scene.paid.outcome.correlation.supplied)

    def test_ingress_prepayment_cannot_publish_admission_when_either_partition_short(self):
        for dimension in ("work", "storage"):
            with self.subTest(dimension=dimension):
                scene = Scene(admit=False)
                paid = scene.paid
                cleanup = paid.cleanup_left
                if dimension == "storage":
                    paid.operation("independent-spend-storage", 1, paid.storage_left - 11)
                else:
                    overhead = 64 + sum(map(len, scene.paths)) + len(scene.raw[2])
                    paid.operation("independent-spend-work", paid.work_left - overhead - 11)
                error = self.refused(scene.admit)
                self.assertIn("prepay", str(error))
                self.assertIsNone(paid.outcome.admission)
                self.assertFalse(paid.outcome.correlation.funded)
                self.assertFalse(paid.outcome.correlation.attempted)
                self.assertEqual(paid.cleanup_left, cleanup)
                self.no_leaf(paid)
                self.complete(paid, steps=39)

    def test_exhaustion_after_admission_still_owns_consumes_and_preserves_error(self):
        scene = Scene()
        selected = scene.selected()
        scene.paid.operation("independent-spend-rest", scene.paid.work_left)
        self.consume_refusal(scene, selected)
        self.assertEqual(scene.paid.work_left, 0)
        self.complete(scene.paid, steps=47)


class NestedSessionControls(ContractCase):
    def rejects_record(self, change):
        scene = Scene(change_session=change, admit=False)
        error = self.refused(scene.admit)
        self.assertIs(error.outcome, scene.paid.outcome)
        self.assertIsNone(scene.paid.outcome.admission)
        self.assertFalse(scene.paid.outcome.correlation.funded)
        self.no_leaf(scene.paid)
        self.complete(scene.paid, steps=39)

    def test_three_equal_float_witnesses_rejected_before_admission(self):
        self.rejects_record(lambda r: r.__setitem__("extent", float(r["extent"])))
        for field in ("inode", "mtime_ns"):
            self.rejects_record(lambda r, field=field: r["source_identity"].__setitem__(field, float(r["source_identity"][field])))

    def test_all_eight_identity_fields_reject_bool_float_string_null_list_and_object(self):
        for field in ("device", "inode", "length", "mode", "mtime", "mtime_ns", "ctime", "ctime_ns"):
            for value in (True, False, 1.0, "1", None, [], {}):
                with self.subTest(field=field, value=value):
                    self.rejects_record(lambda r, field=field, value=value: r["source_identity"].__setitem__(field, value))

    def test_exact_nested_keys_unsigned_signed_domains_and_regular_mode(self):
        for field in ("device", "inode", "length", "mode", "mtime", "mtime_ns", "ctime", "ctime_ns"):
            self.rejects_record(lambda r, field=field: r["source_identity"].pop(field))
        self.rejects_record(lambda r: r["source_identity"].__setitem__("extra", 9))
        for value in (None, [], 1, "identity"):
            self.rejects_record(lambda r, value=value: r.__setitem__("source_identity", value))
        for field in ("device", "inode", "length", "mode"):
            for value in (-1, 1 << 64):
                self.rejects_record(lambda r, field=field, value=value: r["source_identity"].__setitem__(field, value))
        for field in ("mtime", "mtime_ns", "ctime", "ctime_ns"):
            for value in (-(1 << 63) - 1, 1 << 63):
                self.rejects_record(lambda r, field=field, value=value: r["source_identity"].__setitem__(field, value))
        for mode in (0, 0o040755, 0o120777, 0o020600):
            self.rejects_record(lambda r, mode=mode: r["source_identity"].__setitem__("mode", mode))

    def test_extent_limits_digests_nonce_and_top_keys_keep_strict_shape(self):
        for value in (0, -1, 1 << 64, True, False, 97.0, "97", None, [], {}):
            self.rejects_record(lambda r, value=value: r.__setitem__("extent", value))
        for index in range(5):
            for value in (0, -1, 1 << 64, True, 1.0, "1", None):
                self.rejects_record(lambda r, index=index, value=value: r["validation"].__setitem__(index, value))
        for value in ([], [1] * 4, [1] * 6, None, 7, "12345"):
            self.rejects_record(lambda r, value=value: r.__setitem__("validation", value))
        for field in ("source", "manifest", "build", "executable", "nonce"):
            for value in ("0" * 63, "g" * 64, True, 1, None, [], {}):
                self.rejects_record(lambda r, field=field, value=value: r.__setitem__(field, value))
        for field in ("source", "manifest", "build", "executable", "nonce", "validation", "extent", "source_identity"):
            self.rejects_record(lambda r, field=field: r.pop(field))
        self.rejects_record(lambda r: r.__setitem__("extra", 1))

    def test_typed_but_different_full_identity_or_extent_cannot_be_normalized(self):
        self.rejects_record(lambda r: r.__setitem__("extent", r["extent"] + 1))
        for field in ("device", "inode", "length", "mode", "mtime", "mtime_ns", "ctime", "ctime_ns"):
            self.rejects_record(lambda r, field=field: r["source_identity"].__setitem__(field, r["source_identity"][field] + 1))

    def test_negative_signed_timestamp_boundaries_remain_valid_through_leaf_and_retirement(self):
        for times in ((-1, -2, -3, -4), (-(1 << 63), (1 << 63) - 1, -1, -(1 << 63))):
            with self.subTest(times=times):
                scene = Scene(source_times=times)
                self.assertEqual(scene.view.correspondence.actual4[0], scene.ids[0])
                selected = scene.selected()
                self.assertIn("model leaf reached", m.correlate_before_leaf(scene.paid, scene.view, selected))
                self.complete(scene.paid, steps=47)


class RetainedContractControls(ContractCase):
    def test_all_13_adoption_failures_keep_raw_suffix_no_raw_close_and_charge(self):
        for index in range(13):
            with self.subTest(index=index):
                paid = reservation()
                files = [m.TestHandle(b"x", m.TestFileIdentity(91, 8100 + i, 1)) for i in range(13)]
                files[index].slot_valid = False
                error = self.refused(m.adopt_slots, paid, files, single_threaded=True,
                    no_prior_owners=True, no_close_handlers=True)
                self.assertIs(error.outcome, paid.outcome)
                self.assertEqual([s.adoption_bit for s in paid.outcome.slots], [i < index for i in range(13)])
                self.unresolved(paid)
                self.assertTrue(all(not h.live for h in files[:index]))
                self.assertTrue(all(h.live for h in files[index:]))
                self.assertTrue(all(not s.close_attempted for s in paid.outcome.slots[index:]))

    def test_all_39_acquisition_work_cutoffs_preserve_cleanup_and_partial_owners(self):
        for cutoff in range(39):
            paid = reservation(work=39)
            paid.operation("independent-budget-use", 39 - cutoff)
            files = [m.TestHandle(b"x", m.TestFileIdentity(92, 8200 + i, 1)) for i in range(13)]
            self.refused(m.adopt_slots, paid, files, single_threaded=True,
                no_prior_owners=True, no_close_handlers=True)
            self.assertEqual(paid.cleanup_left, 100)
            self.assertEqual(sum(s.adoption_bit for s in paid.outcome.slots), cutoff // 3)
            self.unresolved(paid)
            self.assertTrue(all(not s.close_attempted for s in paid.outcome.slots if not s.adoption_bit))

    def test_all_47_retirement_failures_and_unwinds_conservatively_retain_no_second_attempt(self):
        for action in ("failure", "unwind"):
            for index in range(47):
                with self.subTest(action=action, index=index):
                    scene = Scene(cleanup=47)
                    selected = scene.selected()
                    m.correlate_before_leaf(scene.paid, scene.view, selected)
                    charge = scene.paid.root.used_storage
                    original = OSError("independent-retirement-error")
                    if action == "failure":
                        token = scene.paid.destroy(fail_at=index, original=original)
                        self.assertFalse(token.complete)
                        self.assertTrue(any(x is original for x in scene.paid.diagnostics))
                        self.refused(token.release)
                    else:
                        with self.assertRaises(RuntimeError): scene.paid.destroy(unwind_at=index)
                    self.assertEqual(scene.paid.root.used_storage, charge)
                    self.assertIsNone(scene.paid.outcome.complete_token)
                    effects = len(scene.paid.root.trace)
                    self.refused(scene.paid.destroy)
                    self.assertEqual(effects, len(scene.paid.root.trace))

    def test_cleanup_46_refuses_47_succeeds_without_operation_refund(self):
        for count in (46, 47):
            scene = Scene(cleanup=count)
            selected = scene.selected()
            m.correlate_before_leaf(scene.paid, scene.view, selected)
            work = scene.paid.root.used_work
            if count == 46:
                self.unresolved(scene.paid)
            else:
                self.complete(scene.paid, steps=47)
            self.assertEqual(scene.paid.root.used_work, work)

    def test_closed_nine_groups_and_all_32_full_identity_field_substitutions(self):
        changes = [(name, lambda p, name=name: p.__setitem__(name, bytes([p[name][0] ^ 1]) + p[name][1:]))
            for name in ("source", "manifest", "build", "session", "executable", "nonce")]
        changes += [("validation", lambda p: p.__setitem__("validation", (98,) + p["validation"][1:])),
            ("extent", lambda p: p.__setitem__("extent", p["extent"] + 1)),
            ("actual4", lambda p: p.__setitem__("actual4", tuple(reversed(p["actual4"]))))]
        self.assertEqual(len(changes), 9)
        for name, change in changes:
            with self.subTest(group=name):
                scene = Scene()
                selected = scene.selected()
                change(selected.provenance)
                self.consume_refusal(scene, selected)
                self.complete(scene.paid, steps=47)
        for index in range(4):
            for field in ("device", "inode", "length", "mode", "mtime", "mtime_ns", "ctime", "ctime_ns"):
                scene = Scene()
                selected = scene.selected()
                ids = list(selected.provenance["actual4"])
                ids[index] = replace(ids[index], **{field: getattr(ids[index], field) + 1})
                selected.provenance["actual4"] = tuple(ids)
                self.consume_refusal(scene, selected)
                self.complete(scene.paid, steps=47)

    def test_closed_provenance_missing_extra_types_and_all_five_limit_fields(self):
        for field in ("source", "manifest", "build", "session", "executable", "nonce", "validation", "extent", "actual4"):
            scene = Scene()
            selected = scene.selected()
            selected.provenance.pop(field)
            self.consume_refusal(scene, selected)
            self.complete(scene.paid, steps=47)
        for change in (lambda p: p.__setitem__("extra", 1), lambda p: p.__setitem__("extent", 97.0),
                       lambda p: p.__setitem__("actual4", list(p["actual4"]))):
            scene = Scene()
            selected = scene.selected()
            change(selected.provenance)
            self.consume_refusal(scene, selected)
            self.complete(scene.paid, steps=47)
        for index in range(5):
            scene = Scene()
            selected = scene.selected()
            limits = list(selected.provenance["validation"])
            limits[index] += 1
            selected.provenance["validation"] = tuple(limits)
            self.consume_refusal(scene, selected)
            self.complete(scene.paid, steps=47)

    def test_allocation_requested_slack_original_failure_backing_prepaid_and_retained(self):
        paid = reservation(storage=23)
        body = paid.allocate("envelope", 5, m.AllocationContract(5, 7, 11))
        self.assertEqual(body.allocation_bound, 23)
        self.assertEqual(paid.storage_left, 0)
        self.assertEqual(paid.cleanup_left, 100)
        self.refused(paid.allocate, "no-second-backing", 1)
        self.assertTrue(body.live)
        paid = reservation(storage=23)
        original = MemoryError("original independent allocation failure")
        error = self.refused(paid.allocate, "refused", 5, m.AllocationContract(5, 7, 11), failure=original)
        self.assertTrue(any(x is original for x in paid.diagnostics))
        self.assertTrue(any(x is error for x in paid.diagnostics))
        self.assertEqual(paid.storage_left, 0)
        self.assertEqual(paid.owned, [])
        for contract in (m.AllocationContract(4, 7, 11), m.AllocationContract(5, -1, 0), m.AllocationContract(5, 1 << 64, 0)):
            paid = reservation()
            before = paid.work_left, paid.storage_left
            self.refused(paid.allocate, "invalid-contract", 5, contract)
            self.assertEqual(before, (paid.work_left, paid.storage_left))

    def test_startup_is_external_and_dependency_cycles_fail_closed(self):
        self.refused(m.TestRoot, policy(), startup_already_provisioned=False)
        for graph in ({"acquire": ("grant",), "grant": ("acquire",)},
                      {"review": ("review",)}, {"manifest": ("executable",), "executable": ("manifest",)}):
            self.refused(m.check_dependency_dag, graph)
        m.check_dependency_dag({"startup": (), "acquire": ("startup",), "correlate": ("acquire",), "leaf": ("correlate",)})


class ReadBoundsControls(ContractCase):
    def read(self, count, responses, *, raw=None):
        paid = reservation()
        body = b"r" * count if raw is None else raw
        files = [m.TestHandle(body if i == 0 else b"x", m.TestFileIdentity(93, 8300 + i, count if i == 0 else 1),
            responses=responses if i == 0 else None) for i in range(13)]
        m.adopt_slots(paid, files, single_threaded=True, no_prior_owners=True, no_close_handlers=True)
        result = m.acquire_body(paid, files[0], "independent-read", max(8192, count))
        return paid, files[0], result

    def test_exhaustive_small_extents_under_actual_32_attempt_program(self):
        global READ_SCHEDULES
        def schedules(remaining, left, prefix=()):
            if remaining == 0:
                yield prefix
            elif left:
                yield from schedules(remaining, left - 1, prefix + ("Interrupted",))
                for n in range(1, remaining + 1):
                    yield from schedules(remaining - n, left - 1, prefix + (n,))
        count = 0
        for extent in range(1, 5):
            extent_count = 0
            for responses in schedules(extent, 32):
                paid, file, (body, hashed) = self.read(extent, list(responses) + [0])
                self.assertEqual(body.data, b"r" * extent)
                self.assertEqual(hashed, digest(body.data))
                self.assertEqual(file.position, extent)
                reads = sum(name == "read:independent-read" for name in paid.effects)
                self.assertEqual(reads, len(responses))
                self.assertLessEqual(reads, 32)
                self.assertEqual(paid.cleanup_left, 100)
                extent_count += 1
            self.assertEqual(extent_count, math.comb(31 + extent, extent))
            count += extent_count
        self.assertEqual(count, 58904)
        READ_SCHEDULES = count

    def test_finite_eof_boundary_block_boundary_and_interrupted_cap(self):
        for interruptions in range(32):
            paid, file, _ = self.read(1, [1] + ["Interrupted"] * interruptions + [0])
            self.assertEqual(sum(n == "eof:independent-read" for n in paid.effects), interruptions + 1)
            self.assertEqual(file.position, 1)
        for count in (4095, 4096, 4097, 8192):
            paid, file, _ = self.read(count, [])
            self.assertEqual(sum(n == "read:independent-read" for n in paid.effects), math.ceil(count / 4096))
            self.assertEqual(file.position, count)
        for responses, reason in ((["Interrupted"] * 32, "attempt cap"),
            ([1] + ["Interrupted"] * 32, "EOF attempt cap"), ([0], "short input"),
            ([2], "overreported read"), ([True], "overreported read"), ([1, 1], "extra input")):
            with self.assertRaises(m.Refused) as caught:
                self.read(1, responses)
            self.assertEqual(str(caught.exception), reason)
            paid = caught.exception.outcome.reservation
            self.assertLessEqual(sum(n.startswith("read:") for n in paid.effects), 32)
            self.assertLessEqual(sum(n.startswith("eof:") for n in paid.effects), 32)
            self.assertTrue(all(h.live for h in paid.owned if type(h) is m.TestHandle))
            self.complete(paid)


class FrozenEvidenceControls(unittest.TestCase):
    def test_complete_inputs_original_failures_and_current_candidate_seals_remain_immutable(self):
        rows = custody()
        self.assertEqual(len(rows), 548)
        self.assertEqual(row(CANDIDATE / "model.py")["sha256"], "e18bdf16f9de346d3ab553a525d49b735c240ce86c0bdf9717b7a175767fed7f")

    def test_three_retained_command_receipts_are_regression_evidence_not_fresh_review(self):
        expected = {"focused-attempt1": 26, "all-attempt1": 109, "all-final": 110}
        for label, methods in expected.items():
            base = CANDIDATE / "commands" / label
            plan = json.loads((base / "plan.json").read_bytes())
            receipt = json.loads((base / "receipt.json").read_bytes())
            self.assertEqual(receipt["exit"], 0)
            self.assertFalse(receipt["timed_out"])
            self.assertTrue(receipt["child_reaped"] and receipt["owned_group_absent"])
            self.assertTrue(receipt["inputs_unchanged"] and receipt["source_unchanged"])
            self.assertEqual(plan["source"], receipt["source_before"])
            self.assertEqual(receipt["source_before"], receipt["source_after"])
            self.assertEqual(len(json.loads((base / "input-before.json").read_bytes())), 479)
            self.assertEqual((base / "input-before.json").read_bytes(), (base / "input-after.json").read_bytes())
            self.assertIn("Ran " + str(methods) + " tests", (base / "stderr").read_text())
            for entry in receipt["outputs"]:
                self.assertEqual(row(ROOT / entry["path"]), entry)
            for entry in plan["source"]:
                snapshot = row(base / Path(entry["path"]).name)
                self.assertEqual((snapshot["bytes"], snapshot["sha256"]), (entry["bytes"], entry["sha256"]))
            self.assertEqual(plan["timeout_seconds"], 55)
            self.assertIn("parent_environment_exact", plan)
            self.assertEqual(plan["environment_exact"]["PYTHONDONTWRITEBYTECODE"], "1")
        final = CANDIDATE / "commands/all-final"
        self.assertIn('"exhaustive_read_schedules": 100842', (final / "stdout").read_text())
        self.assertEqual((final / "model.py").read_bytes(), (CANDIDATE / "model.py").read_bytes())

    def test_pending_limits_remain_pending_and_no_native_authority_is_selected(self):
        contract = json.loads((CANDIDATE / "contract.json").read_bytes())
        report = json.loads((CANDIDATE / "report.json").read_bytes())
        self.assertEqual(report["policy_fields"], 17)
        self.assertEqual(report["unselected_policy_fields"], 15)
        self.assertEqual(report["original_unverified_claims"], 8)
        self.assertEqual(contract["model_correction"]["all_six_upstream_needs"], ["Pending"] * 6)
        self.assertEqual((contract["actual_selected_binding"], contract["actual_selected_parent_account"],
            contract["actual_selected_whole_quote"]), ("ImmutableBindingAndP0ReviewPending", "RootPolicyPending", "WholeQuotePending"))
        self.assertIsNone(contract["inherited_transfer"]["FD_BASE"])
        self.assertEqual(contract["path_caps"], [None] * 5)
        self.assertIsNone(contract["path_packet_cap"])
        self.assertIsNone(next(r["cap"] for r in contract["identity_caps"] if r["role"] == "compiler"))
        self.assertIsNone(next(r["cap"] for r in contract["identity_caps"] if r["role"] == "review"))
        self.assertFalse(contract["root_funding_selected"])
        self.assertFalse(contract["known_caps_are_prices_or_authority"])
        self.assertFalse(contract["model_correction"]["same_handle_route_selected"])
        self.assertFalse(report["fresh_independent_review_claimed"])
        self.assertFalse(report["native_image_allocator_error_and_ownership_contracts_qualified"])
        self.assertFalse(report["FieldLog_operational_OTA_GA"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
