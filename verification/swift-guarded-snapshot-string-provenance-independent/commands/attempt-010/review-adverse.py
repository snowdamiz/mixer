#!/usr/bin/env python3
"""Independently authored fail-closed expectations; known failures are evidence.

This intentionally fails against the frozen producer. It never rewrites it.
Synthetic MIR is a parser control, not a compiled product fixture or execution.
"""
import importlib.util,json,pathlib,sys,unittest
D=pathlib.Path(__file__).resolve().parent;P=D.parent/'swift-guarded-snapshot-string-provenance'
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('frozen_producer_graph',P/'mir_graph.py')
producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
spec2=importlib.util.spec_from_file_location('frozen_producer_check',P/'check.py')
sys.modules['mir_graph']=producer
checker=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(checker)
class FailClosedExpectations(unittest.TestCase):
    def test_unknown_reference_trait_producer_must_refuse(self):
        with self.assertRaises(producer.Refused):
            producer.classify_external('<&ForeignFailure as ForeignFactory>::new',['&ForeignFailure'])
    def test_unknown_generic_trait_producer_must_refuse(self):
        with self.assertRaises(producer.Refused):
            producer.classify_external('<Option<ForeignFailure> as ForeignFactory>::take',['ForeignFailure'])
    def test_comparison_basename_must_not_authorize_unknown_trait(self):
        with self.assertRaises(producer.Refused):
            producer.classify_external('<ForeignFailure as ForeignFactory>::eq',['ForeignFailure'])
    def test_unreviewed_std_namespace_must_refuse(self):
        with self.assertRaises(producer.Refused):
            producer.classify_external('std::future_vendor::take',['ForeignFailure'])
    def test_nested_scope_str_assignments_must_be_censused(self):
        mir='''fn nested() -> () {
    scope 1 {
        let _1: &str;
    }
    bb0: {
        _1 = const "nested_string";
        return;
    }
}
'''
        functions,_,_=producer.parse_functions(mir,{})
        self.assertEqual(len(functions['f0000']['str_assignments']),1)
    def test_named_callback_must_be_censused(self):
        mir='''fn entry(_1: Option<&Foreign>) -> Option<ForeignFailure> {
    let mut _0: Option<ForeignFailure>;
    bb0: {
        _0 = Option::<&Foreign>::map::<ForeignFailure, fn(&Foreign) -> ForeignFailure {Foreign::make}>(move _1, Foreign::make) -> [return: bb1, unwind continue];
    }
    bb1: {
        return;
    }
}
'''
        functions,_,_=producer.parse_functions(mir,{})
        call=functions['f0000']['calls'][0]
        self.assertIn('Foreign::make',call['callbacks'])
    def test_actual_multibyte_byte_bound_stays_fail_closed(self):
        self.assertEqual(checker.bound_text('é'*2540,5080)['utf8_bytes'],5080)
        self.assertEqual(checker.bound_text('😀'*1270,5080)['utf8_bytes'],5080)
        for value in ['é'*2541,'😀'*1271,'a'*5081,'\ud800']:
            with self.assertRaises(producer.Refused):checker.bound_text(value,5080)
    def test_existing_frozen_omissions_are_reproducible(self):
        independent=json.loads((D/'typed-graph.json').read_text());frozen=json.loads((P/'graph.json').read_text())
        self.assertEqual(sum(len(r['string_assignments']) for r in independent['nodes'].values()),80)
        self.assertEqual(len(frozen['source_str_assignments']),78)
        for key in ('f1605','f1697','f1899','f1900','f1927','f1928'):
            self.assertIn(key,independent['nodes']);self.assertNotIn(key,frozen['nodes'])
if __name__=='__main__':unittest.main(verbosity=2)
