"""Private Linux candidate backend; imported host-side without launching anything.

Execution is called only after the v3 outer capability/source/artifact/review
gate. Every operation below is controller selected. No HTTP value reaches it.
"""
import errno
import json
import os
from pathlib import Path
import platform
import selectors
import signal
import socket
import stat
import subprocess
import time
import uuid

import checkpoint
import lifecycle as life

base = checkpoint.load_controller()
HERE = Path(__file__).resolve().parent
NS_FIELDS = {"pidNs", "mountNs", "netNs", "ipcNs", "utsNs"}
NS_NAMES = {"pidNs": "pid", "mountNs": "mnt", "netNs": "net", "ipcNs": "ipc", "utsNs": "uts"}


def compiled_identity(header, actual_sha, expected_sha, machine):
    """Fresh outputs must match the sealed Linux artifact, including ELF ABI.

    This checks content/ABI identity, not independently established build
    provenance or runtime symbol resolution. Those remain review/replay gates.
    """
    if (len(header) != 20 or header[:6] != b"\x7fELF\x02\x01"
            or int.from_bytes(header[18:20], "little") != {"aarch64": 183, "x86_64": 62}.get(machine)
            or actual_sha != expected_sha):
        raise life.Unavailable()


class Audit(base.OutputAudit):
    EVENTS = {**base.OutputAudit.EVENTS, "phase_armed": life.ARM_FIELDS, "phase_gate": life.GATE_FIELDS,
              "term_callback": life.CALLBACK_FIELDS, "phase_result": life.RESULT_FIELDS,
              "lifecycle": {"stage", "reached", "injected"}, "namespace": NS_FIELDS}
    def __init__(self, row_totals):
        super().__init__()
        self.cursor = 0
        self.row_totals = row_totals
    def feed(self, stream, raw):
        self.row_totals[stream] += len(raw)
        if self.row_totals[stream] > 1_048_576:
            self.rejected += 1
            self.buffers[stream].clear()
            raise base.Refusal("output_overflow")
        super().feed(stream, raw)
    def fresh(self):
        events = self.events[self.cursor:]
        self.cursor = len(self.events)
        return events


def owned_signal(cgroup, sig):
    """Signal stable pidfds only after membership readback; never a stale PID."""
    sent = 0
    expected = "0::/" + str(cgroup.path.relative_to("/sys/fs/cgroup"))
    for pid in cgroup.pids():
        try:
            fd = os.pidfd_open(pid, 0)
        except ProcessLookupError:
            continue
        try:
            try:
                membership = (Path("/proc") / str(pid) / "cgroup").read_text().splitlines()
            except FileNotFoundError:
                continue
            if expected not in membership:
                raise life.Unavailable()
            try:
                signal.pidfd_send_signal(fd, sig, None, 0)
                sent += 1
            except ProcessLookupError:
                pass
        finally:
            os.close(fd)
    return sent


def role_term(cgroup, pid_namespace):
    """One actual TERM to the unique contained namespace PID2 via stable pidfd.

    Namespace PID2 is fixed by the sealed launcher. Read it again after opening
    the pidfd; no creator SO_PEERCRED or unbound numeric PID substitutes here.
    """
    if type(pid_namespace) is not int or pid_namespace <= 0:
        raise life.Unavailable()
    def identity(pid):
        try:
            proc = Path("/proc") / str(pid)
            values = dict(row.split(":", 1) for row in (proc / "status").read_text().splitlines() if ":" in row)
            ids = [int(n) for n in values["NSpid"].split()]
            uids = [int(n) for n in values["Uid"].split()]
            return (ids, uids, (proc / "ns/pid").stat().st_ino)
        except FileNotFoundError:
            raise
        except (OSError, KeyError, ValueError):
            raise life.Unavailable() from None
    candidates = []
    for pid in cgroup.pids():
        try:
            ids, uids, namespace = identity(pid)
        except FileNotFoundError:
            continue
        if len(ids) >= 2 and ids[0] == pid and ids[-1] == 2 and namespace == pid_namespace and uids == [65534] * 4:
            candidates.append((pid, (ids, uids, namespace)))
    if len(candidates) != 1:
        raise life.Unavailable()
    pid, expected_identity = candidates[0]
    fd = os.pidfd_open(pid, 0)
    try:
        expected_membership = "0::/" + str(cgroup.path.relative_to("/sys/fs/cgroup"))
        if identity(pid) != expected_identity or expected_membership not in (Path("/proc") / str(pid) / "cgroup").read_text().splitlines():
            raise life.Unavailable()
        sent_ns = time.monotonic_ns()
        signal.pidfd_send_signal(fd, signal.SIGTERM, None, 0)
        return 1, sent_ns
    finally:
        os.close(fd)


