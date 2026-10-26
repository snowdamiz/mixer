#!/usr/bin/env python3
"""Bounded compile and fixture check against the full frozen PRIOR source only."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import time

D = Path(__file__).resolve().parent
R = D / 'old-source-check-1'
R.mkdir(exist_ok=False)
J = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
S = D / 'inputs/old-source-only'
scratch = R / 'owned-scratch'
scratch.mkdir()
empty = scratch / 'empty-source'
empty.mkdir()
base = R / 'old-source-classes'
base.mkdir()
controls = R / 'prospective-control-classes'
controls.mkdir()
witness = R / 'unchanged-witness-classes'
witness.mkdir()
env = {key: value for key, value in os.environ.items() if key not in {
    'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS', 'CLASSPATH',
    'JAVA_OPTIONS', 'JAVA_OPTS', 'JDK_JAVAC_OPTIONS'}}
env['JAVA_HOME'] = str(J.parent)
commands = []
status = 'incomplete'

def ident(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def run(name, arguments, expected=0):
    arguments = [str(item) for item in arguments]
    item = {'name': name, 'argv': arguments, 'timeout_seconds': 60,
            'expected_exit': expected, 'cwd': str(D)}
    commands.append(item)
    started = time.monotonic()
    with (R / (name + '.stdout')).open('wb') as out, (R / (name + '.stderr')).open('wb') as err:
        child = subprocess.Popen(arguments, cwd=D, env=env, stdout=out, stderr=err,
                                 start_new_session=True)
        try:
            child.wait(timeout=60)
        except BaseException:
            child.kill()
            child.wait()
            raise
        finally:
            item['reaped'] = child.poll() is not None
            item['exit_code'] = child.returncode
            item['elapsed_seconds'] = time.monotonic() - started
            item['stdout'] = ident(R / (name + '.stdout'))
            item['stderr'] = ident(R / (name + '.stderr'))
            (R / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    print(name, child.returncode, (R / (name + '.stdout')).read_text()[-1600:].strip(), flush=True)
    if child.returncode != expected:
        raise RuntimeError(f'{name}: exit {child.returncode}, expected {expected}; inspect retained raw stderr')

def compile_to(output, classpath, sources, name):
    run(name, [J / 'javac', '--release', '17', '-Xlint:all', '-Werror', '-proc:none',
               '-sourcepath', empty, '-classpath', classpath, '-d', output, *sources])

try:
    source_map = {str(path.relative_to(S)): ident(path) for path in sorted(S.rglob('*')) if path.is_file()}
    (R / 'old-source-map.json').write_text(json.dumps(source_map, indent=2) + '\n')
    run('javac-version', [J / 'javac', '-version'])
    run('java-version', [J / 'java', '-version'])
    compile_to(base, empty, sorted((S / 'source').glob('*.java')) +
               sorted((S / 'host-leaves').rglob('*.java')) + sorted((S / 'tests').glob('*.java')),
               'complete-prior-closure-compile')
    compile_to(controls, base, [D / 'PreservationCompletionControls.java'], 'prospective-controls-typecheck')
    compile_to(witness, base, [D / 'inputs/unchanged-witnesses/FocusHistoryControls.java'], 'unchanged-witness-typecheck')
    desc = S / 'descriptor.json'
    run('old-source-fixture-smoke', [J / 'java', '-ea', '-Xmx256m', '-cp', str(controls) + os.pathsep + str(base),
                                    'dev.mixer.android.PreservationCompletionControls', 'fixture-smoke', desc])
    for case in ('post-attach-rollback', 'cross-renderer-end'):
        run('old-source-' + case, [J / 'java', '-ea', '-Xmx256m', '-cp', str(witness) + os.pathsep + str(base),
                                  'dev.mixer.android.FocusHistoryControls', case, desc], expected=1)
    status = 'passed-typecheck-and-old-source-baseline-only'
finally:
    shutil.rmtree(scratch)
    source_files = [D / 'PreservationCompletionControls.java', D / 'inputs/unchanged-witnesses/FocusHistoryControls.java']
    receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': status,
               'scope': 'Only complete frozen prior source, unchanged authored host leaves, independently authored prospective controls; NO selected-candidate access or execution',
               'old_product_seal_sha256': '2ebf7634886be778b06ecdfa0ab2a9ac69d14a473b88a7f6ea623ccddfcd5af8',
               'old_product_tree_digest': '2d0a89dac0c629b7257a75dfa42dee3794f021c558300f968fc4d8baaaecba01',
               'commands': commands, 'tools': {str(path): ident(path.resolve()) for path in (J / 'javac', J / 'java')},
               'control_sources': {str(path.relative_to(D)): ident(path) for path in source_files},
               'source_map': ident(R / 'old-source-map.json'),
               'environment': {'removed_java_injection_variables': True, 'pinned_java_home': str(J.parent)},
               'cleanup': {'all_children_reaped': all(item['reaped'] for item in commands),
                           'scratch_removed': not scratch.exists(), 'native_UI_capture_process_inventory': False},
               'selected_candidate_tests_pending': True, 'native_OTA_GA_accepted': False}
    (R / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(status, flush=True)
