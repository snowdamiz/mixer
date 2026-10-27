"""Deterministic storage and lifetime controls. No product runtime or compiler."""
import dataclasses as dc,json,unittest,copy
from pathlib import Path
from model import *
HERE=Path(__file__).resolve().parent

def b(n=1,name='synthetic-unselected-bound'):return Bound(n,name)
def fixture(inv):
 return RequiredStorage(SOURCE,HOST,tuple(PathBacking(b(12),b(12),b(13)) for _ in range(5)),
  b(),b(),b(512),b(),OriginalValidationBudget(b(64*1024**2),b(16*1024**2),b(1024**2)),
  b(100),b(200),b(512),b(512),b(),b(4097),b(),b(),CountBound(1,'synthetic-count'),b(),b(16*1024**2),
  {k:b(65536) for k in inv['required_layouts']})

class StorageControls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.inv=json.loads((HERE/'inline-inventory.json').read_text())
 def setUp(self):self.x=fixture(self.inv)
 def test_fixed_exact_inline_rosters(self):
  y=checked_inventory(self.inv,self.x.missing_layout_extents)
  self.assertEqual((y['P0'],y['child'],y['leaf']),(234375,76696,320766))
  self.assertEqual(len(self.inv['loader_slots']),9403)
  self.assertEqual(sum(r['validator'] for r in self.inv['loader_slots']),6458)
 def test_complete_positive_evaluation_and_distinct_six_parts(self):
  y=evaluate(self.inv,self.x)
  self.assertEqual(set(y['six_child_storage_parts']),set(COMPONENTS))
  self.assertEqual(y['child_prepaid_storage'],sum(y['six_child_storage_parts'].values()))
  self.assertEqual(y['whole_external_storage'],y['P0_preexisting_required_before_policy_quote_account_entry']+y['child_prepaid_storage'])
  self.assertTrue(y['RootPolicyPending']);self.assertFalse(y['whole_host_grant'])
 def test_product_retention_and_H_appear_once(self):
  y=evaluate(self.inv,self.x)
  self.assertEqual(y['product_recipe'],dict(C=79676,S=941467,A=430175,H_unit=81327,retained=1899541,H_added_again=0,product_limit_unchanged=268435456))
  self.assertEqual([r['bytes'] for r in y['source_object_owner_roster'] if r['id']=='product-accepted-full-retention'],[1899541])
 def test_native_work_occurrence_totals_are_not_storage(self):
  self.assertEqual(self.inv['leaf_work_native_occurrence_bytes_used'],0)
  self.assertEqual(self.inv['leaf_bytes'],320766)
  self.assertNotIn(3597716,[r['bytes'] for r in evaluate(self.inv,self.x)['source_object_owner_roster']])
 def test_all_unknown_bytes_are_positive_finite_no_default(self):
  bad=[None,0,-1,True,1.5,'1',U64+1]
  fields=[f.name for f in dc.fields(RequiredStorage) if isinstance(getattr(self.x,f.name),Bound)]
  for field in fields:
   for value in bad:
    with self.subTest(field=field,value=value),self.assertRaises((Refused,TypeError,AttributeError)):
     evaluate(self.inv,dc.replace(self.x,**{field:Bound(value,'unknown')}))
 def test_all_required_path_dimensions(self):
  for index in range(5):
   for field in ['encoded_bytes','p0_backing_bytes','open_temporary_bytes']:
    for value in [0,None,-1,True,U64+1]:
     paths=list(self.x.paths);paths[index]=dc.replace(paths[index],**{field:b(value)})
     with self.subTest(index=index,field=field,value=value),self.assertRaises(Refused):evaluate(self.inv,dc.replace(self.x,paths=tuple(paths)))
  for count in [0,1,4,6]:
   with self.assertRaises(Refused):evaluate(self.inv,dc.replace(self.x,paths=self.x.paths[:count] if count<6 else self.x.paths+(self.x.paths[0],)))
 def test_path_backing_conversion_and_no_reused_4096_cap(self):
  with self.assertRaises(Refused):PathBacking(b(10),b(9),b(11)).checked()
  with self.assertRaises(Refused):PathBacking(b(10),b(10),b(10)).checked()
  for n in [4096,4097,65536,1<<32]:self.assertEqual(PathBacking(b(n),b(n),b(n+1)).checked(),(n,n,n+1))
 def test_missing_unknown_layout_and_each_layout_value(self):
  for k in self.inv['required_layouts']:
   cuts=dict(self.x.missing_layout_extents);cuts.pop(k)
   with self.subTest(k=k),self.assertRaises(Refused):evaluate(self.inv,dc.replace(self.x,missing_layout_extents=cuts))
   for bad in [0,None,-1,True,U64+1]:
    cuts=dict(self.x.missing_layout_extents);cuts[k]=b(bad)
    with self.subTest(k=k,bad=bad),self.assertRaises(Refused):evaluate(self.inv,dc.replace(self.x,missing_layout_extents=cuts))
  cuts=dict(self.x.missing_layout_extents,unknown=b())
  with self.assertRaises(Refused):evaluate(self.inv,dc.replace(self.x,missing_layout_extents=cuts))
 def test_count_is_typed_positive_finite(self):
  for count in [0,None,-1,True,1.5,U64+1]:
   with self.assertRaises(Refused):evaluate(self.inv,dc.replace(self.x,error_owner_count=CountBound(count,'unselected')))
  with self.assertRaises(AttributeError):evaluate(self.inv,dc.replace(self.x,error_owner_count=b()))
 def test_explicit_source_obligations_required(self):
  for cut in [Bound(1,''),Bound(1,' '),Bound(1,None)]:
   with self.assertRaises(Refused):evaluate(self.inv,dc.replace(self.x,outer_parent_inline=cut))
 def test_source_identity_and_recursive_or_duplicate_slot_fail_closed(self):
  for field in ['source_tree_sha256','host_tree_sha256']:
   with self.assertRaises(Refused):evaluate(self.inv,dc.replace(self.x,**{field:'0'*64}))
  for mutation in ['recursive','duplicate','changed']:
   inv=copy.deepcopy(self.inv)
   if mutation=='recursive':inv['all_authored_frame_call_graph_acyclic']=False
   elif mutation=='duplicate':inv['loader_slots'][0]['id']=inv['loader_slots'][1]['id']
   else:inv['caller_slots'][0]['bytes']+=1
   with self.assertRaises(Refused):evaluate(inv,self.x)
 def test_checked_arithmetic_and_overflow(self):
  self.assertEqual(add(U64,0),U64);self.assertEqual(mul(U64,1),U64)
  for action in [lambda:add(U64,1),lambda:mul(U64,2),lambda:evaluate(self.inv,dc.replace(self.x,outer_parent_inline=b(U64))),lambda:evaluate(self.inv,dc.replace(self.x,error_owner_count=CountBound(U64,'unselected'),error_backing_each=b(2)))]:
   with self.assertRaises(Refused):action()
 def test_original_validation_budgets_and_geometry_narrow_only(self):
  for name,n in [('source_file_bytes',67108865),('build_file_bytes',131073),('session_file_bytes',65537),('executable_file_bytes',67108865),('initial_cache_requested_backing',16777217)]:
   with self.subTest(name=name),self.assertRaises(Refused):evaluate(self.inv,dc.replace(self.x,**{name:b(n)}))
  for name,n in [('source_bytes',67108865),('metadata_bytes',16777217),('scratch_bytes',1048577)]:
   with self.assertRaises(Refused):evaluate(self.inv,dc.replace(self.x,original_validation=dc.replace(self.x.original_validation,**{name:b(n)})))
 def test_immutable_binding_is_backing_not_reference_width(self):
  for n in [8,80,256,511]:
   with self.assertRaises(Refused):evaluate(self.inv,dc.replace(self.x,reviewed_binding_object=b(n)))
 def test_executable_input_proof_lifetimes_and_union(self):
  y=evaluate(self.inv,self.x);owners={r['id']:r for r in y['source_object_owner_roster']}
  self.assertEqual(owners['loader-executable-Vec']['last'],'P1_EXECUTABLE')
  self.assertEqual(owners['loader-input-Vec']['first'],'P1_VALIDATE')
  self.assertEqual(owners['original-proof-source-Box']['last'],'P5_DESTROYING')
  expected=512+512+max(200,100+67108864+16777216+1048576)
  self.assertEqual(y['loader_buffer_peak'],expected)
  for v in y['actual_logical_owner_union_by_phase'].values():self.assertLessEqual(v,y['whole_external_storage'])
 def test_cancellation_shared_backing_and_retained_original_files(self):
  owners={r['id']:r for r in evaluate(self.inv,self.x)['source_object_owner_roster']}
  self.assertEqual(owners['actual-shared-Cancellation-ArcInner']['bytes'],24)
  self.assertEqual(owners['actual-shared-Cancellation-ArcInner']['last'],'P5_DESTROYING')
  self.assertEqual(owners['actual-six-File-resource-envelope']['bytes'],6)
  self.assertEqual(owners['actual-six-File-resource-envelope']['last'],'P5_DESTROYING')
 def test_no_child_charge_before_quote_and_no_early_retirement(self):
  y=evaluate(self.inv,self.x);t=y['conservative_held_charge_trace'];child=y['child_prepaid_storage']
  self.assertEqual([r['child_held'] for r in t[:2]],[0,0])
  self.assertTrue(all(r['child_held']==child for r in t[2:-1]));self.assertEqual(t[-1]['child_held'],0)
  a=RetentionControl()
  for action in [a.quote_after_p0,lambda:a.reserve(1),a.dispatch,a.retire]:
   with self.assertRaises(Refused):action()
  a.provision_p0(1);a.quote_after_p0();a.reserve(child);a.dispatch()
  for _ in range(3):
   self.assertEqual(a.implicit_drop_or_unwind(),child)
   with self.assertRaises(Refused):a.retire()
  a.destroy(False);self.assertEqual(a.held,child)
  with self.assertRaises(Refused):a.retire()
  a.destroy(True);self.assertEqual(a.held,child);a.retire();self.assertEqual(a.held,0)
  with self.assertRaises(Refused):a.retire()
 def test_monotone_unknown_bounds(self):
  baseline=evaluate(self.inv,self.x)['whole_external_storage']
  for field in ['outer_parent_inline','outer_parent_owned_backing','immutable_identity_and_diagnostic_backing','loader_native_temporaries','error_backing_each','all_payload_destructor_temporaries']:
   y=evaluate(self.inv,dc.replace(self.x,**{field:b(2)}))
   self.assertGreater(y['whole_external_storage'],baseline)

if __name__=='__main__':unittest.main(verbosity=2)
