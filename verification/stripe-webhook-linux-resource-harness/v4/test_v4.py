"""Actual adapter/session controls with low-level operations mocked; no live proc."""
import contextlib
import importlib.util
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest import mock

import checkpoint
import lifecycle as life
import linux_backend as backend
import proc_inventory as proc
import run as candidate
from test_host import proof


class KernelFixture:
    """Finite low-level syscall model; actual ProcMetadata remains installed."""
    def __init__(self):
        self.tids = {"310", "311"}
        self.handles, self.identities, self.visits = {}, {}, []
        self.next_fd, self.now = 70, 1
        self.values = {("311", "pid_for_children"): 777}
        self.targets = {"310": {}, "311": {}}
        self.errors, self.reads = {}, {}
        self.on_namespace = None
    def directory(self, path):
        if path in ("/proc", "/proc/310", "/proc/310/task"): return True
        return any(path in ("/proc/310/task/" + tid, "/proc/310/task/" + tid + "/ns",
                           "/proc/310/task/" + tid + "/fd") for tid in self.tids)
    def path(self, name, parent):
        return str(name) if parent is None else self.handles[parent][0] + "/" + str(name)
    def metadata(self, path):
        if path not in self.identities: self.identities[path] = len(self.identities) + 400
        return SimpleNamespace(st_dev=1, st_ino=self.identities[path], st_uid=0, st_mode=stat.S_IFDIR | 0o555)
    def open(self, name, flags, *, dir_fd=None):
        path = self.path(name, dir_fd)
        if not self.directory(path): raise FileNotFoundError()
        if not flags & backend.os.O_NOFOLLOW or not flags & backend.os.O_DIRECTORY:
            raise AssertionError("identity open must not follow links")
        handle = self.next_fd; self.next_fd += 1
        self.handles[handle] = path, self.metadata(path)
        return handle
    def close(self, handle): del self.handles[handle]
    def fstat(self, handle): return self.handles[handle][1]
    def stat(self, name, *, dir_fd=None, follow_symlinks=True):
        path = self.path(name, dir_fd); self.visits.append(path)
        if path in self.errors: raise self.errors[path]()
        if self.directory(path): return self.metadata(path)
        parts = path.split("/")
        if len(parts) != 7 or parts[5] != "ns" or parts[4] not in self.tids: raise FileNotFoundError()
        if not follow_symlinks: raise AssertionError("namespace identity must be read")
        tid, kind = parts[4], parts[6]
        self.reads[path] = self.reads.get(path, 0) + 1
        if self.on_namespace: self.on_namespace(tid, kind, self.reads[path])
        return SimpleNamespace(st_ino=self.values.get((tid, kind), 9))
    @contextlib.contextmanager
    def scandir(self, handle):
        path = self.handles[handle][0]
        if not self.directory(path): raise FileNotFoundError()
        if path == "/proc": names = ("310",)
        elif path.endswith("/task"): names = tuple(sorted(self.tids))
        elif path.endswith("/fd"): names = tuple(self.targets[path.split("/")[4]])
        else: raise AssertionError("unexpected directory scope")
        yield iter(SimpleNamespace(name=str(name)) for name in names)
    def readlink(self, name, *, dir_fd=None):
        path = self.path(name, dir_fd); parts = path.split("/")
        return self.targets[parts[4]][int(parts[6])]
    @contextlib.contextmanager
    def patched(self, module=proc):
        with mock.patch.object(module.os, "open", side_effect=self.open), \
             mock.patch.object(module.os, "close", side_effect=self.close), \
             mock.patch.object(module.os, "stat", side_effect=self.stat), \
             mock.patch.object(module.os, "fstat", side_effect=self.fstat), \
             mock.patch.object(module.os, "scandir", side_effect=self.scandir), \
             mock.patch.object(module.os, "readlink", side_effect=self.readlink), \
             mock.patch.object(module.time, "monotonic_ns", side_effect=lambda: self.now):
            try: yield
            finally:
                if self.handles: raise AssertionError("modeled inventory handle leaked")


