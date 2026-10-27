#!/usr/bin/env python3
"""Close and verify finite source-specific host evidence; grants no qualification."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import sys
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
ROOT=D.parent.parent
CONTEXT='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
def identity(p):
    data=p.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    sealpath=D/'seal.json'
    if sealpath.exists():
        seal=json.loads(sealpath.read_bytes());assert seal['selected_run']=='run-3' and seal['source_context']==CONTEXT
        expected={r['path']:r for r in seal['members']}
        actual={str(p.relative_to(D)) for p in D.rglob('*') if p.is_file() and p!=sealpath}
        assert actual==set(expected),'packet member set changed'
        for name,row in expected.items():assert identity(D/name)=={'bytes':row['bytes'],'sha256':row['sha256']},name
        print('PASS immutable finite observation packet',len(expected),'members; seal',identity(sealpath)['sha256']);return
    run=D/'run-3';result=json.loads((run/'actual-results.json').read_bytes());receipt=json.loads((run/'receipt.json').read_bytes());commands=json.loads((run/'commands.json').read_bytes());cleanup=json.loads((run/'cleanup.json').read_bytes());compile_id=json.loads((run/'compile-identity.json').read_bytes())
    assert result['source_context']==CONTEXT and result['invocations']==56 and result['checks']==731
    assert result['original_edit_completed_after_restores'] and result['actual_original_boundary_counts']==[2,2,3] and result['actual_final_counts']==[0,0,0]
    assert result['getter_entries']==result['checking_true_at_entries']==22 and result['host_threads_started']==result['host_threads_joined']==2
    assert result['no_final_field_or_exhaustion_mutations'] and result['failure_latch_clear']
    assert len(commands)==4 and all(r['exit']==0 and not r['timeout'] and r['reaped'] and r['elapsed_seconds']<60 for r in commands)
    for r in commands:
        for stream in ('stdout','stderr'):
            streamrow=r[stream];assert identity(run/streamrow['path'])=={'bytes':streamrow['bytes'],'sha256':streamrow['sha256']}
    argv=commands[2]['argv'];assert '--release' in argv and argv[argv.index('--release')+1]=='17' and '-proc:none' in argv and '-Xlint:all' in argv and '-Werror' in argv and not any(x=='-g' or x.startswith('-g:') for x in argv)
    assert cleanup['all_started_children_reaped'] and cleanup['maximum_concurrent_children']==1 and cleanup['owned_scratch_removed'] and cleanup['jdk_tool_lease_preserved'] and not cleanup['process_inventory_or_other_projects_touched'] and cleanup['native_instances_started']==0
    assert compile_id['source_context']==CONTEXT and compile_id['all_209_exact_matches'] and compile_id['product_classes']==209 and compile_id['product_sources']==16 and not compile_id['BCI_remapping']
    assert identity(D/'FieldObservationControls.java')==identity(run/'FieldObservationControls.java')==receipt['control'] and identity(D/'run_controls.py')==identity(run/'run_controls.py')==receipt['runner']
    assert identity(run/'actual-results.json')==receipt['results']
    original=json.loads((D/'inputs/original-280-obligations.json').read_bytes());contracts=json.loads((D/'inputs/exact-four-subject-contracts.json').read_bytes())
    assert len(original['subjects'])==280 and len({r['id'] for r in original['subjects']})==280
    selected={r['id']:r for r in contracts['subjects']};assert len(selected)==4
    for r in original['subjects']:
        if r['id'] in selected:assert r==selected[r['id']] and len(r['required_semantic_cases'])==8
    methods=collections.Counter(r['subject_id'] for r in result['rows']);assert set(methods)==set(selected)
    counts={'tuple':29,'capture':4,'exact':19,'continuation':4}
    for key,r in selected.items():assert methods[key]==counts[r['method']]
    direct=0;getters=0
    for row in result['rows']:
        assert row['class_sha256']==selected[row['subject_id']]['class_sha256'] and row['original_eight_cases_retained_without_discharge'] and row['no_membership_release_authority']
        assert row['counts_before']==row['counts_after']==[2,2,3] and row['restored_before_original_edit_resumes'] and row['actual_Input'] is None
        assert row['exact_Input_invocation_counts_and_BCIs'].startswith('pending: original final Input unchanged')
        oracle=row['independent_expected_before_invocation'];support=oracle.get('separate_support_call')
        if support is not None:
            direct+=1;assert support['method']=='editorLossObservation' and support['descriptor']=='()J' and 'no claim about tuple call count/BCI' in support['attribution']
        for outcome in row['actual_native_getter_outcomes']:
            getters+=1;assert outcome['checking_at_outcome'] and outcome['method']=='TextView.getEditableText' and len(outcome['production_frames'])<24
            assert any(f['class']=='dev.mixer.android.NativeAppearanceViewsV2$FieldPreservation' and f['method']=='exact' and f['descriptor']=='()V' and f['bci']==40 for f in outcome['production_frames'])
            if outcome['completion']=='return':assert outcome['returned_editable_immutable_value']['reference']==outcome['actual_value_reference']
            else:assert outcome['completion']=='exception' and outcome['exception_reference']==row['exact_exception_reference']
    assert direct==7 and getters==22
    historical=json.loads((D/'inputs/historical189-custody.json').read_bytes());assert historical['unchanged'] and identity(ROOT/historical['path'])=={'bytes':historical['bytes'],'sha256':historical['sha256']}
    failed=json.loads((D/'run-1/failure.json').read_bytes());assert failed['status']=='actual-failed-attempt-no-pass-credit';assert json.loads((D/'run-1/commands.json').read_bytes())[-1]['exit']==1
    for name in ('run-1','run-2','run-3'):
        c=json.loads((D/name/'cleanup.json').read_bytes());assert c['all_started_children_reaped'] and c['owned_scratch_removed'] and c['jdk_tool_lease_preserved']
    facets=[]
    for subject_id,subject in selected.items():
        facets.append({'subject_id':subject_id,'source_context':CONTEXT,'source_sha256':subject['source_sha256'],'class_sha256':subject['class_sha256'],'categories':subject['categories'],'original_subject_record':{'path':'inputs/exact-four-subject-contracts.json','selection':'subjects.id == subject_id'},'actual_row_indexes':[i for i,r in enumerate(result['rows']) if r['subject_id']==subject_id],'actual_finite_invocations':methods[subject_id],'selected_result':{'path':'run-3/actual-results.json',**identity(run/'actual-results.json')},'finite_facet_only':True,'original_required_semantic_cases':[{'case':case,'status':'pending-original-enclosing-case-not-discharged-by-these-finite-facets'} for case in subject['required_semantic_cases']],'allocation_exceptional_partial_output_obligations':'pending','canonical_qualification':'not-granted'})
    save(D/'finite-facet-joins.json',{'schema':1,'source_context':CONTEXT,'all280_original_subjects_retained':True,'historical189_plus5_preserved':historical,'exact_Input_counts_and_BCIs':'pending-original-final-Input-unchanged','subjects':facets,'authority':'none; root independent review and producer selection pending'})
    fields=[('reference','FieldPreservation'),('field','NativeField'),('record','Record'),('original','Mutation'),('selected','Binding'),('editable','Editable'),('renderer','NativeRenderer'),('candidate','NativeRenderer.Candidate'),('journal','NativeRenderer.AttachmentJournal'),('before','Binding'),('predecessor','NativeField.Attempt'),('disposition','NativeField.Close'),('loss_observation','long'),('snapshot','EditorSnapshot'),('phase','int'),('entered','boolean'),('ended','boolean'),('checking','boolean'),('counted','boolean'),('released','boolean'),('release_ready','boolean'),('callbacks','int'),('hooks_reference','ArrayDeque<String>'),('hooks_values','immutable List<String>')]
    save(D/'typed-snapshot-schema.json',{'schema':1,'receiver_capture':'immutable typed Java FrozenField record; referenced mutable objects are paired with immutable value captures','captured_receiver_field_order':[{'json_name':k,'java_type':t} for k,t in fields],'EditorSnapshot_capture_field_order':['text:String (identity and content)','start:int','end:int','spans:Object[] (array identity and immutable ordered element identities)','bounds:int[] (array identity and immutable ordered integer values)'],'buffer_capture':'immutable reference/text/selection/span identity/start/end/flags values at native outcome','identities':'IdentityHashMap-assigned object identities, never content equality; null is literal string null for reference fields','numeric_scope':'actual long values serialized as integral JSON numbers; exact Python validator parses integers without truncation'})
    save(D/'validation.json',{'schema':1,'status':'passed-source-specific-finite-host-packet-root-review-pending','selected_run':'run-3','source_context':CONTEXT,'subject_bodies':4,'invocations':56,'assertions':731,'actual_getter_outcomes':22,'actual_direct_Input_support_returns':7,'original280_unchanged':True,'original189_plus5_unchanged':True,'original_eight_cases_each_retained_pending':True,'exact_Input_subject_counts_and_BCIs':'pending','all209_product_classes_exact':True,'run1_failed_preflight_retained':True,'run2_pass_retained':True,'all_owned_cleanup_complete':True,'native_or_GA_credit':False})
    paths=sorted(p for p in D.rglob('*') if p.is_file() and p!=sealpath)
    members=[{'path':str(p.relative_to(D)),**identity(p)} for p in paths]
    save(sealpath,{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'closed-four-exact-observation-bodies-finite-host-packet-root-review-pending','selected_run':'run-3','source_context':CONTEXT,'source_revision_context':receipt['source_revision_context'],'members':members,'member_count':len(members),'member_bytes':sum(r['bytes'] for r in members),'qualification':'finite facets only; all original cases/enclosing/exceptional allocation obligations pending','permissions':'host JVM only; no final Record field replacement, no native/runtime/UI/capture/inventory or Git/index mutations'})
    print('CLOSED',len(members),'members; seal',identity(sealpath)['sha256'])
if __name__=='__main__':main()
