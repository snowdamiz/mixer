"""Closed R14/R18 orchestration and observation validators.

The host model is an executable control test, never a Linux backend. A missing
or incomplete Linux backend must refuse every runtime row. Faults cannot select
a command/path/FD, change a budget, or intercept the independent cleanup path.
"""
from dataclasses import dataclass
from enum import IntEnum
import time

PHASES = ("idle", "h1_body", "h2_reader_frozen", "blocked_response")
ROW_WALL_NS = 120_000_000_000
SUITE_WALL_NS = 900_000_000_000
STOP_GRACE_NS = 2_000_000_000
DISPOSAL_NS = 2_500_000_000
WIRE_MAX_BYTES = 33_554_432


class Stage(IntEnum):
    PROFILE_VALIDATED = 1
    SOURCE_VALIDATED = 2
    CAPABILITIES_VALIDATED = 3
    RELEASE_VALIDATED = 4
    REVIEW_VALIDATED = 5
    SCRATCH_CREATED = 6
    HELPER_COMPILED = 7
    NIF_COMPILED = 8
    CGROUP_CREATED = 9
    CGROUP_CONFIGURED = 10
    CGROUP_READBACK = 11
    CHANNEL_CREATED = 12
    LAUNCHER_ENTERED = 13
    LAUNCHER_LIMITS_SET = 14
    LAUNCHER_CGROUP_JOINED = 15
    LAUNCHER_NAMESPACES_CREATED = 16
    LAUNCHER_MOUNTS_SEALED = 17
    LAUNCHER_REAPER_STARTED = 18
    LAUNCHER_PRIVILEGES_DROPPED = 19
    LAUNCHER_ROLE_EXEC_ENTERED = 20
    ROLE_NIF_SECURED = 21
    ROLE_TRANSPORT_STARTED = 22
    ROLE_PHASE_ARMED = 23
    ROLE_READY_SENT = 24
    FIRST_SAMPLE_COLLECTED = 25
    OUTPUT_COLLECTED = 26
    STOP_REQUESTED = 27
    SIGTERM_OBSERVED_SENT = 28
    CGROUP_KILL_OBSERVED = 29
    EMPTY_OBSERVED = 30
    PIPES_DRAINED = 31
    BEFORE_CGROUP_REMOVAL = 32
    MOUNT_TARGET_REMOVED = 33
    BEFORE_SCRATCH_REMOVAL = 34


@dataclass(frozen=True)
class Boundary:
    stage: Stage
    component: str
    boundary: str
    observation: str
    cleanup: str


