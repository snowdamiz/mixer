"""One-shot explicit-path delivery of accepted component slices and frozen evidence."""
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
BASE = 'ee9f6dc77f88259e2b143fc81dc1085b34a4a943'
PROTECTED = {
    '.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57',
    'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299',
}

def row(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def read(path):
    return json.loads(path.read_bytes())

def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

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
    try:
        os.killpg(child.pid, 0)
        absent = False
    except ProcessLookupError:
        absent = True
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
dispatcher = read(review / 'fixed-dispatcher-acceptance.json')
checkout = read(review / 'android-checkout-acceptance.json')
assert dispatcher['status'] == 'accepted-private-fixed-dispatcher-source-and-component-host-slice'
assert checkout['status'] == 'accepted-offline-Android-owner-checkout-closure-for-remote-validation'
canonical = [r['path'] for r in dispatcher['owned_files']] + ['.github/workflows/verify.yml']
for expected in dispatcher['owned_files'] + [checkout['workflow']]:
    assert row(ROOT / expected['path']) == expected
validation = read(review / 'fixed-dispatcher-metadata-validation.json')
assert validation['passed']
for expected in validation['metadata_files']:
    assert row(ROOT / expected['path']) == expected
selected = {ROOT / name for name in canonical + ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']}
for acceptance in [dispatcher, checkout]:
    for packet in acceptance['packets']:
        for expected in packet['members']:
            assert row(ROOT / expected['path']) == expected
            selected.add(ROOT / expected['path'])
for name, seal_name, digest in [
    ('swift-guarded-snapshot-actual-owner-rust-retirement-correction', 'seal.json', '46d811b1264770604106b061386e6eba01ea07e55590240eff722c36af4bcaa0'),
    ('swift-guarded-snapshot-actual-owner-rust-retirement-independent', 'seal.json', 'feb1ed71043022fb2d2cd98dd07ee14800f7828b9d8a325a3a9f5411a000f387'),
    ('console-fixed-workspace-dispatcher-selection', 'freeze.json', '07eb7fb6b7d2806e0ba51943d730b39ae205aa10aab6ae27529e9702f3d5bf42'),
]:
    directory = ROOT / 'verification' / name
    assert row(directory / seal_name)['sha256'] == digest
    seal = read(directory / seal_name)
    for expected in seal.get('members', seal.get('files', [])):
        actual = row(directory / expected['path'])
        assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256']
        selected.add(directory / expected['path'])
    selected.add(directory / seal_name)
    assert {p for p in directory.rglob('*') if p.is_file()} <= selected
root_review = ROOT / 'verification/swift-semantic-adapter-root-review'
selection = read(root_review / 'guarded-snapshot-root-result-lifetime-selection.json')
for packet in selection['packets']:
    for expected in packet['members']:
        assert row(ROOT / expected['path']) == expected
        selected.add(ROOT / expected['path'])
for name in ['accept-retirement-token-scope.py', 'guarded-snapshot-actual-owner-Rust-retirement-correction-release.json',
    'guarded-snapshot-actual-owner-Rust-retirement-token-scope-acceptance.json', 'guarded-snapshot-root-result-lifetime-selection.json',
    'release-actual-owner-retirement-correction.py', 'select-root-result-lifetime.py']:
    selected.add(root_review / name)
for directory in [review, ROOT / 'verification/github-delivery-session-consumer-swift-checkout']:
    selected.update(p for p in directory.rglob('*') if p.is_file())
selected.update([Path(__file__).resolve(), OUT / 'observe-ci.py'])
rows = [row(path) for path in sorted(selected)]
assert all(r['bytes'] < 100 * 1024 * 1024 for r in rows)
assert all(not r['path'].startswith(('vm/', 'native/', '.github/workflows/hosted.yml',
    'hosted/lib/mixer_hosted/browser_auth/', 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/',
    'verification/swift-guarded-snapshot-root-result-lifetime-independent/',
    'verification/ci-swift-capability-sparse-checkout-contract/')) for r in rows)
w = read(ROOT / 'work-graph.json'); g = read(ROOT / 'gates/ga.json')
assert [p['id'] for p in w['packages']] == [f'W{i:02}' for i in range(1, 19)]
assert [p['id'] for p in g['gates']] == [f'G{i:02}' for i in range(1, 39)]
assert sum(p['status'] == 'running' for p in g['gates']) == 8
assert sum(p['status'] == 'planned' for p in g['gates']) == 30
assert w['packages'][7]['fixtureCacheStateContractCandidate'] == g['gates'][1]['fixtureCacheStateContractCandidate']
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
assert [p['id'] for p in read(ROOT / 'dogfood/receipts/milestones.json')['milestones']] == [f'D{i}' for i in range(9)]
save('manifest.json', {'schema': 1, 'base': BASE, 'members': rows, 'canonical_paths': canonical,
    'scope': 'Accepted private dispatcher and Android owner checkout; narrow live-ledger IR01 review, selected IR02 contract/preaccess, and terminal prior CI. Active new Rust implementation/review and next checkout contract excluded.'})
paths = [r['path'] for r in rows] + [str((OUT / 'manifest.json').relative_to(ROOT))]
(OUT / 'paths.nul').write_bytes(b''.join(p.encode() + b'\0' for p in paths))
command('stage', ['git', 'add', '--force', '--pathspec-from-file=' + str(OUT / 'paths.nul'), '--pathspec-file-nul'])
for expected in rows:
    assert row(ROOT / expected['path']) == expected
index = set(filter(None, command('index-selected', ['git', 'diff', '--cached', '--name-only', '-z']).decode().split('\0')))
assert index <= set(paths) and set(canonical) <= index
command('authored-check', ['git', 'diff', '--cached', '--check', '--', *canonical,
    'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json', str(Path(__file__).relative_to(ROOT))])
raw = command('staged-objects', ['git', 'diff', '--cached', '--raw', '--no-abbrev', '-z']).split(b'\0')
for offset in range(0, len(raw) - 1, 2):
    header = raw[offset].decode().split(); path = raw[offset+1].decode()
    assert len(header) == 5 and header[-1] in ('A', 'M') and header[1] in ('100644', '100755')
    data = (ROOT / path).read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == header[3]
command('commit', ['git', 'commit', '-m', 'Add private workspace dispatcher and bound Android host checkout'])
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
    'pushed': True, 'force': False, 'canonical_paths': canonical, 'protected_work_unchanged': PROTECTED,
    'active_Rust_implementation_review_and_checkout_contract_excluded': True, 'CI_pending': True,
    'default_Repo_session_provider_native_customer_or_GA_acceptance': False})
print(json.dumps({'commit': head, 'tree': tree, 'changed_paths': len(index), 'pushed': True}))
