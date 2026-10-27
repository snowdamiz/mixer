#!/usr/bin/env python3
"""Root's exact four failures and analogous strict-type/refusal controls."""
import copy
import json
import unittest
from pathlib import Path
import test_typed_join as retained
import typed_join as join

class CorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        retained.TypedJoinTests.setUpClass()
        cls.fixture=retained.TypedJoinTests()
        cls.root=json.loads(Path(__file__).with_name('root-findings.json').read_text())
    def root_refusal(self,index):
        row=self.root['independent_controls'][index]['row']
        with self.assertRaises(join.Refusal):join.validate_rows(self.fixture.policy,self.fixture.doc(row))
    def test_root_boolean_bci(self):self.root_refusal(0)
    def test_root_float_opcode(self):self.root_refusal(1)
    def test_root_wrong_thread_subject_public_contradiction(self):self.root_refusal(2)
    def test_root_entry_subject_public_contradiction(self):self.root_refusal(3)
    def test_mutable_policy_numeric_type_change_refused(self):
        for key in ('source_count','editor_subject_count'):
            p=copy.deepcopy(self.fixture.policy);p[key]=float(p[key])
            with self.assertRaisesRegex(join.Refusal,'policy-object-mutation'):join.validate_rows(p,self.fixture.doc(self.fixture.row()))
    def test_mutable_policy_bool_bci_and_tuple_list_refused(self):
        p=copy.deepcopy(self.fixture.policy)
        s=next(s for s in p['subjects'] if s['method']=='performSpellCheck');s['exact_invocations'][0]['bci']=True
        with self.assertRaisesRegex(join.Refusal,'policy-object-mutation'):join.validate_rows(p,self.fixture.doc(self.fixture.row()))
        p=copy.deepcopy(self.fixture.policy);p['subjects']=tuple(p['subjects'])
        with self.assertRaisesRegex(join.Refusal,'policy-object-mutation'):join.validate_rows(p,self.fixture.doc(self.fixture.row()))
    def test_native_invocation_integer_types_strict(self):
        for name in ('bci','opcode'):
            row=self.fixture.row();row['observations']['native_invocation'][name]=float(row['observations']['native_invocation'][name])
            self.fixture.refuses(row,'native-overload-tuple-mismatch')
    def test_native_invocation_alone_is_validated(self):
        row=self.fixture.row();del row['observations']['native_outcome'];row['observations']['native_invocation']['bci']=999
        self.fixture.refuses(row,'native-overload-tuple-mismatch')
    def test_native_outcome_without_tuple_refused(self):
        row=self.fixture.row();del row['observations']['native_invocation']
        self.fixture.refuses(row,'native-overload-tuple-mismatch')
    def test_wrong_thread_native_invocation_without_outcome_forbidden(self):
        row=copy.deepcopy(self.root['independent_controls'][2]['row']);row['observations']['subject_outcome']=copy.deepcopy(row['observations']['public_outcome']);row['observations']['native_invocation']=self.fixture.row()['observations']['native_invocation']
        self.fixture.refuses(row,'wrong-thread-native-call-forbidden')
    def test_guard_public_contradiction_refused(self):
        row=self.fixture.row('commitText');subject=self.fixture.subject('commitText');row['case_id']='unsupported-argument-refuses'
        row['observations']={'subject_outcome':{'kind':'boolean','value':False},'public_outcome':{'kind':'boolean','value':True},'guard':{'expression':subject['source_guard'],'accepted':False}}
        self.fixture.refuses(row,'subject-public-result-mismatch')
    def test_constant_public_contradiction_refused(self):
        row=self.fixture.row('sendKeyEvent',value={'kind':'boolean','value':False});row['observations']['thread']='main';row['observations']['public_outcome']={'kind':'boolean','value':True}
        self.fixture.refuses(row,'subject-public-result-mismatch')
    def test_get_handler_public_contradiction_refused(self):
        row=self.fixture.row('getHandler',value={'kind':'null'});row['observations']['thread']='background';row['observations']['public_outcome']={'kind':'reference','identity':'bad@1','snapshot':{'type':'android/os/Handler','fields':{}}}
        self.fixture.refuses(row,'subject-public-result-mismatch')
    def test_guard_integer_zero_cannot_be_false(self):
        row=self.fixture.row('commitText');subject=self.fixture.subject('commitText');row['case_id']='unsupported-argument-refuses'
        row['observations']={'subject_outcome':{'kind':'boolean','value':False},'guard':{'expression':subject['source_guard'],'accepted':0}}
        self.fixture.refuses(row,'guard-observation-mismatch')
    def test_snapshot_bool_and_integer_do_not_compare_equal(self):
        row=self.fixture.row('getSelectedText',value={'kind':'reference','identity':'ref@1','snapshot':{'type':'java/lang/CharSequence','fields':{'offset':1}}})
        row['observations']['public_outcome']['snapshot']['fields']['offset']=True
        self.fixture.refuses(row,'native-public-clean-result-mismatch')

if __name__=='__main__':unittest.main(verbosity=2)
