#!/usr/bin/env python3
"""Positive growth source/MIR/alias/literal/capture/promotion inventory.

Parser mechanics reuse the independently authored accepted bulk collector.
All growth roles are fresh positions. No old field, alias or padding supplies
credit. Every logical object is simultaneously added with measured padding.
"""
from pathlib import Path
import re,json,gzip,sys
HERE=Path(__file__).resolve().parent
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
 line=1;previous=0
 for m in re.finditer(r'^const ([^\n]+)',text,re.M):
  line+=text.count('\n',previous,m.start());previous=m.start()
  head=m.group(1)
  if '::promoted[' not in head:continue
  name=head.split(': &',1)[0]
  yield name,'',text[m.start():text.find('\n}',m.start())+2],line

def selected(name):
 if '::tests::' in name or '::tests}' in name:return False
 return name.startswith('memory_growth_operations::') or '::memory_growth_operations::' in name or any(name==n or name.startswith(n+'::') for n in ['growth_operation','growth_unsupported','growth_operation_inner','growth_pinned_caller','growth_pinned_step','release_growth_pending','complete_growth'])

def normalize(ty,closures):
 def replace(m):
  assert m.group(0) in closures,('unresolved closure',m.group(0))
  return closures[m.group(0)]
 ty=re.sub(r'\{closure@[^}]+\}',replace,ty)
 ty=re.sub(r"'[A-Za-z_][A-Za-z_0-9]*","'static",ty)
 for prefix,path in [('experimental_swift_reactor::','crate::experimental_swift_reactor::'),('experimental_wasi::','crate::experimental_wasi::'),('experimental::','crate::experimental::'),('control::','crate::experimental_swift_reactor::control::')]:ty=re.sub(r'(?<![:\w])'+re.escape(prefix),path,ty)
 ty=re.sub(r"&(?!(?:'|\s*'))","&'static ",ty)
 ty=re.sub(r'(?<![:\w])TryReserveError', 'std::collections::TryReserveError',ty)
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
    rows.append(dict(envelope='permanent'if window in ['prepare_growth','complete_growth']or '::GrowthCompletion::'in name else'active',window=window,field=f'{stem}_{pos}',rustType=normalize(ty,closures),binding=binding,sourceNames=source,mirFunction=name,mirLine=line,mirType=ty,position=pos,config=config,kind=kind))
  for ident,ty in decl.items():
   add(ident,ty,'canonical',debug.get(ident,[]),f'mir_{config}_{ordinal}_{ident[1:]}')
   for index,source in enumerate(debug.get(ident,[])):add(source,ty,'authored-alias',[source],f'alias_{config}_{ordinal}_{ident[1:]}_{index}_{source}')
  literals=re.findall(r'const ("(?:[^"\\]|\\.)*"|true|false|\d+_(?:u|i)(?:size|8|16|32|64|128))',body)
  for index,literal in enumerate(literals):
   ty="&'static str" if literal.startswith('"') else 'bool' if literal in ['true','false'] else literal.rsplit('_',1)[1]
   add('literal_'+str(index),ty,'direct-literal',[literal],f'literal_{config}_{ordinal}_{index}')
  manifest.append(dict(function=name,window=window,mirLine=line,canonicalTypedBindings=len(decl),sourceAliases=sum(map(len,debug.values())),directTypedLiterals=len(literals),config=config))
 return rows,manifest,closures


