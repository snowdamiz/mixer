#!/usr/bin/env python3
"""Positive authored + actual canonical-MIR roles, never credits prior rows.

Each argument/return/local, authored alias and direct typed literal has separate
source/argument/returned/caller fields. All positions are summed simultaneously.
Unit-only positions are additional to production; no stack/RSS inference.
"""
from pathlib import Path
import re,json,sys,gzip
HERE=Path(__file__).resolve().parent
REF="&'static mut FrameOperationPhase<'static>"
SLOT="Option<Result<(), SwiftRunFailure>>"
AUTHORED={
'bulk_memory_bulk':[('phase',REF),('length','usize'),('credits','u64'),('result','Result<(),SwiftRunFailure>')],
'bulk_memory_copy':[('phase',REF),('length','usize'),('source','usize'),('destination','usize'),('range','std::ops::Range<usize>'),('left','usize'),('at','usize'),('chunk','usize'),('memory',"&'static mut Vec<u8>"),('iteration','std::iter::StepBy<std::ops::Range<usize>>'),('result','Result<(),SwiftRunFailure>')],
'bulk_memory_fill':[('phase',REF),('length','usize'),('value','u8'),('destination','usize'),('range','std::ops::Range<usize>'),('start','usize'),('end','usize'),('slice',"&'static mut [u8]"),('iteration','std::iter::StepBy<std::ops::Range<usize>>'),('result','Result<(),SwiftRunFailure>')],
'bulk_memory_check':[('phase',REF),('cursor','Cursor'),('wasi','Option<WasiUsage>'),('result','Result<(),SwiftRunFailure>')],
'bulk_memory_preflight':[('phase',REF),('operands','bool'),('pages','usize'),('memory',"&'static Vec<u8>"),('frame',"&'static SwiftFrame"),('floor','usize'),('available','usize'),('length','usize'),('values',"&'static [Value]"),('type','Type'),('result','Result<(),SwiftRunFailure>')],
'bulk_memory_unsupported':[('phase',REF),('cursor','Cursor'),('fault','Fault'),('wasi','Option<WasiUsage>'),('failure','SwiftRunFailure')],
'bulk_memory_operation':[('phase',REF),('operation','Operation'),('slot',"&'static mut "+SLOT),('vacant','bool'),('failure','SwiftRunFailure'),('result','Result<(),SwiftRunFailure>'),('publication',SLOT),('admission','Result<(),SwiftRunFailure>')],
'bulk_memory_operation_inner':[('phase',REF),('operation','Operation'),('pages','usize'),('size','Value'),('result','Result<(),SwiftRunFailure>')],
'bulk_memory_pinned_caller':[('phase',REF),('storage',"&'static mut FrameOperationStorage<'static>"),('slot',"&'static mut "+SLOT),('failure','SwiftRunFailure'),('result','Result<(),SwiftRunFailure>'),('publication',SLOT),('admission','Result<(),SwiftRunFailure>')],
'bulk_memory_pinned_step':[('phase',REF),('frame',"&'static SwiftFrame"),('pin',"&'static SwiftFunctionPin"),('view',"FunctionView<'static>"),('instruction','DecodedInstruction'),('instruction_borrow',"&'static DecodedInstruction"),('selection','(u32,DecodedInstruction)'),('function','u32'),('cursor','Cursor'),('charged','Result<(),SwiftRunFailure>'),('pc','usize'),('checked_pc','Option<usize>'),('frame_mut',"&'static mut SwiftFrame"),('result','Result<(),SwiftRunFailure>')],
}
PERMANENT={
'fixed_bulk_caller':[('storage',"FrameOperationStorage<'static>"),('slot',SLOT),('result','Result<(),SwiftRunFailure>'),('admission','Result<(),SwiftRunFailure>'),('failure','SwiftRunFailure'),('retained_failure','Option<SwiftRunFailure>')],
'fixed_bulk_completion':[('storage',"FrameOperationStorage<'static>"),('drop_tuple',"(ExecutionParts<'static,SwiftMode>,FrameOperationStorage<'static>)"),('slot',SLOT),('result','Result<(),SwiftRunFailure>'),('admission','Result<(),SwiftRunFailure>'),('failure','SwiftRunFailure'),('report','FrameDrainReport')],
}
def split_top(text):
 result=[];last=0;level=0
 for i,c in enumerate(text):
  if c in '<([{':level+=1
  elif c in '>)]}':level-=1
  elif c==',' and level==0:result.append(text[last:i].strip());last=i+1
 result.append(text[last:].strip());return [v for v in result if v]
def functions(text):
 line_number=1;previous_start=0
 for m in re.finditer(r'^fn ([^\n]+)',text,re.M):
  line_number+=text.count('\n',previous_start,m.start());previous_start=m.start()
  head=m.group(1);at=head.index('(');i=at+1;depth=1
  while depth:depth+=(head[i]=='(')-(head[i]==')');i+=1
  yield head[:at],head[at+1:i-1],text[m.start():text.find('\n}',m.start())+2],line_number

# Promoted constants have typed return/backing places even when their borrowed
# reference appears in a function local. Name them separately and positively.
def promoted_constants(text):
 for m in re.finditer(r'^const ([^\n]+)',text,re.M):
  head=m.group(1)
  if '::promoted[' not in head:continue
  name=head.split(': &',1)[0]
  yield name,'',text[m.start():text.find('\n}',m.start())+2],text.count('\n',0,m.start())+1

def selected(name):
 if '::tests::' in name or '::tests}' in name:return False
 return name.startswith('bulk_memory_operations::') or '::bulk_memory_operations::' in name or name.startswith('bulk_memory_pinned')

