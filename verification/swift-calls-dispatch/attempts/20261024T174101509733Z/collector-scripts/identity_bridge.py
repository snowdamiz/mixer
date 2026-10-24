"""Compare actual compiler type graphs with explicit contextual definition bridges.
No type spelling/equal-size alias or blanket hash erasure establishes identity.
"""
import collect as c
import json,gzip,re,copy
from functools import lru_cache

@lru_cache(None)
def source_binding(encoded):
 d=json.loads(encoded);s=d['source'];assert d['isLocal']and s is not None
 rel=s['file'];base=c.HERE/'candidate';p=base/rel
 assert not rel.startswith('/')and '..'not in p.relative_to(base).parts,(rel,'unbound local source')
 raw=p.read_bytes();manifest=json.loads((c.HERE/'candidate-final-manifest.json').read_text());assert c.sha(raw)==manifest[rel]
 lines=raw.decode().splitlines(keepends=True);lo=s['startLine']-1;hi=s['endLine']-1
 assert 0<=lo<=hi<len(lines);start=s['startColumn'];end=s['endColumn'];assert start>=0 and end>=0
 span=(lines[lo][start:end]if lo==hi else lines[lo][start:]+''.join(lines[lo+1:hi])+lines[hi][:end]).encode()
 assert span
 return {'file':rel,'fileSHA256':manifest[rel],'span':s,'spanSHA256':c.sha(span),'sourceClosure':json.loads((c.HERE/'candidate-final-source.json').read_text())['sourceClosure']}

def definition(a,b,definitions):
 assert set(a)==set(b)
 assert all(a[k]==b[k]for k in ['path','disambiguatedDefPath','kind','crateName','isLocal'])
 if not a['isLocal']:
  assert a==b,('external definition drift',a,b)
  proof={'method':'exact-external-identity-pinned-official-sysroot','origin':a,'compiled':b}
 else:
  sa=source_binding(json.dumps(a,sort_keys=True));sb=source_binding(json.dumps(b,sort_keys=True));assert sa==sb
  assert a['span']==b['span']
  def parts(d):
   m=re.fullmatch(r'DefPathHash\(Fingerprint\((\d+), (\d+)\)\)',d['rawDefPathHash']);assert m
   stable=re.fullmatch(r'StableCrateId\((\d+)\)',d['crateStableId']);assert stable and m[1]==stable[1]
   return m[1],m[2]
  ca,pa=parts(a);cb,pb=parts(b);assert pa==pb
  proof={'method':'same-compiler-defpath-source-and-local-hash-contextual-crate-bridge','origin':a,'compiled':b,'source':sa,'originCrateComponent':ca,'compiledCrateComponent':cb,'exactLocalDefPathHash':pa}
 key=c.sha(c.enc(proof));definitions[key]=proof
 return key

def compare(a,b,definitions):
 assert type(a)is type(b),(a,b)
 if isinstance(a,dict):
  assert set(a)==set(b)
  for k in a:
   if k=='definition':definition(a[k],b[k],definitions)
   else:compare(a[k],b[k],definitions)
 elif isinstance(a,list):
  assert len(a)==len(b)
  for x,y in zip(a,b):compare(x,y,definitions)
 else:assert a==b,(a,b)

def graphs(records):
 out={r['identity']:r['graph']for r in records if r['kind']=='type-graph'}
 assert len(out)==sum(r['kind']=='type-graph'for r in records)and out
 return out

def reject_controls(example):
 controls=[]
 def rejection(name,a,b):
  try:compare(a,b,{})
  except (AssertionError,KeyError,ValueError):controls.append({'name':name,'rejected':True});return
  raise AssertionError(('mutation accepted',name))
 rejection('same-size primitive replacement',{'kind':'primitive','actual':'u32'},{'kind':'primitive','actual':'i32'})
 rejection('same-size reference mutability',{'kind':'Ref','region':"'{erased}",'mutability':'Mut','pointee':{'kind':'primitive','actual':'u32'}},{'kind':'Ref','region':"'{erased}",'mutability':'Not','pointee':{'kind':'primitive','actual':'u32'}})
 a=copy.deepcopy(example);b=copy.deepcopy(example)
 def first_def(x):
  if isinstance(x,dict):
   if 'definition'in x:return x['definition']
   for v in x.values():
    found=first_def(v)
    if found:return found
  if isinstance(x,list):
   for v in x:
    found=first_def(v)
    if found:return found
 d=first_def(b);assert d;d['path']+='::different_same_size_definition';rejection('changed actual definition',a,b)
 a={'kind':'Adt','definition':first_def(example),'args':[{'kind':'type','value':{'kind':'primitive','actual':'u32'}}]};b=copy.deepcopy(a);b['args'][0]['value']['actual']='i32';rejection('same-size generic argument',a,b)
 a={'kind':'FnPtr','binder':'[Region(BrAnon)]','inputs':[],'output':{'kind':'primitive','actual':'u32'}};b=copy.deepcopy(a);b['binder']='[]';rejection('changed higher-ranked binder',a,b)
 return controls