PHASE="&'static mut FrameOperationPhase<'static>"
CONTEXT="&'static mut SwiftGrowthContext<'static>"
STORAGE="&'static mut SwiftGrowthStorage"
EXECUTION="&'static mut SwiftGrowthExecution<'static,'static>"
RESULT='Result<(),SwiftRunFailure>'
SLOT='Option<Result<(),SwiftRunFailure>>'
PREPARATION="Option<Result<(FrameOperationPhase<'static>,SwiftGrowthContext<'static>),SwiftRunFailure>>"
AUTHORED={
'context':[('memory_ticket',"&'static mut Option<ReservationTicket>"),('context',"SwiftGrowthContext<'static>")],
'empty':[('storage','SwiftGrowthStorage'),('transfer','GrowthTransfer'),('replacement','Vec<u8>'),('ticket','Option<ReservationTicket>'),('old','Vec<u8>'),('old_ticket','Option<ReservationTicket>'),('old_pages','u32'),('next_pages','u32'),('copied','usize'),('pages_debited','usize'),('live_unreconciled','bool')],
'vacant':[('storage',"&'static SwiftGrowthStorage"),('vacant','bool'),('replacement',"&'static Vec<u8>"),('old',"&'static Vec<u8>"),('ticket',"&'static Option<ReservationTicket>"),('old_ticket',"&'static Option<ReservationTicket>")],
'grow':[('execution',EXECUTION),('delta','u32'),('old','u32'),('maximum','u32'),('next','u32'),('next_checked','Option<u32>'),('bytes','usize'),('work','usize'),('memory','Vec<u8>'),('result',RESULT),('error','SwiftRunFailure'),('old_bytes','usize'),('at','usize'),('end','usize'),('loop','std::iter::StepBy<std::ops::Range<usize>>'),('new_slice',"&'static mut [u8]"),('old_slice',"&'static [u8]"),('value','Value')],
'invariant':[('execution',EXECUTION),('failure','SwiftRunFailure'),('fault','Fault'),('wasi','Option<WasiUsage>'),('cursor','Cursor')],
'work':[('execution',EXECUTION),('amount','usize'),('result',RESULT)],
'maximum':[('execution',EXECUTION),('descriptor','MemoryExecutionView'),('descriptor_option','Option<MemoryExecutionView>'),('declared_maximum','Option<u32>'),('host_maximum','u32'),('narrowed_maximum','u32'),('maximum','u32'),('result','Result<u32,SwiftRunFailure>')],
'check':[('execution',EXECUTION),('cursor','Cursor'),('wasi','Option<WasiUsage>'),('result',RESULT)],
'checked_memory':[('execution',EXECUTION),('memory',"&'static [u8]"),('stage','u8'),('result',RESULT)],
'allocate':[('execution',EXECUTION),('bytes','usize'),('ticket','ReservationTicket'),('ticket_result','Result<ReservationTicket,SwiftRunFailure>'),('delta','usize'),('replacement',"&'static mut Vec<u8>"),('old_pages','u32'),('next_pages','u32'),('result',RESULT),('error','SwiftRunFailure'),('allocation_result','Result<(),std::collections::TryReserveError>'),('allocation_error','std::collections::TryReserveError'),('fault','Fault'),('observed','usize'),('allocation','Vec<u8>'),('returned_allocation','Result<Vec<u8>,SwiftRunFailure>')],
'release_ticket':[('execution',EXECUTION),('old','bool'),('transfer',"&'static mut GrowthTransfer"),('slot',"&'static mut Option<ReservationTicket>"),('pages','u32'),('selection',"(&'static mut Option<ReservationTicket>,u32)"),('ticket',"&'static ReservationTicket"),('control',"&'static mut RuntimeControl"),('wasi','Option<WasiUsage>'),('taken_ticket','ReservationTicket'),('result',RESULT),('layout','bool'),('bytes','usize')],
'release_pending':[('execution',EXECUTION),('replacement','Vec<u8>'),('old','Vec<u8>'),('result',RESULT),('error','SwiftRunFailure'),('pages_debited','usize'),('wasi','Option<WasiUsage>')],
'commit':[('execution',EXECUTION),('memory','Vec<u8>'),('old_bytes','usize'),('next','u32'),('failure','SwiftRunFailure'),('replacement','Vec<u8>'),('old','Vec<u8>'),('ticket','Option<ReservationTicket>'),('old_ticket','Option<ReservationTicket>'),('result',RESULT)],
'preflight':[('execution',EXECUTION),('length','usize'),('pages','usize'),('ticket',"&'static ReservationTicket"),('frame',"&'static SwiftFrame"),('available','usize'),('checked_available','Option<usize>'),('type','Type'),('value',"&'static Value"),('result',RESULT)],
'growth_operation':[('phase',PHASE),('context',CONTEXT),('growth',STORAGE),('operation','Operation'),('returned',"&'static mut "+SLOT),('failure','SwiftRunFailure'),('result',RESULT),('publication',SLOT),('admission',RESULT)],
'growth_unsupported':[('phase',PHASE),('cursor','Cursor'),('fault','Fault'),('wasi','Option<WasiUsage>'),('failure','SwiftRunFailure')],
'growth_operation_inner':[('phase',PHASE),('context',CONTEXT),('growth',STORAGE),('operation','Operation'),('execution',"SwiftGrowthExecution<'static,'static>"),('result',RESULT)],
'growth_pinned_caller':[('phase',PHASE),('context',CONTEXT),('growth',STORAGE),('storage',"&'static mut FrameOperationStorage<'static>"),('result',RESULT),('failure','SwiftRunFailure'),('slot',SLOT)],
'growth_pinned_step':[('phase',PHASE),('context',CONTEXT),('growth',STORAGE),('frame',"&'static SwiftFrame"),('pin',"&'static SwiftFunctionPin"),('view',"FunctionView<'static>"),('selected','(u32,DecodedInstruction)'),('instruction','DecodedInstruction'),('instruction_borrow',"&'static DecodedInstruction"),('function','u32'),('cursor','Cursor'),('pc','usize'),('checked_pc','Option<usize>'),('frame_mut',"&'static mut SwiftFrame"),('result',RESULT)],
'release_growth_pending':[('phase',PHASE),('context',CONTEXT),('growth',STORAGE),('execution',"SwiftGrowthExecution<'static,'static>"),('result',RESULT)],
'prepare_growth':[('owner',"&'static mut SwiftReactorInstance"),('control',"&'static mut RuntimeControl"),('cache',"&'static mut SwiftFunctionCache"),('wasi',"&'static mut AccountedWasi"),('state',"&'static mut SwiftExecutionState"),('lifecycle',"&'static mut Lifecycle"),('cursor','Cursor'),('live','SwiftLiveUsage'),('previous','usize'),('admitted','usize'),('bytes','usize'),('bound','FrameBound'),('memory',"&'static mut Vec<u8>"),('table',"&'static mut Vec<Option<u32>>"),('globals',"&'static mut Vec<Value>"),('values',"&'static mut Vec<Value>"),('controls',"&'static mut Vec<Control>"),('frames',"&'static mut Vec<SwiftFrame>"),('buffers',"&'static mut [Option<ReservationTicket>;6]"),('cleanup',"&'static mut FrameCleanupState"),('context',"SwiftGrowthContext<'static>"),('phase',"FrameOperationPhase<'static>"),('pair',"(FrameOperationPhase<'static>,SwiftGrowthContext<'static>)"),('result',"Result<(FrameOperationPhase<'static>,SwiftGrowthContext<'static>),SwiftRunFailure>")],
}
PERMANENT={
'caller_and_completion':[('phase',"FrameOperationPhase<'static>"),('context',"SwiftGrowthContext<'static>"),('growth','SwiftGrowthStorage'),('transfer','GrowthTransfer'),('storage',"FrameOperationStorage<'static>"),('preparation',PREPARATION),('slot',SLOT),('result',RESULT),('completion',"GrowthCompletion<'static>"),('frame_completion','FrameCompletion'),('drop_growth',"(SwiftGrowthContext<'static>,SwiftGrowthStorage,"+PREPARATION+")"),('drop_frame',"(ExecutionParts<'static,SwiftMode>,FrameOperationStorage<'static>)"),('retained',"(FrameOperationPhase<'static>,SwiftGrowthContext<'static>,SwiftGrowthStorage,FrameOperationStorage<'static>,"+PREPARATION+")"),('failure','SwiftRunFailure')],
}

