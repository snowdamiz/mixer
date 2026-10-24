"""Positive implementation supplement; never credits the frozen1061 rows.

Every exact compiler-typed selected argument/local/return and anonymous capture
gets distinct positive source/argument/returned/caller fields. Manual source
aliases remain separate where lowering merges them. All rows are reserved
simultaneously; no frozen field, receiver alias, padding or previous bound pays
for a new position. Unit hook leaves use a strict whitelist and permanent scope.
Independent actual-source completeness review remains mandatory.
"""
from pathlib import Path
import importlib.util,re,json
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('frozen', ROOT/'verification/swift-active-frame-contract/inventory.py')
frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
REF="&'static mut FrameOperationPhase<'static>"
LOCALS={
'original_owners': [('control',"&'static mut RuntimeControl"),('cache',"&'static SwiftFunctionCache"),('wasi',"&'static AccountedWasi"),('state',"&'static SwiftExecutionState"),('cursor','Cursor'),('header',"&'static ReservationTicket"),('requests','[usize; 6]'),('requests_option','Option<[usize; 6]>'),('budget','SwiftRunBudget'),('ticket_iterator',"std::iter::Enumerate<std::slice::Iter<'static, Option<ReservationTicket>>>"),('index','usize'),('ticket_option',"&'static Option<ReservationTicket>"),('ticket',"&'static ReservationTicket")],
'prepare_frames':[('self',"&'static mut SwiftReactorInstance"),('control_option',"&'static mut Option<RuntimeControl>"),('cache_option',"&'static mut Option<SwiftFunctionCache>"),('wasi_option',"&'static mut Option<AccountedWasi>"),('state_option',"&'static mut Option<SwiftExecutionState>"),('lifecycle',"&'static mut Lifecycle"),('control',"&'static mut RuntimeControl"),('cache',"&'static mut SwiftFunctionCache"),('wasi',"&'static mut AccountedWasi"),('state',"&'static mut SwiftExecutionState"),('cursor','Cursor'),('live','SwiftLiveUsage'),('previous','usize'),('admitted','usize'),('bytes','usize'),('bound','FrameBound'),('phase',"FrameOperationPhase<'static>"),('result',"Result<FrameOperationPhase<'static>, SwiftRunFailure>")],
'resume_frame_cleanup':[('self',"&'static mut SwiftReactorInstance"),('control',"&'static mut RuntimeControl"),('cache',"&'static mut SwiftFunctionCache"),('wasi',"&'static mut AccountedWasi"),('state',"&'static mut SwiftExecutionState"),('lifecycle',"&'static mut Lifecycle"),('cursor','Cursor'),('bound','FrameBound'),('bytes','usize'),('phase',"FrameOperationPhase<'static>"),('result',"Result<FrameOperationPhase<'static>, SwiftRunFailure>")],
'invariant':[('self',REF),('code',"&'static str"),('fault','Fault'),('failure','SwiftRunFailure')],
'limit':[('self',REF),('kind','SwiftRunFailureKind'),('resource','SwiftRunResource'),('code',"&'static str"),('attempted','usize'),('limit','usize'),('fault','Fault'),('failure','SwiftRunFailure')],
'active':[('self',REF),('result','Result<(), SwiftRunFailure>')],
'agreement':[('self',REF),('live','SwiftLiveUsage')],
'work':[('self',REF),('amount','usize')],
'acquire_pin':[('self',REF),('function','u32'),('frame_bound','usize'),('preparation',"Option<Result<CacheOperationPhase<'static>, SwiftRunFailure>>"),('phase',"CacheOperationPhase<'static>"),('returned','Option<Result<SwiftFunctionPin, SwiftRunFailure>>'),('pin','Option<SwiftFunctionPin>'),('failure','Option<SwiftRunFailure>'),('completion','Result<(), SwiftRunFailure>'),('completion_failure','SwiftRunFailure'),('nested_restore','Option<usize>'),('attempt','PinAttempt')],
'enter':[('self',REF),('function','u32'),('pre_values_len','usize'),('pre_controls_len','usize'),('result','Result<(), SwiftRunFailure>')],
'enter_inner':[('self',REF),('function','u32'),('frame_limit','usize'),('params','usize'),('result','bool'),('signature',"SignatureView<'static>"),('base','usize'),('operands','usize'),('parameter_index','usize'),('parameter_type','Option<Type>'),('parameter_value',"Option<&'static Value>"),('pin','Option<SwiftFunctionPin>'),('failure','Option<SwiftRunFailure>'),('nested_restore','Option<usize>'),('guard_shared',"&'static EntryGuard"),('guard_pin',"&'static SwiftFunctionPin"),('view',"FunctionView<'static>"),('locals','usize'),('end','usize'),('total_locals','usize'),('value_capacity','usize'),('control_capacity','usize'),('caller',"&'static SwiftFrame"),('index','usize'),('borrowed','Option<&\'static Type>'),('ty','Option<Type>'),('value','Value'),('controls','usize'),('function_control','Control'),('guard','EntryGuard'),('guard_pin_take','SwiftFunctionPin'),('frame','SwiftFrame')],
'add_live':[('self',REF),('resource','Live'),('result','Result<(), SwiftRunFailure>')],
'remove_live':[('self',REF),('resource','Live'),('amount','usize'),('result','bool')],
'release':[('self',REF),('pin','SwiftFunctionPin'),('function','u32'),('result','Result<(), SwiftReleaseFailure>')],
'rollback_entry':[('self',REF),('pre_values_len','usize'),('pre_controls_len','usize'),('values','Option<usize>'),('controls','Option<usize>'),('value_delta','usize'),('control_delta','usize')],
'retire_entry':[('self',REF),('pin','Option<SwiftFunctionPin>'),('actual_pin','SwiftFunctionPin'),('rejected','SwiftReleaseFailure'),('failure','SwiftRunFailure'),('guard',"&'static EntryGuard")],
'finish':[('self',REF),('result','Result<FrameReturn, SwiftRunFailure>')],
'finish_inner':[('self',REF),('result','bool'),('saved','Option<Value>'),('frame_borrow',"&'static SwiftFrame"),('base','usize'),('controls','usize'),('values_removed','usize'),('controls_removed','usize'),('work','usize'),('n','usize'),('frame','SwiftFrame'),('function','u32'),('pc','usize'),('operands','usize'),('pin','SwiftFunctionPin'),('rejected','SwiftReleaseFailure'),('failure','SwiftRunFailure'),('returned_pin','SwiftFunctionPin'),('restored_frame','SwiftFrame'),('value','Value'),('pushed','Result<(), SwiftRunFailure>'),('returned','FrameReturn')],
'restore_nested':[('self',REF),('bound','usize')],
'report':[('self',REF),('first_failure','Option<SwiftRunFailure>'),('usage','SwiftRunUsage'),('report','FrameDrainReport')],
'drain':[('self',REF),('live','SwiftLiveUsage'),('values','usize'),('controls','usize'),('index','usize'),('frame','SwiftFrame'),('function','u32'),('pc','usize'),('base','usize'),('operands','usize'),('frame_controls','usize'),('result','bool'),('pin','SwiftFunctionPin'),('rejected','SwiftReleaseFailure'),('failure','SwiftRunFailure'),('returned_pin','SwiftFunctionPin'),('restored_frame','SwiftFrame')],
'complete':[('self',"FrameOperationPhase<'static>"),('storage',"FrameOperationStorage<'static>"),('phase',"ExecutionOperationPhase<'static>"),('cleanup',"&'static mut FrameCleanupState"),('lifecycle',"&'static mut Lifecycle"),('parts',"ExecutionParts<'static, SwiftMode>"),('operation',"SwiftExecutionOperation<'static>"),('control',"&'static mut RuntimeControl"),('wasi',"&'static mut AccountedWasi"),('live','SwiftLiveUsage'),('clean','bool'),('report','FrameDrainReport'),('bound','FrameBound'),('previous','usize'),('restored','Result<(), SwiftRunFailure>'),('drop_pair',"(ExecutionParts<'static, SwiftMode>, FrameOperationStorage<'static>)"),('completion','FrameCompletion')],
}

