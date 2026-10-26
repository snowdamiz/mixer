#!/usr/bin/env python3
"""Freeze this independent packet only; verify without writing any files."""
import datetime,hashlib,json,pathlib,sys
D=pathlib.Path(__file__).resolve().parent
ROOT=D.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def need(v,m):
 if not v:raise SystemExit(m)
def inventory():
 return [{'path':str(p.relative_to(ROOT)),'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for p in sorted(D.rglob('*')) if p.is_file() and p.name!='seal.json']
rows=inventory()
if '--verify' in sys.argv:
 x=json.loads((D/'seal.json').read_text());need(rows==x['members'],'independent packet changed');need(len(rows)==x['member_count'] and sum(x['bytes'] for x in rows)==x['member_bytes'],'member totals')
 # Also ensure the producer seal and actual source still have exact identities.
 for path,digest in x['frozen_external_inputs'].items():need(sha((ROOT/path).read_bytes())==digest,'external input changed '+path)
 print(json.dumps({'verified':True,'seal_sha256':sha((D/'seal.json').read_bytes()),'member_count':len(rows),'member_bytes':sum(x['bytes'] for x in rows)}))
else:
 result=json.loads((D/'check-result.json').read_text());inputs=json.loads((D/'inputs.json').read_text());need(result['corrected_complete_G2_upper']['groups']==2494,'review mismatch')
 x={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],'python':sys.version,'input_tree_digest':inputs['tree_digest'],'source_sha256':result['source_sha256'],'producer_seal_sha256':result['producer_seal_sha256'],'status':'independent conditional scoped source/accounting acceptance; root selection required','producer_original_exact_totals_accepted':False,'complete_G2_conservative_upper':result['corrected_complete_G2_upper'],'valid_witness':result['corrected_valid_witness'],'scoped_added_Control':1220,'scoped_added_Wire':24,'scoped_added_Setup':80,'whole_lifetime_G3_G4_G5_implementation_native_GA_accepted':False,'member_count':len(rows),'member_bytes':sum(r['bytes'] for r in rows),'members':rows,'frozen_external_inputs':{'verification/swift-cache-state-row-probe-proposal/seal.json':result['producer_seal_sha256'],'verification/swift-cache-state-row-probe-proposal/source/cache_state.rs.txt':result['source_sha256']},'producer_code_Rust_compiler_native_UI_capture_Git_process_inventory_hosted_executed':False}
 (D/'seal.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n');print(json.dumps({'created':True,'seal_sha256':sha((D/'seal.json').read_bytes()),'member_count':len(rows),'member_bytes':x['member_bytes']}))
