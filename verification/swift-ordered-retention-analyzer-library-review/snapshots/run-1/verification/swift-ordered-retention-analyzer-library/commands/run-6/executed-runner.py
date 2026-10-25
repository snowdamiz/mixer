#!/usr/bin/env python3
"""Owned host-only fixture framing evidence runner. No target/native/harness use."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'verification/swift-ordered-retention-analyzer-library'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
EXPECTED = {
    'swift-ordered-retention-diagnostic-rust': ('c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf', 186),
    'swift-ordered-retention-diagnostic-completion': ('2e427447a34357ab4ff70eb220f56754f685a930edf4a89ebc29096fff3b73ba', 222),
    'swift-ordered-retention-diagnostic-completion-review': ('87a6fe21fd5c8f6590992aae8cc826e2502454686cf0d7a8c550acb7965827cc', 158),
    'swift-ordered-retention-analyzer-design': ('c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8', 67),
    'swift-ordered-retention-analyzer-review': ('da87dd37e0983e212bbaf9658bc3177cb47c146bb13d82ddd2fea948c1966ebc', 212),
}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(65536): h.update(block)
    return h.hexdigest()

def describe(path): return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': sha(path)}
def write(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def upstream():
    results = []
    for name, (digest, count) in EXPECTED.items():
        path = ROOT / 'verification' / name / 'seal.json'
        assert sha(path) == digest, name
        record = json.loads(path.read_bytes())
        assert len(record['members']) == count, name
        for member in record['members']:
            p = ROOT / member['path']
            assert p.stat().st_size == member['bytes'] and sha(p) == member['sha256'], member['path']
        results.append({'packet': name, 'seal_sha256': digest, 'members': count})
    return results

def main():
    serial = 1
    while (PACKET / 'commands' / f'run-{serial}').exists(): serial += 1
    run = PACKET / 'commands' / f'run-{serial}'; run.mkdir()
    scratch = PACKET / 'scratch' / f'run-{serial}'; scratch.mkdir()
    shutil.copy2(__file__, run / 'executed-runner.py')
    receipt = {'schema': 1, 'at_unix': time.time(), 'scope': 'Fixture-only framing foundation; no semantic replay or acceptance', 'commands': [], 'passed': False}
    def command(name, argv, env=None):
        output = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=60)
        (run / (name + '.stdout')).write_bytes(output.stdout)
        (run / (name + '.stderr')).write_bytes(output.stderr)
        row = {'name': name, 'argv': [str(x) for x in argv], 'cwd': str(ROOT), 'returncode': output.returncode,
               'stdout_sha256': sha(run / (name + '.stdout')), 'stderr_sha256': sha(run / (name + '.stderr')), 'timeout_seconds': 60}
        receipt['commands'].append(row); write(run / 'result.json', receipt)
        return output
    try:
        receipt['upstream_before'] = upstream()
        receipt['revision_start'] = command('revision-start', ['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
        command('rust-version', [str(RUSTC), '--version', '--verbose'])
        command('python-version', [sys.executable, '--version'])
        receipt['tools'] = {'rustc': {'path': str(RUSTC), 'sha256': sha(RUSTC)}, 'python': {'path': sys.executable, 'sha256': sha(Path(sys.executable)), 'version': sys.version}}
        sources = []
        for relative in ['src/analyzer.rs', 'tests/fixture_tests.rs', 'inventory.py']:
            source = PACKET / relative; dest = run / 'sources' / relative; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, dest); sources.append(describe(source))
        receipt['sources_before'] = sources
        receipt['source_tree_sha256'] = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        history = ROOT / 'verification/swift-ordered-retention-diagnostic-completion/streams'
        destination = PACKET / 'inputs/historical'; destination.mkdir(exist_ok=True)
        sidecars = sorted(history.glob('*/*.sidecar.json')); assert len(sidecars) == 17
        historical = []
        for sidecar in sidecars:
            value = json.loads(sidecar.read_bytes()); assert value['status'] == 'invalid' and value['failure'] == 15
            stream = sidecar.with_name(sidecar.name.replace('.sidecar.json', '.bin'))
            assert stream.stat().st_size <= 4 * 1024 * 1024
            assert sha(stream) == value['stream_sha256']
            for member in [sidecar, stream]:
                target = destination / (member.parent.name + '__' + member.name)
                if target.exists(): assert sha(target) == sha(member)
                else: shutil.copy2(member, target)
            historical.append({'sidecar': describe(sidecar), 'stream': describe(stream), 'original_status': 'invalid', 'original_failure': 15})
        receipt['historical'] = historical
        write(PACKET / 'inputs/historical-manifest.json', historical)
        source = run / 'sources/src/analyzer.rs'
        lib = command('library-compile', [str(RUSTC), '--edition=2021', '--crate-name=mixer_fixture_framing', '--crate-type=lib', '-Dwarnings', str(source), '-o', str(run / 'foundation.rlib')])
        if lib.returncode: return
        test = command('test-compile', [str(RUSTC), '--edition=2021', '--test', '-Dwarnings', str(source), '-o', str(run / 'foundation-tests')])
        if test.returncode: return
        env = dict(os.environ, MIXER_ANALYZER_LIBRARY_TEST_SCRATCH=str(scratch), MIXER_ANALYZER_LIBRARY_HISTORICAL=str(destination), PYTHONDONTWRITEBYTECODE='1')
        receipt['test_environment'] = {k: env[k] for k in ['MIXER_ANALYZER_LIBRARY_TEST_SCRATCH', 'MIXER_ANALYZER_LIBRARY_HISTORICAL', 'PYTHONDONTWRITEBYTECODE']}
        test_run = command('test-execute', [str(run / 'foundation-tests'), '--test-threads=1', '--nocapture'], env)
        inventory_run = command('inventory', [sys.executable, '-B', str(run / 'sources/inventory.py')])
        if inventory_run.returncode == 0:
            inventory = json.loads(inventory_run.stdout); write(PACKET / 'logical-inventory.json', inventory)
            receipt['inventory'] = {'reserved_bytes': inventory['reserved_total'], 'named_role_upper_bytes': inventory['named_role_upper_total'], 'unassigned_margin': inventory['unassigned_margin']}
        receipt['passed'] = test_run.returncode == 0 and inventory_run.returncode == 0
    except BaseException:
        (run / 'runner-exception.stderr').write_text(traceback.format_exc())
        receipt['runner_exception'] = True
        raise
    finally:
        receipt['upstream_after'] = upstream()
        receipt['sources_after'] = [describe(PACKET / relative) for relative in ['src/analyzer.rs', 'tests/fixture_tests.rs', 'inventory.py']]
        if 'sources_before' in receipt: assert receipt['sources_before'] == receipt['sources_after']
        receipt['revision_end'] = command('revision-end', ['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
        if any(scratch.iterdir()): shutil.move(str(scratch), str(run / 'retained-test-files'))
        else: scratch.rmdir()
        receipt['cleanup'] = {'owned_scratch_remaining': False, 'synchronous_children_reaped': True, 'native_started': False, 'capture_started': False, 'process_discovery': False, 'target_or_hosted_harness_executed': False, 'test_binary_retained': (run / 'foundation-tests').exists(), 'rlib_retained': (run / 'foundation.rlib').exists()}
        write(run / 'result.json', receipt)
        print(json.dumps({'run': serial, 'passed': receipt['passed'], 'result': str((run / 'result.json').relative_to(ROOT))}))

if __name__ == '__main__': main()
