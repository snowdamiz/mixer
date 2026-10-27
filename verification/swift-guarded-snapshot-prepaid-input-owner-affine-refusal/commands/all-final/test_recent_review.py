"""Retained review methods rebound to this candidate; NOT fresh review."""
from dataclasses import asdict, replace
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE
ORIGINAL = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-contract"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


m = load("independent_corrected_model", CANDIDATE / "model.py")
old = load("independent_original_model", ORIGINAL / "model.py")
ROLES = ("source", "build", "session", "executable", "compiler", "compiler_version",
         "compile_manifest", "compile_argv", "compile_environment", "process_argv",
         "process_environment", "review")
TRUST = dict(trusted_local_launch_contract=True, all_actual_correspondence=True,
             review_provenance=True)
ADOPTION = dict(single_threaded=True, no_prior_owners=True, no_close_handlers=True)


def reserve(*, cleanup=100, work=2000000):
    p = m.TestPolicy(work + cleanup, 1000000, (100000,) * 12, (8000,) * 5, 50000)
    r = m.TestRoot(p, startup_already_provisioned=True)
    return r, r.reserve(work, 1000000, cleanup_work=cleanup)


def inherited(data=None):
    data = [b"independent:" + role.encode() for role in ROLES] if data is None else data
    return [m.TestHandle(raw, m.TestFileIdentity(27, 200 + i, len(raw), 0o100640,
            -17, 123456789, 19, 987654321)) for i, raw in enumerate(data)]


def complete(*, cleanup=100, record_change=None, admit=True):
    root, paid = reserve(cleanup=cleanup)
    raw = [b"independent:" + role.encode() for role in ROLES]
    ident = m.TestFileIdentity(27, 200, len(raw[0]), 0o100640, -17, 123456789, 19, 987654321)
    record = {name: hashlib.sha256(raw[index]).hexdigest() for name, index in
              (("source", 0), ("manifest", 6), ("build", 1), ("executable", 3))}
    record.update(nonce=bytes(range(32)).hex(), validation=[1947, 1000000, 65536, 1000000, 10000],
                  extent=len(raw[0]), source_identity=asdict(ident))
    if record_change:
        record_change(record)
    raw[2] = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    paths = tuple(b"/independent/" + bytes([97 + i]) for i in range(5))
    packet = b"MIXPTH01" + struct.pack("<QQ", 1, 64 + sum(map(len, paths)))
    packet += b"".join(struct.pack("<Q", len(p)) for p in paths) + b"".join(paths)
    files = inherited(raw + [packet])
    m.adopt_slots(paid, files, **ADOPTION)
    bodies = tuple(m.acquire_body(paid, files[i], role, 100000)[0] for i, role in enumerate(ROLES))
    m.acquire_body(paid, files[12], "path_packet", 50000)
    owned_paths = m.acquire_native_paths(paid, paths)
    view = m.admit_model_only(paid, bodies, owned_paths, **TRUST) if admit else None
    return root, paid, view, bodies, owned_paths


def selected(paid, view, *, provenance=None, buffer_count=4):
    files = tuple(m.TestHandle(body.data, handle.identity)
                  for body, handle in zip(view.bodies[:4], view.files[:4]))
    buffers = []
    for index, handle in enumerate(files[:buffer_count]):
        body = paid.allocate("independent-loader:" + str(index), len(handle.body))
        body.set_once(handle.body)
        buffers.append(body)
    return m.TestSelectedResult(view.correspondence.mapping() if provenance is None else provenance,
                                files, buffers)


