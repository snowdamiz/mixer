"""Bounded, child-free DEVNULL setup on the selected interpreter, before original36."""
import errno
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import types
import stdin_guard as guard
HERE = Path(__file__).resolve().parent

def no_children(event, args):
    if event in {'subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.kill','os.killpg','os.exec','os.spawn'} or event.startswith('socket.'):
        raise RuntimeError('Descriptor preflight forbids process/network operations: ' + event)

def require(value, message):
    if not value:
        raise RuntimeError(message)

def main():
    guard.write_guard(HERE)
    sys.addaudithook(no_children)
    evidence = HERE / 'evidence'
    evidence.mkdir(exist_ok=True)
    mode = 'optimized' if sys.flags.optimize else 'normal'
    destination = Path(tempfile.mkdtemp(prefix='preflight-' + mode + '-', dir=evidence))
    report = {'passed': False, 'mode': mode, 'python': sys.version, 'argv': sys.argv,
              'executable': sys.executable, 'executable_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
              'stdlib': subprocess.__file__, 'stdlib_sha256': hashlib.sha256(Path(subprocess.__file__).read_bytes()).hexdigest(),
              'guard_sha256': hashlib.sha256((HERE / 'stdin_guard.py').read_bytes()).hexdigest(),
              'actual_get_handles': True, 'actual_get_devnull': True, 'private_methods_patched': False,
              'real_inner_children': 0, 'timeout_seconds': 5, 'events': [], 'closed_descriptors': []}
    active = [True]
    def observer(event, args):
        if active[0] and event == 'open' and args[0] == '/dev/null':
            report['events'].append({'path': args[0], 'flags': args[2],
                'original_code': sys._getframe(1).f_code is guard._devnull_code})
    sys.addaudithook(observer)
    def expired(*args):
        raise TimeoutError('Descriptor preflight exceeded five seconds')
    handler = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 5)
    obj = object.__new__(subprocess.Popen)
    obj._closed_child_pipe_fds = False
    obj.pipesize = -1
    handles = []
    try:
        def setup(*args, **kwargs):
            nonlocal handles
            handles = list(obj._get_handles(subprocess.DEVNULL, subprocess.PIPE, subprocess.PIPE))
            require(len(handles) == 6 and handles[1] == -1, 'Unexpected selected-interpreter handle layout')
            descriptors = [handles[0], *handles[2:]]
            require(all(type(fd) is int and fd >= 0 for fd in descriptors)
                    and len(set(descriptors)) == 5, 'Five distinct nonnegative descriptors required')
            require(handles[0] == getattr(obj, '_devnull', None), 'Stdin must be the cached DEVNULL descriptor')
            for fd in descriptors:
                os.fstat(fd)
            report['validated_descriptors'] = descriptors
            report['stdin_matches_cached_devnull'] = True
            require(os.read(handles[0], 1) == b'', 'DEVNULL read differs')
            require(os.write(handles[0], b'preflight') == 9, 'DEVNULL write differs')
            for read_fd, write_fd in [(handles[2], handles[3]), (handles[4], handles[5])]:
                require(os.write(write_fd, b'x') == 1 and os.read(read_fd, 1) == b'x', 'Pipe roundtrip differs')
        guard.run_direct(types.SimpleNamespace(run=setup), [], HERE)
        require(guard._stdin_scope.get() is None, 'Capability leaked into caller')
        require(report['events'] == [{'path': '/dev/null', 'flags': os.O_RDWR | getattr(os, 'O_CLOEXEC', 0),
                                     'original_code': True}], 'Selected-interpreter audit boundary differs')
        report['passed'] = True
    except BaseException as error:
        report['error'] = repr(error)
    finally:
        active[0] = False
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, handler)
        # _get_handles closes partial pipe allocation itself on setup failure.
        # Close returned handles and the cached DEVNULL exactly once.
        for fd in sorted(set(handles + ([obj._devnull] if hasattr(obj, '_devnull') else []))):
            if fd < 0:
                continue
            try:
                os.close(fd)
                try:
                    os.fstat(fd)
                except OSError as error:
                    require(error.errno == errno.EBADF, 'Descriptor close not confirmed')
                else:
                    raise RuntimeError('Descriptor remains open')
                report['closed_descriptors'].append(fd)
            except BaseException as error:
                report['passed'] = False
                report.setdefault('cleanup_errors', []).append(repr(error))
        report['timer_disarmed'] = signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
        (destination / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'descriptor_preflight': str(destination / 'result.json'), **report}, sort_keys=True))
    return 0 if report['passed'] and report['timer_disarmed'] else 1

if __name__ == '__main__':
    sys.exit(main())
