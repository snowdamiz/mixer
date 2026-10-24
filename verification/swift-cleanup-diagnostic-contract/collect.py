#!/usr/bin/env python3
"""Baseline-only bounded diagnostic audit; never writes the live VM."""
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
BASE = ROOT / 'verification/swift-memory-growth-root-integration'
EXPECTED = 'a0bbe77aca3021e48f1fb76dc97cfbc0406c24e5ba7eacdd33d5dabe8f998d9b'
sha = lambda body: hashlib.sha256(body).hexdigest()
enc = lambda value: (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()

def save(name, value):
    (HERE / name).write_bytes(enc(value))

def manifest(tree):
    files = [tree / 'Cargo.toml', tree / 'Cargo.lock']
    files += [path for name in ['src', 'tests', 'include'] for path in (tree / name).rglob('*') if path.is_file()]
    return {str(path.relative_to(tree)): sha(path.read_bytes()) for path in sorted(files)}

def archive(tree, name, selected):
    with tarfile.open(HERE / name, 'w:gz') as out:
        for relative in sorted(selected):
            body = (tree / relative).read_bytes()
            entry = tarfile.TarInfo(relative); entry.size = len(body); entry.mode = 0o644
            out.addfile(entry, io.BytesIO(body))

def main():
    assert not (HERE / 'receipt.json').exists(), 'preserve completed audit'
    original = json.loads((BASE / 'integrated-source-manifest.json').read_text())
    assert sha(enc(original)) == EXPECTED and len(original) == 127
    # Bind the entire root packet plus every recursively named accepted input.
    upstream = json.loads((BASE / 'accepted-input-bindings.json').read_text())
    assert isinstance(upstream, dict)
    bindings = dict(upstream)
    for path in BASE.rglob('*'):
        if path.is_file():
            bindings[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    inputs = ['AGENTS.md', 'mixer-product-plan.md', 'docs/swift-control-behavior-review.md',
        'docs/swift-control-behavior-implementation.md', 'docs/swift-memory-helper-contract.md',
        'docs/swift-memory-growth-integration-checkpoint.md',
        'verification/android-coordinator-runner-cleanup/owned_process.py']
    for relative in inputs:
        path = ROOT / relative
        bindings[relative] = sha(path.read_bytes())
        copy = HERE / 'inputs' / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(path.read_bytes())
    for relative, digest in bindings.items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    save('input-bindings.json', bindings)
    shutil.copyfile(BASE / 'integrated-source.tar.gz', HERE / 'baseline-source.tar.gz')
    save('baseline-source-manifest.json', original)
    helper_spec = importlib.util.spec_from_file_location('cleanup_diagnostic_owned_process', HERE / 'inputs/verification/android-coordinator-runner-cleanup/owned_process.py')
    helper = importlib.util.module_from_spec(helper_spec); helper_spec.loader.exec_module(helper)
    scratch = Path(tempfile.mkdtemp(prefix='mixer-cleanup-diagnostic-', dir='/private/tmp'))
    identity = (scratch.stat().st_dev, scratch.stat().st_ino)
    contexts = {}
    commands = []
    status = 'failed'
    env = {**os.environ, 'PATH': '/opt/homebrew/opt/rustup/bin:' + os.environ['PATH']}
    for key in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_BOOTSTRAP', 'CARGO_TARGET_DIR',
        'CARGO_BUILD_TARGET', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER']:
        env.pop(key, None)

    def run(label, argv, tree, command_env, expected_code=0, timeout=180):
        before = manifest(tree)
        started = now()
        result = helper.execute(argv, cwd=tree, env=command_env, timeout=timeout)
        (HERE / (label + '.log')).write_bytes(result.stdout)
        after = manifest(tree)
        row = {'label': label, 'argv': argv, 'cwd': str(tree), 'environment': {
            key: command_env.get(key) for key in ['PATH', 'CARGO_TARGET_DIR', 'RUSTFLAGS',
                'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_BOOTSTRAP', 'CARGO_BUILD_TARGET', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER']},
            'startedUTC': started, 'finishedUTC': now(), 'exitCode': result.returncode,
            'log': label + '.log', 'outputSHA256': sha(result.stdout),
            'sourceBeforeSHA256': sha(enc(before)), 'sourceAfterSHA256': sha(enc(after)),
            'sourceUnchanged': before == after, 'timedOut': result.timedOut,
            'timeoutSeconds': timeout, 'groupCleanup': result.groupCleanup}
        commands.append(row); save('commands.json', commands)
        assert before == after and result.returncode == expected_code and not result.timedOut, label
        assert not result.groupCleanup['after'], label
        print(label + ' passed', flush=True)
        return result.stdout

    try:
        baseline = scratch / 'baseline'; baseline.mkdir()
        with tarfile.open(HERE / 'baseline-source.tar.gz') as source:
            entries = source.getmembers()
            assert len(entries) == 127
            assert all(e.isfile() and not PurePosixPath(e.name).is_absolute() and '..' not in PurePosixPath(e.name).parts for e in entries)
            source.extractall(baseline, filter='data')
        assert manifest(baseline) == original
        probe = scratch / 'probe'; shutil.copytree(baseline, probe)
        patch = ''
        for leaf, target in [('memory_probe.rs', 'src/experimental_swift_reactor/memory_operations_tests.rs'),
                ('control_probe.rs', 'src/experimental_swift_reactor/control_tests.rs')]:
            path = probe / target
            before = path.read_text(); after = before + (HERE / leaf).read_text(); path.write_text(after)
            patch += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='baseline/' + target, tofile='probe/' + target))
        (HERE / 'probe.patch').write_text(patch)
        save('probe-source-manifest.json', manifest(probe))
        archive(probe, 'probe-source.tar.gz', manifest(probe))
        for label, argv in [('rustc-version', ['rustc', '--version', '--verbose']),
                ('cargo-version', ['cargo', '--version']), ('host-version', ['uname', '-a']),
                ('python-version', [sys.executable, '--version'])]:
            run(label, argv, baseline, env)
        baseline_selections = ['sc09_defensive_live_faults', 'mm08_post_pop_live_fault',
            'mg14_post_pop_live_debt_and_fail_closed',
            'cleanup_invariants_are_separate_from_the_immutable_first_terminal_cause',
            'live_cleanup_underflow_retains_counts_and_remaining_cleanup_still_drains']
        probe_selections = ['cd01_actual_pinned_load_preserves_absent_cleanup_origin',
            'cd02_cursorless_cleanup_remains_absent_for_all_actual_live_resources',
            'cd03_later_live_underflow_only_enriches_cleanup_observation']
        for name, tree, selections in [('baseline', baseline, baseline_selections), ('probe', probe, probe_selections)]:
            digest = sha(enc(manifest(tree)))
            target = scratch / ('target-' + name + '-' + digest + '-all-release-unit')
            assert not target.exists()
            build_env = {**env, 'CARGO_TARGET_DIR': str(target)}
            output = run(name + '-compile', ['cargo', 'test', '--locked', '--offline', '--lib',
                '--all-features', '--release', '--no-run', '--message-format=json-render-diagnostics'], tree, build_env, timeout=240)
            rows = []
            for line in output.splitlines():
                try: row = json.loads(line)
                except (ValueError, UnicodeDecodeError): continue
                if row.get('reason') == 'compiler-artifact' and row.get('executable') and row['target']['name'] == 'mixer_vm' and Path(row['target']['src_path']) == tree / 'src/lib.rs' and row['profile']['test']:
                    rows.append(row)
            assert len(rows) == 1 and rows[0]['fresh'] is False
            binary = Path(rows[0]['executable']); assert binary.is_relative_to(target)
            body = binary.read_bytes(); binary_hash = sha(body)
            (HERE / (name + '-binary.gz')).write_bytes(gzip.compress(body, mtime=0))
            save(name + '-artifact.json', {'cargoArtifact': rows[0], 'binarySHA256': binary_hash,
                'binaryBytes': len(body), 'sourceSHA256': digest, 'features': 'all',
                'profile': 'release', 'context': name + '-all-release-unit'})
            listed = run(name + '-test-list', [str(binary), '--list'], tree, build_env)
            full = [line.decode().removesuffix(': test') for line in listed.splitlines() if line.endswith(b': test')]
            selected = []
            for short in selections:
                match = [test for test in full if test.endswith('::' + short)]
                assert len(match) == 1, (short, match)
                selected += match
            contexts[name] = {'sourceSHA256': digest, 'sourceFiles': len(manifest(tree)),
                'binarySHA256': binary_hash, 'fullTestCount': len(full), 'selectedTests': selected,
                'features': 'all', 'profile': 'release', 'productionEngineChanged': False}
            save('contexts.json', contexts)
            for index, test in enumerate(selected, 1):
                assert sha(binary.read_bytes()) == binary_hash
                output = run(name + '-test-' + str(index), [str(binary), test, '--exact',
                    '--nocapture', '--test-threads=1'], tree, build_env)
                assert b'test result: ok. 1 passed; 0 failed; 0 ignored;' in output
                assert sha(binary.read_bytes()) == binary_hash
        status = 'baseline-attribution-gap-reproduced-contract-only'
    finally:
        cleanup = {'ownedScratch': str(scratch), 'device': identity[0], 'inode': identity[1],
            'nativeInstancesStarted': 0, 'physicalRuns': 0, 'otherProjectProcessesModified': False}
        files = [path for path in scratch.rglob('*') if path.is_file()]
        cleanup.update({'files': len(files), 'bytes': sum(path.stat().st_size for path in files)})
        holders = helper.execute(['lsof', '-nP', '+D', str(scratch)], cwd=ROOT, env=env, timeout=60)
        (HERE / 'cleanup-open-holders.log').write_bytes(holders.stdout)
        cleanup.update({'holderCheckExitCode': holders.returncode, 'holderCheckEmpty': not holders.stdout,
            'holderCommand': ['lsof', '-nP', '+D', str(scratch)], 'groupCleanup': holders.groupCleanup})
        if holders.returncode == 1 and not holders.stdout and not holders.groupCleanup['after']:
            assert (scratch.stat().st_dev, scratch.stat().st_ino) == identity
            shutil.rmtree(scratch)
        cleanup['ownedScratchRemoved'] = not scratch.exists()
        save('cleanup.json', cleanup)
        save('receipt.json', {'schema': 1, 'status': status, 'observedUTC': now(),
            'sourceRevisionContext': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'acceptedBaselineSourceSHA256': EXPECTED, 'sourceFiles': 127,
            'contexts': contexts, 'commands': commands, 'cleanup': cleanup,
            'inputBindings': len(bindings), 'liveVmWritten': False, 'implementationAuthorized': False,
            'g08Accepted': False, 'fullSwiftAccepted': False, 'nativeAccepted': False,
            'releaseAccepted': False, 'gaAccepted': False})
        assert cleanup['ownedScratchRemoved']

if __name__ == '__main__':
    main()
