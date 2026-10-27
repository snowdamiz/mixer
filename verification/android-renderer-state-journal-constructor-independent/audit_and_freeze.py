#!/usr/bin/env python3
"""Check retained raw observations and close this review packet without touching its producer."""
from pathlib import Path
import collections
import datetime
import hashlib
import json

D=Path(__file__).resolve().parent
P=D.parent/'android-renderer-state-journal-constructor-controls'
EXPECTED='d134612993dd5d2071c55e2f63c2ee93fbaea503f5123e146a839ee89354a279'
STATES={'clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback'}

def identity(path):
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def main():
    assert identity(P/'seal.json')['sha256']==EXPECTED
    seal=json.loads((P/'seal.json').read_bytes())
    for row in seal['members']:assert identity(P/row['path'])=={key:row[key] for key in ('bytes','sha256')}
    run=D/'run-1';producer=json.loads((run/'producer-results.json').read_bytes());independent=json.loads((run/'independent-results.json').read_bytes())
    assert producer==json.loads((P/'run-3/actual-results.json').read_bytes())
    assert producer['invocations']==85 and producer['callback_rows']==70 and producer['finite_rows']==15 and producer['checks']==2556
    branches=collections.defaultdict(set);hooks=[];returns=[];exceptions=[];frame_lengths=collections.Counter()
    for row in producer['rows']:
        assert row['counts_before']==row['counts_after']==[2,2,3]
        assert row['mutations_restored'] and row['original_authority_references_preserved'] and row['native_outcome_capture_clean']
        selected=row['native_site_id']
        if selected is None:
            assert not row['exact_tuple_hooks'] and not row['actual_native_outcomes']
            continue
        branches[(selected,row['branch'])].add(row['callback_state'])
        assert [hook['phase'] for hook in row['exact_tuple_hooks']]==['entry','beforeReturn']
        for hook in row['exact_tuple_hooks']:
            assert hook['receiver']==hook['original_own_receiver']
            assert hook['frames'][0]['method']=='<init>'
            assert '@'+str(hook['frames'][0]['bci'])+':' in selected
            assert hook['frames'][0]['class'].replace('.','/')+'#<init>'+hook['frames'][0]['descriptor'] in selected
            assert hook['counts']==[2,2,3]
            hooks.append(hook);frame_lengths[len(hook['frames'])]+=1
        throwing='throw-after-callback' in row['callback_state']
        if '@222:' in selected and not throwing:
            assert not row['actual_native_outcomes'] and row['actual_enclosing_snapshot']['window_position']==[108,209]
        else:assert len(row['actual_native_outcomes'])==1
        for outcome in row['actual_native_outcomes']:
            assert outcome['frames']==row['exact_tuple_hooks'][-1]['frames']
            frame_lengths[len(outcome['frames'])]+=1
            if throwing:
                assert outcome['completion']=='exception'
                assert outcome['exception_reference']==row['actual_enclosing_snapshot']['exception_reference']
                assert row['actual_enclosing_snapshot']['exact_original_identity'] and not row['actual_enclosing_snapshot']['partial_object_observable']
                exceptions.append(outcome)
            else:
                assert outcome['completion']=='return'
                returns.append(outcome)
    assert len(branches)==10 and all(value==STATES for value in branches.values())
    assert len({key[0] for key in branches})==5
    assert len(hooks)==140 and len({h['event_reference'] for h in hooks})==140 and len({h['event_index'] for h in hooks})==140
    assert len(returns)==30 and len(exceptions)==20 and frame_lengths=={17:190}
    assert sum(r['enclosing_completion']=='normal-object' for r in producer['rows'])==65
    assert producer['original_final_counts']==independent['final_counts']==[0,0,0]
    assert independent['checks']==104 and independent['independent_cases']==3
    all_returns=[o for row in independent['rows'] for o in row['all_unfiltered_passive_outcomes']]
    assert len(all_returns)==9 and all(o['completion']=='return' for o in all_returns)
    assert [len(row['all_unfiltered_passive_outcomes']) for row in independent['rows']]==[1,2,6]
    timed=independent['rows'][1]['all_unfiltered_passive_outcomes']
    assert [o['frames'][0]['bci'] for o in timed]==[67,145]
    assert [o['value']['text'] for o in timed]==['initial-live','return-live']
    assert timed[0]['value']['reference']==timed[1]['value']['reference']
    alias=independent['rows'][2]['all_unfiltered_passive_outcomes']
    assert [o['value']['value'] for o in alias[-2:]]==[500,333]
    commands=json.loads((run/'commands.json').read_bytes());assert len(commands)==6
    for command in commands:
        assert command['exit']==0 and command['reaped'] and not command['timeout']
        for stream in ('stdout','stderr'):assert identity(run/command[stream]['path'])=={key:command[stream][key] for key in ('bytes','sha256')}
    argv=next(c['argv'] for c in commands if c['name']=='compile')
    assert all(flag in argv for flag in ('--release','17','-proc:none','-Xlint:all','-Werror'))
    assert not any(flag.startswith('-g') for flag in argv)
    cleanup=json.loads((run/'cleanup.json').read_bytes())
    assert cleanup['all_started_children_reaped'] and cleanup['owned_scratch_removed'] and cleanup['leased_JDK_preserved'] and cleanup['native_instances_started']==0
    assert identity(D/'run_review.py')==identity(run/'run_review.py')
    assert identity(D/'IndependentConstructorControls.java')==identity(run/'IndependentConstructorControls.java')
    summary={'schema':1,'verdict':'accept-scoped-host-constructor-facets','required_amendments':[],'producer_seal_sha256':EXPECTED,'source_context':producer['source_context'],'producer_packet_members':152,'producer_packet_bytes':2814411,'fresh_all209_exact':True,'fresh_producer_results_equal_selected_run3':True,'producer_direct_calls':85,'producer_checks':2556,'producer_finite_rows':15,'producer_callback_rows':70,'producer_tuple_branch_state_combinations':70,'producer_exact_native_tuples':5,'producer_normal_objects':65,'producer_exact_exceptions':20,'producer_tuple_selected_nonvoid_returns':30,'producer_full_hook_and_outcome_frame_lengths':dict(frame_lengths),'independent_controls':3,'independent_checks':104,'independent_unfiltered_nonvoid_returns':9,'retained_run1_setup_failure_and_missing_runner_snapshot_limit':True,'run2_is_historical_not_extra_final_credit':True,'scope':'Exact host constructor object/result and callback facets only; no complete enclosing/matrix, membership, release, native, OTA, publication or GA authority.','pending':['Unhooked finite host getter/child/span helper native qualification and transitive matrix joins','Original enclosing authority/cohort/funding/completion/cleanup obligations','Exceptional constructor receiver/private partial output-array identity','Internal drawable source-array identity and runtime allocation-failure injection','Native runtime/physical/UI/capture tests remain paused'],'cleanup':cleanup}
    save(D/'review.json',summary)
    members=[{'path':str(p.relative_to(D)),**identity(p)} for p in sorted(D.rglob('*')) if p.is_file() and p.name!='seal.json']
    assert not any('scratch/' in row['path'] for row in members)
    final={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'closed-independent-scoped-host-review','producer_seal_sha256':EXPECTED,'source_context':producer['source_context'],'verdict':summary['verdict'],'members':members,'member_count':len(members),'member_bytes':sum(row['bytes'] for row in members),'no_native_runtime_UI_capture_process_inventory':True,'no_canonical_index_git_or_external_mutation':True}
    save(D/'seal.json',final)
    for row in members:assert identity(D/row['path'])=={key:row[key] for key in ('bytes','sha256')}
    print(json.dumps({'seal':identity(D/'seal.json'),'members':len(members),'bytes':final['member_bytes'],'verdict':summary['verdict']},indent=2))

if __name__=='__main__':main()
