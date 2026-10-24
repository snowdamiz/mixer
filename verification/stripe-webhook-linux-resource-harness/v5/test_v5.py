"""Actual metadata/Session regressions; finite syscall mocks, never live proc."""
import contextlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import checkpoint
import lifecycle as life
import linux_backend as backend
import proc_inventory as proc
from test_v4 import KernelFixture


class DescriptorFixture(KernelFixture):
    def __init__(self, action="permission", malformed=None):
        super().__init__()
        self.values[("311", "pid_for_children")] = 9
        self.targets["311"] = {7: "socket:[999]", 8: "pipe:[888]"}
        self.action, self.malformed = action, malformed
        self.links, self.scanners = [], 0
    @contextlib.contextmanager
    def scandir(self, handle):
        self.scanners += 1
        try:
            with super().scandir(handle) as entries:
                if self.handles[handle][0].endswith("/311/fd") and self.action == "duplicate":
                    yield iter([SimpleNamespace(name="7"), SimpleNamespace(name="7")])
                elif self.handles[handle][0].endswith("/311/fd") and self.action == "bad_entry":
                    yield iter([SimpleNamespace(name="7"), SimpleNamespace(name="unknown")])
                else:
                    yield entries
        finally:
            self.scanners -= 1
    def readlink(self, name, *, dir_fd=None):
        self.links.append((self.handles[dir_fd][0].split("/")[4], name))
        if name == "8":
            if self.action == "permission": raise PermissionError("PRIVATE_ERROR_VALUE")
            if self.action == "exit":
                self.tids.remove("311"); raise FileNotFoundError("PRIVATE_ERROR_VALUE")
            if self.action == "live_enoent": raise FileNotFoundError("PRIVATE_ERROR_VALUE")
            if self.action == "malformed": return self.malformed
            if self.action == "change":
                self.targets["311"][7] = "socket:[111]"
        result = super().readlink(name, dir_fd=dir_fd)
        if name == "7" and self.action == "deadline": self.now = 10
        return result
    @contextlib.contextmanager
    def patched(self, module=proc):
        with super().patched(module):
            try: yield
            finally:
                if self.scanners: raise AssertionError("modeled scandir iterator leaked")


