#!/usr/bin/env python3
"""Independent v3 host controls: mock OS APIs, never inspect live /proc.

The finite fake filesystem exercises the actual ProcMetadata adapter, rather
than replacing that adapter with the producer's ProcModel.
"""
import contextlib
import json
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / "verification/stripe-webhook-linux-resource-harness/v3"
sys.dont_write_bytecode = True
sys.path.insert(0, str(V3))
import lifecycle as life
import linux_backend as backend
import proc_inventory as proc
import run as candidate


def proof(counts=None):
    value = dict.fromkeys(life.PROOF_FIELDS, 0)
    value.update(identityMatched=1, cgroupRemoved=1, mountTargetRemoved=1, controlClosed=1, rowScratchRemoved=1)
    value.update(counts or {})
    return value


def refuses(callback):
    try:
        callback()
    except life.Unavailable:
        return
    raise AssertionError("Expected closed refusal")


class FakeProcOS:
    """Synthetic directory/namespace/link API with finite paths and fake FDs."""
    def __init__(self):
        self.tids = ("100", "101")
        self.handles, self.visited, self.identities = {}, [], {}
        self.next_fd = 50
        self.net = self.child_pid = 9
        self.fds = {}
        self.denied = set()
        self.namespace_calls = {}
        self.namespace_change = False

    def directory(self, path):
        base = {"/proc", "/proc/100", "/proc/100/task"}
        for tid in self.tids:
            task = "/proc/100/task/" + tid
            base.update((task, task + "/ns", task + "/fd"))
        return path in base

    def path(self, name, parent=None):
        return name if parent is None else self.handles[parent] + "/" + name

    def open(self, name, flags, *, dir_fd=None):
        path = self.path(name, dir_fd)
        self.visited.append(["open", path])
        assert flags & proc.os.O_NOFOLLOW and flags & proc.os.O_DIRECTORY
        if path in self.denied:
            raise PermissionError()
        if not self.directory(path):
            raise FileNotFoundError()
        handle = self.next_fd
        self.next_fd += 1
        self.handles[handle] = path
        return handle

    def close(self, handle):
        del self.handles[handle]

    def directory_stat(self, path):
        if path not in self.identities:
            self.identities[path] = len(self.identities) + 100
        return SimpleNamespace(st_mode=stat.S_IFDIR | 0o555, st_dev=1,
                               st_ino=self.identities[path], st_uid=0)

    def fstat(self, handle):
        return self.directory_stat(self.handles[handle])

    def stat(self, name, *, dir_fd=None, follow_symlinks=True):
        path = self.path(name, dir_fd)
        self.visited.append(["stat", path, follow_symlinks])
        if path in self.denied:
            raise PermissionError()
        if self.directory(path):
            return self.directory_stat(path)
        if "/ns/" not in path:
            raise FileNotFoundError()
        kind = path.rsplit("/", 1)[1]
        assert follow_symlinks
        self.namespace_calls[path] = self.namespace_calls.get(path, 0) + 1
        inode = 9
        if path.startswith("/proc/100/task/101/"):
            if kind == "net":
                inode = self.net
                if self.namespace_change and self.namespace_calls[path] >= 2:
                    inode = 777
            elif kind == "pid_for_children":
                inode = self.child_pid
        return SimpleNamespace(st_ino=inode)

    @contextlib.contextmanager
    def scandir(self, handle):
        path = self.handles[handle]
        self.visited.append(["scandir", path])
        if path in self.denied:
            raise PermissionError()
        if path == "/proc":
            names = ("100",)
        elif path == "/proc/100/task":
            names = self.tids
        elif path.endswith("/fd"):
            names = tuple(str(n) for n in self.fds) if "/101/" in path else ()
        else:
            raise AssertionError("Unexpected scandir outside finite metadata scope")
        yield iter(SimpleNamespace(name=name) for name in names)

    def readlink(self, name, *, dir_fd=None):
        path = self.path(name, dir_fd)
        self.visited.append(["readlink", path])
        assert path.startswith("/proc/100/task/101/fd/")
        return self.fds[int(name)]

    @contextlib.contextmanager
    def patched(self):
        with mock.patch.object(proc.os, "open", side_effect=self.open), \
             mock.patch.object(proc.os, "close", side_effect=self.close), \
             mock.patch.object(proc.os, "fstat", side_effect=self.fstat), \
             mock.patch.object(proc.os, "stat", side_effect=self.stat), \
             mock.patch.object(proc.os, "scandir", side_effect=self.scandir), \
             mock.patch.object(proc.os, "readlink", side_effect=self.readlink), \
             mock.patch.object(proc.time, "monotonic_ns", return_value=1):
            try:
                yield
            finally:
                assert self.handles == {}, "Inventory leaked a modeled handle"


def adapter_control(label, configure, expected=None, should_refuse=False):
    model = FakeProcOS()
    configure(model)
    with model.patched():
        if should_refuse:
            refuses(lambda: proc.holder_counts({777}, {888, 999}, 10))
            counts = None
        else:
            counts = proc.holder_counts({777}, {888, 999}, 10)
            assert counts == expected
    return {"name": label, "passed": True, "counts": counts,
            "adapter": "actual ProcMetadata with mocked os.open/stat/fstat/scandir/readlink/close",
            "liveProcQueried": False}


