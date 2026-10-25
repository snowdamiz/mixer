#!/usr/bin/env python3
"""Record finite design support only; never run product or original workload."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
RUST = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
UPSTREAM = {
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
        while block := stream.read(65536): h.update(block)
    return h.hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def check_upstream():
    out = []
    for name, expected in UPSTREAM.items():
        seal = ROOT / name
        assert digest(seal) == expected, name
        rows = json.loads(seal.read_bytes())['members']
        assert len(rows) < 512
        for row in rows:
            path = ROOT / row['path']
            assert path.is_file() and path.stat().st_size == row['bytes'], row['path']
            assert digest(path) == row['sha256'], row['path']
        out.append({'seal': name, 'sha256': expected, 'members': len(rows),
                    'bytes': sum(row['bytes'] for row in rows)})
    return out

def capture(argv, directory, name, env):
    result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=60)
    (directory / (name + '.stdout')).write_bytes(result.stdout)
    (directory / (name + '.stderr')).write_bytes(result.stderr)
    return {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 60,
            'returncode': result.returncode,
            'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
            'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()}

def main():
    assert sys.dont_write_bytecode
    commands = BASE / 'commands'
    commands.mkdir(exist_ok=True)
    ordinal = 1
    while (commands / f'run-{ordinal}').exists(): ordinal += 1
    run = commands / f'run-{ordinal}'
    run.mkdir()
    before = check_upstream()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    inputs = BASE / 'inputs'
    inputs.mkdir(exist_ok=True)
    selected = ['AGENTS.md', 'mixer-product-plan.md', 'PLAN.md',
        'docs/swift-ordered-retention-diagnostic-design.md',
        'docs/swift-ordered-retention-diagnostic-design-review.md',
        'docs/swift-ordered-retention-diagnostic-rust.md',
        'docs/swift-ordered-retention-diagnostic-rust-review.md',
        'docs/swift-ordered-retention-diagnostic-completion.md',
        'docs/swift-ordered-retention-diagnostic-completion-review.md',
        'verification/swift-ordered-retention-diagnostic-completion-root-review/acceptance.json',
        'verification/swift-ordered-retention-diagnostic-completion/logical-inventory.md',
        'verification/swift-ordered-retention-diagnostic-rust/writer.rs',
        'verification/swift-ordered-retention-diagnostic-rust/observer.rs',
        'verification/swift-ordered-retention-diagnostic-rust/source-code-table.json']
    bindings = []
    for name in selected:
        source = ROOT / name
        dest = inputs / name.replace('/', '__')
        if dest.exists() and digest(dest) != digest(source):
            dest = inputs / (f'run-{ordinal}__' + name.replace('/', '__'))
        if not dest.exists(): dest.write_bytes(source.read_bytes())
        bindings.append({'path': name, 'snapshot': str(dest.relative_to(ROOT)),
                         'bytes': dest.stat().st_size, 'sha256': digest(dest)})
    candidate = ROOT / 'verification/swift-ordered-retention-diagnostic-completion/candidate-source.tar.gz'
    manifest_path = ROOT / 'verification/swift-ordered-retention-diagnostic-completion/candidate-manifest.json'
    assert digest(manifest_path) == '007ba0dc9aaac2402cbf49d08ffaf8a1e2f75e5813ba4996e4936be4d0a92357'
    manifest = json.loads(manifest_path.read_bytes())
    selected_archive = {'src/experimental/cache/borrowed.rs',
        'src/experimental_swift_reactor/cache.rs', 'src/experimental_swift_reactor/control.rs'}
    with tarfile.open(candidate) as archive:
        members = archive.getmembers()
        assert len(members) == len(manifest) == 132
        assert {m.name for m in members} == set(manifest)
        for member in members:
            assert member.isfile()
            member_hash = hashlib.sha256()
            with archive.extractfile(member) as stream:
                while block := stream.read(65536): member_hash.update(block)
            assert member_hash.hexdigest() == manifest[member.name]
            if member.name in selected_archive:
                assert member.size <= 2_000_000
                body = archive.extractfile(member).read(2_000_001)
                assert len(body) == member.size
                dest = inputs / ('candidate__' + member.name.replace('/', '__'))
                if dest.exists(): assert dest.read_bytes() == body
                else: dest.write_bytes(body)
                bindings.append({'archive': str(candidate.relative_to(ROOT)),
                    'member': member.name, 'bytes': len(body), 'sha256': manifest[member.name]})
    source_rows = []
    for path in sorted(BASE.glob('*.py')) + [BASE / 'layout.rs', ROOT / 'docs/swift-ordered-retention-analyzer.md']:
        source_rows.append({'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size,
                            'sha256': digest(path)})
    source_tree = hashlib.sha256(json.dumps(source_rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    rows = []
    rows.append(capture([str(RUST), '--version', '--verbose'], run, 'rust-version', env))
    rows.append(capture([sys.executable, '--version'], run, 'python-version', env))
    rows.append(capture([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(BASE),
                         '-p', 'test_model.py', '-v'], run, 'finite-model', env))
    binary = run / 'layout-probe'
    rows.append(capture([str(RUST), '--edition=2021', '-O', str(BASE / 'layout.rs'), '-o', str(binary)],
                        run, 'layout-compile', env))
    if rows[-1]['returncode'] == 0:
        rows.append(capture([str(binary)], run, 'layout-execute', env))
    after = check_upstream()
    assert before == after
    for binding in bindings:
        if 'snapshot' in binding: assert digest(ROOT / binding['snapshot']) == binding['sha256']
    result = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Finite independent design support only; no complete analyzer or target qualification',
        'agent': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh', 'context': 'fresh bounded delegation'},
        'revision': revision, 'source_tree_sha256': source_tree, 'sources': source_rows,
        'tools': {'python': {'path': sys.executable, 'version': sys.version, 'sha256': digest(Path(sys.executable).resolve())},
                  'rustc': {'path': str(RUST), 'sha256': digest(RUST)}},
        'platform': platform.platform(),
        'environment': {'PYTHONDONTWRITEBYTECODE': '1', 'no_dependencies': True},
        'upstream_before': before, 'upstream_after': after, 'input_bindings': bindings,
        'commands': rows, 'passed': all(r['returncode'] == 0 for r in rows),
        'binary': {'path': str(binary.relative_to(ROOT)), 'sha256': digest(binary)} if binary.exists() else None,
        'cleanup': {'temporary_source_or_build_tree': False, 'retained_layout_binary': True,
                    'native_started': False, 'capture_started': False, 'process_discovery': False,
                    'owned_scratch_remaining': False, 'all_sync_children_reaped': True},
        'limitations': ['Design and finite oracle only; complete analyzer not implemented',
            'Host custody wrapper, strict adapters, full schema and code applicability remain review/implementation gates',
            'Layout types and reservations do not prove complete analyzer lifetime inventory or physical memory',
            'No product/native/target/source restoration/commit/push/GA action']}
    write_json(run / 'result.json', result)
    write_json(BASE / 'result.json', result)
    print(json.dumps({'run': str(run.relative_to(ROOT)), 'passed': result['passed'],
                      'source_tree_sha256': source_tree, 'upstream': before}, sort_keys=True))
    return 0 if result['passed'] else 1

if __name__ == '__main__': raise SystemExit(main())
