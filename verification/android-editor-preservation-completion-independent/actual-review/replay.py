#!/usr/bin/env python3
"""Independent explicit source replay; no producer generator/harness execution."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

D = Path(__file__).resolve().parent
F = D / 'frozen'
mode = sys.argv[1]
assert mode in ('host', 'cross', 'controls', 'witness')
number = 1
while (D / f'{mode}-{number}').exists(): number += 1
R = D / f'{mode}-{number}'
R.mkdir()
J = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK = Path('/opt/homebrew/share/android-commandlinetools')
jar = SDK / 'platforms/android-37.0/android.jar'
d8 = SDK / 'build-tools/37.0.0/d8'
scratch = R / 'owned-scratch'
scratch.mkdir()
empty = scratch / 'empty-source'
empty.mkdir()
temp = scratch / 'tmp'
temp.mkdir()
classes = R / 'classes'
classes.mkdir()
env = {key: value for key, value in os.environ.items() if key not in {
    'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS', 'CLASSPATH',
    'JAVA_OPTIONS', 'JAVA_OPTS', 'JDK_JAVAC_OPTIONS'}}
env.update({'JAVA_HOME': str(J), 'PATH': str(J / 'bin') + os.pathsep + env.get('PATH', ''),
            'TMPDIR': str(temp), 'TMP': str(temp), 'TEMP': str(temp)})
commands = []
status = 'failed'

def ident(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def run(name, argv, expected=0):
    argv = [str(item) for item in argv]
    item = {'name': name, 'argv': argv, 'timeout_seconds': 60, 'expected_exit': expected}
    commands.append(item)
    start = time.monotonic()
    with (R / (name + '.stdout')).open('wb') as out, (R / (name + '.stderr')).open('wb') as err:
        child = subprocess.Popen(argv, cwd=D, env=env, stdout=out, stderr=err, start_new_session=True)
        try: child.wait(timeout=60)
        except BaseException:
            child.kill(); child.wait(); raise
        finally:
            item.update({'exit': child.returncode, 'elapsed_seconds': time.monotonic() - start,
                         'reaped': child.poll() is not None,
                         'stdout': ident(R / (name + '.stdout')), 'stderr': ident(R / (name + '.stderr'))})
            (R / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    print(name + ': ' + str(child.returncode) + ' ' + (R / (name + '.stdout')).read_text()[-1300:].strip(), flush=True)
    if child.returncode != expected: raise RuntimeError(name + ' unexpected exit; inspect retained stdout/stderr')

def case(prefix, main, selected):
    run(prefix + selected, [J / 'bin/java', '-Djava.io.tmpdir=' + str(temp), '-ea', '-Xmx256m', '-cp', classes, main, selected, F / 'descriptor.json'])

try:
    source_map = {str(path.relative_to(F)): ident(path) for path in sorted(F.rglob('*')) if path.is_file()}
    own_sources = {str(path.relative_to(D)): ident(path) for path in sorted((D / 'controls').glob('*.java'))}
    shutil.copytree(D / 'controls', R / 'control-source')
    (R / 'input-map.json').write_text(json.dumps({'frozen': source_map, 'controls': own_sources}, indent=2) + '\n')
    run('javac-version', [J / 'bin/javac', '-version'])
    run('java-version', [J / 'bin/java', '-version'])
    sources = sorted((F / 'source').glob('*.java'))
    if mode == 'cross': sources += [F / 'cross-source/NativeBridge.java']
    elif mode == 'host': sources += sorted((F / 'host-leaves').rglob('*.java')) + sorted((F / 'tests').glob('*.java'))
    elif mode == 'controls': sources = sorted((R / 'control-source').glob('Independent*.java'))
    else: sources = [R / 'control-source/FocusHistoryControls.java']
    cp = jar if mode == 'cross' else empty if mode == 'host' else D / 'host-1/classes'
    run('compile', [J / 'bin/javac', '-J-Djava.io.tmpdir=' + str(temp), '--release', '17', '-Xlint:all', '-Werror', '-proc:none', '-sourcepath', empty, '-classpath', cp, '-d', classes, *sources])
    if mode in ('controls', 'witness'):
        # Each selected control runs with its own classes before the complete product classes.
        classes = str(classes) + os.pathsep + str(cp)
        for selected in sys.argv[2:]: case('independent-', 'dev.mixer.android.IndependentPreservationCompletionControls' if mode == 'controls' else 'dev.mixer.android.FocusHistoryControls', selected)
    elif mode == 'host':
        run('producer-52', [J / 'bin/java', '-Djava.io.tmpdir=' + str(temp), '-ea', '-Xmx256m', '-cp', classes, 'dev.mixer.android.EditorImplementationTests', F / 'descriptor.json'])
        for selected in ('admission-order', 'positive-values', 'foreign-dispatch', 'selection-postevent', 'annotation-mutable-bundle', 'snapshot-reservation'):
            case('prepared-', 'dev.mixer.android.ReplacementReviewControls', selected)
        for selected in ('final-balance', 'tuple-after-getter', 'captured-target', 'blurred-A-replacement', 'focused-B-echo-after-A-blur'):
            case('additional-', 'dev.mixer.android.AdditionalReplacementControls', selected)
        run('descriptors-38', [J / 'bin/java', '-Djava.io.tmpdir=' + str(temp), '-ea', '-cp', classes, 'DescriptorClosure', 'dev.mixer.android.NativeEditorConnectionV2$Api34'])
        for selected in ('positive-history', 'entry-loss', 'stage-loss', 'other-denials', 'marker-exhaustion', 'preservation-callback', 'first-fatal-busy', 'restoration', 'live-exhaustion', 'event-reentry', 'multiple-preservations', 'preservation-balance-fatal', 'scope-custody'):
            case('focus-', 'dev.mixer.android.FocusHistoryControls', selected)
        for selected in ('prior-focus-values', 'coexistence', 'eligible-restore', 'lost-original-restore', 'foreign-token-restore', 'loss-phases', 'settled-loss-phases', 'observed-hooks', 'event-reentry', 'event-postgetter', 'scope-imbalance', 'exhaustion', 'post-attach-rollback', 'cross-renderer-end'):
            case('prior-independent-', 'dev.mixer.android.IndependentFocusHistoryControls', selected)
        for selected in ('multiple-with-active-B', 'event-provenance'):
            case('prior-audit-', 'dev.mixer.android.IndependentAdditionalFocusAuditControls', selected)
        for selected in ('outcomes', 'refresh', 'no-scopes', 'partial-entry', 'partial-release', 'chronology', 'foreign-endpoints', 'terminal-end', 'imbalances', 'getter-loss', 'begin-accounting', 'precommit-refusals'):
            case('producer-completion-', 'dev.mixer.android.PreservationCompletionControls', selected)
    else:
        run('d8-version', [d8, '--version'])
        run('sdk-descriptors', [J / 'bin/javap', '-p', '-s', '-classpath', jar, 'android.view.inputmethod.InputConnection'])
        dex = R / 'dex'
        dex.mkdir()
        run('d8', [d8, '--min-api', '28', '--lib', jar, '--output', dex, *sorted(classes.rglob('*.class'))])
        (R / 'dex-map.json').write_text(json.dumps({str(path.relative_to(dex)): ident(path) for path in sorted(dex.rglob('*')) if path.is_file()}, indent=2) + '\n')
    assert source_map == {str(path.relative_to(F)): ident(path) for path in sorted(F.rglob('*')) if path.is_file()}
    status = 'passed-' + mode + '-only'
finally:
    shutil.rmtree(scratch)
    class_dir = R / 'classes'
    (R / 'class-map.json').write_text(json.dumps({str(path.relative_to(class_dir)): ident(path) for path in sorted(class_dir.rglob('*.class'))}, indent=2) + '\n')
    (R / 'receipt.json').write_text(json.dumps({'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': status,
        'scope': 'Independently copied complete source + controlled host Android/JNI leaves' if mode != 'cross' else 'Unsigned SDK37 Java/D8 min-api28 compile only',
        'input_map': ident(R / 'input-map.json'), 'commands': commands,
        'tools': {str(path): ident(path.resolve()) for path in (J / 'bin/javac', J / 'bin/java', J / 'bin/javap', J / 'lib/modules', J / 'lib/server/libjvm.dylib', jar, d8, d8.parent / 'lib/d8.jar')},
        'cleanup': {'children_reaped': all(item['reaped'] for item in commands), 'scratch_tmp_removed': not scratch.exists(), 'native_UI_capture_process_inventory': False}}, indent=2) + '\n')
    print(status, str(R), flush=True)