LOCALS['check_construction_owner']=[('control',"&'static mut RuntimeControl"),('cursor','Cursor'),('wasi','Option<WasiUsage>'),('ticket',"&'static ReservationTicket"),('violation',"Option<(SwiftCleanupInvariant, &'static str)>"),('invariant','SwiftCleanupInvariant'),('code',"&'static str"),('failure','SwiftRunFailure'),('result','Result<(), SwiftRunFailure>')]
LOCALS['terminal']=[('self',REF)]
LOCALS['function_entry']=[('end','usize'),('height','usize'),('result','bool'),('control','Control')]
LOCALS['rollback_entry'] += [('acquired_values','usize'),('acquired_controls','usize')]
LOCALS['enter_inner'] += [('local_work','usize')]

def split_top(text):
 result=[];last=0;level=0
 for i,c in enumerate(text):
  if c in '<([{':level+=1
  elif c in '>)]}':level-=1
  elif c==',' and level==0:result.append(text[last:i].strip());last=i+1
 result.append(text[last:].strip())
 return [v for v in result if v]

def functions(text):
 for match in re.finditer(r'^fn ([^\n]+)',text,re.M):
  start=match.start();end=text.find('\n}',start)+2
  header=match.group(1)
  # All selected declarations are printed on one line by stable emit=mir.
  at=header.index('(');depth=1;i=at+1
  while depth:
   depth+=(header[i]=='(')-(header[i]==')');i+=1
  name=header[:at]
  params=header[at+1:i-1]
  body=text[start:end]
  yield name,params,body,text.count('\n',0,start)+1

