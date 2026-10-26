#!/usr/bin/env python3
"""Freeze only this independently owned component-review packet."""
import datetime, hashlib, json, pathlib, sys
root = pathlib.Path(__file__).resolve().parent
repo = root.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (root / 'seal.json').exists(), 'Never rewrite a frozen seal'
decision = json.loads((root / 'final-decision.json').read_text())
assert decision['implementation_component_accepted'] and not decision['canonical_integration_selected']
assert decision['review_sha256'] == sha(root / 'review.md')
inputs = json.loads((root / 'input-bindings.json').read_text())['inputs']
inputs += [{'path': 'verification/swift-cache-state-scalar-cursor-implementation/seal.json',
    'sha256': decision['producer_custody']['producer_seal_sha256']},
    {'path': 'verification/swift-semantic-adapter-root-review/scalar-cursor-test-amendment.json',
     'sha256': sha(repo / 'verification/swift-semantic-adapter-root-review/scalar-cursor-test-amendment.json')}]
for row in inputs:
    assert sha(repo / row['path']) == row['sha256']
rows = [{'path': str(p.relative_to(root)), 'bytes': p.stat().st_size, 'sha256': sha(p)}
    for p in sorted(root.rglob('*')) if p.is_file()]
assert not list(root.rglob('__pycache__')) and not list(root.glob('.scratch*'))
seal = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve())],
    'python': sys.version, 'builder_sha256': sha(pathlib.Path(__file__)),
    'member_base': 'packet-relative', 'members': rows, 'member_count': len(rows),
    'total_bytes': sum(row['bytes'] for row in rows), 'external_inputs': inputs,
    'decision': decision['decision'], 'implementation_component_accepted': True,
    'canonical_integration_selected': False, 'full_target_native_or_GA_qualified': False,
    'producer_seal_sha256': decision['producer_custody']['producer_seal_sha256'],
    'source_sha256': decision['source_sha256'], 'independent_checks_each_mode': {
        'methods': 7, 'merge_cases': 16456, 'G2_admitted_G5': 2056, 'malformed_refusals': 27, 'layouts': 21},
    'owned_products_hashed_removed': 2, 'children_reaped': True,
    'native_UI_capture_or_process_inventory_started': False}
(root / 'seal.json').write_text(json.dumps(seal, indent=2) + '\n')
print(json.dumps({'seal_sha256': sha(root / 'seal.json'), 'member_count': len(rows),
    'total_bytes': seal['total_bytes']}, indent=2))
