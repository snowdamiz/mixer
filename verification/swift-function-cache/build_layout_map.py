#!/usr/bin/env python3
"""Bind conservative named-object sums to executed target layouts, not RSS."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'qualification/named/receipt.json').read_text())
def key(s):return re.sub(r'\s+','',s)
by_mode={}
for c in r['commands']:
 if any(a.endswith('::frozen_layout_allocation_work_error_snapshots')for a in c['argv']):
  mode='release'if '--release'in c['argv']else'debug'
  by_mode[mode]={key(t):{'size':int(n),'align':int(a)}for t,n,a in re.findall(r'^layout (.*?) (\d+) (\d+)$',c['stdout'],re.M)}
assert set(by_mode)=={'debug','release'}and by_mode['debug']==by_mode['release']
layouts=by_mode['debug']
# Reader and legacy-only types are printed by the executed unchanged-engine replay.
# Use current-engine commands (odd entries), checking every mode/feature observation.
parity=json.loads((HERE/'legacy-parity-receipt.json').read_text())
legacy_layouts=None
for c in parity['commands'][1::2]:
 observed={key(t):{'size':int(n),'align':int(a)}for t,n,a in re.findall(r'^layout (.*?) (\d+) (\d+)$',c['stdout'],re.M)}
 if legacy_layouts is None:legacy_layouts=observed
 assert observed==legacy_layouts
for ty,shape in legacy_layouts.items():
 if ty in layouts:assert layouts[ty]==shape
 else:layouts[ty]=shape
src=(ROOT/'vm/src/experimental_swift_reactor/cache.rs').read_text()
functions=['cache_cleanup_temporary_bytes','cache_construction_bytes','cache_operation_bytes']
sums={}
for f in functions:
 body=src[src.index('fn '+f):];body=body[body.index('sum_named(&['):body.index('])',body.index('sum_named(&['))+2]
 rows=[]
 for count,ty in re.findall(r'\(\s*(\d+)\s*,\s*size_of::<(.*?)>\(\)\s*,?\s*\)',body,re.S):
  ty=key(ty);shape=layouts[ty];rows.append({'type':ty,'count':int(count),**shape,'bytes':int(count)*shape['size']})
 assert rows
 sums[f]={'objects':rows,'bytes':sum(x['bytes']for x in rows)}
base=layouts['SwiftFunctionCache']['size']-layouts['ValidatedSwiftReactor']['size']
header=base+sums['cache_cleanup_temporary_bytes']['bytes']
foundation=[(3,'ValidatedSwiftReactor'),(3,'RuntimeControl'),(3,'AdoptedProof'),(4,'SwiftRunFailure'),(4,'SwiftRunUsage'),(6,'ReservationTicket'),(6,'Option<WasiUsage>')]
foundation=[{'type':ty,'count':count,**layouts[ty],'bytes':count*layouts[ty]['size']}for count,ty in foundation]
record={'schema':'mixer-cache-target-named-layouts-v1','target':'aarch64-apple-darwin','scope':'named Rust logical reservation model; no compiler-stack, allocator-overhead or RSS claim','debug_release_identical':True,'layouts':layouts,'bounds':sums,'exclusive_cache_header':{'cache':layouts['SwiftFunctionCache']['size'],'already_retained_proof':layouts['ValidatedSwiftReactor']['size'],'exclusive':base,'cleanup':sums['cache_cleanup_temporary_bytes']['bytes'],'total':header},'foundation':{'objects':foundation,'bytes':sum(x['bytes']for x in foundation)},'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'legacy_parity_receipt_sha256':hashlib.sha256((HERE/'legacy-parity-receipt.json').read_bytes()).hexdigest(),'named_receipt_sha256':hashlib.sha256((HERE/'qualification/named/receipt.json').read_bytes()).hexdigest()}
assert record['foundation']['bytes']==16504
for c in r['commands']:
 if any(a.endswith('::frozen_layout_allocation_work_error_snapshots')for a in c['argv']):
  m=re.search(r'bounds cleanup=(\d+) header=(\d+) construction=(\d+) operation=(\d+) foundation=(\d+)',c['stdout'])
  expected=[sums['cache_cleanup_temporary_bytes']['bytes'],header,sums['cache_construction_bytes']['bytes'],sums['cache_operation_bytes']['bytes'],record['foundation']['bytes']]
  assert list(map(int,m.groups()))==expected
(HERE/'layout-map.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v['bytes']for k,v in sums.items()}|{'header':header,'foundation':record['foundation']['bytes']}))
