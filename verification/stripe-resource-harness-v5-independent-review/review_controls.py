#!/usr/bin/env python3
"""Focused actual-adapter/Session controls; all OS authority is mocked."""
import contextlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
V5 = ROOT / "verification/stripe-webhook-linux-resource-harness/v5"
sys.dont_write_bytecode = True
sys.path.insert(0, str(V5))
import lifecycle as life
import linux_backend as backend
import proc_inventory as proc


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixtures = load("v3_independent_syscall_fixture", ROOT / "verification/stripe-resource-harness-v3-independent-review/review_controls.py")
sys.path.insert(0, str(V5))
old = load("v4_inventory_for_comparison", V5.parent / "v4/proc_inventory.py")


def refuses(action):
    try:
        action()
    except life.Unavailable as error:
        return error
    raise AssertionError("Expected closed refusal")


class StreamFixture(fixtures.FakeProcOS):
    def __init__(self, action):
        super().__init__()
        self.action = action
        self.fds = {7: "socket:[999]", 8: "pipe:[888]"}
        self.now, self.scanners = 1, 0
        self.reads = []

    def readlink(self, name, *, dir_fd=None):
        self.reads.append(name)
        if name == "8":
            if self.action == "permission":
                raise PermissionError("SYNTHETIC_PRIVATE_ERROR")
            if self.action == "exit":
                self.tids = ("100",)
                raise FileNotFoundError("SYNTHETIC_PRIVATE_ERROR")
            if self.action == "malformed":
                return "socket:[bogus]"
        result = super().readlink(name, dir_fd=dir_fd)
        if name == "7" and self.action == "deadline":
            self.now = 10
        return result

    @contextlib.contextmanager
    def scandir(self, handle):
        self.scanners += 1
        try:
            with super().scandir(handle) as entries:
                if self.handles[handle].endswith("/101/fd") and self.action == "duplicate":
                    yield iter([SimpleNamespace(name="7"), SimpleNamespace(name="7")])
                elif self.handles[handle].endswith("/101/fd") and self.action == "iterator_error":
                    def failing_entries():
                        yield SimpleNamespace(name="7")
                        raise OSError("SYNTHETIC_PRIVATE_ERROR")
                    yield failing_entries()
                else:
                    yield entries
        finally:
            self.scanners -= 1

    @contextlib.contextmanager
    def patched(self):
        with super().patched(), mock.patch.object(proc.time, "monotonic_ns", side_effect=lambda: self.now):
            try:
                yield
            finally:
                assert self.scanners == 0


def inventory(model, module=proc):
    with model.patched():
        return module.holder_counts({777}, {888, 999}, 10, pid_namespace_ids={777})


def session():
    owner = backend.LinuxBackend(Path("/model/parent"), Path("/model/release"), {}, "model", {})
    active = backend.Session(owner, "idle")
    owner.active = active
    owner.sessions.append(active)
    active.disposal_steps = mock.Mock()
    active.stop_started = active.term_at = active.empty_at = 1
    active.term_count = 1
    active.namespace_ids, active.role_pid_namespace, active.descriptor_inodes = {777}, 777, {888, 999}
    return owner, active


def permission_comparison():
    prior = refuses(lambda: inventory(StreamFixture("permission"), old))
    current = refuses(lambda: inventory(StreamFixture("permission")))
    prior_counts, current_counts = dict(prior.observed_counts), dict(current.observed_counts)
    assert prior_counts["socketHolders"] == 0 and current_counts["socketHolders"] == 1
    return {"name": "old-loss-reproduced-current-immediate-yield-retained", "passed": True,
            "v4PartialCounts": prior_counts, "v5PartialCounts": current_counts}


def session_retry_and_detached_views():
    owner, active = session()
    with StreamFixture("permission").patched():
        refuses(lambda: owner.cleanup(object()))
    frozen = active.cleanup_attempts[0]
    first = owner.cleanup_attempt_records()[0]
    assert first["countsStatus"] == "partial" and first["observedCounts"]["socketHolders"] == 1
    assert first["observedReferenceCounts"]["socketHolders"] == 1
    with mock.patch.object(backend, "holder_counts", return_value=proc.HolderCounts(proc.ZERO, proc.ZERO)), \
         mock.patch.object(backend.time, "monotonic_ns", return_value=2):
        owner.cleanup(object())
        owner.cleanup(object())
    assert active.cleanup_attempts[0] == frozen
    records = owner.cleanup_attempt_records()
    assert [r["outcome"] for r in records] == ["failed", "disposed", "already_disposed"]
    assert records[1]["observedCounts"] == proc.ZERO and records[2]["observedCounts"] is None
    assert len({r["deadlineMonotonicNs"] for r in records}) == 1
    records[0]["observedCounts"]["socketHolders"] = 0
    records[0]["observedReferenceCounts"]["socketHolders"] = 0
    assert owner.cleanup_attempt_records()[0]["observedReferenceCounts"]["socketHolders"] == 1
    assert active.failed and active.cleaned and owner.admission_blocked and not owner.cleanup_complete()
    with mock.patch.object(backend, "Session", side_effect=AssertionError("Admission must remain closed")):
        refuses(lambda: owner.phase("idle", object()))
        refuses(lambda: owner.lifecycle(life.Stage.PROFILE_VALIDATED, lambda _: None, object()))
    assert "SYNTHETIC_PRIVATE_ERROR" not in b"".join(active.cleanup_attempts).decode()
    return {"name": "actual-session-partial-retry-history-detached-and-admission-sticky", "passed": True,
            "firstPartialSocketCount": 1, "attemptOutcomes": [r["outcome"] for r in records],
            "sameDeadlineAcrossAttempts": True, "physicalCleanupSucceeded": True, "admissionStillBlocked": True}


