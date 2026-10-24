#!/usr/bin/env python3
"""Root-only exact integration after a separately pinned independent review."""
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = ROOT / 'verification/swift-bulk-memory'
REVIEW = ROOT / 'verification/swift-bulk-memory-review'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def save(name, value):
    (HERE / name).write_bytes(encoded(value))

def source():
    vm = ROOT / 'vm'
    paths = [vm / 'Cargo.toml', vm / 'Cargo.lock']
    paths += [p for name in ['src', 'tests', 'include'] for p in (vm / name).rglob('*') if p.is_file()]
    return {str(p.relative_to(vm)): sha(p.read_bytes()) for p in paths}

def main():
    selected = json.loads((HERE / 'review-selection.json').read_text())
    assert selected['rootSelectedForIntegration'] is True
    assert not (HERE / 'integration.json').exists(), 'one-time collector; preserve failed attempts'
    assert sha((REVIEW / 'receipt.json').read_bytes()) == selected['reviewReceiptSHA256']
    assert sha((CANDIDATE / 'receipt.json').read_bytes()) == selected['producerReceiptSHA256']
    baseline = json.loads((CANDIDATE / 'baseline-source-manifest.json').read_text())
    reviewed = json.loads((CANDIDATE / 'candidate-source-manifest.json').read_text())
    expected = json.loads((HERE / 'expected-source-manifest.json').read_text())
    assert source() == baseline, 'live VM drift; no overwrite'
    assert sha(encoded(reviewed)) == selected['candidateSourceClosure']
    assert sha(encoded(expected)) == selected['integratedSourceClosure']
    commands, applied = [], []
    scratch = None
    status = 'failed'
    env = {**os.environ, 'PATH': '/opt/homebrew/opt/rustup/bin:' + os.environ['PATH']}
    for key in ['RUSTFLAGS', 'RUSTC_BOOTSTRAP']:
        env.pop(key, None)

    def run(label, argv, cwd=ROOT, tests=None):
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True)
        output = result.stdout + result.stderr
        (HERE / (label + '.log')).write_bytes(output)
        commands.append({'label': label, 'argv': argv, 'cwd': str(cwd), 'startedUTC': started,
                         'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'exitCode': result.returncode, 'log': label + '.log', 'sha256': sha(output),
                         'sourceDigest': sha(encoded(source()))})
        save('commands.json', commands)
        assert result.returncode == 0, (label, result.returncode)
        if tests is not None:
            assert f'test result: ok. {tests} passed; 0 failed; 0 ignored;' in output.decode(), label
        print(label + ' passed', flush=True)

    try:
        run('producer-integrity', ['python3', '-B', str(CANDIDATE / 'verify.py'), '--live-baseline'])
        run('review-integrity', ['python3', '-B', str(REVIEW / 'verify.py'), '--live-baseline'])
        with tarfile.open(CANDIDATE / 'candidate-source.tar.gz') as archive:
            members = archive.getmembers()
            assert len(members) == len(expected) == 125
            assert all(m.isfile() and not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts for m in members)
            bodies = {m.name: archive.extractfile(m).read() for m in members}
        assert {name: sha(body) for name, body in bodies.items()} == reviewed
        name = 'src/experimental/execution/mod.rs'
        lines = bodies[name].splitlines(keepends=True)
        assert lines[1049] == lines[1050] == b'    \n'
        lines[1049] = lines[1050] = b'\n'
        bodies[name] = b''.join(lines)
        assert {name: sha(body) for name, body in bodies.items()} == expected
        changed = [name for name in expected if expected[name] != baseline.get(name)]
        assert len(changed) == 9 and not (set(baseline) - set(expected))
        assert changed == selected['changedRelativeFiles']
        for name in changed:
            target = ROOT / 'vm' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bodies[name])
            applied.append('vm/' + name)
        assert source() == expected
        save('integrated-source-manifest.json', source())
        scratch = Path(tempfile.mkdtemp(prefix='mixer-bulk-root-', dir='/private/tmp'))
        env['CARGO_TARGET_DIR'] = str(scratch / 'target')
        run('rustc-version', ['rustc', '--version', '--verbose'])
        run('cargo-version', ['cargo', '--version'])
        run('host-version', ['uname', '-a'])
        run('integrated-bulk-memory-frame-value-control', ['cargo', 'test', '--lib', '--locked', '--offline', '--all-features', '--release', 'experimental_swift_reactor::execution::', '--', '--nocapture', '--test-threads=1'], ROOT / 'vm', 78)
        run('integrated-frozen', ['cargo', 'test', '--test', 'span_execution', '--locked', '--offline', '--all-features', '--release', '--', '--nocapture', '--test-threads=1'], ROOT / 'vm', 16)
        run('integrated-ci-swift-clippy', ['cargo', 'clippy', '--locked', '--offline', '--lib', '--features', 'experimental-swift-reactor', '--', '-D', 'warnings'], ROOT / 'vm')
        run('integrated-whitespace', ['git', 'diff', '--check', '--', *applied])
        assert source() == expected
        status = 'passed-private-bulk-memory-integration'
    finally:
        cleanup = {'ownedScratch': str(scratch) if scratch else None, 'nativeInstancesStarted': 0,
                   'physicalRuns': 0, 'otherProjectProcessesModified': False}
        if scratch:
            holders = subprocess.run(['lsof', '-nP', '+D', str(scratch)], capture_output=True)
            (HERE / 'cleanup-open-holders.log').write_bytes(holders.stdout + holders.stderr)
            cleanup['holderCheckExitCode'] = holders.returncode
            cleanup['holderCheckEmpty'] = not holders.stdout and not holders.stderr
            if holders.returncode == 1 and cleanup['holderCheckEmpty']:
                shutil.rmtree(scratch)
            else:
                status = 'failed-owned-scratch-cleanup'
        cleanup['ownedScratchRemoved'] = scratch is None or not scratch.exists()
        save('cleanup.json', cleanup)
        save('integration.json', {'schema': 1, 'status': status, 'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
             'reviewReceiptSHA256': selected['reviewReceiptSHA256'], 'integratedSourceClosure': sha(encoded(expected)),
             'reviewedSourceClosure': sha(encoded(reviewed)), 'reviewedSourceUnchanged': False,
             'normalization': 'Only four ASCII spaces removed from each otherwise blank line 1050/1051 of experimental/execution/mod.rs; exact patch bound.',
             'sourceFiles': len(expected), 'appliedFiles': applied,
             'commands': commands, 'cleanup': cleanup, 'fullDispatcher': False, 'publicInvocation': False, 'gaAccepted': False})
        if not cleanup['ownedScratchRemoved']:
            raise RuntimeError('owned scratch retained after holder-check failure')

if __name__ == '__main__':
    main()
