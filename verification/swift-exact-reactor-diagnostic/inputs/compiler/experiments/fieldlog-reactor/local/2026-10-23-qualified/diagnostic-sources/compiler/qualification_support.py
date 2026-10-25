"""Bounded evidence collection for the local, trusted-tool compiler harness."""
from pathlib import Path
import hashlib
import json
import os
import signal
import stat
import subprocess
import time


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def tool_identity(path):
    requested = Path(path).absolute()
    resolved = requested.resolve(strict=True)
    mode = resolved.stat().st_mode
    if not stat.S_ISREG(mode) or not os.access(requested, os.X_OK):
        raise ValueError(f'Not a regular executable: {requested}')
    return {'path': str(requested), 'resolvedPath': str(resolved),
            'bytes': resolved.stat().st_size, 'sha256': digest(resolved)}


def clean_environment(source=None):
    # Installed compiler/toolchain configuration remains trusted. Drop ambient
    # code injection, compiler replacement, Node options and SwiftPM overrides.
    source = os.environ if source is None else source
    accepted = {'HOME', 'USER', 'LOGNAME', 'PATH', 'TMPDIR', 'LANG', 'TERM'}
    return {key: value for key, value in source.items()
            if key in accepted or key.startswith('LC_')}


def strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError(f'Duplicate JSON member: {key}')
            result[key] = item
        return result

    def constant(value):
        raise ValueError(f'Non-finite JSON number: {value}')

    return json.loads(value, object_pairs_hook=pairs, parse_constant=constant)


def model_observations(value):
    expected = {'status': 'passed', 'taskCount': 1000, 'completionBasisPoints': 5000,
                'codableRoundTrip': True, 'unicodePreserved': True, 'reordered': True,
                'committedEntries': 1, 'pendingChanges': 1503, 'emptyTitleRejected': True,
                'repeatedCommitRejected': True, 'reportIncludesEntry': True}
    if (not isinstance(value, dict) or value.keys() != expected.keys()
            or any(type(value[key]) is not type(item) or value[key] != item
                   for key, item in expected.items())):
        raise ValueError('Model observations do not match the bounded corpus expectations')
    return value


def vm_receipt(value, exit_code):
    fields = {'profile', 'valid', 'inventory_complete', 'imports', 'exports', 'opcodes',
              'extended_opcodes', 'error', 'inventory_error'}
    if (not isinstance(value, dict) or value.keys() != fields
            or value['profile'] != 'mixer-integer-v1'
            or type(value['valid']) is not bool
            or type(value['inventory_complete']) is not bool
            or any(type(value[key]) is not list
                   for key in ['imports', 'exports', 'opcodes', 'extended_opcodes'])
            or exit_code not in (0, 2) or value['valid'] != (exit_code == 0)):
        raise ValueError('Owned VM exit status/profile/receipt disagree')
    if value['valid'] and (not value['inventory_complete']
                           or value['error'] is not None or value['inventory_error'] is not None):
        raise ValueError('Owned VM accepted with an incomplete inventory or error')
    if not value['valid'] and not isinstance(value['error'], dict):
        raise ValueError('Owned VM rejection omitted its error')
    return value


class CommandRecorder:
    def __init__(self, output, commands, cwd, *, log_limit=64 * 1024 * 1024,
                 result_limit=2 * 1024 * 1024):
        self.output, self.commands, self.cwd = Path(output), commands, cwd
        self.log_limit, self.result_limit = log_limit, result_limit

    def run(self, name, command, *, env=None, expected=(0,), timeout=300):
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._' for c in name):
            raise ValueError('Unsafe command evidence name')
        command = [str(item) for item in command]
        identity = tool_identity(command[0])
        started = time.monotonic()
        item = {'name': name, 'command': command, 'executable': identity,
                'exitCode': None, 'timedOut': False, 'outputLimitExceeded': False}
        self.commands.append(item)
        stdout, stderr = self.output / (name + '.stdout'), self.output / (name + '.stderr')
        process = None
        try:
            with stdout.open('xb') as out, stderr.open('xb') as err:
                process = subprocess.Popen(command, cwd=self.cwd, env=env, stdout=out, stderr=err,
                                           start_new_session=True)
                while process.poll() is None:
                    item['timedOut'] = time.monotonic() - started > timeout
                    item['outputLimitExceeded'] = max(os.fstat(out.fileno()).st_size,
                                                       os.fstat(err.fileno()).st_size) > self.log_limit
                    if item['timedOut'] or item['outputLimitExceeded']:
                        os.killpg(process.pid, signal.SIGKILL)
                        break
                    time.sleep(0.02)
                item['exitCode'] = process.wait()
            item['outputLimitExceeded'] |= max(stdout.stat().st_size, stderr.stat().st_size) > self.log_limit
            if tool_identity(command[0]) != identity:
                raise RuntimeError(f'{name} executable changed during execution')
            if item['timedOut']:
                raise RuntimeError(f'{name} timed out; partial stdout/stderr retained')
            if item['outputLimitExceeded']:
                raise RuntimeError(f'{name} exceeded its command log byte limit')
            if item['exitCode'] not in expected:
                raise RuntimeError(f'{name} failed ({item["exitCode"]}); see {stderr}')
            if stdout.stat().st_size > self.result_limit:
                raise RuntimeError(f'{name} exceeded its bounded result byte limit')
            return stdout.read_text(encoding='utf-8')
        finally:
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            # Keep evidence even on spawn errors, invalid UTF-8, timeouts and
            # receipt parsing failures. Logs are streamed to disk, never pipes.
            item['elapsedSeconds'] = round(time.monotonic() - started, 3)
            for key, path in [('stdout', stdout), ('stderr', stderr)]:
                if path.exists():
                    item[key] = {'path': path.name, 'bytes': path.stat().st_size, 'sha256': digest(path)}
