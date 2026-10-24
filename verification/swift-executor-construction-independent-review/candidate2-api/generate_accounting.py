#!/usr/bin/env python3
"""Typed authored-object accounting proposal; every explicit call operand named.

A conservative sum counts every selected own-code local and explicit callsite
argument separately, including mutually exclusive paths. No physical stack,
register/liveness, standard-library implementation, or allocator claim follows.
"""
from pathlib import Path
import re,json,hashlib
out=Path(__file__).resolve().parent
mirpath=out/'target/debug/deps/mixer_vm.mir';mir=mirpath.read_text()
functions=[]
for m in re.finditer(r'^fn (.*?) \{\n(.*?)^\}',mir,re.M|re.S):
 functions.append({'header':m.group(1),'body':m.group(2),'line':mir.count('\n',0,m.start())+1})
closures={}
for f in functions:
 m=re.search(r'\{closure@([^}]+)\}',f['header'])
 if m:
  c={int(n):t for n,t in re.findall(r'_1\.(\d+): ([^\n]+?)\)\)',f['body'])}
  closures[m.group(1)]=[c[n]for n in sorted(c)]

def split(s):
 outparts=[];start=0;depth=0;quote=False;escape=False
 for i,ch in enumerate(s):
  if quote:
   if escape:escape=False
   elif ch=='\\':escape=True
   elif ch=='"':quote=False
   continue
  if ch=='"':quote=True
  elif ch in '<([{':depth+=1
  elif ch in '>)]}':depth-=1
  elif ch==',' and depth==0:outparts.append(s[start:i].strip());start=i+1
 if s[start:].strip():outparts.append(s[start:].strip())
 return outparts

def typ(t,spec='()'):
 t=t.replace("'_","'static").replace('std::sync::atomic::Atomic<bool>','std::sync::atomic::AtomicBool')
 def closure(m):
  types=[typ(x,spec)for x in closures[m.group(1)]]
  return '('+','.join(types)+(','if len(types)==1 else'')+')'
 t=re.sub(r'\{closure@([^}]+)\}',closure,t)
 t=re.sub(r'\bD\b','crate::experimental::metadata::SwiftDeclaration',t)
 for mod in ['experimental_swift_reactor','experimental_wasi','experimental','execute']:
  t=re.sub(r'(?<![\w:])'+mod+'::','crate::'+mod+'::',t)
 t=re.sub(r'(?<![\w:])control::','super::control::',t)
 for a,b in {'Segment':'crate::experimental::metadata::Segment','Infallible':'std::convert::Infallible','Duration':'std::time::Duration','TryReserveError':'std::collections::TryReserveError','WasiContext':'crate::experimental_wasi::WasiContext','SwiftCacheUsage':'super::cache::SwiftCacheUsage'}.items():
  t=re.sub(r'(?<![\w:])'+a+r'\b',b,t)
 t=re.sub(r'\bT\b',spec,t)
 t=re.sub(r"&(?!'static)(mut\s+)?",lambda m:"&'static "+('mut 'if m.group(1)else''),t)
 return t

def declaration(f):
 sig=f['header'];args=sig.split('(',1)[1].rsplit(') ->',1)[0]
 d={int(n):t for n,t in re.findall(r'let(?: mut)? _(\d+): ([^\n]+);',f['body'])}
 for a in split(args):
  m=re.match(r'_(\d+): (.*)',a);assert m,a;d[int(m.group(1))]=m.group(2)
 aliases={int(n):name for name,n in re.findall(r'debug (\w+) => _(\d+);',f['body'])}
 return d,aliases,len(split(args))

