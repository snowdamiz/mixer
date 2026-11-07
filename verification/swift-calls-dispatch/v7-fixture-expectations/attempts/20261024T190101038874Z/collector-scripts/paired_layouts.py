"""16 separate metadata-only actual formula/owner layouts in disposable overlays.
The probe only prints sizes, offsets and reservation formulas. It never constructs
an execution owner, validates Wasm, enters a frame or invokes the interpreter.
"""
import collect as c
from pathlib import Path
import json,shutil,tempfile,subprocess,sys,gzip,re
TOTALS={'header':'execution_header_bytes().unwrap()','frame':'FRAME_OPERATION_BYTES.unwrap()','frame_permanent':'PERMANENT_BYTES','frame_active':'ACTIVE_BYTES','frame_frozen_permanent':'FROZEN_PERMANENT_BYTES','frame_frozen_active':'FROZEN_ACTIVE_BYTES','value':'value_operations::VALUE_OPERATION_BYTES.unwrap()','control_permanent':'control_operations::PERMANENT_BYTES','control_active':'control_operations::ACTIVE_BYTES','memory_permanent':'memory_operations::PERMANENT_BYTES','memory_active':'memory_operations::ACTIVE_BYTES','bulk_permanent':'bulk_memory_operations::PERMANENT_BYTES','bulk_active':'bulk_memory_operations::ACTIVE_BYTES','growth_permanent':'memory_growth_operations::PERMANENT_BYTES','growth_active':'memory_growth_operations::ACTIVE_BYTES','host_permanent':'host_runtime_import::PERMANENT_BYTES','host_active':'host_runtime_import::ACTIVE_BYTES','ticket_max':'MAX_RESERVATION_TICKETS','state_limit':'SwiftRunBudget::default().state_bytes','combined_limit':'SwiftRunBudget::default().combined_bytes'}
OWNERS={'SwiftExecutionState':['memory','table','globals','values','controls','frames','buffers','execution_header','frame_cleanup'],'SwiftReactorInstance':['control','cache','wasi','state','lifecycle'],'SwiftFrame':['function','pc','base','operands','controls','result','pin'],"FrameOperationPhase<'static>":['phase','cleanup','lifecycle'],"ExecutionOperationPhase<'static>":['parts','operation','previous_bound'],"FrameOperationStorage<'static>":['preparation','entry','returned','drained','controlled'],'FrameCleanupState':['disposition','bound','unvisited','nested_restore','live_unreconciled','entry_attempted','entry']}
def execute(label,features,profile,unit,scratch,state):
 name=f'{label}-{features}-{profile}-'+('unit'if unit else'production');tree=scratch/'crate';base=c.HERE/label;shutil.copytree(base,tree);source=c.manifest(base);assert c.manifest(tree)==source
 frame=tree/'src/experimental_swift_reactor/frame_operations.rs';body=['pub(crate) fn calls_layout_metadata() {']
 for k,e in TOTALS.items():body.append(f'println!("CL_TOTAL {k} {{}}",{e});')
 for ty,fields in OWNERS.items():
  body.append(f'println!("CL_TYPE {ty} {{}} {{}}",size_of::<{ty}>(),std::mem::align_of::<{ty}>());')
  for field in fields:body.append(f'println!("CL_OWNER {ty}.{field} {{}}",std::mem::offset_of!({ty},{field}));')
 if label=='candidate':body+=['println!("CL_TOTAL calls_active {}",call_dispatch::ACTIVE_BYTES.unwrap());', 'println!("CL_TOTAL calls_permanent {}",CALLS_PERMANENT_BYTES.unwrap());', 'println!("CL_TOTAL calls_typed_active {}",size_of::<call_dispatch::CallsActivePositions>());', 'println!("CL_TOTAL calls_typed_permanent {}",size_of::<call_dispatch::CallsPermanentPositions>());', 'println!("CL_TOTAL calls_kind_active {}",crate::experimental::execution::borrowed::calls_kind_accounting::ACTIVE_BYTES);', 'println!("CL_TOTAL calls_kind_permanent {}",crate::experimental::execution::borrowed::calls_kind_accounting::PERMANENT_BYTES);', 'println!("CL_TOTAL calls_never_active {}",call_dispatch::NEVER_ACTIVE_BYTES);', 'println!("CL_TOTAL calls_never_permanent {}",call_dispatch::NEVER_PERMANENT_BYTES);', 'println!("CL_TOTAL calls_numeric_active {}",call_dispatch::NUMERIC_ACTIVE_PRODUCTION_BYTES+call_dispatch::NUMERIC_ACTIVE_UNIT_BYTES);', 'println!("CL_TOTAL calls_numeric_permanent {}",call_dispatch::NUMERIC_PERMANENT_PRODUCTION_BYTES+call_dispatch::NUMERIC_PERMANENT_UNIT_BYTES);']
 body+=['}','#[cfg(test)] #[test] fn calls_layout_only_metadata(){ calls_layout_metadata(); }'];frame.write_text(frame.read_text()+'\n'+'\n'.join(body)+'\n')
 p=tree/'src/experimental_swift_reactor/mod.rs';p.write_text(p.read_text()+'\npub(crate) fn calls_layout_route(){execution::frame_operations::calls_layout_metadata();}\n')
 p=tree/'src/lib.rs';p.write_text(p.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn calls_layout_metadata_only(){experimental_swift_reactor::calls_layout_route();}\n')
 p=tree/'src/bin/calls_layout.rs';p.parent.mkdir(exist_ok=True);p.write_text('fn main(){mixer_vm::calls_layout_metadata_only();}\n')
 projection={}
 for rel,digest in source.items():
  before=(base/rel).read_bytes();after=(tree/rel).read_bytes();assert after.startswith(before),rel
  if after!=before:projection[rel]={'prefixBytes':len(before),'originalSHA256':digest,'appendedSHA256':c.sha(after[len(before):])}
 assert set(projection)=={'src/experimental_swift_reactor/frame_operations.rs','src/experimental_swift_reactor/mod.rs','src/lib.rs'}
 assert set(c.manifest(tree))-set(source)=={'src/bin/calls_layout.rs'}
 flags=['--no-default-features']+(['--features','experimental-swift-reactor']if features=='swift'else['--all-features'])+(['--release']if profile=='release'else[])
 if unit:argv=['cargo','test','--lib','--no-run','--locked','--offline',*flags,'--message-format=json-render-diagnostics'];post={'target':'mixer_vm','prefixes':['calls_layout_only_metadata'],'args':['calls_layout_only_metadata','--nocapture','--test-threads=1']}
 else:argv=['cargo','build','--bin','calls_layout','--locked','--offline',*flags,'--message-format=json-render-diagnostics'];post={'target':'calls_layout','args':[]}
 code,attempt,out,err=c.run(argv,tree=tree,label='metadata-only-paired-layout-'+name,post=post,env_extra={'RUSTC_BOOTSTRAP':'1','RUSTFLAGS':'-Zprint-type-sizes'})
 state['attempt']=attempt
 types={};current=None
 for line in (out+err).decode().splitlines():
  m=re.fullmatch(r'print-type-size type: `(.+)`: (\d+) bytes, alignment: (\d+) bytes',line)
  if m:
   current=m[1];item={'bytes':int(m[2]),'alignment':int(m[3]),'details':[]};types.setdefault(current,item)
  elif current and line.startswith('print-type-size '):types[current]['details'].append(line.removeprefix('print-type-size '))
 layoutbytes=c.enc(types);c.save(attempt/'compiler-type-layouts.json.gz',gzip.compress(layoutbytes,mtime=0))
 c.save(attempt/'source-projection.json',{'originalManifest':source,'originalClosure':c.sha(c.enc(source)),'probeManifest':c.manifest(tree),'onlyProbeAppendAndBin':True,'appends':projection,'noInterpreterExecution':True})
 parsed={k:{}for k in ['totals','types','owners']}
 if code==0:
  for line in out.decode().splitlines():
   if 'CL_'in line:
    kind,key,*vs=line[line.index('CL_'):].split();values=list(map(int,vs));target={'CL_TOTAL':'totals','CL_TYPE':'types','CL_OWNER':'owners'}[kind];assert key not in parsed[target];parsed[target][key]=values[0]if len(values)==1 else dict(bytes=values[0],alignment=values[1])
  assert len(parsed['totals'])==len(TOTALS)+(10 if label=='candidate'else 0);assert parsed['totals']['ticket_max']==86;assert parsed['totals']['state_limit']==128*1024*1024;assert parsed['totals']['combined_limit']==256*1024*1024
 c.save(c.HERE/f'paired-layout-{name}.json',{'attempt':str(attempt.relative_to(c.HERE)),'sourceClosure':c.sha(c.enc(source)),'exitCode':code,'compilerLayouts':{'path':'compiler-type-layouts.json.gz','sha256':c.sha(layoutbytes),'types':len(types)},**parsed})
 return code

def run(label,features,profile,unit):
 scratch=Path(tempfile.mkdtemp(prefix='mixer-calls-layout-overlay-'));state={}
 try:return execute(label,features,profile,unit,scratch,state)
 except BaseException as error:
  if 'attempt'in state:
   import traceback;c.save(state['attempt']/'overlay-driver-error.log',traceback.format_exc().encode())
  raise
 finally:
  holders=subprocess.run(['lsof','-nP','+D',str(scratch)],capture_output=True)
  if 'attempt'in state:c.save(state['attempt']/'overlay-holders.log',holders.stdout+holders.stderr)
  assert not holders.stdout
  shutil.rmtree(scratch)
  if 'attempt'in state:c.save(state['attempt']/'overlay-cleanup.json',{'scratch':str(scratch),'removed':not scratch.exists(),'holderCheckEmpty':True,'nativeInstancesCreated':0})
if __name__=='__main__':raise SystemExit(run(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]=='unit'))
