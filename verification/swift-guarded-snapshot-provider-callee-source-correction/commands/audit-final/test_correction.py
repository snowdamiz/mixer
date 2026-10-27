"""Fresh targeted R1-R3 host controls. Synthetic bounds are never selected prices."""
from dataclasses import replace
from pathlib import Path
import copy,json,re,sys,unittest
sys.dont_write_bytecode=True
import derive as D
import ledger as L
import model as M
from custody import ORIGINAL,REVIEW,roster
HERE=Path(__file__).resolve().parent
LABEL='b'*64
ADVERSE=0
ARITHMETIC=0

def b(value,unit='bytes'):
 return M.provider().Bound(value,'synthetic correction test only; not source pricing, owner or funding evidence',M.TREE,LABEL,unit)
def fixture():
 P=M.provider();raw=M.sealed_input(D.V/'swift-real-profile-loader-binding/source-preimages/genuine.wasm')
 ids=tuple(P.Identity(name,raw if i==0 else ('correction '+name).encode(),P.digest(raw if i==0 else ('correction '+name).encode()),b(len(raw) if i==0 else len('correction '+name))) for i,name in enumerate(P.IDENTITIES))
 paths=tuple(P.PathInput(b'/path/'+bytes([97+i]),b'/path/'+bytes([97+i]),b(7),b(7),b(8),LABEL) for i in range(5))
 budget={name:1 for name in P.BUDGET_FIELDS};budget.update(execution_work=1_000_000_000,combined_bytes=268435456)
 return P.BindingInput(M.TREE,ids,paths,tuple(bytes([i])*32 for i in range(8)),budget,LABEL,b(128),b(64),b(512),b(8572),b(4097),b(73),b(32),b(396924,'count'),b(29394))
def residuals(v,unit):
 p=M.proposal();_,contexts=M.contexts(v)
 return tuple(M.ResidualBound(53+i,unit,c['frontier'],c['occurrence'],M.TREE,M.TARGET,M.COMPILER,p['positive_residual_contracts'][c['frontier']]['native_target'],tuple(p['positive_residual_contracts'][c['frontier']]['argument_types']),p['positive_residual_contracts'][c['frontier']]['return_type'],c['body_lengths'],LABEL,'synthetic full exact source contract obligation; no acceptance',p['source_closure_frontiers_sha256'],c.get('invocation_context',())) for i,c in enumerate(contexts))
def evaluate(v,work=None,storage=None,outcome='normal',old=None,acq=None,caller=None):
 return M.evaluate(v,{k:b(31,'work') for k in M.provider().INHERITED_WORK} if old is None else old,residuals(v,'work') if work is None else work,residuals(v,'bytes') if storage is None else storage,b(37,'work') if acq is None else acq,b(41,'work') if caller is None else caller,outcome=outcome)
def at(p,B):return p['fixed']+B*p['B']+B*B*p['B2']
def independently_price_row(code,roles,B):
 # Direct occurrence arithmetic; does not call derive.operation/compose/poly.
 def occurrence(role):
  return 2*(role['bytes']+role['leaves']+at(role['pointee_bytes'],B)+at(role['pointee_leaves'],B))
 value=2+sum(code.count(ch) for ch in '()[].*&')+len(re.findall(r'\bas\b',code))
 for identifier in re.findall(r'\b_\d+\b',code):value+=occurrence(roles[identifier])
 for token in re.finditer(r'(?<!\*)\bconst\s+(\d+_(?:usize|isize|u8|i32)|true|false|\(\))',code):
  literal=token[1]
  width=0 if literal=='()' else 1 if literal in ('true','false') or literal.endswith('_u8') else 4 if literal.endswith('_i32') else 8
  value+=2+2*width
 if code=='return;':value+=occurrence(roles['_0'])
 return value
