import copy,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
import checks,derive,evaluator,layouts,pipeline
H=Path(__file__).resolve().parent
class CalleeCost(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.ledger,cls.obs,cls.contract=pipeline.compute();cls.route=evaluator.canonical_route();cls.negative_cases=0
 def inputs(self):
  rows=self.contract['exports'].values()
  return ({k:16 for r in rows for k in r['native']},{k:256 for r in rows for k in r['unsized']},{k:100 for r in rows for k in r['payload']},{r['required_private_primitive_cut']:100 for r in rows})
 def test_01_deterministic_replay(self):
  for file,value in [('callee-ledger.json',self.ledger),('cost-interface.json',self.contract),('native-layout-observations.json',self.obs)]:self.assertEqual(json.loads((H/file).read_text()),value)
 def test_02_authored_graph_and_source_phase_invariants(self):
  self.assertTrue(checks.validate(self.ledger,self.contract));self.assertEqual(85,len(self.ledger['nodes']));self.assertEqual(21,len(self.contract['exports']))
 def test_03_no_generic_or_ordinary_policy_escape(self):
  for key,value in [('selected_policy','OriginalAdoptionV1'),('selected_policy','P'),('fixed_execution_work',0),('fixed_execution_work',True),('source_tree_sha256','0'*64)]:
   r=copy.deepcopy(self.route);r[key]=value
   with self.assertRaises(ValueError):evaluator.check_route(r)
 def test_04_closed_route_no_intervening_cache_activity(self):
  for key,value in [('consuming_construct_count',2),('outer_observation_count',2),('consuming_finish_count',0),('authentic_ingress_count',0),('intervening_cache_mutations',1),('attached_wasi',True)]:
   r=copy.deepcopy(self.route);r[key]=value
   with self.assertRaises(ValueError):evaluator.check_route(r)
 def test_05_finite_loop_caps_not_caller_discounts(self):
  for key in ['cache_pin_bound','cache_slot_bound','wasi_buffer_bound']:
   for x in [0,1,63,65,True,-1,1.0,None]:
    if type(x) is int and x==self.route[key]:continue
    r=dict(self.route);r[key]=x
    with self.assertRaises(ValueError):evaluator.check_route(r)
 def test_06_every_required_positive_input_is_mandatory(self):
  bad=[None,0,-1,True,False,1.5,'8',evaluator.MAX+1]
  for export,row in self.contract['exports'].items():
   maps=list(self.inputs())
   terms=[(0,k) for k in row['native']]+[(1,k) for k in row['unsized']]+[(2,k) for k in row['payload']]+[(3,row['required_private_primitive_cut'])]
   for index,key in terms:
    for value in bad:
     altered=copy.deepcopy(maps)
     if value is None:altered[index].pop(key,None)
     else:altered[index][key]=value
     with self.assertRaises(ValueError):evaluator.evaluate_synthetic(self.contract,export,self.route,*altered)
     type(self).negative_cases+=1
 def test_07_no_implicit_resource_destructor_credit(self):
  payload={k for r in self.contract['exports'].values() for k in r['payload']}
  self.assertIn('payload::Partial',payload);self.assertIn('payload::AdoptionBodyV1',payload);self.assertIn('payload::SnapshotAttemptV1',payload)
  self.assertGreater(self.contract['exports']['callee::construct_snapshot_in_scope_v1']['payload']['payload::Partial'],0)
 def test_08_source_specific_missing_callee_and_callback_controls(self):
  edits=[('drop_proof','accepted::refund_with_wasi'),('cache_cleanup','accepted::wasi_usage'),('core_callback_before','accepted::check_budget')]
  for node,callee in edits:
   mutant=copy.deepcopy(self.ledger);mutant['nodes'][node]['calls'].pop(callee)
   with self.assertRaises(ValueError):checks.validate(mutant,self.contract)
 def test_09_loop_underpricing_hostile_controls(self):
  for node in ['cache_cleanup','wasi_pair']:
   mutant=copy.deepcopy(self.ledger);mutant['nodes'][node]['loops'][0]['max_iterations']-=1
   with self.assertRaises(ValueError):checks.validate(mutant,self.contract)
   mutant=copy.deepcopy(self.ledger);b=mutant['nodes'][node]['loops'][0]['blocks'][0];next(o for o in mutant['nodes'][node]['operations'] if o['block']==b)['weight']=1
   with self.assertRaises(ValueError):checks.validate(mutant,self.contract)
 def test_10_store_move_or_omission_refused(self):
  for destination in ['core_callback_before','remove']:
   mutant=copy.deepcopy(self.ledger);store=mutant['core_phase_binding']['counter_store'];after=mutant['nodes']['core_fixed_store_and_after']['operations'];after[:]=[o for o in after if o['code']!=store['code']]
   if destination!='remove':mutant['nodes'][destination]['operations'].append(store)
   with self.assertRaises(ValueError):checks.validate(mutant,self.contract)
 def test_11_concrete_selected_policy_binding_not_old_trait_capture(self):
  m=copy.deepcopy(self.ledger);m['source_bindings']['policy_retire']['source']='fn retire_tickets(...) -> Self::Retirement; } impl ClosedAdoptionV1 for OriginalAdoptionV1 {}'
  with self.assertRaises(ValueError):checks.validate(m,self.contract)
 def test_12_constructor_aggregate_abuse_or_destructor_omission_refused(self):
  for edit in ['extra-caller','aggregate','drop-omission','writer-live']:
   m=copy.deepcopy(self.ledger)
   if edit=='extra-caller':m['nodes']['drop_proof']['calls']['accepted_constructor_region']=1
   elif edit=='aggregate':m['nodes']['accepted_constructor_region']['own']=451814442
   elif edit=='drop-omission':m['nodes']['accepted_constructor_region']['payload'].pop('payload::Partial')
   else:m['constructor_applicability']['writer_encoder_initializer_entered']=True
   with self.assertRaises(ValueError):checks.validate(m,self.contract)
 def test_13_checked_arithmetic_grid(self):
  grid=[0,1,2,(1<<32)-1,1<<32,evaluator.MAX//2,evaluator.MAX-1,evaluator.MAX,-1,evaluator.MAX+1,True,1.0,None]
  for a in grid:
   for b in grid:
    for fn,operation in [(evaluator.add,lambda a,b:a+b),(evaluator.mul,lambda a,b:a*b)]:
     valid=type(a) is int and type(b) is int and 0<=a<=evaluator.MAX and 0<=b<=evaluator.MAX and operation(a,b)<=evaluator.MAX
     if valid:self.assertEqual(operation(a,b),fn(a,b))
     else:
      with self.assertRaises(ValueError):fn(a,b)
 def test_14_graph_missing_or_recursive_authored_body_refuses(self):
  for child in ['missing','drop_proof']:
   m=copy.deepcopy(self.ledger);m['nodes']['drop_proof']['calls'][child]=1
   with self.assertRaises(ValueError):evaluator.flatten(m,'drop_proof')
 def test_15_qualified_cursor_fault_layouts_no_short_name_fallback(self):
  self.assertEqual(32,self.obs['resolved']['Cursor']['size']);self.assertEqual(64,self.obs['resolved']['Fault']['size'])
  self.assertEqual('experimental_swift_reactor::control::Cursor',self.obs['resolved']['Cursor']['qualified']);self.assertEqual(87,len(self.obs['resolved']));self.assertEqual(13,len(self.obs['missing']))
  self.assertFalse(self.obs['short_name_fallback'])
 def test_16_conflicting_same_qualified_layout_refuses(self):
  records,binding=layouts.load_records();k='experimental_swift_reactor::control::Cursor';records[k].append(dict(records[k][0],size=16))
  with patch.object(layouts,'load_records',return_value=(records,binding)):
   with self.assertRaises(ValueError):layouts.reconcile(self.ledger,{'exports':{'x':{'native':{'Cursor':2}}}})
 def receipt(self):
  sizes=self.inputs()[0]
  return dict(source_tree_sha256=evaluator.TREE,native_query_roster_sha256=self.contract['native_query_roster_sha256'],target='aarch64-apple-darwin',scope='compiler-observed-source146-size-and-alignment',product_executed=False,compiler_receipt_sha256='0'*64,observations=[dict(key=k,size=v,alignment=8,kind='actual-size-and-alignment',source_tree_sha256=evaluator.TREE,compiler_diagnostic_binding_sha256='0'*64) for k,v in sorted(sizes.items())])
 def test_17_arbitrary_positive_sizes_do_not_qualify_native_binding(self):
  with self.assertRaises(ValueError):evaluator.evaluate_bound(self.contract,next(iter(self.contract['exports'])),self.route,self.inputs()[0],*self.inputs()[1:])
  r=json.dumps(self.receipt(),sort_keys=True).encode()
  with self.assertRaises(ValueError):evaluator.bind_native(r,'0'*64,self.contract)
 def test_18_receipt_source_roster_target_scope_and_completeness_controls(self):
  cases=[('source_tree_sha256','0'*64),('native_query_roster_sha256','0'*64),('target','x86_64-unknown-linux-gnu'),('scope','synthetic'),('product_executed',True),('observations',[])]
  for key,value in cases:
   receipt=self.receipt();receipt[key]=value;b=json.dumps(receipt,sort_keys=True).encode()
   with self.assertRaises(ValueError):evaluator.bind_native(b,hashlib.sha256(b).hexdigest(),self.contract)
 def test_19_synthetic_bound_receipt_stays_conditional(self):
  r=json.dumps(self.receipt(),sort_keys=True).encode();bound=evaluator.bind_native(r,hashlib.sha256(r).hexdigest(),self.contract)
  _,u,p,s=self.inputs()
  for export in self.contract['exports']:
   answer=evaluator.evaluate_bound(self.contract,export,self.route,bound,u,p,s)
   self.assertGreater(answer['conditional_logical_price'],0);self.assertFalse(answer['complete_host_quote']);self.assertFalse(answer['operational_grant'])
 def test_20_frozen_downstream_rosters(self):
  for folder,expected in [('constructor-destructor-roster','183bf0311de870bf6986b44e9ccfad9f035d9eb41e1f5f0470433f09bd09fc24'),('native-query-roster','8893f5d47ea65ca4411712d381eec383142e8f51bef6fad2db86a7cb652c18ab')]:
   digest=hashlib.sha256((H/folder/'seal.json').read_bytes()).hexdigest();self.assertEqual(expected,digest)
   for row in json.loads((H/folder/'seal.json').read_text())['members']:
    b=(H/folder/row['path']).read_bytes();self.assertEqual((row['bytes'],row['sha256']),(len(b),hashlib.sha256(b).hexdigest()))
if __name__=='__main__':unittest.main(verbosity=2)
