#!/usr/bin/env python3
"""Compile the exact frozen product16/B87 roster and run finite identity controls only."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
ROOT = D.parent.parent
COHERENT = ROOT / 'verification/android-source-pair5-coherent-integration-preparation'
V1 = ROOT / 'verification/android-editor-membership-qualification-independent/v1-positive-preparation'
CHECKLIST = ROOT / 'verification/android-editor-membership-qualification-independent/semantic-applicability/applicability-checklist.json'
JDK = ROOT / 'verification/android-editor-membership-compiled-boundary-qualification/state-qualification/owned-tool-scratch/jdk-17.0.21+9/Contents/Home'
CONTEXT = '1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
SUBJECT_IDS = [
    'dev/mixer/android/NativeCoordinatorV2#remember(Ljava/lang/Throwable;)V',
    'dev/mixer/android/NativeEnvironmentV2$Observer#remember(Ljava/lang/Throwable;)V',
    'dev/mixer/android/NativeOwnerV2#remember(Ljava/lang/Throwable;)V',
]

def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')

def verified_packet(root, expected_seal):
    assert identity(root / 'seal.json')['sha256'] == expected_seal
    packet = json.loads((root / 'seal.json').read_bytes())
    for member in packet['members']:
        path = Path(member['path'])
        assert not path.is_absolute() and '..' not in path.parts
        assert identity(root / path) == {'bytes': member['bytes'], 'sha256': member['sha256']}, member
    return {'root': str(root.relative_to(ROOT)), 'seal': identity(root / 'seal.json'), 'verified_members': len(packet['members'])}

def main():
    runroot = D / 'run-1'
    runroot.mkdir()
    inputs = D / 'inputs'
    inputs.mkdir()
    scratch = runroot / 'scratch'
    scratch.mkdir()
    classes = scratch / 'classes'
    classes.mkdir()
    empty = scratch / 'empty'
    empty.mkdir()
    commands = []
    env = dict(os.environ)
    for key in ('_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH', 'JAVA_OPTS', 'JDK_JAVAC_OPTIONS'):
        env.pop(key, None)
    def run(name, argv):
        start = time.monotonic()
        stdout, stderr = runroot / (name + '.stdout'), runroot / (name + '.stderr')
        with stdout.open('wb') as out, stderr.open('wb') as err:
            child = subprocess.Popen([str(value) for value in argv], cwd=D, stdout=out, stderr=err,
                                     env=env, start_new_session=True)
            timeout = False
            try:
                child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                timeout = True
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        result = {'name': name, 'argv': [str(value) for value in argv], 'cwd': str(D),
                  'exit': child.returncode, 'timeout': timeout, 'reaped': True,
                  'elapsed_seconds': time.monotonic() - start,
                  'stdout': {'path': stdout.name, **identity(stdout)},
                  'stderr': {'path': stderr.name, **identity(stderr)}}
        commands.append(result)
        save(runroot / 'commands.json', commands)
        print(name, child.returncode, flush=True)
        assert child.returncode == 0 and not timeout, result
    try:
        packets = [
            verified_packet(COHERENT, '0dc913d88d4ee7d1e6583bdf00e1e407cc6b446ac7c7aaf6180a36a45b021e9b'),
            verified_packet(V1, 'd982305bafe8abcfc6945ea37ca8ff908aa748f00dfcad7e303517b327d74c8f'),
        ]
        reference = json.loads((V1 / 'run-1/bound-five-v1-proposal.json').read_bytes())
        source_map = reference['product_sources']
        class_map = reference['product_class_map']
        assert len(source_map) == 16 and len(class_map) == 209
        assert hashlib.sha256(json.dumps({'source_map': source_map, 'class_map': class_map}, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == CONTEXT
        for name, expected in class_map.items():
            assert identity(V1 / 'run-1/classes' / name) == expected
        save(inputs / 'selected-product-source-map.json', source_map)
        save(inputs / 'selected-product-class-map.json', class_map)
        original = json.loads(CHECKLIST.read_bytes())
        selected = [next(s for s in original['subjects'] if s['id'] == name) for name in SUBJECT_IDS]
        save(inputs / 'original-three-subjects.json', {'input': {'path': str(CHECKLIST.relative_to(ROOT)), **identity(CHECKLIST)}, 'subjects': selected})
        roster = []
        for name, expected in source_map.items():
            source = COHERENT / 'source/native/android/app/src/dev/mixer/android' / name
            assert identity(source) == expected
            target = inputs / 'product' / name
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, target)
            roster.append({'role': 'exact-product', 'origin': str(source.relative_to(ROOT)), 'path': str(target.relative_to(D)), **identity(target)})
        leaves = COHERENT / 'source/native/android/tests/NativeOwnerV2ConcreteHostLeaves'
        old = json.loads((V1 / 'run-1/source-and-tools.json').read_bytes())['sources']
        old_leaves = {row['path'].split('/host-leaves/', 1)[1]: {'bytes': row['bytes'], 'sha256': row['sha256']} for row in old if '/host-leaves/' in row['path']}
        assert len(old_leaves) == 87
        assert {path.relative_to(leaves).as_posix(): identity(path) for path in leaves.rglob('*.java')} == old_leaves
        for name, expected in sorted(old_leaves.items()):
            source = leaves / name
            target = inputs / 'host-leaves' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            assert identity(target) == expected
            roster.append({'role': 'exact-selected-B-leaf', 'origin': str(source.relative_to(ROOT)), 'path': str(target.relative_to(D)), **identity(target)})
        roster.append({'role': 'new-finite-identity-control', 'path': 'FiniteLedgerControls.java', **identity(D / 'FiniteLedgerControls.java')})
        save(inputs / 'source-roster.json', roster)
        save(inputs / 'provenance.json', {'packets': packets, 'source_revision_context': '6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2',
            'source_context': CONTEXT, 'full_product_sources': 16, 'selected_B_leaves': 87, 'product_classes_expected': 209,
            'tool_lease': str(JDK.relative_to(ROOT)), 'tool_lease_scope': 'producer-authorized whole JDK installation read/execute only',
            'runner': identity(Path(__file__)), 'python': sys.version, 'platform': platform.platform(),
            'tools': {name: identity(JDK / name) for name in ('bin/java', 'bin/javac', 'lib/modules', 'lib/server/libjvm.dylib')},
            'compiled_sources_unchanged': True, 'no_explicit_g_switch': True,
            'launch_command': [sys.executable, '-B', str(Path(__file__))]})
        run('java-version', [JDK / 'bin/java', '-version'])
        run('javac-version', [JDK / 'bin/javac', '-version'])
        sources = [D / row['path'] for row in roster]
        run('compile', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-proc:none',
                        '-sourcepath', empty, '-classpath', empty, '-d', classes, *sources])
        actual_map = {name: identity(classes / name) for name in class_map}
        assert actual_map == class_map, 'all 209 actual product class identities must match'
        actual_source_map = {name: identity(inputs / 'product' / name) for name in source_map}
        actual_context = hashlib.sha256(json.dumps({'source_map': actual_source_map, 'class_map': actual_map}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert actual_context == CONTEXT
        save(runroot / 'actual-product-class-map.json', actual_map)
        save(runroot / 'compile-identity.json', {'source_context': actual_context, 'exact_product_sources': 16, 'exact_product_classes': 209,
                                               'all_209_exact_matches': True, 'selected_B_leaves_exact_matches': 87})
        run('finite-ledger-controls', [JDK / 'bin/java', '-ea', '-Xmx256m', '-cp', classes,
                                      'dev.mixer.android.FiniteLedgerControls', runroot / 'actual-ledger-results.json'])
        result = json.loads((runroot / 'actual-ledger-results.json').read_bytes())
        assert result['invocations'] == 66 and len(result['rows']) == 66
        assert {row['subject_id'] for row in result['rows']} == set(SUBJECT_IDS)
        for subject in selected:
            rows = [row for row in result['rows'] if row['subject_id'] == subject['id']]
            assert len(rows) == 22
            assert all(row['class_sha256'] == subject['class_sha256'] for row in rows)
        shutil.copytree(classes, runroot / 'classes')
        save(runroot / 'receipt.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status': 'three-exact-finite-host-JVM-ledger-controls-passed-root-selection-pending',
            'source_revision_context': '6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2', 'source_context': actual_context,
            'source_roster': identity(inputs / 'source-roster.json'), 'control': identity(D / 'FiniteLedgerControls.java'),
            'actual_results': identity(runroot / 'actual-ledger-results.json'), 'invocations': result['invocations'],
            'checks': result['checks'], 'subjects': SUBJECT_IDS, 'environment': 'macOS host JVM17 with exact selected concrete B leaves; direct ordinary reflection invocation',
            'reflection_scope': 'private remember(Throwable) and finite field snapshots/seeding only; ordinary constructors; no product byte rewriting or special allocation',
            'native_runtime_device_UI_capture_or_process_inventory': False,
            'physical_or_native_cleanup_credit': False, 'security_or_interpreter_experiments': False,
            'enclosing_cleanup_exception_propagation_OTA_GA_or_final_matrix_accepted': False,
            'pending': ['Independent root semantic policy selection', 'Fresh final selected producer joins if these controls are selected',
                        'Actual enclosing cleanup/callback/reentrant/refusal/count/close and exception-propagation obligations',
                        'Native runtime and physical-device checks remain paused and pending']})
    finally:
        shutil.rmtree(scratch)
        save(runroot / 'cleanup.json', {'all_started_children_reaped': all(row['reaped'] for row in commands),
            'scratch_removed': not scratch.exists(), 'native_instances_started': 0, 'native_cleanup_credit': False,
            'UI_capture_process_inventory_or_other_projects_touched': False,
            'retained': 'explicit sources, exact emitted classes, raw commands/stdout/stderr, finite results; no child left running'})

if __name__ == '__main__':
    main()
