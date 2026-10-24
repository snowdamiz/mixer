"""Full-header MIR inventory. Compiler bodies are partitioned by explicit identity.

Canonical locals include return _0 and typed arguments. Every canonical role,
source alias, literal and closure transfer adds four disjoint positive positions.
Fixture builders/assertions have a separate full-header inventory and no credit.
"""
import collect as c
import gzip,re,json
FREE=['check','trap','pop_checked','typed_i32','frame_guard','fetch','prefix','call_selected','signature_mismatch','indirect','local_slot','local_get','local_set','global_get','global_set','select_guard','publication','result_guard','run','complete']
RUNTIME_HOOKS=['checkpoint','PC_OVERFLOW','CHECK_COUNT','CANCEL_AT']
PREFIX='experimental_swift_reactor::execution::frame_operations::call_dispatch::'
def split_top(s):
 out=[];at=0;depth=0
 for i,ch in enumerate(s):
  if ch in '<([{':depth+=1
  elif ch in '>)]}':depth-=1
  elif ch==',' and depth==0:out.append(s[at:i].strip());at=i+1
 return [x for x in out+[s[at:].strip()] if x]
def blocks(text):
 line=1;previous=0
 for m in re.finditer(r'^(fn|const|static) ([^\n]+)',text,re.M):
  line+=text.count('\n',previous,m.start());previous=m.start()
  header=m[0];body=m[0] if m[0].endswith(';') else text[m.start():text.find('\n}',m.start())+2]
  if m[1]=='fn':
   pos=header.index('(');name=header[3:pos];end=pos+1;depth=1
   while depth:depth+=(header[end]=='(')-(header[end]==')');end+=1
   args=header[pos+1:end-1]
  else:name=header.split(' ',1)[1].split(': ',1)[0];args=''
  yield {'name':name,'kind':m[1],'header':header,'line':line,'args':args,'body':body}
def root_name(name):return name.split('::promoted[')[0].split('::{closure#')[0]
def selection(b):
 name=b['name'];stem=root_name(name);qualified=stem.removeprefix(PREFIX)
 if qualified in FREE:return 'product'
 if name.startswith(PREFIX+'tests::'):
  tail=name.removeprefix(PREFIX+'tests::')
  if root_name(tail).split('::')[0] in RUNTIME_HOOKS:return 'unit-runtime-hook'
  return 'fixture-only'
 if root_name(name).split('::')[0] in ['CHECK_COUNT','CANCEL_AT']:return 'unit-runtime-hook'
 if '::frame_operations::'in name and '::tests::'not in name and re.search(r'::enter_inner(?:::|$)',name):return 'changed-product'
 if 'host_runtime_import::'in name and re.search(r'::host_operation_inner(?:::|$)',name):return 'changed-product'
 return None
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
  ty=body[at:end]
  assert int(m[1]) not in fields or fields[int(m[1])]==ty,(fields,ty)
  fields[int(m[1])]=ty
 return fields
def normalize(ty,captures):
 ty=re.sub(r'\{closure@[^}]+\}',lambda m:captures[m[0]],ty)
 ty=re.sub(r"'[A-Za-z_][A-Za-z_0-9]*","'static",ty)
 for name,target in [('experimental_swift_reactor::','crate::experimental_swift_reactor::'),('experimental_wasi::','crate::experimental_wasi::'),('experimental::','crate::experimental::'),('control::','crate::experimental_swift_reactor::control::'),('accounted::','crate::experimental_wasi::accounted::')]:ty=re.sub(r'(?<![:\w])'+name,target,ty)
 ty=ty.replace('crate::experimental_wasi::descriptor::WasiFunction','crate::experimental_wasi::WasiFunction')
 for name in ['SwiftGrowthContext','SwiftGrowthStorage','GrowthCompletion']:
  ty=re.sub(r'(?<![:\w])'+name+r'\b','crate::experimental_swift_reactor::execution::frame_operations::memory_growth_operations::'+name,ty)
 ty=re.sub(r'(?<![:\w])Cell<','std::cell::Cell<',ty);ty=re.sub(r'(?<![:\w])LocalKey<','std::thread::LocalKey<',ty)
 ty=re.sub(r'(?<![:\w])execute::Cancellation','crate::Cancellation',ty)
 ty=re.sub(r"&(?!(?:'|\s*'))","&'static ",ty)
 return ty
