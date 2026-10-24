#!/usr/bin/env python3
"""Actual layout-only host execution; it never enters an interpreter or WASI."""
from pathlib import Path
import json, shutil, sys
import collect as probe
from collect import HERE, save, archive
TYPES={
 'State':'SwiftExecutionState','Instance':'SwiftReactorInstance','SwiftFrame':'SwiftFrame',
 'FramePhase':"FrameOperationPhase<'static>",'ExecutionPhase':"ExecutionOperationPhase<'static>",
 'FrameStorage':"FrameOperationStorage<'static>",'FrameCleanup':'FrameCleanupState',
 'Control':'RuntimeControl','Cache':'SwiftFunctionCache','Wasi':'AccountedWasi',
 'Ticket':'ReservationTicket','Failure':'SwiftRunFailure','WasiUsage':'WasiUsage',
 'Errno':'crate::experimental_wasi::Errno','Descriptor':'crate::experimental_wasi::WasiFunction',
 'Instruction':'DecodedInstruction','Value':'Value','Cursor':'Cursor','Usage':'SwiftRunUsage','LiveUsage':'SwiftLiveUsage',
}
FIELDS={
 'SwiftExecutionState':['memory','table','globals','values','controls','frames','buffers','execution_header','frame_cleanup'],
 'SwiftReactorInstance':['control','cache','wasi','state','lifecycle'],
 'SwiftFrame':['function','pc','base','operands','controls','result','pin'],
 "FrameOperationPhase<'static>":['phase','cleanup','lifecycle'],
 "ExecutionOperationPhase<'static>":['parts','operation','previous_bound'],
 "FrameOperationStorage<'static>":['preparation','entry','returned','drained','controlled'],
 'FrameCleanupState':['disposition','bound','unvisited','nested_restore','live_unreconciled','entry_attempted','entry'],
}
TOTALS={
 'header':'execution_header_bytes().unwrap()', 'frame':'FRAME_OPERATION_BYTES.unwrap()',
 'memory_permanent':'memory_operations::PERMANENT_BYTES','memory_active':'memory_operations::ACTIVE_BYTES',
 'bulk_permanent':'bulk_memory_operations::PERMANENT_BYTES','bulk_active':'bulk_memory_operations::ACTIVE_BYTES',
 'growth_permanent':'memory_growth_operations::PERMANENT_BYTES','growth_active':'memory_growth_operations::ACTIVE_BYTES',
 'ticket_max':'MAX_RESERVATION_TICKETS','state_limit':'SwiftRunBudget::default().state_bytes',
 'combined_limit':'SwiftRunBudget::default().combined_bytes',
}
def setup(label,schema):
    vm=probe.SCRATCH/(getattr(probe,'METADATA_PREFIX','metadata')+'-'+label);shutil.copytree(probe.SCRATCH/label,vm)
    f=vm/'src/experimental_swift_reactor/frame_operations.rs'
    if label=='candidate':
        text=f.read_text()
        if (HERE/'positive-positions.rs').read_text() not in text: text=text.replace('// CONTRACT_INVENTORY_INSERT',(HERE/'positive-positions.rs').read_text())
        body=['pub(super) fn cleanup_positions_metadata(){']
        for cls in ['DiagnosticPermanentPositions','DiagnosticValuePositions','DiagnosticFramePositions']:
            body.append(f'println!("HC_CLASS {cls} {{}} {{}}",size_of::<{cls}>(),std::mem::align_of::<{cls}>());')
        for row in schema:
            prefix='#[cfg(test)] ' if row['config']=='unit' else ''
            body.append(prefix+f'println!("HC_FIELD {row["field"]} {{}} {{}} {{}}",std::mem::offset_of!({row["ownerClass"]},{row["field"]}),size_of::<{row["rustType"]}>(),std::mem::align_of::<{row["rustType"]}>());')
        body+=['}']
        text += '\n'+'\n'.join(body)+'\n'
        f.write_text(text)
    code=['pub(crate) fn cleanup_contract_metadata(){']
    for name,ty in TYPES.items():code.append(f'println!("HC_TYPE {name} {{}} {{}}",size_of::<{ty}>(),std::mem::align_of::<{ty}>());')
    for ty,fields in FIELDS.items():
        for field in fields:code.append(f'println!("HC_OWNER {ty}.{field} {{}}",std::mem::offset_of!({ty},{field}));')
    for name,expr in TOTALS.items():code.append(f'println!("HC_TOTAL {name} {{}}",{expr});')
    if label=='candidate':
        code+=['cleanup_positions_metadata();',
          'println!("HC_TOTAL proposed_header {}",execution_header_bytes().unwrap());',
          'println!("HC_TOTAL proposed_frame {}",FRAME_OPERATION_BYTES.unwrap());']
    code+=['}','#[cfg(test)] #[test] fn cleanup_contract_layout_only(){cleanup_contract_metadata();}']
    f.write_text(f.read_text()+'\n'+'\n'.join(code)+'\n')
    p=vm/'src/experimental_swift_reactor/mod.rs';p.write_text(p.read_text()+'\npub(crate) fn cleanup_layout_route(){execution::frame_operations::cleanup_contract_metadata();}\n')
    p=vm/'src/lib.rs';p.write_text(p.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn cleanup_layout_route(){experimental_swift_reactor::cleanup_layout_route();}\n')
    p=vm/'src/bin/cleanup_contract_layout.rs';p.parent.mkdir(exist_ok=True);p.write_text('fn main(){mixer_vm::cleanup_layout_route();}\n')
    return vm
def parse(output):
    result={k:{} for k in ['types','classes','fields','totals','owners']}
    for line in output.splitlines():
        if 'HC_' not in line:continue
        kind,name,*values=line[line.index('HC_'):].split();values=list(map(int,values))
        target={'HC_TYPE':'types','HC_CLASS':'classes','HC_FIELD':'fields','HC_TOTAL':'totals','HC_OWNER':'owners'}[kind]
        assert name not in result[target],name
        result[target][name]=(dict(bytes=values[0],alignment=values[1]) if target in ['types','classes']
            else dict(offset=values[0],bytes=values[1],alignment=values[2]) if target=='fields' else values[0])
    return result
