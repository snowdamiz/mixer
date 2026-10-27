#!/usr/bin/env python3
"""Freeze only this owned preparation packet; no Git or external mutation."""
from pathlib import Path
import datetime,hashlib,json
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,j):p.write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
def main():
    assert not list(OUT.glob('preparation-compile-*')), 'owned compiler scratch remains'
    baseline=json.loads((OUT/'inputs/source-manifest.json').read_text())
    for row in baseline['members']:
        p=OUT/'inputs/accepted-source/vm'/row['path']
        assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
    receipt=json.loads((OUT/'receipt-attempt-4.json').read_text())
    assert receipt['commands']==31 and receipt['passed_expectations']==31 and not receipt['failed_expectations']
    commands=[]
    for folder in sorted((OUT/'commands/attempt-4').iterdir()):
        r=json.loads((folder/'receipt.json').read_text())
        assert r['expectation_met'] and sha(folder/'stdout')==r['stdout_sha256'] and sha(folder/'stderr')==r['stderr_sha256']
        for name,digest in r['source_inputs'].items():assert sha(OUT/name)==digest
        commands.append({'path':str((folder/'receipt.json').relative_to(OUT)), 'sha256':sha(folder/'receipt.json'),'name':r['name'],'expectation_met':True})
    assert len(commands)==31
    result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'status':'frozen-concrete-contract-and-bounded-preparation-awaiting-root-independent-review',
       'source_revision_context':receipt['source_revision_context'],'accepted_source_tree_sha256':baseline['tree_sha256'],
       'accepted_source_members':144,'original_host_support_members_not_replayed':11,
       'baseline201_layout_identities':'inherited original source attribution; not whole matrix rerun',
       'wire_proposal':{'snapshot_magic':'MIXSNB02','snapshot_version':2,'header_bytes':2560,'snapshot_cap':69765152,
                       'provenance_magic':'MIXLPR01','provenance_bytes':576,'runtime_magic':'MIXRTB01','runtime_bytes':512,
                       'actual_loader_unchanged':['MIXLBD01','MIXLSE01'],'transfer_bytes':4096,'attempts_per_block':32},
       'final_commands':commands,'final_passed_expectations':31,'format_methods_passed':12,
       'compile_cases':28,'compile_positive':2,'compile_expected_negative':26,
       'compiler_modes':['ordinary-production debug','ordinary-production optimized'],
       'native_size_constant_assertions_per_positive':8,
       'source_roster_sha256':sha(OUT/'source-roster.json'),'storage_plan_sha256':sha(OUT/'storage-plan.json'),'contract_sha256':sha(OUT/'contract.md'),
       'new_exporter_layout_floor_measured':False,'new_exporter_admission_implemented':False,
       'source_owned_prototype_changes_only':True,'original_constructor_body_outcome_enum_guard_literal_header_rows_unchanged':True,
       'original300000grant':'required refusal preserved; no product limit increase',
       '400000fixture':'historical refusal-path only; not promoted',
       'independent_review_and_root_selection_pending':['wire IDs/format','private bridge','outer independent observation','all measured source places','pre-guard work and immutable deadline/cancellation design','separate host-only positive grant based on fresh exactfloor'],
       'future_evidence_pending':['working guarded exporter','all8 actual outcomes and partial output','unit+production newtype layouts and lifetime accounting','loader/output acquisition and operational IO allocation','File close/name/hash custody','runtime record actualcontrol/WASI joins','typedresult/rawDebug actual failures and15 finalledger values','context/FSM/replay/fullworkload/canonicalintegration','native/device/simulator/emulator/UI/capture paused','FieldLog separate-repo published package','OTA/store/customer/operational/GA'],
       'cleanup':receipt['cleanup'],'canonical_product_changed':False,'GA_gates_verified':0}
    write(OUT/'preparation-result.json',result)
    members=[{'path':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='seal.json']
    seal={'schema':1,'scope':'producer preparation only; root/independent selection pending','member_count':len(members),'bytes':sum(v['bytes'] for v in members),'tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'members':members}
    write(OUT/'seal.json',seal)
    print(json.dumps({'member_count':seal['member_count'],'bytes':seal['bytes'],'tree_sha256':seal['tree_sha256'],'seal_sha256':sha(OUT/'seal.json'),'status':result['status']}))
if __name__=='__main__':main()
