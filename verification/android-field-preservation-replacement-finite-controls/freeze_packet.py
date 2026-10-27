#!/usr/bin/env python3
"""Close only four direct finite host bodies; preserve all original obligations."""
from pathlib import Path
import collections
import datetime
import hashlib
import json

D=Path(__file__).resolve().parent
ROOT=D.parent.parent
CONTEXT='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
FP='dev/mixer/android/NativeAppearanceViewsV2$FieldPreservation'
RP='dev/mixer/android/NativeAppearanceViewsV2$Replacement'

def identity(path):
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')

def main():
    run=D/'run-2'
    result=json.loads((run/'actual-results.json').read_bytes())
    receipt=json.loads((run/'receipt.json').read_bytes())
    provenance=json.loads((run/'provenance.json').read_bytes())
    commands=json.loads((run/'commands.json').read_bytes())
    cleanup=json.loads((run/'cleanup.json').read_bytes())
    contracts=json.loads((D/'inputs/exact-four-subject-contracts.json').read_bytes())
    assert result['source_context']==receipt['source_context']==provenance['source_context']==contracts['source_context']==CONTEXT
    assert receipt['control']==identity(D/'FieldFiniteControls.java')==identity(run/'FieldFiniteControls.java')
    assert receipt['runner']==identity(D/'run_controls.py')==identity(run/'run_controls.py')
    assert receipt['results']==identity(run/'actual-results.json')
    assert [command['name'] for command in commands]==['java-version','javac-version','compile','field-finite-controls']
    for command in commands:
        assert command['exit']==0 and not command['timeout'] and command['reaped']
        for stream in ('stdout','stderr'):
            assert identity(run/command[stream]['path'])=={key:command[stream][key] for key in ('bytes','sha256')}
    argv=commands[2]['argv']
    assert all(flag in argv for flag in ('--release','17','-proc:none','-Xlint:all','-Werror'))
    assert '-g' not in argv and '-g:none' not in argv
    for flag in ('-sourcepath','-classpath'):assert argv[argv.index(flag)+1].endswith('/scratch/empty')
    assert cleanup['all_started_children_reaped'] and cleanup['owned_scratch_removed'] and cleanup['jdk_tool_lease_preserved']
    assert cleanup['maximum_concurrent_children']==1 and cleanup['native_instances_started']==0 and not cleanup['process_inventory_or_other_projects_touched']
    assert result['host_threads_started']==result['host_threads_joined']==3
    expected_classes=json.loads((D/'inputs/selected-product-class-map.json').read_bytes())
    assert len(expected_classes)==209 and json.loads((run/'actual-product-class-map.json').read_bytes())==expected_classes
    source_map=json.loads((D/'inputs/selected-product-source-map.json').read_bytes())
    assert len(source_map)==16 and hashlib.sha256(json.dumps({'source_map':source_map,'class_map':expected_classes},sort_keys=True,separators=(',',':')).encode()).hexdigest()==CONTEXT
    roster=json.loads((D/'inputs/source-roster.json').read_bytes())
    for row in roster:assert identity(D/row['path'])=={key:row[key] for key in ('bytes','sha256')}
    assert collections.Counter(row['role'] for row in roster)=={'exact-product16':16,'exact-B87':79,'selected-v4-derivative':8,'released-selected6-exact-original-fixture':1,'released-descriptor':1}
    origin=ROOT/contracts['origin']['path']
    assert identity(origin)=={key:contracts['origin'][key] for key in ('bytes','sha256')}
    full=json.loads(origin.read_bytes());originals={subject['id']:subject for subject in full['subjects']}
    subjects={subject['id']:subject for subject in contracts['subjects']}
    assert len(subjects)==4
    for subject in subjects.values():assert subject==originals[subject['id']]
    rows=result['rows'];assert len(rows)==result['invocations']==123
    counts=collections.Counter();completions=collections.Counter();calls=collections.Counter();values=collections.Counter();sites=collections.Counter();hooks=set();mask_rows={}
    pair_oracles=[(0,0,True),(0,1,False),(1,0,False),(-1,-1,True),(-(1<<63),-(1<<63),True),((1<<63)-1,(1<<63)-2,False),((1<<63)-2,(1<<63)-2,True),(1,4294967297,False),(-(1<<63),0,False),(0,-(1<<63),False)]
    for row in rows:
        subject=subjects[row['subject_id']]
        owner,method=subject['class'],subject['method']
        counts[(owner,method)]+=1;completions[row['completion']]+=1
        assert row['class_sha256']==subject['class_sha256']
        assert row['counts_before']==row['counts_after']==[2,2,3]
        assert row['shared_mutations_restored'] and row['no_native_events'] and row['no_membership_release_authority'] and row['original_required_cases_retained']
        assert row['native_callback_state']=='not-applicable-no-fabricated-native-callback'
        before,after=row['actual_before'],row['actual_after'];branch=row['finite_case'];observation=row['input_observation']
        if method=='<init>' and row['completion']=='normal':
            assert after['hooks_reference'] not in hooks and after['hooks_values']==[];hooks.add(after['hooks_reference'])
            assert after['field'].startswith('dev.mixer.android.NativeAppearanceViewsV2$NativeField@')
            assert after['record'].startswith('dev.mixer.android.NativeAppearanceViewsV2$Record@')
            assert after['reference']==row['actual_result'] and after['callbacks']==0
            if owner==FP:
                assert after['phase']==0 and after['snapshot']=='null'
                assert all(after[flag] is False for flag in ('entered','ended','checking','counted','released','release_ready'))
            else:
                assert after['stage']=='SNAPSHOTTING' and after['setter_calls']==0 and after['next_editable']==after['proposal']=='null' and after['event_value'] is None
                assert all(after[flag] is False for flag in ('registered','native_executing','setter_active','started','setter_returned','watcher_seen','lost','completed','event_claimed','event_evaluating'))
        if method=='endReady':
            assert before==after and observation is None
            mask=row['independent_expected_before_invocation']['mask']
            assert row['actual_result'] is (mask==63)
            assert before['entered'] is bool(mask&1) and before['ended'] is bool(mask&2)
            assert before['checking'] is not bool(mask&32)
            assert (before['callbacks']==0) is bool(mask&8) and bool(before['hooks_values']) is not bool(mask&16)
            assert before['counted'] and before['released'] and before['release_ready']
            if branch.startswith('truth-table-'):mask_rows[int(branch.removeprefix('truth-table-'))]=row['actual_result']
        if method=='unchangedLoss':
            assert before==after
            if branch.startswith('literal-equality-'):
                index=int(branch.removeprefix('literal-equality-'));stored,serial,expected=pair_oracles[index]
                assert before['loss_observation']==stored and observation['actual_return_long']==serial and row['actual_result'] is expected
            if branch.startswith('lost-'):
                assert before['lost'] and row['actual_result'] is False and observation['calls']==0
        if observation is not None:
            calls[observation['calls']]+=1
            assert observation['delegate_reference'].startswith('dev.mixer.android.NativeRenderer$2@')
            if observation['calls']:
                assert observation['calls']==1 and len(observation['production_call_frames'])<24
                bci=116 if method=='<init>' else 14
                assert any(frame['class'].replace('.','/')==owner and frame['method']==method and frame['descriptor']==subject['descriptor'] and frame['bci']==bci for frame in observation['production_call_frames'])
                sites[(owner,method,bci)]+=1
                if row['completion']=='exact-actual-input-exception':
                    assert observation['actual_exception_type']=='java.lang.IllegalStateException' and observation['actual_exception_message']=='V2 requires UI owner thread'
                    assert row['exact_exception_reference']==observation['actual_exception_reference']!='null' and observation['actual_return_long'] is None
                    assert row['actual_result'] is None
                    if method=='<init>':assert before is None and after is None
                    values['exact-actual-exception']+=1
                else:
                    assert observation['actual_exception_reference']=='null' and isinstance(observation['actual_return_long'],int)
                    values['actual-long-return']+=1
            else:assert observation['actual_return_long'] is None and observation['actual_exception_reference']=='null'
    assert counts=={(FP,'<init>'):16,(FP,'endReady'):76,(RP,'<init>'):9,(RP,'unchangedLoss'):22}
    assert mask_rows=={mask:mask==63 for mask in range(64)} and len(hooks)==24
    assert completions=={'normal':121,'exact-actual-input-exception':2} and calls=={1:27,0:20} and values=={'actual-long-return':25,'exact-actual-exception':2}
    assert sites=={(FP,'<init>',116):16,(RP,'unchangedLoss',14):11}
    assert result['original_edit_completed_after_restores'] and result['original_final_counts']==[0,0,0]
    failure=json.loads((D/'run-1/failure.json').read_bytes());failed_commands=json.loads((D/'run-1/commands.json').read_bytes());failed_cleanup=json.loads((D/'run-1/cleanup.json').read_bytes())
    assert failure['status']=='actual-failed-attempt-no-pass-credit' and failed_commands[-1]['name']=='compile' and failed_commands[-1]['exit']==1
    assert failed_cleanup['all_started_children_reaped'] and failed_cleanup['owned_scratch_removed']
    assert identity(D/'run-1/FieldFiniteControls.java')!=identity(D/'FieldFiniteControls.java')
    closure={'source_roster':identity(D/'inputs/source-roster.json'),'control':identity(D/'FieldFiniteControls.java'),'runner':identity(D/'run_controls.py'),'product_source_map':identity(D/'inputs/selected-product-source-map.json'),'product_class_map':identity(D/'inputs/selected-product-class-map.json'),'contracts':identity(D/'inputs/exact-four-subject-contracts.json'),'tools':provenance['tools']}
    closure_hash=hashlib.sha256(json.dumps(closure,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    finite=[]
    for subject in subjects.values():
        finite.append({'subject_id':subject['id'],'source_sha256':subject['source_sha256'],'class_sha256':subject['class_sha256'],'categories':subject['categories'],'required_semantic_cases':subject['required_semantic_cases'],'original_required_finite_or_enclosing_cases':subject['required_finite_or_enclosing_cases'],'original_subject_unchanged':True,'actual_direct_host_rows':counts[(subject['class'],subject['method'])],'finite_facet_status':'passed-root-review-pending','original_enclosing_semantic_cases_status':'all-retained-pending','allocation_failures':'pending','membership_release_authority_accepted':False,'native_callback_state_credit':0})
    save(D/'finite-facet-joins.json',{'schema':1,'source_context':CONTEXT,'subjects':finite,'out_of_scope':['Replacement tuple/endReady/permitsPredecessor','EditorLease and NativeField predicates','native callback states and enclosing membership/release/authority'],'full_matrix_or_release_accepted':False})
    summary={'subjects':4,'invocations':123,'assertions':result['checks'],'field_preservation_constructor_rows':16,'field_preservation_endReady_rows':76,'replacement_constructor_rows':9,'replacement_unchangedLoss_rows':22,'actual_constructor_objects':24,'actual_Input_long_returns':25,'exact_actual_Input_exceptions':2,'Input_no_call_rows':20,'endReady_exhaustive_masks':64,'host_threads_started_joined':3,'all209_classes_exact':True,'source_tool_closure_sha256':closure_hash}
    save(D/'validation.json',{'schema':1,'selected_run':'run-2','source_context':CONTEXT,'source_revision_context':receipt['source_revision_context'],'summary':summary,'original_four_subjects_byte_semantics_retained':True,'source16_B87_selected8_original_fixture_preserved':True,'all_selected_commands_pass':True,'actual_original_edit_counts_before':[2,2,3],'actual_original_edit_counts_after':[0,0,0],'failed_compile_attempt_exact_source_and_logs_retained':True,'all_children_reaped_and_owned_scratch_removed':True,'JDK_lease_preserved':True,'native_UI_capture_process_inventory_started':False,'canonical_membership_release_native_OTA_GA_accepted':False})
    members=[{'path':str(path.relative_to(D)),**identity(path)} for path in sorted(D.rglob('*')) if path.is_file() and path.name!='seal.json']
    seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'closed-four-exact-bodies-finite-host-controls-root-review-pending','selected_run':'run-2','source_context':CONTEXT,'source_revision_context':receipt['source_revision_context'],'members':members,'member_count':len(members),'member_bytes':sum(row['bytes'] for row in members),'summary':summary,'scope':'Only exact FieldPreservation constructor/endReady and Replacement constructor/unchangedLoss finite ordinary host facets; original categories/cases/enclosing/allocation obligations retained pending. No membership or release authority.','native_runtime_UI_capture_process_inventory_started':False,'physical_native_cleanup_credit':False,'full_matrix_canonical_membership_release_native_OTA_GA_accepted':False}
    save(D/'seal.json',seal)
    for row in members:assert identity(D/row['path'])=={key:row[key] for key in ('bytes','sha256')}
    print(json.dumps({'seal':identity(D/'seal.json'),'member_count':len(members),'member_bytes':seal['member_bytes'],'summary':summary},indent=2))

if __name__=='__main__':main()
