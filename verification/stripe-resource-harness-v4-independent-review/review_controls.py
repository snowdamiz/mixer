#!/usr/bin/env python3
"""Independent v4 controls using actual adapters/sessions and mocked OS calls."""
import importlib.util
import json
from pathlib import Path
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
V4 = ROOT / "verification/stripe-webhook-linux-resource-harness/v4"
sys.dont_write_bytecode = True
sys.path.insert(0, str(V4))
import lifecycle as life
import linux_backend as backend
import proc_inventory as proc
import run as candidate


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Reuse the already reviewed independent finite syscall fixture, preserving its
# sealed source. Imported control functions have no main/authority side effects.
fixtures = load("v3_independent_fixture", ROOT / "verification/stripe-resource-harness-v3-independent-review/review_controls.py")
sys.path.insert(0, str(V4))
old_proc = load("v3_inventory_read_only", V4.parent / "v3/proc_inventory.py")
old_backend = load("v3_backend_read_only", V4.parent / "v3/linux_backend.py")


def refuses(action):
    try:
        action()
    except life.Unavailable as error:
        return error
    raise AssertionError("Expected closed refusal")


def session(module=backend):
    owner = module.LinuxBackend(Path("/model/parent"), Path("/model/release"), {}, "model", {})
    active = module.Session(owner, "idle")
    owner.active = active
    owner.sessions.append(active)
    active.disposal_steps = mock.Mock()
    active.stop_started = active.term_at = 1000
    active.term_count = 1
    active.empty_at = 1100
    return owner, active


def child_reference_repair():
    old = fixtures.FakeProcOS()
    old.child_pid = 777
    with old.patched():
        old_counts = old_proc.holder_counts({777}, set(), 10)
    assert old_counts == proc.ZERO
    new = fixtures.FakeProcOS()
    new.child_pid = 777
    with new.patched():
        new_counts = proc.holder_counts({777}, set(), 10, pid_namespace_ids={777})
    assert new_counts["namespaceHolders"] == 1
    refuses(lambda: life.validate_cleanup(fixtures.proof(new_counts)))
    missing = fixtures.FakeProcOS()
    missing.denied.add("/proc/100/task/101/ns/pid_for_children")
    with missing.patched():
        refuses(lambda: proc.holder_counts({777}, set(), 10, pid_namespace_ids={777}))
    return {"name": "old-child-reference-defect-reproduced-and-v4-detects-or-refuses", "passed": True,
            "v3FinalCounts": old_counts, "v4FinalCounts": dict(new_counts), "unreadableChildLinkRefused": True}


def immutable_retry_repair():
    old_owner, old = session(old_backend)
    positive = dict(proc.ZERO, namespaceHolders=1)
    with mock.patch.object(old_backend, "holder_counts", side_effect=[positive, dict(proc.ZERO)]), \
         mock.patch.object(old_backend.time, "monotonic_ns", return_value=1200):
        refuses(lambda: old_owner.cleanup(object()))
        old_owner.cleanup(object())
    assert old.last_counts["namespaceHolders"] == 0
    owner, active = session()
    with mock.patch.object(backend, "holder_counts", side_effect=[positive, dict(proc.ZERO)]), \
         mock.patch.object(backend.time, "monotonic_ns", return_value=1200):
        refuses(lambda: owner.cleanup(object()))
        first = active.cleanup_attempts[0]
        owner.cleanup(object())
        owner.cleanup(object())
    records = owner.cleanup_attempt_records()
    assert [r["observedCounts"]["namespaceHolders"] if r["observedCounts"] is not None else None for r in records] == [1, 0, None]
    assert active.cleanup_attempts[0] == first and active.last_counts["namespaceHolders"] == 1
    records[0]["observedCounts"]["namespaceHolders"] = 99
    assert owner.cleanup_attempt_records()[0]["observedCounts"]["namespaceHolders"] == 1
    assert active.cleaned and active.failed and owner.admission_blocked and not owner.cleanup_complete()
    with mock.patch.object(backend, "Session", side_effect=AssertionError("No later session")):
        refuses(lambda: owner.phase("idle", object()))
        refuses(lambda: owner.lifecycle(life.Stage.PROFILE_VALIDATED, lambda _: None, object()))
    return {"name": "old-lost-retry-evidence-reproduced-and-v4-records-sticky-detached-attempts", "passed": True,
            "v3LastCountsAfterRetry": old.last_counts, "v4FirstCounts": active.last_counts,
            "v4AttemptOutcomes": [r["outcome"] for r in owner.cleanup_attempt_records()],
            "v4FirstFailure": active.first_cleanup_failure_reason, "admissionBlockedAfterPhysicalSuccess": True}


