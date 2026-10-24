#!/usr/bin/env python3
"""Reproduce and verify test-observer isolation; never changes engine source."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT / 'verification/swift-control-macro-implementation/results/20261024T032530904964Z'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(output):
    markers = ['control_trace ', 'control_warm ', 'control_validation_ceiling ']
    return sorted(line[line.index(marker):] for line in output.splitlines()
                  for marker in markers if marker in line)


def main():
    out = HERE / 'candidate-1'
    out.mkdir()
    workspace = Path(tempfile.mkdtemp(prefix='mixer-control-observer-'))
    source = workspace / 'vm'
    names = subprocess.check_output(['git', 'ls-files', '-z', '--', 'vm'], cwd=ROOT).decode().strip('\0').split('\0')
    hashes = {name: sha(ROOT / name) for name in names}
    for name in names:
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    (out / 'source-manifest.json').write_text(json.dumps(hashes, indent=2) + '\n')
    with tarfile.open(out / 'source.tar.gz', 'w:gz') as archive:
        archive.add(source, arcname='vm')
    env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])
    env.pop('RUSTC_BOOTSTRAP', None)
    env.pop('RUST_TEST_THREADS', None)
    env.pop('MIXER_ALLOCATOR_NOISE', None)
    commands, binaries = [], []

    def run(name, argv, noise=False):
        command_env = dict(env)
        if noise:
            command_env['MIXER_ALLOCATOR_NOISE'] = '1'
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        process = subprocess.run(argv, cwd=source, env=command_env, capture_output=True, text=True)
        (out / (name + '.stdout')).write_text(process.stdout)
        (out / (name + '.stderr')).write_text(process.stderr)
        commands.append({'name': name, 'argv': argv, 'cwd': str(source),
                         'noise': noise, 'diagnosticBootstrap': False,
                         'startedUTC': started, 'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'exitCode': process.returncode,
                         'stdoutSHA256': sha(out / (name + '.stdout')),
                         'stderrSHA256': sha(out / (name + '.stderr'))})
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        assert process.returncode == 0, (name, process.stderr[-1000:])
        return process.stdout

    receipt = {'status': 'failed', 'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'scope': 'Test-only observer serialization and diagnostic transport; unchanged engine/fixtures/assertions.',
               'nativeRuntime': False, 'gaAcceptance': False}
    try:
        run('rust-version', ['rustc', '--version', '--verbose'])
        run('cargo-version', ['cargo', '--version', '--verbose'])
        run('format', ['cargo', 'fmt', '--all', '--', '--check'])
        old = json.loads((PRIOR / 'receipt.json').read_text())
        for mode in ['span', 'all']:
            for profile in ['debug', 'release']:
                label = mode + '-' + profile
                flags = ['--features', 'experimental-span-execution'] if mode == 'span' else ['--all-features']
                args = ['cargo', 'test', '--locked', '--target-dir', str(workspace / ('target-' + mode)),
                        '--test', 'span_control_extraction', '--no-run', '--message-format=json'] + flags
                if profile == 'release':
                    args.append('--release')
                output = run(label + '-build', args)
                parsed = [json.loads(line) for line in output.splitlines() if line.startswith('{')]
                found = [item['executable'] for item in parsed if item.get('reason') == 'compiler-artifact'
                         and item.get('profile', {}).get('test') and item.get('executable')
                         and item['target']['name'] == 'span_control_extraction']
                assert len(found) == 1
                binary = Path(found[0])
                retained = out / 'binaries' / label
                retained.parent.mkdir(exist_ok=True)
                shutil.copy2(binary, retained)
                original = next(b for b in old['binaries'] if b['label'] == 'candidate-' + label)
                expected = rows((PRIOR / (original['runCommand'] + '.stdout')).read_text())
                assert len(expected) == 795
                listing = run(label + '-list', [str(retained), '--list'])
                assert [line[:-6] for line in listing.splitlines() if line.endswith(': test')] == original['tests']
                # No --nocapture: exercise the default libtest output path.
                # Six runner threads make the shared-lane contract explicit.
                for noise in [False, True]:
                    output = run(label + ('-noise' if noise else '-normal'), [str(retained), '--test-threads=6'], noise)
                    assert 'test result: ok. 6 passed; 0 failed; 0 ignored;' in output
                    assert rows(output) == expected, label
                binaries.append({'configuration': label, 'sha256': sha(retained),
                                 'relativePath': str(retained.relative_to(out)),
                                 'tests': original['tests'], 'rowsPerRun': len(expected)})
        assert hashes == {name: sha(ROOT / name) for name in names}
        receipt.update(status='passed-test-only-observer-concurrency-repair', configurations=4,
                       runs=8, testsPerRun=6, unchangedControlRowsPerRun=795,
                       sourceUnchanged=True, binaries=binaries)
    finally:
        receipt.update(observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       sourceManifestSHA256=sha(out / 'source-manifest.json'),
                       sourceArchiveSHA256=sha(out / 'source.tar.gz'), commandsSHA256=sha(out / 'commands.json'))
        receipt['artifacts'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ['artifacts', 'binaries']}))


if __name__ == '__main__':
    main()
