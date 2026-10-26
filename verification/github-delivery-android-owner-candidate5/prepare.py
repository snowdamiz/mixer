"""Verify and stage an explicit frozen delivery selection, including one deletion."""
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def bind(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def safe(name):
    parts = PurePosixPath(name)
    assert not parts.is_absolute() and '..' not in parts.parts and '\\' not in name
    path = ROOT
    for part in parts.parts:
        path /= part
        assert not path.is_symlink(), name
    assert path.is_file(), name
    return path

selection = json.loads((OUT / 'selection.json').read_bytes())
assert git('rev-parse', 'HEAD').decode().strip() == selection['base']
assert git('branch', '--show-current').decode().strip() == 'main'
assert not git('diff', '--cached', '--name-only', '--no-renames', '-z')
assert not (OUT / 'manifest.json').exists(), 'one-shot preparation already ran'
for row in selection['required_root_receipts']:
    path = safe(row['path'])
    assert bind(path)['sha256'] == row['sha256']
    data = json.loads(path.read_bytes())
    for key in row['required_true']:
        assert data[key] is True, (row['path'], key)

selected = set(selection['individual_files'])
verified_packets = []
for packet in selection['packets']:
    name = packet['path']
    path = safe(name)
    assert bind(path)['sha256'] == packet['sha256'], name
    data = json.loads(path.read_bytes())
    rows = data['members'] if isinstance(data.get('members'), list) else [
        {'path': key, **value} for key, value in data['files'].items()]
    assert len(rows) == len({row['path'] for row in rows})
    for row in rows:
        member = (path.parent.relative_to(ROOT) / row['path']).as_posix() if packet['relative_members'] else row['path']
        assert bind(safe(member)) == {key: row[key] for key in ('bytes', 'sha256')}, member
        selected.add(member)
    selected.add(name)
    verified_packets.append({**packet, 'members': len(rows), 'bytes': sum(row['bytes'] for row in rows)})

for name, digest in selection['canonical_maps'].items():
    path = safe(name)
    assert bind(path)['sha256'] == digest
    data = json.loads(path.read_bytes())
    rows = data.get('files', data)
    for member, row in rows.items():
        assert bind(safe(member)) == {key: row[key] for key in ('bytes', 'sha256')}, member

for name, row in selection['canonical_changed_files'].items():
    assert bind(safe(name)) == row, name
    selected.add(name)
for name, digest in selection['deletions'].items():
    assert not (ROOT / name).exists()
    assert hashlib.sha256(git('show', 'HEAD:' + name)).hexdigest() == digest

for prefix in selection['frozen_root_directories']:
    for path in (ROOT / prefix).rglob('*'):
        if path.is_file() and path.name != 'paths.nul':
            selected.add(path.relative_to(ROOT).as_posix())
selected.update((OUT.relative_to(ROOT) / name).as_posix() for name in ('selection.json', 'prepare.py', 'deliver.py'))
assert not any(name.startswith(('hosted/', '.wrangler/', 'verification/hosted-', 'docs/hosted-')) for name in selected)
assert '.github/workflows/hosted.yml' not in selected
assert 'docs/swift-calls-dispatch-v6-fixture-review.md' not in selected
assert not any(name.startswith(('verification/swift-cache-state-fixed-array-merge-proposal/', 'verification/swift-cache-state-c3-lifetime-independent/', 'verification/android-api28-v2-support-prerequisite/')) for name in selected)
assert 'docs/android-api28-v2-support-prerequisite.md' not in selected

changed = set(git('ls-files', '-m', '-o', '--exclude-standard', '-z').decode().split('\0'))
selected &= changed
selected.discard('')
members = {name: bind(safe(name)) for name in sorted(selected)}
assert all(row['bytes'] < 100_000_000 for row in members.values())
deletions = selection['deletions']
w = json.loads((ROOT / 'work-graph.json').read_bytes())['packages']
g = json.loads((ROOT / 'gates/ga.json').read_bytes())['gates']
assert [row['id'] for row in w] == [f'W{i:02}' for i in range(1, 19)]
assert [row['id'] for row in g] == [f'G{i:02}' for i in range(1, 39)]
assert not any(row['status'] == 'passed' for row in g)
for key in ('fixtureCacheStateContractCandidate', 'privateOwnerEffectContractCandidate'):
    assert next(row[key] for row in w if key in row) == next(row[key] for row in g if key in row)
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json', 'native/android', 'cli', '.github/workflows/verify.yml', 'THIRD_PARTY.yml'], cwd=ROOT, check=True)
manifest = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'command': sys.argv,
    'python': sys.version, 'base': selection['base'], 'scope': selection['scope'],
    'packets': verified_packets, 'files': members, 'deletions': deletions,
    'members': len(members), 'bytes': sum(row['bytes'] for row in members.values()),
    'canonical_private_owner_and_CLI_development_scope_accepted': True,
    'native_runtime_or_capture_started': False, 'public_V2_selected': False, 'GA_qualified': False,
}
manifest_path = OUT / 'manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
paths = sorted(selected | set(deletions) | {manifest_path.relative_to(ROOT).as_posix()})
listing = OUT / 'paths.nul'
listing.write_bytes(b'\0'.join(path.encode() for path in paths) + b'\0')
subprocess.run(['git', 'add', '--pathspec-from-file=' + str(listing), '--pathspec-file-nul'], cwd=ROOT, check=True)
staged = set(git('diff', '--cached', '--name-only', '--no-renames', '-z').decode().strip('\0').split('\0'))
assert staged == set(paths), sorted(staged ^ set(paths))
objects = {}
for row in git('ls-files', '--stage', '-z').split(b'\0'):
    if not row:
        continue
    head, name = row.split(b'\t', 1)
    mode, oid, stage = head.decode().split()
    if name.decode() in members:
        assert stage == '0'
        objects[name.decode()] = oid
assert set(objects) == set(members)
ordered = sorted(members)
request = ''.join(objects[name] + '\n' for name in ordered).encode()
batch = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT, input=request, capture_output=True, timeout=60, check=True).stdout
position = 0
for name in ordered:
    end = batch.index(b'\n', position)
    oid, kind, size_text = batch[position:end].decode().split()
    size = int(size_text)
    assert kind == 'blob' and oid == objects[name]
    blob = batch[end + 1:end + 1 + size]
    position = end + 2 + size
    assert {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()} == members[name], name
assert position == len(batch)
print(json.dumps({'staged_paths': len(paths), 'bytes': manifest['bytes'], 'manifest': bind(manifest_path)}))
