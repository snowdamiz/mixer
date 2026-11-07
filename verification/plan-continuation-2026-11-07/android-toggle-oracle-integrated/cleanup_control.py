"""Bounded cleanup of Popen-owned session groups only; never searches other groups."""
import os
import signal
import subprocess
import time


def presence(pid, result):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        probe = subprocess.run(['pgrep', '-g', str(pid)], capture_output=True, text=True, timeout=5)
        result.setdefault('permissionErrorGroupProbes', []).append({
            'argv': ['pgrep', '-g', str(pid)], 'exitCode': probe.returncode,
            'stdout': probe.stdout, 'stderr': probe.stderr})
        return False if probe.returncode == 1 else True if probe.returncode == 0 else None


def stop(process):
    result = {'pid': process.pid, 'pgid': process.pid, 'signals': []}
    try:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            process.poll()
            state = presence(process.pid, result)
            if state is False:
                break
            if state is None:
                result['groupAbsent'] = False
                return result
            try:
                os.killpg(process.pid, sig)
                result['signals'].append(sig.name)
            except ProcessLookupError:
                break
            except PermissionError as failure:
                result['signalError'] = str(failure)
                break
            until = time.monotonic() + 3
            while time.monotonic() < until:
                process.poll()
                if presence(process.pid, result) is False:
                    break
                time.sleep(.1)
        process.poll()
        result['groupAbsent'] = presence(process.pid, result) is False
        result['leaderReaped'] = process.returncode is not None
    except (OSError, subprocess.TimeoutExpired) as failure:
        result.update(groupAbsent=False, cleanupError=str(failure))
    return result
