from run import *
import shutil
schema=json.loads((PACKET/'inventory-schema.json').read_text());recorded=json.loads((PACKET/'layouts.json').read_text())
results=[]
for label in['baseline','candidate']:
 vm=SCRATCH/('layout-'+label)
 if not vm.exists():
  shutil.copytree(SCRATCH/label,vm)
  p=vm/'src/experimental_swift_reactor/frame_operations.rs'
  code=['pub(crate) fn review_metadata(){']
  types={'State':'SwiftExecutionState','Instance':'SwiftReactorInstance','SwiftFrame':'SwiftFrame','Control':'Control','Phase':"FrameOperationPhase<'static>",'ExecutionPhase':"ExecutionOperationPhase<'static>",'Storage':"FrameOperationStorage<'static>",'DropTuple':"(ExecutionParts<'static, SwiftMode>, FrameOperationStorage<'static>)",'Preparation':"Option<Result<FrameOperationPhase<'static>, SwiftRunFailure>>",'MemoryResult':'Result<(), SwiftRunFailure>','MemorySlot':'Option<Result<(), SwiftRunFailure>>','Failure':'SwiftRunFailure','Cursor':'Cursor','Operation':'Operation','Instruction':'DecodedInstruction','Value':'Value','FrameCleanupState':'FrameCleanupState','RuntimeControl':'RuntimeControl','Cache':'SwiftFunctionCache','Pin':'SwiftFunctionPin','Wasi':'AccountedWasi','Ticket':'ReservationTicket','FramePermanent':'PermanentPositions','FrameActive':'ActivePositions','FrameImplementationPermanent':'ImplementationPermanentPositions','FrameImplementationActive':'ImplementationActivePositions'}
  for name,ty in types.items():code.append(f'println!("RV_TYPE {name} {{}} {{}}",size_of::<{ty}>(),std::mem::align_of::<{ty}>());')
  for ty,fields in{'SwiftExecutionState':['memory','table','globals','values','controls','frames','buffers','execution_header','frame_cleanup'],'SwiftReactorInstance':['control','cache','wasi','state','lifecycle'],'SwiftFrame':['function','pc','base','operands','controls','result','pin'],"FrameOperationPhase<'static>":['phase','cleanup','lifecycle'],"ExecutionOperationPhase<'static>":['parts','operation','previous_bound'],"FrameOperationStorage<'static>":['preparation','entry','returned','drained','controlled'],'FrameCleanupState':['disposition','bound','unvisited','nested_restore','live_unreconciled','entry_attempted','entry']}.items():
   for field in fields:code.append(f'println!("RV_OWNER {ty}.{field} {{}}",std::mem::offset_of!({ty},{field}));')
  for name,expr in{'header':'execution_header_bytes().unwrap()','construction':'construction_bytes().unwrap()','frame':'FRAME_OPERATION_BYTES.unwrap()','frame_permanent':'PERMANENT_BYTES','frame_active':'ACTIVE_BYTES','control_permanent':'control_operations::PERMANENT_BYTES','control_active':'control_operations::ACTIVE_BYTES','value':'value_operations::VALUE_OPERATION_BYTES.unwrap()','accepted_memory_permanent':'memory_operations::PERMANENT_BYTES','accepted_memory_active':'memory_operations::ACTIVE_BYTES','state_limit':'SwiftRunBudget::default().state_bytes','combined_limit':'SwiftRunBudget::default().combined_bytes'}.items():code.append(f'println!("RV_TOTAL {name} {{}}",{expr});')
  if label=='candidate':code.append('bulk_memory_operations::review_metadata();')
  code+=['crate::experimental::execution::review_frozen_metadata();','}','#[cfg(test)] #[test] fn review_layout_only(){review_metadata();}'];p.write_text(p.read_text()+'\n'+'\n'.join(code)+'\n')
  p=vm/'src/experimental/execution/mod.rs';p.write_text(p.read_text()+'''\npub(crate) fn review_frozen_metadata(){
 println!("RV_TOTAL frozen_header {}",size_of::<SpanInstance>()-size_of::<FunctionCache>()+3*size_of::<ExecutionFailure>()+2*size_of::<CacheFailure>()+size_of::<super::cache::DecodedInstruction>()+size_of::<Control>()+size_of::<ScalarReader<'_>>()+512);
 println!("RV_TYPE FrozenOwner {} {}",size_of::<SpanInstance>(),std::mem::align_of::<SpanInstance>());
 println!("RV_TYPE FrozenFrame {} {}",size_of::<Frame>(),std::mem::align_of::<Frame>());
 println!("RV_TYPE FrozenControl {} {}",size_of::<Control>(),std::mem::align_of::<Control>());
 }\n''')
  if label=='candidate':
   p=vm/'src/experimental_swift_reactor/bulk_memory_operations.rs';code=['pub(super) fn review_metadata(){']
   for cls in['PermanentPositions','ActivePositions']:code.append(f'println!("RV_CLASS {cls} {{}} {{}}",size_of::<{cls}>(),std::mem::align_of::<{cls}>());')
   for r in schema:code.append(('#[cfg(test)] 'if r['config']=='unit'else'')+f'println!("RV_FIELD {r["field"]} {{}} {{}} {{}}",std::mem::offset_of!({r["ownerClass"]},{r["field"]}),size_of::<{r["rustType"]}>(),std::mem::align_of::<{r["rustType"]}>());')
   code+=['println!("RV_TOTAL bulk_permanent {}",PERMANENT_BYTES);','println!("RV_TOTAL bulk_active {}",ACTIVE_BYTES);','}'];p.write_text(p.read_text()+'\n'+'\n'.join(code)+'\n')
  p=vm/'src/experimental_swift_reactor/mod.rs';p.write_text(p.read_text()+'\npub(crate) fn review_metadata(){execution::frame_operations::review_metadata();}\n')
  p=vm/'src/lib.rs';p.write_text(p.read_text()+'\npub fn review_metadata(){experimental_swift_reactor::review_metadata();}\n')
  p=vm/'src/bin/review_layout.rs';p.parent.mkdir(exist_ok=True);p.write_text('fn main(){mixer_vm::review_metadata();}\n')
  (HERE/('layout-'+label+'-source-manifest.json')).write_bytes(enc(manifest(vm)))
  with tarfile.open(HERE/('layout-'+label+'-source.tar.gz'),'w:gz')as tar:
   for name in manifest(vm):tar.add(vm/name,arcname=name)
 for unit in[False,True]:
  name='fresh-layout-'+label+('-unit'if unit else'-production')
  args=['cargo','test','--lib','--locked','--offline','--all-features','--release','review_layout_only','--','--nocapture','--test-threads=1']if unit else['cargo','run','--locked','--offline','--all-features','--release','--bin','review_layout']
  if (HERE/'commands'/name/'receipt.json').exists():
   text=(HERE/'commands'/name/'stdout').read_text()
  else:
   p=run(name,args,vm,{'CARGO_TARGET_DIR':str(SCRATCH/'target-layout')});assert p.returncode==0;text=p.stdout.decode()
  data={k:{}for k in['types','owners','classes','fields','totals']}
  for line in text.splitlines():
   at=line.find('RV_')
   if at<0:continue
   tag,key,*values=line[at:].split();v=list(map(int,values));target={'RV_TYPE':'types','RV_OWNER':'owners','RV_CLASS':'classes','RV_FIELD':'fields','RV_TOTAL':'totals'}[tag];assert key not in data[target]
   data[target][key]=dict(bytes=v[0],alignment=v[1])if target in['types','classes']else dict(offset=v[0],bytes=v[1],alignment=v[2])if target=='fields'else v[0]
  prior=next(r for r in recorded if r['label']==label and r['features']=='all'and r['profile']=='release'and r['unit']==unit)
  assert all(data[k]==prior[k]for k in data),label
  if label=='candidate':
   selected=[r for r in schema if unit or r['config']!='unit'];assert set(data['fields'])=={r['field']for r in selected};ends={}
   for row in sorted(selected,key=lambda r:(r['ownerClass'],data['fields'][r['field']]['offset'])):
    field=data['fields'][row['field']];cls=row['ownerClass'];assert field['bytes']>=0 and field['offset']%field['alignment']==0 and field['offset']>=ends.get(cls,0);ends[cls]=field['offset']+field['bytes'];assert ends[cls]<=data['classes'][cls]['bytes']
  results.append(dict(label=label,features='all',profile='release',unit=unit,**data));(HERE/'layout-results.json').write_bytes(enc(results))
print('PASS four fresh all-feature Release typed layout probes exact to sealed evidence')
