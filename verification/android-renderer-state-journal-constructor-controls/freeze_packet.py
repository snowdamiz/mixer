#!/usr/bin/env python3
"""Close the exact two-constructor packet; no product/canonical authority is implied."""
from pathlib import Path
import collections
import datetime
import hashlib
import json

D=Path(__file__).resolve().parent
CONTEXT='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'

def identity(path):
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def main():
    run=D/'run-3'
    results=json.loads((run/'actual-results.json').read_bytes())
    receipt=json.loads((run/'receipt.json').read_bytes())
    provenance=json.loads((run/'provenance.json').read_bytes())
    commands=json.loads((run/'commands.json').read_bytes())
    cleanup=json.loads((run/'cleanup.json').read_bytes())
    contracts=json.loads((D/'inputs/exact-two-subject-contracts.json').read_bytes())
    assert results['source_context']==receipt['source_context']==provenance['source_context']==CONTEXT
    assert identity(D/'ConstructorControls.java')==receipt['control']==identity(run/'ConstructorControls.java')
    assert identity(D/'run_controls.py')==receipt['runner']==identity(run/'run_controls.py')
    assert identity(run/'actual-results.json')==receipt['results']
    assert all(row['exit']==0 and row['reaped'] and not row['timeout'] for row in commands)
    assert [row['name'] for row in commands]==['java-version','javac-version','compile','constructor-controls']
    compile_command=next(row['argv'] for row in commands if row['name']=='compile')
    assert '-g' not in compile_command and '-g:none' not in compile_command
    assert '--release' in compile_command and '-proc:none' in compile_command and '-Xlint:all' in compile_command and '-Werror' in compile_command
    assert cleanup['all_started_children_reaped'] and cleanup['owned_scratch_removed'] and cleanup['jdk_tool_lease_preserved']
    actual_classes=json.loads((run/'actual-product-class-map.json').read_bytes())
    expected_classes=json.loads((D/'inputs/selected-product-class-map.json').read_bytes())
    assert actual_classes==expected_classes and len(actual_classes)==209
    source_roster=json.loads((D/'inputs/source-roster.json').read_bytes())
    for source in source_roster:assert identity(D/source['path'])=={'bytes':source['bytes'],'sha256':source['sha256']}
    assert len([x for x in source_roster if x['role']=='exact-product16'])==16
    assert len([x for x in source_roster if '/host-leaves/' in x['path']])==87
    expected_subjects={s['id']:s for s in contracts['subjects']};assert len(expected_subjects)==2
    expected_tuples={site for subject in contracts['subjects'] for case in subject['required_cases'] if case['kind']=='callback-state' for site in case['applicable_native_site_ids']}
    required_states={'clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback'}
    tuple_branches=collections.defaultdict(lambda:collections.defaultdict(set))
    finite=collections.Counter();completions=collections.Counter();frame_lengths=collections.Counter();outcome_completions=collections.Counter()
    assert results['invocations']==len(results['rows'])==85 and results['callback_rows']==70 and results['finite_rows']==15
    for row in results['rows']:
        subject=expected_subjects[row['subject_id']]
        assert row['class_sha256']==subject['class_sha256']
        assert row['counts_before']==row['counts_after']==[2,2,3]
        assert row['original_authority_references_preserved'] and row['mutations_restored'] and row['native_outcome_capture_clean'] and row['no_membership_or_release_authority']
        completions[row['enclosing_completion']]+=1
        site_id=row['native_site_id']
        if site_id is None:
            finite[row['subject_id']]+=1
            assert row['callback_state']=='finite-no-fabricated-callback' and not row['exact_tuple_hooks']
            continue
        assert site_id in expected_tuples
        tuple_branches[site_id][row['branch']].add(row['callback_state'])
        assert [hook['phase'] for hook in row['exact_tuple_hooks']]==['entry','beforeReturn']
        for hook in row['exact_tuple_hooks']:
            assert hook['event_reference'] and isinstance(hook['event_index'],int) and hook['receiver']==hook['original_own_receiver']
            assert len(hook['frames'])<24
            assert any(frame['class'].replace('.','/')==subject['class'] and frame['method']=='<init>' and frame['descriptor']==subject['descriptor'] and f"@{frame['bci']}:" in site_id for frame in hook['frames'])
            frame_lengths[len(hook['frames'])]+=1
        throwing=row['callback_state'] in {'ordinary-throw-after-callback','fatal-throw-after-callback'}
        assert row['enclosing_completion']==('exact-exception' if throwing else 'normal-object')
        if throwing:assert row['actual_enclosing_snapshot']['exact_original_identity'] and not row['actual_enclosing_snapshot']['partial_object_observable']
        if '@222:' in site_id and not throwing:
            assert row['actual_native_outcomes']==[]
            assert row['actual_enclosing_snapshot']['window_position']==[108,209]
        else:assert len(row['actual_native_outcomes'])==1
        for outcome in row['actual_native_outcomes']:
            assert len(outcome['frames'])<24
            outcome_completions[outcome['completion']]+=1
            if throwing:
                assert outcome['completion']=='exception'
                assert outcome['exception_reference']==row['actual_enclosing_snapshot']['exception_reference']
    assert set(tuple_branches)==expected_tuples and len(expected_tuples)==5
    assert all(states==required_states for branches in tuple_branches.values() for states in branches.values())
    assert sorted(finite.values())==[4,11]
    assert completions=={'normal-object':65,'exact-exception':20}
    assert outcome_completions=={'return':30,'exception':20}
    assert frame_lengths=={17:140}
    assert results['original_final_counts']==[0,0,0] and results['original_edit_completed_after_restores']
    assert (D/'run-1/failure.json').exists() and not (D/'run-1/commands.json').exists()
    assert json.loads((D/'run-2/receipt.json').read_bytes())['invocations']==85
    closure={'source_roster':identity(D/'inputs/source-roster.json'),'control':identity(D/'ConstructorControls.java'),'runner':identity(D/'run_controls.py'),'product_source_map':identity(D/'inputs/selected-product-source-map.json'),'product_class_map':identity(D/'inputs/selected-product-class-map.json'),'tools':provenance['tools']}
    closure_hash=hashlib.sha256(json.dumps(closure,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    save(D/'validation.json',{'schema':1,'selected_run':'run-3','source_context':CONTEXT,'source_revision_context':receipt['source_revision_context'],'execution_source_tool_closure_sha256':closure_hash,'exact_class209_reproduced':True,'source16_B87_selected8_original_fixture_preserved':True,'invocations':85,'finite_rows':15,'callback_rows':70,'exact_hooked_tuples':5,'canonical_states_per_applicable_branch':7,'checks':results['checks'],'normal_enclosing_objects':65,'exact_original_exceptions':20,'actual_nonvoid_native_returns':30,'actual_hook_exception_observations':20,'void_normal_nonvoid_outcomes_invented':0,'full_frame_lengths':dict(frame_lengths),'tuple_branch_states':{site:{branch:sorted(states) for branch,states in branches.items()} for site,branches in tuple_branches.items()},'selected_command_count':len(commands),'initial_failed_attempt_retained':True,'run1_source_snapshot_missing_explicitly_disclosed':True,'all_children_reaped_scratch_removed':True,'JDK_lease_preserved':True,'native_UI_capture_process_inventory_started':False,'canonical_membership_release_native_OTA_GA_accepted':False})
    members=[]
    for path in sorted(D.rglob('*')):
        if path.is_file() and path.name!='seal.json':members.append({'path':str(path.relative_to(D)),**identity(path)})
    seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'closed-two-exact-constructors-host-controls-root-review-pending','selected_run':'run-3','source_context':CONTEXT,'source_revision_context':receipt['source_revision_context'],'members':members,'member_count':len(members),'member_bytes':sum(row['bytes'] for row in members),'summary':{'subjects':2,'invocations':85,'finite_rows':15,'callback_rows':70,'hooked_tuples':5,'canonical_states_per_applicable_branch':7,'assertions':results['checks'],'class209_exact':True,'source_tool_closure_sha256':closure_hash},'scope':'Exact NativeState and AttachmentJournal ordinary host constructors only; immutable typed results and exact original callback exceptions. Constructor membership/release authority and original enclosing obligations remain unaccepted.','native_runtime_UI_capture_process_inventory_started':False,'full_matrix_canonical_membership_release_native_OTA_GA_accepted':False}
    save(D/'seal.json',seal)
    for row in members:assert identity(D/row['path'])=={'bytes':row['bytes'],'sha256':row['sha256']}
    print(json.dumps({'seal':identity(D/'seal.json'),'member_count':len(members),'member_bytes':seal['member_bytes'],'summary':seal['summary']},indent=2))

if __name__=='__main__':main()
