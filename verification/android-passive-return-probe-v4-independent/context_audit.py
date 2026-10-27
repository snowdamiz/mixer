#!/usr/bin/env python3
"""Record immutable packet/source/class context after the bounded replay."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = ROOT/'verification/android-editor-membership-compiled-boundary-qualification'
def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
frozen_path = BASE/'passive-return-probe-v4/run-1/source-freeze.json'
frozen = json.loads(frozen_path.read_text())
context_path = BASE/'state-replay-candidate-v2/product-context.json'
context = json.loads(context_path.read_text())
seal_path = BASE/'state-replay-candidate-v2/seal.json'
seal_identity = identity(seal_path)
assert seal_identity['sha256'] == '997ffefd7eaad9ba8e0f6ddb0aa8654a5cee37304be8f49927874229e3f73a30'
seal = json.loads(seal_path.read_text())
members = seal['members']
if isinstance(members, list):
    members = {row['path']: {'bytes':row['bytes'], 'sha256':row['sha256']} for row in members}
assert identity(context_path) == members['product-context.json']
source_map = {Path(row['path']).name: {'bytes': row['bytes'], 'sha256': row['sha256']}
              for row in frozen['sources'] if '/inputs/source/' in row['path']}
assert len(source_map) == 16 and source_map == context['source_map']
for variant in ('v3', 'v4'):
    assert json.loads((OUT/('product-class-map-'+variant+'.json')).read_text()) == context['class_map']
assert context['context_id'] == '1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
data = {'source_freeze': identity(frozen_path), 'product_source_tree': frozen['exact_product_tree'],
        'selected_v2_seal': seal_identity, 'selected_context': identity(context_path),
        'context_id': context['context_id'], 'source16_exact_equal': True,
        'v3_and_v4_product209_exact_equal': True,
        'independent_runner': identity(OUT/'replay.py'),
        'independent_controls': identity(OUT/'IndependentAttributeControls.java')}
(OUT/'source-context.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data,indent=2))
