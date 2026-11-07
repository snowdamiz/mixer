#!/usr/bin/env python3
"""Freeze scoped proposal2 review support, without selecting numeric values."""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
from admit import verify_proposal,verify_old
ROOT=Path(__file__).resolve().parents[2];OWN=Path(__file__).resolve().parent
DOC=ROOT/'docs/swift-ordered-retention-analyzer-envelope-correction-accounting-review-2.md'
def sha(data):return hashlib.sha256(data).hexdigest()
def write_json(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def main():
 assert not(OWN/'seal.json').exists() and not(OWN/'seal.sha256').exists()
 proposal=verify_proposal();old=verify_old();audit=json.loads((OWN/'commands/audit-1/receipt.json').read_bytes())
 assert audit['C1_resolved_for_proposal'] and audit['C2_resolved_for_proposal'] and not audit['new_actionable_findings']
 receipt={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':'proposal2-accounting-proposal-supported-ready-for-root-selection',
  'scope':'immutable proposal2 source/operation/funding/type/edge/memory review; no numeric or implementation selection',
  'proposal':proposal,'old_seals_verified':old,'source_sha256':'e86ef43a99f99245c78308666f91f5147981859ca03fa3f97e62d46993667535',
  'ledger_sha256':'8ba395af50cd827242ce121f60dade5ebd270956602454fbd7345cf8f89c0a0f','numeric_sha256':'736947e71b0fcaf102ac2c64438730afbc6d2954ac082134066f73fae8211550',
  'funding_sha256':'baec5fde93a784a20351e48f1200cb1d7378c0999f82aa4dd84e94aba897581d',
  'own_document_sha256':sha(DOC.read_bytes()),'audit_receipt':'commands/audit-1/receipt.json','C1_resolved':True,'C2_resolved':True,'findings':[],
  'rows_checked':116,'transfer_edges_checked':108,'input_result_funding_classes_checked':8,'accepted_framing22_mappings':7,
  'unchanged_source_layout_facts_reused':32,'new_Rust_or_runtime_probes':0,
  'named_logical_bytes':24656,'reserved_logical_bytes':41984,'transient_ceiling':65536,
  'existing_fixed_report_upper':6245,'new_fixed_report_reservations':201,'combined_report_upper':6446,
  'proposal_source_bounds_accepted_for_root_consideration':True,'425_is_upper_not_minimum_lower_bound':True,
  'numeric_values_selected':False,'historical128_192_qualified':False,'implementation_accepted':False,'combined_final_source_qualified':False,
  'product_acceptance':False,'fullReplayAccepted':False,'storedPrefixValidated':False,'ga_gate_promotions':0,
  'producer_scripts_tests_or_frozen_runners_executed':False,'native_capture_process_or_device_discovery':False,
  'cleanup':audit['cleanup'],'pending':['explicit root contract/numeric selection','constant update in separate producer packet','fresh selected-final-source behavior/budget/oracle evidence','combined final-source qualification','semantic/custody/target/native/device/signing/store/FieldLog/GA']}
 write_json(OWN/'review-receipt.json',receipt)
 excluded={OWN/'seal.json',OWN/'seal.sha256'};files=sorted([DOC]+[p for p in OWN.rglob('*') if p.is_file() and p not in excluded]);members=[]
 for path in files:
  raw=path.read_bytes()
  if path.suffix in ['.py','.md','.rs']:assert not any(line.endswith((' ','\t')) for line in raw.decode().splitlines()),str(path)
  if path.suffix=='.json':json.loads(raw)
  members.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)})
 assert verify_proposal()==proposal and verify_old()==old
 write_json(OWN/'seal.json',{'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':receipt['status'],'scope':receipt['scope'],'members':members,'excluded':[str(p.relative_to(ROOT)) for p in sorted(excluded)],'numeric_values_selected':False,'implementation_accepted':False})
 digest=sha((OWN/'seal.json').read_bytes());(OWN/'seal.sha256').write_text(digest+'\n')
 print(json.dumps({'status':receipt['status'],'seal_sha256':digest,'members':len(members),'bytes':sum(m['bytes'] for m in members),'findings':0},sort_keys=True))
if __name__=='__main__':main()
