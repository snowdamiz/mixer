#!/usr/bin/env python3
"""Host source/evidence and comparator adversarial checks; no product runtime."""
import json
from pathlib import Path
import re
import sys
import unittest

sys.dont_write_bytecode=True
from prepare import HERE,PROFILE,ACCOUNT,accepted_source,transform,manifest,query_source,sha
from review import normalize,strip_comment,is_inert

def data(name): return json.loads((HERE/name).read_bytes())

class SourceAndEvidenceTests(unittest.TestCase):
    def test_all_146_source_members_reproduce_and_only_profile_changes(self):
        source,custody=accepted_source(); old=manifest(source)
        transformed,edits=transform(source[PROFILE]);source[PROFILE]=transformed
        expected=data('source-manifest.json')
        self.assertEqual(manifest(source),expected)
        self.assertEqual(len(custody),146)
        self.assertEqual(edits,data('exact-edits.json'))
        self.assertEqual([x['path'] for x,y in zip(old['members'],expected['members']) if x!=y],[PROFILE])
        for name,value in source.items():self.assertEqual(value,(HERE/'source/vm'/name).read_bytes())

    def test_inert_query_sources_reproduce(self):
        base=data('source-manifest.json');source={x['path']:(HERE/'source/vm'/x['path']).read_bytes() for x in base['members']}
        for mode in ['positive','negative']:
            query=query_source(source,mode)
            self.assertEqual(manifest(query),data(mode+'-source-manifest.json'))
            self.assertEqual({k for k in source if source[k]!=query[k]},{PROFILE,ACCOUNT})
            self.assertTrue(query[PROFILE].endswith(b'\n}\n}\n'))

    def test_selectors_stay_pending_and_no_authority_constructor_added(self):
        before,_=accepted_source(); old=before[PROFILE].decode(); new=(HERE/'source/vm'/PROFILE).read_text()
        for name in ['selected_outer_request_v1','run_one_fixture_v1','setup_files_once_v1','run_prepaid_fixture_v1','consume_outer_request_v1']:
            # Balanced source bodies, not authorization for OTA. Runtime MIR
            # equality separately binds all actual operations.
            def body(text):
                start=text.index('fn '+name);start=text.index('{',start);depth=0
                for i in range(start,len(text)):
                    depth += (text[i]=='{')-(text[i]=='}')
                    if depth==0:return text[start:i+1]
                self.fail('unclosed '+name)
            self.assertEqual(body(old),body(new))
        self.assertIn('Err(BindingSelectionRefusalV1::ImmutableBindingAndP0ReviewPending)',new)
        self.assertNotIn('scoped_local_binding_compiles_v1',new)
        self.assertNotIn('reject_escaping_request_v1',new)

    def test_exact_compiler_terminal_and_cleanup_evidence(self):
        for mode,code in [('positive',0),('negative',1)]:
            receipt=data('commands/compiler-'+mode+'/receipt.json')
            self.assertEqual(receipt['exit_code'],code)
            self.assertEqual(receipt['compiler_invocations'],1)
            for field in ['child_reaped','owned_group_absent','owned_scratch_removed','expected_terminal_status_observed']:self.assertTrue(receipt[field])
            for field in ['timed_out','cfg_test','codegen','product_test_native_runtime']:self.assertFalse(receipt[field])
            self.assertLess(receipt['elapsed_seconds'],55)
            self.assertFalse((HERE/'owned-work'/mode).exists())
        self.assertEqual(data('negative-results.json')['actual_codes'],['E0515','E0515','E0506','E0505','E0382'])

    def test_all_production_mir_and_layouts_equal(self):
        report=data('mir-comparison.json')
        self.assertTrue(report['equality']);self.assertEqual(report['before_functions'],2020)
        self.assertEqual(report['before_blocks'],4221);self.assertEqual(report['differing_blocks'],0)
        self.assertEqual(report['before_allocations'],1953)
        self.assertEqual(report['before_normalized_sha256'],report['after_normalized_sha256'])
        layouts=data('layouts.json');self.assertEqual(len(layouts['rows']),46)
        self.assertTrue(layouts['first_44_identical']);self.assertTrue(layouts['result_two_match'])

    def test_normalizer_retains_semantic_mutations(self):
        base='fn f() -> usize {\n    _0 = const 7_usize;\n    return;\n}'
        for mutant in [base.replace('7_usize','8_usize'),base.replace('return;','drop(_1) -> [return: bb1, unwind continue];'),base.replace('_0 =','_1 ='),base.replace('usize','u64')]:
            self.assertNotEqual(normalize(base),normalize(mutant))
        types="fn f(_1: FrozenFixtureV1<'_>) {\n    return;\n}"
        self.assertEqual(normalize(types),normalize(types.replace("<'_>",'')))
        unrelated="fn f(_1: SomeOtherType<'_>) {\n    return;\n}"
        self.assertNotEqual(normalize(unrelated),normalize(unrelated.replace("<'_>",'')))
        literal='fn f() {\n    _0 = const "FrozenFixtureV1::<'+"'_"+'> // alloc27";\n}'
        self.assertIn('alloc27',normalize(literal,{'alloc27':'alloc2'}))
        self.assertIn('// alloc27',normalize(literal,{'alloc27':'alloc2'}))

    def test_allocation_correspondence_preserves_payload_and_relocations(self):
        a='alloc2 (size: 2, align: 1) {\n    01 02\n    pointer alloc1\n}'
        b='alloc6 (size: 2, align: 1) {\n    01 02\n    pointer alloc5\n}'
        mapping={'alloc6':'alloc2','alloc5':'alloc1'}
        self.assertEqual(normalize(a),normalize(b,mapping))
        for mutant in [b.replace('01 02','01 03'),b.replace('size: 2','size: 3'),b.replace('align: 1','align: 8'),b.replace('pointer alloc5','pointer alloc6')]:
            self.assertNotEqual(normalize(a),normalize(mutant,mapping))

    def test_only_named_inert_queries_excluded(self):
        self.assertTrue(is_inert('fn scoped_local_binding_compiles_v1() {\n}'))
        self.assertFalse(is_inert('fn consume_outer_request_v1() {\n}'))
        self.assertFalse(is_inert('fn scoped_local_binding_compiles_v1_mutant() {\n}'))
        self.assertEqual(strip_comment('    _0 = const "// literal"; // span'),'    _0 = const "// literal";')

if __name__=='__main__':unittest.main(verbosity=2)