def selected(name):
 if '::tests::' in name:return None
 if name=='original_owners':return ('original_owners','permanent')
 if name.split('::{closure#')[0].split('::')[-1] in UNIT_HOOKS:return (name.split('::{closure#')[0].split('::')[-1],'permanent')
 method=name.split('::')[-1]
 parent=name.split('::{closure#')[0]
 leaf=parent.split('::')[-1]
 if 'frame_operations::' in name:
  if leaf in LOCALS:return (leaf,'permanent' if leaf in ['original_owners','prepare_frames','resume_frame_cleanup','complete','check_construction_owner'] else 'active')
  if leaf in ['is_empty','empty','default']:return (leaf,'permanent')
 if leaf in ['prepare_value_operation','cleanup_owned','matches_layout','check_construction_owner']:return (leaf,'permanent')
 # Private Kind field-constant spills inside the frozen constructor are not
 # authored source bindings. Keep constructor args/whole Control roles above.
 if leaf=='function_entry':return None
 if name=='primitive_push':return ('primitive_push','permanent')
 return None

def typed_rows(path,config):
 text=path.read_text(); result=[];closure_types={}; selected_functions=[]
 # Infer anonymous closure payloads from the actual MIR capture operands. The
 # source closure positions remain separate from every argument/local copy.
 for name,params,body,line in functions(text):
  selection=selected(name)
  if not selection:continue
  decl={i:ty for i,ty in re.findall(r'let (?:mut )?(_\d+): ([^\n]+);',body)}
  for arg in split_top(params):
   ident,ty=arg.split(': ',1);decl[ident]=ty
  for m in re.finditer(r'(\{closure@[^}]+\})\s*\{([^}]*)\}',body):
   captures=[]
   for capture in split_top(m.group(2)):
    if not capture:continue
    operand=re.search(r'(?:move|copy) (_\d+)',capture)
    if not operand:raise AssertionError(('unresolved capture',capture))
    captures.append(decl[operand.group(1)])
   closure_types[m.group(1)]='('+', '.join(captures)+(',' if len(captures)==1 else '')+')'
  selected_functions.append((name,params,body,line,selection,decl))
 def normalize(ty):
  def closure(m):
   site=m.group(0)
   if site in closure_types:return closure_types[site]
   # A closure with no source capture projection is zero-capture. Prove its
   # own MIR body never projects a captured field before selecting ().
   bodies=[b for n,p,b,l,x,d in selected_functions if site in p]
   if not bodies or any(re.search(r'_1\.\d+:',b) for b in bodies):raise AssertionError(('unknown closure',site))
   return '()'
  ty=re.sub(r'\{closure@[^}]+\}',closure,ty)
  ty=ty.replace("'_","'static")
  ty=re.sub(r'(?<!:)\bCell\b','std::cell::Cell',ty)
  ty=re.sub(r'(?<!:)\bRefCell\b','std::cell::RefCell',ty)
  ty=re.sub(r'\bexperimental_swift_reactor::','crate::experimental_swift_reactor::',ty)
  ty=re.sub(r'\bexperimental_wasi::','crate::experimental_wasi::',ty)
  ty=re.sub(r'(?<!:)\bexperimental::','crate::experimental::',ty)
  ty=re.sub(r'(?<!:)\bcontrol::','crate::experimental_swift_reactor::control::',ty)
  ty=re.sub(r'(?<!:)\baccounted::','crate::experimental_wasi::accounted::',ty)
  ty=re.sub(r'(?<!:)\bdescriptors::','crate::experimental::descriptors::',ty)
  ty=re.sub(r'(?<!:)\bexecute::','crate::execute::',ty)
  ty=re.sub(r'&(?!(?:\'|\s*\'))',"&'static ",ty)
  if ty=='!':ty='Infallible'
  return ty
 for ordinal,(name,params,body,line,(window,env),decl) in enumerate(selected_functions):
  debug={}
  for source,ident in re.findall(r'debug ([\w_]+) => (_\d+);',body):debug.setdefault(ident,[]).append(source)
  for ident,ty in decl.items():
   rust=normalize(ty)
   for position in ['source','argument','returned','caller']:
    result.append(dict(envelope=env,window=window,binding=ident,position=position,rustType=rust,
      sourceNames=debug.get(ident,[]),mirFunction=name,mirLine=line,mirType=ty,config=config,
      field=f'mir_{config}_{ordinal}_{ident[1:]}_{position}'))
 return result

