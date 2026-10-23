#!/usr/bin/env python3
"""Bind executed named tests, exact sums and independently replayed legacy layouts."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def key(s):return re.sub(r'\s+','',s)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((HERE/'qualification/named/receipt.json').read_text());assert r['status']=='named_synthetic_commands_passed_review_pending'
phase=json.loads((HERE/'preflight-root-tail-map.json').read_text())
assert digest(ROOT/phase['source'])==phase['source_sha256']
by_mode={}
for c in r['commands']:
 if any(a.endswith('::frozen_layout_allocation_work_error_snapshots') for a in c['argv']):
  mode='release' if '--release' in c['argv'] else 'debug'
  by_mode[mode]={key(t):{'size':int(n),'align':int(a)}for t,n,a in re.findall(r'^layout (.*?) (\d+) (\d+)$',c['stdout'],re.M)}
  assert list(map(int,re.search(r'bounds cleanup=(\d+) header=(\d+) construction=(\d+) operation=(\d+) foundation=(\d+)',c['stdout']).groups()))==list(phase['observed_bounds'].values())
assert set(by_mode)=={'debug','release'}and by_mode['debug']==by_mode['release']
layouts=by_mode['debug']
assert layouts=={k:{'size':v['size'],'align':v['align']}for k,v in phase['layouts'].items()}
parity=json.loads((HERE/'legacy-parity-receipt.json').read_text());assert parity['status']=='pass'
legacy_layouts=None
for c in parity['commands'][1::2]:
 observed={key(t):{'size':int(n),'align':int(a)}for t,n,a in re.findall(r'^layout (.*?) (\d+) (\d+)$',c['stdout'],re.M)}
 if legacy_layouts is None:legacy_layouts=observed
 assert observed==legacy_layouts
for ty,shape in legacy_layouts.items():
 if ty in layouts:assert layouts[ty]==shape
 else:layouts[ty]=shape
sums={k.removeprefix('compute_'):v for k,v in phase['component_checked_sums'].items()}
exclusive=layouts['SwiftFunctionCache']['size']-layouts['ValidatedSwiftReactor']['size']
header=exclusive+sums['cache_cleanup_temporary_bytes']['bytes'];assert header==phase['observed_bounds']['header']
record={'schema':'mixer-cache-target-named-layouts-v2','target':'aarch64-apple-darwin','scope':phase['scope'],'debug_release_identical':True,'layouts':layouts,'bounds':sums,'exclusive_cache_header':{'cache':layouts['SwiftFunctionCache']['size'],'already_retained_proof':layouts['ValidatedSwiftReactor']['size'],'exclusive':exclusive,'cleanup':sums['cache_cleanup_temporary_bytes']['bytes'],'total':header},'foundation':{'objects':phase['foundation_counts'],'bytes':16504},'phase_map':'preflight-root-tail-map.json','phase_map_sha256':digest(HERE/'preflight-root-tail-map.json'),'source_sha256':phase['source_sha256'],'legacy_parity_receipt_sha256':digest(HERE/'legacy-parity-receipt.json'),'named_receipt_sha256':digest(HERE/'qualification/named/receipt.json')}
(HERE/'layout-map.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(phase['observed_bounds']))
