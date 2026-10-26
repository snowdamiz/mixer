#!/usr/bin/env python3
"""Seal this owned review-only packet after exact-source verification."""
from pathlib import Path
import hashlib,json,datetime,sys
D=Path(__file__).resolve().parent
if (D/'seal.json').exists():raise SystemExit('Already frozen')
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
source=json.loads((D/'source-verification.json').read_text())
assert source['selected_final_runs']==['host-8','cross-3']
assert json.loads((D/'runs/host-8/receipt.json').read_text())['status']=='passed-host-only'
assert json.loads((D/'runs/cross-3/receipt.json').read_text())['status']=='passed-cross-only'
assert not list(D.rglob('__pycache__'))
# Nested immutable input seals are themselves members; only this packet's seal is excluded.
members=[{'path':str(p.relative_to(D)),**ident(p)} for p in sorted(D.rglob('*')) if p.is_file() and p!=D/'seal.json']
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Frozen complete-source focus-history correction for independent review only; no canonical/native/OTA/GA acceptance','product_source_tree_digest':source['product_source_tree_digest'],'complete_host_closure_tree_digest':source['host_closure_tree_digest'],'tree_digest_encoding':'SHA256 compact sorted-key JSON per-file bytes/SHA256 identity map; product map relative to source/; closure map nested source/host-leaves/tests','selected_final_runs':['host-8','cross-3'],'native_or_GA_accepted':False,'members':members}
(D/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'seal':str(D/'seal.json'),'sha256':ident(D/'seal.json')['sha256'],'members':len(members),'bytes':sum(row['bytes'] for row in members),'product_source_tree_digest':source['product_source_tree_digest']}))