def scheduler_barrier():
    actual_failure = {"caseId": "R14", "status": "failed", "reason": "cleanup",
                      "observedFailure": {"retained": 123}, "cleanup": {"complete": False, "validated": False}}
    called, rows = [], []
    def execute(case, *_):
        called.append(case)
        assert case == "R14"
        return actual_failure
    with mock.patch.object(candidate, "execute_row", side_effect=execute):
        after = candidate.schedule_rows(rows, object(), {}, {}, "digest", 1)
    assert after == "R14" and called == ["R14"]
    assert next(row for row in rows if row["caseId"] == "R14") is actual_failure
    assert all(row["cleanup"]["launcherStarts"] == 0 and row["cleanup"]["unrun"]
               for row in rows if row["caseId"] in ("R15", "R16", "R17", "R18"))
    return {"name": "suite-barrier-preserves-failed-row-and-suppresses-R18", "passed": True,
            "executeRowCalls": called, "blockedAfterCase": after}


def retry_latch_and_evidence_loss():
    owner = backend.LinuxBackend(Path("/model/parent"), Path("/model/release"), {}, "model", {})
    session = backend.Session(owner, "idle")
    owner.active = session
    owner.sessions.append(session)
    session.disposal_steps = mock.Mock()
    session.stop_started = session.term_at = 1000
    session.term_count = 1
    session.empty_at = 1100
    failed_counts = dict(proc.ZERO, namespaceHolders=1)
    with mock.patch.object(backend, "holder_counts", side_effect=[failed_counts, dict(proc.ZERO)]), \
         mock.patch.object(backend.time, "monotonic_ns", return_value=1200):
        refuses(lambda: owner.cleanup(object()))
        first = dict(session.last_counts)
        assert first["namespaceHolders"] == 1 and owner.admission_blocked
        owner.cleanup(object())
    assert session.last_counts["namespaceHolders"] == 0
    assert session.cleaned and not session.failed and session.error_reason == "completed"
    assert len(owner.history) == 1 and owner.history[0]["cleanup"]["namespaceHolders"] == 0
    assert not owner.cleanup_complete()
    with mock.patch.object(backend, "Session", side_effect=AssertionError("No next session permitted")):
        refuses(lambda: owner.phase("idle", object()))
        refuses(lambda: owner.lifecycle(life.Stage.PROFILE_VALIDATED, lambda _: None, object()))
    return {"name": "retry-latch-blocks-new-session-but-overwrites-failed-holder-evidence", "passed": True,
            "finding": "V3-F2", "admissionStillBlocked": owner.admission_blocked,
            "firstCounts": first, "afterRetryLastCounts": session.last_counts,
            "sessionFailedAfterRetry": session.failed, "errorReasonAfterRetry": session.error_reason,
            "retainedHistoryCleanupCounts": [row["cleanup"]["namespaceHolders"] for row in owner.history],
            "scope": "actual Session/LinuxBackend cleanup with disposal and holder counts mocked"}


def missing_pid_for_children():
    model = FakeProcOS()
    model.child_pid = 777
    with model.patched():
        counts = proc.holder_counts({777}, set(), 10)
    assert counts == proc.ZERO
    assert not any("pid_for_children" in str(entry) for entry in model.visited)
    life.validate_cleanup(proof(counts))
    return {"name": "owned-pid-namespace-pinned-only-by-pid-for-children-is-missed", "passed": True,
            "finding": "V3-F1", "modeledHoldingTid": 101, "ownedPidNamespaceInode": 777,
            "actualQueriedNamespaceNames": list(proc.NS_NAMES), "pidForChildrenQueried": False,
            "reported": counts, "numericCleanupValidatorAccepted": True,
            "apiBasis": "namespaces(7) Namespace lifetime and pid_namespaces(7) setns/unshare semantics",
            "liveProcQueried": False}


if __name__ == "__main__":
    results = [scheduler_barrier(),
        adapter_control("complete-stable-per-TID-zero", lambda _: None, dict(proc.ZERO)),
        adapter_control("nonleader-netns-detected", lambda model: setattr(model, "net", 777), dict(proc.ZERO, namespaceHolders=1)),
        adapter_control("unshared-nonleader-pipe-socket-namespace-FDs-detected",
                        lambda model: setattr(model, "fds", {7: "pipe:[888]", 8: "socket:[999]", 9: "net:[777]"}),
                        dict(namespaceHolders=1, pipeHolders=1, socketHolders=1, listenerHolders=1)),
        adapter_control("nonleader-permission-fails-closed", lambda model: model.denied.add("/proc/100/task/101/fd"), should_refuse=True),
        adapter_control("changed-namespace-fails-closed", lambda model: setattr(model, "namespace_change", True), should_refuse=True),
        retry_latch_and_evidence_loss(), missing_pid_for_children()]
    print(json.dumps({"schema": 1, "status": "eight-host-controls-complete-two-v3-defects-reproduced",
                      "controlsRun": len(results), "controlsPassed": sum(row["passed"] for row in results),
                      "results": results, "runtimeRowsExecuted": 0, "compilerRun": False,
                      "actualProcMetadataAdapterExercised": True, "LinuxEnforcementVerified": False}, indent=2, sort_keys=True))
