"""Meaningful current-MIR and source/caller negatives, bounded by group."""
import copy, unittest
from origins import *
class CurrentExactTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tables,cls.blocks,cls.production,cls.mir,cls.source=current_inputs()
  cls.graph=load(D/'selected-graph.json')
 def reject(self,fn,*args):
  with self.assertRaises((ValueError,AssertionError)):fn(*args)
 def test_missing_singleline_constant_refuses_full_base(self):
  changed=copy.copy(self.blocks);pools=[S.parse_mir(t)[0] for t in mir_texts()]
  constant=next(b for b in pools[3] if '\n' not in b and not provider(b) and not probe(b,3))
  pools[3].remove(constant);self.reject(full_base_correspondence,pools)
 def test_changed_singleline_constant_refuses_full_base(self):
  pools=[S.parse_mir(t)[0] for t in mir_texts()]
  i=next(i for i,b in enumerate(pools[3]) if '\n' not in b and 'const 5_usize;' in b and not provider(b) and not probe(b,3))
  pools[3][i]=pools[3][i].replace('const 5_usize;','const 6_usize;');self.reject(full_base_correspondence,pools)
 def test_changed_allocation_payload_refuses(self):
  pools=[S.parse_mir(t)[0] for t in mir_texts()]
  i=next(i for i,b in enumerate(pools[3]) if b.startswith('alloc') and '│ 00 ' in b)
  pools[3][i]=pools[3][i].replace('│ 00 ','│ 01 ',1);self.reject(full_base_correspondence,pools)
 def test_changed_compiler_constant_is_substantive(self):
  pools=[S.parse_mir(t)[0] for t in mir_texts()];i=next(i for i,b in enumerate(pools[3]) if b.startswith('const COMPILED: '))
  pools[3][i]=pools[3][i].replace('_1 = Option::<&str>::None;','_1 = Option::<&str>::Some(const "forged");',1)
  self.reject(compiled_constant,pools,self.tables[3])
 def test_source_owner_and_lifetime_mutations_refuse(self):
  for before,after in [(b"paths: [&'p0 Path; 5]",b"paths: [&'p0 mut Path; 5]"),(b'original_validation_budget: SwiftValidationBudget',b'original_validation_budget: SwiftRunBudget')]:
   tables=list(self.tables);tables[3]=dict(tables[3]);self.assertIn(before,tables[3][PROFILE]);tables[3][PROFILE]=tables[3][PROFILE].replace(before,after,1);self.reject(source_lineage,tables)
 def test_current_caller_mutation_never_grants_authority(self):
  expected=caller_contract(self.tables[3]);bind_caller(expected,expected)
  variants=[]
  for key in ('L_str_selected','actual_P0_root_caller_and_fixture_binding_selected','whole_host_funding','operational_grant','OTA','GA','authenticated_owner_created_by_provider','actual_acquisition_implemented','current_metadata_query_is_final_fixture_executable','current_compiled_five_identity_values_present'):
   x=copy.deepcopy(expected);x[key]=True;variants.append(x)
  for key in ('required_route','selected_specializations','shared_lifetime_owner_requirement','future_compiler_identity_change_requires_fresh_rebind'):
   x=copy.deepcopy(expected);del x[key];variants.append(x)
  x=copy.deepcopy(expected);x['root_incoming_authored_str_ports']=['arbitrary static str/Fault'];variants.append(x)
  x=copy.deepcopy(expected);x['selected_specializations']['Read']='CustomReader';variants.append(x)
  for value in variants:self.reject(bind_caller,value,expected)
 def test_literal_and_foreign_identity_never_normalize(self):
  literal='fn f() -> () {\n    bb0: {\n        _0 = const "'+SCRATCH[3]+" FrozenFixtureV1::<'_> // unchanged"+'";\n    }\n}'
  self.assertIn(SCRATCH[3],project(literal));self.assertIn("FrozenFixtureV1::<'_>",project(literal))
  self.assertNotEqual(project(literal),project(literal.replace('unchanged','forged')))
  foreign="fn foreign::f(_1: foreign::FrozenFixtureV1<'_>) -> foreign::Result<'_> {\n}"
  self.assertEqual(project(foreign),foreign)
  self.assertFalse(probe('fn foreign::owned_provider_remaining_layout_query_v1() -> () {\n}',3))
 def test_all_current_raw_typed_headers(self):
  rows=M.parse_functions('\n'.join(self.production)+'\n',self.source)[0];saved=load(D/'raw-current-typed-headers.json')
  self.assertEqual(len(rows),len(saved))
  for key,row in rows.items():self.assertEqual({n:row[n] for n in saved[key]},saved[key])
  historical=load(OLD/'typed-header-inventory.json')['historical_discrepancy_roster']['whole_compiler_pool_header_misparses']
  self.assertEqual(len(historical),9)
 def test_changed_primitive_literal_origin_refuses_transport(self):
  self.assertIn('const "swift_cache_layout_overflow"',self.mir)
  altered=self.mir.replace('const "swift_cache_layout_overflow"','const "'+'x'*5081+'"',1)
  graph=M.analyze(altered,self.source)
  self.assertEqual(graph['L_str_source_candidate'],5081)
  changed_blocks=S.parse_mir(altered)[0];self.reject(selected_transport,graph,changed_blocks,self.tables)
 def test_missing_selected_callback_edge_refuses_transport(self):
  call=next(c for r in self.graph['nodes'].values() for c in r['calls'] if c['named_callbacks'] and 'accounted::AccountedWasi::usage' in c['named_callbacks'])
  # Change an actual authored named callback to a standard-looking foreign item;
  # exact function-item resolution must refuse rather than erase that edge.
  altered=self.mir.replace(call['statement'],call['statement'].replace('accounted::AccountedWasi::usage','foreign::AccountedWasi::usage'),1)
  self.reject(M.analyze,altered,self.source)