UNIT_HOOKS={
'before_cache_completion': [('phase',"&'static mut CacheOperationPhase<'static>"),('reject','bool'),('old_bound','usize')],
'before_local': [('control',"&'static RuntimeControl"),('index','usize'),('reject','bool'),('cancellation','crate::Cancellation')],
'before_predebit': [('control',"&'static mut RuntimeControl"),('resource','Live'),('selected','bool'),('hooks','tests::Hooks'),('ordinal','usize'),('live','SwiftLiveUsage'),('limit','usize'),('returned','Option<usize>')],
'after_predebit': [('control',"&'static mut RuntimeControl"),('resource','Live'),('old','Option<usize>'),('restored','usize')],
'before_release': [('cache',"&'static mut SwiftFunctionCache"),('function','u32'),('hooks','tests::Hooks'),('ordinal','usize'),('reject','bool'),('foreign','ReservationTicket'),('original','Option<ReservationTicket>'),('refmut',"std::cell::RefMut<'static, Option<ReservationTicket>>"),('capture_original','(Option<ReservationTicket>,)')],
'after_release': [('cache',"&'static mut SwiftFunctionCache"),('original','ReservationTicket'),('foreign','Option<ReservationTicket>'),('refmut',"std::cell::RefMut<'static, Option<ReservationTicket>>"),('capture_foreign','(Option<ReservationTicket>,)')],
'outer_restore_target': [('previous','usize'),('reject','bool'),('returned','usize')],
'before_result_push': [('control',"&'static mut RuntimeControl"),('hooks','tests::Hooks'),('old','Option<(u8,u64)>'),('work','u64'),('live','usize')],
'after_result_push': [('control',"&'static mut RuntimeControl"),('old','Option<(u8,u64)>'),('kind','u8'),('work','u64'),('live','usize')],
'observed_push_capacity': [('capacity','usize'),('length','usize'),('hooks','tests::Hooks'),('reject','bool'),('returned','usize')],
'resource_code': [('resource','Live'),('returned','u8')],
'test_replace_live_limit': [('control',"&'static mut RuntimeControl"),('resource','Live'),('ceiling','usize'),('destination',"&'static mut usize"),('old','usize')],
 'test_replace_execution_work_limit': [('control',"&'static mut RuntimeControl"),('ceiling','u64'),('old','u64')],
 'test_replace_construction': [('control',"&'static mut RuntimeControl"),('ticket','Option<ReservationTicket>'),('old','Option<ReservationTicket>')],
 'replace_header': [('cache',"&'static mut SwiftFunctionCache"),('ticket','Option<ReservationTicket>'),('old','Option<ReservationTicket>')],
 'replace_operation_restore_bound': [('phase',"&'static mut CacheOperationPhase<'static>"),('bound','usize'),('old','usize')],
}
UNIT_HOOKS['observed_push_capacity_wrapper']=[('capacity','usize'),('length','usize'),('returned','usize')]
def rows():
 result=[]
 for window,bindings in UNIT_HOOKS.items():
  for binding,ty in bindings:
   for position in ['source','argument','returned','caller']:
    result.append(dict(envelope='permanent',window=window,binding=binding,position=position,rustType=ty,sourceNames=[binding],config='unit',field=f'unit_hook_{window}_{binding}_{position}'))
 # Source-local aliases/argument/return roles remain separately positive where
 # compiler lowering elides or merges them. Exact MIR roles never replace them.
 for window,locals in LOCALS.items():
  env='permanent' if window in ['original_owners','prepare_frames','resume_frame_cleanup','complete','check_construction_owner'] else 'active'
  for binding,ty in locals:
   for position in ['source','argument','returned','caller']:
    result.append(dict(envelope=env,window=window,binding=binding,position=position,rustType=ty,sourceNames=[binding],config='source',field=f'source_{window}_{binding}_{position}'))
 # Original preflight has four newly authored caller edges; all copies are
 # permanent, including value/consuming-cleanup before frame admission.
 for caller in ['prepare_frames','resume_frame_cleanup','prepare_value_operation','cleanup_owned']:
  for binding,ty in LOCALS['original_owners']:
   for position in ['source','argument','returned','caller']:
    result.append(dict(envelope='permanent',window=caller,binding=binding,position=position,rustType=ty,sourceNames=['original_owners caller '+caller],config='source',field=f'owner_edge_{caller}_{binding}_{position}'))
 for config in ['production','unit']:result+=typed_rows(Path(__file__).parent/(config+'.mir'),config)
 return result

