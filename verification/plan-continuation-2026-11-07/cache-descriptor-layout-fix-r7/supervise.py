"""Two one-use campaigns using only the accepted controller; UNKNOWN is sticky."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTROL = HERE.parent / 'native-custody-premise/cleanup_control.py'
CONTROL_SHA = '8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, x): p.write_text(json.dumps(x, indent=2, sort_keys=True) + '\n')
parser = argparse.ArgumentParser()
parser.add_argument('campaign', choices=['baseline', 'final'])
args = parser.parse_args()
if (HERE / 'HOLD.json').exists():
    raise RuntimeError('Inner or outer UNKNOWN: no further process operations')
if sha(CONTROL) != CONTROL_SHA:
    raise RuntimeError('Accepted controller changed')
if args.campaign == 'baseline':
    manifest = json.loads((HERE / 'baseline-sources.json').read_bytes())
    commands = [(mode + '-R5-baseline', flags + [str(HERE / 'baseline_context.py')])
                for mode, flags in [('normal', []), ('optimized', ['-O'])]]
    overall = 60
else:
    prior = json.loads((HERE / 'campaign-baseline/result.json').read_bytes())
    if not prior['all_passed'] or not prior['outer_cleanup']['allTerminalCustody']:
        raise RuntimeError('Baseline did not complete with expected counterexample and custody')
    manifest = json.loads((HERE / 'sources.json').read_bytes())
    commands = []
    # Both interpreter modes pass the pure guards before either real suite starts.
    for mode, flags in [('normal', []), ('optimized', ['-O'])]:
        commands.extend([
            (mode + '-descriptor-preflight', flags + [str(HERE / 'descriptor_preflight.py')]),
            (mode + '-scope-controls', flags + [str(HERE / 'test_scope.py')]),
            (mode + '-prior-guards', flags + [str(HERE / 'test_stdin_premise.py')]),
            (mode + '-fakes', flags + [str(HERE / 'fake_replay.py'), 'fake-' + mode,
                                      sha(HERE / 'sources.json'), manifest['tree_sha256']])])
    for mode, flags in [('normal', []), ('optimized', ['-O'])]:
        commands.append((mode + '-original36', flags + [str(HERE / 'test_original.py'), '-v']))
    overall = 180
for row in manifest['members']:
    if sha(HERE / row['path']) != row['sha256']:
        raise RuntimeError('Sealed source drift: ' + row['path'])
    if row['path'].endswith('.py'):
        compile((HERE / row['path']).read_bytes(), str(HERE / row['path']), 'exec')
# Creating this directory is the one-use claim. Never reuse an output.
destination = HERE / ('campaign-' + args.campaign)
destination.mkdir()
scratch = destination / 'scratch'
scratch.mkdir()
for row in manifest['members']:
    target = destination / 'executed-sources' / row['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((HERE / row['path']).read_bytes())
spec = importlib.util.spec_from_file_location('accepted_outer', CONTROL)
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)
start = time.monotonic()
active = overall - 10
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(scratch), TMP=str(scratch), TEMP=str(scratch))
controller = control.Commands(destination, env, deadline=start+overall,
                              output_bytes=8*1024*1024, total_output_bytes=64*1024*1024, cleanup_seconds=10)
save(destination / 'host.json', {
    'argv': sys.argv, 'python': sys.version, 'executable': sys.executable,
    'executable_sha256': sha(Path(sys.executable).resolve()), 'uname': list(os.uname()),
    'revision': json.loads((HERE / 'source-revision.json').read_bytes()),
    'manifest': manifest, 'controller_sha256': sha(CONTROL),
    'active_seconds': active, 'overall_seconds': overall, 'cleanup_seconds': 10,
    'output_cap_bytes': 8*1024*1024, 'aggregate_cap_bytes': 64*1024*1024,
    'planned_total_campaign_bound_seconds': 240, 'scope': 'Python controls only; no compiler/native/network'})
results = []
for label, arguments in commands:
    argv = [sys.executable, '-B', *arguments]
    try:
        controller.run(label, argv, ROOT, timeout=max(0, active-(time.monotonic()-start)), allowed=(0,1))
        results.append({'label': label, 'exit': controller.records[-1]['exit_code'], 'argv': argv})
    except BaseException as error:
        results.append({'label': label, 'error': repr(error), 'argv': argv})
    if controller.hold or (HERE / 'HOLD.json').exists():
        hold = {'outer': controller.hold, 'outer_records': controller.records,
                'outer_scratch': str(scratch), 'inner_hold_record': 'HOLD.json', 'no_further_operations': True}
        if controller.hold and not (HERE / 'HOLD.json').exists(): save(HERE / 'HOLD.json', hold)
        save(destination / 'result.json', {'all_passed': False, 'hold': hold, 'results': results})
        print(json.dumps({'UNKNOWN': True, 'campaign': args.campaign, 'hold': 'HOLD.json'}))
        sys.exit(2)
    if results[-1].get('exit') != 0:
        break
cleanup = controller.cleanup(scratch)
if controller.hold:
    save(HERE / 'HOLD.json', {'outer': controller.hold, 'records': controller.records, 'scratch': str(scratch)})
    print(json.dumps({'UNKNOWN': True, 'campaign': args.campaign, 'hold': 'HOLD.json'}))
    sys.exit(2)
unchanged = all(sha(HERE / row['path']) == row['sha256'] for row in manifest['members'])
passed = (len(results) == len(commands) and all(r.get('exit') == 0 for r in results)
          and cleanup['allTerminalCustody'] and cleanup['scratchRemoved'] and unchanged)
save(destination / 'result.json', {'all_passed': passed, 'results': results,
    'outer_cleanup': cleanup, 'unchanged': unchanged, 'elapsed_seconds': time.monotonic()-start})
print(json.dumps({'campaign': args.campaign, 'all_passed': passed, 'results': results, 'outer_cleanup': cleanup}))
sys.exit(0 if passed else 1)
