#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json
OUT=Path(__file__).resolve().parent
ROOT=OUT.parent.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def write(n,d):(OUT/n).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def main():
 inputs=[]
 for n,h in [('initial-profile-source-action-scope-amendment.md','0f680dcfdeb3ae217bc18f91b7d006dd2c3ab0f545741b5e5260af62d106534f'),('initial-profile-source-action-scope-selection.json','7185ac67c7742f7142f4f7aca44628411da56b92dbfb1c56615c4a776d3991c9')]:
  b=(ROOT/'verification/swift-semantic-adapter-root-review'/n).read_bytes();assert sha(b)==h;p=OUT/'root-corrections'/n;p.write_bytes(b);inputs.append({'path':str(p.relative_to(OUT)),'bytes':len(b),'sha256':h})
 prior=ROOT/'verification/swift-cache-state-profile-adapter-independent/actual-review';sealbytes=(prior/'seal.json').read_bytes();assert sha(sealbytes)=='b94d01584dabd9882c3df6e4f7867872fe1666ba7fc72c576e0e48e7ab4a40e2';seal=json.loads(sealbytes)
 for m in seal['members']:
  b=(prior/m['path']).read_bytes();assert len(b)==m['bytes'] and sha(b)==m['sha256'],m['path']
 assert len(seal['members'])==1127 and sum(m['bytes'] for m in seal['members'])==324086953
 rows=[]
 for n,h in [('independent-accounting.json','ebeed856d7f7ac203a7dd168e665655435ec8284ae19fa2cfb8cb991fbc168f3'),('SOURCE_REVIEW.md','bd2ca018f8bbd6aabbd67ba323d586ef965b798c5941fc29291d9b962637fc45'),('decision.json','9bd8334faa2cf1c2bec85f179563ae36cf09a86f92e4358f8485d5eacf9d802f')]:
  b=(prior/n).read_bytes();assert sha(b)==h;p=OUT/'row-bound-inputs'/n;p.parent.mkdir(exist_ok=True);p.write_bytes(b);rows.append({'path':str(p.relative_to(OUT)),'bytes':len(b),'sha256':h})
 row=json.loads((prior/'independent-accounting.json').read_text());terms=row['source_work'];assert all(t['bound']==t['allowance']*t['multiplicity'] for t in terms);assert sum(t['bound'] for t in terms)==450652288
 added=json.loads((OUT/'candidate-evidence/accounting.json').read_text())['source_action_terms'];assert all(t['total']==t['maximum_items']*t['conservative_source_actions_per_item'] for t in added);assert sum(t['total'] for t in added)==521088
 # Same-unit reconciliation: collapsing each selected std primitive and pure
 # owner callback to one abstract action never increases the prior conservative
 # per-source-operation/byte-transfer allowances. Fixed explicit source loop
 # multiplicities and the independent requested-I/O extent do not change.
 write('abstract-action-reconciliation.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root_scope_inputs':inputs,'prior_row_custody':{'seal_sha256':sha(sealbytes),'members_verified':1127,'bytes_verified':324086953,'retained_inputs':rows},'selected_unit':'Abstract primitive/callsite actions plus cumulative requested-I/O bytes only','row_terms':terms,'added_terms':added,'row_term_mapping':[{'item':t['item'],'interpretation':'Fixed byte-extent requested I/O, counted independently of primitive call execution' if t['item']=='requested_IO_byte_extent' else 'Conservative allowance for explicit bounded row source actions/transfers; each selected std primitive charged once, internals excluded','unchanged_multiplicity':t['multiplicity'],'allowance_still_dominates_collapsed_primitive_model':True} for t in terms],'added_term_mapping':{'complete_budget_and_local':'Explicit fixed record/165-entry comparisons and source Result/borrow/error transfers; primitive equality/copy operations charged once; conservative allowances not multiplied by implementation retries','initial_state_and_constructors':'Explicit source iteration counts832 initial-state plus1344 original constructor; original explicit credits4928 are distinct from abstract actions','owner_allocation':'One selected standard AtomicU64::try_update primitive and its closed checked-add callback charged once; callback reevaluation and retry internals excluded, no actual retry count inferred','cleanup_and_fixed_paths':'Explicit actual fresh-cache pins/slots/fixed transfer paths; original return/tail drop-order and fixed complete fields; allocator/library internals excluded'},'original_constructor_explicit_Cache_credits_max':4928,'abstract_row':450652288,'abstract_added':521088,'abstract_joined':451173376,'same_unit_reconciled':True,'no_primitive_retry_or_callback_reevaluation_count':True,'all_actual_authored_source_evaluations_bound_qualified':False,'CPU_retry_wallclock_VMdebit_stack_RSS_bound_qualified':False,'not_a_capacity_reservation_or_release_gate':True,'requested_row_IO_calls_max':20000,'requested_row_IO_bytes_max':81920000,'acknowledged_row_bytes_max':2560000,'new_source_test_cap_deadline_changes':False,'source_object_union_qualified_separately':True})
 print('PASS same-unit reconciliation: row450652288+added521088=abstract451173376; explicit primitive/callsite/requested-I/O scope only; actual callback/CPU/retry bounds remain unqualified.')
if __name__=='__main__':main()