def holder_counts(namespace_ids, descriptor_inodes, deadline_ns=None, *, pid_namespace_ids=()):
    # Fixed per-task read-only inventory; no leader-only or ambiguity fallback.
    import proc_inventory
    return proc_inventory.holder_counts(namespace_ids, descriptor_inodes, deadline_ns,
                                       pid_namespace_ids=pid_namespace_ids)


class Session:
    def __init__(self, owner, phase, selected=None, observe=None):
        self.owner, self.phase, self.selected = owner, phase, selected
        self.observe = observe or (lambda stage: None)
        self.cg = None
        self.scratch = self.identity = None
        self.mount_target = None
        self.proc = self.channel = self.endpoint = self.child_endpoint = self.selector = None
        self.launch_pidfd = None
        self.audit = Audit(owner.output_totals)
        self.namespace_ids, self.descriptor_inodes = set(), set()
        self.role_pid_namespace = None
        self.arm = self.gate = self.callback = self.stopped = None
        self.observation = {"arm": None, "gate": None, "callback": None, "stopped": None, "termination": None}
        self.preparation_started = 0
        self.stop_started = self.term_at = self.kill_at = self.empty_at = 0
        self.term_count = self.kill_used = 0
        self.sampled = self.output_collected = False
        self.samples, self.boundaries = [], []
        self.next_sample_ns = 0
        self.before, self.after = {}, {}
        self.exit_code = None
        self.failed = False
        self.error_reason = "completed"
        self.cleaned = False
        self.proof = None
        self.last_counts = None
        self.first_counts_status = "unknown"
        self.cleanup_attempts = ()  # canonical bytes; no mutable evidence aliases
        self.session_index = len(getattr(owner, "sessions", ())) + 1
        self.first_cleanup_failure_reason = None
        self.first_cleanup_error_reason = None
        self.injected_seen = False

    def mark(self, stage):
        self.boundaries.append(int(stage))
        self.observe(stage)

    def check_cgroup_identity(self):
        if self.cg is None or self.cg.fd is None or self.cg.pids() or self.cg.path.is_symlink():
            raise life.Unavailable()
        now, descriptor = self.cg.path.stat(), os.fstat(self.cg.fd)
        expected = (self.cg.identity.st_dev, self.cg.identity.st_ino, self.cg.identity.st_uid)
        if (self.cg.path.parent != self.cg.parent
                or (now.st_dev, now.st_ino, now.st_uid) != expected
                or (descriptor.st_dev, descriptor.st_ino, descriptor.st_uid) != expected):
            raise life.Unavailable()

    def setup(self, budget):
        budget.check()
        self.owner.validate_profile(); self.mark(life.Stage.PROFILE_VALIDATED)
        self.owner.validate_sources(); self.mark(life.Stage.SOURCE_VALIDATED)
        self.owner.validate_capabilities(); self.mark(life.Stage.CAPABILITIES_VALIDATED)
        self.owner.validate_release(); self.mark(life.Stage.RELEASE_VALIDATED)
        self.owner.validate_review(); self.mark(life.Stage.REVIEW_VALIDATED)
        self.scratch = HERE / (".owned-scratch-" + uuid.uuid4().hex)
        self.scratch.mkdir(mode=0o700)
        self.identity = self.scratch.stat()
        (self.scratch / "identity.json").write_bytes(base.canonical({"schema": 1, "owner": "mixer-resource-v2",
            "pid": os.getpid(), "harnessDigest": self.owner.harness_digest}))
        self.mark(life.Stage.SCRATCH_CREATED)
        self.compile("fault_helper.c", "fault_helper", [], budget); self.mark(life.Stage.HELPER_COMPILED)
        self.compile("control_nif.c", "control_nif.so", ["-fPIC", "-shared", "-I", str(self.owner.release / "usr/include")], budget)
        self.mark(life.Stage.NIF_COMPILED)
        self.cg = base.Cgroup(self.owner.parent, self.owner.profile, uuid.uuid4().hex)
        # Split exact existing cgroup setup into observable pre-admission stages.
        base.ancestors(self.cg.parent, self.owner.profile)
        for filename in ("cgroup.controllers", "cgroup.subtree_control"):
            base.require({"memory", "cpu", "pids"} <= set((self.cg.parent / filename).read_text().split()), "delegation", True)
        self.cg.path.mkdir(mode=0o700)
        self.cg.fd = os.open(self.cg.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.cg.identity = os.fstat(self.cg.fd)
        base.require(base.read_at(self.cg.fd, "cgroup.procs") == "", "ownership")
        self.mark(life.Stage.CGROUP_CREATED)
        for name, value in self.owner.profile["cgroup"].items():
            if name != "version":
                base.write_at(self.cg.fd, name, value)
        self.mark(life.Stage.CGROUP_CONFIGURED)
        for name, value in self.owner.profile["cgroup"].items():
            if name != "version":
                base.require(base.read_at(self.cg.fd, name) == str(value), "cgroup_readback")
        base.require((self.cg.path / "cgroup.kill").is_file(), "capability_unavailable", True)
        self.before = self.cg.sample()
        self.mark(life.Stage.CGROUP_READBACK)
        self.endpoint, self.child_endpoint = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.namespace_ids = set()
        self.descriptor_inodes.update((os.fstat(self.endpoint.fileno()).st_ino, os.fstat(self.child_endpoint.fileno()).st_ino))
        self.mark(life.Stage.CHANNEL_CREATED)
        generation = uuid.uuid4().hex
        self.channel = base.Control(self.endpoint, generation)
        target = self.selected.name.lower() if self.selected and 13 <= int(self.selected) <= 24 else "none"
        self.mount_target = self.scratch / "mount"
        argv = [str(self.scratch / "fault_helper"), "launch", str(self.cg.path), str(self.owner.release),
                str(self.mount_target), str(self.child_endpoint.fileno()), generation, self.owner.case,
                str(HERE / "role.exs"), str(os.getpid()), str(self.scratch / "control_nif.so"), self.phase, target]
        self.proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=base.FIXED_ENV, close_fds=True, pass_fds=(self.child_endpoint.fileno(),), start_new_session=True)
        self.launch_pidfd = os.pidfd_open(self.proc.pid, 0)
        for pipe in (self.proc.stdout, self.proc.stderr):
            self.descriptor_inodes.add(os.fstat(pipe.fileno()).st_ino)
        self.child_endpoint.close(); self.child_endpoint = None
        self.selector = selectors.DefaultSelector()
        for name, pipe in (("stdout", self.proc.stdout), ("stderr", self.proc.stderr), ("control", self.endpoint)):
            os.set_blocking(pipe.fileno(), False)
            self.selector.register(pipe, selectors.EVENT_READ, name)

    def compile(self, source, output, extra, budget):
        timeout = min(20.0, budget.check() / 1_000_000_000)
        argv = ["/usr/bin/cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", *extra,
                str(HERE / source), "-o", str(self.scratch / output)]
        built = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=base.FIXED_ENV, timeout=timeout)
        self.owner.commands.append({"argv": argv, "exitCode": built.returncode,
            "stdoutBytes": len(built.stdout), "stderrBytes": len(built.stderr),
            "compilerVersion": self.owner.release_manifest["compiler"],
            "compilerExecutableSha256": self.owner.release_manifest["controlNifCompilerSha256"],
            "nifHeadersDigest": base.digest(self.owner.release_manifest["nifHeaders"]),
            "sourceSha256": base.sha(HERE / source),
            "artifactSha256": base.sha(self.scratch / output) if built.returncode == 0 else None})
        if built.returncode or built.stdout or built.stderr:
            raise life.Unavailable()
        artifact = self.scratch / output
        with artifact.open("rb") as stream:
            header = stream.read(20)
        compiled_identity(header, base.sha(artifact),
                          self.owner.release_manifest["files"].get("opt/harness/" + output), platform.machine())
        budget.check()

    def poll(self, timeout=0.01, allow_injection=True):
        if self.selector is None or self.selector.get_map() is None:
            return
        for key, _ in self.selector.select(timeout):
            if key.data == "control":
                if not self.channel.receive():
                    self.selector.unregister(key.fileobj)
            else:
                raw = os.read(key.fd, 65536)
                if not raw:
                    self.selector.unregister(key.fileobj)
                else:
                    self.audit.feed(key.data, raw)
        for event in self.audit.fresh():
            counters = {k: v for k, v in event.items() if k not in ("schema", "event")}
            if event["event"] == "namespace":
                self.namespace_ids.update(v for v in counters.values() if v)
                if counters["pidNs"]:
                    if self.role_pid_namespace is not None:
                        raise life.Unavailable()
                    self.role_pid_namespace = counters["pidNs"]
            elif event["event"] == "phase_armed":
                if self.arm is not None:
                    raise life.Unavailable()
                self.arm = counters
                self.observation["arm"] = counters
            elif event["event"] == "phase_gate":
                if self.gate is not None:
                    raise life.Unavailable()
                self.gate = counters
                self.observation["gate"] = counters
            elif event["event"] == "term_callback":
                if self.callback is not None:
                    raise life.Unavailable()
                self.callback = counters
                self.observation["callback"] = counters
            elif event["event"] == "phase_result":
                if self.stopped is not None:
                    raise life.Unavailable()
                self.stopped = counters
                self.observation["stopped"] = counters
            elif event["event"] == "lifecycle":
                if not (counters["reached"] == 1 and counters["injected"] == 1 and self.selected
                        and counters["stage"] == int(self.selected)):
                    raise life.Unavailable()
                self.injected_seen = True
                if allow_injection:
                    self.mark(self.selected)
        now = time.monotonic_ns()
        if self.cg and self.cg.fd is not None and now >= self.next_sample_ns:
            self.samples.append(self.cg.sample())
            self.next_sample_ns = now + 20_000_000
            for pid in self.cg.pids():
                try:
                    for descriptor in (Path("/proc") / str(pid) / "fd").iterdir():
                        try:
                            value = os.readlink(descriptor)
                        except FileNotFoundError:
                            continue
                        if value.startswith(("socket:[", "pipe:[")) and value.endswith("]"):
                            number = value.split("[", 1)[1][:-1]
                            if number.isdecimal():
                                self.descriptor_inodes.add(int(number))
                except FileNotFoundError:
                    continue

    def await_armed_or_fault(self, budget):
        while True:
            budget.check()
            self.poll()
            if self.selected and 13 <= int(self.selected) <= 24:
                # A positive exit or intended stage never substitutes for the
                # exact numeric reached+injected event emitted at that boundary.
                if self.proc.poll() is not None and not self.injected_seen:
                    self.poll(0)
                    raise life.Unavailable()
                continue
            if self.channel.ready and self.arm is not None:
                if self.arm["phase"] != life.PHASES.index(self.phase) + 1:
                    raise life.Unavailable()
                if not self.cg.pids():
                    raise life.Unavailable()
                self.samples.append(self.cg.sample())
                self.mark(life.Stage.FIRST_SAMPLE_COLLECTED)
                if self.audit.allowed <= 0:
                    raise life.Unavailable()
                self.mark(life.Stage.OUTPUT_COLLECTED)
                return
            if self.proc.poll() is not None:
                self.poll(0)
                raise life.Unavailable()

    def primary_dispose(self, budget):
        self.disposal_steps(inject=True)

    def safe_cleanup_poll(self, timeout):
        try:
            self.poll(timeout, allow_injection=False)
        except base.Refusal as error:
            self.failed = True
            self.error_reason = error.reason
        except (OSError, ValueError, life.Unavailable):
            # An observation failure is retained as failure but cannot interrupt
            # whole-domain termination. No rejected bytes are forwarded.
            self.failed = True
            self.error_reason = "cgroup_readback"

    def live_owned_launch_signal(self, sig):
        # Covers the trusted launcher before its first cgroup join. This stable
        # Popen pidfd cannot target a reused or unrelated PID.
        if self.launch_pidfd is not None:
            try:
                signal.pidfd_send_signal(self.launch_pidfd, sig, None, 0)
            except ProcessLookupError:
                pass

    def disposal_steps(self, inject=False):
        def mark(stage):
            if inject:
                self.mark(stage)
        if self.preparation_started == 0:
            self.preparation_started = time.monotonic_ns()
            if self.channel and not self.channel.stop_sent and not self.channel.closed:
                try:
                    self.channel.send_stop()
                    mark(life.Stage.STOP_REQUESTED)
                except (OSError, base.Refusal):
                    pass
        # stop closes admission only; actual TERM must find the original phase
        # still live. Gate preparation is bounded within the shared row clock.
        admission_until = self.preparation_started + 150_000_000
        while self.channel and not self.gate and not self.channel.closed and time.monotonic_ns() < admission_until:
            self.safe_cleanup_poll(0.002)
        if self.cg and self.cg.fd is not None:
            if self.term_at == 0:
                phase_ready = bool(self.channel and self.channel.ready and self.arm)
                if phase_ready:
                    if self.gate is None:
                        raise life.Unavailable()
                    expected_owners = int(self.phase != "idle")
                    if (self.gate["phase"] != life.PHASES.index(self.phase) + 1 or self.gate["gateClosed"] != 1
                            or self.gate["ownersAliveAtGate"] != expected_owners or self.gate["phaseArmedAtGate"] != 1):
                        raise life.Unavailable()
                    # Source-selected R18 TERM/kill stages require a still-live
                    # frozen domain after the real gate observation.
                    if inject and self.selected in (life.Stage.SIGTERM_OBSERVED_SENT, life.Stage.CGROUP_KILL_OBSERVED):
                        if owned_signal(self.cg, signal.SIGSTOP) == 0:
                            raise life.Unavailable()
                    self.term_count, self.term_at = role_term(self.cg, self.role_pid_namespace)
                else:
                    sent_ns = time.monotonic_ns()
                    self.term_count = owned_signal(self.cg, signal.SIGTERM)
                    if self.term_count:
                        self.term_at = sent_ns
                if self.term_at:
                    self.stop_started = self.term_at
                    mark(life.Stage.SIGTERM_OBSERVED_SENT)
            if not self.stop_started:
                self.stop_started = self.preparation_started
            grace = self.stop_started + life.STOP_GRACE_NS
            deadline = self.stop_started + life.DISPOSAL_NS
            while self.cg.pids() and time.monotonic_ns() < grace:
                self.safe_cleanup_poll(0.005)
                time.sleep(0.005)
            if self.cg.pids() and not self.kill_used:
                base.write_at(self.cg.fd, "cgroup.kill", 1)
                self.kill_used = 1
                self.kill_at = time.monotonic_ns()
                mark(life.Stage.CGROUP_KILL_OBSERVED)
            while self.cg.pids() and time.monotonic_ns() < deadline:
                self.safe_cleanup_poll(0.002)
                time.sleep(0.002)
            if self.cg.pids():
                raise life.Unavailable()
        if self.empty_at == 0:
            self.empty_at = time.monotonic_ns()
        if not self.stop_started:
            self.stop_started = self.preparation_started
        mark(life.Stage.EMPTY_OBSERVED)
        if self.empty_at > self.stop_started + life.DISPOSAL_NS:
            raise life.Unavailable()
        if self.proc is not None:
            self.exit_code = self.proc.wait(timeout=0.5)
            drain_deadline = time.monotonic_ns() + 500_000_000
            while self.selector and self.selector.get_map() and time.monotonic_ns() < drain_deadline:
                self.safe_cleanup_poll(0.005)
            try:
                self.audit.finish()
            except base.Refusal as failure:
                self.failed = True
                self.error_reason = failure.reason
            if self.selector and self.selector.get_map() and any(key.data in ("stdout", "stderr") for key in self.selector.get_map().values()):
                raise life.Unavailable()
        mark(life.Stage.PIPES_DRAINED)
        if self.cg and self.cg.fd is not None:
            self.after = self.cg.sample()
            self.after["processLimits"] = list(self.cg.limit_inventory.values())
            self.check_cgroup_identity()
            mark(life.Stage.BEFORE_CGROUP_REMOVAL)
            self.cg.cleanup()
        if self.mount_target and self.mount_target.exists():
            self.mount_target.rmdir()
        mark(life.Stage.MOUNT_TARGET_REMOVED)
        if self.scratch and self.scratch.exists():
            self.check_scratch_identity()
            mark(life.Stage.BEFORE_SCRATCH_REMOVAL)
            self.remove_scratch()

    def check_scratch_identity(self):
        now = self.scratch.stat()
        if self.scratch.is_symlink() or (now.st_dev, now.st_ino, now.st_uid) != (
                self.identity.st_dev, self.identity.st_ino, self.identity.st_uid):
            raise life.Unavailable()
        expected = {"schema": 1, "owner": "mixer-resource-v2", "pid": os.getpid(), "harnessDigest": self.owner.harness_digest}
        if base.load(self.scratch / "identity.json") != expected:
            raise life.Unavailable()
        if {p.name for p in self.scratch.iterdir()} - {"identity.json", "fault_helper", "control_nif.so"}:
            raise life.Unavailable()
        for path in self.scratch.iterdir():
            if path.is_symlink() or not path.is_file():
                raise life.Unavailable()

    def remove_scratch(self):
        self.check_scratch_identity()
        for path in self.scratch.iterdir():
            path.unlink()
        self.scratch.rmdir()

    def emergency_dispose(self):
        """Bounded, non-injectable cleanup after an observation/action failure.

        Keep the original grace/deadline. Refuse deletion if task emptiness or
        identity remains unknown. These errors never become a passing receipt.
        """
        if not self.stop_started:
            self.stop_started = time.monotonic_ns()
        self.live_owned_launch_signal(signal.SIGTERM)
        if self.cg and self.cg.fd is not None:
            grace = self.stop_started + life.STOP_GRACE_NS
            deadline = self.stop_started + life.DISPOSAL_NS
            while time.monotonic_ns() < grace:
                try:
                    if not self.cg.pids():
                        break
                except (OSError, base.Refusal):
                    pass
                time.sleep(0.005)
            try:
                remaining = bool(self.cg.pids())
            except (OSError, base.Refusal):
                remaining = True
            if remaining:
                base.write_at(self.cg.fd, "cgroup.kill", 1)
                self.live_owned_launch_signal(signal.SIGKILL)
                self.kill_used, self.kill_at = 1, time.monotonic_ns()
            while time.monotonic_ns() < deadline:
                try:
                    if not self.cg.pids():
                        break
                except (OSError, base.Refusal):
                    pass
                time.sleep(0.005)
            if self.cg.pids():
                raise life.Unavailable()
            self.empty_at = time.monotonic_ns()
        if self.proc is not None:
            self.exit_code = self.proc.wait(timeout=0.5)
        if self.cg and self.cg.fd is not None:
            self.check_cgroup_identity()
            self.cg.cleanup()
        if self.mount_target and self.mount_target.exists():
            self.mount_target.rmdir()
        if self.scratch and self.scratch.exists():
            self.remove_scratch()

    def cleanup_attempt_records(self):
        return [json.loads(record) for record in self.cleanup_attempts]

    def note_counts(self, counts, status):
        fields = {"namespaceHolders", "pipeHolders", "socketHolders", "listenerHolders"}
        value = life.numeric_record(dict(counts), fields)
        self._attempt_counts, self._attempt_counts_status = value, status
        self._attempt_holder_at = time.monotonic_ns()
        if self.last_counts is None:
            self.last_counts, self.first_counts_status = dict(value), status

    def retain_cleanup_failure(self, reason):
        self.failed = True
        if self.first_cleanup_failure_reason is None:
            self.first_cleanup_failure_reason = reason
            self.first_cleanup_error_reason = self.error_reason if self.error_reason != "completed" else "cleanup"
        self.error_reason = self.first_cleanup_error_reason
        self.owner.admission_blocked = True

    def cleanup(self, budget):
        started = time.monotonic_ns()
        self._attempt_counts, self._attempt_counts_status = None, "unknown"
        self._attempt_reference_counts = None
        self._attempt_holder_at, self._attempt_stage = None, "disposal"
        cached, outcome, reason = self.cleaned, "failed", None
        try:
            result = self.cleanup_once(budget)
            outcome = "already_disposed" if cached else "disposed"
            if self.failed:
                self.retain_cleanup_failure(self.first_cleanup_failure_reason or self.error_reason)
            return result
        except BaseException as failure:
            partial = getattr(failure, "observed_counts", None)
            if self._attempt_counts is None and partial is not None:
                try:
                    self.note_counts(dict(partial), "partial")
                    self._attempt_reference_counts = dict(self._attempt_counts)
                except (life.Unavailable, TypeError, ValueError):
                    pass  # Unknown stays unknown; never copy arbitrary error data.
            if isinstance(failure, base.Refusal):
                reason = failure.reason
            elif self._attempt_stage == "disposal" and self.error_reason in base.REASONS and self.error_reason != "completed":
                reason = self.error_reason
            elif self._attempt_stage == "holders":
                reason = "inventory_unavailable"
            elif self._attempt_counts and any(self._attempt_counts.values()):
                reason = "holders_present"
            else:
                reason = "cleanup"
            if self.stop_started and time.monotonic_ns() > self.stop_started + life.DISPOSAL_NS:
                reason = "deadline"
            self.retain_cleanup_failure(reason)
            if isinstance(failure, (life.Unavailable, base.Refusal)) or not isinstance(failure, Exception):
                raise
            raise life.Unavailable() from None
        finally:
            ended = time.monotonic_ns()
            record = {"schema": 1, "sessionIndex": self.session_index, "attemptIndex": len(self.cleanup_attempts) + 1,
                "phase": self.phase, "selectedStage": int(self.selected or 0), "outcome": outcome,
                "failureReason": reason, "retainedFailureReason": self.first_cleanup_failure_reason,
                "failedStateRetained": int(self.failed), "startedMonotonicNs": started, "endedMonotonicNs": ended,
                "stopStartedMonotonicNs": self.stop_started, "deadlineMonotonicNs": self.stop_started + life.DISPOSAL_NS if self.stop_started else None,
                "emptyObservedMonotonicNs": self.empty_at, "termSentMonotonicNs": self.term_at,
                "termSentCount": self.term_count, "killUsed": self.kill_used, "killSentMonotonicNs": self.kill_at,
                "countsStatus": self._attempt_counts_status, "observedCounts": self._attempt_counts,
                "observedReferenceCounts": self._attempt_reference_counts,
                "holderObservedMonotonicNs": self._attempt_holder_at, "stage": self._attempt_stage,
                "physicalDisposalComplete": int(self.cleaned), "physicalProof": self.proof if self.cleaned else None,
                "samples": self.samples, "cgroupBefore": self.before, "cgroupAfter": self.after,
                "reachedBoundaries": self.boundaries,
                "outputAudit": self.audit.receipt()}
            frozen = base.canonical(record)
            self.cleanup_attempts += (frozen,)
            self.owner.cleanup_attempt_history = getattr(self.owner, "cleanup_attempt_history", ()) + (frozen,)
            if self.first_cleanup_error_reason is not None:
                self.error_reason = self.first_cleanup_error_reason

    def cleanup_once(self, budget):
        if self.cleaned:
            return self.proof
        # Never check row time as permission to abandon owned resources.
        error = None
        try:
            self.disposal_steps(inject=False)
        except (OSError, ValueError, base.Refusal, life.Unavailable, subprocess.SubprocessError) as failure:
            error = failure
            self.error_reason = failure.reason if isinstance(failure, base.Refusal) else "cleanup"
            try:
                self.emergency_dispose()
            except (OSError, ValueError, base.Refusal, life.Unavailable, subprocess.SubprocessError):
                self.failed = True
        finally:
            if self.selector is not None:
                self.selector.close()
                self.selector = None
            for pipe in (() if self.proc is None else (self.proc.stdout, self.proc.stderr)):
                if not pipe.closed:
                    pipe.close()
            for endpoint in (self.endpoint, self.child_endpoint):
                if endpoint is not None:
                    endpoint.close()
            if self.launch_pidfd is not None:
                os.close(self.launch_pidfd)
                self.launch_pidfd = None
        if error is not None:
            self.failed = True
            raise life.Unavailable() from None
        self._attempt_stage = "holders"
        counts = holder_counts(self.namespace_ids, self.descriptor_inodes,
                               self.stop_started + life.DISPOSAL_NS,
                               pid_namespace_ids={self.role_pid_namespace} if self.role_pid_namespace else set())
        self.note_counts(counts, "actual")
        seen = getattr(counts, "observed_counts", None)
        if seen is not None:
            self._attempt_reference_counts = life.numeric_record(dict(seen), set(self._attempt_counts))
        self._attempt_stage = "proof"
        all_resources_at = time.monotonic_ns()
        if all_resources_at > self.stop_started + life.DISPOSAL_NS:
            self.failed = True
            self.error_reason = "deadline"
        # No retained writable role mount exists after its namespace holders are
        # zero. The only host scratch allowed a fixed, already-removed file set.
        proof = {"ownedTasks": 0, **counts, "dumpFiles": 0, "identityMatched": 1,
                 "cgroupRemoved": int(self.cg is None or (self.cg.fd is None and not self.cg.path.exists())),
                 "mountTargetRemoved": int(self.mount_target is None or not self.mount_target.exists()),
                 "controlClosed": 1, "rowScratchRemoved": int(self.scratch is None or not self.scratch.exists())}
        life.validate_cleanup(proof)
        self.observation["termination"] = {"stopStartedMonotonicNs": self.stop_started,
            "emptyObservedMonotonicNs": self.empty_at, "termSentMonotonicNs": self.term_at,
            "termSentCount": self.term_count, "killUsed": self.kill_used, "killSentMonotonicNs": self.kill_at,
            "allResourcesObservedMonotonicNs": all_resources_at}
        life.validate_disposal(self.observation["termination"])
        self.cleaned, self.proof = True, proof
        self.owner.history.append({"phase": self.phase, "selectedStage": int(self.selected or 0),
            "boundaries": self.boundaries, "samples": self.samples, "termination": self.observation["termination"],
            "cgroupBefore": self.before, "cgroupAfter": self.after,
            "outputAudit": self.audit.receipt(), "cleanup": proof,
            "exitCode": self.exit_code if self.exit_code is not None and self.exit_code >= 0 else None,
            "signal": -self.exit_code if self.exit_code is not None and self.exit_code < 0 else None})
        return proof