def rows():
 result=[];functions=[];captures={}
 for config in ['production','unit']:
  part,defs,captured=canonical(HERE/('final-all-'+config+'.mir.gz'),config);result+=part;functions+=defs;captures[config]=captured
 for envelope,windows in [('active',AUTHORED),('permanent',PERMANENT)]:
  for window,bindings in windows.items():
   for binding,ty in bindings:
    for pos in ['source','argument','returned','caller']:
     result.append(dict(envelope='permanent'if window in ['prepare_growth','context']else envelope,window=window,field=f'source_{window}_{binding}_{pos}',rustType=ty,binding=binding,sourceNames=[binding],position=pos,config='source',kind='authored'))
 return result,functions,captures

def render(vm):
 data,functions,captures=rows();p=vm/'src/experimental_swift_reactor/memory_growth_operations.rs';text=p.read_text().split('// ACCOUNTING_START')[0]+'// ACCOUNTING_START\n'
 for envelope,cls in [('permanent','PermanentPositions'),('active','ActivePositions')]:
  text+='struct '+cls+' {\n'
  for row in data:
   if row['envelope']!=envelope:continue
   if row['config']=='unit':text+='    #[cfg(test)]\n'
   text+='    '+row['field']+': '+row['rustType']+',\n';row['ownerClass']=cls
  text+='}\n'
 text+='pub(in crate::experimental_swift_reactor::execution) const PERMANENT_BYTES:usize=size_of::<PermanentPositions>();\npub(super) const ACTIVE_BYTES:usize=size_of::<ActivePositions>();\n';p.write_text(text)
 for name,obj in [('inventory-schema.json',data),('function-manifest.json',functions),('closure-captures.json',captures)]:
  (HERE/name).write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
 print('Fresh positive fields',len(data),'functions/promotions',len(functions),flush=True)
if __name__=='__main__':render(Path(sys.argv[1]))
