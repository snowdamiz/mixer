#!/usr/bin/env python3
"""Freeze only this independent bounded rejection; never mutate any input."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def digest(x):return hashlib.sha256(x).hexdigest()
def put(name,obj):(HERE/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
assert not (HERE/'seal.json').exists(), 'An existing independent seal is immutable'
models=json.loads((HERE/'model-results.json').read_text())
g4=json.loads((HERE/'G4-independent-bound.json').read_text())
put('results.json',{'at':datetime.now(timezone.utc).isoformat(),'python':sys.version,
 'status':'independent bounded rejection; required revision',
 'proposal_seal_sha256':'d4cad24a902d5a8551fa51a93b445382be59027e129ac2f65408bd22666ae736',
 'source_revision_context':'d275c072b6c89b8e99213e4eb4dafdc4722f5f40',
 'live_tree_clean_claim':False,
 'custody_passed':True,'changed_regions_and_complete_suffix_binding_passed':True,
 'model_case_counts':{k:models[k] for k in ('sort_cases','prefix_cases','arena_address_cases','candidate_padding_and_cleanup_cases')},
 'G4_necessary_floor':g4['selected_model_assignment_necessary_floor'],
 'G4_cap':768,'G4_cap_failure_proved_under_selected_component_model':True,
 'G2_G3_G5_producer_bound_acceptance':False,
 'replacement_G2_G3_G5_complete_counts_claimed':False,
 'G6_unchanged_body_and_actual_outer_caller_boundaries_rebound':True,
 'layout_amendment_or_product_source_selected':False,
 'whole29344_lifetime_accepted':False,'implementation_compiler_or_runtime_accepted':False,
 'native_capture_or_process_inventory_execution':False,'GA_qualified':False,
 'only_owned_directory_mutated':True,'commits_pushes_or_customer_messages':False,
 'finite_scope_stop_reason':'Necessary G4 lower bound already exceeds cap768; root requested sealed rejection, no repair in this review.'})
rows=[]
for p in sorted(HERE.rglob('*')):
 if not p.is_file() or p.name in ('seal.json','seal-verification.json'):continue
 b=p.read_bytes();rows.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':digest(b)})
put('seal.json',{'schema':1,'at':datetime.now(timezone.utc).isoformat(),
 'status':'independent bounded rejection; preserve proposal; required revision',
 'member_count':len(rows),'member_bytes':sum(r['bytes'] for r in rows),'members':rows,
 'source_tree_digest':digest(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()),
 'source_tree_digest_method':'SHA256 compact sorted-key JSON of path-sorted independent member rows',
 'source_model_only':True,'producer_packet_changed':False,
 'compiler_runtime_native_capture_or_process_inventory_execution':False,
 'implementation_or_layout_selection_accepted':False})
raw=(HERE/'seal.json').read_bytes()
print(json.dumps({'seal_sha256':digest(raw),'member_count':len(rows),'member_bytes':sum(r['bytes'] for r in rows)},indent=2))