class Correction(unittest.TestCase):
 def reject(self,f,kind=ValueError):
  global ADVERSE
  with self.assertRaises(kind):f()
  ADVERSE+=1
 def test_R1_exact_macro_binding_and_unpriced_full_aggregate(self):
  source=(HERE/'official-source/library/core/src/num/mod.rs').read_text().splitlines()
  self.assertEqual(source[1449],'#[cfg(target_pointer_width = "64")]')
  self.assertEqual(source[1452].strip(),'Self = usize,');self.assertEqual(source[1453].strip(),'ActualT = u64,')
  original=(ORIGINAL/'official-source/library/core/src/num/uint_macros.rs').read_text().splitlines()
  self.assertIn('self as $ActualT, rhs as $ActualT',original[2989]);self.assertIn('(a as Self, b)',original[2990])
  c=L.closure_frontiers()['range_next'];self.assertEqual(c['exact_macro_selection']['ActualT'],'u64');self.assertEqual(c['R1']['casts'],3)
  self.assertEqual([r['type'] for r in c['R1']['roles']],['usize','usize','u64','u64','(u64, bool)','u64','bool','usize','(usize, bool)'])
  self.assertIsNone(c['R1']['unobserved_full_aggregate']['size']);self.assertIsNone(c['R1']['unobserved_full_aggregate']['align'])
  types=D.type_table();self.assertNotIn('(u64, bool)',types)
  self.assertEqual((types['(usize, bool)']['bytes'],types['(usize, bool)']['align']),(16,8));self.assertEqual((types['ProductionClosure']['bytes'],types['ProductionClosure']['align']),(16,8))
  for key in ('casts','operations','roles','unobserved_full_aggregate','observed_outer_return'):
   p=copy.deepcopy(M.proposal());p['source_closure_frontiers']['range_next']['R1'].pop(key);self.reject(lambda p=p:M.validate_proposal(p),M.Refused)
  for wrong in ('usize','u32','i64'):
   p=copy.deepcopy(M.proposal());p['source_closure_frontiers']['range_next']['exact_macro_selection']['ActualT']=wrong;self.reject(lambda p=p:M.validate_proposal(p),M.Refused)
 def test_R2_runtime_macro_and_consumed_boolean_shell(self):
  source=(ORIGINAL/'official-source/library/core/src/intrinsics/mod.rs').read_text()
  for text in ('fn runtime$(<$($binders)*>)?($($arg: $ty),*)','const fn compiletime$(<$($binders)*>)?($($arg: $ty),*)','const_eval_select(($($val,)*), compiletime, runtime)'):self.assertIn(text,source)
  n=next(x for x in L.nodes() if x['id']=='language_ub_check');rows=[r['code'] for r in n['rows']]
  self.assertIn('_1 = ConstEvalSelectResidual();',rows);self.assertIn('switchInt(copy _1);',rows);self.assertIn('_0 = copy _2;',rows);self.assertIn('_0 = const false;',rows)
  self.assertFalse(any('ConstEvalSelectRuntime' in x or 'BitAnd' in x for x in rows))
  self.assertEqual([r['type'] for r in n['roles']],['bool','bool','bool'])
  c=L.closure_frontiers()['range_next']['R2'];self.assertEqual(len(c['roles']),8)
  self.assertIn('fn runtime() -> bool',c['expanded']);self.assertIn('const_eval_select::<(), CompiletimeItem, RuntimeItem, bool>',c['expanded'])
  self.assertIsNone(c['callable_layouts']['runtime_item']);self.assertIsNone(c['callable_layouts']['compiletime_item'])
  for field in ('roles','operations','expanded','selection','callable_layouts','private_intrinsic_implementation'):
   p=copy.deepcopy(M.proposal());p['source_closure_frontiers']['range_next']['R2'].pop(field);self.reject(lambda p=p:M.validate_proposal(p),M.Refused)
  for index in range(len(n['rows'])):
   ns=L.nodes();i=next(i for i,x in enumerate(ns) if x['id']=='language_ub_check');ns[i]['rows'].pop(index);self.reject(lambda ns=ns:D.validate_ledger(ns,D.type_table()))
 def test_R3_full_receiver_matches_obligations_in_each_existing_composite(self):
  self.assertIn('pub const fn is_some(&self) -> bool {\n        matches!(*self, Some(_))',(ORIGINAL/'official-source/library/core/src/option.rs').read_text())
  source=(HERE/'official-source/library/core/src/macros/mod.rs').read_text()
  self.assertIn('match $expression {\n            $pattern $(if $guard)? => true,\n            _ => false',source)
  c=L.closure_frontiers()['contains'];self.assertEqual(c['count'],5);self.assertEqual(c['expanded'],'match *self { Some(_) => true, _ => false }')
  self.assertIn('&Option<usize>',c['receiver']);self.assertEqual(len(c['all_prior_obligations_preserved']),5)
  spec=L.FRONTIERS['CONTAINS_RESIDUAL_FRONTIER'];self.assertIn('receiver auto-borrow',spec['remaining']);self.assertIn('finite source place ending',spec['remaining'])
  for key in ('receiver','signature','expanded','roles','operations','all_prior_obligations_preserved','actual_lengths'):
   p=copy.deepcopy(M.proposal());p['source_closure_frontiers']['contains'].pop(key);self.reject(lambda p=p:M.validate_proposal(p),M.Refused)
  for i in range(9):
   p=copy.deepcopy(M.proposal());p['source_closure_frontiers']['contains']['roles'].pop(i);self.reject(lambda p=p:M.validate_proposal(p),M.Refused)
 def test_all30_exact_contexts_individually_positive_in_both_units(self):
  v=fixture();_,ctx=M.contexts(v);self.assertEqual(len(ctx),30)
  schedule=ctx[11:];self.assertEqual([x['invocation_context'] for x in schedule],[('identity',12,i) for i in range(13)]+[('path',5,i) for i in range(6)])
  for unit in ('work','bytes'):
   good=residuals(v,unit);self.assertGreater(M.residuals(v,good,unit),0)
   for i in range(30):
    self.reject(lambda i=i:M.residuals(v,good[:i]+good[i+1:],unit),M.Refused)
    for replacement in (0,-1,True,1.5,M.U64+1):
     bad=good[:i]+(replace(good[i],value=replacement),)+good[i+1:];self.reject(lambda bad=bad:M.residuals(v,bad,unit),M.Refused)
   for wrong in (tuple(reversed(good)),good+good[:1],list(good)):
    self.reject(lambda wrong=wrong:M.residuals(v,wrong,unit),M.Refused)
 def test_targeted_exact_types_counts_unit_source_digest_and_context_fail_closed(self):
  v=fixture()
  for unit in ('work','bytes'):
   good=residuals(v,unit)
   for i in range(30):
    item=good[i]
    changes=[{'unit':'bytes' if unit=='work' else 'work'},{'frontier':'unknown'},{'occurrence':True},{'occurrence':item.occurrence+1},{'compiler_sha256':'0'*64},{'source_tree':'0'*64},{'target':'x86_64-apple-darwin'},{'native_target':'memcmp' if i>=11 else 'unknown'},{'argument_types':item.argument_types+('u64',)},{'return_type':'bool' if i>=11 else 'usize'},{'source_contract_sha256':'0'*64},{'invocation_context':('identity',12,True)},{'body_lengths':(65536,)},{'evidence_sha256':'not evidence'},{'obligation':''}]
    for change in changes:
     wrong=good[:i]+(replace(item,**change),)+good[i+1:];self.reject(lambda wrong=wrong:M.residuals(v,wrong,unit),M.Refused)
 def test_independent_changed_rows_all_helper_composition_and_storage(self):
  global ARITHMETIC
  nodes={n['id']:n for n in D.load(HERE/'source-ledger.json')['nodes']};p=M.proposal();abi={n['node']:n for n in D.load(HERE/'native-ABI-boundaries.json')['rows']}
  def compose(name,B):
   n=nodes[name];roles={r['id']:r for r in n['roles']};work=2
   for r in roles.values():
    if r['kind']=='parameter':work+=2*(r['bytes']+r['leaves']+at(r['pointee_bytes'],B)+at(r['pointee_leaves'],B))
   work+=sum(2+2*r['leaves']+2*r['bytes'] for r in roles.values())
   for row in n['rows']:
    part=independently_price_row(row['code'],roles,B)
    self.assertEqual(part,at(row['combined'],B));work+=part*(B+1 if row['body_iterations'] else 1)
   work+=abi.get(name,{}).get('logical_native_boundary_supplement',0)
   slots=sum(r['bytes'] for r in roles.values());native=abi.get(name,{}).get('additional_reserved_native_interface_fields',0);callbacks=0
   for edge in n['calls']:
    child=edge['node'];count=edge['count']
    if child=='AUTHORED_CALLBACK':callbacks+=count;continue
    if child in p['positive_residual_contracts']:continue
    cw,cs,cn,cb=compose(child,B);work+=cw*(B+1 if count=='body+1' else count);slots+=cs*(1 if count=='body+1' else count);native+=cn*(1 if count=='body+1' else count);callbacks+=cb*(B+1 if count=='body+1' else count)
   return work,slots,native,callbacks
  for B in (0,1,16,1947,65537):
   total=source=native=callback=0
   for interface in p['interfaces']:
    w,s,n,c=compose(interface['name'],B);cap=interface['call_cap'];total+=w*cap;source+=s*cap;native+=n*cap;callback+=c*cap
    self.assertEqual(w,at(interface['per_call_source_and_native_shell'],B));self.assertEqual(s*cap,interface['reserved_distinct_source_places']);self.assertEqual(n*cap,interface['reserved_distinct_native_ABI_fields']);ARITHMETIC+=3
   self.assertEqual(total,at(p['callee_source_shell_work'],B));self.assertEqual(source,p['additional_source_ledger_slots']);self.assertEqual(native,p['additional_native_ABI_field_reservations']);self.assertEqual(callback,5);ARITHMETIC+=4
  self.assertEqual(p['callee_source_shell_work'],{'fixed':187034,'B':6867,'B2':160});self.assertEqual((source,native),(19029,9882))
  self.assertEqual(p['additional_total_slots'],28911);self.assertEqual(p['proposed_conditional_P0_fixed_excluding_positive_residual_storage'],330644)
  rng=next(x for x in p['interfaces'] if x['name']=='range_next');self.assertEqual(rng['call_cap'],19);self.assertEqual(rng['per_call_source_and_native_shell']['fixed'],2246);self.assertEqual(rng['reserved_distinct_source_places'],3819)
  for field in ('additional_total_slots','additional_source_ledger_slots','additional_native_ABI_field_reservations','proposed_conditional_P0_fixed_excluding_positive_residual_storage'):
   wrong=copy.deepcopy(p);wrong[field]-=1;self.reject(lambda wrong=wrong:M.validate_proposal(wrong),M.Refused)
 def test_all15_phases_inherited_terms_backing_and_no_refund(self):
  v=fixture();p=M.proposal();base=M.provider().storage(v);work=residuals(v,'work');storage=residuals(v,'bytes');normal=evaluate(v)
  phases=D.load(HERE/'phase-reservations.json')['phases'];self.assertEqual(len(phases),15)
  for row in phases.values():self.assertEqual((row['provider_9696_retained'],row['new_source_ledger_places'],row['new_native_ABI_fields'],row['new_total']),(9696,19029,9882,28911))
  self.assertEqual(normal['P0_preexisting']-base['P0_preexisting'],28911+sum(x.value for x in storage))
  self.assertEqual(normal['inherited_six_child_storage_parts'],base['inherited_six_child_storage_parts']);self.assertEqual(normal['inherited_child_prepaid'],base['inherited_child_prepaid'])
  self.assertEqual(p['provider_source_work_unchanged'],{'fixed':276580,'input_operand_bytes':1324});self.assertEqual(p['provider_slots_unchanged'],9696);self.assertEqual(p['authored_callback_body_cap_inherited'],5)
  self.assertEqual(p['all10_inherited_terms']['L_str'],67424)
  for outcome in ('refusal','unwind'):
   result=evaluate(v,outcome=outcome);self.assertEqual(result['P0_preexisting'],normal['P0_preexisting']);self.assertEqual(result['whole_conditional_work'],normal['whole_conditional_work']);self.assertFalse(result['None_refusal_unwind_refund'])
  for frontier_unit,bounds in (('work',work),('bytes',storage)):
   for i in (11,23,24,29):
    bad=bounds[:i]+(replace(bounds[i],value=0),)+bounds[i+1:]
    self.reject(lambda bad=bad,frontier_unit=frontier_unit:evaluate(v,work=bad if frontier_unit=='work' else work,storage=bad if frontier_unit=='bytes' else storage),M.Refused)
  for field in ('future_root_inline','future_root_owned_backing','immutable_diagnostic_backing','loader_native_temporaries','executable_open_temporary','file_resource_backing_each','error_backing_each','all_payload_destructor_temporaries'):
   self.reject(lambda field=field:evaluate(replace(v,**{field:b(0)})),M.Refused)
  for i in range(12):
   ids=list(v.identities);ids[i]=replace(ids[i],backing=b(0));self.reject(lambda ids=ids:evaluate(replace(v,identities=tuple(ids))),M.Refused)
  for i in range(5):
   for field in ('native_backing','byte_preimage_backing','open_temporary'):
    paths=list(v.paths);paths[i]=replace(paths[i],**{field:b(0)});self.reject(lambda paths=paths:evaluate(replace(v,paths=tuple(paths))),M.Refused)
  old={k:b(31,'work') for k in M.provider().INHERITED_WORK}
  for key in old:
   wrong=dict(old);wrong.pop(key);self.reject(lambda wrong=wrong:evaluate(v,old=wrong),M.Refused)
  self.reject(lambda:evaluate(v,acq=b(0,'work')),M.Refused);self.reject(lambda:evaluate(v,caller=b(0,'work')),M.Refused)
  for key in ('frontier_prices_selected','actual_acquisition_authenticated_owner_or_root_funding','accepted_bound','native_FieldLog_OTA_GA'):self.assertFalse(normal[key])
 def test_frozen_custody_and_native_boundary_field_independence(self):
  locked=roster();self.assertEqual(locked,D.load(HERE/'input-lock.json'));self.assertEqual((locked['inherited_priced_input_count'],locked['inherited_frozen_packet_count'],len(locked['frozen_packets'])),(1245,15,17))
  self.assertEqual(len(locked['excluded_inherited_cache_metadata']),1)
  rows=D.load(HERE/'native-ABI-boundaries.json')['rows'];self.assertEqual(len(rows),23)
  for row in rows:
   fields=sum(x['native_field_bytes']+x['sret_logical_result_payload_bytes'] for x in row['formals'])+row['result_native_field_bytes']
   self.assertEqual(row['additional_reserved_native_interface_fields'],fields);self.assertEqual(row['logical_native_boundary_supplement'],2*fields)
  target=next(x for x in rows if x['node']=='candidate_result_from_residual');self.assertIn('sret([1352 x i8])',target['header']);self.assertIn('ptr align 8 %0',target['header'])

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Correction))
 report={'schema':1,'fresh_targeted_R1_R2_R3_test_methods':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'adverse_cases_rejected':ADVERSE,'independent_interface_and_storage_equalities':ARITHMETIC,'producer_tests_replayed':False,'original_or_independent_historical_counts_not_new_tests':True,'compiler_product_native_runtime_UI_capture_or_global_inventory':False}
 if not(HERE/'seal.json').exists():(HERE/'latest-checks.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
 print(json.dumps(report));raise SystemExit(not result.wasSuccessful())
