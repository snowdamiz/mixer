"""Recover only timed-out whole children using unchanged one-state legacy bodies.

The original failed streams remain failed. This produces separate host evidence
with an explicit additional driver/source/class closure, never a parent pass.
"""
from pathlib import Path
import argparse
import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time

S = Path(__file__).resolve().parent
Q = S.parent
R = Q.parents[1]
STATES = ('clean', 'terminal-at-entry', 'terminal-before-return', 'dirty-at-entry',
          'dirty-before-return', 'ordinary-throw-after-callback', 'fatal-throw-after-callback')


def ident(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--parent', required=True, type=Path)
    parser.add_argument('--label', required=True, nargs='+')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    parent = args.parent.resolve()
    out = args.output.resolve()
    assert parent.is_relative_to(S / 'full-candidate-v1') and not out.exists() and out.is_relative_to(S)
    assert len(args.label) == len(set(args.label)) and all(re.fullmatch('boundary-[0-9]{3}', name) for name in args.label)
    receipt = json.loads((parent / 'receipt.json').read_bytes())
    assert receipt['cleanup']['all_children_reaped'] and receipt['cleanup']['scratch_removed']
    assert not receipt['all_commands_passed'], 'only a retained failed parent is eligible'
    selected = {item['label']: item for item in receipt['commands'] if item['label'] in args.label}
    assert set(selected) == set(args.label) and all(item['timeout'] and item['reaped'] and item['timeout_seconds'] == 60 for item in selected.values())
    out.mkdir()
    commands = []
    status = 'failed'
    scratch = Path(tempfile.mkdtemp(prefix='owned-legacy-state-', dir=out))
    driver_classes = scratch / 'driver-classes'
    driver_classes.mkdir()
    empty = scratch / 'empty'
    empty.mkdir()
    temp = scratch / 'tmp'
    temp.mkdir()
    jdk = Path(json.loads((S / 'jdk17-download-receipt.json').read_bytes())['jdk_home'])
    env = {'PATH': str(jdk / 'bin') + ':/usr/bin:/bin', 'JAVA_HOME': str(jdk), 'LANG': 'en_US.UTF-8',
           'LC_ALL': 'en_US.UTF-8', 'TZ': 'UTC', 'TMPDIR': str(temp), 'TMP': str(temp), 'TEMP': str(temp)}
    classmap = json.loads((parent / 'class-map.json').read_bytes())
    freeze = json.loads((parent / 'source-freeze.json').read_bytes())

    def verify_inputs():
        nodes = list((parent / 'classes').rglob('*'))
        assert not any(path.is_symlink() for path in nodes)
        assert {str(path.relative_to(parent / 'classes')) for path in nodes if path.is_file()} == set(classmap)
        for relative, expected in classmap.items():
            assert ident(parent / 'classes' / relative) == expected
        for name, expected in freeze['tools'].items():
            assert ident(jdk / name) == expected
        for item in freeze['sources']:
            original = R / item['path']
            actual = parent / original.name if original.parent.name == 'full-candidate-v1' else original
            assert ident(actual) == {key: item[key] for key in ('bytes', 'sha256')}

    def run(label, argv):
        started = time.monotonic()
        with (out / (label + '.stdout')).open('wb') as stdout, (out / (label + '.stderr')).open('wb') as stderr:
            child = subprocess.Popen([str(value) for value in argv], cwd=R, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            timed_out = False
            try:
                child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            except BaseException:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                raise
        command = {'label': label, 'argv': [str(value) for value in argv], 'exit': child.returncode,
                   'timeout': timed_out, 'timeout_seconds': 60, 'elapsed_seconds': time.monotonic() - started,
                   'reaped': True, 'stdout': ident(out / (label + '.stdout')), 'stderr': ident(out / (label + '.stderr'))}
        commands.append(command)
        save(out / 'commands.json', commands)
        print(label, 'exit', child.returncode, flush=True)
        assert child.returncode == 0 and not timed_out, label

    try:
        signal.alarm(60)
        verify_inputs()
        source = S / 'full-candidate-v1/LegacyBoundarySingleState.java'
        shutil.copyfile(source, out / source.name)
        shutil.copyfile(__file__, out / 'runner.py')
        save(out / 'parent-reference.json', {'parent': str(parent.relative_to(R)), 'receipt': ident(parent / 'receipt.json'),
              'class_map': ident(parent / 'class-map.json'), 'source_freeze': ident(parent / 'source-freeze.json'),
              'failed_children': selected, 'partial_failed_streams_admitted': False})
        signal.alarm(0)
        run('java-version', [jdk / 'bin/java', '-version'])
        run('javac-version', [jdk / 'bin/javac', '-version'])
        run('compile-single-state-driver', [jdk / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-proc:none',
             '-classpath', parent / 'classes', '-sourcepath', empty, '-d', driver_classes, out / source.name])
        driver_map = {str(path.relative_to(driver_classes)): ident(path) for path in sorted(driver_classes.rglob('*.class'))}
        assert set(driver_map) == {'dev/mixer/android/LegacyBoundarySingleState.class'} and not set(driver_map) & set(classmap)
        shutil.copytree(driver_classes, out / 'driver-classes')
        save(out / 'driver-class-map.json', driver_map)
        save(out / 'execution-closure.json', {'schema': 1, 'product_context_id': freeze['product_context_id'],
             'parent_class_map': classmap, 'additional_driver_class_map': driver_map,
             'driver_source': ident(out / source.name), 'recovery_runner': ident(out / 'runner.py'),
             'original_source_freeze': ident(parent / 'source-freeze.json'), 'tools': freeze['tools'],
             'environment': env, 'classpath_order': ['driver-classes', str(parent / 'classes')],
             'scope': 'Additional bounded host driver plus unchanged exact original compiled classes; no execution/runtime closure admission'})
        classpath = str(driver_classes) + ':' + str(parent / 'classes')
        for label in args.label:
            binding = parent / (label + '.binding.json')
            item = json.loads(binding.read_bytes())['records'][0]
            shutil.copyfile(binding, out / binding.name)
            for state in STATES:
                run(label + '-' + state, [jdk / 'bin/java', '-Djava.io.tmpdir=' + str(temp), '-ea', '-Xmx512m', '-cp', classpath,
                    'dev.mixer.android.LegacyBoundarySingleState', Q / 'passive-return-probe-v4/descriptor.json',
                    out / binding.name, item['historical_id'], state, out / (label + '-' + state + '.rows.jsonl.gz')])
                with gzip.open(out / (label + '-' + state + '.rows.jsonl.gz'), 'rt') as stream:
                    rows = [json.loads(line) for line in stream]
                assert len(rows) == 1 and rows[0]['historical_id'] == item['historical_id'] and rows[0]['state'] == state
        signal.alarm(60)
        verify_inputs()
        assert {str(path.relative_to(out / 'driver-classes')): ident(path) for path in (out / 'driver-classes').rglob('*.class')} == driver_map
        signal.alarm(0)
        status = 'passed-unchanged-body-single-state-recovery'
    finally:
        signal.alarm(0)
        shutil.rmtree(scratch)
        save(out / 'receipt.json', {'status': status, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'commands': commands, 'all_commands_passed': status == 'passed-unchanged-body-single-state-recovery',
             'all_children_reaped': all(item['reaped'] for item in commands), 'scratch_removed': not scratch.exists(),
             'failed_parent_promoted': False, 'original_scenario_and_assertion_bodies_changed': False,
             'full_matrix_execution_closure_native_OTA_GA_accepted': False})


if __name__ == '__main__':
    main()
