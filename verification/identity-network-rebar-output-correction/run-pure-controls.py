#!/usr/bin/env python3
"""Audited pure controls only: no children, sockets, private files or proc probes."""
from pathlib import Path
import contextlib, hashlib, json, os, runpy, signal, sys, tempfile, time
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
label = sys.argv[1]
assert label in {'baseline', 'corrected', 'corrected-final'}
allowed_reads = [str(ROOT) + os.sep, str(Path(sys.base_prefix)) + os.sep,
                 str(Path(tempfile.gettempdir())) + os.sep]
for p in sys.path:
    if p and ('python' in p or p.endswith('.zip')):
        allowed_reads.append(str(Path(p).absolute()))
blocked = []
counts = {'audit_events': 0, 'opens': 0}
process = {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.posix_spawnp',
           'os.fork', 'os.forkpty', 'os.exec', 'pty.spawn', 'ctypes.dlopen'}
def audit(event, args):
    counts['audit_events'] += 1
    if event in process or event.startswith('socket.'):
        blocked.append({'event': event})
        raise RuntimeError('execution denied by pure control audit: ' + event)
    if event == 'open' and isinstance(args[0], (str, bytes)):
        counts['opens'] += 1
        p = os.fsdecode(args[0]); absolute = os.path.abspath(p)
        sensitive = ('/.ssh/', '/.aws/', '/.config/', '/FieldLog/')
        if absolute.startswith(('/proc/', '/dev/')) or any(s in absolute for s in sensitive) or not any(absolute.startswith(p) for p in allowed_reads):
            blocked.append({'event': event, 'path': absolute})
            raise RuntimeError('file custody denied by pure control audit')
sys.addaudithook(audit)
# Probe the denial hook by emitting audit events, never by invoking the OS action.
for event in ('subprocess.Popen', 'socket.__new__', 'os.system'):
    try: sys.audit(event)
    except RuntimeError: pass
    else: raise AssertionError('missing audit refusal')
for path in ('/proc/20745/status', '/private/FieldLog/secret'):
    try: sys.audit('open', path, 'r', 0)
    except RuntimeError: pass
    else: raise AssertionError('missing custody refusal')
probe_denials = blocked[:]; blocked.clear()
signal.alarm(50)
started = time.monotonic(); result = 0
sys.argv = ['hosted/scripts/test_identity_network_collector.py']
with (BASE / (label + '.stdout')).open('w') as stdout, (BASE / (label + '.stderr')).open('w') as stderr:
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try: runpy.run_path(str(ROOT / sys.argv[0]), run_name='__main__')
        except SystemExit as error: result = error.code or 0
signal.alarm(0)
receipt = {'schema':1, 'argv':['python3','-B',str(Path(__file__).relative_to(ROOT)),label],
 'subject_argv':['python3','-B','hosted/scripts/test_identity_network_collector.py'],
 'python':sys.version,'alarm_seconds':50,'seconds':round(time.monotonic()-started,3),
 'exit_code':result, 'denial_hook_self_tests':probe_denials, 'unexpected_denials':blocked,
 'counts':counts, 'scope':'pure host controls; no child/socket/compiler/runtime qualification'}
(BASE / (label + '-run.json')).write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,sort_keys=True))
assert not blocked
raise SystemExit(result)
