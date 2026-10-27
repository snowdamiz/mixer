#!/usr/bin/env python3
"""Executable host validator controls; synthetic rows carry no product credit."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import typed_join as join
import example_adapter
import review_delegated_association

class TypedJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = join.load_policy()

    def subject(self, method='beginBatchEdit', cls='Base', descriptor=None):
        name = 'dev/mixer/android/NativeEditorConnectionV2'+('$'+cls if cls else '')
        return next(s for s in self.policy['subjects'] if s['class'] == name and s['method'] == method and (descriptor is None or s['descriptor'] == descriptor))

    def row(self, method='beginBatchEdit', cls='Base', descriptor=None, value=None):
        s = self.subject(method, cls, descriptor)
        native = next(q for q in self.policy['subjects'] if q['id'] == s['native_supplier_ids'][0]) if s['native_supplier_ids'] else None
        tup = next(i for i in native['exact_invocations'] if i['callee']['owner'] == 'android/view/inputmethod/InputConnection') if native else None
        value = {'kind': 'boolean', 'value': True} if value is None else value
        observations = {'subject_outcome': copy.deepcopy(value), 'public_outcome': copy.deepcopy(value)}
        if native: observations.update(native_outcome=copy.deepcopy(value), native_invocation=copy.deepcopy(tup))
        return {'subject_id': s['id'], 'case_id': '$state', 'state_id': 'clean',
            'invocation': copy.deepcopy(next((i for i in s['exact_invocations'] if i['callee']['name'] == 'call'), s['exact_invocations'][0] if s['exact_invocations'] else None)),
            'association': 'direct-body', 'observations': observations,
            'evidence': {'kind': 'method-exit', 'environment': 'synthetic-validator-test', 'receipt_sha256': 'a'*64, 'event_id': 'unit-test-only'}}

    def doc(self, *rows):
        p=self.policy
        return {'schema': join.SCHEMA, 'encoding': 'raw', 'policy_sha256': join.POLICY_SHA256,
            'context': {'product_context': p['context_id'], 'source_map_sha256': p['source_map_sha256'], 'class_map_sha256': p['class_map_sha256'], 'execution_closure_sha256': None}, 'rows': list(rows)}

    def check(self, row): return join.validate_rows(self.policy, self.doc(row))
    def good(self, row):
        result=self.check(row)
        self.assertEqual(result['typed_consistent_count'],1)
        self.assertFalse(result['qualified'])
        self.assertTrue(all(not r['qualified'] for r in result['rows']))
        return result
    def refuses(self, row, reason):
        with self.assertRaisesRegex(join.Refusal, reason): self.check(row)

    def test_exact_roster_original_cases_categories_and_history(self):
        p=self.policy
        original=json.loads((example_adapter.HERE.parent/'android-editor-membership-compiled-boundary-qualification/semantic-review-candidate-v1/active-semantic-obligations.json').read_text())
        original={s['id']:s for s in original['subjects']}
        self.assertEqual(len(p['subjects']),103)
        self.assertEqual(len({s['id'] for s in p['subjects']}),103)
        for s in p['subjects']:
            self.assertEqual(s['categories'], original[s['id']]['categories'])
            self.assertEqual(s['required_semantic_cases'], original[s['id']]['required_semantic_cases'])
            self.assertEqual([x['case_id'] for x in s['case_policies']],s['required_semantic_cases'])
            self.assertEqual([x['state_id'] for x in s['required_states']],list(join.STATES))
        self.assertEqual(len(set(p['historical189_ids'])),189)
        self.assertEqual(len(p['historical9_replacements']),9)
        self.assertEqual(len(p['out_of_scope_replacement_links']),1)
        self.assertEqual(p['out_of_scope_replacement_links'][0]['compiled_candidates'][0]['method'],'drain')

    def test_clean_boolean_exact(self): self.good(self.row())
    def test_clean_integer_exact(self): self.good(self.row('getCursorCapsMode',value={'kind':'int','value':17}))
    def test_clean_reference_snapshot_exact(self):
        self.good(self.row('getSelectedText',value={'kind':'reference','identity':'native@1','snapshot':{'type':'java/lang/CharSequence','fields':{'text':'hello','spans':[]}}}))
    def test_clean_null_exact(self): self.good(self.row('getSelectedText',value={'kind':'null'}))

    def test_reference_identity_change_refused(self):
        r=self.row('getSelectedText',value={'kind':'reference','identity':'native@1','snapshot':{'type':'java/lang/CharSequence','fields':{'text':'hello'}}})
        r['observations']['public_outcome']['identity']='other@2'
        self.refuses(r,'native-public-clean-result-mismatch')
    def test_reference_without_snapshot_refused(self):
        r=self.row('getSelectedText',value={'kind':'reference','identity':'native@1'})
        self.refuses(r,'reference-outcome-fields')
    def test_boolean_cannot_be_integer(self): self.refuses(self.row('getCursorCapsMode',value={'kind':'int','value':True}),'int-outcome-type')
    def test_integer_overflow_refused(self): self.refuses(self.row('getCursorCapsMode',value={'kind':'int','value':2**31}),'int-outcome-type')
    def test_nonboolean_truthy_value_refused(self): self.refuses(self.row(value={'kind':'boolean','value':1}),'boolean-outcome-type')

    def test_each_exact_invocation_identity_component(self):
        for key,new in [('class','foreign/Class'),('method','wrong'),('descriptor','()V'),('bci',999),('opcode',0),('source_sha256','0'*64),('class_sha256','0'*64)]:
            with self.subTest(key=key):
                r=self.row();r['invocation'][key]=new;self.refuses(r,'invocation-tuple-mismatch')
    def test_attribute_overload_cannot_use_plain_overload(self):
        r=self.row('setComposingRegion','Api33')
        r['observations']['native_invocation']['callee']['descriptor']='(II)Z'
        self.refuses(r,'native-overload-tuple-mismatch')
    def test_policy_header_drift(self):
        d=self.doc(self.row());d['policy_sha256']='0'*64
        with self.assertRaisesRegex(join.Refusal,'row-policy-digest-mismatch'):join.validate_rows(self.policy,d)
    def test_context_and_map_drift(self):
        for name in ('product_context','source_map_sha256','class_map_sha256'):
            with self.subTest(name=name):
                d=self.doc(self.row());d['context'][name]='0'*64
                with self.assertRaises(join.Refusal):join.validate_rows(self.policy,d)
    def test_policy_object_cannot_be_mutated(self):
        p=copy.deepcopy(self.policy);p['subjects'][0]['required_semantic_cases']=[]
        with self.assertRaisesRegex(join.Refusal,'policy-object-mutation'):join.validate_rows(p,self.doc(self.row()))
    def test_policy_file_digest_cannot_be_self_declared(self):
        with tempfile.TemporaryDirectory(prefix='editor-validator-test-') as d:
            p=Path(d)/'policy.json';p.write_text('{}')
            with self.assertRaisesRegex(join.Refusal,'policy-digest-mismatch'):join.load_policy(p)
    def test_candidate_expected_or_passed_status_refused(self):
        for key in ('expected','status','qualified'):
            with self.subTest(key=key):
                r=self.row();r['observations'][key]='passed';self.refuses(r,'candidate-expectation-or-unknown-observation')
    def test_duplicate_join_refused(self):
        r=self.row()
        with self.assertRaisesRegex(join.Refusal,'duplicate-subject-case-state'):join.validate_rows(self.policy,self.doc(r,r))
    def test_foreign_subject_case_and_state_refused(self):
        for key,new,reason in [('subject_id','foreign','foreign-subject'),('case_id','new-case','foreign-case'),('state_id','current','noncanonical-state')]:
            with self.subTest(key=key):
                r=self.row();r[key]=new;self.refuses(r,reason)

    def test_guard_actual_false_short_circuits(self):
        r=self.row('commitText');s=self.subject('commitText')
        r.update(case_id='unsupported-argument-refuses')
        r['observations']={'subject_outcome':{'kind':'boolean','value':False},'guard':{'expression':s['source_guard'],'accepted':False}}
        self.good(r)
        r['observations']['native_outcome']={'kind':'boolean','value':True}
        r['observations']['native_invocation']=self.row('commitText')['observations']['native_invocation']
        self.refuses(r,'guard-must-short-circuit-native')
    def test_inner_supplier_does_not_own_outer_guard(self):
        s=self.subject('lambda$commitText$6')
        r=self.row('commitText');r.update(subject_id=s['id'],case_id='unsupported-argument-refuses',invocation=next(i for i in s['exact_invocations'] if i['callee']['owner']=='android/view/inputmethod/InputConnection'))
        r['observations']={}
        result=self.check(r)
        self.assertEqual(result['rows'][0]['join'],'pending-guard-is-outside-inner-supplier')
    def test_pre_public_entry_refusal_has_no_native_call(self):
        r=self.row();r.update(case_id='terminal-before-entry-refuses',state_id='terminal-at-entry')
        r['observations']={'subject_outcome':{'kind':'boolean','value':False},'public_outcome':{'kind':'boolean','value':False}}
        self.good(r)
        r['observations'].update(native_outcome={'kind':'boolean','value':True},native_invocation=self.row()['observations']['native_invocation'])
        self.refuses(r,'entry-refusal-native-call-forbidden')
    def test_native_hook_entry_then_public_postcheck_refusal(self):
        for state in ('terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return'):
            with self.subTest(state=state):
                r=self.row();r['state_id']=state
                r['observations']['public_outcome']={'kind':'boolean','value':False}
                r['observations']['subject_outcome']={'kind':'boolean','value':False}
                self.good(r)
    def test_native_hook_entry_does_not_preserve_public_true(self):
        r=self.row();r['state_id']='terminal-at-entry';self.refuses(r,'postcheck-public-refusal-mismatch')
    def test_missing_native_is_pending(self):
        r=self.row();del r['observations']['native_outcome'];del r['observations']['native_invocation']
        self.assertEqual(self.check(r)['rows'][0]['join'],'pending-distinct-native-and-public-outcomes')
    def test_missing_actual_body_is_pending(self):
        r=self.row();del r['observations']['subject_outcome']
        self.assertEqual(self.check(r)['rows'][0]['join'],'pending-actual-subject-outcome')
    def test_ancestor_never_supplies_return_credit(self):
        r=self.row();r['association']='ancestor-presence'
        self.assertEqual(self.check(r)['rows'][0]['join'],'pending-ancestor-is-not-an-outcome')
    def test_source_analysis_cannot_supply_exit_credit(self):
        r=self.row();r['evidence']['kind']='source-analysis'
        self.assertEqual(self.check(r)['rows'][0]['join'],'pending-no-direct-method-exit')

    def test_ordinary_original_exception_exact_identity(self):
        r=self.row();r['state_id']='ordinary-throw-after-callback'
        e={'kind':'exception','identity':'original@1','class':'java/lang/IllegalStateException','fatal':False}
        r['observations'].update(subject_outcome=e,public_outcome=e,native_outcome=e,original_exception=e)
        self.good(r)
        r['observations']['public_outcome']=dict(e,identity='same-class-new-instance@2')
        self.refuses(r,'exception-identity-not-preserved')
    def test_first_fatal_exact_identity(self):
        r=self.row();r['state_id']='fatal-throw-after-callback'
        e={'kind':'exception','identity':'first@1','class':'java/lang/Error','fatal':True}
        r['observations'].update(subject_outcome=e,public_outcome=e,native_outcome=e,first_fatal=e)
        self.good(r)
    def test_exception_without_origin_is_pending(self):
        r=self.row();r['state_id']='ordinary-throw-after-callback'
        e={'kind':'exception','identity':'original@1','class':'java/lang/IllegalStateException','fatal':False}
        r['observations'].update(subject_outcome=e,public_outcome=e,native_outcome=e)
        self.assertEqual(self.check(r)['rows'][0]['join'],'pending-exact-exception-origin')
    def test_get_handler_any_thread_null(self):
        for thread in ('main','background'):
            r=self.row('getHandler',value={'kind':'null'});r.update(case_id='wrong-thread-refuses');r['observations']['thread']=thread;self.good(r)
    def test_get_handler_cannot_read_native_state(self):
        r=self.row('getHandler',value={'kind':'null'});r['observations'].update(thread='background',guard={'accepted':False})
        self.refuses(r,'getHandler-must-not-read-native-state')
    def test_wrong_thread_constant_false_method_throws_first(self):
        r=self.row('sendKeyEvent',value={'kind':'exception','identity':'wrong-thread@1','class':'java/lang/IllegalStateException','fatal':False});r.update(case_id='wrong-thread-refuses');r['observations']['thread']='background';self.good(r)
    def test_constant_unsupported_is_false_main_only(self):
        r=self.row('sendKeyEvent',value={'kind':'boolean','value':False});r['observations']['thread']='main';self.good(r)
    def test_constructors_factories_helpers_remain_pending(self):
        for method,cls in [('<init>','Base'),('create',''),('call','Base'),('nativeValue','Base'),('closeConnection','Base')]:
            r=self.row(method,cls,value={'kind':'void'})
            self.assertEqual(self.check(r)['typed_consistent_count'],0)
    def test_unsupported_callback_needs_actual_callback_body(self):
        r=self.row('performHandwritingGesture','Api34',value={'kind':'void'})
        self.assertEqual(self.check(r)['typed_consistent_count'],0)
    def test_caller_hash_cannot_grant_execution_closure(self):
        d=self.doc(self.row());d['context']['execution_closure_sha256']='b'*64
        result=join.validate_rows(self.policy,d)
        self.assertFalse(result['qualified']);self.assertTrue(result['execution_closure'].startswith('pending'))

    def test_compact_lossless_matches_raw(self):
        raw=self.doc(self.row());compact=copy.deepcopy(raw);compact.update(encoding='compact',columns=list(reversed(join.ROW_FIELDS)))
        compact['rows']=[[r[k] for k in compact['columns']] for r in raw['rows']]
        self.assertEqual(join.normalize_rows(raw),join.normalize_rows(compact))
        self.assertEqual(join.validate_rows(self.policy,raw),join.validate_rows(self.policy,compact))
    def test_compact_malformed_width_and_duplicate_columns_refused(self):
        d=self.doc();d.update(encoding='compact',columns=list(join.ROW_FIELDS),rows=[[]])
        with self.assertRaisesRegex(join.Refusal,'compact-row-width'):join.normalize_rows(d)
        d['columns'][0]=d['columns'][1]
        with self.assertRaisesRegex(join.Refusal,'compact-columns'):join.normalize_rows(d)
    def test_released_raw_compact_actual_examples(self):
        result=example_adapter.run()
        self.assertTrue(result['raw_compact_equivalent'])
        for report in result['reports'].values():
            self.assertEqual(len(report['rows']),18)
            self.assertEqual(report['typed_consistent_count'],9)
            self.assertEqual(sum(r['join']=='pending-no-direct-method-exit' for r in report['rows']),7)
            self.assertEqual(sum(r['join']=='pending-distinct-native-and-public-outcomes' for r in report['rows']),2)
            self.assertFalse(report['qualified'])
    def test_focused_source_association_review_and_coherent_refusals(self):
        report=review_delegated_association.run()
        self.assertEqual(len(report['positive_reviews']),2)
        self.assertEqual(len(report['mutation_controls']),9)
        self.assertTrue(all(x['independent_raw_join']['refused'] for x in report['mutation_controls']))
        self.assertEqual(sum(not x['producer_pair_helper']['refused'] for x in report['mutation_controls']),5)
        self.assertFalse(report['qualified'])

if __name__ == '__main__': unittest.main(verbosity=2)
