"""Host-only independent controls; failures assert the documented contract."""
import copy
from contextlib import ExitStack
import hashlib
import importlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "replay"))
import prototype as p
import schema as s
import test_preparation as t

OBSERVATIONS = []

class Independent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="independent-", dir=ROOT / "replay" / "owned-scratch")
        self.directory = Path(self.tmp.name)
        self.assertFalse(p.OPEN_FDS)

    def tearDown(self):
        self.assertFalse(p.OPEN_FDS)
        self.assertFalse(p.STDIO_FDS)
        self.assertFalse(p.QUARANTINES)
        self.tmp.cleanup()

    def test_closed_retained_wrapper_cannot_reauthorize_reused_descriptor(self):
        path = self.directory / "file"
        path.write_bytes(b"unchanged quiescent bytes")
        stale = p.Retained(path, path.stat().st_size)
        stale_fd = stale.fd
        stale.close()
        with p.Retained(path, path.stat().st_size) as fresh:
            self.assertEqual(stale_fd, fresh.fd, "deterministic same-order reopen reused the descriptor number")
            observation = {"id": "R01", "stale_fd_equal_fresh_fd": stale.fd == fresh.fd, "stale_owned_fds": len(stale.fds), "fresh_owned_fds": len(fresh.fds)}
            try:
                digest = p.hash_range(stale, bytearray(4096), p.IOCount(), p.IO())
            except p.Refusal as error:
                observation["refused"] = error.code
            else:
                observation["stale_hash_accepted"] = digest.hex()
                self.assertEqual(digest, hashlib.sha256(path.read_bytes()).digest())
            OBSERVATIONS.append(observation)
            self.assertIn("refused", observation, "closed wrapper must refuse; reused fd belongs to fresh owner")

    def test_close_failure_still_accounts_for_and_closes_remaining_owned_descriptors(self):
        path = self.directory / "file"
        path.write_bytes(b"x")
        held = p.Retained(path, 1)
        original = os.close
        first = True
        owned_before = tuple(held.fds)
        def close_then_error(fd):
            nonlocal first
            original(fd)
            if first:
                first = False
                raise OSError("injected post-close reporting failure")
        try:
            with patch.object(p.os, "close", close_then_error):
                with self.assertRaises(OSError):
                    held.close()
            left = sorted(p.OPEN_FDS)
            live = []
            for fd in left:
                try:
                    os.fstat(fd)
                    live.append(fd)
                except OSError:
                    pass
            OBSERVATIONS.append({"id": "R02", "owned_before": len(owned_before), "tracked_remaining": len(left), "actual_known_owned_still_open": len(live), "scope": "injected close report after actual leaf close; no OS fault claim"})
            self.assertEqual(live, [], "close failure must not strand every remaining ancestor descriptor")
        finally:
            for fd in tuple(p.OPEN_FDS):
                try:
                    original(fd)
                finally:
                    p.OPEN_FDS.remove(fd)
            held.fds.clear()

    def test_nonterminal_child_model_keeps_body_and_profile_leased(self):
        paths, sizes, head, _ = t.fixture(self.directory)
        class Nonterminal:
            returncode = None
            def __init__(self, *args, **kwargs):
                self.kills = self.waits = 0
            def wait(self, timeout):
                self.waits += 1
                raise p.subprocess.TimeoutExpired("finite source-fault model; no process created", timeout)
            def kill(self): self.kills += 1
            def poll(self): return None
        observed = None
        try:
            with patch.object(p.subprocess, "Popen", Nonterminal):
                with self.assertRaises(p.Refusal):
                    p.compose_fixture(paths, sizes, head, self.directory / "output", self.directory)
            self.assertEqual(len(p.QUARANTINES), 1)
            process, held = p.QUARANTINES[0]
            self.assertEqual(len(held), 2)
            self.assertTrue(all(x.live for x in held))
            self.assertEqual((process.waits, process.kills), (3, 2))
            for owner in held:
                with self.assertRaises(p.Refusal): owner.close()
            observed = {"id": "R03", "model_only_no_process_created": True, "leased_owners": 2, "wait_calls": process.waits, "kill_calls": process.kills, "retained_fds_quarantined_before_model_cleanup": len(p.OPEN_FDS)}
        finally:
            # No process exists in this modeled branch. Retire only this model's
            # actual owned descriptor wrappers after recording preserved lease.
            for _, held in p.QUARANTINES:
                for owner in held:
                    owner.live = False
                    owner.close()
            p.QUARANTINES.clear()
        OBSERVATIONS.append(observed)

    def test_preclose_error_does_not_forget_known_open_descriptor(self):
        path = self.directory / "file"
        path.write_bytes(b"x")
        held = p.Retained(path, 1)
        captured = tuple(held.fds)
        leaf = held.fd
        original = os.close
        first = True
        def fail_before_close(fd):
            nonlocal first
            if first:
                first = False
                raise OSError("injected before actual leaf close")
            return original(fd)
        try:
            with patch.object(p.os, "close", fail_before_close):
                with self.assertRaises(OSError): held.close()
            os.fstat(leaf)
            OBSERVATIONS.append({"id": "R02B", "leaf_confirmed_open_by_owned_fstat": True, "leaf_still_tracked": leaf in p.OPEN_FDS, "captured_owned_before": len(captured), "registry_after": len(p.OPEN_FDS), "scope": "injected pre-close failure; no actual kernel fault claimed"})
            self.assertIn(leaf, p.OPEN_FDS, "unclosed leaf cannot disappear from ownership accounting")
        finally:
            # No new descriptor is opened before retiring the captured set.
            for fd in reversed(captured):
                original(fd)
                p.OPEN_FDS.discard(fd)
            held.fds.clear()

    def test_canonical_decode_closes_duplicate_and_noncanonical_number_forms(self):
        for raw in (b'MIXTST01\n{"x":-0}\n', b'MIXTST01\n{"x":1e0}\n', b'MIXTST01\n{"x":NaN}\n', b'MIXTST01\n{"x":0,"x":0}\n'):
            with self.subTest(raw=raw), self.assertRaises(s.SchemaError): s.decode(b"MIXTST01", raw)

    def test_all_eight_original_transport_claim_ranges_are_zero_and_only_claims_change(self):
        claims = [hashlib.sha256(bytes([i])).digest() for i in range(8)]
        original = t.header([bytes(32)] * 8)
        final = p.bind_fixture_template(original, claims, 128)
        self.assertEqual(final[:128] + final[384:], original[:128] + original[384:])
        self.assertEqual(original[128:384], bytes(256))
        for i in range(8):
            malformed = bytearray(original)
            malformed[128 + i * 32] = 1
            with self.subTest(slot=i), self.assertRaises(p.Refusal): p.bind_fixture_template(bytes(malformed), claims, 128)
        OBSERVATIONS.append({"id": "R05", "all_eight_zero_claim_slots_checked": True, "nonclaim_bytes_preserved": 256, "original_retained_bytes_unchanged": original == t.header([bytes(32)] * 8)})

    def test_complete_snapshot_field_sets_match_frozen_owner_and_accounting(self):
        value = t.snapshot_fixture()
        self.assertEqual(set(value), {"schema", "validator_revision", "decoder_revision", "policy", "source", "metadata", "resolved_imports", "usage", "observations", "provenance"})
        self.assertEqual(len(s.USAGE), 10)
        self.assertEqual(len(s.OBSERVATIONS), 18)
        for name in s.BUFFERS:
            self.assertEqual(set(value["metadata"][name]), {"capacity", "charged", "category", "items"})
            modified = copy.deepcopy(value)
            modified["metadata"][name]["charged"] += 1
            self.assertNotEqual(s.snapshot(value), s.snapshot(modified))
        for section in ("usage", "observations", "provenance"):
            for key in value[section]:
                modified = copy.deepcopy(value)
                del modified[section][key]
                with self.subTest(section=section, key=key), self.assertRaises(s.SchemaError): s.snapshot(modified)

    def test_source_manifest_roles_are_domain_separated(self):
        base = {"schema": 1, "role": "baseline", "members": [{"path": "vm/a.rs", "bytes": 1, "sha256": "11" * 32, "role": "distribution"}]}
        other = copy.deepcopy(base)
        other["role"] = "candidate"
        self.assertNotEqual(hashlib.sha256(s.source_manifest(base)).digest(), hashlib.sha256(s.source_manifest(other)).digest())

    def test_independent_explicit_io_envelope_arithmetic(self):
        limits = json.loads((ROOT.parent / "swift-retained-profile-composition-preparation" / "budget.json").read_bytes())
        blocks = sum((size + 4095) // 4096 for size in p.CAPS)
        self.assertEqual(limits["parent_read_calls_max"], 32 * (2 * blocks + 625 + 2 * 626 + 2 * 625 + 21))
        self.assertEqual(limits["parent_read_requested_bytes_max"], 32 * (2 * sum(p.CAPS) + p.BODY + 2 * p.PROFILE + 2 * p.BODY + 21))
        self.assertEqual(limits["parent_write_calls_max"], 32 * (625 + 1))
        self.assertEqual(limits["parent_write_requested_bytes_max"], 32 * p.PROFILE)
        self.assertEqual(limits["child_read_calls_max"], 32 * (626 + 625 + 625 + 3))
        self.assertEqual(limits["child_read_requested_bytes_max"], 32 * (p.PROFILE + 2 * p.BODY + 3))
        self.assertEqual(limits["visible_retained_descriptors_max"], 9 * 65)

if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    (ROOT / "independent-results.json").write_text(json.dumps({"methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped), "observations": OBSERVATIONS, "owned_fds_final": len(p.OPEN_FDS), "stdio_fds_final": len(p.STDIO_FDS), "quarantines_final": len(p.QUARANTINES), "owned_scratch_entries_final": len(list((ROOT / "replay" / "owned-scratch").iterdir())), "actual_rust_exporter_tested": False, "real_binding_authority": False}, indent=2, sort_keys=True) + "\n")
    raise SystemExit(not result.wasSuccessful())
