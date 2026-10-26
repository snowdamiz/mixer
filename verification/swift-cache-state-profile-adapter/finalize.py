#!/usr/bin/env python3
"""Verify exact local evidence, remove only owned scratch, seal this packet."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,sys
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(name):return json.loads((P/name).read_text())
def dump(name,obj):(P/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def members(base):return [{'path':str(f.relative_to(base)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(base.rglob('*')) if f.is_file()]
def main():
    freeze=load('source-freeze.json');changed=[]
    for m in freeze['members']:
        live=ROOT/m['path'];assert live.stat().st_size==m['bytes'] and sha(live)==m['sha256'],m['path']
        copy=P/'source'/m['path']
        if sha(copy)!=m['sha256']:changed.append(m['path'])
    assert changed==['vm/src/experimental_swift_reactor/mod.rs'],changed
    original=set(m['path'] for m in freeze['members']);added=sorted('vm/'+m['path'] for m in members(P/'source/vm') if 'vm/'+m['path'] not in original)
    assert added==['vm/src/experimental_swift_reactor/diagnostic_profile.rs','vm/src/experimental_swift_reactor/diagnostic_profile_tests.rs'],added
    candidate=members(P/'source/vm');digest=hashlib.sha256(json.dumps(candidate,sort_keys=True,separators=(',',':')).encode()).hexdigest();assert digest=='d65ea46493da772cdbf15c3f00da366feb43113c52104079147449c0aa9789cf'
    dump('candidate-source-manifest.json',{'members':candidate,'member_count':len(candidate),'bytes':sum(m['bytes'] for m in candidate),'tree_sha256':digest,'original_changed':changed,'original_added':added})
    before=load('closed-fixture-before.json')
    for m in before:assert sha(ROOT/m['path'])==m['sha256'] and (ROOT/m['path']).stat().st_size==m['bytes']
    for m in before[:3]:assert sha(P/'closed-fixture-source'/Path(m['path']).name)==m['sha256']
    dump('closed-fixture-after.json',{'members':before,'unchanged':True,'source_library_only':True,'full_pack_or_tests_not_run':True})
    req=load('required-tests.json');assert req['count']==17 and len(set(req['methods']))==17 and req['source_sha256']==sha(P/'source/vm/src/experimental_swift_reactor/diagnostic_profile_tests.rs')
    bridge=load('required-bridge.json');assert bridge['count']==16 and len(set(bridge['invocations']))==16
    for mode in ['debug','optimized']:
        unit=load(f'unit-qualification-{mode}.json');assert unit['selected']==req['methods'] and [unit[x] for x in ['compiler_listed_total','passed','failed','ignored','filtered']]==[403,17,0,0,386]
        q=load(f'bridge-qualification-{mode}.json');assert q['passed'] and [r['name'] for r in q['results']]==bridge['invocations']
        for r in q['results']:
            log=P/'logs'/f"bridge-{mode}-{r['name']}.stdout";assert log.read_text().count('case='+r['name']+' ')==1 and r['passed'] and r['report_bytes']==49152
            output=P/'artifacts'/mode/'bridge-reports'/(r['name']+'.bin');assert sha(output)==r['report_sha256']
        for name in ['units','list-all','list-selected']:
            assert load(f'logs/{mode}-{name}.json')['candidate_source_tree_sha256']==digest
    assert load('accounting.json')['candidate_tree_sha256']==digest
    warnings=load('inherited-warning-inventory.json');assert all(warnings[m]['count']==148 and not warnings[m]['suppressed'] for m in ['debug','optimized'])
    assert not load('environment-controls.json')['observed_compiler_controls_present']
    # Retain one complete actual-File bridge input set; remaining exact variants
    # are reproducible by the independent encoder and have per-run input hashes.
    positive=P/'artifacts/retained-bridge-positive';positive.mkdir(exist_ok=True)
    for kind in ['stream','profile','context']:
        src=P/'scratch/bridge-debug'/('miss_build_publish_release-'+kind+'.bin');shutil.copyfile(src,positive/(kind+'.bin'))
    assert (positive/'profile.bin').read_bytes()[512:]==(P/'artifacts/debug/actual-rows.bin').read_bytes()
    records=[]
    for f in sorted((P/'logs').glob('*.json')):
        r=json.loads(f.read_text())
        if 'argv' not in r:continue
        assert r['timeout_seconds']==60 and r['owned_child_reaped']
        for kind in ['stdout','stderr']:
            output=f.with_suffix('.'+kind);assert output.stat().st_size==r[kind]['bytes'] and sha(output)==r[kind]['sha256']
        records.append({'receipt':str(f.relative_to(P)),'exit_code':r['exit_code'],'timed_out':r['timed_out'],'elapsed_seconds':r['elapsed_seconds']})
    dump('command-inventory.json',{'commands':records,'count':len(records),'failed_retained':[r for r in records if r['exit_code']!=0 or r['timed_out']],'earliest_PATH_failure':'logs/authoring-failure-01.txt','deadline_each_seconds':60,'direct_children_reaped_and_groups_terminated':True,'no_process_inventory':True})
    scratch=P/'scratch';scratch_inventory=members(scratch);shutil.rmtree(scratch)
    pyc=[]
    for path in list(P.rglob('__pycache__')):
        pyc.append(str(path.relative_to(P)));shutil.rmtree(path)
    dump('cleanup.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owned_scratch':str(scratch),'removed_files':len(scratch_inventory),'removed_bytes':sum(m['bytes'] for m in scratch_inventory),'scratch_removed':not scratch.exists(),'removed_python_caches':pyc,'all_recorded_direct_children_reaped_and_owned_groups_terminated':True,'no_native_runtime_or_capture_process_started':True,'no_other_project_processes_or_data_inspected_or_modified':True,'partial_File_and_positive_rows_and_reports_retained':True})
    limits=['real header/cache construction/binding/result/ledger/custody and semantic replay remain pending','unchanged fixture schema cannot independently establish sealed-owner import/defined provenance; collusive defined-row/event replacement can remain synthetically admissible','exact tested import/tail negatives are invalid sentinels or event mismatches against unchanged undefined rows','File metadata/position failure and unreachable sealed-owner inconsistency branches are source-reviewed only','concurrent drift/report-output fault not newly exercised by this bridge; late footer suppression exercised','acknowledged writes only; no durability/fsync/crypto/custody','no full VM target or 103-command suite','Rust 1.99.0 aarch64 macOS host only; no new Rust1.98.1/Linux/CI acceptance','native simulator/emulator/device/UI/capture paused; signing/store/published FieldLog/customer/operations/GA unqualified']
    dump('decision.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate_locally_qualified':True,'implementation_accepted':False,'independent_review_required':True,'canonical_integration_selected':False,'source_revision_context':freeze['head'],'source_tree_context':freeze['git_tree'],'candidate_source_tree_sha256':digest,'exact_unit_methods_each_mode':17,'compiler_total':403,'filtered':386,'exact_bridge_invocations_each_mode':16,'source_and_live_VM_unchanged_except_isolated_declarations_and_new_files':True,'new_logical_union_bytes':7504,'source_action_upper_bound':97301024,'new_allocation_requests_observed':0,'all_four_authority_getters_false':True,'fixture_context_and_header_synthetic':True,'bridge_profile_body_matches_actual_derived_File_bytes':True,'source_body_comparison':'actual-source-row-comparison.json','all_owned_scratch_cleaned':True,'limits':limits,'hosted_forbidden_sources_read_imported_or_executed':False})
    excluded={'seal.json','seal.sha256'};items=[m for m in members(P) if m['path'] not in excluded]
    seal={'schema':1,'scope':'Isolated actual validated-owner row body candidate; local qualification only, independent review required','members':items,'member_count':len(items),'total_bytes':sum(m['bytes'] for m in items),'tree_sha256':hashlib.sha256(json.dumps(items,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'excluded':sorted(excluded),'implementation_accepted':False,'native_or_GA_accepted':False}
    dump('seal.json',seal);(P/'seal.sha256').write_text(sha(P/'seal.json')+'  seal.json\n');print(json.dumps({k:v for k,v in seal.items() if k!='members'}));print('seal_sha256='+sha(P/'seal.json'))
if __name__=='__main__':main()