class PartialDescriptorFixture(fixtures.FakeProcOS):
    def __init__(self, exit_task=False):
        super().__init__()
        self.fds = {7: "socket:[999]", 8: "pipe:[888]"}
        self.successfully_read = []
        self.exit_task = exit_task

    def readlink(self, name, *, dir_fd=None):
        if name == "8":
            if self.exit_task:
                self.tids = ("100",)
                raise FileNotFoundError()
            raise PermissionError()
        value = super().readlink(name, dir_fd=dir_fd)
        self.successfully_read.append(proc.descriptor_value(value))
        return value


def partial_descriptor_error():
    model = PartialDescriptorFixture()
    owner, active = session()
    active.namespace_ids = {777}
    active.descriptor_inodes = {888, 999}
    active.role_pid_namespace = 777
    # Keep the real Session->holder_counts->Inventory->ProcMetadata chain. Only
    # OS calls and the independent destructive disposal method are mocked.
    with model.patched():
        active.stop_started = active.term_at = active.empty_at = 1
        refuses(lambda: owner.cleanup(object()))
    records = owner.cleanup_attempt_records()
    assert model.successfully_read == [("socket", 999)]
    assert records[0]["countsStatus"] == "partial"
    assert records[0]["observedCounts"]["socketHolders"] == 0
    assert records[0]["observedReferenceCounts"]["socketHolders"] == 0
    first = active.cleanup_attempts[0]
    with mock.patch.object(backend, "holder_counts", return_value=dict(proc.ZERO)), \
         mock.patch.object(backend.time, "monotonic_ns", return_value=2):
        owner.cleanup(object())
    assert active.cleanup_attempts[0] == first and owner.admission_blocked
    return {"name": "successful-owned-FD-read-lost-before-later-readlink-permission-error", "passed": True,
            "finding": "V4-F1", "successfullyReadOwnedReferences": model.successfully_read,
            "firstAttempt": records[0], "laterAttempt": owner.cleanup_attempt_records()[1],
            "scope": "actual Session->Inventory->ProcMetadata with low-level OS calls mocked"}


def partial_descriptor_exit():
    model = PartialDescriptorFixture(exit_task=True)
    with model.patched():
        counts = proc.holder_counts({777}, {888, 999}, 10, pid_namespace_ids={777})
    assert model.successfully_read == [("socket", 999)]
    assert counts == proc.ZERO and dict(counts.observed_counts)["socketHolders"] == 0
    return {"name": "successful-owned-FD-read-lost-before-proved-thread-exit", "passed": True,
            "finding": "V4-F1", "successfullyReadOwnedReferences": model.successfully_read,
            "finalCounts": dict(counts), "retainedObservedReferenceCounts": dict(counts.observed_counts),
            "explicitExitProved": True, "scope": "actual Inventory/ProcMetadata with low-level OS calls mocked"}


if __name__ == "__main__":
    results = [child_reference_repair(), immutable_retry_repair(), partial_descriptor_error(), partial_descriptor_exit()]
    print(json.dumps({"schema": 1, "status": "four-independent-host-controls-complete-one-remaining-partial-evidence-defect",
                      "controlsRun": len(results), "controlsPassed": sum(r["passed"] for r in results), "results": results,
                      "runtimeRowsExecuted": 0, "compilerRun": False, "liveProcQueried": False,
                      "LinuxEnforcementVerified": False}, indent=2, sort_keys=True))
