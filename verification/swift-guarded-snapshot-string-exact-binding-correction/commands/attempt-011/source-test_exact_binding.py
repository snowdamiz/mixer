"""S1-S5 regression controls; no compiler or product program is executed."""
import copy,gzip,json,sys,unittest
from pathlib import Path
import mir_graph as p
D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification'
class ExactBindingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  base=V/'swift-guarded-snapshot-loader-work-source146'
  refs=json.loads((base/'source-reference-map.json').read_text())
  cls.source={m['path']:(R/m['source']).read_text() for m in refs['members'] if m['path'].endswith('.rs')}
  cls.mir=gzip.decompress((base/'whole-source146.mir.gz').read_bytes()).decode()
  cls.graph=json.loads((D/'graph.json').read_text())
 def altered_body(self,key,old,new):
  row=self.graph['nodes'][key];start=self.mir.index(row['header']+'\n');end=self.mir.index('\n}\n',start)+3
  body=self.mir[start:end];self.assertEqual(body.count(old),1,(key,old))
  return self.mir[:start]+body.replace(old,new,1)+self.mir[end:]
 def refuse_mir(self,mir,reason):
  with self.assertRaisesRegex(p.Refused,reason):p.analyze(mir,self.source)
 def test_balanced_nested_fn_tuple_array_and_generic_types(self):
  param="impl FnOnce((u32, [fn([u8; 3]) -> Result<(u32, u64), E>; 2])) -> Result<Option<fn() -> [u8; 4]>, E>"
  returned="Result<(fn() -> [u8; 8], [Option<fn(u8) -> u32>; 2]), E>"
  text='fn nested(_1: '+param+', _2: [u8; 8]) -> '+returned+' {\n    let mut _0: '+returned+';\n    bb0: {\n        return;\n    }\n}\n'
  fs,_,_=p.parse_functions(text,{})
  self.assertEqual(fs['f0000']['params'],{'_1':param,'_2':'[u8; 8]'})
  self.assertEqual(fs['f0000']['return_type'],returned)
  self.assertEqual(fs['f0000']['local_types']['_1'],param)
  for malformed in (text.replace('>; 2]','>; 2}',1),text.replace(' -> '+returned,' -> '+returned[:-1],1)):
   self.assertNotEqual(malformed,text)
   with self.assertRaises(p.Refused):p.parse_functions(malformed,{})
 def test_all_2009_headers_and_full_nine_header_discrepancy_roster(self):
  inventory=json.loads((D/'typed-header-inventory.json').read_text())
  fs,_,_=p.parse_functions(self.mir,self.source)
  self.assertEqual(len(fs),2009)
  for key,row in fs.items():
   for field in ('params','return_type','local_types'):self.assertEqual(row[field],inventory['headers'][key][field])
  expected={'f0907','f1257','f1258','f1297','f1298','f1299','f1300','f1319','f1405'}
  self.assertEqual({r['function'] for r in inventory['historical_discrepancy_roster']['whole_compiler_pool_header_misparses']},expected)
 def test_full_mir_foreign_namespace_refuses(self):
  self.refuse_mir(self.altered_body('f0730','control::Fault::new','foreign::Fault::new'),'unreviewed-exact-external-contract')
 def test_full_mir_std_namespace_refuses(self):
  self.refuse_mir(self.altered_body('f0730','control::Fault::new','std::future_vendor::Fault::new'),'unreviewed-exact-external-contract')
 def test_full_mir_unknown_trait_with_authored_receiver_refuses(self):
  self.refuse_mir(self.altered_body('f0730','control::Fault::new','<control::Fault as foreign::Mint>::new'),'unreviewed-exact-external-contract')
 def test_full_mir_policy_namespace_refuses(self):
  row=next((k,c) for k,r in self.graph['nodes'].items() for c in r['calls'] if c['target']=="experimental::policy::Policy::<'static>::swift")
  self.refuse_mir(self.altered_body(row[0],row[1]['statement'],row[1]['statement'].replace("experimental::policy::Policy::<'static>::swift",'foreign::Policy::swift')),'unreviewed-exact-external-contract')
 def test_full_mir_foreign_shared_control_receiver_refuses(self):
  target="<<B as ClosedBranchV1>::Access<'_> as SharedControlV1>::shared_control"
  key,call=next((k,c) for k,r in self.graph['nodes'].items() for c in r['calls'] if c['target']==target)
  self.refuse_mir(self.altered_body(key,call['statement'],call['statement'].replace(target,'<Foreign as SharedControlV1>::shared_control')),'unreviewed-exact-external-contract')
 def test_full_mir_foreign_meter_receiver_refuses(self):
  target='<C as experimental::account::MeterControl>::expired'
  key,call=next((k,c) for k,r in self.graph['nodes'].items() for c in r['calls'] if c['target']==target)
  self.refuse_mir(self.altered_body(key,call['statement'],call['statement'].replace(target,'<Foreign as experimental::account::MeterControl>::expired')),'unreviewed-exact-external-contract')
 def test_full_mir_missing_authored_argument_refuses(self):
  self.refuse_mir(self.altered_body('f0730',', const "swift_cache_layout_overflow"',''),'unreviewed-authored-typed-signature')
 def test_full_mir_changed_authored_argument_refuses(self):
  self.refuse_mir(self.altered_body('f0730','let mut _7: control::SwiftRunFailureKind;','let mut _7: u32;'),'unreviewed-authored-typed-signature')
 def test_full_mir_changed_nested_authored_result_refuses(self):
  self.refuse_mir(self.altered_body('f0730','let mut _6: control::Fault;','let mut _6: Option<control::SwiftRunFailure>;'),'unreviewed-authored-typed-signature')
 def test_full_mir_changed_named_callback_result_refuses(self):
  edge=next(e for e in self.graph['edges'] if e['kind']=='named-authored-callback' and e['target']=='accounted::AccountedWasi::usage')
  call=next(c for c in self.graph['nodes'][edge['caller']]['calls'] if c['line']==edge['line'])
  changed=call['statement'].replace(' -> experimental_wasi::WasiUsage {',' -> Option<control::SwiftRunFailure> {')
  self.assertNotEqual(changed,call['statement'])
  self.refuse_mir(self.altered_body(edge['caller'],call['statement'],changed),'unreviewed-authored-function-item-type')
 def test_full_mir_unknown_named_callback_refuses(self):
  edge=next(e for e in self.graph['edges'] if e['kind']=='named-authored-callback' and e['target']=='accounted::AccountedWasi::usage')
  call=next(c for c in self.graph['nodes'][edge['caller']]['calls'] if c['line']==edge['line'])
  self.refuse_mir(self.altered_body(edge['caller'],call['statement'],call['statement'].replace(edge['target'],'foreign::AccountedWasi::usage')),'unclosed-named-function-item')
 def test_full_mir_changed_closure_header_refuses(self):
  self.refuse_mir(self.altered_body('f1412','_2: &[u8]','_2: &[u16]'),'closure-definition-typed-signature')
 def test_catalog_is_complete_identity_and_type_contract_not_body_hash(self):
  catalog=json.loads((D/'authored-contracts.json').read_text())
  self.assertEqual(len(catalog['contracts']),423)
  self.assertEqual(sum(len(c['signatures']) for c in catalog['contracts'].values()),434)
  self.assertEqual(sum(len(c['named_callback_signatures']) for c in catalog['contracts'].values()),4)
  self.assertTrue(catalog['closure_contracts'])
  self.assertNotIn('MIR_sha256',json.dumps(catalog))
  for contract in catalog['contracts'].values():
   for sig in contract['signatures']:self.assertEqual(len(sig['type_equations']),len(sig['arguments'])+1)

if __name__=='__main__':
 # Full-MIR attacks are split across bounded <=55-second recorder children.
 group=sys.argv[1:] or ['syntax']
 names=[n for n in unittest.defaultTestLoader.getTestCaseNames(ExactBindingTests)]
 groups={'syntax':[n for n in names if not n.startswith('test_full_mir_')],
  'identity':[n for n in names if n in ('test_full_mir_foreign_namespace_refuses','test_full_mir_std_namespace_refuses','test_full_mir_unknown_trait_with_authored_receiver_refuses','test_full_mir_policy_namespace_refuses')],
  'receiver':[n for n in names if 'receiver_refuses' in n],
  'types':[n for n in names if n in ('test_full_mir_missing_authored_argument_refuses','test_full_mir_changed_authored_argument_refuses','test_full_mir_changed_nested_authored_result_refuses')],
  'callbacks':[n for n in names if n in ('test_full_mir_changed_named_callback_result_refuses','test_full_mir_unknown_named_callback_refuses','test_full_mir_changed_closure_header_refuses')]}
 selected=[n for g in group for n in groups[g]]
 result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(ExactBindingTests(n) for n in selected))
 raise SystemExit(not result.wasSuccessful())
