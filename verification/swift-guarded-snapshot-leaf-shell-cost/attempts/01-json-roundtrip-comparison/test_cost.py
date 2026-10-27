#!/usr/bin/env python3
"""Pure proposal controls only; no actual fixture/destructor/runtime call."""
import collections, copy, json, sys, unittest
from pathlib import Path
sys.dont_write_bytecode=True
import derive as D
import model as M

class LeafShellControls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.bundle=D.derive()
  cls.interface=cls.bundle['cost-interface.json']
  cls.ledger=cls.bundle['operation-ledger.json']
  cls.functions={f['function']:f for f in cls.ledger['functions']}
  cls.sizes={k:1 for k in cls.interface['missing_native_occurrence_coefficients']}
  cls.cuts={k:1 for k in cls.interface['required_nonzero_callee_drop_and_backing_cuts']}
  cls.unsized={k:1 for k in cls.interface['unsized_source_and_native_byte_coefficients']}
 def test_exact_source146_and_frozen_bindings(self):
  self.assertEqual(D.SOURCE146,self.interface['source_tree_sha256'])
  self.assertEqual(146,self.interface['source_members'])
  self.assertEqual(4,len(self.bundle['input-custody.json']['seals']))
  self.assertFalse(self.bundle['input-custody.json']['new_compiler'])
 def test_deterministic_retained_results(self):
  for name,value in self.bundle.items():
   p=D.HERE/name
   self.assertTrue(p.exists(),name)
   self.assertEqual(value,p.read_text() if isinstance(value,str) else json.loads(p.read_bytes()),name)
 def test_eight_concrete_boundaries(self):
  self.assertEqual({'leaf','into_scope','selected_into_body','snapshot_into_body','adopt_snapshot','construct','outer','finish'},set(self.functions))
  self.assertEqual(205,sum(len(f['roles']) for f in self.functions.values()))
  self.assertEqual(598,sum(len(b['lines']) for f in self.functions.values() for b in f['blocks'].values()))
  self.assertEqual(13827,sum(f['terminal_path_count'] for f in self.functions.values()))
 def test_each_function_is_bounded_above_all_cfg_paths(self):
  for f in self.functions.values():
   self.assertGreaterEqual(f['all_blocks_once_source_action_units'],f['maximum_single_CFG_path_source_action_units'])
   for path in f['terminal_paths']:
    self.assertEqual(len(path),len(set(path)))
 def test_internal_consuming_graph_has_each_body_once(self):
  inbound=collections.Counter(b for a,b in self.ledger['internal_edges'])
  self.assertEqual({k:1 for k in self.functions if k!='leaf'},dict(inbound))
 def test_all_scalar_and_native_dimensions_reconcile(self):
  scalar=sum(f['all_blocks_once_source_action_units'] for f in self.functions.values())
  self.assertEqual(639237,scalar)
  self.assertEqual(scalar,self.interface['fixed_source_action_units'])
  self.assertEqual(118660,self.interface['known_native_occurrence_bytes'])
  self.assertEqual(53,len(self.interface['missing_native_occurrence_coefficients']))
  self.assertEqual(33,len(self.interface['required_nonzero_callee_drop_and_backing_cuts']))
 def test_typed_claims_pointer_covers_256_scalar_pointees(self):
  role=self.functions['leaf']['roles']['_5']
  self.assertEqual(1,role['scalar_leaves'])
  self.assertEqual(256,role['pointee_scalar_leaves'])
  self.assertEqual({'UnverifiedProfileDigestBytesV1':1},role['pointee_types'])
 def test_typed_scope_borrow_aggregate_closes_all_pointer_fields(self):
  roles=[r for r in self.functions['construct']['roles'].values() if 'SnapshotScopeBorrowV1' in r['compiler_type']]
  self.assertTrue(roles)
  for r in roles:
   self.assertGreater(r['pointee_scalar_leaves'],r['scalar_leaves'])
   self.assertIn('RuntimeControl',r['pointee_types'])
   self.assertIn('Option<SwiftFunctionCache>',r['pointee_types'])
 def test_nested_reference_native_types_remain_required(self):
  sizes=self.bundle['native-occurrence-interface.json']['all_type_occurrence_coefficients']
  self.assertIn('RuntimeControl',sizes)
  self.assertIn('SnapshotRunV1',sizes)
  self.assertIn('SnapshotOuterV1',sizes)
  self.assertIn('UnverifiedProfileDigestBytesV1',sizes)
  self.assertEqual({'str':2188},self.interface['unsized_source_and_native_byte_coefficients'])
 def test_cleanup_paths_and_actual_payload_cuts_are_present(self):
  cuts=self.interface['required_nonzero_callee_drop_and_backing_cuts']
  for t in ['SnapshotScopeV1','SnapshotRunV1','RuntimeControl','AdoptedProof','Option<SwiftFunctionCache>','Option<AccountedWasi>']:
   self.assertIn('drop_payload::'+t,cuts)
  for f in ('leaf','adopt_snapshot','construct','finish','into_scope'):
   self.assertTrue(any(b['cleanup'] for b in self.functions[f]['blocks'].values()))
 def test_exact_pre_store_cut_cannot_be_counter_credit(self):
  m=self.bundle['accepted-core-boundary-map.json']
  self.assertEqual(716,m['exact_source_core_boundary']['fixed_store_line'])
  self.assertEqual(0,m['claimed_451814442_discount'])
  self.assertFalse(m['accepted_core_price_transferred'])
  self.assertIn('core_before_fixed_store',self.cuts)
  self.assertIn('core_fixed_store_and_after',self.cuts)
 def test_only_synthetic_complete_terms_allow_component_evaluation(self):
  result=M.require_complete(self.interface,self.sizes,self.cuts,self.unsized)
  self.assertGreater(result,self.interface['fixed_source_action_units']+self.interface['known_native_occurrence_bytes'])
  self.assertFalse(self.interface['operational_grant'])
  self.assertFalse(self.interface['complete_host_quote'])
 def test_every_missing_layout_is_mandatory_positive(self):
  for key in self.sizes:
   for bad in (None,0,-1,True,'8'):
    values=dict(self.sizes)
    if bad is None:del values[key]
    else:values[key]=bad
    with self.assertRaises(ValueError,msg=f'{key}={bad}'):
     M.require_complete(self.interface,values,self.cuts,self.unsized)
 def test_every_external_callee_and_drop_cut_is_mandatory_positive(self):
  for key in self.cuts:
   for bad in (None,0,-1,True,'1'):
    values=dict(self.cuts)
    if bad is None:del values[key]
    else:values[key]=bad
    with self.assertRaises(ValueError,msg=f'{key}={bad}'):
     M.require_complete(self.interface,self.sizes,values,self.unsized)
 def test_unsized_backing_cannot_be_zero_or_omitted(self):
  for v in ({},{'str':0},{'str':-1},{'str':True},{'str':'1'}):
   with self.assertRaises(ValueError):M.require_complete(self.interface,self.sizes,self.cuts,v)
 def test_u64_overflow_and_noninteger_refuse(self):
  self.assertEqual(M.U64_MAX,M.checked_sum([M.U64_MAX]))
  for v in ([M.U64_MAX,1],[-1],[True],['1']):
   with self.assertRaises(ValueError):M.checked_sum(v)
  for a,b in [(M.U64_MAX,2),(-1,2),(True,2),(1,'2')]:
   with self.assertRaises(ValueError):M.checked_product(a,b)
  huge=dict(self.sizes);huge[next(iter(huge))]=M.U64_MAX
  with self.assertRaises(ValueError):M.require_complete(self.interface,huge,self.cuts,self.unsized)
 def test_cfg_cycles_missing_target_unknown_terminal_refuse(self):
  for g in [dict(bb0=dict(lines=[(1,'goto -> bb0;')])),dict(bb0=dict(lines=[(1,'goto -> bb1;')])),dict(bb0=dict(lines=[(1,'unknown;')]))]:
   with self.assertRaises(ValueError):M.paths(g)
 def test_unknown_type_is_never_scalar_fallback(self):
  shapes=M.SourceShapes({'one.rs':b'struct Known { x: u64 }'})
  with self.assertRaises(ValueError):shapes.n('UnknownPayload')
 def test_unknown_mir_local_and_constant_refuse(self):
  with self.assertRaises(ValueError):D.operation('_9 = move _1;',{'_1':{}})
  with self.assertRaises(ValueError):D.constants('_1 = const MissingGlobal;')
 def test_unsupported_missing_or_ambiguous_boundary_refuses(self):
  raw=self.bundle['selected-boundaries.mir']
  with self.assertRaises(ValueError):D.functions(raw.replace('fn run_one_loaded_fixture_v1(', 'fn missing_leaf('))
  with self.assertRaises(ValueError):D.functions(raw+raw)
 def test_inactive_test_payload_excluded_and_standard_backing_explicit(self):
  defs=self.bundle['scalar-shapes.json']['definitions']
  self.assertNotIn('DispatchTest',str(defs['AccountedWasi']))
  self.assertNotIn('TestState',str(defs['WasiContext']))
  self.assertIn('retained_dynamic_resource_backing_and_native_transfer_allowance',self.cuts)
 def test_source_resource_names_do_not_cross_bind(self):
  defs=self.bundle['scalar-shapes.json']['definitions']
  self.assertEqual('src/experimental/mod.rs',defs['experimental::Resource']['path'])
  self.assertEqual('src/experimental_wasi/mod.rs',defs['experimental_wasi::Resource']['path'])
 def test_every_cut_has_a_nonzero_occurrence_bound(self):
  self.assertTrue(all(isinstance(n,int) and n>0 for n in self.interface['required_nonzero_callee_drop_and_backing_cuts'].values()))
  self.assertGreater(len(self.interface['missing_native_occurrence_coefficients']),0)
  self.assertFalse(self.interface['actual_callees_priced'])
 def test_scope_remains_proposal_only(self):
  for key in ('operational_grant','actual_writer_or_fixture_execution','native_OTA_GA_accepted','actual_native_layouts_complete','source_body_tests_are_runtime_receipts'):
   self.assertIs(self.interface[key],False)
  self.assertIs(self.interface['WorkAuditPending'],True)

if __name__=='__main__':unittest.main(verbosity=2)
