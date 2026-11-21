"""Bounded evidence collection for the local, trusted-tool compiler harness."""
from contextlib import ExitStack
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


class _QualificationProcess(subprocess.Popen):
    def __del__(self):
        # Popen's finalizer can poll and register a child for later implicit polls.
        # Only the recorder may observe a child whose custody is unresolved.
        pass


class CommandRecorder:
    def __init__(self, output, commands, cwd, *, log_limit=64 * 1024 * 1024,
                 result_limit=2 * 1024 * 1024):
        self.output, self.commands, self.cwd = Path(output), commands, cwd
        self.log_limit, self.result_limit = log_limit, result_limit

    @staticmethod
    def _finish_process(process, item):
        group_gone = False
        step = 'stop process group'
        try:
            if item['exitCode'] is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    group_gone = True
                step = 'reap direct child'
                item['exitCode'] = process.wait(timeout=3)
            if not group_gone:
                step = 'observe process group absence'
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    group_gone = True
        except (OSError, subprocess.TimeoutExpired) as error:
            item['cleanupError'] = f'{step} failed ({error})'
            return error
        if group_gone:
            item['terminalCustody'] = 'TERMINAL'
        else:
            item['cleanupError'] = 'Process group still present after direct child exit'
        return None

    def run(self, name, command, *, env=None, expected=(0,), timeout=300):
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._' for c in name):
            raise ValueError('Unsafe command evidence name')
        command = [str(item) for item in command]
        identity = tool_identity(command[0])
        started = time.monotonic()
        item = {'name': name, 'command': command, 'executable': identity,
                'exitCode': None, 'timedOut': False, 'outputLimitExceeded': False,
                'terminalCustody': 'NOT_STARTED'}
        self.commands.append(item)
        stdout, stderr = self.output / (name + '.stdout'), self.output / (name + '.stderr')
        opened_logs = {}
        evidence_error = None
        try:
            with ExitStack() as logs:
                out = logs.enter_context(stdout.open('xb'))
                opened_logs['stdout'] = stdout
                err = logs.enter_context(stderr.open('xb'))
                opened_logs['stderr'] = stderr
                item['terminalCustody'] = 'UNKNOWN'
                process = _QualificationProcess(command, cwd=self.cwd, env=env, stdout=out,
                                                stderr=err, start_new_session=True)
                item['pid'] = item['pgid'] = process.pid
                try:
                    while True:
                        item['exitCode'] = process.poll()
                        if item['exitCode'] is not None:
                            break
                        item['timedOut'] = time.monotonic() - started > timeout
                        item['outputLimitExceeded'] = max(os.fstat(out.fileno()).st_size,
                                                           os.fstat(err.fileno()).st_size) > self.log_limit
                        if item['timedOut'] or item['outputLimitExceeded']:
                            break
                        time.sleep(0.02)
                finally:
                    cleanup_error = self._finish_process(process, item)
            if item['terminalCustody'] == 'UNKNOWN':
                reason = 'could not confirm process termination'
                if item['timedOut']:
                    reason = 'timed out'
                elif item['outputLimitExceeded']:
                    reason = 'exceeded its command log byte limit'
                message = f'{name} {reason}. UNKNOWN process custody. Preserve {self.output}'
                raise RuntimeError(message) from cleanup_error
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
            result = stdout.read_text(encoding='utf-8')
        except Exception as error:
            item['error'] = str(error)
            raise
        finally:
            item['elapsedSeconds'] = round(time.monotonic() - started, 3)
            for key, path in opened_logs.items():
                metadata = item[key] = {'path': path.name}
                try:
                    metadata['bytes'] = path.stat().st_size
                    item['outputLimitExceeded'] |= metadata['bytes'] > self.log_limit
                    # An unresolved writer may still be appending to the log.
                    if item['terminalCustody'] != 'UNKNOWN':
                        metadata['sha256'] = digest(path)
                except OSError as error:
                    metadata['error'] = str(error)
                    if evidence_error is None:
                        evidence_error = error
        if evidence_error is not None:
            item['error'] = f'{name} could not record command log evidence'
            raise RuntimeError(item['error']) from evidence_error
        return result
