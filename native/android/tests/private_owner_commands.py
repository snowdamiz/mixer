"""Controlled commands for JVM tests; accepted custodian is copied without edits."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

CUSTODIAN_SHA256 = '8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
CONTROL = Path(__file__).with_name('private_owner_cleanup_control.py')
if hashlib.sha256(CONTROL.read_bytes()).hexdigest() != CUSTODIAN_SHA256:
    raise RuntimeError('test custodian changed')
_spec = importlib.util.spec_from_file_location('private_owner_cleanup_control', CONTROL)
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)
FACTS = ('direct_child_reaped', 'stdout_eof', 'stderr_eof', 'owned_group_absent', 'terminal_custody')

class ControlledCommands:
    def __init__(self, out, env, *, deadline):
        self.out = Path(out)
        self.commands = core.Commands(self.out, env, deadline=deadline,
            output_bytes=8*1024*1024, total_output_bytes=64*1024*1024, cleanup_seconds=60)

    def run(self, label, argv, cwd, timeout=60):
        if not 0 < timeout <= 300:
            raise ValueError('per-command deadline must be in (0,300] seconds')
        c = self.commands
        if c.hold or any(not all(r[k] for k in FACTS) for r in c.records):
            raise RuntimeError('unresolved previous command; admission closed')
        item = c.start(label, list(map(str, argv)), cwd)
        r = item['record']
        until = min(c.deadline-60, time.monotonic()+timeout)
        r['execution_deadline_monotonic'] = until
        r['requested_timeout_seconds'] = timeout
        interruption = None
        try:
            while not c.hold:
                if time.monotonic() >= until:
                    r['stop'] = 'timeout'
                    break
                c.pump(min(.02, max(0, until-time.monotonic())))
                if c.hold or c.limit:
                    break
                if c.reaped(item) and r['stdout_eof'] and r['stderr_eof']:
                    break
        except BaseException as error:
            r['execution_error'] = repr(error)
            if isinstance(error,(KeyboardInterrupt,SystemExit)):
                interruption = error
        finally:
            if not c.hold:
                c.stop(item)
            c.persist(item)
            if c.hold:
                self.write_hold()
        if interruption is not None:
            raise interruption
        if (c.hold or c.limit or not all(r[k] for k in FACTS) or r['stop'] or
                'execution_error' in r or r['exit_code'] != 0):
            raise RuntimeError(label+' failed: '+str(c.hold or c.limit or r['stop'] or r['exit_code']))
        return bytes(item['buffers']['stdout'])

    def write_hold(self):
        c = self.commands
        (self.out/'HOLD.json').write_text(json.dumps({
            'hold': c.hold, 'commands': str(self.out/'commands.json'),
            'policy': 'sticky UNKNOWN: retain all scratch; no further process operations or retry'
        }, indent=2)+'\n')

    def finish(self, scratch, *, retain_scratch=False):
        c = self.commands
        if retain_scratch:
            for item in reversed(c.owned):
                if c.hold:
                    break
                c.stop(item)
            for item in c.owned:
                c.persist(item)
            terminal = not c.hold and all(all(r[k] for k in FACTS) for r in c.records)
            if terminal:
                c.selector.close()
            result = {'allTerminalCustody':terminal,'hold':c.hold,'scratchRemoved':False,
                'scratchRetainedForInterruption':True,'aggregateBytes':c.used_output,'aggregateLimit':c.total_output_bytes}
        else:
            result = c.cleanup(scratch)
        if c.hold or not result['allTerminalCustody']:
            self.write_hold()
        return result
