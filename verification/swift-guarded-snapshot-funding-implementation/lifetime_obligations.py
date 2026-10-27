"""Name the preserved lifetime boundaries; this report does not discharge them."""
from collections import Counter
from pathlib import Path
import json
import sys

sys.dont_write_bytecode=True
from prepare import HERE,BASE,RECIPE,CONTROL,PROFILE,sha,write
from verify import bounded,custody

def child():
    binding=custody()
    inventory_root=HERE.parent/'swift-guarded-snapshot-owner-storage-closure'
    inventory=json.loads((inventory_root/'inventory.json').read_text())
    host=json.loads((inventory_root/'host-caller.json').read_text())
    funding={r['id']:r['funding'] for r in json.loads((RECIPE/'funding.json').read_text())['roles']}
    def row(role):
        return {**{k:role[k] for k in ['id','template','compiler_type','kind','bytes','source','source_text','source_member_sha256']},
                'corrected_funding':funding[role['id']]}
    a_returns=[row(r) for r in inventory['roles'] if r['kind']=='return-expression'
               and funding[r['id']]['admitted-only']>0]
    writer_moves=[row(r) for r in inventory['roles'] if r['template']=='owner::write_snapshot_v1'
                  and r['compiler_type'].endswith(('SnapshotAttemptV1','SnapshotObservationV1','SnapshotExportErrorV1'))]
    receiving=[row(r) for r in inventory['roles'] if funding[r['id']]['selected-unconditional']>0
               and any(name in r['compiler_type'] for name in ['SnapshotAttemptV1','SnapshotOuterV1',
                   'SnapshotPrimaryRetirementV1','SnapshotRunV1','SnapshotScopeFinishV1'])]
    assert len(a_returns)==13
    assert next(r for r in a_returns if r['id']=='owner::write_snapshot_v1::_0')['bytes']==2248
    assert any(r['id'].endswith('::finish::_3') and r['source_text']=='export' for r in receiving)
    host_roles=host['function']['roles']
    product=[r for r in host_roles if r['funding_class']=='host-caller']
    external=[r for r in host_roles if r['funding_class']=='external-harness']
    assert len(product)==53 and len(external)==163
    assert sum(r['bytes'] for r in product)==81327
    # Exact roles already authored before the selected ingress call's returned
    # scope. Their presence is a reservation-order obligation, not permission
    # to remove the existing H charge or to reclassify them as external.
    pre_ingress_ids=['owner::selected_owned_files_v1::_'+str(n) for n in [1,3,6,7,8,9,10]]
    pre_ingress=[{k:r[k] for k in ['id','compiler_type','kind','bytes','source','source_text','source_member_sha256']}
                 for r in product if r['id'] in pre_ingress_ids]
    assert len(pre_ingress)==7
    profile=(HERE/'source/vm'/PROFILE).read_text()
    selected_complete='Self::Admitted{control,previous,wasi}=>control.end_construction_phase_with_wasi(storage,previous,wasi),'
    assert selected_complete in profile
    report=dict(schema=1,source_binding=binding,
        target_scope=dict(rustc='1.99.0 b940084d7eb6a299eb4bfeb8e34901bc051e7ac4',
                          target='aarch64-apple-darwin',contexts=['production','cfg(test)'],
                          Linux_32bit_native_qualified=False),
        A_narrowing=dict(status='required independent source integration review before any writer release',
            preserved_source=selected_complete,
            return_chain=['write_snapshot_v1 returns SnapshotAttemptV1',
                'SnapshotBranchV1::export transfers it to the existing selected Attempt place',
                'SnapshotBranchV1::finish receives export before access.complete(storage)',
                'access.complete drops phase storage and narrows same ticket to previous Fselected [+H]',
                'finish moves export into SnapshotOuterV1 after narrowing',
                'outer survives in SnapshotRunV1 then SnapshotPrimaryRetirementV1/finish/caller diagnostics'],
            exact_A_return_roles=a_returns,exact_writer_return_move_roles=writer_moves,
            exact_S_receiving_roles=receiving,
            determination='The receiving S slots are already charged. This report does not assert that those slots are missing funding; review must prove each A producer return/move place and any owned diagnostic backing has actually ended or transferred to separately reserved storage before A is refunded.',
            conservative_finalizer='Original ConstructionBound retirement remains unchanged and retains enlarged selected charge; it is not a proof of the earlier A narrowing boundary.',
            admission_reachable=False,reason='Unchanged proposed_emission_work_v1 returns WorkAuditPending before conditional A commit.'),
        H_pre_ingress=dict(status='required genuine host ownership/reservation review before host dispatch',
            charged_at='SnapshotAdoptionV1 foundation during selected Construction admission in cfg(test)',
            production_H_included=False,unit_H_bytes=81327,charged_product_roles=53,
            exact_already_authored_argument_roles=pre_ingress,
            separate_external_harness_roles=163,external_harness_costs_reserved=False,
            outside_scope='Retain separate 19 cfg(test) instrumentation roles from accepted producer; no qualification follows from including H in a selected const.',
            qualification=False),
        narrowed_fixture_grants=dict(values=[300000,400000],unchanged=True,
            boundary='Larger exact common Construction admission may refuse the unchanged 400000 fixture earlier than its historical downstream boundary. No VM fixture was dispatched and no limit was raised.'),
        fixed_policy=dict(memory_bytes=268435456,work_units=1000000000,changed=False),
        helper_delegation=dict(included=False,selected_17728_delta_added=False,
                               WorkAuditPending=True,source_members=144),
        engine_VM_writer_runtime_executed=False,healthy_cleanup_selected=False,
        native_device_simulator_emulator_UI_capture='paused and pending; none started or inspected',
        immutable_report_inputs=[dict(path=str(inventory_root/name),sha256=sha((inventory_root/name).read_bytes()))
                                 for name in ['inventory.json','host-caller.json']])
    write('lifetime-obligations.json',report)
    print(json.dumps(dict(A_return_roles=len(a_returns),writer_move_roles=len(writer_moves),
        S_receiving_roles=len(receiving),pre_ingress_H_roles=len(pre_ingress),
        admitted_A_boundary='pending',actual_writer_dispatched=False),sort_keys=True))

def main():
    if len(sys.argv)==2 and sys.argv[1]=='--child':
        child()
        return
    directory=HERE/'commands/lifetime-obligation-report'
    directory.mkdir(parents=True,exist_ok=False)
    argv=[sys.executable,str(Path(__file__).resolve()),'--child']
    out,err,receipt=bounded(argv,{'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},HERE.parent.parent)
    (directory/'stdout').write_bytes(out)
    (directory/'stderr').write_bytes(err)
    receipt.update(schema=1,python_version=sys.version,driver_sha256=sha(Path(__file__).read_bytes()),
        source_binding=custody(),stdout_sha256=sha(out),stderr_sha256=sha(err),
        scope='Finite frozen inventory/source lifetime obligation reporting; no runtime qualification')
    (directory/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    assert receipt['exit_code']==0 and receipt['owned_group_absent'] and not receipt['timed_out'],err.decode()
    print(out.decode().strip())

if __name__=='__main__':
    main()