def construct_prelude(f):
 blocks={int(n):b for n,b in re.findall(r'^    bb(\d+)(?: \(cleanup\))?: \{\n(.*?)^    \}',f['body'],re.M|re.S)}
 visited=set();todo=[0];parts=[]
 while todo:
  n=todo.pop()
  if n in visited:continue
  visited.add(n);body=blocks[n]
  if re.search(r'Option::<\(.*RuntimeControl, .*AdoptedProof\)>::take\(',body):
   body=body.split('Option::<',1)[0].rsplit('\n',1)[0];parts.append((n,body));continue
  parts.append((n,body));todo.extend(int(x)for x in re.findall(r'\bbb(\d+)\b',body))
 return parts

def all_blocks(f):
 return [(int(n),b)for n,b in re.findall(r'^    bb(\d+)(?: \(cleanup\))?: \{\n(.*?)^    \}',f['body'],re.M|re.S)]

def callargs(line):
 m=re.match(r'\s*(_\d+) = (.*) -> \[.*\];$',line)
 if not m:return None
 rhs=m.group(2)
 if not rhs.endswith(')'):return None
 depth=0;quote=False;escape=False;opening=None
 # Find the outer call's final matching parentheses; () may appear in callee generics.
 for i in range(len(rhs)-1,-1,-1):
  c=rhs[i]
  if c==')':depth+=1
  elif c=='(':
   depth-=1
   if depth==0:opening=i;break
 if opening is None:return None
 return m.group(1),rhs[:opening],split(rhs[opening+1:-1])

preflight_names=['construction_bytes','checked','construction_failure','layout_failure','pairing','micros']
control_pre=['check_adopted_owner','reservation_owner_matches','check_reservation_owner','enlarge_construction','enlarge_construction_with_wasi','check_with_wasi','usage','fail','preflight_bytes','commit_bytes','category_limit','category','category_mut','new','limit']
cache_pre=['check_owner','check_header','error','observation','usage']
wasi_pre=['checked_usage','usage']
selected=[]

