"""Deterministic S1-S5 correction report; writers are refused after sealing."""
import json,os,sys
from pathlib import Path
from mir_graph import sha,require
D=Path(__file__).resolve().parent
def main(check=False):
 g=json.loads((D/'graph.json').read_text());a=json.loads((D/'analysis.json').read_text());c=json.loads((D/'candidate.json').read_text())
 catalog=json.loads((D/'authored-contracts.json').read_text());custody=json.loads((D/'custody.json').read_text())
 failures=[]
 for attempt in sorted((D/'commands').glob('attempt-*')):
  if str(attempt)==os.environ.get('MIXER_STRING_PACKET_ACTIVE_ATTEMPT'):continue
  receipt=attempt/'receipt.json';supplement=attempt/'recorder-failure.json'
  if receipt.exists():
   r=json.loads(receipt.read_text())
   if r['exit_code']!=0:failures.append({'path':str(receipt.relative_to(D)),'sha256':sha(receipt.read_bytes()),'exit_code':r['exit_code'],'status':'failed and preserved'})
  elif supplement.exists():failures.append({'path':str(supplement.relative_to(D)),'sha256':sha(supplement.read_bytes()),'exit_code':1,'status':'failed recorder; original incomplete attempt preserved; not a passing receipt'})
  else:require(False,'unexplained-incomplete-attempt:'+str(attempt))
 value={'schema':1,'status':'implemented-S1-S5-exact-authored-binding-and-balanced-typed-parser-candidate',
  'source_tree_sha256':c['source_tree_sha256'],'host_tree_sha256':c['host_tree_sha256'],
  'root_return_sha256':'9dba765988b0e464fe58245520586696945e9f4bbd87f1ca2b8bc4051cf68440',
  'binding_correction_contract_sha256':'e8c3364612e7e9f90b9da0456d54c1c806968474676b0efe6b5c038309976974',
  'requirements':{
   'S1':'Exact definition or complete finite target/receiver/trait/member/generic contract only; no shortname fallback. The 423 target aliases retain explicit source owner/declaration identity, not body-hash authorization.',
   'S2':'Only complete reviewed B, B::Access, P, C, impl MeterControl, D and SnapshotView identities enter the exact roster. Foreign receiver/trait/namespace variants miss and refuse.',
   'S3':'Balanced complete Fn/FnMut/FnOnce, tuple/array/generic header syntax. All 2009 params/return/local type inventories independently agree; both selected headers and the full nine-header historical discrepancy roster are retained.',
   'S4':'Every authored call checks arity, exact reviewed argument/result variant and structural positional equations with consistent T/R/N substitutions. Named callbacks and closure adapters have complete typed contracts; callee _0 declarations are also bound.',
   'S5':'All original graph/origin/port/semantic caller evidence and failed receipts retained; no string/root/budget/operational selection.'},
  'counts':c['counts'],'authored_contracts':{'exact_targets':len(catalog['contracts']),'direct_typed_signatures':sum(len(x['signatures']) for x in catalog['contracts'].values()),'named_function_item_signatures':sum(len(x['named_callback_signatures']) for x in catalog['contracts'].values()),'exact_closure_adapter_contracts':len(catalog['closure_contracts'])},
  'current_header_discrepancies':a['typed_header_discrepancies'],'current_simple_local_call_discrepancies':a['simple_local_call_argument_or_result_discrepancies'],
  'historical_affected_headers':[x['function'] for x in a['whole_compiler_pool_header_misparses']],
  'preserved_methods':{'original_producer':14,'first_correction':16,'prior_independent_adverse':17,'new_exact_binding':17,'total':64},
  'full_MIR_negative_cases':['foreign Fault namespace at f0730 line20','std::future_vendor Fault namespace','unknown Mint trait for authored Fault','foreign Policy namespace','Foreign SharedControl receiver','Foreign MeterControl receiver','missing authored code argument','changed authored kind argument','changed nested authored result','changed named function-item result','unknown named function item','changed closure parameter header'],
  'current_failed_attempts_preserved':failures,'additional_frozen_failed_attempts':custody['additional_failure_roster'],
  'semantic_origin_contract':'Private fixture paths/byte claims/scalar budgets; unmodified selected-loader proof; fresh cancellation/control with None latches; exact Policy::swift; no incoming arbitrary str/Fault/failure/custom callback or intervening mutation. Policy::Frozen(&Limits) is a scalar/profile control dependency, not a fabricated str field.',
  'conservation':'24 primitive literals, 54 reference/field transfers, two policy returns; nested aggregates, failure/error latches, returns, cleanup, retirement and Drop preserve/move/drop references. Exact reviewed standard container/residual/scalar/callback contracts accompany full typed statements and source excerpts.',
  'opaque_native_backing':['Path/OsStr','io::Error private/native backing'],
  'L_str_candidate':5080,'L_str_selected':False,'root_selected':False,'whole_budget_selected':False,'source_or_complete_typed_graph_accepted':False,
  'compiler_or_product_executed':False,'native_or_UI_or_capture':False,'operational_grant':False,'OTA_or_GA':False,
  'pending':['fresh independent review','root selection','actual immutable P0 package/compiler/session/executable binding and full binary correspondence','native/runtime/device checks remain paused or separately pending','outer 27deef candidate requires a separate rebind']}
 raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
 if check:require((D/'correction-summary.json').read_bytes()==raw,'correction-report-rederive')
 else:
  require(not (D/'seal.json').exists(),'already-frozen');(D/'correction-summary.json').write_bytes(raw)
 print(json.dumps({'S1_S5_implemented':True,'all_current_typed_header_discrepancies':len(a['typed_header_discrepancies']),'current_failures_preserved':len(failures),'read_only':check,'independent_review_required':True,'L_str_selected':False,'operational_grant':False},sort_keys=True))
if __name__=='__main__':main('--check' in sys.argv)
