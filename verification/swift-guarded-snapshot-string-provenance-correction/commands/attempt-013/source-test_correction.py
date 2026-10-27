#!/usr/bin/env python3
"""Deterministic controls for R1-R5; synthetic MIR is never compiled/run."""
import copy,json,unittest
from pathlib import Path
import mir_graph as p
D=Path(__file__).resolve().parent

def mini(body,helpers=''):
    roots=[]
    for name in p.ROOTS:
        roots.append('fn '+name+'() -> () {\n    let mut _0: ();\n    bb0: {\n'+(body if name==p.ROOTS[0] else '        return;\n')+'    }\n}\n')
    return '\n'.join(roots)+'\n'+helpers

class CorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=json.loads((D/'graph.json').read_text())
        cls.induction=json.loads((D/'carrier-induction.json').read_text())
    def refuse(self,fn,*args):
        with self.assertRaises(p.Refused):fn(*args)
    # The first six tests preserve the independent adverse expectations. They
    # now target the new implementation; the original failing receipt is kept.
    def test_unknown_reference_trait_producer_must_refuse(self):
        self.refuse(p.classify_external,'<&ForeignFailure as ForeignFactory>::new',['&ForeignFailure'])
    def test_unknown_generic_trait_producer_must_refuse(self):
        self.refuse(p.classify_external,'<Option<ForeignFailure> as ForeignFactory>::take',['ForeignFailure'])
    def test_comparison_basename_must_not_authorize_unknown_trait(self):
        self.refuse(p.classify_external,'<ForeignFailure as ForeignFactory>::eq',['ForeignFailure'])
    def test_unreviewed_std_namespace_must_refuse(self):
        self.refuse(p.classify_external,'std::future_vendor::take',['ForeignFailure'])
    def test_nested_scope_str_assignments_must_be_censused(self):
        mir='fn nested() -> () {\n    scope 1 {\n        scope 2 {\n            let _1: &str;\n            let _2: [Option<&str>; 3];\n        }\n    }\n    bb0: {\n        _1 = const "nested_string";\n        return;\n    }\n}\n'
        functions,_,_=p.parse_functions(mir,{})
        self.assertEqual(len(functions['f0000']['str_assignments']),1)
        self.assertEqual(functions['f0000']['local_types']['_2'],'[Option<&str>; 3]')
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
        functions,_,_=p.parse_functions(mir,{})
        self.assertIn('Foreign::make',functions['f0000']['calls'][0]['callbacks'])
    def test_end_to_end_unknown_nested_carrier_producer_refuses(self):
        # The outer Result/Option hides the str-bearing authored Failure. A
        # familiar namespace/member must not close that manufactured value.
        body='        _0 = std::future_vendor::take() -> [return: bb1, unwind continue];\n'
        mir=mini(body).replace('fn '+p.ROOTS[0]+'() -> ()','fn '+p.ROOTS[0]+'() -> Result<Option<control::SwiftRunFailure>, ()>',1).replace('    let mut _0: ();','    let mut _0: Result<Option<control::SwiftRunFailure>, ()>;',1)
        self.refuse(p.analyze,mir,{})
    def test_end_to_end_known_target_changed_nested_return_refuses(self):
        target='Option::<u32>::is_some'
        if target not in p.external_catalog():target=next(t for t,c in p.external_catalog().items() if c['identity']['member']=='is_some')
        mir=mini('        _0 = '+target+'(const 0_u32) -> [return: bb1, unwind continue];\n')
        mir=mir.replace('    let mut _0: ();','    let mut _0: Option<control::SwiftRunFailure>;',1)
        self.refuse(p.analyze,mir,{})
    def test_exact_contract_argument_and_result_compatibility(self):
        target,contract=next(iter(p.external_catalog().items()));sig=contract['signatures'][0]
        p.classify_external(target,[sig['result']],[sig['arguments']])
        self.refuse(p.classify_external,target,['Option<ForeignFailure>'],[sig['arguments']])
        self.refuse(p.classify_external,target,[sig['result']],[sig['arguments']+['&ForeignFailure']])
        self.refuse(p.classify_external,target,[sig['result']])
    def test_named_unknown_and_indirect_items_refuse(self):
        self.refuse(p.standard_named_callback,'Foreign::make','Option::<u8>::map::<ForeignFailure, fn(u8) -> ForeignFailure {Foreign::make}>')
        self.refuse(p.analyze,mini('        _0 = move _9() -> [return: bb1, unwind continue];\n'),{})
    def test_named_constructor_duplicates_and_transitive_calls_retained(self):
        g=self.graph;self.assertEqual(len(g['nodes']),525);self.assertEqual(len(g['edges']),1908)
        self.assertEqual(set(self.induction['added_bodies']),{'f1605','f1697','f1899','f1900','f1927','f1928'})
        self.assertTrue(any(e['caller']=='f1605' and e['callee']=='f1697' for e in g['edges']))
        edges=[e for e in g['edges'] if e['kind']=='named-authored-callback']
        self.assertEqual(len(edges),28);self.assertEqual(len({(e['caller'],e['line']) for e in edges}),22)
        for key in ('f1899','f1900','f1927','f1928'):self.assertTrue(any(e['callee']==key for e in edges))
        self.assertEqual(len(g['standard_named_callbacks']),2)
        for row in g['standard_named_callbacks']:
            outer=next(c['target'] for c in g['nodes'][row['caller']]['calls'] if c['line']==row['line'])
            p.standard_named_callback(row['target'],outer)
            self.refuse(p.standard_named_callback,row['target'],outer.replace(' -> bool ',' -> ForeignFailure '))
    def test_all_eighty_transfers_and_complete_origin_pool(self):
        g=self.graph;self.assertEqual(len(g['source_str_assignments']),80)
        for key,local,line in [('f0279','_35',256),('f1035','_29',203)]:
            rows=[x for x in g['source_str_assignments'] if x['function']==key and x['local']==local and x['line']==line]
            self.assertEqual(len(rows),1);self.assertEqual(rows[0]['kind'],'reference-or-field-transfer')
        self.assertEqual(g['constant_allocations']['unique_ids'],1464)
        self.assertEqual(g['constant_allocations']['unresolved_ids'],[])
        self.assertEqual(len(self.induction['origin_pool']['literal_occurrences']),3189)
    def test_nested_carriers_return_errors_latches_and_drop_are_retained(self):
        i=self.induction
        self.assertTrue(i['nested_and_direct_ports'])
        for name in ('SwiftRunFailure','Fault','Policy','SnapshotStopV1','SnapshotScopeFinishV1'):
            self.assertIn(name,i['carrier_names_conservative'])
        self.assertTrue(any(row['return_carries_str'] for row in i['body_induction'].values()))
        self.assertTrue(any('PrepaidOwnedV1' in r['header'] and r['base']=='drop' for r in self.graph['nodes'].values()))
        for flag in ('L_str_selected','root_selected','whole_budget_selected','OTA_or_GA'):self.assertIs(i[flag],False)
    def test_selected_inline_asm_cannot_be_authorized_by_lexer(self):
        self.refuse(p.analyze,mini('        _0 = asm!("mrs {0}, fpcr", out(reg) _0, options(NOMEM | NOSTACK)) -> [return: bb1, unwind continue];\n'),{})
    def test_original_failures_remain_failed(self):
        for name in ('producer-006','producer-007','independent-adverse-006'):
            receipt=json.loads((D/'history'/name/'receipt.json').read_text());self.assertEqual(receipt['exit_code'],1)
        adverse=(D/'history/independent-adverse-006/stderr').read_text()
        self.assertIn('FAILED (failures=6)',adverse)
if __name__=='__main__':unittest.main(verbosity=2)
