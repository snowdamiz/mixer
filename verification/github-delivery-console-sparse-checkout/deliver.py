"""One-shot, explicit-path delivery of the reviewed console checkout repair."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = 'b231f3d405c06bfb348f193d46a348af0529bd84'
PROTECTED = {
    '.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57',
    'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299',
}

def row(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False

def command(name, argv, timeout=45):
    start = time.monotonic()
    timed = False
    with (OUT / (name + '.stdout')).open('xb') as stdout, (OUT / (name + '.stderr')).open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
    absent = not group_exists(child.pid)
    save(name + '.command.json', {'argv': argv, 'exit': child.returncode, 'timed_out': timed,
        'elapsed_seconds': time.monotonic() - start, 'owned_pid': child.pid, 'owned_pgid': child.pid,
        'direct_child_reaped': True, 'owned_group_observed_absent': absent,
        'stdout': row(OUT / (name + '.stdout')), 'stderr': row(OUT / (name + '.stderr'))})
    assert not timed and absent and child.returncode == 0, name
    return (OUT / (name + '.stdout')).read_bytes()

assert not (OUT / 'manifest.json').exists(), 'One-shot; do not replay'
assert command('branch', ['git', 'branch', '--show-current']).decode().strip() == 'main'
assert command('head', ['git', 'rev-parse', 'HEAD']).decode().strip() == BASE
assert command('remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == BASE
assert not command('index-before', ['git', 'diff', '--cached', '--name-only'])
for path, sha in PROTECTED.items():
    assert row(ROOT / path)['sha256'] == sha
review = ROOT / 'verification/console-session-and-checkout-root-review'
acceptance = json.loads((review / 'acceptance.json').read_bytes())
assert acceptance['checkout_repair']['status'] == 'accepted-offline-input-closure-for-remote-validation'
assert row(ROOT / '.github/workflows/console.yml') == acceptance['checkout_repair']['workflow']
metadata = json.loads((review / 'retirement-metadata-validation.json').read_bytes())
assert metadata['passed']
for item in metadata['metadata_files']:
    assert row(ROOT / item['path']) == item
selected = {ROOT / name for name in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json', '.github/workflows/console.yml']}
for packet in acceptance['packets']:
    for item in packet['members']:
        assert row(ROOT / item['path']) == item
        selected.add(ROOT / item['path'])
for directory in [review, ROOT / 'verification/github-delivery-console-pagination-owner-contracts']:
    selected.update(path for path in directory.rglob('*') if path.is_file())
for name in ['release-actual-owner-rust-implementation.py', 'guarded-snapshot-actual-owner-Rust-frozen-release.json', 'return-actual-owner-rust-ir01.py', 'guarded-snapshot-actual-owner-Rust-IR01-return.json']:
    selected.add(ROOT / 'verification/swift-semantic-adapter-root-review' / name)
independent = ROOT / 'verification/swift-guarded-snapshot-actual-owner-rust-independent'
assert row(independent / 'seal.json')['sha256'] == 'e9d55089795d317048040be973e518ff9ce841d7f39cb1449b930d7ae066990c'
for item in json.loads((independent / 'seal.json').read_bytes())['members']:
    actual = row(independent / item['path'])
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
    selected.add(independent / item['path'])
selected.add(independent / 'seal.json')
selected.add(Path(__file__).resolve())
rows = [row(path) for path in sorted(selected)]
assert all(item['bytes'] < 100 * 1024 * 1024 for item in rows)
assert all(not item['path'].startswith(('console/', 'hosted/', 'android/', 'vm/', '.github/workflows/hosted.yml',
    'verification/console-browser-session-consumer/', 'verification/swift-guarded-snapshot-actual-owner-rust-implementation/',
    'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction/')) for item in rows)
w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
assert [item['id'] for item in w['packages']] == [f'W{i:02}' for i in range(1,19)]
assert [item['id'] for item in g['gates']] == [f'G{i:02}' for i in range(1,39)]
assert sum(item['status'] == 'running' for item in g['gates']) == 8
assert sum(item['status'] == 'planned' for item in g['gates']) == 30
assert w['packages'][7]['fixtureCacheStateContractCandidate'] == g['gates'][1]['fixtureCacheStateContractCandidate']
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
save('manifest.json', {'schema': 1, 'base': BASE, 'members': rows,
    'scope': 'Checkout-only console CI repair; released frontend session contract selection and current root evidence. Active product and Rust candidates excluded.'})
paths = [item['path'] for item in rows] + [str((OUT / 'manifest.json').relative_to(ROOT))]
(OUT / 'paths.nul').write_bytes(b''.join(path.encode() + b'\0' for path in paths))
command('stage', ['git', 'add', '--force', '--pathspec-from-file=' + str(OUT / 'paths.nul'), '--pathspec-file-nul'])
for item in rows:
    assert row(ROOT / item['path']) == item
index = set(filter(None, command('index-selected', ['git', 'diff', '--cached', '--name-only', '-z']).decode().split('\0')))
assert index <= set(paths) and '.github/workflows/console.yml' in index
command('authored-check', ['git', 'diff', '--cached', '--check', '--', '.github/workflows/console.yml',
    'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json', str(Path(__file__).relative_to(ROOT))])
raw = command('staged-objects', ['git', 'diff', '--cached', '--raw', '--no-abbrev', '-z']).split(b'\0')
for offset in range(0, len(raw) - 1, 2):
    header = raw[offset].decode().split()
    path = raw[offset+1].decode()
    assert len(header) == 5 and header[-1] in ('A','M') and header[1] in ('100644','100755')
    data = (ROOT / path).read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == header[3]
command('commit', ['git', 'commit', '-m', 'Bound console CI checkout to required inputs'])
head = command('after-head', ['git', 'rev-parse', 'HEAD']).decode().strip()
tree = command('tree', ['git', 'rev-parse', 'HEAD^{tree}']).decode().strip()
assert command('parent', ['git', 'rev-parse', 'HEAD^']).decode().strip() == BASE
committed = set(filter(None, command('committed-paths', ['git', 'diff-tree', '--no-commit-id', '--name-only', '-z', '-r', 'HEAD']).decode().split('\0')))
assert committed == index
assert not command('index-after', ['git', 'diff', '--cached', '--name-only'])
command('push', ['git', 'push', 'origin', 'HEAD:main'])
assert command('remote-after', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == head
for path, sha in PROTECTED.items():
    assert row(ROOT / path)['sha256'] == sha
save('receipt.json', {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'commit': head,
    'tree': tree, 'parent': BASE, 'committed_paths': len(index), 'manifest': row(OUT / 'manifest.json'),
    'pushed': True, 'force': False, 'canonical_paths': ['.github/workflows/console.yml'],
    'protected_work_unchanged': PROTECTED, 'active_product_lanes_excluded': True,
    'CI_pending': True, 'native_browser_provider_or_GA_acceptance': False})
print(json.dumps({'commit': head, 'tree': tree, 'changed_paths': len(index), 'pushed': True}))
