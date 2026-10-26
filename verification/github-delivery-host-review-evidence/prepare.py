"""Stage only explicit immutable review packets and root-owned checkpoint metadata."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = '99f8a0a727bc08a15561d8d83b2aed8b9ad96265'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def bind(path):
    b = path.read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def safe(name):
    parts = PurePosixPath(name)
    assert not parts.is_absolute() and '..' not in parts.parts and '\\' not in name
    p = ROOT
    for part in parts.parts:
        p /= part
        assert not p.is_symlink()
    assert p.is_file()
    return p

assert git('rev-parse', 'HEAD').decode().strip() == BASE
assert git('branch', '--show-current').decode().strip() == 'main'
assert not git('diff', '--cached', '--name-only', '-z')
selected = set()
packets = [
 ('verification/android-private-owner-profile3-independent-review/manifest.json', '685a1d1f905540c023d3ffebd5eed392cde08fd8e07ee15e6d9d246dcbd8b7ac', True),
 ('verification/android-private-owner-integration-implementation/candidate-4/manifest.json', '69fcd445119c0ea311c11cf97587d591d87ba1c5bd2d5b3c0a722116f66231c5', True),
 ('verification/android-private-owner-profile3-integration/candidate4-qualification/manifest.json', 'ff947ccf16b055e10e3458bd9b8161b597b7744131c5eb8d7f67377736c134a6', True),
 ('verification/android-private-owner-independent-review/implementation-review-3/checkpoint-first10/manifest.json', 'd12dd7f879ab399900d26f5fbd559254ac495d4c4f6fe94b6430ab0ca6945087', False),
 ('verification/swift-cache-state-independent-review/implementation-review-2/bulk-words-0000-root/bulk-results-seal.json', '6fa4ff335341aa5a05eeedad550b41ed7e55a62cf78a11b40fc526f4774f14ba', False),
 ('verification/swift-cache-state-independent-review/implementation-review-2/transport-amendment/transport-seal.json', '27d8d6313c7578c8bb486d5044b68f1a1482945e338e7c111ec8635f04879afc', False),
 ('verification/swift-cache-state-accounting-supplement/seal.json', '7558f957bfe4b8cb62703b76e064f87d2e70a535cf5d61d55b826244c6770c77', False),
 ('verification/swift-cache-state-accounting-independent-review/seal.json', '706e1ab2a1caa6b14cf588d40545a086ea32fc1a7a23a7eb5c1b1f5a48dfacd8', False),
]
verified = []
for name, digest, local in packets:
    path = safe(name)
    assert bind(path)['sha256'] == digest
    data = json.loads(path.read_bytes())
    members = data['members'] if isinstance(data['members'], list) else [{'path': k, **v} for k, v in data['files'].items()]
    assert len({m['path'] for m in members}) == len(members)
    for m in members:
        relative = (path.parent.relative_to(ROOT) / m['path']).as_posix() if local else m['path']
        assert bind(safe(relative)) == {'bytes': m['bytes'], 'sha256': m['sha256']}
        selected.add(relative)
    selected.add(name)
    verified.append({'seal': name, 'sha256': digest, 'members': len(members), 'bytes': sum(x['bytes'] for x in members)})
selected.update(['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json', 'docs/android-private-owner-profile3-integration.md', 'docs/android-private-owner-profile3-independent-review.md', 'verification/android-private-owner-profile3-independent-review/seal-receipt.json', 'docs/android-private-owner-integration-implementation.md', Path(__file__).relative_to(ROOT).as_posix()])
for prefix in ('verification/android-private-owner-effect-integration-root-review',
               'verification/swift-semantic-adapter-root-review',
               'verification/github-delivery-guard-review-checkpoint'):
    for path in (ROOT / prefix).rglob('*'):
        if path.is_file() and path.name != 'paths.nul':
            assert not path.is_symlink()
            selected.add(path.relative_to(ROOT).as_posix())
# Keep unrelated edits, active source/proof lanes, CLI changes, and mutable native
# implementation ledgers entirely outside this evidence-only checkpoint.
assert not any(n.startswith(('cli/', 'native/', 'hosted/', '.github/', '.wrangler/')) for n in selected)
changed = set(git('ls-files', '-m', '-o', '--exclude-standard', '-z').decode().split('\0'))
selected &= changed
selected.discard('')
members = {n: bind(safe(n)) for n in sorted(selected)}
assert len(members) > 3500
assert all(m['bytes'] < 100_000_000 for m in members.values())
for name in ('work-graph.json', 'gates/ga.json'):
    json.loads((ROOT / name).read_bytes())
w = json.loads((ROOT / 'work-graph.json').read_bytes())['packages']
g = json.loads((ROOT / 'gates/ga.json').read_bytes())['gates']
assert [x['id'] for x in w] == [f'W{i:02}' for i in range(1, 19)]
assert [x['id'] for x in g] == [f'G{i:02}' for i in range(1, 39)]
assert not any(x['status'] == 'passed' for x in g)
for key in ('fixtureCacheStateContractCandidate', 'privateOwnerEffectContractCandidate'):
    assert next(x[key] for x in w if key in x) == next(x[key] for x in g if key in x)
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], cwd=ROOT, check=True)
manifest = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': sys.argv, 'python': sys.version, 'base': BASE,
    'scope': 'Immutable candidate4 and CLI host qualification, first10 independent owner controls,192 independent semantic cases, source-accounting findings, root metadata and terminal99fCI. Canonical product/CLI/native/hosted edits remain excluded; full implementation acceptance is pending.',
    'packets': verified, 'files': members, 'members': len(members), 'bytes': sum(m['bytes'] for m in members.values()),
    'validation': 'Exact explicit-member SHA256 custody, safe paths, root JSON identities/mirrors, no GA promotion, metadata whitespace checks.',
    'source_accounting_or_full_implementation_accepted': False, 'native_runtime_or_capture_started': False, 'GA_qualified': False}
manifest_path = OUT / 'manifest.json'
assert not manifest_path.exists()
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
paths = sorted(selected | {manifest_path.relative_to(ROOT).as_posix()})
listing = OUT / 'paths.nul'
listing.write_bytes(b'\0'.join(p.encode() for p in paths) + b'\0')
subprocess.run(['git', 'add', '--pathspec-from-file=' + str(listing), '--pathspec-file-nul'], cwd=ROOT, check=True)
staged = set(git('diff', '--cached', '--name-only', '-z').decode().strip('\0').split('\0'))
assert staged == set(paths), sorted(staged ^ set(paths))
# Validate the staged blobs in one bounded batch without thousands of subprocesses.
index_rows = git('ls-files', '--stage', '-z').split(b'\0')
index_objects = {}
for row in index_rows:
    if not row:
        continue
    head, name = row.split(b'\t', 1)
    mode, oid, stage = head.decode().split()
    if name.decode() in members:
        assert stage == '0'
        index_objects[name.decode()] = oid
assert set(index_objects) == set(members)
ordered = sorted(members)
request = ''.join(index_objects[name] + '\n' for name in ordered).encode()
result = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT, input=request, capture_output=True, timeout=60, check=True)
position = 0
for name in ordered:
    end = result.stdout.index(b'\n', position)
    oid, kind, size_text = result.stdout[position:end].decode().split()
    size = int(size_text)
    assert kind == 'blob' and oid == index_objects[name]
    blob = result.stdout[end + 1:end + 1 + size]
    position = end + 2 + size
    expected = members[name]
    assert {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()} == expected, name
assert position == len(result.stdout)

print(json.dumps({'staged_paths': len(paths), 'bytes': manifest['bytes'], 'manifest': bind(manifest_path), 'scope': manifest['scope']}))
