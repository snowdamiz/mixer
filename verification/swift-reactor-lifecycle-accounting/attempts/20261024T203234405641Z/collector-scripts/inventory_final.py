"""Full compiler bodies, exact types and four disjoint roles per fresh position.

Discovery proposes finite exceptions only. Numeric accounting is never installed
until root binds the actual finite positions and their complete compiler layouts.
"""
from pathlib import Path
import re,json,gzip,collections
import collect as c
ROLES=['source','argument','returned','caller']
PREFIX='crate::experimental_swift_reactor::execution::frame_operations::memory_growth_operations::'

def split_top(s):
 out=[];at=0;depth=0
 for i,ch in enumerate(s):
  if ch in '<([{':depth+=1
  elif ch in '>)]}':depth-=1
  elif ch==',' and depth==0:out.append(s[at:i].strip());at=i+1
 return [x for x in out+[s[at:].strip()] if x]
def capture_fields(body):
 fields={}
 for m in re.finditer(r'(?:_1|\(\*_1\))\.(\d+): ',body):
  at=m.end();end=at;depth=0
  while end<len(body):
   ch=body[end]
   if ch==')' and depth==0:break
   if ch in '<([':depth+=1
   elif ch in '>)]':depth-=1
   end+=1
  ty=body[at:end];assert int(m[1]) not in fields or fields[int(m[1])]==ty
  fields[int(m[1])]=ty
 return fields
def raw_decls(body):
 out=dict(re.findall(r'let (?:mut )?(_\d+): ([^\n]+);',body));h=body.splitlines()[0]
 if h.startswith('fn '):
  pos=h.index('(');end=pos+1;depth=1
  while depth:depth+=(h[end]=='(')-(h[end]==')');end+=1
  for arg in split_top(h[pos+1:end-1]):
   ident,ty=arg.split(': ',1);assert ident not in out or out[ident]==ty;out[ident]=ty
 return {int(k[1:]):ty for k,ty in out.items()}
def normal(ty):
 assert '{closure@' not in ty and ty!='!'
 bound=set(re.findall(r"'[A-Za-z_][A-Za-z_0-9]*",' '.join(re.findall(r'for<([^>]+)>',ty))))
 ty=ty.replace("'{erased}","'static")
 ty=re.sub(r"'[A-Za-z_][A-Za-z_0-9]*",lambda m:m[0]if m[0]in bound else "'static",ty)
 for name,target in [('experimental_swift_reactor::','crate::experimental_swift_reactor::'),('experimental_wasi::','crate::experimental_wasi::'),('experimental::','crate::experimental::'),('control::','crate::experimental_swift_reactor::control::'),('accounted::','crate::experimental_wasi::accounted::')]:ty=re.sub(r'(?<![:\w])'+name,target,ty)
 ty=ty.replace('crate::experimental_wasi::descriptor::WasiFunction','crate::experimental_wasi::WasiFunction').replace('std::sync::atomic::Atomic<bool>','std::sync::atomic::AtomicBool')
 for name in ['SwiftGrowthContext','SwiftGrowthStorage','GrowthCompletion','CompletionGoal','PreparationGoal']:ty=re.sub(r'(?<![:\w])'+name+r'\b',PREFIX+name,ty)
 for name in ['Request','Rejection','Reply','Completion','Admission']:ty=re.sub(r'(?<![:\w])'+name+r'\b',PREFIX+'lifecycle::'+name,ty)
 ty=re.sub(r'(?<![:\w])Cell<','std::cell::Cell<',ty);ty=re.sub(r'(?<![:\w])LocalKey<','std::thread::LocalKey<',ty);ty=re.sub(r'(?<![:\w])execute::Cancellation','crate::Cancellation',ty)
 return re.sub(r"&(?!(?:'|\s*'))","&'static ",ty)
def phase(path):
 if '::execute_phase' in path or '::tests::runtime_' in path:return 'active'
 return 'permanent'
def method(ty,layout):
 if ty=='!':return 'exact-inferred-never'
 if 'Closure(' in layout['identity'] or '{closure@' in ty:return 'finite-proposed-actual-closure'
 if any(x in ty for x in ['::local_impl::','std::sys::','::niche_types::','::fmt::rt::','alloc::sync::ArcInner','alloc::raw_vec::','std::alloc::Global','::private::']):return 'finite-proposed-private-std'
 return 'exact-typed'
def contexts():
 for features in ['swift','all']:
  for profile in ['debug','release']:
   for mode in ['production','unit']:yield f'{features}-{profile}-{mode}'
