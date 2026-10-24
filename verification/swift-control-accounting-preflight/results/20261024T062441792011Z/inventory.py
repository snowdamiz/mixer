"""Exact positive additions derived from actual draft MIR. No baseline row credit."""
from pathlib import Path
import re,json,sys,importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('prior',ROOT/'verification/swift-active-frames-implementation/inventory.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
ACCESSORS={'result','height','start','end','is_loop','is_function','is_if','clear_result','decoded'}
def selected(name):
 if name.startswith('control_operations::'):return ('active',name.split('::{closure#')[0].split('::')[-1])
 if name.startswith('experimental::execution::') and name.split('::')[-1] in ACCESSORS:return ('active','Control_'+name.split('::')[-1])
 return None

def normalize(ty,closures):
 def closure(m):
  site=m.group(0)
  if site not in closures:raise ValueError(('unresolved closure',site))
  return closures[site]
 ty=re.sub(r'\{closure@[^}]+\}',closure,ty)
 ty=ty.replace("'_","'static")
 for alias,path in [('experimental_swift_reactor::','crate::experimental_swift_reactor::'),('experimental_wasi::','crate::experimental_wasi::'),('experimental::','crate::experimental::'),('control::','crate::experimental_swift_reactor::control::'),('accounted::','crate::experimental_wasi::accounted::')]:ty=re.sub(r'(?<![:\w])'+re.escape(alias),path,ty)
 ty=re.sub(r'&(?!(?:\'|\s*\'))',"&'static ",ty)
 return 'Infallible' if ty=='!' else ty

def inventory(path,config):
 functions=[];closures={}
 for name,params,body,line in prior.functions(path.read_text()):
  use=selected(name)
  if not use:continue
  decl=dict(re.findall(r'let (?:mut )?(_\d+): ([^\n]+);',body))
  for arg in prior.split_top(params):
   ident,ty=arg.split(': ',1);decl[ident]=ty
  functions.append((name,params,body,line,use,decl))
  # Use the compiler's actual capture field projections, preserving every type.
  for site in re.findall(r'\{closure@[^}]+\}',params):
   fields={int(i):ty for i,ty in re.findall(r'_1\.(\d+): ([^\n]*?)\)',body)}
   if fields:closures[site]='('+', '.join(fields[i] for i in range(len(fields)))+(',' if len(fields)==1 else '')+')'
   else:
    assert not re.search(r'_1\.\d+',body),name
    closures[site]='()'
 rows=[];defs=[]
 for ordinal,(name,params,body,line,(env,window),decl) in enumerate(functions):
  debug={}
  for source,ident in re.findall(r'debug ([\w_]+) => (_\d+);',body):debug.setdefault(ident,[]).append(source)
  for ident,ty in decl.items():
   rust=normalize(ty,closures)
   for position in ['source','argument','returned','caller']:
    rows.append(dict(envelope=env,window=window,binding=ident,position=position,rustType=rust,sourceNames=debug.get(ident,[]),mirFunction=name,mirLine=line,mirType=ty,config=config,field=f'mir_{config}_{ordinal}_{ident[1:]}_{position}'))
   # Source bindings stay separate when compiler aliases them to an argument or
   # another source name. These are not credited to the compiler transfer row.
   for alias_ordinal,source in enumerate(debug.get(ident,[])):
    for position in ['source','argument','returned','caller']:
     rows.append(dict(envelope=env,window=window,binding=source,position=position,rustType=rust,sourceNames=[source],mirFunction=name,mirLine=line,mirType=ty,config=config,field=f'alias_{config}_{ordinal}_{ident[1:]}_{alias_ordinal}_{source}_{position}'))
  # Typed direct literal arguments do not always receive a MIR local.
  literals=re.findall(r'const ("(?:[^"\\]|\\.)*"|(?:true|false)|\d+_(?:u|i)(?:size|8|16|32|64|128))',body)
  for i,literal in enumerate(literals):
   ty="&'static str" if literal.startswith('"') else 'bool' if literal in ['true','false'] else literal.rsplit('_',1)[1]
   for position in ['source','argument','returned','caller']:
    rows.append(dict(envelope=env,window=window,binding='literal_'+str(i),position=position,rustType=ty,sourceNames=[literal],mirFunction=name,mirLine=line,mirType=ty,config=config,field=f'literal_{config}_{ordinal}_{i}_{position}'))
  defs.append(dict(function=name,mirLine=line,window=window,envelope=env,locals=len(decl),sourceAliases=sum(map(len,debug.values())),directTypedLiterals=len(literals),closures=[site for site in re.findall(r'\{closure@[^}]+\}',params)],config=config))
 return rows,defs

def complete_delta(path,config):
 # Only new slot-check positions. Existing complete/storage/drop positions stay
 # in their original inventories and enlarge with the actual concrete type.
 result=[]
 for name,params,body,line in prior.functions(path.read_text()):
  if 'frame_operations::' not in name or not name.endswith('::complete'):continue
  all_decl=dict(re.findall(r'let (?:mut )?(_\d+): ([^\n]+);',body))
  additions=[(i,t) for i,t in all_decl.items() if re.search(r'&.*Option<.*Result<bool,',t)]
  assert len(additions)==1,(name,additions)
  ident,ty=additions[0]
  bool_ident=re.search(r'(_\d+) = Option::<.*Result<bool,.*>>::is_none\((?:copy|move) '+ident+r'\)',body)
  assert bool_ident,('controlled check missing',name)
  for binding,t in [(ident,ty),(bool_ident.group(1),'bool')]:
   for position in ['source','argument','returned','caller']:
    result.append(dict(envelope='permanent',window='complete_controlled_empty',binding=binding,position=position,rustType=normalize(t,{}),sourceNames=['storage.controlled.is_none'],mirFunction=name,mirLine=line,mirType=t,config=config,field=f'completion_{config}_{binding[1:]}_{position}'))
 return result

def rows(directory):
 out=[];defs=[]
 for config in ['production','unit']:
  part,functions=inventory(directory/(config+'.mir'),config);out+=part;defs+=functions
  out+=complete_delta(directory/(config+'.mir'),config)
 # New flat caller slot, move-out result/bool/failure, retained copies, and every
 # prepare/complete/drop tuple edge. Whole original storage copies are already
 # occupied in existing inventories and gain their 1096 bytes there.
 permanent=[('slot','Option<Result<bool, SwiftRunFailure>>'),('result','Result<bool, SwiftRunFailure>'),('bool','bool'),('failure','SwiftRunFailure'),('retained_failure','Option<SwiftRunFailure>')]
 for edge in ['fixed_caller','prepare_storage','complete_storage','complete_drop_tuple','return_wrapper','retained_report']:
  for binding,ty in permanent:
   for pos in ['source','argument','returned','caller']:
    out.append(dict(envelope='permanent',window=edge,binding=binding,position=pos,rustType=ty,sourceNames=[binding],config='source',field=f'fixed_{edge}_{binding}_{pos}'))
 return out,defs

def render(directory,vm):
 data,functions=rows(directory);control=vm/'src/experimental_swift_reactor/control_operations.rs';owner=vm/'src/experimental/execution/mod.rs'
 # Inventory declarations live where the private Kind type is nameable. No new
 # method/field visibility, owner, proof, pin, control arena or wrapper is added.
 private=[];normal=[]
 for row in data:
  private.append(row) if 'execution::Kind' in row['rustType'] else normal.append(row)
 original=owner.read_text().split('// CONTROL_PRIVATE_ACCOUNTING_START')[0]
 original+='\n// CONTROL_PRIVATE_ACCOUNTING_START\n#[cfg(feature = "experimental-swift-reactor")]\n#[allow(dead_code)]\npub(crate) struct SwiftControlPrivatePositions {\n'
 for row in private:
  if row['config']=='unit':original+='    #[cfg(test)]\n'
  original+='    '+row['field']+': '+row['rustType'].replace('crate::experimental::execution::Kind','Kind')+',\n'
 original+='}\n';owner.write_text(original)
 source=control.read_text().split('// ACCOUNTING_START')[0]+'// ACCOUNTING_START\n'
 for env,cls in [('permanent','PermanentPositions'),('active','ActivePositions')]:
  source+='struct '+cls+' {\n'
  if env=='active':source+='    private_scalar_transfers: crate::experimental::execution::SwiftControlPrivatePositions,\n'
  for row in normal:
   if row['envelope']!=env:continue
   if row['config']=='unit':source+='    #[cfg(test)]\n'
   source+='    '+row['field']+': '+row['rustType']+',\n'
  source+='}\n'
 source+='pub(in crate::experimental_swift_reactor::execution) const PERMANENT_BYTES: usize = size_of::<PermanentPositions>();\npub(super) const ACTIVE_BYTES: usize = size_of::<ActivePositions>();\n'
 control.write_text(source)
 for row in data:row['ownerClass']='crate::experimental::execution::SwiftControlPrivatePositions' if row in private else 'PermanentPositions' if row['envelope']=='permanent' else 'ActivePositions'
 (directory/'inventory-schema.json').write_text(json.dumps(data,sort_keys=True,indent=2)+'\n');(directory/'function-manifest.json').write_text(json.dumps(functions,sort_keys=True,indent=2)+'\n')
 print('inventory',len(data),'private fields',len(private),'functions',len(functions))
if __name__=='__main__':render(Path(sys.argv[1]),Path(sys.argv[2]))
