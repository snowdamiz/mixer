#!/usr/bin/env python3
"""Actual target layout probes, isolated from candidate compiler-MIR source."""
from pathlib import Path
import json,shutil,sys
STAGE=sys.argv[1] if len(sys.argv)>1 else ""
from run import run,SCRATCH,HERE,enc
SCHEMA=json.loads((HERE/'inventory-schema.json').read_text())
TYPES={
 'GrowthTransfer':'GrowthTransfer','State':'SwiftExecutionState','Instance':'SwiftReactorInstance','SwiftFrame':'SwiftFrame','Control':'Control','Phase':"FrameOperationPhase<'static>",'ExecutionPhase':"ExecutionOperationPhase<'static>",'Storage':"FrameOperationStorage<'static>",'DropTuple':"(ExecutionParts<'static, SwiftMode>, FrameOperationStorage<'static>)",'Preparation':"Option<Result<FrameOperationPhase<'static>, SwiftRunFailure>>",'MemoryResult':'Result<(), SwiftRunFailure>','MemorySlot':'Option<Result<(), SwiftRunFailure>>','Failure':'SwiftRunFailure','Cursor':'Cursor','Operation':'Operation','Instruction':'DecodedInstruction','Value':'Value','FrameCleanupState':'FrameCleanupState','RuntimeControl':'RuntimeControl','Cache':'SwiftFunctionCache','Pin':'SwiftFunctionPin','Wasi':'AccountedWasi','Ticket':'ReservationTicket','FramePermanent':'PermanentPositions','FrameActive':'ActivePositions','FrameImplementationPermanent':'ImplementationPermanentPositions','FrameImplementationActive':'ImplementationActivePositions',
}
FIELDS={
'GrowthTransfer':['replacement','ticket','old','old_ticket','old_pages','next_pages','copied'],
'SwiftExecutionState':['memory','table','globals','values','controls','frames','buffers','execution_header','frame_cleanup'],
'SwiftReactorInstance':['control','cache','wasi','state','lifecycle'],
'SwiftFrame':['function','pc','base','operands','controls','result','pin'],
"FrameOperationPhase<'static>":['phase','cleanup','lifecycle'],
"ExecutionOperationPhase<'static>":['parts','operation','previous_bound'],
"FrameOperationStorage<'static>":['preparation','entry','returned','drained','controlled'],
'FrameCleanupState':['disposition','bound','unvisited','nested_restore','live_unreconciled','entry_attempted','entry'],
}
def setup(label):
 vm=SCRATCH/('metadata-'+label+('-'+STAGE if STAGE else ''));assert not vm.exists();shutil.copytree(SCRATCH/label/'vm',vm)
 frame=vm/'src/experimental_swift_reactor/frame_operations.rs';code=['pub(crate) fn growth_contract_metadata(){']
 for name,ty in TYPES.items():code.append(f'println!("MG_TYPE {name} {{}} {{}}",size_of::<{ty}>(),std::mem::align_of::<{ty}>());')
 for ty,fields in FIELDS.items():
  for field in fields:code.append(f'println!("MG_OWNER {ty}.{field} {{}}",std::mem::offset_of!({ty},{field}));')
 for name,expression in {'header':'execution_header_bytes().unwrap()','construction':'construction_bytes().unwrap()','frame':'FRAME_OPERATION_BYTES.unwrap()','frame_permanent':'PERMANENT_BYTES','frame_active':'ACTIVE_BYTES','control_permanent':'control_operations::PERMANENT_BYTES','control_active':'control_operations::ACTIVE_BYTES','value':'value_operations::VALUE_OPERATION_BYTES.unwrap()','accepted_memory_permanent':'memory_operations::PERMANENT_BYTES','accepted_memory_active':'memory_operations::ACTIVE_BYTES','accepted_bulk_permanent':'bulk_memory_operations::PERMANENT_BYTES','accepted_bulk_active':'bulk_memory_operations::ACTIVE_BYTES','state_limit':'SwiftRunBudget::default().state_bytes','combined_limit':'SwiftRunBudget::default().combined_bytes'}.items():code.append(f'println!("MG_TOTAL {name} {{}}",{expression});')
 code+=['#[cfg(feature="experimental-span-execution")] crate::experimental::execution::memory_frozen_metadata();']
 if label=='candidate':code+=['memory_growth_operations::growth_metadata();']
 code+=['}','#[cfg(test)] #[test] fn growth_contract_metadata_only(){growth_contract_metadata();}']
 frame.write_text(frame.read_text()+'\n'+'\n'.join(code)+'\n')
 if label=='candidate':
  p=vm/'src/experimental_swift_reactor/memory_growth_operations.rs';code=['pub(super) fn growth_metadata(){']
  for name,ty in {'Context':"SwiftGrowthContext<'static>",'Storage':'SwiftGrowthStorage','Execution':"SwiftGrowthExecution<'static,'static>",'Completion':"GrowthCompletion<'static>",'Preparation':"Option<Result<(FrameOperationPhase<'static>,SwiftGrowthContext<'static>),SwiftRunFailure>>"}.items():code.append(f'println!("MG_NEWTYPE {name} {{}} {{}}",size_of::<{ty}>(),std::mem::align_of::<{ty}>());')
  for ty,fields in {"SwiftGrowthContext<'static>":['memory_ticket'],'SwiftGrowthStorage':['transfer','pages_debited','live_unreconciled']}.items():
   for field in fields:code.append(f'println!("MG_NEWOWNER {ty}.{field} {{}}",std::mem::offset_of!({ty},{field}));')
  for cls in ['PermanentPositions','ActivePositions']:code.append(f'println!("MG_CLASS {cls} {{}} {{}}",size_of::<{cls}>(),std::mem::align_of::<{cls}>());')
  for row in SCHEMA:
   prefix='#[cfg(test)] ' if row['config']=='unit' else ''
   code.append(prefix+f'println!("MG_FIELD {row["field"]} {{}} {{}} {{}}",std::mem::offset_of!({row["ownerClass"]},{row["field"]}),size_of::<{row["rustType"]}>(),std::mem::align_of::<{row["rustType"]}>());')
  code+=['println!("MG_TOTAL growth_permanent {}",PERMANENT_BYTES);','println!("MG_TOTAL growth_active {}",ACTIVE_BYTES);','}'];p.write_text(p.read_text()+'\n'+'\n'.join(code)+'\n')
 p=vm/'src/experimental_swift_reactor/mod.rs';p.write_text(p.read_text()+'\npub(crate) fn growth_metadata_route(){execution::frame_operations::growth_contract_metadata();}\n')
 p=vm/'src/lib.rs';p.write_text(p.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn growth_metadata_route(){experimental_swift_reactor::growth_metadata_route();}\n')
 p=vm/'src/bin/growth_contract_layout.rs';p.parent.mkdir(exist_ok=True);p.write_text('fn main(){mixer_vm::growth_metadata_route();}\n')
 p=vm/'src/experimental/execution/mod.rs';p.write_text(p.read_text()+'''
#[cfg(feature="experimental-span-execution")]
pub(crate) fn memory_frozen_metadata(){
 println!("MG_TOTAL frozen_header {}",size_of::<SpanInstance>()-size_of::<FunctionCache>()+3*size_of::<ExecutionFailure>()+2*size_of::<CacheFailure>()+size_of::<super::cache::DecodedInstruction>()+size_of::<Control>()+size_of::<ScalarReader<'_>>()+512);
 println!("MG_TYPE FrozenOwner {} {}",size_of::<SpanInstance>(),std::mem::align_of::<SpanInstance>());
 println!("MG_TYPE FrozenFrame {} {}",size_of::<Frame>(),std::mem::align_of::<Frame>());
 println!("MG_TYPE FrozenControl {} {}",size_of::<Control>(),std::mem::align_of::<Control>());
}
''')
 return vm

def parse(text):
 result={k:{} for k in ['types','classes','fields','totals','owners','newTypes','newOwners']}
 for line in text.splitlines():
  at=line.find('MG_')
  if at<0:continue
  kind,name,*values=line[at:].split();values=list(map(int,values))
  target={'MG_TYPE':'types','MG_CLASS':'classes','MG_FIELD':'fields','MG_TOTAL':'totals','MG_OWNER':'owners','MG_NEWTYPE':'newTypes','MG_NEWOWNER':'newOwners'}[kind]
  assert name not in result[target],name
  result[target][name]=dict(bytes=values[0],alignment=values[1]) if target in ['types','classes','newTypes'] else dict(offset=values[0],bytes=values[1],alignment=values[2]) if target=='fields' else values[0]
 return result

def main():
 layouts=[] if STAGE in ['binary','qualified'] else [x for x in json.loads((HERE/'layouts.json').read_text()) if x['label']=='baseline'] if STAGE else []
 for label in (['candidate'] if STAGE and STAGE not in ['binary','qualified'] else ['baseline','candidate']):
  vm=setup(label)
  for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
   for release in [False,True]:
    for unit in [False,True]:
     name=('layout-'+STAGE+'-' if STAGE else 'layout-')+label+'-'+config+('-release' if release else '-debug')+('-unit' if unit else '-production')
     args=['cargo','test','--lib','--locked','--offline',*flags,*(['--release'] if release else []),'growth_contract_metadata_only','--','--nocapture','--test-threads=1'] if unit else ['cargo','run','--locked','--offline','--bin','growth_contract_layout',*flags,*(['--release'] if release else [])]
     p=run(name,args,vm);assert p.returncode==0
     layout=parse(p.stdout.decode());layout.update(label=label,features=config,profile='release' if release else 'debug',unit=unit)
     if label=='candidate':
      expected={r['field'] for r in SCHEMA if unit or r['config']!='unit'};assert set(layout['fields'])==expected
      seen={}
      for row in sorted((r for r in SCHEMA if unit or r['config']!='unit'),key=lambda r:(r['ownerClass'],layout['fields'][r['field']]['offset'])):
       v=layout['fields'][row['field']];cls=row['ownerClass'];assert v['bytes']==0 or v['offset']>=seen.get(cls,0);assert v['offset']%v['alignment']==0;seen[cls]=max(seen.get(cls,0),v['offset']+v['bytes']);assert seen[cls]<=layout['classes'][cls]['bytes']
      old=next(v for v in layouts if (v['label'],v['features'],v['profile'],v['unit'])==('baseline',config,layout['profile'],unit))
      assert layout['types']==old['types']
      assert layout['owners']==old['owners']
      for k in ['construction','frame_permanent','frame_active','control_permanent','control_active','value','state_limit','combined_limit','accepted_memory_permanent','accepted_memory_active','accepted_bulk_permanent','accepted_bulk_active']:assert layout['totals'][k]==old['totals'][k]
      assert layout['totals']['header']==old['totals']['header']+layout['totals']['growth_permanent']
      assert layout['totals']['frame']==old['totals']['frame']+layout['totals']['growth_active']
      assert layout['totals']['frame'] == layout['totals']['frame_active']+layout['totals']['value']+layout['totals']['control_active']+layout['totals']['accepted_memory_active']+layout['totals']['accepted_bulk_active']+layout['totals']['growth_active']
     if config=='all':assert layout['totals']['frozen_header']==2912
     layouts.append(layout);(HERE/'layouts.json').write_bytes(enc(layouts))
 print('16 exact metadata layouts; original owner shapes/offsets unchanged; positive containing bounds',flush=True)
if __name__=='__main__':main()