def normalize(ty,closures):
 def replace(m):
  assert m.group(0) in closures,('unresolved closure',m.group(0))
  return closures[m.group(0)]
 ty=re.sub(r'\{closure@[^}]+\}',replace,ty)
 ty=re.sub(r"'[A-Za-z_][A-Za-z_0-9]*","'static",ty)
 for prefix,path in [('experimental_swift_reactor::','crate::experimental_swift_reactor::'),('experimental_wasi::','crate::experimental_wasi::'),('experimental::','crate::experimental::'),('control::','crate::experimental_swift_reactor::control::')]:ty=re.sub(r'(?<![:\w])'+re.escape(prefix),path,ty)
 ty=re.sub(r"&(?!(?:'|\s*'))","&'static ",ty)
 return 'std::convert::Infallible' if ty=='!' else ty

def canonical(path,config):
 selected_functions=[];closures={}
 text=gzip.decompress(path.read_bytes()).decode() if path.suffix==".gz" else path.read_text()
 for name,params,body,line in [*functions(text),*promoted_constants(text)]:
  if not selected(name):continue
  decl=dict(re.findall(r'let (?:mut )?(_\d+): ([^\n]+);',body))
  for arg in split_top(params):
   ident,ty=arg.split(': ',1);decl[ident]=ty
  # Capture tuples contain the actual compiler-projected types. Every field is
  # positively named; no zero-size/equal-layout credit is borrowed elsewhere.
  for site in re.findall(r'\{closure@[^}]+\}',params):
   fields={int(i):ty for i,ty in re.findall(r'_1\.(\d+): ([^\n]*?)\)',body)}
   if fields:
    assert set(fields)==set(range(len(fields))),(name,fields)
    closures[site]='('+', '.join(fields[i] for i in range(len(fields)))+(',' if len(fields)==1 else '')+')'
   else:
    assert not re.search(r'_1\.\d+',body),name
    closures[site]='()'
  selected_functions.append((name,params,body,line,decl))
 rows=[];manifest=[]
 for ordinal,(name,params,body,line,decl) in enumerate(selected_functions):
  debug={}
  for source,ident in re.findall(r'debug ([\w_]+) => (_\d+);',body):debug.setdefault(ident,[]).append(source)
  window=name.split('::{closure#')[0].split('::')[-1]
  def add(binding,ty,kind,source,stem):
   for pos in ['source','argument','returned','caller']:
    rows.append(dict(envelope='active',window=window,field=f'{stem}_{pos}',rustType=normalize(ty,closures),binding=binding,sourceNames=source,mirFunction=name,mirLine=line,mirType=ty,position=pos,config=config,kind=kind))
  for ident,ty in decl.items():
   add(ident,ty,'canonical',debug.get(ident,[]),f'mir_{config}_{ordinal}_{ident[1:]}')
   for index,source in enumerate(debug.get(ident,[])):add(source,ty,'authored-alias',[source],f'alias_{config}_{ordinal}_{ident[1:]}_{index}_{source}')
  literals=re.findall(r'const ("(?:[^"\\]|\\.)*"|true|false|\d+_(?:u|i)(?:size|8|16|32|64|128))',body)
  for index,literal in enumerate(literals):
   ty="&'static str" if literal.startswith('"') else 'bool' if literal in ['true','false'] else literal.rsplit('_',1)[1]
   add('literal_'+str(index),ty,'direct-literal',[literal],f'literal_{config}_{ordinal}_{index}')
  manifest.append(dict(function=name,window=window,mirLine=line,canonicalTypedBindings=len(decl),sourceAliases=sum(map(len,debug.values())),directTypedLiterals=len(literals),config=config))
 return rows,manifest,closures

def rows():
 result=[];manifest=[];closures={}
 for config in ['production','unit']:
  part,defs,captures=canonical(HERE/(config+'.mir') if (HERE/(config+'.mir')).exists() else HERE/('canonical-'+config+'.mir.gz'),config);result+=part;manifest+=defs;closures[config]=captures
 for env,source in [('active',AUTHORED),('permanent',PERMANENT)]:
  for window,bindings in source.items():
   for binding,ty in bindings:
    for pos in ['source','argument','returned','caller']:
     result.append(dict(envelope=env,window=window,field=f'source_{window}_{binding}_{pos}',rustType=ty,binding=binding,sourceNames=[binding],position=pos,config='source',kind='authored'))
 return result,manifest,closures

def render(vm):
 data,manifest,captures=rows();p=(vm/'vm' if (vm/'vm'/'Cargo.toml').exists() else vm)/'src/experimental_swift_reactor/bulk_memory_operations.rs';s=p.read_text().split('// ACCOUNTING_START')[0]+'// ACCOUNTING_START\n'
 for env,cls in [('permanent','PermanentPositions'),('active','ActivePositions')]:
  s+='struct '+cls+' {\n'
  for row in data:
   if row['envelope']!=env:continue
   if row['config']=='unit':s+='    #[cfg(test)]\n'
   s+='    '+row['field']+': '+row['rustType']+',\n'
   row['ownerClass']='PermanentPositions' if row['envelope']=='permanent' else 'ActivePositions'
  s+='}\n'
 s+='pub(in crate::experimental_swift_reactor::execution) const PERMANENT_BYTES: usize = size_of::<PermanentPositions>();\npub(super) const ACTIVE_BYTES: usize = size_of::<ActivePositions>();\n';p.write_text(s)
 enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n')
 (HERE/'inventory-schema.json').write_text(enc(data));(HERE/'function-manifest.json').write_text(enc(manifest));(HERE/'closure-captures.json').write_text(enc(captures))
 print('positive fields',len(data),'functions',len(manifest),'closures',sum(map(len,captures.values())))
if __name__=='__main__':render(Path(sys.argv[1]))
