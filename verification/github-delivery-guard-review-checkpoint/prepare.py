"""Stage only explicit immutable review packets and root-owned checkpoint metadata."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = '137d3e1d833fcaee08244b439e50c2c42723bddd'

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
 ('verification/android-private-owner-integration-implementation/candidate-2/manifest.json', 'dc75c6544fdc10d25457c00782dcfb8afbcde756988ce0fd742606bb69c8c0e7', True),
 ('verification/android-private-owner-integration-implementation/candidate-3/manifest.json', 'c5bed3d89498abe0f9d9ee2547e74f4b26d2f29a05c9744e09b61d47259ecb6b', True),
 ('verification/android-private-owner-independent-review/implementation-review-1/manifest.json', 'e59aed63978371a1bb946b77b3e07ef0fce0fd9bd39a14d1c5c3f45aa2dd4742', False),
 ('verification/android-private-owner-independent-review/implementation-review-2/manifest.json', 'f9f1b610a6a7bfb7918be64f27b19b95a44682348168407c5af079405ca289ab', False),
 ('verification/swift-cache-state-implementation/candidate-repo-seal.json', 'caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3', False),
 ('verification/swift-cache-state-implementation/correction-1/candidate-repo-seal.json', 'b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6', False),
 ('verification/swift-cache-state-independent-review/implementation-review-1/review-seal.json', '3c189178c6c8cef3fa2236bbe9d3d0c8cb2806fc4afcf9940bdc7af67a444382', False),
 ('verification/swift-cache-state-independent-review/implementation-review-2/correction-control-seal.json', '13b4e77974be545bb34274ddba68b6b3b159e8d2287390dcffff864373d136c5', False),
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
selected.update(['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json', Path(__file__).relative_to(ROOT).as_posix()])
for prefix in ('verification/android-private-owner-effect-integration-root-review',
               'verification/swift-semantic-adapter-root-review',
               'verification/github-delivery-envelope-timeout-control',
               'verification/github-delivery-cache-state-review-preparation'):
    for path in (ROOT / prefix).rglob('*'):
        if path.is_file():
            assert not path.is_symlink()
            selected.add(path.relative_to(ROOT).as_posix())
# Keep unrelated edits, active source/proof lanes, CLI changes, and mutable native
# implementation ledgers entirely outside this evidence-only checkpoint.
assert not any(n.startswith(('cli/', 'native/', 'hosted/', '.github/', '.wrangler/')) for n in selected)
changed = set(git('ls-files', '-m', '-o', '--exclude-standard', '-z').decode().split('\0'))
selected &= changed
selected.discard('')
members = {n: bind(safe(n)) for n in sorted(selected)}
assert len(members) > 5000
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
    'scope': 'Immutable rejected Android candidates/reviews, Swift guard correction and exact independent control evidence, root metadata and prior CI terminal receipts. No canonical product, CLI, native or hosted changes.',
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
for name, expected in members.items():
    blob = git('show', ':' + name)
    assert {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()} == expected
print(json.dumps({'staged_paths': len(paths), 'bytes': manifest['bytes'], 'manifest': bind(manifest_path), 'scope': manifest['scope']}))
