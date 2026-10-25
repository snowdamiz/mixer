#!/usr/bin/env python3
"""Owned, offline review replay; never starts a target/native/hosted harness."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
FROZEN = BASE / 'inputs/verification/swift-ordered-retention-analyzer-design'
RUST = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
UPSTREAM = {
    'verification/swift-ordered-retention-analyzer-design/seal.json':
        '4869a708a63be760519cf62c5d1bc42631a06049ea0d410408f3f5fb96637246',
    'verification/swift-ordered-retention-diagnostic-rust/seal.json':
        'c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf',
    'verification/swift-ordered-retention-diagnostic-completion/seal.json':
        '2e427447a34357ab4ff70eb220f56754f685a930edf4a89ebc29096fff3b73ba',
    'verification/swift-ordered-retention-diagnostic-completion-review/seal.json':
        '87a6fe21fd5c8f6590992aae8cc826e2502454686cf0d7a8c550acb7965827cc',
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_packet(seal, expected, member_root):
    assert digest(seal) == expected, str(seal)
    rows = json.loads(seal.read_bytes())['members']
    for row in rows:
        member = member_root / row['path']
        assert member.is_file() and member.stat().st_size == row['bytes'], row['path']
        assert digest(member) == row['sha256'], row['path']
    return dict(seal=str(seal.relative_to(ROOT)), sha256=expected,
                members=len(rows), bytes=sum(row['bytes'] for row in rows))


def check():
    rows = [verify_packet(ROOT / name, expected, ROOT) for name, expected in UPSTREAM.items()]
    verify_packet(FROZEN / 'seal.json', next(iter(UPSTREAM.values())), BASE / 'inputs')
    return rows


def main():
    assert sys.dont_write_bytecode
    run = BASE / 'commands/run-1'
    ordinal = 1
    while run.exists():
        ordinal += 1
        run = BASE / f'commands/run-{ordinal}'
    run.mkdir(parents=True)
    (run / 'executed-runner.py').write_bytes(Path(__file__).read_bytes())
    (run / 'executed-independent-tests.py').write_bytes((BASE / 'test_independent.py').read_bytes())
    result = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Independent finite design review only; no analyzer implementation acceptance',
        'agent': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh', 'context': 'fresh bounded delegation'},
        'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        'platform': platform.platform(),
        'environment': {'PYTHONDONTWRITEBYTECODE': '1'},
        'tools': {'python': {'path': sys.executable, 'version': sys.version,
                             'sha256': digest(Path(sys.executable).resolve())},
                  'rustc': {'path': str(RUST), 'sha256': digest(RUST)}},
        'commands': [], 'passed': False}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')

    def command(name, argv):
        completed = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=60)
        (run / f'{name}.stdout').write_bytes(completed.stdout)
        (run / f'{name}.stderr').write_bytes(completed.stderr)
        row = {'name': name, 'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 60,
               'returncode': completed.returncode,
               'stdout_sha256': hashlib.sha256(completed.stdout).hexdigest(),
               'stderr_sha256': hashlib.sha256(completed.stderr).hexdigest()}
        result['commands'].append(row)
        return completed.returncode == 0

    try:
        result['upstream_before'] = check()
        sources = [BASE / 'test_independent.py', BASE / 'run_review.py',
                   FROZEN / 'interface_schema.py', FROZEN / 'model.py',
                   FROZEN / 'test_model.py', FROZEN / 'layout.rs',
                   BASE / 'inputs/docs/swift-ordered-retention-analyzer.md']
        result['sources'] = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size,
                              'sha256': digest(p)} for p in sources]
        result['source_tree_sha256'] = hashlib.sha256(json.dumps(result['sources'],
                    sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        command('python-version', [sys.executable, '--version'])
        command('rust-version', [str(RUST), '--version', '--verbose'])
        command('producer-model', [sys.executable, '-B', '-m', 'unittest', 'discover',
                    '-s', str(FROZEN), '-p', 'test_model.py', '-v'])
        command('independent-model', [sys.executable, '-B', '-m', 'unittest', 'discover',
                    '-s', str(BASE), '-p', 'test_independent.py', '-v'])
        binary = run / 'layout-probe'
        if command('layout-compile', [str(RUST), '--edition=2021', '-O',
                                     str(FROZEN / 'layout.rs'), '-o', str(binary)]):
            command('layout-execute', [str(binary)])
            result['binary'] = {'path': str(binary.relative_to(ROOT)), 'sha256': digest(binary)}
        result['upstream_after'] = check()
        assert result['upstream_before'] == result['upstream_after']
        result['passed'] = all(row['returncode'] == 0 for row in result['commands'])
    except Exception as error:
        result['error'] = {'type': type(error).__name__, 'text': str(error)}
    finally:
        result['cleanup'] = {'all_synchronous_children_reaped': True,
            'only_owned_evidence_binary_retained': True, 'scratch_created': False,
            'product_target_started': False, 'native_started': False,
            'capture_started': False, 'process_discovery': False,
            'unrelated_processes_touched': False}
        (run / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        (BASE / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'run': str(run.relative_to(ROOT)), 'passed': result['passed'],
                      'source_tree_sha256': result.get('source_tree_sha256'),
                      'error': result.get('error')}, sort_keys=True))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
