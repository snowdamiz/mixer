"""Fresh, finite owned Git/gh commands for envelope/lint delivery.

Design basis only: reviewed-host-slices gated admission and streaming custody.
No earlier helper, admission or command is executed by this module.
"""
import sys
sys.dont_write_bytecode = True

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import selectors
import signal
import subprocess
import time
import threading

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
CAP = 8 * 1024 * 1024
AGGREGATE_CAP = 32 * 1024 * 1024
SESSION_REFUSAL = None
SESSION_ACTIVE = None
RETAINED_CHILDREN = []


def now():
    return datetime.now(timezone.utc).isoformat()


def save(name, value):
    with (OUT / name).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    directory = os.open(OUT, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def row(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    b = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(b),
            'sha256': hashlib.sha256(b).hexdigest()}


def wrapper():
    assert sys.flags.isolated == 1 and sys.flags.optimize == 0 and sys.flags.no_site == 1 and sys.dont_write_bytecode is True
    admission, gate = int(sys.argv[2]), int(sys.argv[3])
    payload = {'pid': os.getpid(), 'pgid': os.getpgrp(), 'sid': os.getsid(0)}
    os.write(admission, json.dumps(payload).encode() + b'\n')
    os.close(admission)
    released = os.read(gate, 1)
    os.close(gate)
    if released != b'1':
        raise SystemExit(125)
    os.execvpe(sys.argv[4], sys.argv[4:], os.environ)


def validate_argv(argv):
    """Pure admission rules; broad index enumeration is never admissible."""
    assert isinstance(argv, (list, tuple)) and argv and all(isinstance(a, str) and a and '\0' not in a for a in argv)
    assert argv[0] in ('git', 'gh') and len(argv) <= 2048
    if argv[0] == 'git':
        args = list(argv[1:])
        while args and args[0] == '-c':
            assert len(args) > 1 and args[1] in ('core.hooksPath=/dev/null', 'commit.gpgsign=false')
            args = args[2:]
        assert args and args[0] in (
            '--version', 'rev-parse', 'branch', 'remote', 'ls-remote', 'diff',
            'ls-files', 'status', 'add', 'commit', 'diff-tree', 'push')
        assert not any(a in ('--all', '--recurse-submodules', '-f') or a.startswith('--force') for a in args[1:]) or args[0] == 'add'
        assert not any(a.startswith('--output=') for a in args)
        if args[0] == 'ls-files':
            assert '--' in args, 'Exact finite dependency paths required'
            subjects = args[args.index('--') + 1:]
            assert 0 < len(subjects) <= 1024
            assert all(not p.startswith(('-', ':', '/')) and not any(c in p for c in '*?[]\\') and '..' not in p.split('/') and '.' not in p.split('/') and not p.endswith('/') for p in subjects)
            assert all((ROOT / p).is_file() and not (ROOT / p).is_symlink() for p in subjects), 'Only exact regular file dependencies are admissible'
    else:
        assert len(argv) >= 2 and argv[1] in ('--version', 'api', 'workflow')
        if argv[1] == 'api':
            assert len(argv) >= 3 and argv[2].startswith('repos/snowdamiz/mixer/')
            assert not any(a in ('-X', '--method', '--input', '-F', '--field', '-f', '--raw-field') for a in argv[3:]), 'API reads only'
        if argv[1] == 'workflow':
            assert len(argv) >= 4 and argv[2] == 'run'
    return True


def terminal_closed(code, group_absent, stdout_eof, stderr_eof):
    """Pure terminal conjunction; neither a reap nor one EOF alone suffices."""
    return (code is not None and group_absent is True
            and stdout_eof is True and stderr_eof is True)


def authority():
    p = OUT / 'authority.json'
    assert p.is_file() and not p.is_symlink(), 'Root final immutable selection authority is required'
    raw = p.read_bytes()
    a = json.loads(raw)
    assert a['schema'] == 1 and a['authorized'] is True
    assert a['repository'] == 'snowdamiz/mixer' and a['branch'] == 'main'
    selection = a['selection']
    assert row(ROOT / selection['path']) == selection
    assert a['baseline'] == {'head': 'a3967100c5773685bbaedb964aa6e5de9838cb8a', 'tree': '69178bebcc6f73680b28e920d798c032a51037f6'}
    return hashlib.sha256(raw).hexdigest()


def refuse_session(reason):
    global SESSION_REFUSAL
    if SESSION_REFUSAL is None:
        SESSION_REFUSAL = str(reason)


def assert_no_unresolved_startups():
    assert not (OUT / 'CUSTODY-UNRESOLVED.json').exists(), 'Custody latch blocks commands'
    labels = set()
    for suffix in ('.plan.json', '.started.json', '.admission.json', '.command.json'):
        labels.update(path.name[:-len(suffix)] for path in OUT.glob('*' + suffix))
    for label in sorted(labels):
        plan, terminal = OUT / (label + '.plan.json'), OUT / (label + '.command.json')
        assert plan.is_file() and not plan.is_symlink(), 'Unresolved durable startup plan'
        assert terminal.is_file() and not terminal.is_symlink(), 'Unresolved durable startup ownership'
        value = json.loads(terminal.read_bytes())
        assert value['admitted'] is True and value['exit'] == 0 and value['stopReason'] is None
        assert value['failure'] is None and value['sensitiveOutputRejected'] is False
        assert value['directChildReaped'] is True and value['ownedGroupAbsent'] is True
        assert value['stdoutEOF'] is True and value['stderrEOF'] is True
        assert value['signalAuthorityRetired'] is True and value['signalAuthorityLost'] is None
        assert value['postReapAbsenceProbeCount'] == 1
        assert value['rawWaitPID'] == value['ownedPID']
        status = value['rawWaitStatus']
        assert type(status) is int and (os.WIFEXITED(status) or os.WIFSIGNALED(status))
        assert os.waitstatus_to_exitcode(status) == value['exit']


def read_native_sigchld():
    # Read-only Darwin 64-bit libc sigaction ABI; installed SDK source is bound
    # in the correction packet. Unknown platforms/layouts/state fail closed.
    import ctypes
    assert sys.platform == 'darwin'
    assert ctypes.sizeof(ctypes.c_void_p) == 8
    assert ctypes.sizeof(ctypes.c_uint32) == 4 and ctypes.sizeof(ctypes.c_int) == 4
    class Sigaction(ctypes.Structure):
        _fields_ = [('handler', ctypes.c_void_p), ('mask', ctypes.c_uint32),
                    ('flags', ctypes.c_int)]
    assert ctypes.sizeof(Sigaction) == 16
    assert (Sigaction.handler.offset, Sigaction.mask.offset, Sigaction.flags.offset) == (0, 8, 12)
    libc = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    query = libc.sigaction
    query.argtypes = [ctypes.c_int, ctypes.POINTER(Sigaction), ctypes.POINTER(Sigaction)]
    query.restype = ctypes.c_int
    action = Sigaction()
    assert query(signal.SIGCHLD, None, ctypes.byref(action)) == 0, 'Native SIGCHLD state query failed'
    assert action.handler in (None, 0), 'Native SIGCHLD handler is not default'
    assert type(action.flags) is int and not action.flags & 0x0020, 'Native SA_NOCLDWAIT is forbidden'
    return {'platform': 'darwin-64', 'handler': action.handler, 'flags': action.flags,
            'SA_NOCLDWAIT': 0x0020, 'sigactionBytes': 16, 'readOnly': True}


def assert_driver_prerequisites():
    assert sys.flags.isolated == 1 and sys.flags.optimize == 0
    assert sys.flags.dont_write_bytecode == 1 and sys.dont_write_bytecode is True
    assert sys.flags.no_site == 1
    assert threading.current_thread() is threading.main_thread()
    assert len(threading.enumerate()) == 1, 'Fresh isolated driver with no competing reaper is required'
    assert signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL, 'SIGCHLD must have known default nonignored disposition'
    assert not subprocess._active, 'Preexisting implicit Popen cleanup is forbidden'
    return read_native_sigchld()


class OwnedPopen(subprocess.Popen):
    def __del__(self):
        # Deliberately inert even after partial construction and at shutdown.
        pass

    def _forbidden(self, *args, **kwargs):
        raise AssertionError('Implicit Popen custody API is forbidden')

    poll = wait = _internal_poll = _wait = _try_wait = _handle_exitstatus = _forbidden
    communicate = _communicate = send_signal = terminate = kill = _forbidden
    __enter__ = __exit__ = _forbidden


def construct_owned_child(argv, **kwargs):
    # Retain the inert wrapper before __init__, which may fork and then raise.
    child = OwnedPopen.__new__(OwnedPopen)
    RETAINED_CHILDREN.append(child)
    SESSION_ACTIVE['child'] = child
    OwnedPopen.__init__(child, argv, **kwargs)
    return child


class LeaderCustody:
    """Retain the unreaped leader as signal authority; retire before any reap.

    WNOWAIT observes terminal state without consuming the leader. If unavailable,
    no active observation is attempted; the final direct nonblocking wait first
    retires all signal authority. There is at most one post-reap absence probe.
    """
    def __init__(self, child):
        self.child = child
        self.admitted = False
        self.signal_authority = True
        self.authority_lost = None
        self.reap_attempted = False
        self.code = None
        self.raw_wait_pid = None
        self.raw_wait_status = None
        self.direct_reaped = False
        self.group_absent = None
        self.absence_probes = 0
        self.signals = []
        self.terminal_observed_wnowait = False
        self.terminal_observation = None
        self.wnowait_supported = all(hasattr(os, name) for name in
            ('waitid', 'P_PID', 'WEXITED', 'WNOHANG', 'WNOWAIT'))

    def observe(self):
        if self.reap_attempted:
            return self.direct_reaped
        if self.authority_lost is not None or not self.wnowait_supported:
            return None
        try:
            result = os.waitid(os.P_PID, self.child.pid,
                os.WEXITED | os.WNOHANG | os.WNOWAIT)
            terminal = result is not None and result.si_pid != 0
            if terminal:
                assert type(result.si_pid) is int and result.si_pid == self.child.pid
                assert type(result.si_code) is int and type(result.si_status) is int
                assert result.si_code in (os.CLD_EXITED, os.CLD_KILLED, os.CLD_DUMPED)
                if result.si_code == os.CLD_EXITED:
                    assert 0 <= result.si_status <= 255
                else:
                    assert 0 < result.si_status < signal.NSIG
                observed = (result.si_code, result.si_status)
                assert self.terminal_observation is None or self.terminal_observation == observed, 'Terminal observation changed'
                self.terminal_observation = observed
                self.terminal_observed_wnowait = True
            else:
                assert self.terminal_observation is None, 'Previously terminal leader lost from observation'
            return terminal
        except BaseException as exc:
            self.signal_authority = False
            self.authority_lost = 'unreaped-observation-failed: ' + repr(exc)
            raise

    def send(self, sig):
        assert sig in (signal.SIGTERM, signal.SIGKILL)
        assert self.signal_authority and not self.reap_attempted
        assert self.authority_lost is None, 'Leader signal authority was lost'
        self.signals.append(int(sig))
        try:
            if self.admitted:
                os.killpg(self.child.pid, sig)
            else:
                # Popen.send_signal may internally poll/reap: never use it here.
                os.kill(self.child.pid, sig)
        except ProcessLookupError:
            pass
        except BaseException as exc:
            self.signal_authority = False
            self.authority_lost = 'owned-signal-failed: ' + repr(exc)
            raise

    def final_reap(self):
        assert not self.reap_attempted and self.authority_lost is None
        # The exact kernel wait is a one-way transition. No later signals.
        self.signal_authority = False
        self.reap_attempted = True
        try:
            result = os.waitpid(self.child.pid, os.WNOHANG)
            assert isinstance(result, tuple) and len(result) == 2, 'Unexpected direct wait result'
            self.raw_wait_pid, self.raw_wait_status = result
            assert type(self.raw_wait_pid) is int and type(self.raw_wait_status) is int
            if result == (0, 0):
                self.authority_lost = 'final-direct-wait-did-not-reap-running-leader'
                return None
            assert self.raw_wait_pid == self.child.pid, 'Direct wait returned wrong PID'
            assert 0 <= self.raw_wait_status <= 65535, 'Direct wait raw status is out of range'
            assert os.WIFEXITED(self.raw_wait_status) or os.WIFSIGNALED(self.raw_wait_status), 'Direct wait returned nonterminal status'
            if os.WIFEXITED(self.raw_wait_status):
                assert self.raw_wait_status & 0xff == 0, 'Noncanonical exited raw status'
            else:
                assert self.raw_wait_status & 0xff00 == 0 and 0 < os.WTERMSIG(self.raw_wait_status) < signal.NSIG
            if self.terminal_observation is not None:
                kind, status = self.terminal_observation
                expected = status << 8 if kind == os.CLD_EXITED else status | (0x80 if kind == os.CLD_DUMPED else 0)
                assert self.raw_wait_status == expected, 'Direct wait contradicts unreaped terminal observation'
            self.code = os.waitstatus_to_exitcode(self.raw_wait_status)
        except BaseException as exc:
            self.authority_lost = 'final-direct-wait-failed: ' + repr(exc)
            raise
        self.direct_reaped = True
        # Popen bookkeeping is never reap evidence; no poll/wait method is used.
        self.child.returncode = self.code
        self.probe_absence_once()
        return self.code

    def probe_absence_once(self):
        assert self.reap_attempted and self.direct_reaped
        assert not self.signal_authority and self.absence_probes == 0
        self.absence_probes = 1
        try:
            os.killpg(self.child.pid, 0)
            self.group_absent = False
        except ProcessLookupError:
            self.group_absent = True
        except PermissionError:
            self.group_absent = None
        # Success or EPERM remains held; no second probe or later cleanup.
        return self.group_absent

    def evidence(self):
        return {'wnowaitSupported': self.wnowait_supported,
            'terminalObservedWithoutReap': self.terminal_observed_wnowait,
            'terminalObservation': self.terminal_observation,
            'signalAuthorityRetired': not self.signal_authority,
            'signalAuthorityLost': self.authority_lost,
            'finalReapAttempted': self.reap_attempted,
            'rawWaitPID': self.raw_wait_pid, 'rawWaitStatus': self.raw_wait_status,
            'implicitPopenReapingDisabled': True,
            'unresolvedChildRetainedUntilIsolatedDriverExit': True,
            'interpreterExitIsNotCustodyEvidence': True,
            'postReapAbsenceProbeCount': self.absence_probes,
            'noSignalAfterFinalReapOrLostAuthority': True,
            'postReapProbeSuccessOrEPERMHeldWithoutRetry': self.direct_reaped and self.group_absent is not True}


class Commands:
    def __init__(self, seconds, count, prefix):
        self.refused = False
        self.active = None
        self._check_clear()
        assert 0 < seconds <= 240 and 0 < count <= 25
        self.authority_sha256 = authority()
        self.active = None
        self.deadline = time.monotonic() + seconds
        self.maximum = count
        self.prefix = prefix
        self.records = []
        self.output_bytes = 0

    def _check_clear(self):
        assert not getattr(self, 'refused', False) and SESSION_REFUSAL is None, 'Permanent in-memory custody refusal'
        assert self.active is None and SESSION_ACTIVE is None, 'Active custody blocks commands'
        assert_no_unresolved_startups()

    def run(self, name, argv, seconds=25):
        self._check_clear()
        assert authority() == self.authority_sha256, "Authority changed during bounded session"
        validate_argv(argv)
        try:
            return self._run(name, argv, seconds)
        except BaseException as exc:
            self.refused = True
            refuse_session(repr(exc))
            if self.active is not None:
                try:
                    self._emergency_close(exc)
                except BaseException as cleanup:
                    self.cleanup_failure = repr(cleanup)
            raise

    def _run(self, name, argv, seconds=25):
        global SESSION_ACTIVE
        self._check_clear()
        native_sigchld = assert_driver_prerequisites()
        assert len(self.records) < self.maximum and argv[0] in ('git', 'gh')
        assert self.deadline - time.monotonic() > 15
        assert name and all(x.isalnum() or x == '-' for x in name)
        if argv[0] == 'git':
            argv = ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', *argv[1:]]
        label = self.prefix + name
        timeout = min(seconds, self.deadline - time.monotonic() - 10)
        assert timeout > 0 and not (OUT / (label + '.plan.json')).exists(), 'No command replay'
        save(label + '.plan.json', {
            'at': now(), 'argv': argv, 'cwd': str(ROOT), 'activeSeconds': timeout,
            'admissionSeconds': 5, 'cleanupSeconds': 6, 'streamCapEachBytes': CAP,
            'aggregateCapBytes': AGGREGATE_CAP, 'sessionCommandLimit': self.maximum, 'ordinal': len(self.records) + 1,
            'freshSessionRequired': True, 'targetReleaseAfterPersistedAdmissionOnly': True,
            'nativeSIGCHLD': native_sigchld, 'isolatedNoSiteBytecodeDisabled': True,
        })
        ar, aw = os.pipe()
        gr, gw = os.pipe()
        start = time.monotonic()
        self.active = {'label': label, 'startupFDs': [ar, aw, gr, gw],
                       'constructorCompleted': False, 'cleanupAuthority': False}
        SESSION_ACTIVE = self.active
        child = construct_owned_child(
            [sys.executable, '-I', '-B', '-S', str(Path(__file__).resolve()), '--owned-exec',
             str(aw), str(gr), *argv], cwd=ROOT, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
            pass_fds=(aw, gr),
        )
        custody = LeaderCustody(child)
        self.active = {'child': child, 'custody': custody, 'label': label, 'ar': ar, 'gate': gw, 'admitted': False, 'constructorCompleted': True, 'cleanupAuthority': True}
        SESSION_ACTIVE = self.active
        os.close(aw)
        os.close(gr)
        save(label + '.started.json', {'at': now(), 'ownedPID': child.pid, 'targetReleased': False})
        admitted = False
        identity = None
        failure = None
        stop = None
        signals = custody.signals
        streams = {'stdout': bytearray(), 'stderr': bytearray()}
        eof = {'stdout': False, 'stderr': False}
        observed = {'stdout': 0, 'stderr': 0}
        self.active['eof'] = eof
        selector = selectors.DefaultSelector()
        cleanup_deadline = None

        try:
            with selectors.DefaultSelector() as admission_selector:
                admission_selector.register(ar, selectors.EVENT_READ)
                if not admission_selector.select(5):
                    raise RuntimeError('Owned admission deadline')
                identity = json.loads(os.read(ar, 4096))
            assert identity == {'pid': child.pid, 'pgid': child.pid, 'sid': child.pid}
            assert os.getpgid(child.pid) == child.pid and os.getsid(child.pid) == child.pid
            save(label + '.admission.json', {
                'at': now(), 'argv': argv, 'identity': identity,
                'parentObservedPGID': child.pid, 'parentObservedSID': child.pid,
                'activeSeconds': timeout, 'cleanupSeconds': 6, 'streamCapEachBytes': CAP,
                'targetReleasedOnlyAfterPersistedAdmission': True,
            })
            admitted = True
            self.active['admitted'] = True
            custody.admitted = True
            os.write(gw, b'1')
            os.close(gw)
            gw = None
            self.active['gate'] = None
        except BaseException as exc:
            failure = repr(exc)
            stop = 'admission-failed'
            if gw is not None:
                os.close(gw)
                gw = None
                self.active['gate'] = None
        finally:
            os.close(ar)
            self.active['ar'] = None

        for key, pipe in (('stdout', child.stdout), ('stderr', child.stderr)):
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, key)

        while True:
            if stop is None and time.monotonic() - start >= timeout:
                stop = 'deadline'
            if stop is not None and cleanup_deadline is None:
                cleanup_deadline = time.monotonic() + 6
                custody.send(signal.SIGTERM)
            if cleanup_deadline is not None and time.monotonic() >= cleanup_deadline - 3 and int(signal.SIGKILL) not in signals:
                custody.send(signal.SIGKILL)
            for event, _ in selector.select(.05):
                key = event.data
                data = os.read(event.fileobj.fileno(), 65536)
                if not data:
                    selector.unregister(event.fileobj)
                    event.fileobj.close()
                    eof[key] = True
                else:
                    observed[key] += len(data)
                    remaining = CAP - len(streams[key])
                    streams[key].extend(data[:max(remaining, 0)])
                    self.output_bytes += len(data)
                    if self.output_bytes > AGGREGATE_CAP:
                        stop = stop or 'aggregate-cap'
                    if len(data) > remaining:
                        stop = stop or 'stream-cap'
            terminal = custody.observe()
            if all(eof.values()) and (terminal is True or not custody.wnowait_supported):
                break
            if cleanup_deadline is not None and time.monotonic() >= cleanup_deadline:
                break
        code = custody.final_reap()
        group_absent = custody.group_absent
        if group_absent is not True:
            stop = stop or 'owned-group-not-proven-absent'
        selector.close()
        for pipe in (child.stdout, child.stderr):
            if not pipe.closed:
                pipe.close()
        sensitive = any(marker in bytes(data).lower() for data in streams.values() for marker in (
            b'x-amz-signature=', b'x-goog-signature=', b'ghp_', b'github_pat_',
            b'authorization: bearer ', b'-----begin private key-----'))
        output_rows = {}
        for key, data in streams.items():
            safe = b'[redacted: sensitive output rejected]\n' if sensitive else bytes(data)
            with (OUT / (label + '.' + key)).open('xb') as f:
                f.write(safe)
            output_rows[key] = row(OUT / (label + '.' + key))
        result = {
            'at': now(), 'argv': argv, 'exit': code, 'admitted': admitted,
            'identity': identity, 'stopReason': stop, 'failure': failure,
            'elapsedSeconds': time.monotonic() - start, 'ownedPID': child.pid,
            'ownedPGID': child.pid if admitted else None,
            'directChildReaped': custody.direct_reaped, 'ownedGroupAbsent': group_absent,
            **custody.evidence(),
            'stdoutEOF': eof['stdout'], 'stderrEOF': eof['stderr'], 'signals': signals,
            'stdoutObservedBytes': observed['stdout'], 'stderrObservedBytes': observed['stderr'],
            'separateOutputPipes': True, 'authoritySHA256': self.authority_sha256,
            'aggregateOutputBytes': self.output_bytes, 'sensitiveOutputRejected': sensitive, **output_rows,
        }
        save(label + '.command.json', result)
        self.records.append({'name': label, **{k: result[k] for k in (
            'exit', 'admitted', 'stopReason', 'directChildReaped', 'ownedGroupAbsent',
            'stdoutEOF', 'stderrEOF', 'sensitiveOutputRejected')}})
        closed = terminal_closed(code, group_absent, eof['stdout'], eof['stderr'])
        if not closed:
            self.refused = True
            refuse_session('Terminal conjunction not proven')
            save('CUSTODY-UNRESOLVED.json', {'at': now(), 'command': label, 'result': result,
                                         'noFurtherCommandsOrRetry': True})
        if closed:
            self.active = None
            SESSION_ACTIVE = None
        assert admitted and closed and code == 0 and stop is None and failure is None and not sensitive, label
        return bytes(streams['stdout'])


    def _emergency_close(self, exception):
        """Latch in memory before storage; bounded closure survives evidence failure."""
        global SESSION_ACTIVE
        self.refused = True
        refuse_session(repr(exception))
        active = self.active
        label = active['label']
        errors = []
        def evidence_save(name, value):
            try:
                save(name, value)
            except BaseException as exc:
                errors.append(repr(exc))
        latch = OUT / 'CUSTODY-UNRESOLVED.json'
        try:
            latch_exists = latch.exists()
        except BaseException as exc:
            latch_exists = False
            errors.append(repr(exc))
        if not latch_exists:
            evidence_save(latch.name, {'at': now(), 'command': label,
                'exception': repr(exception), 'unexpectedPostspawnFailure': True,
                'inMemoryRefusalAlreadySet': True, 'noFurtherCommandsOrRetry': True})
        for key in ('gate', 'ar'):
            fd = active.get(key)
            if fd is not None:
                try:
                    os.close(fd)
                except OSError as exc:
                    errors.append(repr(exc))
                active[key] = None
        if not active.get('constructorCompleted'):
            for fd in active.get('startupFDs', []):
                try:
                    os.close(fd)
                except OSError as exc:
                    errors.append(repr(exc))
            active['startupFDs'] = []
            self.emergency_evidence_errors = errors
            # No PID/session/group/signal/wait authority was granted by a constructor exception.
            return
        child, custody = active['child'], active['custody']
        if custody.signal_authority and custody.authority_lost is None:
            custody.send(signal.SIGTERM)
        begin = time.monotonic()
        eof = dict(active.get('eof', {'stdout': False, 'stderr': False}))
        observed = {'stdout': 0, 'stderr': 0}
        with selectors.DefaultSelector() as selector:
            for key, pipe in (('stdout', child.stdout), ('stderr', child.stderr)):
                if not pipe.closed:
                    os.set_blocking(pipe.fileno(), False)
                    selector.register(pipe, selectors.EVENT_READ, key)
            while time.monotonic() - begin < 6:
                if custody.authority_lost is not None:
                    break
                if custody.signal_authority and time.monotonic() - begin >= 3 and int(signal.SIGKILL) not in custody.signals:
                    custody.send(signal.SIGKILL)
                for event, _ in selector.select(.05):
                    key = event.data
                    data = os.read(event.fileobj.fileno(), 65536)
                    if data:
                        observed[key] += len(data)
                    else:
                        selector.unregister(event.fileobj)
                        event.fileobj.close()
                        eof[key] = True
                terminal = custody.observe()
                if all(eof.values()) and (terminal is True or not custody.wnowait_supported):
                    break
        if not custody.reap_attempted and custody.authority_lost is None:
            custody.final_reap()
        for pipe in (child.stdout, child.stderr):
            if not pipe.closed:
                pipe.close()
        closed = terminal_closed(custody.code, custody.group_absent, eof['stdout'], eof['stderr'])
        evidence_save(label + '.emergency.json', {'at': now(), 'exception': repr(exception),
            'ownedPID': child.pid, 'admitted': active['admitted'], 'exit': custody.code,
            'directChildReaped': custody.direct_reaped, 'ownedGroupAbsent': custody.group_absent,
            **custody.evidence(),
            'stdoutEOF': eof['stdout'], 'stderrEOF': eof['stderr'],
            'observedBytesDuringEmergency': observed, 'signals': custody.signals,
            'evidenceWriteErrors': errors, 'inMemoryRefusalRetained': True,
            'hardLatchRetainedEvenIfClosed': True, 'noRetry': True})
        if closed:
            self.active = None
            SESSION_ACTIVE = None
        self.emergency_evidence_errors = errors


if __name__ == '__main__':
    assert sys.argv[1] == '--owned-exec'
    wrapper()
