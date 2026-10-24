#!/usr/bin/env python3
"""Actual layout-only host execution; it never enters an interpreter or WASI."""
from pathlib import Path
import json, shutil, sys
import probe
from probe import HERE, save, run, archive
TYPES={
 'State':'SwiftExecutionState','Instance':'SwiftReactorInstance','SwiftFrame':'SwiftFrame',
 'FramePhase':"FrameOperationPhase<'static>",'ExecutionPhase':"ExecutionOperationPhase<'static>",
 'FrameStorage':"FrameOperationStorage<'static>",'FrameCleanup':'FrameCleanupState',
 'Control':'RuntimeControl','Cache':'SwiftFunctionCache','Wasi':'AccountedWasi',
 'Ticket':'ReservationTicket','Failure':'SwiftRunFailure','WasiUsage':'WasiUsage',
 'Errno':'crate::experimental_wasi::Errno','Descriptor':'crate::experimental_wasi::WasiFunction',
 'Instruction':'DecodedInstruction','Value':'Value',
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
 'ticket_max':'MAX_RESERVATION_TICKETS','state_limit':'SwiftRunBudget::default().state_bytes',
 'combined_limit':'SwiftRunBudget::default().combined_bytes',
}
def setup(label,schema):
    vm=probe.SCRATCH/('metadata-'+label);shutil.copytree(probe.SCRATCH/label,vm)
    f=vm/'src/experimental_swift_reactor/frame_operations.rs'
    if label=='candidate':
        text=f.read_text().replace('// CONTRACT_INVENTORY_INSERT',(HERE/'positive-positions.rs').read_text())
        body=['pub(super) fn host_positions_metadata(){']
        for cls in ['HostPermanentPositions','HostActivePositions']:
            body.append(f'println!("HC_CLASS {cls} {{}} {{}}",size_of::<{cls}>(),std::mem::align_of::<{cls}>());')
        for row in schema:
            prefix='#[cfg(test)] ' if row['config']=='unit' else ''
            body.append(prefix+f'println!("HC_FIELD {row["field"]} {{}} {{}} {{}}",std::mem::offset_of!({row["ownerClass"]},{row["field"]}),size_of::<{row["rustType"]}>(),std::mem::align_of::<{row["rustType"]}>());')
        body+=['}']
        # The module's final closing brace follows the insertion marker.
        text=text[:text.rfind('}')]+ '\n'+'\n'.join(body)+'\n}\n'
        f.write_text(text)
    code=['pub(crate) fn host_contract_metadata(){']
    for name,ty in TYPES.items():code.append(f'println!("HC_TYPE {name} {{}} {{}}",size_of::<{ty}>(),std::mem::align_of::<{ty}>());')
    for ty,fields in FIELDS.items():
        for field in fields:code.append(f'println!("HC_OWNER {ty}.{field} {{}}",std::mem::offset_of!({ty},{field}));')
    for name,expr in TOTALS.items():code.append(f'println!("HC_TOTAL {name} {{}}",{expr});')
    if label=='candidate':
        code+=['host_contract_probe::host_positions_metadata();',
          'println!("HC_TOTAL proposed_header {}",execution_header_bytes().unwrap().checked_add(size_of::<host_contract_probe::HostPermanentPositions>()).unwrap());',
          'println!("HC_TOTAL proposed_frame {}",FRAME_OPERATION_BYTES.unwrap().checked_add(size_of::<host_contract_probe::HostActivePositions>()).unwrap());']
    code+=['}','#[cfg(test)] #[test] fn host_contract_layout_only(){host_contract_metadata();}']
    f.write_text(f.read_text()+'\n'+'\n'.join(code)+'\n')
    p=vm/'src/experimental_swift_reactor/mod.rs';p.write_text(p.read_text()+'\npub(crate) fn host_layout_route(){execution::frame_operations::host_contract_metadata();}\n')
    p=vm/'src/lib.rs';p.write_text(p.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn host_layout_route(){experimental_swift_reactor::host_layout_route();}\n')
    p=vm/'src/bin/host_contract_layout.rs';p.parent.mkdir(exist_ok=True);p.write_text('fn main(){mixer_vm::host_layout_route();}\n')
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
def main():
    probe.SCRATCH=Path(json.loads((HERE/'session.json').read_text())['scratch'])
    schema=json.loads((HERE/'inventory-schema.json').read_text())
    layouts=json.loads((HERE/'layouts.json').read_text()) if sys.argv[1:] else []
    archives={}
    for label in (sys.argv[1:] or ['baseline','candidate']):
        vm=setup(label,schema)
        for features,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
            for release in [False,True]:
                for unit in [False,True]:
                    profile='release' if release else 'debug';config='unit' if unit else 'production'
                    name=f'layout-{label}-{features}-{profile}-{config}'
                    argv=(['cargo','test','--lib','--offline','--locked',*flags,*(['--release'] if release else []),'host_contract_layout_only','--','--nocapture','--test-threads=1'] if unit
                      else ['cargo','run','--offline','--locked','--bin','host_contract_layout',*flags,*(['--release'] if release else [])])
                    p=run(name,argv,vm,{'CARGO_TARGET_DIR':str(probe.SCRATCH/('target-layout-'+label))})
                    layout=parse(p.stdout.decode());layout.update(label=label,features=features,profile=profile,unit=unit)
                    if label=='candidate':
                        old=next(v for v in layouts if (v['label'],v['features'],v['profile'],v['unit'])==('baseline',features,profile,unit))
                        assert layout['types']==old['types'] and layout['owners']==old['owners']
                        for n,v in old['totals'].items():assert layout['totals'][n]==v,(n,v)
                        assert layout['totals']['proposed_header']==old['totals']['header']+layout['classes']['HostPermanentPositions']['bytes']
                        assert layout['totals']['proposed_frame']==old['totals']['frame']+layout['classes']['HostActivePositions']['bytes']
                        expected={r['field'] for r in schema if unit or r['config']!='unit'}
                        assert set(layout['fields'])==expected
                        occupied={}
                        for row in sorted((r for r in schema if r['field'] in expected),key=lambda r:(r['ownerClass'],layout['fields'][r['field']]['offset'])):
                            field=layout['fields'][row['field']];cls=row['ownerClass']
                            assert field['offset']>=occupied.get(cls,0)
                            assert field['offset']%field['alignment']==0
                            occupied[cls]=field['offset']+field['bytes']
                            assert occupied[cls]<=layout['classes'][cls]['bytes']
                    assert layout['totals']['ticket_max']==86
                    assert layout['totals']['state_limit']==134217728 and layout['totals']['combined_limit']==268435456
                    layouts.append(layout);save('layouts.json',layouts)
        archives['metadata-'+label]=archive('metadata-'+label)
    save('metadata-source-closures.json',archives)
    print('16 paired layouts; every positive field disjoint; unchanged owners and prior inventories')
if __name__=='__main__':main()