def main():
 rows=[];headers=[];fnitems=[];partitions=[];queries={};bodytypes=[]
 for cfg in contexts():
  q=json.loads((c.HERE/f'exact-query-{cfg}.json').read_text());assert q['exitCode']==0;queries[cfg]=q
  raw=gzip.decompress((c.HERE/q['attempt']/'exact-layouts.jsonl.gz').read_bytes());assert c.sha(raw)==q['sha256']
  records=[json.loads(line)for line in raw.decode().splitlines()];bodies={};locals={};constants={}
  for r in records:
   key=(r.get('path'),r.get('promoted'))
   if r['kind']=='body':assert key not in bodies;bodies[key]=r
   elif r['kind']=='local':locals.setdefault(key,{})[r['local']]=r
   elif r['kind']=='constant-operand':constants.setdefault(key,[]).append(r)
   elif r['kind']=='FnDef':fnitems.append(dict(config=cfg,querySHA256=q['sha256'],**r))
   elif r['kind']=='partition-body':partitions.append(dict(config=cfg,querySHA256=q['sha256'],**r))
  named={}
  for key,body in bodies.items():
   for i,ty in raw_decls(body['mir']).items():named.setdefault(locals[key][i]['layout']['identity'],ty)
  for key,b in sorted(bodies.items(),key=lambda x:(x[0][0],-1 if x[0][1]is None else x[0][1])):
   decl=raw_decls(b['mir']);assert set(decl)==set(locals[key]),(cfg,key)
   tag=cfg.replace('-','_')+'_'+c.sha(c.enc(key))[:12];bodysha=c.sha(b['mir'].encode())
   headers.append(dict(config=cfg,path=b['path'],promoted=b['promoted'],bodyDefPathHash=b['defPathHash'],bodySHA256=bodysha,header=b['mir'].splitlines()[0],locals=sorted(decl),constantOperands=len(constants.get(key,[])),ownerClass=phase(b['path']),querySHA256=q['sha256']))
   def add(stem,binding,ty,kind,layout,local=None,capture=None,source=None):
    for role in ROLES:
     row=dict(field=stem+'_'+role,config=cfg,unitOnly=cfg.endswith('-unit'),body=b['path'],promoted=b['promoted'],bodyDefPathHash=b['defPathHash'],bodySHA256=bodysha,binding=binding,kind=kind,position=role,mirType=ty,method=method(ty,layout),ownerClass=phase(b['path']),actualIdentity=layout['identity'],actualType=layout['type'],layout=layout,querySHA256=q['sha256'])
     if local is not None:row.update(local=local,sourceInfo=locals[key][local]['sourceInfo'])
     if capture is not None:row['capture']=capture
     if source is not None:row['source']=source
     rows.append(row)
   for i,ty in sorted(decl.items()):add('m_'+tag+'_'+str(i),'_'+str(i),ty,'canonical',locals[key][i]['layout'],local=i)
   for n,(alias,local)in enumerate(re.findall(r'debug (\w+) => (_\d+);',b['mir'])):
    i=int(local[1:]);add('a_'+tag+'_'+str(n),alias,decl[i],'authored-alias',locals[key][i]['layout'],local=i,source=alias)
   captures=capture_fields(b['mir'])if 1 in decl and '{closure@'in decl[1]else{}
   if captures:
    cl=locals[key][1]['captureLayout'];assert cl is not None and len(cl['fields'])==len(captures)
    for i,ty in captures.items():
     field=cl['fields'][i];layout=dict(type=field['type'],identity=field['identity'],bytes=field['bytes'],alignment=field['alignment'],fields=[],variants=[],captureFieldOf=cl['identity'],captureOffset=field['offset'])
     add('c_'+tag+'_'+str(i),'capture_'+str(i),ty,'captured-alias',layout,local=1,capture=i)
   for i,operand in enumerate(constants.get(key,[])):
    ty=operand['layout']['type']
    if ty.startswith('Binder '):assert operand['layout']['identity']in named;ty=named[operand['layout']['identity']]
    add('o_'+tag+'_'+str(i),operand['location']+':'+str(i),ty.replace("'{erased}","'static"),'constant-operand',operand['layout'],source=operand['constant'])
 # Whole returned/retained/caller wrappers are additional permanent positions;
 # none borrows credit from a compiler local or the historical V7 rows.
 retained={'completion':"Completion<'static>",'outcome':'Result<Reply,SwiftRunFailure>','reply':'Reply','scalar':'i32','request':'Request','rejection':'Rejection','failure':'Option<SwiftRunFailure>','usage':'Option<SwiftRunUsage>','cleanup':"GrowthCompletion<'static>",'preparation':"Option<Result<(FrameOperationPhase<'static>,SwiftGrowthContext<'static>),SwiftRunFailure>>",'fixed_storage':"FrameOperationStorage<'static>"}
 for binding,ty in retained.items():
  for role in ROLES:rows.append(dict(field='retained_'+binding+'_'+role,config='source',unitOnly=False,body='source-retained-lifecycle-transfer',binding=binding,kind='whole-carrier',position=role,mirType=ty,method='exact-typed',ownerClass='permanent',semanticLifetime='Caller/retained return and final consuming cleanup storage; permanent header remains admitted.'))
 assert len({r['field']for r in rows})==len(rows)
 finite=[r for r in rows if r['method'].startswith('finite-proposed')]
 c.save(c.HERE/'inventory-final.json',rows);c.save(c.HERE/'finite-proposal-final.json',finite);c.save(c.HERE/'compiler-headers-final.json',headers);c.save(c.HERE/'compiler-function-items-final.json',fnitems);c.save(c.HERE/'compiler-partitions-final.json.gz',gzip.compress(c.enc(partitions),mtime=0));c.save(c.HERE/'inventory-summary-final.json',dict(rows=len(rows),canonicalPositions=sum(r['kind']=='canonical'for r in rows),bodies=len(headers),methods=dict(collections.Counter(r['method']for r in rows)),classes=dict(collections.Counter(r['ownerClass']for r in rows)),finitePositions=len(finite),queries=queries,accountingAccepted=False))
 print(json.dumps(dict(rows=len(rows),bodies=len(headers),methods=dict(collections.Counter(r['method']for r in rows)),classes=dict(collections.Counter(r['ownerClass']for r in rows))),indent=2))
if __name__=='__main__':main()