class IndependentPositiveControls(unittest.TestCase):
    def test_partial_adoption_and_original_defect_differential(self):
        p = old.TestPolicy(100000, 100000, (10000,) * 12, (8000,) * 5, 50000)
        before = old.TestRoot(p, startup_already_provisioned=True).reserve(100000, 100000)
        hs = [old.TestHandle(b"a", old.TestFileIdentity(2, i, 1), slot_valid=i != 3) for i in range(13)]
        with self.assertRaises(old.Refused): old.adopt_slots(before, hs, **ADOPTION)
        self.assertTrue(all(h.adopted for h in hs[:3]))
        self.assertEqual(before.owned, [])  # Historical defect remains reproducible.
        before.destroy().release()
        self.assertEqual(before.root.used_storage, 0)
        for bad in range(13):
            root, paid = reserve()
            hs = inherited([b"a"] * 13)
            hs[bad].slot_valid = False
            with self.assertRaises(m.Refused) as failure: m.adopt_slots(paid, hs, **ADOPTION)
            self.assertIs(failure.exception.outcome, paid.outcome)
            self.assertEqual(len(paid.outcome.slots), 13)
            self.assertEqual([s.adoption_bit for s in paid.outcome.slots], [True] * bad + [False] * (13 - bad))
            self.assertEqual(paid.owned, hs[:bad])
            token = paid.destroy()
            self.assertFalse(token.complete)
            with self.assertRaises(m.Refused): token.release()
            self.assertEqual(root.used_storage, 1000000)
            self.assertTrue(all(h.live for h in hs[bad:]))

    def test_original_detached_and_incomplete_provenance_defects_remain_reproducible(self):
        p = old.TestPolicy(100000, 100000, (10000,) * 12, (8000,) * 5, 50000)
        root = old.TestRoot(p, startup_already_provisioned=True)
        first = root.reserve(100000, 100000)
        marker = old.TestAdmittedView((), (), True)
        first.destroy().release()
        other = old.TestRoot(p, startup_already_provisioned=True).reserve(100000, 100000)
        self.assertIn("leaf reached", old.correlate_before_leaf(other, marker, {}, {}))
        self.assertIn("leaf reached", old.correlate_before_leaf(other, marker, {}, {}))
        _, paid, view, _, _ = complete()
        for mapping in ({}, {"source": view.correspondence.source}):
            # Separate owner per consuming provenance attempt.
            _, owner, admitted, _, _ = complete()
            result = selected(owner, admitted, provenance=mapping)
            with self.assertRaises(m.Refused): m.correlate_before_leaf(owner, admitted, result)
            self.assertNotIn("leaf-model-only", owner.effects)
            self.assertIs(result.owner, owner)

    def test_independent_full_retirement_requires_exact_47_tickets(self):
        for tickets in (1, 13, 46, 47):
            root, paid, view, _, _ = complete(cleanup=tickets)
            result = selected(paid, view)
            m.correlate_before_leaf(paid, view, result)
            self.assertEqual(len(paid.retirement_plan()), 47)
            token = paid.destroy()
            self.assertEqual(token.complete, tickets == 47)
            self.assertEqual(paid.cleanup_left, 0)
            self.assertEqual(root.used_storage, 1000000)
            if tickets == 47:
                token.release()
                self.assertEqual(root.used_storage, 0)
                with self.assertRaises(m.Refused): token.release()
                self.assertFalse(any(h.live for h in view.files + result.files))
                self.assertFalse(any(b.live for b in paid.owned))
            else:
                with self.assertRaises(m.Refused): token.release()
                with self.assertRaises(m.Refused): paid.destroy()
            self.assertFalse(paid.outcome.native_healthy_close_claim)

    def test_acquisition_exhaustion_cannot_debit_cleanup(self):
        for work in (1, 2, 3, 17, 38, 39):
            root, paid = reserve(work=work, cleanup=16)
            hs = inherited([b"a"] * 13)
            if work < 39:
                with self.assertRaises(m.Refused): m.adopt_slots(paid, hs, **ADOPTION)
            else: m.adopt_slots(paid, hs, **ADOPTION)
            self.assertEqual(paid.cleanup_left, 16)
            self.assertLessEqual(len(paid.owned), work // 3)
            token = paid.destroy()
            if token.complete: token.release()
            else:
                with self.assertRaises(m.Refused): token.release()
                self.assertEqual(root.used_storage, 1000000)

    def test_every_retirement_failure_and_unwind_preserve_charge_and_no_retry(self):
        for index in range(47):
            for unwind in (False, True):
                root, paid, view, _, _ = complete()
                result = selected(paid, view)
                m.correlate_before_leaf(paid, view, result)
                original = OSError("independent retirement index " + str(index))
                if unwind:
                    with self.assertRaises(RuntimeError): paid.destroy(unwind_at=index)
                else:
                    token = paid.destroy(fail_at=index, original=original)
                    self.assertIn(original, paid.diagnostics)
                    with self.assertRaises(m.Refused): token.release()
                with self.assertRaises(m.Refused): paid.destroy()
                self.assertEqual(root.used_storage, 1000000)
                self.assertIsNone(paid.outcome.complete_token)

    def test_full_identity_and_field_substitutions_never_reach_leaf(self):
        _, _, reference, _, _ = complete()
        alterations = []
        for key in reference.correspondence.mapping():
            alterations.append(("missing:" + key, lambda v, k=key: v.pop(k)))
        alterations.append(("extra", lambda v: v.update(extra=1)))
        for i in range(4):
            for field in m.TestFileIdentity.__dataclass_fields__:
                def change(v, index=i, name=field):
                    identities = list(v["actual4"])
                    identities[index] = replace(identities[index], **{name: getattr(identities[index], name) + 1})
                    v["actual4"] = tuple(identities)
                alterations.append((str(i) + ":" + field, change))
        for label, change in alterations:
            with self.subTest(label=label):
                _, paid, view, _, _ = complete()
                provenance = view.correspondence.mapping()
                change(provenance)
                result = selected(paid, view, provenance=provenance)
                with self.assertRaises(m.Refused) as caught: m.correlate_before_leaf(paid, view, result)
                self.assertEqual(paid.state, "consumed")
                self.assertIs(result.owner, paid)
                self.assertIs(paid.diagnostics[-1], caught.exception)
                self.assertNotIn("leaf-model-only", paid.effects)

    def test_distinct_handle_positive_and_foreign_or_copied_view_negative(self):
        _, paid, view, _, _ = complete()
        result = selected(paid, view)
        self.assertTrue(all(a is not b for a, b in zip(view.files[:4], result.files)))
        m.correlate_before_leaf(paid, view, result)
        with self.assertRaises(m.Refused): m.correlate_before_leaf(paid, view, result)
        for mode in ("copied", "other", "generation", "retirement"):
            _, paid, view, _, _ = complete()
            result = selected(paid, view)
            if mode == "copied": view = replace(view)
            elif mode == "other": _, paid = reserve()
            elif mode == "generation": paid.replace_generation_model_only()
            else: paid.destroy()
            with self.assertRaises(m.Refused): m.correlate_before_leaf(paid, view, result)
            self.assertNotIn("leaf-model-only", paid.effects)


class RequiredPropertyControls(unittest.TestCase):
    def test_public_correlation_refusal_consumes_the_attempt(self):
        # Public constructor, no internal mutation or hostile monkeypatching.
        _, paid, view, _, _ = complete()
        malformed = selected(paid, view, buffer_count=3)
        with self.assertRaises(m.Refused): m.correlate_before_leaf(paid, view, malformed)
        good = selected(paid, view)
        with self.assertRaises(m.Refused, msg="malformed selected refusal must consume original attempt"):
            m.correlate_before_leaf(paid, view, good)
        self.assertNotIn("leaf-model-only", paid.effects)

    def test_public_correlation_refusal_keeps_selected_files_charged(self):
        root, paid, view, _, _ = complete()
        malformed = selected(paid, view, buffer_count=3)
        with self.assertRaises(m.Refused) as caught: m.correlate_before_leaf(paid, view, malformed)
        self.assertIs(paid.diagnostics[-1], caught.exception)
        token = paid.destroy()
        # Safe alternatives: selected files retire OR no complete/releasable token.
        still_live = any(h.live for h in malformed.files) or malformed.live
        self.assertFalse(token.complete and still_live,
                         "complete token while supplied selected/files remain live outside outcome")
        if still_live:
            with self.assertRaises(m.Refused): token.release()
            self.assertEqual(root.used_storage, 1000000)

    def test_forbidden_old_api_refusal_does_not_allow_retry(self):
        _, paid, view, _, _ = complete()
        result = selected(paid, view)
        with self.assertRaises(m.Refused): m.correlate_before_leaf(paid, view, result, {})
        with self.assertRaises(m.Refused, msg="old-API refusal is still a consuming attempt"):
            m.correlate_before_leaf(paid, view, result)

    def test_strict_session_rejects_numeric_identity_and_extent_coercion(self):
        mutations = (
            lambda r: r.update(extent=float(r["extent"])),
            lambda r: r["source_identity"].update(inode=float(r["source_identity"]["inode"])),
            lambda r: r["source_identity"].update(mtime_ns=float(r["source_identity"]["mtime_ns"])),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)):
                with self.assertRaises(m.Refused, msg="strict session must reject JSON non-integer fields"):
                    complete(record_change=mutate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
