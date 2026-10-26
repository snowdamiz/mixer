"""Bounded review-owned host command groups and raw output receipts."""
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import time


def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


class Runner:
    def __init__(self, out):
        self.out = pathlib.Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.commands = []
        self.environment = None

    def run(self, label, argv, cwd, timeout=120, expected=0, env=None):
        argv = list(map(str, argv))
        stdout = self.out / (label + '.stdout')
        stderr = self.out / (label + '.stderr')
        print('START ' + label, flush=True)
        started = time.monotonic()
        with stdout.open('wb') as out, stderr.open('wb') as err:
            child = subprocess.Popen(argv, cwd=cwd, env=env if env is not None else self.environment,
                                     stdout=out, stderr=err, start_new_session=True)
            reason = None
            while child.poll() is None:
                if time.monotonic() - started > timeout:
                    reason = 'deadline'
                    break
                if stdout.stat().st_size > 64 * 1024 * 1024 or stderr.stat().st_size > 64 * 1024 * 1024:
                    reason = 'output-bound'
                    break
                time.sleep(0.05)
            if reason:
                try: os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try: os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    child.wait(timeout=2)
            exit_code = child.wait()
            group_remaining = False
            try:
                os.killpg(child.pid, 0)
                group_remaining = True
            except ProcessLookupError:
                pass
            if group_remaining:
                try: os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                time.sleep(0.2)
                try: os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
        result = {'label': label, 'argv': argv, 'cwd': str(cwd), 'exit_code': exit_code,
                  'deadline_seconds': timeout, 'elapsed_seconds': round(time.monotonic() - started, 3),
                  'stdout': stdout.name, 'stderr': stderr.name,
                  'stdout_sha256': digest(stdout), 'stderr_sha256': digest(stderr),
                  'stdout_bytes': stdout.stat().st_size, 'stderr_bytes': stderr.stat().st_size,
                  'owned_process_group': child.pid, 'owned_group_absent_on_completion': not group_remaining,
                  'failure_reason': reason}
        self.commands.append(result)
        (self.out / 'commands.json').write_text(json.dumps(self.commands, indent=2, sort_keys=True) + '\n')
        print('END ' + label + ' exit=' + str(exit_code), flush=True)
        assert not reason and not group_remaining, result
        if expected is not None:
            assert exit_code == expected, result
        return stdout.read_text(), stderr.read_text(), result
