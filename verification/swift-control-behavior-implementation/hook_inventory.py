from pathlib import Path
import importlib.util,re,json,gzip,collections,hashlib,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];VM=Path('/tmp/mixer-swift-control-behavior-20261024/vm')
spec=importlib.util.spec_from_file_location('prior',ROOT/'verification/swift-active-frames-implementation/inventory.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
def readfunctions(text):
 out={};last=0;line=1
 for match in re.finditer(r'^fn ([^\n]+)',text,re.M):
  start=match.start();line+=text.count('\n',last,start);last=start
  header=match.group(1);at=header.index('(');depth=1;i=at+1
  while depth:depth+=(header[i]=='(')-(header[i]==')');i+=1
  name=header[:at];params=header[at+1:i-1];body=text[start:text.find('\n}',start)+2]
  key=re.sub(r'<impl at [^>]+>::','',name);out[key]=(name,params,body,line)
 return out
def norm(ty):
 ty=re.sub(r'\{closure@[^}]+\}','()',ty).replace("'_","'static")
 for alias,path in [('experimental_swift_reactor::','crate::experimental_swift_reactor::'),('experimental_wasi::','crate::experimental_wasi::'),('experimental::','crate::experimental::'),('control::','crate::experimental_swift_reactor::control::'),('accounted::','crate::experimental_wasi::accounted::'),('execute::','crate::execute::')]:ty=re.sub(r'(?<![:\w])'+re.escape(alias),path,ty)
 ty=re.sub(r'(?<![:\w])Cell\b','std::cell::Cell',ty);ty=re.sub(r'&(?!(?:\'|\s*\'))',"&'static ",ty)
 return 'std::convert::Infallible' if ty=='!' else ty

def items(fn):
 name,params,body,line=fn;decl=dict(re.findall(r'let (?:mut )?(_\d+): ([^\n]+);',body))
 for arg in prior.split_top(params):
  ident,ty=arg.split(': ',1);decl[ident]=ty
 out=[]
 debug=collections.defaultdict(list)
 for source,ident in re.findall(r'debug ([\w_]+) => (_\d+);',body):debug[ident].append(source)
 for ident,ty in decl.items():
  out.append((norm(ty),'mir',ident,ty))
  for source in debug[ident]:out.append((norm(ty),'source_alias',source,ty))
 for i,literal in enumerate(re.findall(r'const ("(?:[^"\\]|\\.)*"|(?:true|false)|\d+_(?:u|i)(?:size|8|16|32|64|128))',body)):
  ty="&'static str" if literal.startswith('"') else 'bool' if literal in ['true','false'] else literal.rsplit('_',1)[1]
  out.append((ty,'direct_literal',literal,ty))
 return out
baseline=readfunctions(gzip.decompress((ROOT/'verification/swift-control-accounting-candidate-2/unit.mir.gz').read_bytes()).decode())
paths=list((VM.parent/'target/debug/deps').glob('*.mir'));found=[p for p in paths if 'fn experimental_swift_reactor::execution::frame_operations::control_after_value_pop(' in p.read_text()];assert len(found)==1
currenttext=found[0].read_text();current=readfunctions(currenttext)
new=[key for key in current if any(s in key for s in ['::control_after_value_pop','::control_work_checkpoint','::test_replace_combined_limit','::test_replace_state_limit'])]
assert len(new)==8,new
changed=['primitive_pop','primitive_push','experimental_swift_reactor::execution::frame_operations::work','before_predebit']
# New before_predebit closure0 is the zero-capture cancellation predicate;
# original closure0 moves to closure1 and remains completely covered by old map.
new+=['before_predebit::{closure#0}']
rows=[];functions=[]
for key in new+changed:
 assert key in current,key
 data=items(current[key]);mode='new'
 if key in changed:
  assert key in baseline,key
  old=collections.Counter((x[0],x[1],x[2] if x[1]!='mir' else '') for x in items(baseline[key]));selected=[]
  for item in data:
   identity=(item[0],item[1],item[2] if item[1]!='mir' else '')
   if old[identity]:old[identity]-=1
   else:selected.append(item)
  data=selected;mode='positive_delta_only_existing_inventory_retained'
 envelope='active' if key in changed[:3] else 'permanent'
 for ordinal,(ty,kind,binding,mirtype) in enumerate(data):
  for position in ['source','argument','returned','caller']:
   rows.append(dict(envelope=envelope,field=f'hook_{len(functions)}_{ordinal}_{position}',rustType=ty,mirType=mirtype,sourceName=binding,kind=kind,mirFunction=current[key][0],mirLine=current[key][3],position=position,mode=mode,config='unit'))
 functions.append(dict(key=key,mirFunction=current[key][0],mode=mode,positions=len(data)*4))
# All new closures have no capture projection; prove () is their actual zero
# capture authored logical layout, not an optimizer-private alias.
for key in new:
 if 'closure#' in key:assert not re.search(r'_1\.\d+:',current[key][2]),key
if '--audit' in sys.argv:
 previous=json.loads((HERE/'unit-hook-inventory.json').read_text())
 identity=lambda row:{k:v for k,v in row.items() if k not in ['mirLine','mirFunction']}
 assert list(map(identity,rows))==list(map(identity,previous))
 (HERE/'unit-hook-final-audit.json').write_text(json.dumps(dict(status='exact-positive-role-replay',positiveFields=len(rows),newFunctions=len(new),changedFunctions=len(changed),finalUnitMIRSHA256=hashlib.sha256(currenttext.encode()).hexdigest(),rows=rows,functions=functions),sort_keys=True,indent=2)+'\n')
 with gzip.open(HERE/'final-unit.mir.gz','wb') as out:out.write(currenttext.encode())
 print('passed: final actual-source 400 positive hook/call/closure positions reproduce exactly')
 sys.exit(0)
(HERE/'unit-hook-inventory.json').write_text(json.dumps(rows,sort_keys=True,indent=2)+'\n');(HERE/'unit-hook-functions.json').write_text(json.dumps(functions,sort_keys=True,indent=2)+'\n')
(HERE/'unit-hook-mir-binding.json').write_text(json.dumps(dict(source=str(found[0]),sha256=hashlib.sha256(currenttext.encode()).hexdigest(),candidateUnitMIRSHA256=hashlib.sha256(gzip.decompress((ROOT/'verification/swift-control-accounting-candidate-2/unit.mir.gz').read_bytes())).hexdigest(),newFunctions=len(new),changedFunctions=len(changed),positiveFields=len(rows)),sort_keys=True,indent=2)+'\n')
with gzip.open(HERE/'unit-with-hooks.mir.gz','wb') as out:out.write(currenttext.encode())
target=HERE/'overlay/src/experimental_swift_reactor/frame_operations_tests.rs';s=target.read_text().split('// CONTROL_HOOK_ACCOUNTING_START')[0]+'\n// CONTROL_HOOK_ACCOUNTING_START\n'
for envelope,cls in [('permanent','ControlHookPermanentPositions'),('active','ControlHookActivePositions')]:
 s+='#[allow(dead_code)]\nstruct '+cls+' {\n'
 for row in rows:
  if row['envelope']==envelope:s+='    '+row['field']+': '+row['rustType']+',\n'
 s+='}\n'
s+='pub(super) const CONTROL_HOOK_PERMANENT_BYTES: usize = size_of::<ControlHookPermanentPositions>();\npub(super) const CONTROL_HOOK_ACTIVE_BYTES: usize = size_of::<ControlHookActivePositions>();\n'
target.write_text(s)
# Test-only inventories are positive additions to candidate2, separately named.
target=HERE/'overlay/src/experimental_swift_reactor/control_operations.rs'
if not target.exists():target.write_bytes((ROOT/'verification/swift-control-accounting-candidate-2/overlay/src/experimental_swift_reactor/control_operations.rs').read_bytes())
s=target.read_text();s=re.sub(r'const PERMANENT_BYTES: usize =\s*size_of::<PermanentPositions>\(\);','const PERMANENT_BYTES: usize = size_of::<PermanentPositions>() + { #[cfg(test)] { super::tests::CONTROL_HOOK_PERMANENT_BYTES } #[cfg(not(test))] { 0 } };',s).replace('const ACTIVE_BYTES: usize = size_of::<ActivePositions>();','const ACTIVE_BYTES: usize = size_of::<ActivePositions>() + { #[cfg(test)] { super::tests::CONTROL_HOOK_ACTIVE_BYTES } #[cfg(not(test))] { 0 } };');target.write_text(s)
print('positive hook fields',len(rows),'new functions',len(new),'changed',len(changed))