def render():
 result=[]
 for env,cls in [('permanent','ImplementationPermanentPositions'),('active','ImplementationActivePositions')]:
  result.append('struct '+cls+' {')
  for row in rows():
   if row['envelope']!=env:continue
   if row['config']=='unit':result.append('    #[cfg(test)]')
   result.append('    '+row['field']+': '+row['rustType']+',')
  result.append('}')
 return '\n'.join(result)
if __name__=='__main__':
 out=ROOT/'vm/src/experimental_swift_reactor/frame_operations.rs'
 text=out.read_text().split('// ACCOUNTING_GENERATED_START')[0]
 accepted=frozen.render().replace('pub(super) const PERMANENT_BYTES:', 'pub(super) const FROZEN_PERMANENT_BYTES:').replace('pub(super) const ACTIVE_BYTES:', 'pub(super) const FROZEN_ACTIVE_BYTES:')
 text+='// ACCOUNTING_GENERATED_START\n'+accepted+'\n'+render()+'''
/// Frozen declarations remain fully occupied; actual implementation positions
/// are fresh positive additions, never alternate aliases or subtraction.
pub(super) const PERMANENT_BYTES: usize = FROZEN_PERMANENT_BYTES + size_of::<ImplementationPermanentPositions>();
pub(super) const ACTIVE_BYTES: usize = FROZEN_ACTIVE_BYTES + size_of::<ImplementationActivePositions>();
pub(super) const FRAME_OPERATION_BYTES: Option<usize> = match value_operations::VALUE_OPERATION_BYTES {
    Some(nested) => ACTIVE_BYTES.checked_add(nested), None => None,
};
'''
 out.write_text(text)
 (Path(__file__).parent/'implementation-inventory-schema.json').write_text(json.dumps(rows(),sort_keys=True,indent=2)+'\n')
 (Path(__file__).parent/'frozen-inventory-schema.json').write_text(json.dumps(frozen.rows(),sort_keys=True,indent=2)+'\n')
 print('exact supplemental typed fields',len(rows()))
