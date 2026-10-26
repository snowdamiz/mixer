#!/usr/bin/env python3
"""Independent bounded method-shape validator controls; no implementation access."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
STAGE = HERE / 'preaccess-shape'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    before = json.loads((HERE / 'preaccess-receipt.json').read_text())
    assert before['active_implementation_candidate_reads'] == 0
    assert before['active_implementation_candidate_executions'] == 0
    STAGE.mkdir(exist_ok=True)
    recorded = []

    def command(label: str, argv: list[str], expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                                timeout=35, check=False)
        (STAGE / (label + '.stdout.txt')).write_text(result.stdout)
        (STAGE / (label + '.stderr.txt')).write_text(result.stderr)
        recorded.append({'label': label, 'argv': argv, 'exit': result.returncode,
                         'expected_exit': expected,
                         'stdout': 'preaccess-shape/' + label + '.stdout.txt',
                         'stderr': 'preaccess-shape/' + label + '.stderr.txt'})
        assert result.returncode == expected, (label, result.returncode, result.stderr)
        return result

    official = json.loads((HERE / 'inputs/verification/android-editor-api-boundary-proposal/official-inputs.json').read_text())
    jars = [row for row in official['installed'] if row['path'].endswith('/android.jar')]
    assert len(jars) == 2
    for row in jars:
        path = Path(row['path'])
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    command('javac-version', [str(JDK / 'bin/javac'), '-version'])
    command('java-version', [str(JDK / 'bin/java'), '-version'])
    classes = STAGE / 'classes'
    classes.mkdir(exist_ok=True)
    source = HERE / 'DescriptorClosure.java'
    command('compile-validator', [str(JDK / 'bin/javac'), '--release', '17',
            '-Xlint:all', '-Werror', '-sourcepath', '', '-d', str(classes), str(source)])
    for row in jars:
        sdk = Path(row['path']).parent.name
        result = command('official-' + sdk, [str(JDK / 'bin/java'), '-ea', '-cp',
                         str(classes) + ':' + row['path'], 'DescriptorClosure'])
        assert result.stdout.strip() == 'descriptor closure: 38; inspected adapters=[]'
    jar36 = next(row['path'] for row in jars if '/android-36/' in row['path'])
    incomplete = STAGE / 'incomplete-classes'
    incomplete.mkdir(exist_ok=True)
    old_input = HERE / 'inputs/native/android/tests/NativeOwnerV2ConcreteHostLeaves/android/view/inputmethod/InputConnection.java'
    command('compile-incomplete-control', [str(JDK / 'bin/javac'), '--release', '17',
            '-Xlint:all', '-Werror', '-sourcepath', '', '-cp', jar36,
            '-d', str(incomplete), str(old_input)])
    result = command('reject-incomplete-interface', [str(JDK / 'bin/java'), '-ea', '-cp',
                     str(classes) + ':' + str(incomplete) + ':' + jar36,
                     'DescriptorClosure'], expected=1)
    assert 'official-or-host InputConnection missing=' in result.stderr
    assert 'getSurroundingText' in result.stderr and 'takeSnapshot' in result.stderr
    result = command('reject-platform-wrapper', [str(JDK / 'bin/java'), '-ea', '-cp',
                     str(classes) + ':' + jar36, 'DescriptorClosure',
                     'android.view.inputmethod.InputConnectionWrapper'], expected=1)
    assert 'platform/default superclass in adapter chain' in result.stderr
    receipt = {
        'schema': 1, 'at': datetime.datetime.now(datetime.UTC).isoformat(),
        'argv': sys.argv, 'python': sys.version, 'platform': platform.platform(),
        'scope': 'Independent compiled shape-validator controls only; no editor implementation or Android runtime test',
        'preaccess_receipt_sha256': sha(HERE / 'preaccess-receipt.json'),
        'script_sha256': sha(Path(__file__)), 'validator_source_sha256': sha(source),
        'current_incomplete_host_interface_sha256': sha(old_input),
        'pinned_jars_verified': jars, 'commands': recorded,
        'passed': ['SDK36 official 38-descriptor baseline', 'SDK37 official 38-descriptor baseline',
                   'incomplete canonical host interface rejected', 'platform wrapper chain rejected'],
        'candidate_reads': 0, 'candidate_executions': 0,
        'native_runtime_capture_ui_or_process_inventory': False,
        'cleanup': 'All exact owned JVM/javac children exited within 35-second bounds; class files retained as host evidence; no native/capture instance started',
        'limitations': ['No actual adapter inspected', 'No method permission behavior executed',
                        'No Android/ART/runtime/native batch/service evidence'],
    }
    (HERE / 'preaccess-shape-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'controls': 4, 'candidate_reads': 0, 'candidate_executions': 0,
                      'scope': receipt['scope']}))


if __name__ == '__main__':
    main()
