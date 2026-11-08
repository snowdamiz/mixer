"""Local adaptation of canonical Commands' bounded pipes and custody facts.

One selector drains short commands plus the three owned native services. No
process enumeration, threads, historical IDs, or retries after unknown custody.
"""
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import time

MIB = 1024 * 1024


class Commands:
    def __init__(self, out, env, *, deadline, output_bytes=8*MIB,
                 total_output_bytes=64*MIB, cleanup_seconds=5):
        self.out, self.env, self.deadline = Path(out), env, deadline
        self.output_bytes, self.total_output_bytes = output_bytes, total_output_bytes
        self.cleanup_seconds = cleanup_seconds
        self.used_output = 0
        self.records, self.owned = [], []
        self.selector = selectors.DefaultSelector()
        self.hold = None
        self.limit = None

    def flush(self):
        (self.out / 'commands.json').write_text(json.dumps(self.records, indent=2)+'\n')

    def unknown(self, item, operation, error):
        record = item['record']
        record['cleanup_errors'].append({'operation': operation, 'error': repr(error)})
        record['state'] = 'UNKNOWN'
        self.hold = {'label': record['label'], 'operation': operation, 'error': repr(error)}
        self.flush()
        return record

    def admissible(self):
        if self.hold or self.limit or time.monotonic() >= self.deadline - self.cleanup_seconds:
            raise RuntimeError('command admission closed: '+str(self.hold or self.limit or 'deadline'))

    def start(self, label, argv, cwd, *, long_lived=False):
        self.admissible()
        if len(self.records) >= 160:
            raise RuntimeError('command count budget exhausted')
        if long_lived and sum(i['record']['state']=='RUNNING' and i['record']['long_lived'] for i in self.owned) >= 3:
            raise RuntimeError('three owned service limit')
        record = {'label': label, 'argv': list(map(str, argv)), 'cwd': str(cwd),
                  'long_lived': long_lived, 'state': 'STARTING', 'exit_code': None,
                  'direct_child_reaped': False, 'stdout_eof': False, 'stderr_eof': False,
                  'owned_group_absent': False, 'terminal_custody': False,
                  'cleanup_errors': [], 'signals': [], 'group_probes': 0,
                  'output_bytes': 0, 'output_limit': self.output_bytes,
                  'aggregate_limit': self.total_output_bytes, 'stop': None,
                  'started_monotonic': time.monotonic()}
        item = {'record': record, 'process': None, 'buffers': {'stdout': bytearray(), 'stderr': bytearray()}}
        self.records.append(record)
        self.owned.append(item)
        try:
            child = subprocess.Popen(record['argv'], cwd=cwd, env=self.env,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            item['process'] = child
            record.update(pid=child.pid, owned_pgid=child.pid, state='RUNNING')
            for name in item['buffers']:
                pipe = getattr(child, name)
                os.set_blocking(pipe.fileno(), False)
                self.selector.register(pipe, selectors.EVENT_READ, (item, name))
        except BaseException as error:
            self.unknown(item, 'launch-or-pipe-setup', error)
            raise
        self.flush()
        return item

    def pump(self, seconds=.02):
        if self.hold:
            return
        for key, _ in self.selector.select(max(0, min(seconds, self.deadline-time.monotonic()))):
            item, name = key.data
            record = item['record']
            if record['state'] != 'RUNNING':
                continue
            try:
                data = os.read(key.fd, 65536)
                if not data:
                    record[name+'_eof'] = True
                    self.selector.unregister(key.fileobj)
                    continue
                room = max(0, min(self.output_bytes-record['output_bytes'],
                                  self.total_output_bytes-self.used_output))
                kept = data[:room]
                item['buffers'][name].extend(kept)
                record['output_bytes'] += len(kept)
                self.used_output += len(kept)
                if len(kept) != len(data):
                    record['stop'] = 'output-limit'
                    self.limit = 'output-limit: '+record['label']
            except BlockingIOError:
                continue
            except BaseException as error:
                self.unknown(item, 'read-'+name, error)
                return

    def reaped(self, item):
        r = item['record']
        if r['state'] != 'RUNNING' or self.hold:
            return r['direct_child_reaped']
        if not r['direct_child_reaped']:
            try:
                code = item['process'].poll()
                if code is not None:
                    r.update(exit_code=code, direct_child_reaped=True)
            except BaseException as error:
                self.unknown(item, 'reap-direct-child', error)
        return r['direct_child_reaped']

    def stop(self, item):
        r = item['record']
        if r['state'] != 'RUNNING' or self.hold:
            return r
        until = min(self.deadline, time.monotonic()+self.cleanup_seconds)
        if time.monotonic() >= until:
            return self.unknown(item, 'cleanup-deadline', 'no remaining time')
        # Reap an already exited direct child before any group operation. Darwin
        # can report EPERM for a group whose only member is an unreaped zombie.
        self.reaped(item)
        if self.hold:
            return r
        try:
            os.killpg(r['owned_pgid'], signal.SIGKILL)
            r['signals'].append('SIGKILL')
        except ProcessLookupError:
            r['owned_group_absent'] = True
        except BaseException as error:
            return self.unknown(item, 'signal-owned-group', error)
        while not self.hold:
            self.reaped(item)
            if self.hold:
                break
            if r['direct_child_reaped'] and not r['owned_group_absent']:
                try:
                    r['group_probes'] += 1
                    os.killpg(r['owned_pgid'], 0)
                except ProcessLookupError:
                    r['owned_group_absent'] = True
                except BaseException as error:
                    return self.unknown(item, 'observe-owned-group', error)
            self.pump(0)
            if self.hold:
                break
            if all(r[k] for k in ('direct_child_reaped','stdout_eof','stderr_eof','owned_group_absent')):
                r['terminal_custody'] = True
                r['state'] = 'TERMINAL'
                break
            if time.monotonic() >= until:
                return self.unknown(item, 'cleanup-deadline', 'custody incomplete')
            self.pump(min(.01, max(0, until-time.monotonic())))
        if r['terminal_custody']:
            try:
                for name in item['buffers']:
                    getattr(item['process'], name).close()
            except BaseException as error:
                r['terminal_custody'] = False
                return self.unknown(item, 'close-pipes', error)
        self.persist(item)
        return r

    def persist(self, item):
        r = item['record']
        try:
            r['logs'] = {}
            for name, data in item['buffers'].items():
                path = self.out / (str(self.records.index(r)).zfill(3)+'-'+r['label']+'.'+name)
                path.write_bytes(data)
                r['logs'][name] = str(path)
            self.flush()
        except BaseException as error:
            r['terminal_custody'] = False
            self.unknown(item, 'persist', error)

    def run(self, label, argv, cwd, timeout=120, allowed=(0,)):
        item = self.start(label, argv, cwd)
        r = item['record']
        until = min(self.deadline-self.cleanup_seconds, time.monotonic()+min(timeout,120))
        try:
            while not self.hold:
                if time.monotonic() >= until:
                    r['stop'] = 'timeout'
                    break
                self.pump(min(.02, max(0, until-time.monotonic())))
                if self.hold or self.limit:
                    break
                if self.reaped(item) and r['stdout_eof'] and r['stderr_eof']:
                    break
                if time.monotonic() >= until:
                    r['stop'] = 'timeout'
                    break
        except BaseException as error:
            r['execution_error'] = repr(error)
        finally:
            self.stop(item)
            self.persist(item)
        if (self.hold or self.limit or not r['terminal_custody'] or r['stop']
                or 'execution_error' in r or r['exit_code'] not in allowed):
            raise RuntimeError(label+' failed: '+str(self.hold or self.limit or r['stop'] or r['exit_code']))
        return bytes(item['buffers']['stdout']+item['buffers']['stderr']).decode(errors='replace').strip()

    def pause(self, seconds):
        until = min(time.monotonic()+seconds, self.deadline-self.cleanup_seconds)
        while time.monotonic() < until:
            self.admissible()
            self.pump(min(.02, until-time.monotonic()))
        self.admissible()

    def captured(self, label):
        return '\n'.join(bytes(i['buffers']['stdout']+i['buffers']['stderr']).decode(errors='replace')
                         for i in self.owned if i['record']['label']==label)

    def cleanup(self, scratch):
        for item in reversed(self.owned):
            if self.hold:
                break
            try:
                self.stop(item)
            except BaseException as error:
                self.unknown(item, 'cleanup', error)
                break
        for item in self.owned:
            self.persist(item)
        terminal = not self.hold and all(r['terminal_custody'] for r in self.records)
        result = {'allTerminalCustody': terminal, 'hold': self.hold, 'scratchRemoved': False,
                  'aggregateBytes': self.used_output, 'aggregateLimit': self.total_output_bytes}
        if terminal:
            try:
                self.selector.close()
                shutil.rmtree(scratch)
                result['scratchRemoved'] = not Path(scratch).exists()
            except BaseException as error:
                result['cleanupError'] = repr(error)
        return result


def restoration(commands, before, read_after):
    """Diagnostic evidence only: never retry instrumentation or mutate a setting."""
    output = commands.captured('canonical-instrumentation')
    result = {'raw': {'status': 'unavailable'}, 'effective': {'status': 'unavailable'},
              'instrumentationOutput': output, 'beforeCleanup': True,
              'instrumentationRetried': False, 'settingWrites': 0,
              'failureDiagnostics': {'output': output, 'appLog': commands.captured('app-logcat-before-startup')}}
    if commands.hold:
        result['reason'] = 'unknown custody; no further commands'
        return result
    if before is not None:
        try:
            commands.admissible()
            after = read_after()
            result['raw'] = {'status': 'verified' if before==after else 'unavailable',
                             'before': before, 'after': after, 'matched': before==after}
        except BaseException as error:
            result['raw']['reason'] = repr(error)
    if commands.hold:
        result['effective']['reason'] = 'unknown custody; no further commands'
        return result
    if 'INSTRUMENTATION_RESULT: motionEffectiveRestored=true' in output:
        result['effective'] = {'status': 'verified', 'evidence': 'unchanged instrumentation effective getter assertion'}
    else:
        result['effective']['reason'] = 'instrumentation effective restoration evidence absent'
    return result


def finish(commands, scratch, before, read_after, write_restoration):
    """Persist the diagnostic outcome before any final service cleanup."""
    try:
        report = restoration(commands, before, read_after)
    except BaseException as error:
        report = {'raw': {'status': 'unavailable'}, 'effective': {'status': 'unavailable'},
                  'reason': repr(error), 'beforeCleanup': True, 'instrumentationRetried': False}
    write_restoration(report)
    try:
        cleanup = commands.cleanup(scratch)
    except BaseException as error:
        cleanup = {'allTerminalCustody': False, 'scratchRemoved': False, 'cleanupError': repr(error)}
    return report, cleanup