class V4Controls(unittest.TestCase):
    def reject(self, action):
        with self.assertRaises(life.Unavailable): action()
    def old_inventory(self):
        spec = importlib.util.spec_from_file_location("sealed_v3_inventory", checkpoint.PACKET / "v3/proc_inventory.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module
    def inventory(self, fixture, **kwargs):
        with fixture.patched(): return proc.holder_counts({777}, {888, 999}, 10, **kwargs)
    def session(self):
        owner = backend.LinuxBackend(Path("/model/parent"), Path("/model/release"), {}, "model", {})
        session = backend.Session(owner, "idle"); owner.active = session; owner.sessions.append(session)
        session.disposal_steps = mock.Mock()
        session.stop_started = session.term_at = 1000; session.term_count = 1; session.empty_at = 1100
        return owner, session
    @contextlib.contextmanager
    def cleanup_observations(self, observations):
        with mock.patch.object(backend, "holder_counts", side_effect=observations) as calls, \
             mock.patch.object(backend.time, "monotonic_ns", return_value=1200): yield calls
    def test_old_actual_adapter_misses_child_reference_and_new_adapter_detects_it(self):
        old = self.old_inventory(); model = KernelFixture()
        with model.patched(old): self.assertEqual(old.holder_counts({777}, set(), 10), proc.ZERO)
        self.assertFalse(any(path.endswith("pid_for_children") for path in model.visits))
        model = KernelFixture(); counts = self.inventory(model, pid_namespace_ids={777})
        self.assertEqual(counts["namespaceHolders"], 1)
        self.assertIn("/proc/310/task/311/ns/pid_for_children", model.visits)
        self.reject(lambda: life.validate_cleanup({**proof(), **counts}))
    def test_child_reference_matches_only_known_owned_pid_namespace_ids(self):
        self.assertEqual(self.inventory(KernelFixture()), proc.ZERO)
        model = KernelFixture()
        with model.patched(): self.reject(lambda: proc.holder_counts({9}, set(), 10, pid_namespace_ids={777}))
    def test_missing_child_metadata_for_live_leader_or_nonleader_refuses_zero(self):
        for tid in ("310", "311"):
            model = KernelFixture(); model.errors[f"/proc/310/task/{tid}/ns/pid_for_children"] = FileNotFoundError
            self.reject(lambda: self.inventory(model, pid_namespace_ids={777}))
    def test_unreadable_or_ambiguous_child_metadata_refuses_zero(self):
        model = KernelFixture(); model.errors["/proc/310/task/311/ns/pid_for_children"] = PermissionError
        self.reject(lambda: self.inventory(model, pid_namespace_ids={777}))
        for value in (0, -1, None, True, "777"):
            model = KernelFixture(); model.values[("311", "pid_for_children")] = value
            self.reject(lambda: self.inventory(model, pid_namespace_ids={777}))
    def test_changing_child_reference_cannot_be_accepted_as_stable(self):
        model = KernelFixture()
        def changed(tid, kind, count):
            if tid == "311" and kind == "pid_for_children" and count == 2: model.values[(tid, kind)] = 9
        model.on_namespace = changed
        self.reject(lambda: self.inventory(model, pid_namespace_ids={777}))
    def test_only_explicitly_proved_task_exit_allows_missing_child_link(self):
        model = KernelFixture(); model.values[("311", "net")] = 777
        def exited(tid, kind, _):
            if tid == "311" and kind == "pid_for_children":
                model.tids.remove("311"); raise FileNotFoundError()
        model.on_namespace = exited
        counts = self.inventory(model, pid_namespace_ids={777})
        self.assertEqual(counts, proc.ZERO)
        self.assertEqual(dict(counts.observed_counts)["namespaceHolders"], 1)
    def test_child_link_keeps_original_deadline_and_nonleader_fd_detection(self):
        model = KernelFixture(); model.targets["311"] = {7: "pipe:[888]", 8: "socket:[999]"}
        counts = self.inventory(model, pid_namespace_ids={777})
        self.assertEqual((counts["namespaceHolders"], counts["pipeHolders"], counts["socketHolders"]), (1, 1, 1))
        model = KernelFixture()
        def expired(_, kind, __):
            if kind == "pid_for_children": model.now = 10
        model.on_namespace = expired
        self.reject(lambda: self.inventory(model, pid_namespace_ids={777}))
    def test_actual_session_preserves_positive_then_zero_attempts_and_failure(self):
        owner, session = self.session(); positive = dict(proc.ZERO, namespaceHolders=1)
        session.namespace_ids = {777}; session.role_pid_namespace = 777
        with self.cleanup_observations([positive, dict(proc.ZERO)]) as calls:
            self.reject(lambda: owner.cleanup(object()))
            first = session.cleanup_attempts[0]
            owner.cleanup(object())
            self.assertEqual(calls.call_args.kwargs["pid_namespace_ids"], {777})
        attempts = owner.cleanup_attempt_records()
        self.assertEqual([a["observedCounts"]["namespaceHolders"] for a in attempts], [1, 0])
        self.assertEqual([a["countsStatus"] for a in attempts], ["actual", "actual"])
        self.assertEqual([a["outcome"] for a in attempts], ["failed", "disposed"])
        self.assertEqual(first, session.cleanup_attempts[0])
        self.assertEqual(session.last_counts["namespaceHolders"], 1)
        self.assertTrue(session.cleaned and session.failed and owner.admission_blocked)
        self.assertEqual(session.first_cleanup_failure_reason, "holders_present")
        self.assertNotEqual(session.error_reason, "completed")
        self.assertFalse(owner.cleanup_complete())
        self.assertEqual({a["stopStartedMonotonicNs"] for a in attempts}, {1000})
    def test_actual_session_preserves_unknown_then_success_without_exception_text(self):
        owner, session = self.session()
        with self.cleanup_observations([OSError("MIXER_BODY_SENTINEL"), dict(proc.ZERO)]):
            self.reject(lambda: owner.cleanup(object())); owner.cleanup(object())
        records = session.cleanup_attempt_records()
        self.assertIsNone(records[0]["observedCounts"])
        self.assertEqual(records[0]["countsStatus"], "unknown")
        self.assertEqual(records[0]["failureReason"], "inventory_unavailable")
        self.assertNotIn("MIXER_BODY_SENTINEL", b"".join(session.cleanup_attempts).decode())
        self.assertTrue(session.failed and owner.admission_blocked)
    def test_actual_session_preserves_partial_observations_before_retry(self):
        owner, session = self.session(); partial = dict(proc.ZERO, pipeHolders=2)
        with self.cleanup_observations([proc.InventoryUnavailable(partial), dict(proc.ZERO)]):
            self.reject(lambda: owner.cleanup(object())); owner.cleanup(object())
        first, second = owner.cleanup_attempt_records()
        self.assertEqual((first["countsStatus"], first["observedCounts"]["pipeHolders"]), ("partial", 2))
        self.assertEqual(second["observedCounts"]["pipeHolders"], 0)
        self.assertEqual(first["failureReason"], "inventory_unavailable")
        self.assertTrue(session.failed)
    def test_actual_session_action_failure_and_available_samples_are_frozen(self):
        owner, session = self.session(); session.samples = [{"monotonicNs": 900, "pids.current": 2}]
        session.disposal_steps.side_effect = backend.base.Refusal("output_schema")
        session.emergency_dispose = mock.Mock()
        with self.cleanup_observations([]): self.reject(lambda: owner.cleanup(object()))
        frozen = session.cleanup_attempts[0]
        session.samples[0]["pids.current"] = 0
        session.disposal_steps.side_effect = None
        with self.cleanup_observations([dict(proc.ZERO)]): owner.cleanup(object())
        first = session.cleanup_attempt_records()[0]
        self.assertEqual(first["samples"][0]["pids.current"], 2)
        self.assertEqual(first["failureReason"], "output_schema")
        self.assertEqual(frozen, session.cleanup_attempts[0])
        self.assertEqual(session.error_reason, "output_schema")
    def test_attempt_views_are_detached_and_idempotent_call_is_not_new_observation(self):
        owner, session = self.session()
        with self.cleanup_observations([dict(proc.ZERO)]): owner.cleanup(object()); owner.cleanup(object())
        records = session.cleanup_attempt_records(); records[0]["observedCounts"]["namespaceHolders"] = 99
        again = session.cleanup_attempt_records()
        self.assertEqual(again[0]["observedCounts"]["namespaceHolders"], 0)
        self.assertEqual((again[1]["outcome"], again[1]["countsStatus"]), ("already_disposed", "unknown"))
        self.assertIsNone(again[1]["observedCounts"])
    def test_first_failure_survives_multiple_failures_and_physical_success(self):
        owner, session = self.session()
        with self.cleanup_observations([dict(proc.ZERO, socketHolders=1, listenerHolders=1), OSError(), dict(proc.ZERO)]):
            self.reject(lambda: owner.cleanup(object())); self.reject(lambda: owner.cleanup(object())); owner.cleanup(object())
        records = owner.cleanup_attempt_records()
        self.assertEqual(len(records), 3)
        self.assertEqual([a["attemptIndex"] for a in records], [1, 2, 3])
        self.assertEqual({a["retainedFailureReason"] for a in records}, {"holders_present"})
        self.assertEqual(session.last_counts["socketHolders"], 1)
        self.assertTrue(session.failed and owner.admission_blocked)
    def test_row_receipt_serializes_every_attempt_after_physical_cleanup(self):
        owner, session = self.session()
        def run_model(*_):
            self.reject(lambda: owner.cleanup(object())); owner.cleanup(object()); return []
        args = SimpleNamespace(delegated_cgroup=Path("/model/parent"), release=Path("/model/release"), profile=Path("/model/profile"), review=Path("/model/review"))
        with mock.patch.object(backend, "LinuxBackend", return_value=owner), \
             mock.patch.object(life, "run_r14", side_effect=run_model), \
             self.cleanup_observations([dict(proc.ZERO, namespaceHolders=1), dict(proc.ZERO)]):
            row = candidate.execute_row("R14", args, {}, {}, "", 1000)
        self.assertEqual(row["status"], "failed")
        self.assertFalse(row["cleanup"]["complete"])
        self.assertEqual([a["observedCounts"]["namespaceHolders"] for a in row["cleanup"]["attempts"]], [1, 0])


if __name__ == "__main__": unittest.main(verbosity=2)