# This source-derived table is intentionally separate from runtime selection.
# Controller-side Linux hooks and cross-process reachability still need review.
BOUNDARIES = (
    Boundary(Stage.PROFILE_VALIDATED, "controller", "after exact profile validation", "selected profile and schema hash matched", "no launch or resource"),
    Boundary(Stage.SOURCE_VALIDATED, "controller", "after accepted source checks", "all non-index input hashes matched", "no launch or resource"),
    Boundary(Stage.CAPABILITIES_VALIDATED, "controller", "after read-only Linux capability checks", "genuine cgroup2 and setup capabilities observed", "no launch or resource"),
    Boundary(Stage.RELEASE_VALIDATED, "controller", "after sealed Linux artifact validation", "source/lock/ELF/library/header bindings matched", "no launch or resource"),
    Boundary(Stage.REVIEW_VALIDATED, "controller", "after independent implementation/enum review validation", "review binds this exact harness and enum", "no launch or resource"),
    Boundary(Stage.SCRATCH_CREATED, "controller", "after owned scratch mkdir and identity seal", "inode/owner/marker recorded", "identity-checked scratch removal"),
    Boundary(Stage.HELPER_COMPILED, "controller", "after successful helper compile", "compiler exit and artifact hash recorded", "owned build files and scratch removal"),
    Boundary(Stage.NIF_COMPILED, "controller", "after successful NIF compile", "matching ERTS headers and sealed Linux ELF output identity recorded", "owned build files and scratch removal"),
    Boundary(Stage.CGROUP_CREATED, "controller", "after child mkdir and identity FD open", "empty cgroup inode/owner recorded", "empty owned child removal"),
    Boundary(Stage.CGROUP_CONFIGURED, "controller", "after writing every selected limit before admission", "all writes completed; no contained task", "empty owned child removal"),
    Boundary(Stage.CGROUP_READBACK, "controller", "after exact limit and ancestor readback", "values matched selected profile", "empty owned child removal"),
    Boundary(Stage.CHANNEL_CREATED, "controller", "after owned SEQPACKET pair construction", "two private endpoint identities recorded", "both endpoints and pipes closed"),
    Boundary(Stage.LAUNCHER_ENTERED, "launcher", "at trusted launcher entry before fork or role", "fixed launcher emitted stage13 then exit79", "Popen exit plus no role/listener and owned cgroup cleanup"),
    Boundary(Stage.LAUNCHER_LIMITS_SET, "launcher", "after hard/soft limits before containment", "fixed launcher emitted stage14 then exit79", "Popen exit and no descendants plus owned cgroup cleanup"),
    Boundary(Stage.LAUNCHER_CGROUP_JOINED, "launcher", "after cgroup.procs join before namespace or fork", "fixed launcher emitted stage15 then exit79", "cgroup-wide disposal and zero tasks"),
    Boundary(Stage.LAUNCHER_NAMESPACES_CREATED, "launcher", "after private namespaces and loopback setup", "fixed launcher emitted stage16 then exit79", "zero tasks and no owned namespace holders"),
    Boundary(Stage.LAUNCHER_MOUNTS_SEALED, "launcher", "after private root/proc-target/tmp/harness mount setup", "fixed launcher emitted stage17 then exit79", "namespace disposal; target empty; no host remount"),
    Boundary(Stage.LAUNCHER_REAPER_STARTED, "launcher", "after PID1 proc mount and chroot", "fixed launcher emitted stage18 then exit79", "namespace reaper exit and descendants zero"),
    Boundary(Stage.LAUNCHER_PRIVILEGES_DROPPED, "launcher", "after PID1 ID/capability/no-escalation drop", "fixed launcher emitted stage19 then exit79", "cgroup-wide disposal; no migration"),
    Boundary(Stage.LAUNCHER_ROLE_EXEC_ENTERED, "launcher", "immediately before fixed BEAM exec", "fixed PID2 emitted stage20 then exit79", "role exec absent; namespace/reaper/cgroup empty"),
    Boundary(Stage.ROLE_NIF_SECURED, "role", "after actual NIF security readback before transport", "role emitted stage21 then exit79", "zero role tasks; output/control/namespace cleanup"),
    Boundary(Stage.ROLE_TRANSPORT_STARTED, "role", "after actual private listener info", "role emitted stage22 then exit79", "listener and all role tasks disappear"),
    Boundary(Stage.ROLE_PHASE_ARMED, "role", "after actual selected fixture observation", "phase_armed plus stage23 then exit79", "original owners and peers disposed; no late success"),
    Boundary(Stage.ROLE_READY_SENT, "role", "after ready packet send", "role emitted stage24 then exit79", "no replay acceptance; all private resources disposed"),
    Boundary(Stage.FIRST_SAMPLE_COLLECTED, "controller", "after first role-ready complete counter snapshot", "numeric readback and actual sample time recorded after observed readiness", "whole-cgroup disposal and closed sinks"),
    Boundary(Stage.OUTPUT_COLLECTED, "controller", "after a complete allowed output record", "reconstructed safe schema count increased", "whole-cgroup disposal; no rejected bytes retained"),
    Boundary(Stage.STOP_REQUESTED, "controller", "after exactly one stop packet write", "stop packet count1 and bounded gate-preparation origin recorded", "independent disposal observes gate then keeps first actual TERM deadline"),
    Boundary(Stage.SIGTERM_OBSERVED_SENT, "controller", "after actual signal to the unique identity-bound owned namespace PID2", "pidfd-bound SIGTERM send count1 and first actual TERM clock recorded", "continue original2000ms grace then kill if needed"),
    Boundary(Stage.CGROUP_KILL_OBSERVED, "controller", "after actual cgroup.kill write on a deliberately frozen owned domain", "kill counter1 after original grace", "zero tasks by original2500ms deadline"),
    Boundary(Stage.EMPTY_OBSERVED, "controller", "after actual zero-task/readback observation", "owned cgroup task count zero at original disposal deadline", "socket/namespace/pipe/no-dump proof and owned removal"),
    Boundary(Stage.PIPES_DRAINED, "controller", "after both pipe EOFs and bounded schema audit", "both output EOFs and output overflow checks complete", "descriptor/namespace-holder proof and owned removal"),
    Boundary(Stage.BEFORE_CGROUP_REMOVAL, "controller", "before identity-checked removal of an already-empty child", "identity, emptiness and parent boundary observed", "independent cleanup performs same guarded removal"),
    Boundary(Stage.MOUNT_TARGET_REMOVED, "controller", "after empty private target rmdir", "private target absent after role/reaper exit", "namespace-holder proof and remaining owned scratch removal"),
    Boundary(Stage.BEFORE_SCRATCH_REMOVAL, "controller", "before final identity-checked empty scratch removal", "marker, inode, owner and known file set match", "independent cleanup completes guarded removal"),
)
assert tuple(boundary.stage for boundary in BOUNDARIES) == tuple(Stage)


