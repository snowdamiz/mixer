"""Exact compiler-only array annotation proof, bound to parent typed fields.

This is no suffix-only exemption: each full CTFE body must return its actual
parent field's exact Array length, have one usize local/constant, and call none.
"""
import re
PREFIX='experimental_swift_reactor::execution::frame_operations::memory_growth_operations::lifecycle::LifecyclePermanentPositions'
def partition(records,config,query):
 declarations={r['path']:r for r in records if r['kind']=='declaration'}
 graphs={r['identity']:r['graph']for r in records if r['kind']=='type-graph'}
 locals={};constants={};fndef={}
 for r in records:
  key=(r.get('path'),r.get('promoted'))
  if r['kind']=='local':locals.setdefault(key,[]).append(r)
  elif r['kind']=='constant-operand':constants.setdefault(key,[]).append(r)
  elif r['kind']=='FnDef':fndef.setdefault(key,[]).append(r)
 declared=declarations[PREFIX]
 variant=declared['layout']['variants'][0]
 fields=dict(zip(variant['fieldNames'],variant['fields']))
 selected=set();proof=[]
 for body in records:
  if body['kind']!='body' or not body['path'].startswith(PREFIX+'::'):continue
  key=(body['path'],body['promoted']);assert body['promoted']is None
  tail=body['path'][len(PREFIX)+2:];field_name,marker=tail.rsplit('::',1)
  assert marker=='{constant#0}' and field_name in fields
  field=fields[field_name];graph=graphs[field['identity']]
  assert graph['kind']=='Ref' and graph['pointee']['kind']=='Array'
  actual_length=graph['pointee']['length'];assert actual_length==6
  ls=locals[key];ops=constants[key]
  assert len(ls)==1 and ls[0]['local']==0 and ls[0]['layout']['type']=='usize'
  assert len(ops)==1 and ops[0]['layout']['type']=='usize' and not fndef.get(key)
  mir=body['mir'];assert re.findall(r'_0 = const (\d+)_usize;',mir)==[str(actual_length)]
  assert len(re.findall(r'^    bb\d+:',mir,re.M))==1
  assert 'bb0:'in mir and not any(x in mir for x in [' -> [','goto ->','switchInt(','resume;','drop('])
  assert re.search(r'let (?:mut )?_0: usize;',mir)
  selected.add(key)
  proof.append({'config':config,'querySHA256':query,'body':body,'exactParentDeclaration':declared['path'],'parentDefPathHash':declared['defPathHash'],'fieldName':field_name,'actualParentFieldLayout':field,'actualParentFieldGraph':graph,'actualLength':actual_length,'actualReturnLocal':ls[0],'actualConstantOperand':ops[0],'noFunctionItemOrCall':True,'runtimeByteCredit':0,'partition':'compiler-type-annotation-only-not-admitted-runtime'})
 for key in selected:assert key[0].startswith(PREFIX+'::')
 filtered=[r for r in records if (r.get('path'),r.get('promoted'))not in selected]
 return filtered,proof