def method(f):return f['header'].split('(',1)[0].rsplit('::',1)[-1]
def own_execution(f):return 'src/experimental_swift_reactor/execution.rs:'in f['header']
def add(scope,role,f,spec='()',prelude=False):selected.append({'scope':scope,'role':role,'function':f,'spec':spec,'prelude':prelude})
for f in functions:
 h=f['header'];m=method(f)
 if '::{closure#'in h:continue
 if h.split('(',1)[0] in ['construction_bytes','checked','construction_failure','experimental_swift_reactor::execution::layout_failure']:
  add('preflight','free_'+m,f);continue
 if h.split('(',1)[0] in ['work','arena_bytes','execution_header_bytes','drop_construction_return_storage']:
  add('active','free_'+m,f,'(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)');continue
 if h.split('(',1)[0]=='drop_cleanup_return_storage':
  add('active','construction_inner_return_storage',f,'(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)');continue
 if h.split('(',1)[0]=='cleanup_cursor':add('cleanup','cleanup_cursor',f);continue
 if own_execution(f):
  if m=='fmt':continue # Debug formatting is not called by bounded constructor/cleanup paths.
  if m in ['terms','phase_bytes','named_bytes','arena_bytes','execution_header_bytes','with_cache_operation']:continue
  if m=='construct' and '_1: &mut Option<'in h:
   add('preflight','constructor_before_take',f,prelude=True);add('active','constructor_all',f);continue
  if m=='prepare':add('preflight','state_prepare',f);continue
  if h.split('(',1)[0]in preflight_names:add('preflight',m,f);continue
  if m=='reserve':
   for role,spec in [('values','Value'),('controls','Control'),('frames','SwiftFrame'),('memory','u8'),('table','Option<u32>')]:add('active','reserve_'+role,f,spec)
   continue
  if m=='cleanup_owned':add('cleanup','composed_cleanup',f);continue
  if m=='complete' and '_1: ConstructionCleanupTail'in h:
   add('final','construction_tail_complete',f,'(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)');continue
  if m=='complete' and '_1: ExecutionCleanupTail'in h:continue # exact accepted unchanged final boundary
  if m=='complete':add('active','state_phase_complete',f,'Option<Result<SwiftExecutionState,SwiftRunFailure>>');continue
  if m=='drop_construction_return_storage':add('active','construction_return_storage',f,'(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)');continue
  if m=='drop_cleanup_return_storage':continue # accepted ordinary tail helper; caller storage unchanged
  if m=='cleanup_cursor':add('cleanup',m,f);continue
  add('active',m+'_'+str(f['line']),f)
  if m=='drop_arenas':add('cleanup','state_drop_arenas',f)
 elif (h.startswith('control::<impl')and m in control_pre)or('src/experimental_swift_reactor/cache.rs:'in h and m in cache_pre and ('_1: &SwiftFunctionCache'in h or '_1: &mut CacheControl'in h or '_1: &CacheControl'in h))or('src/experimental_wasi/accounted.rs:'in h and m in wasi_pre)or('src/experimental_wasi/mod.rs:'in h and m=='usage')or(h.split('(',1)[0]=='micros')or('src/execute.rs:'in h and m=='is_cancelled')or(h.split('(',1)[0]=='pairing'):
  add('preflight','leaf_'+m+'_'+str(f['line']),f)
 elif h.startswith('control::<impl')and m in ['admit_with_wasi','exact_capacity_with_wasi','work_with_wasi','add_live_with_wasi','remove_live_with_wasi','live_parts','live_mut','refund_with_wasi','cleanup_fault_with_wasi','drop_reserved_with_wasi','end_construction_phase_with_wasi']:
  if m=='drop_reserved_with_wasi':
   for role,spec in [('values','Vec<Value>'),('controls','Vec<Control>'),('frames','Vec<SwiftFrame>'),('memory','Vec<u8>'),('table','Vec<Option<u32>>'),('state','SwiftExecutionState')]:
    add('active','drop_'+role,f,spec)
    if role!='state':add('cleanup','drop_'+role,f,spec)
   add('final','drop_unit',f,'()')
  elif m=='end_construction_phase_with_wasi':
   add('final','end_construction_unit',f,'()')
   add('active','end_state_phase',f,'Option<Result<SwiftExecutionState,SwiftRunFailure>>')
   add('active','end_composed_phase',f,'(PartialInstance,Result<(),SwiftRunFailure>)')
  else:
   add('active','leaf_'+m,f)
   if m in ['remove_live_with_wasi','live_parts','live_mut','refund_with_wasi','cleanup_fault_with_wasi']:add('cleanup','leaf_'+m,f)
for f in functions:
 if f['header'].startswith('ConstructionFailure::Rejected('):
  add('preflight','rejected_enum_constructor',f)
  break
# Existing retained descriptor helpers are a closed, private transitive boundary.
for f in functions:
 h=f['header'];m=method(f)
 if ('src/experimental/swift.rs:'in h and m in ['execution_signature','execution_global_count','execution_global','execution_global_initializer_offset','execution_data_count','execution_data','execution_element_count','execution_element','execution_segment','execution_memory','execution_table']):
  add('descriptor','getter_'+m,f)
 elif 'src/experimental/metadata.rs:'in h and m in ['signature','params','slice']:
  add('descriptor','metadata_'+m,f)
 elif 'src/experimental/account.rs:'in h and 'Buffer' in h and m in ['len','get','as_slice']:
  for role,t in [('global','crate::experimental::metadata::Global'),('segment','crate::experimental::metadata::Segment'),('signature','crate::experimental::metadata::Signature'),('function','crate::experimental::metadata::Function'),('import','crate::experimental::metadata::Import'),('type','Type')]:
   if (m,role) not in [('len','global'),('get','global'),('len','segment'),('get','segment'),('get','signature'),('len','import'),('get','import'),('get','function'),('as_slice','type')]:continue
   add('descriptor','buffer_'+role+'_'+m,f,t)
 elif ('src/experimental_swift_reactor/cache.rs:'in h or 'src/experimental_swift_reactor/control.rs:'in h)and m=='proof':add('active','proof_'+str(f['line']),f)
 elif h.startswith('<impl at src/lib.rs:')and m=='ty':add('active','value_ty',f)
