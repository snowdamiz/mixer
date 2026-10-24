"""Inventory selected delivery sizes only, without Git or runtime execution."""
from pathlib import Path
import hashlib, json, os, sys
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
V7 = ROOT / 'verification/swift-calls-dispatch/v7-fixture-expectations'
def read(p): return json.loads(p.read_bytes())
files = {}; groups = {}
def bound(label, base, bindings):
    groups[label] = len(bindings)
    for rel, row in bindings.items():
        p = base / rel
        assert p.is_file() and not p.is_symlink() and p.stat().st_size == row['bytes']
        files[str(p.relative_to(ROOT))] = row
bound('v7', V7, read(V7 / 'review-seal.json')['bindings'])
history = read(V7 / 'v6-history-bindings.json')
bound('v6-history', (V7 / history['path']).resolve(), history['files'])
for name in ['swift-calls-dispatch-v7-independent-review', 'swift-calls-dispatch-node-oracle-qualification']:
    folder = ROOT / 'verification' / name; seal = read(folder / 'review-seal.json')
    bound(name, folder, seal['bindings']); bound(name + '-documents', ROOT, seal.get('documents', {}))
bound('supplemental-history', ROOT, read(ROOT / 'verification/swift-calls-dispatch-root-review/v7-supplemental-history.json')['files'])
for folder in ['verification/github-ci-3f6be79b-engine', 'verification/github-ci-6291ea80-engine', 'verification/github-delivery-9a9c0e00']:
    for p in (ROOT / folder).rglob('*'):
        if p.is_file():
            assert not p.is_symlink(); files[str(p.relative_to(ROOT))] = {'bytes': p.stat().st_size}
extra = ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json', 'docs/swift-dispatch-v7-runtime-checkpoint.md']
for name in ['v7-supplemental-history.json', 'v7-runtime-selection.json', 'sealed-v7/receipt.json', 'sealed-v7/read-only.stdout', 'sealed-v7/read-only.stderr']:
    extra.append('verification/swift-calls-dispatch-root-review/' + name)
for name in extra:
    p = ROOT / name
    if p.is_file(): files[name] = {'bytes': p.stat().st_size}
links = read(V7 / 'shared-evidence-links.json')
for row in links:
    p = V7 / row['path']; assert p.is_symlink() and os.readlink(p) == row['target']
large = [{'path': k, **v} for k, v in sorted(files.items()) if v['bytes'] >= 95_000_000]
assert {x['path'] for x in large} == {
    'verification/swift-calls-dispatch/v6-fixture-expectation/inventory-v5.json',
    'verification/swift-calls-dispatch/v7-fixture-expectations/compiler-partitions-v5.json'}
parent = V7.parent; prior = read(parent / 'review-seal.json')['bindings']
assert not any(v['bytes'] >= 95_000_000 for v in prior.values())
result = {'scope': 'Selected root delivery script input sizes, plus inherited V5 bound sizes; no Git status or tracked-delta evaluation',
          'thresholdBytes': 95_000_000, 'groups': groups, 'uniqueSelectedRegularPaths': len(files),
          'unmodifiedSharedSymlinks': len(links), 'oversized': large,
          'inheritedV5Bindings': len(prior), 'inheritedV5Oversized': 0,
          'existingEvidenceWritten': False, 'gitOrRuntimeExecuted': False,
          'rootPreparationSourceSHA256': hashlib.sha256(Path('/tmp/mixer-v7-delivery-prepare.py').read_bytes()).hexdigest(),
          'argv': [sys.executable, '-B', str(Path(__file__))]}
(HERE / 'delivery-inventory.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
print(len(files), 'selected regular paths;', len(links), 'unchanged links;', len(large), '>=95MB files')