def legacy_suite(group):
 # Preserve the accepted adverse tests themselves; supply actual current MIR,
 # current source and explicit definition-role labels. No old runner executes.
 legacy=module(OLD/'test_exact_binding.py','accepted_exact_tests');legacy.p=M
 tables,blocks,production,mir,source=current_inputs();graph=load(D/'selected-graph.json');mapping=load(D/'definition-role-map.json')['selected_rows'];back={r['current']:r['old'] for r in mapping}
 relabeled=dict(graph,nodes={back[k]:v for k,v in graph['nodes'].items()},edges=[dict(e,caller=back[e['caller']],callee=back[e['callee']]) for e in graph['edges']])
 class CurrentLegacy(legacy.ExactBindingTests):
  @classmethod
  def setUpClass(cls):cls.mir=mir;cls.source=source;cls.graph=relabeled
 groups={
 'identity':['foreign_namespace','std_namespace','unknown_trait_with_authored_receiver','policy_namespace'],
 'receiver':['foreign_shared_control_receiver','foreign_meter_receiver'],
 'types':['missing_authored_argument','changed_authored_argument','changed_nested_authored_result'],
 'callbacks':['changed_named_callback_result','unknown_named_callback','changed_closure_header'],
 }
 if group=='finite':names=['test_balanced_nested_fn_tuple_array_and_generic_types','test_catalog_is_complete_identity_and_type_contract_not_body_hash','test_all_423_targets_refuse_namespace_and_receiver_shadow','test_all_434_authored_signatures_reject_changed_arguments_and_nested_result']
 else:names=['test_full_mir_'+name+'_refuses' for name in groups[group]]
 return unittest.TestSuite(CurrentLegacy(n) for n in names)
if __name__=='__main__':
 group=sys.argv[1] if len(sys.argv)>1 else 'local'
 groups={'census':['test_missing_singleline_constant_refuses_full_base','test_changed_singleline_constant_refuses_full_base','test_changed_allocation_payload_refuses','test_changed_compiler_constant_is_substantive'],
 'local':['test_source_owner_and_lifetime_mutations_refuse','test_current_caller_mutation_never_grants_authority','test_literal_and_foreign_identity_never_normalize','test_all_current_raw_typed_headers'],
 'literal':['test_changed_primitive_literal_origin_refuses_transport'],
 'edge':['test_missing_selected_callback_edge_refuses_transport']}
 suite=unittest.TestSuite(CurrentExactTests(n) for n in groups[group]) if group in groups else legacy_suite(group)
 result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(not result.wasSuccessful())