# Callback bodies have their own argument/local/return positions as well as caller closure objects.
for parent in list(selected):
 base=parent['function']['header'].split('(',1)[0]
 for f in functions:
  if f['header'].startswith(base+'::{closure#'):
   add(parent['scope'],parent['role']+'_callback_'+f['header'].split('::{closure#')[1].split('}')[0],f,parent['spec'])

unresolved=[];excluded=[];groups=[]
for group in selected:
 f=group['function'];d,aliases,argc=declaration(f);blocks=construct_prelude(f)if group['prelude']else all_blocks(f)
 used={int(n)for _,b in blocks for n in re.findall(r'\b_(\d+)\b',b)}|set(range(argc+1))
 fields=[];zeros=[]
 for n,t in sorted(d.items()):
  if group['prelude']and n not in used:continue
  if t=='!':excluded.append({'function':f['header'],'local':'_'+str(n),'reason':'Uninhabited never place cannot contain a runtime object'});continue
  fields.append({'field':'object_'+str(n),'type':typ(t,group['spec']),'source_type':t,'role':'whole authored '+('return'if n==0 else'parameter'if n<=argc else'local/receiver/return-holder/closure/control-flow object'),'binding':aliases.get(n),'mir_local':'_'+str(n)})
 for bb,body in blocks:
  for index,line in enumerate(body.splitlines()):
   call=callargs(line)
   if not call:continue
   returned,callee,args=call
   for arg,operand in enumerate(args):
    mt=re.fullmatch(r'(?:copy|move) _(\d+)',operand)
    ty=None
    if mt:ty=d[int(mt.group(1))]
    elif operand.startswith('const ZeroSized: '):
     zero=operand[len('const ZeroSized: '):]
     zeros.append({'callee':callee,'block':bb,'argument':arg,'source_type':zero,'operand':operand,'count':1,'size_evidence':'Compiler explicit ZeroSized function/closure item; separate named zero-sized term, never borrowed bytes'});continue
    elif operand in ['AccountedWasi::usage','ConstructionFailure::Rejected']:
     zeros.append({'callee':callee,'block':bb,'argument':arg,'source_type':'function item '+operand,'operand':operand,'count':1,'size_evidence':'size_of_val/align_of_val direct function item probe'});continue
    elif operand=='const Option::<Infallible>::None':ty='Option<std::convert::Infallible>'
    elif re.fullmatch(r'const core::num::<impl (u64|usize)>::MAX',operand):ty=re.fullmatch(r'const core::num::<impl (u64|usize)>::MAX',operand).group(1)
    elif re.fullmatch(r'const \(\)',operand):ty='()'
    elif re.match(r'const "',operand):ty='&str'
    elif re.fullmatch(r'const (true|false)',operand):ty='bool'
    elif re.fullmatch(r'const -?\d+_(?:u|i)(?:8|16|32|64|128|size)',operand):ty=operand.rsplit('_',1)[1]
    elif re.match(r'const [\w:]+::\w+$',operand):ty=operand[len('const '):].rsplit('::',1)[0]
    elif operand.startswith('copy ')or operand.startswith('move '):
     projection=re.findall(r': (.+?)\)',operand)
     if projection:ty=projection[-1]
    if ty is None:unresolved.append({'function':f['header'],'block':bb,'callee':callee,'argument':arg,'operand':operand});continue
    if ty=='!':continue
    fields.append({'field':f'call_{bb}_{index}_argument_{arg}','type':typ(ty,group['spec']),'source_type':ty,'role':'whole explicit authored callsite argument/receiver transfer','callee':callee,'block':bb,'argument':arg,'operand':operand,'callee_domain':'authored helper'if any(callee.split('::<',1)[0]in x['header']for x in functions)else'standard library/intrinsic callsite only; library internals excluded'})
 g={k:v for k,v in group.items()if k!='function'};g.update({'function':f['header'],'mir_line':f['line'],'fields':fields,'zero_terms':zeros});groups.append(g)

