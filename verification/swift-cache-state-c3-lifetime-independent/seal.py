#!/usr/bin/env python3
"""Seal only this independent directory; never alter any input packet."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
manifest=HERE/'seal.json'
def sha(data):return hashlib.sha256(data).hexdigest()
def rows():
    return [{'path':str(p.relative_to(ROOT)),'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())}
            for p in sorted(HERE.rglob('*')) if p.is_file() and p!=manifest]
if '--verify' in sys.argv:
    d=json.loads(manifest.read_text())
    current=rows()
    if current!=d['members'] or len(current)!=d['member_count'] or sum(r['bytes'] for r in current)!=d['member_bytes']:
        raise SystemExit('independent packet seal mismatch')
    print(json.dumps({'status':'seal-verified','sha256':sha(manifest.read_bytes()),
                      'members':len(current),'bytes':sum(r['bytes'] for r in current)}))
else:
    current=rows()
    d={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'python':sys.version,
       'argv':sys.argv,'scope':'finite independent C3 lifetime source review and bounded mapping addendum',
       'members':current,'member_count':len(current),'member_bytes':sum(r['bytes'] for r in current),
       'source_sha256':'0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8',
       'producer_seal_sha256':'703bf7ca338dac74574c60a7ac42addcd4d1bc44645d559dd05ca0c4dad56c22',
       'candidate_seal_sha256':'7044a00eef658d8c729e7301c0923ed193ec405c6c6009989a964b3159bad12f',
       'root_selection_required':True,'whole_lifetime_acceptance_granted':False,
       'original_exact_phase_completeness_accepted':False,'numeric_caps_changed':False,
       'compiler_product_runtime_native_UI_capture_process_inventory_Git_hosted_actions':False,
       'product_or_old_packet_writes':False,'GA_qualified':False}
    manifest.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'sealed','sha256':sha(manifest.read_bytes()),
                      'members':len(current),'bytes':d['member_bytes']}))
