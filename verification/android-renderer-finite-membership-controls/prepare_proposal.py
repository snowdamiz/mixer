#!/usr/bin/env python3
"""Join finite actual results to unchanged original subjects/cases, retaining enclosing obligations."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import sys
D=Path(__file__).resolve().parent

def identity(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(name,data):
    (D/name).write_text(json.dumps(data,indent=2)+'\n')

def main():
    original=json.loads((D/'inputs/original-six-subjects.json').read_bytes())['subjects']
    semantic=json.loads((D/'inputs/original-six-semantic-proposals.json').read_bytes())['subjects']
    actual=json.loads((D/'run-3/actual-results.json').read_bytes())
    assert actual['invocations']==142 and actual['original_final_counts']==[0,0,0]
    assert len(original)==len(semantic)==6
    results=identity(D/'run-3/actual-results.json')
    def join(indices,scope):
        return {'results':{'path':'run-3/actual-results.json',**results},'row_indices_zero_based':indices,'control_source':identity(D/'FiniteMembershipControls.java'),
                'source_context':actual['source_context'],'proof_scope':scope,'enclosing_obligations_accepted':False}
    packet=[]
    semantic_out=[]
    for source in original:
        subject=copy.deepcopy(source)
        indices=[i for i,row in enumerate(actual['rows']) if row['subject_id']==source['id']]
        assert indices
        cases=[]
        for case in source['required_semantic_cases']:
            if case=='allocation-failure-source-proof-only-pending-runtime':
                chosen=[];scope='No allocation-failure runtime execution supplied; original case remains pending.'
            elif case=='duplicate-or-foreign-state-refuses':
                chosen=[i for i in indices if any(term in actual['rows'][i]['control_case'] for term in ('foreign','duplicate','reordered','wrong','malformed','null-candidate-journal'))]
                scope='Only actual scalar rejection/classifier branch outcomes for the exact subject, including malformed-but-accepted classifier states where applicable. No enclosing refusal/effect authority.'
            elif case=='held-failure-funded-membership':
                chosen=[i for i in indices if any(term in actual['rows'][i]['control_case'] for term in ('count','roster','membership','ended-release','capture','actual-','provenance'))]
                scope='Only finite exact membership/capture/classifier/count relationships. Funding is not healthy release authority; captured/provenance/identity subjects do not acquire count authority.'
            elif case=='ordered-constructor-bound-membership':
                chosen=indices
                scope='Only direct finite method identity/boolean/typed-failure outcomes against actual constructor-bound objects and deliberately restored test states. Classifier acceptance of malformed own states is retained.'
            elif case=='no-tail-callback-before-complete-roster':
                chosen=indices
                scope='Only purity: each direct call leaves native event prefix, NativeBridge counters/references and all relevant object fields/arrays unchanged. Actual enclosing callback ordering remains pending.'
            elif case=='same-first-fatal':
                chosen=indices
                scope='Only exact primary/first Error object identity preservation under pure direct calls, using ordinary test-only seeded references restored afterward. No exception transport, fatal ordering or enclosing cleanup acceptance.'
            else:raise AssertionError(case)
            cases.append({'original_case_id':case,'status':'pending-enclosing-or-runtime-obligation','finite_execution_join':join(chosen,scope) if chosen else None,'scope':scope,'original_case_accepted':False})
        subject['finite_control_extension']={'status':'finite-direct-host-results-root-selection-pending','independent_invocations':len(indices),'finite_execution_join':join(indices,'Exact six-method finite direct host result/purity controls only'),
            'original_case_dispositions':cases,'all_original_categories_cases_preserved':True,'original_case_or_subject_accepted':False}
        assert subject['categories']==source['categories'] and subject['required_semantic_cases']==source['required_semantic_cases']
        packet.append(subject)
        prepared=copy.deepcopy(next(s for s in semantic if s['id']==source['id']))
        for case in prepared['required_cases']:
            if case['id']=='renderer-finite-source-invariants':
                case['execution_join']=join(indices,'Direct finite host result/purity control only; no enclosing obligation acceptance')
                case['status']='finite-host-observed-root-selection-pending'
                case['pending_reason']='Root must independently select policy and final producer joins; enclosing original control remains unexecuted by this packet.'
            else:
                assert case['execution_join'] is None
                case['status']='pending-enclosing-original-control'
        semantic_out.append(prepared)
    save('proposal.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'six-exact-finite-results-review-pending',
        'source_context':actual['source_context'],'source_revision_context':'6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2','original_full280_checklist':json.loads((D/'inputs/original-six-subjects.json').read_bytes())['checklist'],
        'original_subject_count':6,'original_ids_categories_cases_preserved':True,'subjects':packet,'selected_prepared_semantic_subjects':semantic_out,
        'complete_matrix_policy_canonical_native_OTA_GA_accepted':False,'generator':identity(Path(__file__)),'command':[sys.executable,'-B',str(Path(__file__))]})
    save('manifest.json',{'schema':1,'status':'closed-finite-host-packet-root-review-pending','selected_run':'run-3','invocations':actual['invocations'],
        'assertions':actual['checks'],'assertion_count_explanation':'11,035,945 is repeated deep field/array/collection/native-event comparison work across 142 independent direct calls; it is not 11 million semantic cases or callback coverage.',
        'per_subject':{s['method']:sum(row['subject_id']==s['id'] for row in actual['rows']) for s in original},
        'exact_product16_B87_all209_context_reproduced':True,'source_context':actual['source_context'],'results':results,
        'subject_ids':[s['id'] for s in original],'original_case_ids':original[0]['required_semantic_cases'],
        'attempts':[{'run':'run-1','status':'failed-authoring-no-pass-credit','reason':'full matrix reached output serialization, then boxed integer JSON authoring error; no results/receipt accepted'},
                    {'run':'run-2','status':'passed-superseded','invocations':136,'checks':10572874},
                    {'run':'run-3','status':'selected-finite-host-pass-root-review-pending','invocations':142,'checks':actual['checks']}],
        'original_boundary':actual['original_boundary'],'actual_counts':{'held_global_shared_at_entry':[2,2,3],'after_original_edit':[0,0,0]},
        'all_direct_calls_pure_zero_native_effects':True,'no_special_allocation_predicate_copy_or_product_rewriting':True,
        'cleanup':json.loads((D/'run-3/cleanup.json').read_bytes()),'enclosing_original_cases_all_pending':True,'canonical_native_OTA_GA_accepted':False})
    save('validation.json',{'original_six_ids_preserved':{s['id'] for s in original}=={s['id'] for s in semantic_out},'original_categories_and_semantic_case_lists_preserved':True,
        'actual_result_row_count':len(actual['rows']),'unique_control_cases':len({(r['subject_id'],r['control_case']) for r in actual['rows']}),
        'all_outcomes_equal_independent_literal_expected':all(r['expected']==r['actual'] for r in actual['rows']),
        'all_counts_unchanged':all(r['counts_before']==r['counts_after'] for r in actual['rows']),
        'all_snapshot_digests_unchanged':all(r['snapshot_before_sha256']==r['snapshot_after_sha256'] for r in actual['rows']),
        'all_zero_native_effects':all(r['native_effects']==0 and r['native_events_before']==r['native_events_after'] for r in actual['rows']),
        'all_enclosing_execution_joins_null':all(c['execution_join'] is None for s in semantic_out for c in s['required_cases'] if c['id']!='renderer-finite-source-invariants'),
        'context':actual['source_context'],'run3_compile_identity':identity(D/'run-3/compile-identity.json'),'run3_cleanup':identity(D/'run-3/cleanup.json')})
    print('Prepared six original subject/case joins; 142 finite direct rows; enclosing obligations remain pending.')
if __name__=='__main__':main()
