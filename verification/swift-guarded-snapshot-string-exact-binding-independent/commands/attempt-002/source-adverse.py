"""New independent hostile controls against the frozen checker, never its writers."""
import collections,copy,json,sys,unittest
from common import C,inputs,need
sys.path.insert(0,str(C));import mir_graph as p
import type_contracts as types
class Adverse(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.mir,cls.source=inputs();cls.g=json.loads((C/'graph.json').read_text());cls.cat=json.loads((C/'authored-contracts.json').read_text())
  cls.fs=cls.g['nodes'];cls.bn=collections.defaultdict(list);cls.bb=collections.defaultdict(list)
  for k,r in cls.fs.items():cls.bn[r['name']].append(k);cls.bb[r['base']].append(k)
 def denied(self,fn,*args):
  with self.assertRaises(p.Refused):fn(*args)
 def altered(self,key,old,new):
  h=self.fs[key]['header'];a=self.mir.index(h+'\n');z=self.mir.index('\n}\n',a)+3;b=self.mir[a:z]
  self.assertEqual(b.count(old),1);return self.mir[:a]+b.replace(old,new,1)+self.mir[z:]
 def test_complete_identity_namespace_trait_receiver_and_generic_mutations(self):
  n=0
  for target,c in self.cat['contracts'].items():
   self.assertTrue(p.resolve(target,self.fs,self.bn,self.bb))
   for altered in ('foreign::'+target,'std::future_vendor::'+target,target+'::<Foreign>'):
    self.assertEqual(p.resolve(altered,self.fs,self.bn,self.bb),[]);n+=1
   if target.startswith('<') and ' as ' in target:
    altered=target.replace(' as ',' as foreign::',1)
    self.assertEqual(p.resolve(altered,self.fs,self.bn,self.bb),[]);n+=1
  self.assertGreater(n,1269)
 def test_all_direct_signatures_and_exact_name_destination_types(self):
  n=0
  for target,c in self.cat['contracts'].items():
   dest=p.resolve(target,self.fs,self.bn,self.bb)
   for sig in c['signatures']:
    call={'arguments':[{'type':t,'operand':'review'} for t in sig['arguments']],'result_type':sig['result']}
    p.validate_authored_call(target,call,dest,self.fs);n+=1
    changed=copy.deepcopy(call);changed['result_type']='Result<'+sig['result']+', foreign::Fault>'
    self.denied(p.validate_authored_call,target,changed,dest,self.fs)
    changed=copy.deepcopy(call)
    if changed['arguments']:changed['arguments'][0]['type']='foreign::'+changed['arguments'][0]['type']
    else:changed['arguments'].append({'type':'foreign::Fault','operand':'review'})
    self.denied(p.validate_authored_call,target,changed,dest,self.fs)
  self.assertEqual(n,434)
  # Bypass the catalog lookup deliberately with the actual full authored name.
  # Exact-name precedence must still enforce the destination declaration.
  row=self.fs['f0982'];name=row['name'];call={'arguments':[{'type':t,'operand':'review'} for t in row['params'].values()],'result_type':row['return_type']}
  p.validate_authored_call(name,call,['f0982'],self.fs)
  for bad in ({'arguments':call['arguments'][:-1],'result_type':call['result_type']},{'arguments':call['arguments'],'result_type':'Option<control::Fault>'},{'arguments':[{'type':'u32','operand':'review'},*call['arguments'][1:]],'result_type':call['result_type']}):self.denied(p.validate_authored_call,name,bad,['f0982'],self.fs)
 def test_finite_aliases_preserve_foreign_names_and_structural_boundaries(self):
  for short,full in self.cat['type_path_aliases'].items():
   self.assertEqual(types.canonical(short),types.canonical(full))
   self.denied(types.unify,full,'foreign::'+short,{})
  for short,full in self.cat['selected_specializations'].items():
   self.assertEqual(types.canonical(short),types.canonical(full))
   self.denied(types.unify,full,'Foreign'+short,{})
  for a,b in [('Option<T>','Result<u8, u8>'),('(T, T)','(u32, u64)'),('[T; 8]','[u8; 9]'),('&mut T','&u8'),('Result<T, T>','Result<Option<u8>, Option<u16>>'),('Vec<T>','foreign::Vec<u8>')]:self.denied(types.unify,a,b,{})
 def test_typed_constants_require_exact_reviewed_origin(self):
  for name,t in self.cat['constant_types'].items():
   types.unify(t,'exact-compiler-constant:'+name,{})
   for changed in ('foreign::'+name,name+'x',name.replace('::','::foreign::',1)):
    self.denied(types.unify,t,'exact-compiler-constant:'+changed,{})
 def test_all_closure_adapter_argument_result_and_environment_contracts(self):
  count=0
  for key,c in self.cat['closure_contracts'].items():
   outer,site=key.rsplit(' | ',1);dest=[k for k,r in self.fs.items() if r['name'] in c['definitions']]
   call={'target':outer,'arguments':[{'type':t,'operand':'review'} for t in c['outer_arguments']],'result_type':c['outer_result']}
   p.validate_closure_callback(site,call,dest,self.fs);count+=1
   changed=copy.deepcopy(call);changed['result_type']='Option<foreign::Fault>';self.denied(p.validate_closure_callback,site,changed,dest,self.fs)
   changed=copy.deepcopy(call)
   if changed['arguments']:changed['arguments'][-1]['type']='foreign::FnEnvironment'
   else:changed['arguments'].append({'type':'u8','operand':'review'})
   self.denied(p.validate_closure_callback,site,changed,dest,self.fs)
   for field in ('return_type','params','local_types'):
    rows=dict(self.fs);row=copy.deepcopy(rows[dest[0]]);rows[dest[0]]=row
    if field=='return_type':row[field]='Result<(), foreign::Fault>'
    elif field=='params':row[field][next(iter(row[field]))]='&foreign::Environment'
    else:row[field]['_0']='Option<foreign::Fault>'
    self.denied(p.validate_closure_callback,site,call,dest,rows)
  self.assertEqual(count,181)
 def test_named_callback_declaration_argument_and_result_mutations(self):
  count=0
  for target,c in self.cat['contracts'].items():
   dest=p.resolve(target,self.fs,self.bn,self.bb)
   for sig in c['named_callback_signatures']:
    p.validate_named_callback(target,sig['outer_target'],dest,self.fs);count+=1
    for field in ('params','return_type'):
     rows=dict(self.fs);row=copy.deepcopy(rows[dest[0]]);rows[dest[0]]=row
     if field=='params':row[field][next(iter(row[field]))]='foreign::CallbackArgument'
     else:row[field]='Option<foreign::Fault>'
     self.denied(p.validate_named_callback,target,sig['outer_target'],dest,rows)
  self.assertEqual(count,4)
 def test_full_mir_exact_name_mismatched_argument(self):
  old='control::Fault::new(move _7, const "swift_cache_layout_overflow")'
  new=self.fs['f0982']['name']+'(const 42_u32, const "swift_cache_layout_overflow")'
  self.denied(p.analyze,self.altered('f0730',old,new),self.source)
 def test_full_mir_exact_name_mismatched_result(self):
  old='control::Fault::new(move _7, const "swift_cache_layout_overflow")'
  m=self.altered('f0730',old,self.fs['f0982']['name']+'(move _7, const "swift_cache_layout_overflow")')
  h=self.fs['f0730']['header'];a=m.index(h+'\n');z=m.index('\n}\n',a)+3;b=m[a:z]
  local='let mut _6: '+self.fs['f0730']['local_types']['_6']+';';self.assertEqual(b.count(local),1)
  m=m[:a]+b.replace(local,'let mut _6: Option<control::Fault>;',1)+m[z:];self.denied(p.analyze,m,self.source)
 def test_full_mir_existing_different_const_generic_target(self):
  old='retained_profile_loader_v1::Bytes::<16384>::new';new='retained_profile_loader_v1::Bytes::<4096>::new'
  k,c=next((k,c) for k,r in self.fs.items() for c in r['calls'] if c['target']==old)
  self.denied(p.analyze,self.altered(k,c['statement'],c['statement'].replace(old,new)),self.source)
 def test_full_mir_reviewed_constant_changed_origin(self):
  k,c=next((k,c) for k,r in self.fs.items() for c in r['calls'] if any(a['type'].endswith('::CONSTRUCTION_CURSOR_V1') for a in c['arguments']))
  self.denied(p.analyze,self.altered(k,c['statement'],c['statement'].replace('experimental_swift_reactor::cache::initial_profile_v1::CONSTRUCTION_CURSOR_V1','foreign::CONSTRUCTION_CURSOR_V1')),self.source)
 def test_full_mir_closure_body_result_changed(self):
  row=self.fs['f1412'];old='let mut _0: '+row['local_types']['_0']+';'
  self.denied(p.analyze,self.altered('f1412',old,'let mut _0: Result<u64, std::io::Error>;'),self.source)
 def test_full_mir_closure_argument_kind_changed(self):
  self.denied(p.analyze,self.altered('f1412','_2: &[u8]','_2: &mut [u8]'),self.source)
if __name__=='__main__':
 group=sys.argv[1] if len(sys.argv)>1 else 'finite'
 allnames=unittest.defaultTestLoader.getTestCaseNames(Adverse)
 groups={'finite':[n for n in allnames if not n.startswith('test_full_mir_')],'exact':['test_full_mir_exact_name_mismatched_argument','test_full_mir_exact_name_mismatched_result'],'generic':['test_full_mir_existing_different_const_generic_target','test_full_mir_reviewed_constant_changed_origin'],'closure':['test_full_mir_closure_body_result_changed','test_full_mir_closure_argument_kind_changed']}
 result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Adverse(n) for n in groups[group]));raise SystemExit(not result.wasSuccessful())