def canonical(name):
 raw=gzip.decompress((c.HERE/('preaccounting-'+name+'.mir.gz')).read_bytes()).decode();allb=list(blocks(raw));chosen=[b for b in allb if selection(b) not in [None,'fixture-only']]
 for required in FREE:assert any(root_name(b['name']).removeprefix(PREFIX)==required and b['kind']=='fn' for b in chosen),(name,required)
 # Check that every declared free body and every descendant closure/promoted body
 # is selected by its full identity, including bare MIR names.
 observed=[b for b in allb if 'src/experimental_swift_reactor/call_dispatch.rs:' in b['body'] and not b['name'].startswith(('CallsActivePositions','CallsPermanentPositions'))]
 missing=[b['header'] for b in observed if selection(b) is None];assert not missing,(name,missing)
 captures={};rows=[]
 for b in chosen:
  fields=capture_fields(b['body']) if '{closure@' in b['args'] else {}
  if fields:
   assert set(fields)==set(range(len(fields))),(name,b['header'],fields)
  for site in re.findall(r'\{closure@[^}]+\}',b['args']):captures[site]='('+', '.join(fields[i] for i in range(len(fields)))+(','if len(fields)==1 else '')+')'
 for ordinal,b in enumerate(chosen):
  decl=dict(re.findall(r'let (?:mut )?(_\d+): ([^\n;]+);',b['body']))
  for arg in split_top(b['args']):ident,ty=arg.split(': ',1);decl[ident]=ty
  aliases={}
  for source,ident in re.findall(r'debug (\w+) => (_\d+);',b['body']):aliases.setdefault(ident,[]).append(source)
  def add(binding,ty,kind,stem,source=None):
   for position in ['source','argument','returned','caller']:
    rows.append({'field':stem+'_'+position,'type':normalize(ty,captures),'mirType':ty,'binding':binding,'kind':kind,'position':position,'config':name,'function':b['name'],'header':b['header'],'line':b['line'],'source':source,'unitOnly':name.endswith('-unit')})
  for ident,ty in decl.items():
   add(ident,ty,'canonical',f'm_{name.replace("-","_")}_{ordinal}_{ident[1:]}')
   for i,alias in enumerate(aliases.get(ident,[])):add(alias,ty,'authored-alias',f'a_{name.replace("-","_")}_{ordinal}_{ident[1:]}_{i}',alias)
  # Captured source aliases are distinct from the closure tuple environment.
  for i,(field,ty) in enumerate((capture_fields(b['body']) if '{closure@' in b['args'] else {}).items()):add('capture_'+str(field),ty,'captured-alias',f'c_{name.replace("-","_")}_{ordinal}_{i}')
  for i,literal in enumerate(re.findall(r'const ("(?:[^"\\]|\\.)*"|true|false|\d+_(?:u|i)(?:size|8|16|32|64|128))',b['body'])):
   ty="&'static str" if literal.startswith('"') else 'bool' if literal in ['true','false'] else literal.rsplit('_',1)[1]
   add('literal_'+str(i),ty,'literal',f'l_{name.replace("-","_")}_{ordinal}_{i}',literal)
 headers=[{k:v for k,v in b.items() if k!='body'}|{'partition':selection(b),'bodySHA256':c.sha(b['body'].encode())}for b in allb if selection(b)]
 return rows,headers,captures

def main():
 rows=[];headers=[];captures={}
 for features in ['swift','all']:
  for profile in ['debug','release']:
   for unit in ['production','unit']:
    name=features+'-'+profile+'-'+unit;r,h,cap=canonical(name);rows+=r;headers += [dict(config=name,**b) for b in h];captures[name]=cap
 permanent=[]
 for name,ty in {'storage':"FrameOperationStorage<'static>",'growth':'SwiftGrowthStorage','context':"SwiftGrowthContext<'static>",'completion':"GrowthCompletion<'static>",'preparation':"Option<Result<(FrameOperationPhase<'static>,SwiftGrowthContext<'static>),SwiftRunFailure>>",'outcome':'Option<Result<FrameReturn,SwiftRunFailure>>','final_failure':'Option<SwiftRunFailure>','final_value':'Option<Value>','final_usage':'Option<SwiftRunUsage>'}.items():
  for position in ['source','argument','returned','caller']:permanent.append({'field':'retained_'+name+'_'+position,'type':normalize(ty,{}),'unitOnly':False,'kind':'retained','position':position,'config':'source'})
 code=[]
 for cls,fields in [('CallsActivePositions',rows),('CallsPermanentPositions',permanent)]:
  code.append('pub(super) struct '+cls+' {')
  for r in fields:
   if r['unitOnly']:code.append('    #[cfg(test)]')
   code.append('    '+r['field']+': '+r['type']+',')
  code.append('}')
 code.extend(['pub(super) const ACTIVE_BYTES:usize=size_of::<CallsActivePositions>();','pub(super) const PERMANENT_BYTES:usize=size_of::<CallsPermanentPositions>();'])
 c.save(c.HERE/'positive-positions.rs',('\n'.join(code)+'\n').encode());c.save(c.HERE/'inventory-schema.json',rows+permanent);c.save(c.HERE/'full-header-partition.json',headers);c.save(c.HERE/'closure-captures.json',captures)
 print(len(rows)+len(permanent),'positive named positions;',len(headers),'full-header partition records')
if __name__=='__main__':main()
