"""Fresh, finite owned Git/gh commands for corrected host-diagnostic delivery.

Design basis only: reviewed-host-slices gated admission and streaming custody.
No earlier helper, admission or command is executed by this module.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import selectors
import signal
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
CAP = 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def save(name, value):
    with (OUT / name).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def row(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    b = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(b),
            'sha256': hashlib.sha256(b).hexdigest()}


def wrapper():
    admission, gate = int(sys.argv[2]), int(sys.argv[3])
    payload = {'pid': os.getpid(), 'pgid': os.getpgrp(), 'sid': os.getsid(0)}
    os.write(admission, json.dumps(payload).encode() + b'\n')
    os.close(admission)
    released = os.read(gate, 1)
    os.close(gate)
    if released != b'1':
        raise SystemExit(125)
    os.execvpe(sys.argv[4], sys.argv[4:], os.environ)


class Commands:
    def __init__(self, seconds, count, prefix):
        assert 0 < seconds <= 240 and 0 < count <= 25
        self.deadline = time.monotonic() + seconds
        self.maximum = count
        self.prefix = prefix
        self.records = []

    def run(self, name, argv, seconds=25):
        assert not (OUT / 'CUSTODY-UNRESOLVED.json').exists(), 'Custody latch blocks commands'
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
            'sessionCommandLimit': self.maximum, 'ordinal': len(self.records) + 1,
            'freshSessionRequired': True, 'targetReleaseAfterPersistedAdmissionOnly': True,
        })
        ar, aw = os.pipe()
        gr, gw = os.pipe()
        start = time.monotonic()
        child = subprocess.Popen(
            [sys.executable, '-B', str(Path(__file__).resolve()), '--owned-exec',
             str(aw), str(gr), *argv], cwd=ROOT, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
            pass_fds=(aw, gr),
        )
        os.close(aw)
        os.close(gr)
        save(label + '.started.json', {'at': now(), 'ownedPID': child.pid, 'targetReleased': False})
        admitted = False
        identity = None
        failure = None
        stop = None
        signals = []
        streams = {'stdout': bytearray(), 'stderr': bytearray()}
        eof = {'stdout': False, 'stderr': False}
        selector = selectors.DefaultSelector()
        cleanup_deadline = None

        def absent():
            try:
                os.killpg(child.pid, 0)
                return False
            except ProcessLookupError:
                return True
            except PermissionError:
                return None

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
            os.write(gw, b'1')
            os.close(gw)
            gw = None
        except BaseException as exc:
            failure = repr(exc)
            stop = 'admission-failed'
            if gw is not None:
                os.close(gw)
                gw = None
        finally:
            os.close(ar)

        for key, pipe in (('stdout', child.stdout), ('stderr', child.stderr)):
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, key)

        while True:
            if stop is None and time.monotonic() - start >= timeout:
                stop = 'deadline'
            if stop is not None and cleanup_deadline is None:
                cleanup_deadline = time.monotonic() + 6
                try:
                    if admitted:
                        os.killpg(child.pid, signal.SIGTERM)
                    else:
                        child.send_signal(signal.SIGTERM)
                    signals.append(int(signal.SIGTERM))
                except ProcessLookupError:
                    pass
            if cleanup_deadline is not None and time.monotonic() >= cleanup_deadline - 3 and int(signal.SIGKILL) not in signals:
                try:
                    if admitted:
                        os.killpg(child.pid, signal.SIGKILL)
                    else:
                        child.send_signal(signal.SIGKILL)
                    signals.append(int(signal.SIGKILL))
                except ProcessLookupError:
                    pass
            for event, _ in selector.select(.05):
                key = event.data
                data = os.read(event.fileobj.fileno(), 65536)
                if not data:
                    selector.unregister(event.fileobj)
                    event.fileobj.close()
                    eof[key] = True
                else:
                    remaining = CAP - len(streams[key])
                    streams[key].extend(data[:max(remaining, 0)])
                    if len(data) > remaining:
                        stop = stop or 'stream-cap'
            code = child.poll()
            if code is not None and all(eof.values()):
                group_absent = absent()
                if group_absent is True:
                    break
                stop = stop or 'owned-group-not-proven-absent'
            if cleanup_deadline is not None and time.monotonic() >= cleanup_deadline:
                break
        code = child.poll()
        group_absent = absent()
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
            'directChildReaped': code is not None, 'ownedGroupAbsent': group_absent,
            'stdoutEOF': eof['stdout'], 'stderrEOF': eof['stderr'], 'signals': signals,
            'sensitiveOutputRejected': sensitive, **output_rows,
        }
        save(label + '.command.json', result)
        self.records.append({'name': label, **{k: result[k] for k in (
            'exit', 'admitted', 'stopReason', 'directChildReaped', 'ownedGroupAbsent',
            'stdoutEOF', 'stderrEOF', 'sensitiveOutputRejected')}})
        closed = code is not None and group_absent is True and all(eof.values())
        if not closed:
            save('CUSTODY-UNRESOLVED.json', {'at': now(), 'command': label, 'result': result,
                                         'noFurtherCommandsOrRetry': True})
        assert admitted and closed and code == 0 and stop is None and failure is None and not sensitive, label
        return bytes(streams['stdout'])


if __name__ == '__main__':
    assert sys.argv[1] == '--owned-exec'
    wrapper()