manifest={'schema':'mixer-swift-construction-exact-positive-accounting-proposal-v2','status':'unresolved roles block freeze'if unresolved else'complete authored inventory proposed for measurement and independent source/lifetime review','input_mir_sha256':hashlib.sha256(mir.encode()).hexdigest(),'scope':'Positive whole typed authored object/callsite inventory. One field per source/local/parameter/return/explicit call-operand position; repeated loop iterations reuse the same position, no recursion in bounded constructor helpers. All selected branches are summed without liveness reuse. Standard-library implementation internals and physical stack/register placement are excluded. Compiler never places have no inhabitant and are recorded excluded; every other branch/residual shape is positive.','groups':groups,'unresolved':unresolved,'excluded':excluded,'pending':['Post-restore successful constructor caller Option/Result transfer shape inventory','Actual unit/prod Debug/Release size/align/offset measurement','Source and final-boundary review of new completion helper','Final product candidate after supplement incorporation']}
(out/'positive-accounting-map.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'groups':len(groups),'fields':sum(len(g['fields'])for g in groups),'zero_terms':sum(len(g['zero_terms'])for g in groups),'unresolved':len(unresolved)}))
for x in unresolved[:15]:print(json.dumps(x))
# Compress identical concrete shapes into arrays, retaining every binding index.
classes={scope:{}for scope in ['preflight','active','cleanup','final','descriptor']}
for gi,g in enumerate(groups):
 for field in g['fields']:
  bucket=classes[g['scope']].setdefault(field['type'],[])
  bucket.append({'group':gi,'field':field['field'],'function':g['function'],'role':field['role'],'block':field.get('block'),'argument':field.get('argument'),'operand':field.get('operand'),'binding':field.get('binding')})
# Explicit whole caller-storage positions derived from the frozen private API and
# construct_failed's caller boundary; the success source Result also appears in
# the constructor frame, and these account its returned caller holders after restore.
transfer_types=[
 ('constructor wrapper caller return','Result<SwiftReactorInstance,ConstructionFailure>'),
 ('caller retained possible-owner slot','Option<Result<SwiftReactorInstance,ConstructionFailure>>'),
 ('caller take returned Option','Option<Result<SwiftReactorInstance,ConstructionFailure>>'),
 ('caller extracted match Result','Result<SwiftReactorInstance,ConstructionFailure>'),
 ('caller extracted ConstructionFailure','ConstructionFailure'),
 ('caller extracted construction completion tail','ConstructionCleanupTail'),
 ('completion supplied original pair plus returned slot','(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)')]
# Pre-take rejected return has only foundation; success persists under the actual
# execution header; post-take error remains under the outer Construction ticket.
for scope in ['preflight','active','cleanup']:
 for role,t in transfer_types:
  classes[scope].setdefault(t,[]).append({'group':'caller-boundary','field':role,'function':'private constructor caller completion contract / construct_owned / construct_failed','role':role,'block':None,'argument':None,'operand':None,'binding':role})
descriptor_code=['// Private retained-descriptor typed accounting proposal.\n']
code=['// Independent positive named authored-object/callsite accounting.\n// Class array indices map one-to-one to positive-accounting-map.json bindings.\n// Every old inventory remains charged. No phase padding or diagnostic slot is reused.\n']
classrows=[]
for scope,buckets in classes.items():
 target=descriptor_code if scope=='descriptor'else code
 name='ConstructionPositive'+scope.title()
 target.append('#[allow(dead_code)]\npub(crate) struct '+name+'{\n')
 for ci,(ty,bindings)in enumerate(buckets.items()):
  field='class_'+str(ci);target.append(f' {field}: [{ty};{len(bindings)}],\n')
  classrows.append({'scope':scope,'struct':name,'field':field,'type':ty,'count':len(bindings),'bindings':bindings})
 target.append('}\n')
 target.append(f'pub(crate)const CONSTRUCTION_POSITIVE_{scope.upper()}_BYTES:usize=std::mem::size_of::<{name}>();\n')
descriptor_code.append('pub(crate)fn independent_descriptor_accounting_probe(){use std::mem::{size_of,align_of,offset_of};\n')
code.append('pub(crate)fn independent_positive_accounting_probe(){use std::mem::{size_of,align_of,offset_of,size_of_val,align_of_val};\n')
for row in classrows:
 target=descriptor_code if row['scope']=='descriptor'else code
 target.append(f'println!("positiveclass|{row["scope"]}|{row["field"]}|{row["count"]}|{{}}|{{}}|{{}}",offset_of!({row["struct"]},{row["field"]}),size_of::<{row["type"]}>(),align_of::<{row["type"]}>());\n')
for scope in classes:
 name='ConstructionPositive'+scope.title();target=descriptor_code if scope=='descriptor'else code;target.append(f'println!("positivetotal|{scope}|{{}}|{{}}",size_of::<{name}>(),align_of::<{name}>());\n')
for operand in ['AccountedWasi::usage','ConstructionFailure::Rejected']:
 code.append(f'println!("positivefunctionitem|{operand}|{{}}|{{}}",size_of_val(&{operand}),align_of_val(&{operand}));\n')
code.append('crate::experimental::swift::independent_descriptor_accounting_probe();}\n')
descriptor_code.append('}\n')
(out/'descriptor-accounting.rs').write_text(''.join(descriptor_code))
(out/'positive-accounting.rs').write_text(''.join(code))
manifest['classes']=classrows;manifest['source_sha256']=hashlib.sha256((''.join(code)).encode()).hexdigest()
manifest['pending']=[x for x in manifest['pending']if not x.startswith('Post-restore')]
(out/'positive-accounting-map.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'classes':len(classrows),'source_sha256':manifest['source_sha256']}))

# Deterministic final assembly of the explicitly audited cfg(test) call boundary.
hook_path=out/'test-hook-inventory.rs'
if hook_path.exists():
 source=(out/'positive-accounting.rs').read_text()
 source=source.replace('pub(crate)fn independent_positive_accounting_probe(){',hook_path.read_text()+'\n'+'pub(crate)fn independent_positive_accounting_probe(){')
 source=source.replace('crate::experimental::swift::independent_descriptor_accounting_probe();}', 'println!("positivetotal|test_hook|{}|{}",CONSTRUCTION_POSITIVE_TEST_HOOK_BYTES,8);\ncrate::experimental::swift::independent_descriptor_accounting_probe();}')
 (out/'positive-accounting.rs').write_text(source)
 (out/'positive-accounting-product.rs').write_text(source.split('pub(crate)fn independent_positive_accounting_probe()',1)[0])
 descriptor=(out/'descriptor-accounting.rs').read_text()
 (out/'descriptor-accounting-product.rs').write_text(descriptor.split('pub(crate)fn independent_descriptor_accounting_probe()',1)[0].replace('pub(crate) struct ConstructionPositiveDescriptor','struct ConstructionPositiveDescriptor'))
 manifest['source_sha256']=hashlib.sha256(source.encode()).hexdigest()
 manifest['descriptor_source_sha256']=hashlib.sha256(descriptor.encode()).hexdigest()
 manifest['product_source_sha256']=hashlib.sha256((out/'positive-accounting-product.rs').read_bytes()).hexdigest()
 manifest['descriptor_product_sha256']=hashlib.sha256((out/'descriptor-accounting-product.rs').read_bytes()).hexdigest()
 (out/'positive-accounting-map.json').write_text(json.dumps(manifest,indent=2)+'\n')
