"""Root checks for the exact source-bound runner; no native commands here."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUNNER = ROOT / 'verification/android-authored-toggle-input-runner'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
bind = lambda p: {'bytes': p.stat().st_size, 'sha256': sha(p)}

def main():
    assert not (HERE / 'selection.json').exists()
    assert sha(RUNNER / 'packet-seal.json') == 'c76e70a6d2023aa09f3206b6fe8826983abb354bbad9417ee651f05037f052cc'
    assert sha(RUNNER / 'runner-contract.json') == '9af8a190a294d31cf946b90053709c6a4a363e241ceb5ff3a4d389b687fdad61'
    seal = read(RUNNER / 'packet-seal.json')
    for name, expected in seal['files'].items():
        assert bind(ROOT / name) == expected, name
    helper = ROOT / 'verification/android-coordinator-runner-cleanup/owned_process.py'
    assert sha(helper) == '209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216'
    spec = importlib.util.spec_from_file_location('root_authored_owned', helper)
    owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
    work = Path(tempfile.mkdtemp(prefix='mixer-authored-runner-root-')); identity = work.stat()
    commands = []
    def run(label, argv, allowed=(0,)):
        result = owned.execute(list(map(str, argv)), cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), timeout=180)
        log = HERE / (label + '.log'); log.write_bytes(result.stdout)
        commands.append({'label': label, 'argv': list(map(str, argv)), 'exitCode': result.returncode,
                         'output': log.name, **bind(log), 'groupCleanup': result.groupCleanup})
        assert result.returncode in allowed, label
        assert not result.groupCleanup['after'], label
        return result.stdout
    try:
        run('runner-replay', [sys.executable, '-B', RUNNER / 'verify.py'])
        run('root-host-controls', [sys.executable, '-B', RUNNER / 'test_host.py', '--work', work / 'tests', '--results', work / 'results.json'])
        result = read(work / 'results.json')
        assert result['status'] == 'passed' and result['tests'] == 23 and result['nativeCommands'] == 0
        shutil.copyfile(work / 'results.json', HERE / 'root-host-results.json')
    finally:
        holders = run('scratch-holders', ['lsof', '-nP', '+D', work], (1,)); assert not holders
        assert not work.is_symlink() and (work.stat().st_dev, work.stat().st_ino) == (identity.st_dev, identity.st_ino)
        files = [p for p in work.rglob('*') if p.is_file() and not p.is_symlink()]
        cleanup = {'files': len(files), 'bytes': sum(p.stat().st_size for p in files), 'path': str(work),
                   'device': identity.st_dev, 'inode': identity.st_ino, 'groupsEmpty': all(not c['groupCleanup']['after'] for c in commands)}
        shutil.rmtree(work); cleanup['removed'] = not work.exists()
        (HERE / 'preflight.json').write_text(json.dumps({'commands': commands, 'cleanup': cleanup}, indent=2) + '\n')
    assert bind(RUNNER / 'packet-seal.json')['sha256'] == 'c76e70a6d2023aa09f3206b6fe8826983abb354bbad9417ee651f05037f052cc'
    bindings = dict(seal['files']); bindings[str((RUNNER / 'packet-seal.json').relative_to(ROOT))] = bind(RUNNER / 'packet-seal.json')
    for name in ['select_runner.py', 'preflight.json', 'root-host-results.json'] + [c['output'] for c in commands]:
        bindings[str((HERE / name).relative_to(ROOT))] = bind(HERE / name)
    selection = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'bindings': bindings, 'runnerFiles': len(seal['files']), 'rootHostControls': 23,
                 'candidate': 'candidate-3', 'supplement': 'supplement-3',
                 'candidateSourceClosure': '509ef6a00bbaf034ebbe9dd6d8d3b8716fe96d9600e7fe8fa92fac41ebca3f99',
                 'baselineNativeRunAuthorized': True, 'supplementNativeRunAuthorized': 'after baseline result and complete owned cleanup review',
                 'productIntegrated': False, 'nativeAccepted': False, 'gaAccepted': False,
                 'scope': 'Explicit new runner with original20-action authority/timing oracle, finite component-only supplement, fresh root controls and sealed source/build/cleanup bindings. No native result yet.',
                 'review': ['Exact finite derivation preserves baseline injection/export validation and cleanup.',
                            'Changed3production source authority is separate from88live baseline input checks.',
                            'One owned read-only API37 emulator per invocation; physical discovery absent.',
                            'Component45cases, counted events plus one constructed history event, direct View vs18worker requests explicit.',
                            'Component proposals and fixture acknowledgements never imply engine commits.',
                            'Ancestor import aliases restored through entire load; repeated imports tested.',
                            'Four component screenshot pixels require later root inspection.']}
    (HERE / 'selection.json').write_text(json.dumps(selection, indent=2) + '\n')
    print(json.dumps({'selected': True, 'runnerFiles': len(seal['files']), 'rootHostControls': 23, 'baselineNativeRunAuthorized': True, 'nativeAccepted': False}))

if __name__ == '__main__':
    main()