def malformed_metadata():
    owner, active = session()
    with StreamFixture("malformed").patched():
        refuses(lambda: owner.cleanup(object()))
    record = owner.cleanup_attempt_records()[0]
    assert record["observedReferenceCounts"]["socketHolders"] == 1
    assert record["countsStatus"] == "partial" and not active.cleaned and owner.admission_blocked
    assert "socket:[bogus]" not in active.cleanup_attempts[0].decode()
    return {"name": "later-malformed-metadata-refuses-and-retains-prior-reference", "passed": True, "retainedSocketReferences": 1}


def proved_exit_and_final_zero():
    prior = inventory(StreamFixture("exit"), old)
    owner, active = session()
    with StreamFixture("exit").patched():
        owner.cleanup(object())
    record = owner.cleanup_attempt_records()[0]
    assert prior == proc.ZERO and dict(prior.observed_counts)["socketHolders"] == 0
    assert record["observedCounts"] == proc.ZERO and record["physicalProof"]["socketHolders"] == 0
    assert record["observedReferenceCounts"]["socketHolders"] == 1
    assert record["outcome"] == "disposed" and owner.cleanup_complete() and not active.failed
    return {"name": "proved-exit-final-zero-separated-from-known-historical-reference", "passed": True,
            "v4HistoricalSocketCount": 0, "v5HistoricalSocketCount": 1, "finalPhysicalSocketCount": 0}


def yielded_reference_before_deadline_refusal():
    model = StreamFixture("deadline")
    error = refuses(lambda: inventory(model))
    assert dict(error.observed_counts)["socketHolders"] == 1 and model.reads == ["7"]
    assert model.scanners == 0 and model.handles == {}
    return {"name": "yield-consumed-before-expired-clock-check-and-stream-closed", "passed": True,
            "retainedSocketReferences": 1, "nextDescriptorNotRead": True}


def iterator_error_after_yield():
    model = StreamFixture("iterator_error")
    error = refuses(lambda: inventory(model))
    assert dict(error.observed_counts)["socketHolders"] == 1 and model.reads == ["7"]
    assert model.scanners == 0 and model.handles == {}
    return {"name": "next-iterator-step-error-cannot-erase-prior-yield", "passed": True, "retainedSocketReferences": 1}


def duplicate_consumer_rejection():
    model = StreamFixture("duplicate")
    error = refuses(lambda: inventory(model))
    assert dict(error.observed_counts)["socketHolders"] == 1
    assert model.scanners == 0 and model.handles == {}
    return {"name": "consumer-side-duplicate-refusal-deduplicates-history-and-closes-stream", "passed": True, "retainedSocketReferences": 1}


def child_reference_and_permission_rules():
    child = StreamFixture("ordinary")
    child.child_pid, child.fds = 777, {}
    counts = inventory(child)
    assert counts["namespaceHolders"] == 1
    missing = StreamFixture("ordinary")
    missing.fds = {}
    missing.denied.add("/proc/100/task/101/ns/pid_for_children")
    refuses(lambda: inventory(missing))
    return {"name": "prior-child-PID-reference-detection-and-unreadable-refusal-retained", "passed": True, "namespaceHolders": 1}


if __name__ == "__main__":
    results = [permission_comparison(), session_retry_and_detached_views(), malformed_metadata(), proved_exit_and_final_zero(),
               yielded_reference_before_deadline_refusal(), iterator_error_after_yield(), duplicate_consumer_rejection(), child_reference_and_permission_rules()]
    print(json.dumps({"schema": 1, "status": "eight-independent-host-controls-passed", "controlsRun": len(results),
                      "controlsPassed": sum(r["passed"] for r in results), "results": results,
                      "runtimeRowsExecuted": 0, "compilerRun": False, "liveProcQueried": False,
                      "LinuxEnforcementVerified": False}, indent=2, sort_keys=True))
