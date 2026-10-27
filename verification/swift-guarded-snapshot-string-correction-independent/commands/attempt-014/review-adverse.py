#!/usr/bin/env python3
"""Independent attack expectations against the frozen analysis target.

Imports only mir_graph as the system under test, never its recorders, derivation
or acceptance helper. Deliberate failures are retained as evidence.
"""
import collections,gzip,hashlib,json,sys,unittest
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification';C=V/'swift-guarded-snapshot-string-provenance-correction'
sys.path.insert(0,str(C));import mir_graph as target
ROOTS=('run_one_fixture_v1','run_prepaid_fixture_v1','run_one_loaded_fixture_v1','destroy_returned_fixture_v1','release_after_retirement_v1')
def mini(statement='',extra='',locals_=''):
 text=''
 for i,name in enumerate(ROOTS):
  text+=f'fn {name}() -> () {{\n    let mut _0: ();\n'+(locals_ if i==0 else '')+'    bb0: {\n'+(statement if i==0 else '')+'        return;\n    }\n}\n'
 return text+extra+'\nalloc999999 (size: 8, align: 1) {\n    00 00 00 00 00 00 00 00\n}\n'
class Adverse(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  base=V/'swift-guarded-snapshot-loader-work-source146';refs=json.loads((base/'source-reference-map.json').read_text())
  cls.source={m['path']:(R/m['source']).read_text() for m in refs['members'] if m['path'].endswith('.rs')}
  cls.mir=gzip.decompress((base/'whole-source146.mir.gz').read_bytes()).decode();cls.graph=json.loads((C/'graph.json').read_text())
  cls.fault=cls.graph['nodes']['f0982'];header=cls.fault['header'];start=cls.mir.index(header+'\n');end=cls.mir.index('\n}\n',start)+3;cls.faultbody=cls.mir[start:end]
  cls.indices=(collections.defaultdict(list),collections.defaultdict(list))
  for k,row in cls.graph['nodes'].items():cls.indices[0][row['name']].append(k);cls.indices[1][row['base']].append(k)
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'observations'):(D/'attack-observations.json').write_text(json.dumps(cls.observations,indent=2,sort_keys=True)+'\n')
 def refusal(self,fn,*args):
  try:result=fn(*args)
  except target.Refused:return
  if not hasattr(type(self),'observations'):type(self).observations=[]
  row={'test':self._testMethodName,'target_function':fn.__name__,'expected':'Refused','actual':'accepted without Refused'}
  if fn.__name__=='analyze':
   row['input_mir_sha256']=hashlib.sha256(args[0].encode()).hexdigest();row['nodes']=len(result['nodes']);row['edges']=len(result['edges']);row['foreign_edges']=[e for e in result['edges'] if 'foreign' in e['target'] or 'future_vendor' in e['target']]
  type(self).observations.append(row);self.fail('Refused not raised')
 def test_unknown_full_namespace_in_actual_frozen_route_must_refuse(self):
  old='_6 = control::Fault::new(move _7, const "swift_cache_layout_overflow") -> [return: bb1, unwind continue];'
  self.assertEqual(self.mir.count(old),1)
  altered=self.mir.replace(old,old.replace('control::Fault::new','foreign::Fault::new'),1)
  self.refusal(target.analyze,altered,self.source)
 def test_unknown_std_namespace_authored_shadow_must_refuse(self):
  call='        _9 = std::future_vendor::Fault::new(move _7, const "seed") -> [return: bb1, unwind continue];\n'
  self.refusal(target.analyze,mini(call,self.faultbody,'    let mut _7: control::SwiftRunFailureKind;\n    let mut _9: control::Fault;\n'),self.source)
 def test_unknown_trait_with_authored_receiver_must_refuse(self):
  call='        _9 = <control::Fault as foreign::Mint>::new(move _7, const "seed") -> [return: bb1, unwind continue];\n'
  self.refusal(target.analyze,mini(call,self.faultbody,'    let mut _7: control::SwiftRunFailureKind;\n    let mut _9: control::Fault;\n'),self.source)
 def test_selected_meter_trait_does_not_waive_foreign_receiver(self):
  self.assertEqual(target.resolve('<Foreign as experimental::account::MeterControl>::expired',self.graph['nodes'],*self.indices),[])
 def test_selected_shared_trait_does_not_waive_foreign_receiver(self):
  self.assertEqual(target.resolve('<Foreign as SharedControlV1>::shared_control',self.graph['nodes'],*self.indices),[])
 def test_unknown_namespace_policy_shadow_must_refuse(self):
  self.assertEqual(target.resolve('foreign::Policy::swift',self.graph['nodes'],*self.indices),[])
 def test_direct_authored_signature_mismatch_must_refuse(self):
  call='        _9 = control::Fault::new(const 7_u32) -> [return: bb1, unwind continue];\n'
  self.refusal(target.analyze,mini(call,self.faultbody,'    let mut _9: Option<control::SwiftRunFailure>;\n    let mut _99: &str;\n').replace('        return;', '        _99 = const \"seed\";\n        return;', 1),self.source)
 def test_unknown_reference_generic_comparison_targets_refuse(self):
  for name in ('<&Foreign as foreign::Mint>::clone','<Foreign<control::Fault> as foreign::Mint>::default','<Foreign as foreign::Compare>::eq','std::future_vendor::take'):
   with self.subTest(name=name):self.refusal(target.classify_external,name,['Option<control::SwiftRunFailure>'],[['&Foreign']])
 def test_end_to_end_unknown_nested_carrier_refuses(self):
  call='        _9 = std::future_vendor::take(const 0_u32) -> [return: bb1, unwind continue];\n'
  self.refusal(target.analyze,mini(call,'','    let mut _9: Option<control::SwiftRunFailure>;\n'),{})
 def test_exact_external_signature_changed_result_or_arg_refuses(self):
  name='<Result<(), experimental::Failure> as Try>::branch';contract=target.external_catalog()[name];sig=contract['signatures'][0]
  target.classify_external(name,[sig['result']],[sig['arguments']])
  self.refusal(target.classify_external,name,['Option<control::SwiftRunFailure>'],[sig['arguments']])
  self.refusal(target.classify_external,name,[sig['result']],[['&Foreign']])
 def test_unknown_fn_item_and_indirect_call_refuse(self):
  self.refusal(target.standard_named_callback,'foreign::Mint','Option::<u8>::map::<Foreign, fn(u8) -> Foreign {foreign::Mint}>')
  self.refusal(target.analyze,mini('        _0 = move _9() -> [return: bb1, unwind continue];\n'),{})
 def test_selected_inline_asm_refuses(self):
  self.refusal(target.analyze,mini('        _0 = asm!("mrs {0}, fpcr", out(reg) _0, options(NOMEM | NOSTACK)) -> [return: bb1, unwind continue];\n'),{})
 def test_two_standard_predicate_signatures_exact(self):
  for row in self.graph['standard_named_callbacks']:
   call=next(c for c in self.graph['nodes'][row['caller']]['calls'] if c['line']==row['line'])
   target.standard_named_callback(row['target'],call['target'])
   self.refusal(target.standard_named_callback,row['target'],call['target'].replace(' -> bool ',' -> Option<control::SwiftRunFailure> '))
 def test_actual_selected_fnonce_header_preserves_complete_types(self):
  header=self.graph['nodes']['f0907']['header'];start=self.mir.index(header+'\n');end=self.mir.index('\n}\n',start)+3
  fs,_,_=target.parse_functions(self.mir[start:end],self.source);row=fs['f0000']
  self.assertEqual(row['params']['_2'],'impl FnOnce() -> T')
  self.assertEqual(row['return_type'],"PrepaidOwnedV1<'_, T>")
 def test_actual_selected_fnmut_header_preserves_complete_types(self):
  header=self.graph['nodes']['f1405']['header'];start=self.mir.index(header+'\n');end=self.mir.index('\n}\n',start)+3
  fs,_,_=target.parse_functions(self.mir[start:end],self.source);row=fs['f0000']
  self.assertEqual(row['params']['_2'],'impl FnMut(&[u8]) -> io::Result<usize>')
  self.assertEqual(row['return_type'],'Result<diagnostic_profile::ProfileRowsObservationV1, diagnostic_profile::ProfileAdapterErrorV1>')
 def test_end_to_end_actual_selected_callback_header_types(self):
  graph=target.analyze(self.mir,self.source)
  self.assertEqual(graph['nodes']['f0907']['params']['_2'],'impl FnOnce() -> T')
  self.assertEqual(graph['nodes']['f1405']['params']['_2'],'impl FnMut(&[u8]) -> io::Result<usize>')
 def test_authored_exact_definition_is_resolved_before_external(self):
  name=self.fault['name'];self.assertEqual(target.resolve(name,self.graph['nodes'],*self.indices),['f0982'])
if __name__=='__main__':unittest.main(verbosity=2)