class Unavailable(Exception):
    """Closed internal refusal; no raw platform error or payload is carried."""


class InjectedFailure(Exception):
    def __init__(self, stage):
        if type(stage) is not Stage:
            raise Unavailable()
        self.stage = stage


def numeric_record(record, fields):
    if type(record) is not dict or set(record) != set(fields):
        raise Unavailable()
    if not all(type(v) is int and 0 <= v <= 2**63 - 1 for v in record.values()):
        raise Unavailable()
    return dict(record)


class Budget:
    def __init__(self, suite_started_ns, row_started_ns, clock=time.monotonic_ns):
        if type(suite_started_ns) is not int or type(row_started_ns) is not int or not 0 <= suite_started_ns <= row_started_ns:
            raise Unavailable()
        self.suite_started_ns, self.row_started_ns, self.clock = suite_started_ns, row_started_ns, clock
        self.deadline = min(suite_started_ns + SUITE_WALL_NS, row_started_ns + ROW_WALL_NS)

    def check(self):
        now = self.clock()
        if type(now) is not int or not self.row_started_ns <= now < self.deadline:
            raise Unavailable()
        return self.deadline - now


ARM_FIELDS = {"phase", "owners", "readerSuspended", "responseBlocked", "queuedMessages",
              "queuedSocketBytes", "wireSentBytes", "roleRelativeNs", "preInitDumpable"}
GATE_FIELDS = {"phase", "gateClosed", "gateClosedNs", "ownersAliveAtGate", "phaseArmedAtGate", "capturesAtGate"}
CALLBACK_FIELDS = {"phase", "completed", "elapsedNs"}
RESULT_FIELDS = {"phase", "gateClosed", "gateClosedNs", "killRequestedNs", "ownersExpected", "ownersDown",
                 "peersExpected", "peersClosed", "capturesBeforeStop", "capturesAfterStop", "captureFailures", "observedStopNs",
                 "ownersAliveAtTerm", "phaseArmedAtTerm", "termObservedCount", "termObservedNs"}
PROOF_FIELDS = {"ownedTasks", "listenerHolders", "socketHolders", "namespaceHolders", "pipeHolders", "dumpFiles",
                "identityMatched", "cgroupRemoved", "mountTargetRemoved", "controlClosed", "rowScratchRemoved"}


def validate_cleanup(proof):
    p = numeric_record(proof, PROOF_FIELDS)
    for key in ("ownedTasks", "listenerHolders", "socketHolders", "namespaceHolders", "pipeHolders", "dumpFiles"):
        if p[key] != 0:
            raise Unavailable()
    for key in ("identityMatched", "cgroupRemoved", "mountTargetRemoved", "controlClosed", "rowScratchRemoved"):
        if p[key] != 1:
            raise Unavailable()
    return p