class V5Controls(unittest.TestCase):
    def old_inventory(self):
        spec = importlib.util.spec_from_file_location("sealed_v4_descriptor_inventory", checkpoint.PACKET / "v4/proc_inventory.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module
    def inventory(self, model, module=proc):
        with model.patched(module):
            return module.holder_counts({777}, {888, 999}, 10, pid_namespace_ids={777})
    def failed_inventory(self, model, module=proc):
        with self.assertRaises(life.Unavailable) as caught:
            self.inventory(model, module)
        return dict(caught.exception.observed_counts)
    def session(self):
        owner = backend.LinuxBackend(Path("/model/parent"), Path("/model/release"), {}, "model", {})
        session = backend.Session(owner, "idle"); owner.active = session; owner.sessions.append(session)
        session.disposal_steps = mock.Mock()
        session.stop_started = session.term_at = session.empty_at = 1; session.term_count = 1
        session.namespace_ids, session.role_pid_namespace, session.descriptor_inodes = {777}, 777, {888, 999}
        return owner, session
    def fail_cleanup(self, owner, model):
        # Actual backend -> Session -> holder_counts -> Inventory -> ProcMetadata;
        # only destructive disposal and low-level OS operations are mocked.
        with model.patched(), self.assertRaises(life.Unavailable):
            owner.cleanup(object())
        return owner.cleanup_attempt_records()[-1]
    def retry_zero(self, owner):
        with mock.patch.object(backend, "holder_counts", return_value=proc.HolderCounts(proc.ZERO, proc.ZERO)), \
             mock.patch.object(backend.time, "monotonic_ns", return_value=2):
            owner.cleanup(object())
    def assert_socket_reference(self, record, status="partial"):
        self.assertEqual(record["countsStatus"], status)
        self.assertEqual(record["observedReferenceCounts"]["socketHolders"], 1)
        self.assertEqual(record["observedReferenceCounts"]["listenerHolders"], 1)
    def test_old_permission_loss_reproduced_and_new_actual_adapter_retains_read(self):
        old = self.failed_inventory(DescriptorFixture(), self.old_inventory())
        current = self.failed_inventory(DescriptorFixture())
        self.assertEqual(old["socketHolders"], 0)
        self.assertEqual(current["socketHolders"], 1)
        self.assertEqual(current["listenerHolders"], 1)
    def test_old_proved_exit_history_loss_reproduced_and_new_adapter_retains_it(self):
        old = self.inventory(DescriptorFixture("exit"), self.old_inventory())
        current = self.inventory(DescriptorFixture("exit"))
        self.assertEqual(old, proc.ZERO); self.assertEqual(current, proc.ZERO)
        self.assertEqual(dict(old.observed_counts)["socketHolders"], 0)
        self.assertEqual(dict(current.observed_counts)["socketHolders"], 1)
    def test_actual_session_permission_error_freezes_known_partial_reference(self):
        owner, session = self.session(); model = DescriptorFixture()
        record = self.fail_cleanup(owner, model)
        self.assert_socket_reference(record)
        self.assertEqual(record["observedCounts"]["socketHolders"], 1)
        self.assertEqual(record["failureReason"], "inventory_unavailable")
        self.assertFalse(record["physicalDisposalComplete"])
        self.assertTrue(session.failed and owner.admission_blocked)
        self.assertIn(("311", "7"), model.links); self.assertIn(("311", "8"), model.links)
    def test_actual_session_proved_exit_keeps_history_and_valid_final_zero_separate(self):
        owner, session = self.session(); model = DescriptorFixture("exit")
        with model.patched(): owner.cleanup(object())
        record = owner.cleanup_attempt_records()[0]
        self.assert_socket_reference(record, "actual")
        self.assertEqual(record["observedCounts"], proc.ZERO)
        self.assertEqual(record["physicalProof"]["socketHolders"], 0)
        self.assertEqual(record["outcome"], "disposed")
        self.assertTrue(session.cleaned and owner.cleanup_complete())
    def test_actual_session_malformed_metadata_retains_prior_read_and_fails_closed(self):
        for malformed in (None, True, "socket:[bogus]", "socket:[0]", "socket:[-1]", "socket:[18446744073709551616]", "socket:[９９９]"):
            with self.subTest(value=malformed):
                owner, session = self.session()
                record = self.fail_cleanup(owner, DescriptorFixture("malformed", malformed))
                self.assert_socket_reference(record)
                self.assertEqual(record["failureReason"], "inventory_unavailable")
                self.assertTrue(session.failed and owner.admission_blocked)
                self.assertNotIn("PRIVATE_ERROR_VALUE", session.cleanup_attempts[0].decode())
    def test_actual_session_partial_positive_to_zero_retry_preserves_failure_and_counts(self):
        owner, session = self.session(); first = self.fail_cleanup(owner, DescriptorFixture())
        frozen = session.cleanup_attempts[0]; original_deadline = first["deadlineMonotonicNs"]
        self.retry_zero(owner); records = owner.cleanup_attempt_records()
        self.assertEqual([r["countsStatus"] for r in records], ["partial", "actual"])
        self.assertEqual([r["observedCounts"]["socketHolders"] for r in records], [1, 0])
        self.assertEqual([r["outcome"] for r in records], ["failed", "disposed"])
        self.assertEqual(session.cleanup_attempts[0], frozen)
        self.assertEqual({r["deadlineMonotonicNs"] for r in records}, {original_deadline})
        self.assertEqual(session.last_counts["socketHolders"], 1)
        self.assertTrue(session.cleaned and session.failed and owner.admission_blocked)
        self.assertFalse(owner.cleanup_complete())
        with self.assertRaises(life.Unavailable): owner.admit()
    def test_actual_session_detached_views_cannot_erase_partial_history_after_retry(self):
        owner, session = self.session(); self.fail_cleanup(owner, DescriptorFixture())
        frozen = session.cleanup_attempts[0]; self.retry_zero(owner)
        one, two = session.cleanup_attempt_records(), owner.cleanup_attempt_records()
        one[0]["observedCounts"]["socketHolders"] = 0
        two[0]["observedReferenceCounts"]["socketHolders"] = 0
        two[0]["failureReason"] = None; two.clear()
        self.assertEqual(session.cleanup_attempts[0], frozen)
        record = owner.cleanup_attempt_records()[0]
        self.assert_socket_reference(record)
        self.assertEqual(record["observedCounts"]["socketHolders"], 1)
        self.assertEqual(record["failureReason"], "inventory_unavailable")
    def test_live_tid_enoent_cannot_become_zero_and_preserves_partial(self):
        owner, session = self.session()
        record = self.fail_cleanup(owner, DescriptorFixture("live_enoent"))
        self.assert_socket_reference(record)
        self.assertFalse(session.cleaned)
    def test_deadline_after_successful_read_still_retains_reference_and_closes_stream(self):
        model = DescriptorFixture("deadline")
        counts = self.failed_inventory(model)
        self.assertEqual(counts["socketHolders"], 1)
        self.assertNotIn(("311", "8"), model.links)
        self.assertFalse(model.handles); self.assertEqual(model.scanners, 0)
    def test_changed_fd_view_refuses_final_zero_and_retains_prior_reference(self):
        owner, session = self.session()
        record = self.fail_cleanup(owner, DescriptorFixture("change"))
        self.assert_socket_reference(record)
        self.assertFalse(session.cleaned)
    def test_duplicate_descriptor_refuses_qualification_without_double_counting(self):
        owner, _ = self.session(); record = self.fail_cleanup(owner, DescriptorFixture("duplicate"))
        self.assert_socket_reference(record)
        self.assertEqual(record["observedCounts"]["socketHolders"], 1)
    def test_malformed_directory_entry_retains_earlier_reference_and_closes_iterator(self):
        owner, _ = self.session(); model = DescriptorFixture("bad_entry")
        self.assert_socket_reference(self.fail_cleanup(owner, model))
        self.assertEqual(model.scanners, 0)
    def test_ordinary_file_target_is_discarded_without_receipt_content(self):
        owner, session = self.session(); model = DescriptorFixture("ordinary")
        model.targets["311"] = {7: "/PRIVATE_PROCESS_FILE_VALUE"}
        with model.patched(): owner.cleanup(object())
        record = owner.cleanup_attempt_records()[0]
        self.assertEqual(record["observedCounts"], proc.ZERO)
        self.assertEqual(record["observedReferenceCounts"], proc.ZERO)
        self.assertNotIn("PRIVATE_PROCESS_FILE_VALUE", session.cleanup_attempts[0].decode())
    def test_stable_two_pass_descriptor_reference_is_deduplicated_but_not_zero(self):
        owner, _ = self.session(); model = DescriptorFixture("stable")
        model.targets["311"] = {7: "socket:[999]"}
        record = self.fail_cleanup(owner, model)
        self.assert_socket_reference(record, "actual")
        self.assertEqual(record["observedCounts"]["socketHolders"], 1)
        self.assertEqual(record["failureReason"], "holders_present")
    def test_distinct_fds_for_same_owned_inode_remain_distinct_known_references(self):
        owner, _ = self.session(); model = DescriptorFixture("stable")
        model.targets["311"] = {7: "socket:[999]", 8: "socket:[999]"}
        record = self.fail_cleanup(owner, model)
        self.assertEqual(record["observedCounts"]["socketHolders"], 2)
        self.assertEqual(record["observedReferenceCounts"]["socketHolders"], 2)
    def test_backend_and_role_authority_bytes_are_identical_to_sealed_v4(self):
        for name in ("linux_backend.py", "lifecycle.py", "control_nif.c", "fault_helper.c", "role.exs", "signal-authority.json"):
            self.assertEqual((Path(__file__).parent / name).read_bytes(), (checkpoint.PACKET / "v4" / name).read_bytes(), name)


if __name__ == "__main__": unittest.main(verbosity=2)
