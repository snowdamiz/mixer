#!/usr/bin/env python3
"""Freeze/verify only this proposal's file custody, never source acceptance."""
import datetime, hashlib, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def member(p):
    b=p.read_bytes(); return {'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha(b)}
paths=sorted(p for p in HERE.rglob('*') if p.is_file() and p.name!='seal.json')
rows=[member(p) for p in paths]
if '--verify' in sys.argv:
    seal=json.loads((HERE/'seal.json').read_text())
    if rows!=seal['members']: raise SystemExit('sealed member drift')
    print(json.dumps({'seal_sha256':sha((HERE/'seal.json').read_bytes()),'member_count':len(rows),'member_bytes':sum(x['bytes'] for x in rows),'verified':True},indent=2))
else:
    source=json.loads((HERE/'source-assembly.json').read_text())
    result=json.loads((HERE/'check-result.json').read_text())
    if result['arithmetic']['upper_groups']>2560: raise SystemExit('G2 bound over cap')
    seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(HERE/'freeze.py')],'python':sys.version,'status':'unselected feasible G2 source/model proposal; independent review and root selection required','source_sha256':source['source_sha256'],'input_tree_digest':json.loads((HERE/'inputs.json').read_text())['tree_digest'],'G2_complete_conservative_upper':2332,'G2_cap':2560,'G2_valid_64_resident_64_live_pin_witness':2230,'G2_changed_Control_bound':result['G2_Control_max'],'G2_Control_allowance':1280,'G3_G4_G5_complete_bounds_accepted':False,'whole_lifetime_or_implementation_accepted':False,'runtime_compiler_native_UI_capture_process_inventory_Git_hosted_executed':False,'GA_qualified':False,'member_count':len(rows),'member_bytes':sum(x['bytes'] for x in rows),'members':rows}
    (HERE/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'seal_sha256':sha((HERE/'seal.json').read_bytes()),'member_count':len(rows),'member_bytes':seal['member_bytes'],'status':seal['status']},indent=2))
