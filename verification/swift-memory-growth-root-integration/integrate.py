#!/usr/bin/env python3
"""One-time root integration of pinned reviewed growth with exact whitespace delta."""
import datetime
import difflib
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VM = ROOT / 'vm'
PRODUCER = ROOT / 'verification/swift-memory-growth'
REVIEW = ROOT / 'verification/swift-memory-growth-review'
sha = lambda b: hashlib.sha256(b).hexdigest()
enc = lambda o: (json.dumps(o, sort_keys=True, indent=2) + '\n').encode()
read = lambda p: json.loads(p.read_text())
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(name, value):
    (HERE / name).write_bytes(enc(value))


def source():
    paths = [VM / 'Cargo.toml', VM / 'Cargo.lock']
    paths += [p for folder in ['src', 'tests', 'include'] for p in (VM / folder).rglob('*') if p.is_file()]
    return {str(p.relative_to(VM)): sha(p.read_bytes()) for p in paths}


def main():
    assert not (HERE / 'integration.json').exists(), 'one-time collector; preserve prior attempts'
    selected = read(HERE / 'review-selection.json')
    assert selected['rootSelectedForIntegration'] is True
    for path, digest in selected['bindings'].items():
        assert sha((ROOT / path).read_bytes()) == digest, path
    baseline = read(PRODUCER / 'baseline-source-manifest.json')
    reviewed = read(PRODUCER / 'candidate-source-manifest.json')
    assert source() == baseline, 'live source drift: do not overwrite'
    assert sha(enc(reviewed)) == selected['reviewedSourceClosure']
    helper_path = ROOT / 'verification/android-coordinator-runner-cleanup/owned_process.py'
    assert sha(helper_path.read_bytes()) == '209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216'
    spec = importlib.util.spec_from_file_location('growth_root_owned_process', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    commands, applied = [], []
    expected = baseline
    scratch = None
    status = 'failed'
    env = {**os.environ, 'PATH': '/opt/homebrew/opt/rustup/bin:' + os.environ['PATH']}
    for name in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_BOOTSTRAP', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER']:
        env.pop(name, None)

    def run(label, argv, *, cwd=ROOT, command_env=None, expected_exit=0, timeout=600):
        before = source()
        assert before == expected, label + ': unexpected live source'
        started = now()
        result = helper.execute(argv, cwd=cwd, env=command_env or env, timeout=timeout)
        output = result.stdout
        (HERE / (label + '.log')).write_bytes(output)
        after = source()
        row = {'label': label, 'argv': argv, 'cwd': str(cwd), 'startedUTC': started, 'finishedUTC': now(),
               'exitCode': result.returncode, 'log': label + '.log', 'outputSHA256': sha(output),
               'sourceBeforeSHA256': sha(enc(before)), 'sourceAfterSHA256': sha(enc(after)),
               'sourceUnchanged': before == after, 'timeoutSeconds': timeout,
               'timedOut': result.timedOut, 'groupCleanup': result.groupCleanup,
               'target': (command_env or env).get('CARGO_TARGET_DIR')}
        commands.append(row)
        save('commands.json', commands)
        assert after == before and result.returncode == expected_exit and not result.timedOut, label
        assert not result.groupCleanup['after'], label
        print(label + ' passed', flush=True)
        return output

    def artifact(label, argv, target_name, target_src, target_dir):
        context_env = {**env, 'CARGO_TARGET_DIR': str(target_dir)}
        assert not target_dir.exists(), 'fresh build context required'
        output = run(label + '-compile', argv, cwd=VM, command_env=context_env)
        rows = []
        for line in output.splitlines():
            try:
                row = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if row.get('reason') == 'compiler-artifact' and row.get('executable') and row['target']['name'] == target_name and Path(row['target']['src_path']) == VM / target_src and row['profile']['test']:
                rows.append(row)
        assert len(rows) == 1 and rows[0]['fresh'] is False, rows
        binary = Path(rows[0]['executable'])
        assert binary.is_relative_to(target_dir) and binary.is_file()
        body = binary.read_bytes()
        digest = sha(body)
        (HERE / (label + '-binary.gz')).write_bytes(gzip.compress(body, mtime=0))
        save(label + '-artifact.json', {'cargoArtifact': rows[0], 'binarySHA256': digest, 'binaryBytes': len(body), 'sourceSHA256': sha(enc(expected))})
        listed = run(label + '-test-list', [str(binary), '--list'], command_env=context_env)
        return binary, digest, listed, context_env

    try:
        run('producer-integrity', [sys.executable, '-B', str(PRODUCER / 'verify.py')])
        run('review-integrity', [sys.executable, '-B', str(REVIEW / 'verify.py')])
        with tarfile.open(PRODUCER / 'candidate-source.tar.gz') as archive:
            members = archive.getmembers()
            assert len(members) == len(reviewed) == 127
            assert all(m.isfile() and not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts for m in members)
            bodies = {m.name: archive.extractfile(m).read() for m in members}
        assert {name: sha(body) for name, body in bodies.items()} == reviewed
        name = 'src/experimental/execution/borrowed.rs'
        original = bodies[name]
        lines = original.splitlines(keepends=True)
        assert lines[528] == b'        $leaf!(work $this, \n'
        lines[528] = b'        $leaf!(work $this,\n'
        bodies[name] = b''.join(lines)
        assert len(original) - len(bodies[name]) == 1
        (HERE / 'normalization.patch').write_text(''.join(difflib.unified_diff(original.decode().splitlines(True), bodies[name].decode().splitlines(True), fromfile='reviewed/' + name, tofile='integrated/' + name)))
        expected = {name: sha(body) for name, body in bodies.items()}
        save('expected-source-manifest.json', expected)
        changed = sorted(name for name in expected if expected[name] != baseline.get(name))
        assert len(changed) == 9 and not set(baseline) - set(expected)
        assert changed == selected['changedRelativeFiles']
        # All checks precede the first live write; only the reviewed changed files are written.
        assert source() == baseline
        for name in changed:
            target = VM / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bodies[name])
            applied.append('vm/' + name)
        assert source() == expected
        save('integrated-source-manifest.json', source())
        with tarfile.open(HERE / 'integrated-source.tar.gz', 'w:gz') as archive:
            for name, body in sorted(bodies.items()):
                info = tarfile.TarInfo(name); info.size = len(body); info.mode = 0o644
                archive.addfile(info, io.BytesIO(body))
        scratch = Path(tempfile.mkdtemp(prefix='mixer-growth-root-', dir='/private/tmp'))
        scratch_identity = {'device': scratch.stat().st_dev, 'inode': scratch.stat().st_ino}
        digest = sha(enc(expected))
        run('rustc-version', ['rustc', '--version', '--verbose'])
        run('cargo-version', ['cargo', '--version'])
        run('host-version', ['uname', '-a'])
        run('python-version', [sys.executable, '--version'])
        common = ['--locked', '--offline', '--all-features', '--release', '--no-run', '--message-format=json-render-diagnostics']
        for label, selector, target_name, target_src, count, filters in [
            ('focused', ['--lib'], 'mixer_vm', 'src/lib.rs', 98, ['experimental_swift_reactor::execution::']),
            ('frozen', ['--test', 'span_execution'], 'span_execution', 'tests/span_execution.rs', 16, []),
        ]:
            target_dir = scratch / ('target-source-' + digest) / ('all-release-' + label + '-runtime')
            binary, binary_hash, listed, context_env = artifact(label, ['cargo', 'test', *selector, *common], target_name, target_src, target_dir)
            assert listed.count(b': test\n') >= count
            if filters:
                assert sum(line.startswith(filters[0].encode()) and line.endswith(b': test') for line in listed.splitlines()) == count
            assert sha(binary.read_bytes()) == binary_hash
            output = run(label + '-execute', [str(binary), *filters, '--nocapture', '--test-threads=1'], command_env=context_env)
            assert sha(binary.read_bytes()) == binary_hash
            assert f'test result: ok. {count} passed; 0 failed; 0 ignored;'.encode() in output
        clippy_env = {**env, 'CARGO_TARGET_DIR': str(scratch / ('target-source-' + digest) / 'swift-debug-production-clippy')}
        assert not Path(clippy_env['CARGO_TARGET_DIR']).exists()
        run('ci-swift-clippy', ['cargo', 'clippy', '--locked', '--offline', '--lib', '--features', 'experimental-swift-reactor', '--', '-D', 'warnings'], cwd=VM, command_env=clippy_env)
        run('integrated-whitespace', ['git', 'diff', '--check', '--', *applied])
        assert source() == expected
        status = 'passed-private-growth-integration'
    finally:
        cleanup = {'ownedScratch': str(scratch) if scratch else None, 'nativeInstancesStarted': 0, 'physicalRuns': 0, 'otherProjectProcessesModified': False}
        if scratch:
            cleanup.update(scratch_identity)
            files = [p for p in scratch.rglob('*') if p.is_file()]
            cleanup.update({'files': len(files), 'bytes': sum(p.stat().st_size for p in files)})
            holders = helper.execute(['lsof', '-nP', '+D', str(scratch)], cwd=ROOT, env=env, timeout=60)
            (HERE / 'cleanup-open-holders.log').write_bytes(holders.stdout)
            cleanup.update({'holderCheckExitCode': holders.returncode, 'holderCheckEmpty': not holders.stdout, 'groupCleanup': holders.groupCleanup})
            if holders.returncode == 1 and not holders.stdout and not holders.groupCleanup['after']:
                assert scratch.stat().st_dev == scratch_identity['device'] and scratch.stat().st_ino == scratch_identity['inode']
                shutil.rmtree(scratch)
            else:
                status = 'failed-owned-scratch-cleanup'
        cleanup['ownedScratchRemoved'] = scratch is None or not scratch.exists()
        save('cleanup.json', cleanup)
        save('integration.json', {'schema': 1, 'status': status, 'observedUTC': now(), 'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
             'reviewReceiptSHA256': selected['bindings']['verification/swift-memory-growth-review/receipt.json'], 'reviewedSourceClosure': sha(enc(reviewed)), 'integratedSourceClosure': sha(enc(expected)),
             'normalization': 'Exactly one trailing ASCII space removed from borrowed.rs line 529; raw reviewed candidate preserved.',
             'sourceFiles': len(expected), 'appliedFiles': applied, 'commands': commands, 'cleanup': cleanup,
             'fullDispatcher': False, 'publicInvocation': False, 'nativeAccepted': False, 'gaAccepted': False})
        assert cleanup['ownedScratchRemoved'], 'owned scratch retained after holder check failure'


if __name__ == '__main__':
    main()
