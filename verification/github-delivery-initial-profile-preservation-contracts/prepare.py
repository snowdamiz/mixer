#!/usr/bin/env python3
"""Stage coherent frozen host evidence and selected correction contracts."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def demand(ok, message):
    if not ok:
        raise ValueError(message)

def git(*args, **kwargs):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True, timeout=60, **kwargs).stdout

def sha(data):
    return hashlib.sha256(data).hexdigest()

def nodes(value, key):
    if isinstance(value, dict):
        if key in value:
            yield value[key]
        for child in value.values():
            yield from nodes(child, key)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child, key)

demand(not (HERE / 'prepared.json').exists(), 'One-shot preparation already completed')
demand(not git('diff', '--cached', '--name-only'), 'Index must be empty')
demand(git('branch', '--show-current').strip() == b'main', 'Expected main')
parent = git('rev-parse', 'HEAD').decode().strip()
demand(parent == '4e7c21ee82def176bfe857dba2fa243eb8b4ebb1', 'Unexpected base')
selection = json.loads((HERE / 'selection.json').read_text())
demand(selection['completed_evidence_scope_root_reviewed'] is True, 'Root acceptance required')
demand(sha((ROOT / '.github/workflows/verify.yml').read_bytes()) == '7f3ab7ef5ec94379a969c91e9f2348cecd2e80908c8a7330aef845f133f38e62', 'Reviewed workflow identity')
demand(selection['canonical_product_changes'] is False, 'Evidence checkpoint must not promote pending product sources')
paths = set(selection['paths'])
for packet in selection['packets']:
    path = ROOT / packet['path']
    demand(sha(path.read_bytes()) == packet['sha256'], 'Frozen packet changed: ' + packet['path'])
    value = json.loads(path.read_text())
    members = value.get('files', value.get('members'))
    rows = [dict(row, path=name) for name, row in members.items()] if isinstance(members, dict) else members
    for row in rows:
        member_name = str(Path(packet.get('member_base', '')) / row['path'])
        data = (ROOT / member_name).read_bytes()
        demand(len(data) == row['bytes'] and sha(data) == row['sha256'], 'Frozen member changed: ' + member_name)
        demand(member_name in paths, 'Frozen member excluded: ' + member_name)
    demand(packet['path'] in paths, 'Packet seal excluded')
for path in HERE.iterdir():
    if path.is_file() and path.name not in {'paths.nul', 'manifest.json', 'prepared.json'}:
        paths.add(str(path.relative_to(ROOT)))
for name in paths:
    demand(not name.startswith(('hosted/', '.wrangler/', '.github/', 'native/', 'vm/', 'cli/', 'verification/swift-initial-profile-construction-protocol/', 'verification/android-editor-preservation-protocol-independent/', 'verification/android-editor-integration-contract-independent/')), 'Unrelated source included')
work = json.loads((ROOT / 'work-graph.json').read_text())
gates = json.loads((ROOT / 'gates/ga.json').read_text())
old_gates = json.loads(git('show', 'HEAD:gates/ga.json'))
demand([p['id'] for p in work['packages']] == [f'W{i:02}' for i in range(1, 19)], 'W01-W18')
demand([g['id'] for g in gates['gates']] == [f'G{i:02}' for i in range(1, 39)], 'G01-G38')
demand([(g['id'], g['status']) for g in old_gates['gates']] == [(g['id'], g['status']) for g in gates['gates']], 'GA status changed')
for key in ['fixtureCacheStateContractCandidate', 'privateOwnerEffectContractCandidate']:
    a = list(nodes(work, key)); b = list(nodes(gates, key))
    demand(len(a) == 1 and a == b, 'Mirror mismatch: ' + key)
milestones = json.loads((ROOT / 'dogfood/receipts/milestones.json').read_text())['milestones']
demand([m['id'] for m in milestones] == [f'D{i}' for i in range(9)], 'D0-D8')
rows = []
for name in sorted(paths):
    data = (ROOT / name).read_bytes()
    rows.append({'path': name, 'bytes': len(data), 'sha256': sha(data)})
manifest = {'schema': 1, 'parent': parent, 'scope': selection['scope'], 'members': rows,
            'member_count': len(rows), 'member_bytes': sum(r['bytes'] for r in rows)}
(HERE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
paths.add(str((HERE / 'manifest.json').relative_to(ROOT)))
(HERE / 'paths.nul').write_bytes(b''.join(p.encode() + b'\0' for p in sorted(paths)))
git('add', '-f', '--pathspec-from-file=' + str(HERE / 'paths.nul'), '--pathspec-file-nul')
staged = set(git('diff', '--cached', '--name-only', '-z').decode().split('\0')) - {''}
demand(staged and staged <= paths, 'Unexpected staged paths')
# Preserve raw command evidence byte-for-byte, including platform whitespace.
source_paths = sorted(p for p in staged if not p.startswith('verification/'))
git('diff', '--cached', '--check', '--', *source_paths)
requests = b''.join((':' + r['path'] + '\n').encode() for r in rows)
raw = git('cat-file', '--batch', input=requests)
cursor = 0
for row in rows:
    end = raw.index(b'\n', cursor); header = raw[cursor:end].split()
    demand(len(header) == 3 and header[1] == b'blob', 'Missing staged blob')
    size = int(header[2]); data = raw[end + 1:end + 1 + size]
    demand(size == row['bytes'] and sha(data) == row['sha256'], 'Staged identity mismatch: ' + row['path'])
    cursor = end + size + 2
receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'argv': sys.argv, 'python': sys.version, 'parent': parent,
           'manifest_sha256': sha((HERE / 'manifest.json').read_bytes()),
           'members_verified': len(rows), 'staged_paths': sorted(staged),
           'GA_statuses_unchanged': True, 'W01_W18_G01_G38_D0_D8_intact': True,
           'evidence_mirrors_equal': True, 'staged_blob_identities_verified': True}
(HERE / 'prepared.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: receipt[k] for k in ['parent', 'manifest_sha256', 'members_verified']}))
