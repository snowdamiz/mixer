#!/usr/bin/env python3
"""Read-only seal/source verification under the pure operation guard."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
import offline_guard
offline_guard.install(HERE)
import hashlib
import json
ROOT = HERE.parents[1]
checks = []
def need(value, label):
    checks.append(label)
    if not value: raise RuntimeError(label)
def raw(path):
    for part in [*reversed(path.parents), path]:
        need(not part.is_symlink(), 'no symlink: ' + str(path))
    need(path.is_file(), 'regular: ' + str(path))
    return path.read_bytes()
def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
seal = json.loads(raw(HERE / 'seal.json'))
rows = seal['members']
need(rows == sorted(rows, key=lambda r:r['path']), 'member order')
need(len(rows) == len({r['path'] for r in rows}) == seal['member_count'], 'exact unique members')
need(sha(canonical(rows)) == seal['tree_sha256'], 'member tree')
need(sum(r['bytes'] for r in rows) == seal['total_bytes'], 'member bytes')
for row in rows:
    rel = Path(row['path'])
    need(not rel.is_absolute() and '..' not in rel.parts and rel.as_posix() == row['path'], 'canonical member path')
    data = raw(HERE / rel)
    need(len(data) == row['bytes'] and sha(data) == row['sha256'], 'bound member: ' + row['path'])
actual = []
for p in HERE.rglob('*'):
    rel = p.relative_to(HERE)
    if rel.parts[0] in {'logs', '__pycache__'} or rel.parts[0].startswith('pure-'): continue
    need(not p.is_symlink(), 'no extra symlink')
    if p.is_file() and rel.as_posix() != 'seal.json': actual.append(rel.as_posix())
need(sorted(actual) == [r['path'] for r in rows], 'exact shipping closure')
decision = json.loads(raw(HERE / 'decision.json'))
for name, row in decision['source']['bindings'].items():
    data = raw(ROOT / name)
    need(len(data) == row['bytes'] and sha(data) == row['sha256'], 'current dependency: ' + name)
overlay = json.loads(raw(HERE / 'overlay.json'))
text = raw(ROOT / overlay['base_path']).decode()
need(sha(text.encode()) == overlay['base_sha256'], 'original runner')
for change in overlay['changes']:
    need(text.count(change['before']) == 1, 'unique transform: ' + change['label'])
    text = text.replace(change['before'], change['after'])
need(text.encode() == raw(HERE / 'candidate_runner.py'), 'exact complete overlay')
need(sha(text.encode()) == overlay['candidate_sha256'] == decision['candidate']['sha256'], 'candidate binding')
pack = ROOT / 'verification/swift-envelope-ci-pack'
manifest = json.loads(raw(pack / 'manifest.json'))
need(sha(canonical(manifest['members'])) == manifest['tree_sha256'], 'frozen pack tree')
for row in manifest['members']:
    data = raw(pack / row['path'])
    need(len(data) == row['bytes'] and sha(data) == row['sha256'], 'frozen pack member: ' + row['path'])
need(offline_guard.DENIED == [], 'no real process attempt')
print(json.dumps({'schema': 1, 'passed': True, 'assertions': len(checks),
                  'tree_sha256': seal['tree_sha256'], 'member_count': len(rows),
                  'candidate_sha256': overlay['candidate_sha256'], 'python': sys.version,
                  'scope': 'pure source and seal verification; no runtime or process evidence'}, sort_keys=True))