def validate_phase(phase, arm, gate, callback, stopped, termination, proof):
    if phase not in PHASES:
        raise Unavailable()
    a = numeric_record(arm, ARM_FIELDS)
    g = numeric_record(gate, GATE_FIELDS)
    c = numeric_record(callback, CALLBACK_FIELDS)
    r = numeric_record(stopped, RESULT_FIELDS)
    t = numeric_record(termination, {"stopStartedMonotonicNs", "emptyObservedMonotonicNs", "termSentMonotonicNs", "termSentCount",
                                     "killUsed", "killSentMonotonicNs", "allResourcesObservedMonotonicNs"})
    number = PHASES.index(phase) + 1
    expected_owners = 0 if phase == "idle" else 1
    if (a["phase"] != number or g["phase"] != number or c["phase"] != number or r["phase"] != number
            or a["owners"] != expected_owners or c["completed"] != 1 or c["elapsedNs"] > 1_000_000_000):
        raise Unavailable()
    if a["preInitDumpable"] not in (0, 1) or a["wireSentBytes"] > WIRE_MAX_BYTES:
        raise Unavailable()
    if a["readerSuspended"] != int(phase == "h2_reader_frozen") or a["responseBlocked"] != int(phase == "blocked_response"):
        raise Unavailable()
    if phase == "h2_reader_frozen" and a["queuedMessages"] == 0:
        raise Unavailable()
    if phase == "blocked_response" and a["queuedSocketBytes"] == 0:
        raise Unavailable()
    if ((phase != "h2_reader_frozen" and a["queuedMessages"] != 0)
            or (phase != "blocked_response" and a["queuedSocketBytes"] != 0)):
        raise Unavailable()
    if r["ownersExpected"] != expected_owners or r["ownersDown"] != expected_owners:
        raise Unavailable()
    if (g["gateClosed"] != 1 or g["ownersAliveAtGate"] != expected_owners or g["phaseArmedAtGate"] != 1
            or r["ownersAliveAtTerm"] != expected_owners or r["phaseArmedAtTerm"] != 1
            or r["termObservedCount"] != 1):
        raise Unavailable()
    if r["peersExpected"] != expected_owners or r["peersClosed"] != expected_owners or r["gateClosed"] != 1:
        raise Unavailable()
    if (g["gateClosedNs"] != r["gateClosedNs"]
            or not a["roleRelativeNs"] <= g["gateClosedNs"] <= r["termObservedNs"] <= r["killRequestedNs"] <= r["observedStopNs"]):
        raise Unavailable()
    captures = 1 if phase == "blocked_response" else 0
    if (g["capturesAtGate"] != captures or r["capturesBeforeStop"] != captures
            or r["capturesAfterStop"] != captures or r["captureFailures"] != 0):
        raise Unavailable()
    if not t["stopStartedMonotonicNs"] <= t["emptyObservedMonotonicNs"] <= t["stopStartedMonotonicNs"] + DISPOSAL_NS:
        raise Unavailable()
    if not t["emptyObservedMonotonicNs"] <= t["allResourcesObservedMonotonicNs"] <= t["stopStartedMonotonicNs"] + DISPOSAL_NS:
        raise Unavailable()
    if (t["termSentCount"] != 1 or t["stopStartedMonotonicNs"] != t["termSentMonotonicNs"]
            or not 0 < t["termSentMonotonicNs"] <= t["emptyObservedMonotonicNs"]):
        raise Unavailable()
    if t["killUsed"] not in (0, 1):
        raise Unavailable()
    if t["killUsed"] == 0 and t["killSentMonotonicNs"] != 0:
        raise Unavailable()
    if t["killUsed"] and not t["stopStartedMonotonicNs"] + STOP_GRACE_NS <= t["killSentMonotonicNs"] <= t["emptyObservedMonotonicNs"]:
        raise Unavailable()
    validate_cleanup(proof)
    return {"phase": number, "observed": 1, "ownersDown": r["ownersDown"], "peersClosed": r["peersClosed"]}


def run_r14(backend, budget):
    """Four serial observed phases. Backend receives the SAME budget object."""
    rows = []
    for phase in PHASES:
        budget.check()
        try:
            observation = backend.phase(phase, budget)
        finally:
            # This is deliberately outside any fault-injection selector.
            proof = backend.cleanup(budget)
        budget.check()
        rows.append(validate_phase(phase, observation["arm"], observation["gate"], observation["callback"],
                                   observation["stopped"], observation["termination"], proof))
    return rows


def run_r18(backend, budget):
    """Each source-derived boundary must be reached, faulted, and disposed.

    This routine cannot establish Linux evidence from a model backend. Callers
    retain backend kind and evidence scope, and forbid runtime pass without the
    independently selected complete Linux backend and enum review.
    """
    rows = []
    for selected in Stage:
        budget.check()
        reached = []
        injected = False
        def observe(stage):
            nonlocal injected
            budget.check()
            if type(stage) is not Stage or stage in reached or (reached and stage <= reached[-1]):
                raise Unavailable()
            reached.append(stage)
            if stage == selected:
                injected = True
                raise InjectedFailure(stage)
        try:
            backend.lifecycle(selected, observe, budget)
        except InjectedFailure as failure:
            if failure.stage != selected:
                raise Unavailable() from None
        finally:
            # No selector, callable, stage name or injected exception is passed
            # to this independent disposal method.
            proof = backend.cleanup(budget)
        budget.check()
        validate_cleanup(proof)
        if not injected or not reached or reached[-1] != selected:
            raise Unavailable()
        rows.append({"stage": int(selected), "reached": 1, "injected": 1, "cleanupObserved": 1})
    return rows