class LinuxBackend:
    kind = "private-linux-cgroup-v2-candidate-runtime-review-required"
    def __init__(self, parent, release, profile, harness_digest, validation):
        self.parent, self.release, self.profile = parent, release, profile
        self.harness_digest, self.validation = harness_digest, validation
        self.active = None
        self.history, self.commands = [], []
        self.sessions = []
        self.cleanup_attempt_history = ()
        self.output_totals = {"stdout": 0, "stderr": 0}
        self.case = "R14"
        self.release_manifest = None
        self.admission_blocked = False
    def validate_profile(self): self.validation["profile"]()
    def validate_sources(self): self.validation["sources"]()
    def validate_capabilities(self): self.validation["capabilities"]()
    def validate_release(self): self.release_manifest, _ = self.validation["release"]()
    def validate_review(self): self.validation["review"]()
    def cleanup_complete(self):
        return not self.admission_blocked and all(life.session_cleanup_validated(session) for session in self.sessions)
    def cleanup_attempt_records(self):
        return [json.loads(record) for record in self.cleanup_attempt_history]
    def admit(self):
        if self.admission_blocked or not self.cleanup_complete():
            self.admission_blocked = True
            raise life.Unavailable()
    def phase(self, phase, budget):
        self.admit()
        self.case = "R14"
        self.active = Session(self, phase)
        self.sessions.append(self.active)
        self.active.setup(budget)
        self.active.await_armed_or_fault(budget)
        return self.active.observation
    def lifecycle(self, selected, observe, budget):
        self.admit()
        self.case = "R18"
        self.active = Session(self, "idle", selected, observe)
        self.sessions.append(self.active)
        self.active.setup(budget)
        self.active.await_armed_or_fault(budget)
        self.active.primary_dispose(budget)
    def cleanup(self, budget):
        if self.active is None:
            raise life.Unavailable()
        try:
            proof = self.active.cleanup(budget)
            if not life.session_cleanup_validated(self.active):
                raise life.Unavailable()
            return proof
        except Exception:
            # Cleanup itself remains callable, but once its proof failed this
            # backend cannot admit another role even after a later disposal retry.
            self.admission_blocked = True
            raise
