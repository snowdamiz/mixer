#!/usr/bin/env python3
"""Seal or verify only this new lane. No source regeneration or Git access."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SEAL=HERE/'seal.json'
def sha(data): return hashlib.sha256(data).hexdigest()
def members():
    return [{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(HERE.rglob('*')) if p.is_file() and p!=SEAL]
if '--verify' in sys.argv:
    expected=json.loads(SEAL.read_text())
    actual=members()
    if actual!=expected['members']: raise SystemExit('FAIL: sealed member drift')
    print(json.dumps({'status':'sealed-packet-verified','members':len(actual),'bytes':sum(p['bytes'] for p in actual),'seal_sha256':sha(SEAL.read_bytes()),'acceptance':False},sort_keys=True))
else:
    if SEAL.exists(): raise SystemExit('Refusing to overwrite an existing seal')
    rows=members()
    output={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'scope':'Source-only complete C3 lifetime/role proposal requiring independent review','source_sha256':'0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8','candidate_seal_sha256':'7044a00eef658d8c729e7301c0923ed193ec405c6c6009989a964b3159bad12f','source_tree_digest':'45bd39ce40ce25cba9304dfd014d8ad3da1b9ee83f9e55de91618da8b77d7dac','member_count':len(rows),'member_bytes':sum(p['bytes'] for p in rows),'members':rows,'fixed_role_union':29344,'reserved_bytes':41984,'global_bytes':65536,'candidate_bytes':2048,'complete_public_Result_bytes':488,'lifetime_proof_accepted':False,'implementation_or_GA_accepted':False,'product_or_native_or_capture_executed':False,'old_packets_mutated':False,'Git_actions':False}
    SEAL.write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'proposal-sealed','members':len(rows),'bytes':output['member_bytes'],'seal_sha256':sha(SEAL.read_bytes()),'acceptance':False},sort_keys=True))
