#!/usr/bin/env python3
"""Stage only frozen review packets and root metadata, excluding active lanes."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def git(*args, **kwargs):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True, **kwargs).stdout


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


demand(not (HERE / 'prepared.json').exists(), 'One-shot preparation already completed')
demand(git('branch', '--show-current').strip() == b'main', 'Expected main')
demand(not git('diff', '--cached', '--name-only'), 'Index must be empty')
parent = git('rev-parse', 'HEAD').decode().strip()
demand(parent == 'fb4c8f074f1a3e5eb2b1b1a45b44f0fa61a7cc62', 'Unexpected parent')
selection = json.loads((HERE / 'selection.json').read_text())
paths = set(selection['paths'])
for path in HERE.iterdir():
    if path.is_file() and path.name not in {'paths.nul', 'manifest.json', 'prepared.json'}:
        paths.add(str(path.relative_to(ROOT)))
# Add later terminal CI evidence if it has arrived since selection creation.
for path in (ROOT / 'verification/github-delivery-android-owner-candidate5').glob('ci-*.json'):
    paths.add(str(path.relative_to(ROOT)))
for path in paths:
    demand(not path.startswith(('native/', 'cli/', 'hosted/', '.github/', '.wrangler/')), 'Active or unrelated source selected')
    demand('swift-cache-state-c3-remaining-work-accounting' not in path and 'swift-cache-state-row-probe-proposal' not in path, 'Active proof selected')
    demand('android-environment-platform-implementation' not in path, 'Active Android implementation selected')
work = json.loads((ROOT / 'work-graph.json').read_text())
gates = json.loads((ROOT / 'gates/ga.json').read_text())
demand([p['id'] for p in work['packages']] == [f'W{i:02}' for i in range(1, 19)], 'W01-W18')
demand([g['id'] for g in gates['gates']] == [f'G{i:02}' for i in range(1, 39)], 'G01-G38')
old_gates = json.loads(git('show', 'HEAD:gates/ga.json'))
demand([(g['id'], g['status']) for g in old_gates['gates']] == [(g['id'], g['status']) for g in gates['gates']], 'GA status changed')
for key in ['fixtureCacheStateContractCandidate', 'privateOwnerEffectContractCandidate']:
    a = [p[key] for p in work['packages'] if key in p]
    b = [g[key] for g in gates['gates'] if key in g]
    demand(len(a) == 1 and a == b, 'Evidence mirror mismatch')
milestones = json.loads((ROOT / 'dogfood/receipts/milestones.json').read_text())['milestones']
demand([m['id'] for m in milestones] == [f'D{i}' for i in range(9)], 'D0-D8')
git('diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json')
rows = []
for name in sorted(paths):
    data = (ROOT / name).read_bytes()
    rows.append({'path': name, 'bytes': len(data), 'sha256': digest(data)})
manifest = {'schema': 1, 'parent': parent, 'scope': selection['scope'], 'members': rows,
            'member_count': len(rows), 'member_bytes': sum(r['bytes'] for r in rows)}
(HERE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
paths.add(str((HERE / 'manifest.json').relative_to(ROOT)))
(HERE / 'paths.nul').write_bytes(b''.join(p.encode() + b'\0' for p in sorted(paths)))
git('add', '-f', '--pathspec-from-file=' + str(HERE / 'paths.nul'), '--pathspec-file-nul')
staged = set(git('diff', '--cached', '--name-only', '-z').decode().split('\0')) - {''}
demand(staged <= paths, 'Unselected staged path')
demand(staged, 'No staged changes')
requests = b''.join((':' + r['path'] + '\n').encode() for r in rows)
raw = git('cat-file', '--batch', input=requests)
cursor = 0
for row in rows:
    end = raw.index(b'\n', cursor)
    header = raw[cursor:end].split()
    demand(len(header) == 3 and header[1] == b'blob', 'Staged blob missing')
    size = int(header[2]); data = raw[end + 1:end + 1 + size]
    demand(size == row['bytes'] and digest(data) == row['sha256'], 'Staged identity mismatch')
    cursor = end + size + 2
receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'argv': sys.argv, 'python': sys.version, 'parent': parent,
           'manifest_sha256': digest((HERE / 'manifest.json').read_bytes()),
           'members_verified': len(rows), 'staged_paths': sorted(staged),
           'active_product_and_proof_lanes_excluded': True, 'GA_statuses_unchanged': True,
           'W01_W18_G01_G38_D0_D8_intact': True, 'evidence_mirrors_equal': True,
           'staged_blob_identities_verified': True}
(HERE / 'prepared.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: receipt[k] for k in ['parent', 'manifest_sha256', 'members_verified', 'active_product_and_proof_lanes_excluded']}))
