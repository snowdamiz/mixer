#!/usr/bin/env python3
"""Read-only all-state positives and hostile raw-data controls."""
import copy
import gzip
import hashlib
import json
import unittest
from pathlib import Path
import delegated_raw as api

HERE=Path(__file__).resolve().parent
PACKET=HERE.parent/'android-editor-membership-compiled-boundary-qualification/delegated-overload-association'
SEAL='68916bf61a5204f022c7e0e6190dd698f621924b25389c3ffcd4989fbbed3104'
FILES=['producer-run/direct-setComposingRegionWithAttributes.rows.jsonl.gz','standalone-replay/attribute-states.rows.jsonl.gz']

def read_inputs():
    assert hashlib.sha256((PACKET/'seal.json').read_bytes()).hexdigest()==SEAL
    manifest=json.loads((PACKET/'seal.json').read_text())['members']
    inputs={}
    for name in FILES:
        path=PACKET/name;entry=next(x for x in manifest if x['path']==name)
        assert path.stat().st_size==entry['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
        with gzip.open(path,'rt') as stream:inputs[name]=[json.loads(line) for line in stream]
        assert len(inputs[name])==13 and {r['state'] for r in inputs[name]}==set(api.load_policy()['states'])
    return inputs

def own(row):return [x for x in row['actual_native_outcomes'] if x['method']=='BaseInputConnection.setComposingRegion']
def both(row,fn):
    for item in own(row):fn(item)
def coherent_receiver(row):
    selected=own(row);row['original_target']='android.view.inputmethod.BaseInputConnection@999'
    for item in selected:item['receiver_identity']=row['original_target']
def intervening(row):
    at=own(row)[0]['native_event_sequence_index'];event=copy.deepcopy(row['native_sequence'][at]);event['phase']='entry';row['native_sequence'].insert(at+1,event);row['operation_end_sequence']+=1

MUTATIONS={
    'wrong-one-frame':lambda r:own(r)[1].__setitem__('production_frames',[]),
    'missing-both-frames':lambda r:both(r,lambda i:i.__setitem__('production_frames',[])),
    'coherent-truncated-frame-chain':lambda r:both(r,lambda i:i.__setitem__('production_frames',i['production_frames'][:1])),
    'coherent-wrong-event-index':lambda r:both(r,lambda i:i.__setitem__('native_event_sequence_index',i['native_event_sequence_index']+1)),
    'coherent-wrong-receiver':coherent_receiver,
    'coherent-wrong-native-value':lambda r:both(r,lambda i:i.__setitem__('value',{'kind':'boolean','value':False})),
    'wrong-outer-descriptor':lambda r:own(r)[1].__setitem__('descriptor','(II)Z'),
    'intervening-raw-native-entry':intervening,
    'duplicate-outer-completion':lambda r:r['actual_native_outcomes'].append(copy.deepcopy(own(r)[1])),
}

def review():
    inputs=read_inputs();positives={}
    for name,rows in inputs.items():positives[name]=[api.validate_delegated_raw(row) for row in rows]
    base=inputs[FILES[0]][0];controls=[]
    for name,mutation in MUTATIONS.items():
        row=copy.deepcopy(base);mutation(row)
        try:api.validate_delegated_raw(row)
        except api.DelegatedRawRefusal as failure:controls.append({'name':name,'refused':True,'reason':str(failure)})
        else:raise AssertionError('accepted hostile raw data: '+name)
    return {'schema':1,'input_packet_sha256':SEAL,'policy_sha256':api.POLICY_SHA256,'positive_rows':positives,'negative_controls':controls,'all_26_rows_consistent':True,'all_original_9_controls_refused':True,'native_normal_body_completion_exceptions':'pending, never inferred from hook-exception','full_matrix_execution_closure_native_OTA_GA':'pending','qualified':False}

class DelegatedRawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.rows=read_inputs()[FILES[0]]
    def get(self,state='current'):return copy.deepcopy(next(r for r in self.rows if r['state']==state))
    def refuses(self,row):
        with self.assertRaises(api.DelegatedRawRefusal):api.validate_delegated_raw(row)
    def test_all_26_actual_rows_and_original_9_controls(self):
        result=review();self.assertEqual(len(result['negative_controls']),9)
        self.assertEqual(sum(map(len,result['positive_rows'].values())),26)
        self.assertFalse(result['qualified'])
    def test_pre_public_refusal_not_native_hook_entry(self):
        for state in ('terminal','dirty','stale','changing'):
            r=api.validate_delegated_raw(self.get(state));self.assertEqual(r['native_entries'],0);self.assertEqual(r['native_result'],'not-entered')
        for state in ('terminal-at-entry','dirty-at-entry'):
            r=api.validate_delegated_raw(self.get(state));self.assertEqual(r['native_entries'],1);self.assertEqual(r['native_result'],{'kind':'boolean','value':True});self.assertEqual(r['public_outcome'],{'kind':'boolean','value':False})
    def test_hook_exception_identity_not_native_scalar_body_result(self):
        for state in ('fatal','ordinary-throw-after-callback','fatal-throw-after-callback'):
            r=api.validate_delegated_raw(self.get(state));self.assertEqual(r['actual_normal_native_returns'],0);self.assertTrue(r['native_result'].startswith('pending'))
            self.assertEqual(r['actual_hook_exception'],r['public_outcome']);self.assertFalse(r['qualified'])
    def test_compact_projection_cannot_self_admit(self):
        row=self.get();del row['native_sequence'];del row['frame_sets'];self.refuses(row)
    def test_source_frame_bci_and_line_strict_integer_types(self):
        for key in ('bci','line'):
            row=self.get();frame=row['frame_sets'][row['selected_event'][0]['frame_set']][0];frame[key]=float(frame[key]);self.refuses(row)
        row=self.get();own(row)[0]['production_frames'][0]['bci']=7.0;self.refuses(row)
    def test_event_index_and_frame_set_strict_integer_types(self):
        for key in ('sequence_index','frame_set'):
            row=self.get();row['selected_event'][0][key]=float(row['selected_event'][0][key]);self.refuses(row)
        row=self.get();own(row)[0]['native_event_sequence_index']=125.0;self.refuses(row)
    def test_missing_one_and_both_native_returns_refuse_every_normal_state(self):
        for state in ('current','successor','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return'):
            row=self.get(state);pair=own(row);row['actual_native_outcomes']=[x for x in row['actual_native_outcomes'] if x is not pair[1]];self.refuses(row)
            row=self.get(state);row['actual_native_outcomes']=[x for x in row['actual_native_outcomes'] if x['method']!='BaseInputConnection.setComposingRegion'];self.refuses(row)
    def test_foreign_receiver_or_bad_completion_never_filtered_out(self):
        row=self.get();own(row)[1]['receiver_identity']='foreign@1';self.refuses(row)
        row=self.get();own(row)[1]['completion']='unknown';self.refuses(row)
    def test_wrong_selected_state_phase_and_wrong_full_chain(self):
        row=self.get('terminal-at-entry');row['selected_event'][0]['sequence_index']=own(row)[0]['native_event_sequence_index'];self.refuses(row)
        row=self.get();own(row)[0]['production_frames'][1]['method']='other';self.refuses(row)
    def test_missing_or_changed_hook_exception_and_first_fatal_refused(self):
        for state in ('fatal','ordinary-throw-after-callback','fatal-throw-after-callback'):
            row=self.get(state);own(row)[0]['original_exception_identity']='different@1';self.refuses(row)
            row=self.get(state);row['actual_native_outcomes']=[x for x in row['actual_native_outcomes'] if x['method']!='BaseInputConnection.setComposingRegion'];self.refuses(row)
        row=self.get('fatal');row['post_operation_authority']['editor']['firstFatal']='different@2';self.refuses(row)
    def test_boolean_scalar_cannot_be_numeric_and_entry_count_cannot_be_boolean(self):
        row=self.get();own(row)[1]['value']={'kind':'boolean','value':1};self.refuses(row)
        row=self.get();row['native_target_entries']=True;self.refuses(row)
        row=self.get('terminal');row['actual_operation_outcome']={'kind':'boolean','value':0};self.refuses(row)
    def test_row_not_mutated_and_status_cannot_grant_qualification(self):
        row=self.get();row['status']='passed';row['original_result_expected']='candidate-wish';before=json.dumps(row,sort_keys=True)
        result=api.validate_delegated_raw(row);self.assertFalse(result['qualified']);self.assertEqual(json.dumps(row,sort_keys=True),before)
    def test_context_and_corrected_dependency_policy_pins(self):
        policy=api.load_policy();dep=policy['mandatory_corrected_dependency']
        self.assertEqual(dep['module_sha256'],'c3a24d05de9670b404357f509a8e1b42924a83cc0c43342a9cdc6630862722db')
        self.assertEqual(policy['product_context'],'1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd')

if __name__=='__main__':unittest.main(verbosity=2)
