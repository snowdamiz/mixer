"""Bounded host regressions. No actual /proc, signal, socket, compiler or role."""
import argparse
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import checkpoint
import lifecycle as life
import linux_backend
import proc_inventory as inventory
import run as candidate
from test_host import phase_observation, proof


def load_v2(name):
    spec = importlib.util.spec_from_file_location("sealed_v2_" + name, checkpoint.PACKET / "v2" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProcModel:
    """Finite in-memory directory/namespace/link metadata with owned handles."""
    def __init__(self):
        self.processes = {"100": {"100": {"net": 9, "fds": {}}, "101": {"net": 9, "fds": {}}}}
        self.handles, self.stamps, self.calls = {}, {}, {}
        self.next_handle = 1
        self.denied = set()
        self.on_names = self.on_namespace = self.on_descriptors = None
        self.on_named_stamp = None
        self.visited = []
    def exists(self, path):
        fields = path.split("/")
        if path == "/proc": return True
        if len(fields) < 3 or fields[2] not in self.processes: return False
        if len(fields) == 3: return True
        if fields[3] != "task": return False
        if len(fields) == 4: return True
        if fields[4] not in self.processes[fields[2]]: return False
        return len(fields) == 5 or (len(fields) == 6 and fields[5] in ("ns", "fd"))
    def ensure(self, path):
        self.visited.append(path)
        if path in self.denied: raise PermissionError()
        if not self.exists(path): raise FileNotFoundError()
    def allocate(self, path):
        self.ensure(path)
        number = self.next_handle; self.next_handle += 1
        self.handles[number] = path
        return number
    def root(self): return self.allocate("/proc")
    def open(self, parent, name): return self.allocate(self.handles[parent] + "/" + name)
    def close(self, handle): del self.handles[handle]
    def identity(self, path):
        if path not in self.stamps: self.stamps[path] = (1, len(self.stamps) + 1, 0)
        return self.stamps[path]
    def stamp(self, handle):
        path = self.handles[handle]; self.ensure(path)
        return self.identity(path)
    def named_stamp(self, parent, name):
        path = self.handles[parent] + "/" + name
        self.ensure(path)
        if self.on_named_stamp: self.on_named_stamp(path)
        return self.identity(path)
    def count(self, method, path):
        key = method, path
        self.calls[key] = self.calls.get(key, 0) + 1
        return self.calls[key]
    def names(self, handle, check):
        check()
        path = self.handles[handle]; self.ensure(path)
        count = self.count("names", path)
        if self.on_names: self.on_names(path, count)
        if path == "/proc": return tuple(sorted(self.processes))
        fields = path.split("/")
        if fields[-1] == "task": return tuple(sorted(self.processes[fields[2]]))
        raise AssertionError("metadata scope exceeded")
    def namespace(self, handle, name):
        path = self.handles[handle]; self.ensure(path)
        count = self.count("namespace:" + name, path)
        if self.on_namespace: self.on_namespace(path, name, count)
        fields = path.split("/")
        return self.processes[fields[2]][fields[4]].get(name, 9)
    def descriptors(self, handle, check):
        check()
        path = self.handles[handle]; self.ensure(path)
        count = self.count("descriptors", path)
        if self.on_descriptors: self.on_descriptors(path, count)
        fields = path.split("/")
        return tuple(sorted((str(n), inventory.descriptor_value(v))
                            for n, v in self.processes[fields[2]][fields[4]]["fds"].items()))


class RepairControls(unittest.TestCase):
    def setUp(self): self.proc = ProcModel()
    def reject(self, callback):
        with self.assertRaises(life.Unavailable): callback()
    def holders(self, namespaces={777}, descriptors={888, 999}, deadline=10):
        with mock.patch.object(inventory, "ProcMetadata", return_value=self.proc), \
             mock.patch.object(inventory.time, "monotonic_ns", return_value=1):
            try: return inventory.holder_counts(namespaces, descriptors, deadline)
            finally: self.assertEqual(self.proc.handles, {})
    def backend(self):
        return linux_backend.LinuxBackend(Path("/model/parent"), Path("/model/release"), {}, "harness", {})
    def cleaned(self):
        return SimpleNamespace(cleaned=True, proof=proof(), observation=phase_observation("idle"))
    def main_model(self, module, completed=False, validated=False, explode=False):
        args = argparse.Namespace(profile=Path("/model/profile"), delegated_cgroup=Path("/model/cgroup"),
            release=Path("/model/release"), review=Path("/model/review"), execute=True, output=Path("/model/output"))
        calls, writes = [], {}
        failed = {"caseId": "R14", "status": "failed", "reason": "cleanup", "termination": {"actualFailureRetained": 123},
                  "cleanup": {"complete": completed, "validated": validated, "launcherStarts": 1}}
        def receipt(case, *_args, **kwargs):
            status = _args[2] if len(_args) >= 3 else kwargs.get("status", "unavailable")
            return {"caseId": case, "status": status, "cleanup": {"complete": True, "validated": True, "launcherStarts": 0}}
        def row(case, *_args, **kwargs):
            calls.append(case)
            if case == "R14": return failed
            if explode: raise RuntimeError("never persisted")
            return receipt(case)
        def write(path, raw): writes[str(path)] = json.loads(raw)
        with mock.patch.object(argparse.ArgumentParser, "parse_args", return_value=args), \
             mock.patch.object(module, "output_directory", return_value=args.output), \
             mock.patch.object(Path, "mkdir"), mock.patch.object(Path, "write_bytes", autospec=True, side_effect=write), \
             mock.patch.object(module.base, "linux_capabilities", return_value={"schema": 1}), \
             mock.patch.object(module, "harness_digest", return_value="h"), \
             mock.patch.object(module, "check_amendment"), mock.patch.object(module.base, "profile", return_value={}), \
             mock.patch.object(module.base, "source_inputs", return_value={}), \
             mock.patch.object(module, "require_capabilities"), mock.patch.object(module, "validate_release", return_value=({}, "d")), \
             mock.patch.object(module.base, "ancestors"), mock.patch.object(module, "check_review"), \
             mock.patch.object(module.base, "receipt", side_effect=receipt), \
             mock.patch.object(module, "execute_row", side_effect=row), contextlib.redirect_stdout(io.StringIO()):
            code = module.main()
        return code, calls, writes, failed
    def test_old_scheduler_failure_reproduced_and_new_main_blocks_later_rows(self):
        old = load_v2("run")
        _, old_calls, _, _ = self.main_model(old)
        self.assertEqual(old_calls, ["R14", "R18"])
        code, calls, writes, failed = self.main_model(candidate)
        self.assertEqual(code, 1)
        self.assertEqual(calls, ["R14"])
        self.assertEqual(writes["/model/output/R14.json"], failed)
        for case in ("R15", "R16", "R17", "R18"):
            row = writes["/model/output/" + case + ".json"]
            self.assertEqual(row["status"], "unavailable")
            self.assertTrue(row["cleanup"]["unrun"])
            self.assertEqual(row["cleanup"]["launcherStarts"], 0)
    def test_missing_validated_cleanup_blocks_even_if_complete_claimed(self):
        _, calls, _, _ = self.main_model(candidate, completed=True, validated=False)
        self.assertEqual(calls, ["R14"])
    def test_failed_row_with_complete_validated_cleanup_may_continue(self):
        _, calls, writes, failed = self.main_model(candidate, completed=True, validated=True)
        self.assertEqual(calls, ["R14", "R18"])
        self.assertEqual(writes["/model/output/R14.json"], failed)
    def test_later_unknown_error_never_replaces_prior_actual_failed_row(self):
        _, calls, writes, failed = self.main_model(candidate, completed=True, validated=True, explode=True)
        self.assertEqual(calls, ["R14", "R18"])
        self.assertEqual(writes["/model/output/R14.json"], failed)
        self.assertFalse(writes["/model/output/R18.json"]["cleanup"]["complete"])
    def test_phase_and_fault_admission_preserve_prior_session_and_latch_closed(self):
        backend = self.backend(); prior = SimpleNamespace(cleaned=False)
        backend.sessions.append(prior); backend.active = prior
        with mock.patch.object(linux_backend, "Session", side_effect=AssertionError("no next session")):
            self.reject(lambda: backend.phase("idle", object()))
            self.reject(lambda: backend.lifecycle(life.Stage.PROFILE_VALIDATED, lambda _: None, object()))
            backend.sessions[0] = self.cleaned()
            self.reject(lambda: backend.phase("idle", object()))
        self.assertIs(backend.active, prior)
        self.assertTrue(backend.admission_blocked)
    def test_backend_revalidates_holder_proof_and_original_cleanup_deadline(self):
        for kind in ("holder", "deadline", "missing"):
            backend = self.backend(); prior = self.cleaned()
            if kind == "holder": prior.proof["pipeHolders"] = 1
            elif kind == "deadline": prior.observation["termination"]["allResourcesObservedMonotonicNs"] = 2_500_001_001
            else: prior.proof = None
            backend.sessions.append(prior)
            with mock.patch.object(linux_backend, "Session", side_effect=AssertionError("no admission")):
                self.reject(lambda: backend.phase("idle", object()))
    def test_backend_allows_only_proved_previous_disposal(self):
        backend = self.backend(); backend.sessions.append(self.cleaned())
        future = SimpleNamespace(observation={"modelOnly": True}, setup=mock.Mock(), await_armed_or_fault=mock.Mock())
        with mock.patch.object(linux_backend, "Session", return_value=future):
            self.assertEqual(backend.phase("idle", "same-budget"), {"modelOnly": True})
        future.setup.assert_called_once_with("same-budget")
        self.assertEqual(len(backend.sessions), 2)
    def test_failed_cleanup_latches_admission_even_if_independent_retry_disposes(self):
        backend = self.backend(); previous = self.cleaned()
        previous.cleanup = mock.Mock(side_effect=life.Unavailable())
        backend.sessions.append(previous); backend.active = previous
        self.reject(lambda: backend.cleanup("same-budget"))
        previous.cleanup.side_effect = None; previous.cleanup.return_value = previous.proof
        self.assertEqual(backend.cleanup("same-budget"), previous.proof)
        self.assertFalse(backend.cleanup_complete())
        with mock.patch.object(linux_backend, "Session", side_effect=AssertionError("must remain blocked")):
            self.reject(lambda: backend.phase("idle", "same-budget"))
            self.reject(lambda: backend.lifecycle(life.Stage.PROFILE_VALIDATED, lambda _: None, "same-budget"))
    def test_old_nonleader_failure_reproduced_and_new_inventory_detects_holder(self):
        old = load_v2("linux_backend")
        leader = Path("/proc/100")
        def directories(path):
            if path == Path("/proc"): return iter([leader])
            if path == leader / "fd": return iter([])
            raise AssertionError("v2 unexpectedly inspects tasks")
        with mock.patch.object(Path, "iterdir", autospec=True, side_effect=directories), \
             mock.patch.object(Path, "stat", return_value=SimpleNamespace(st_ino=9)), \
             mock.patch.object(old.time, "monotonic_ns", return_value=1):
            self.assertEqual(old.holder_counts({777}, set(), 10), inventory.ZERO)
        self.proc.processes["100"]["101"]["net"] = 777
        counts = self.holders()
        self.assertEqual(counts["namespaceHolders"], 1)
        self.reject(lambda: life.validate_cleanup({**proof(), **counts}))
    def test_nonleader_unshared_file_table_pipe_and_socket_holders_detected(self):
        self.proc.processes["100"]["101"]["fds"] = {7: "pipe:[888]", 8: "socket:[999]"}
        counts = self.holders()
        self.assertEqual(counts["pipeHolders"], 1)
        self.assertEqual(counts["socketHolders"], 1)
        self.assertEqual(counts["listenerHolders"], 1)
    def test_nonleader_namespace_descriptor_holder_detected(self):
        self.proc.processes["100"]["101"]["fds"] = {9: "net:[777]"}
        self.assertEqual(self.holders()["namespaceHolders"], 1)
    def test_stable_complete_task_inventory_can_report_zero(self):
        self.assertEqual(self.holders(), inventory.ZERO)
        self.assertIn("/proc/100/task/101/ns", self.proc.visited)
        self.assertIn("/proc/100/task/101/fd", self.proc.visited)
        self.proc.processes.clear()
        self.reject(self.holders)
    def test_inaccessible_nonleader_metadata_cannot_be_zero(self):
        for suffix in ("ns", "fd"):
            self.proc = ProcModel(); self.proc.denied.add("/proc/100/task/101/" + suffix)
            self.reject(self.holders)
    def test_new_task_during_inventory_is_ambiguity_not_zero(self):
        def names(path, count):
            if path == "/proc/100/task" and count == 2:
                self.proc.processes["100"]["102"] = {"net": 777, "fds": {}}
        self.proc.on_names = names
        self.reject(self.holders)
    def test_namespace_or_unshared_fd_table_change_is_rejected(self):
        def namespace(path, name, count):
            if path == "/proc/100/task/101/ns" and name == "net" and count == 2:
                self.proc.processes["100"]["101"]["net"] = 777
        self.proc.on_namespace = namespace
        self.reject(self.holders)
        self.proc = ProcModel()
        def descriptors(path, count):
            if path == "/proc/100/task/101/fd" and count == 2:
                self.proc.processes["100"]["101"]["fds"] = {8: "socket:[999]"}
        self.proc.on_descriptors = descriptors
        self.reject(self.holders)
    def test_identity_replacement_is_rejected(self):
        def changed(path):
            if path == "/proc/100/task/101":
                self.proc.stamps[path] = (1, self.proc.identity(path)[1] + 1, 0)
        self.proc.on_named_stamp = changed
        self.reject(self.holders)
    def test_missing_namespace_of_a_live_task_is_not_treated_as_exit(self):
        def missing(path, name, _):
            if path == "/proc/100/task/101/ns" and name == "net": raise FileNotFoundError()
        self.proc.on_namespace = missing
        self.reject(self.holders)
    def test_explicitly_proved_exited_thread_is_benign_under_same_deadline(self):
        def exited(path, name, _):
            if path == "/proc/100/task/101/ns" and name == "net":
                del self.proc.processes["100"]["101"]
                raise FileNotFoundError()
        self.proc.on_namespace = exited
        self.assertEqual(self.holders(), inventory.ZERO)
    def test_inventory_cannot_reset_or_omit_original_disposal_deadline(self):
        self.reject(lambda: self.holders(deadline=1))
        self.reject(lambda: self.holders(deadline=None))
    def test_between_pass_changes_fail_but_explicit_task_exit_can_be_proved(self):
        def changed(path, name, count):
            if path == "/proc/100/task/101/ns" and name == "net" and count == 3:
                self.proc.processes["100"]["101"]["net"] = 777
        self.proc.on_namespace = changed
        self.reject(self.holders)
        self.proc = ProcModel()
        def exited(path, count):
            if path == "/proc/100/task" and count == 3:
                del self.proc.processes["100"]["101"]
        self.proc.on_names = exited
        self.assertEqual(self.holders(), inventory.ZERO)
    def test_nif_and_role_and_finite_fault_sources_remain_byte_identical(self):
        for name in ("control_nif.c", "fault_helper.c", "role.exs", "signal-authority.json"):
            self.assertEqual((candidate.HERE / name).read_bytes(), (checkpoint.PACKET / "v2" / name).read_bytes())


if __name__ == "__main__": unittest.main(verbosity=2)
