#!/usr/bin/env python3
"""Root source/evidence audit and host JVM decision replay; no Android runtime."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/android-native-v2-coordinator/candidate-3'
REVIEW = ROOT / 'verification/native-v2-transaction-independent-review'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    bindings = {}

    def bind(path, expected=None):
        actual = sha(path)
        assert expected is None or actual == expected, str(path)
        bindings[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)] = actual

    receipt = json.loads((REVIEW / 'coordinator-review-1/receipt.json').read_text())
    completion = json.loads((REVIEW / 'completion-coordinator-1.json').read_text())
    assert receipt['error'] is None and completion['sourceFindings'] == []
    assert completion['bindingChecks'] == 488
    assert not completion['nativeAcceptance'] and not completion['gaAcceptance']
    for name, expected in receipt['evidenceSHA256'].items():
        bind(ROOT / name, expected)
    for name, expected in completion['ownedDeliverablesSHA256'].items():
        bind(ROOT / name, expected)
    bind(REVIEW / 'completion-coordinator-1.json')
    source = json.loads((PRODUCER / 'source-lock.json').read_text())
    for name, expected in source['files'].items():
        bind(ROOT / name, expected)
        bind(PRODUCER / 'inputs' / name, expected)
    state = json.loads((ROOT / 'verification/android-native-v2-coordinator/state.json').read_text())
    assert source['treeSHA256'] == state['sourceTreeSHA256'] == completion['coordinator']['sourceClosureSHA256']
    expected_class = completion['coordinator']['executedCoordinatorClassSHA256']
    class_name = 'dev/mixer/android/NativeCoordinatorV2.class'
    bind(PRODUCER / 'production-classes' / class_name, expected_class)
    bind(PRODUCER / 'host-classes' / class_name, expected_class)
    java = '/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/java'
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix='mixer-root-coordinator-') as temporary:
        classes = Path(temporary) / 'classes'
        shutil.copytree(PRODUCER / 'host-classes', classes)
        bind(classes / class_name, expected_class)
        argv = [java, '-ea', '-Xverify:all',
                '-Xlog:class+load=info:file=' + str(HERE / 'class-load.log'),
                '-classpath', str(classes), 'dev.mixer.android.NativeCoordinatorV2HostTests']
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        (HERE / 'host.stdout').write_text(result.stdout)
        (HERE / 'host.stderr').write_text(result.stderr)
        assert result.returncode == 0, result.stderr
        assert result.stdout == (PRODUCER / 'production-bytecode-host-fault-matrix.log').read_text()
        assert 'scenarios=133 checks=2087' in result.stdout
        loaded = (HERE / 'class-load.log').read_text()
        for name in ['NativeCoordinatorV2', 'NativeRenderer', 'NativeBridge']:
            assert 'dev.mixer.android.' + name + ' source: ' + classes.as_uri() + '/' in loaded, name
    for file in ['host.stdout', 'host.stderr', 'class-load.log', 'review.py']:
        bind(HERE / file)
    acceptance = {
        'status': 'accepted-private-coordinator-host-decisions-and-cross-compilation',
        'reviewer': 'root integrator', 'pythonVersion': platform.python_version(),
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'sourceTreeSHA256': source['treeSHA256'],
        'sourceInputs': len(source['files']), 'bindings': bindings,
        'command': {'argv': argv, 'startedUTC': started, 'exitCode': result.returncode},
        'executedCoordinatorClassSHA256': expected_class,
        'hostScenarios': 133, 'hostChecks': 2087,
        'decision': 'Accept private concrete coordinator source and observed SDK/DEX/host decision scope; permit generated source export while keeping public V1 Activity unchanged.',
        'scope': 'Exact SDK-produced coordinator bytecode with explicit test-only JVM leaves. Joined actual JNI/Swift/native renderer and native input/IME/lifecycle remain unexecuted.',
        'privateNativeAPIFloor': 36, 'productionDEXMinAPI': 28,
        'nativeAcceptance': False, 'physicalAcceptance': False, 'gaAcceptance': False,
        'publicActivityOptIn': False, 'signedPresentation': False
    }
    (HERE / 'acceptance.json').write_text(json.dumps(acceptance, indent=2) + '\n')
    print(json.dumps({k: v for k, v in acceptance.items() if k not in ['bindings', 'command']}))


if __name__ == '__main__':
    main()
