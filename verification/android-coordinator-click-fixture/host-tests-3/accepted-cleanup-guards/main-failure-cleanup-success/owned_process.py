"""Bounded child command execution with cleanup confined to its newly created process group."""
import os
import signal
import subprocess
import time
from types import SimpleNamespace


def members(group):
    result = subprocess.run(['ps', '-axo', 'pid=,pgid=,stat=,command='], capture_output=True,
                            text=True, timeout=10, check=True)
    found = []
    for line in result.stdout.splitlines():
        fields = line.strip().split(None, 3)
        if len(fields) >= 3 and int(fields[1]) == group and not fields[2].startswith('Z'):
            found.append(line.strip())
    return found


def stop_group(group):
    """Only called for a start_new_session child group created by execute below."""
    before = members(group)
    if not before:
        return {'group': group, 'before': [], 'after': [], 'signals': []}
    signals = []
    for sig, duration in [(signal.SIGTERM, 3), (signal.SIGKILL, 3)]:
        try:
            os.killpg(group, sig)
            signals.append(sig.name)
        except ProcessLookupError:
            break
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            if not members(group):
                return {'group': group, 'before': before, 'after': [], 'signals': signals}
            time.sleep(.1)
    after = members(group)
    if after:
        raise RuntimeError('newly owned command group still active: ' + repr(after))
    return {'group': group, 'before': before, 'after': after, 'signals': signals}


def execute(argv, *, cwd, env=None, timeout=180):
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               start_new_session=True)
    group = process.pid
    cleanup = None
    timed_out = False
    output = b''
    try:
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            cleanup = stop_group(group)
            output, _ = process.communicate(timeout=10)
        # Successful parent exit does not authorize leaving compiler/adb descendants behind.
        if cleanup is None:
            cleanup = stop_group(group)
        code = -1 if timed_out else process.returncode
        if cleanup['before'] and not timed_out:
            code = -2
            output += b'\nOWNED COMMAND LEFT DESCENDANTS; CLEANED AND REJECTED\n'
        if timed_out:
            output += b'\nCOMMAND TIMEOUT; NEWLY OWNED GROUP CLEANED\n'
        return SimpleNamespace(stdout=output, returncode=code, groupCleanup=cleanup, timedOut=timed_out)
    finally:
        if process.poll() is None:
            stop_group(group)
            process.wait(timeout=10)
        process.stdout.close()
