#!/usr/bin/env python3
import copy,json,re,unittest
from pathlib import Path
from mir_graph import Refused,sha,require,literal_tokens,call_target,erase_generics,classify_external,parse_functions
from check import bind_exact,bind_artifact,bound_text,alternate_caller_obligation
D=Path(__file__).resolve().parent
class ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate=json.loads((D/'candidate.json').read_text());cls.graph=json.loads((D/'graph.json').read_text());cls.contract=json.loads((D/'caller-contract.json').read_text())
    def refuse(self,fn,*args):
        with self.assertRaises(Refused):fn(*args)
    def test_exact_bound_and_no_authority(self):
        result=bind_exact(self.candidate,self.candidate);self.assertEqual(result['L_str'],5080)
        for k in ('accepted_bound','operational_grant','OTA_authority'):self.assertIs(result[k],False)
    def test_candidate_schema_scope_and_all_authority_mutations_refuse(self):
        for key in self.candidate:
            altered=copy.deepcopy(self.candidate);del altered[key];self.refuse(bind_exact,altered,self.candidate)
        for key in ('accepted_bound','whole_host_funding','policy_or_work_grant','runtime_or_native_test','OTA_authority','GA'):
            altered=copy.deepcopy(self.candidate);altered[key]=True;self.refuse(bind_exact,altered,self.candidate)
        altered=copy.deepcopy(self.candidate);altered['caller_static_lifetime']=True;self.refuse(bind_exact,altered,self.candidate)
    def test_tree_host_and_bound_substitution_refuse(self):
        for key,values in {'source_tree_sha256':['0'*64],'host_tree_sha256':['0'*64],'L_str':[0,1,8,16,92,5079,5081,True,-1,1<<64,5080.0]}.items():
            for value in values:
                altered=copy.deepcopy(self.candidate);altered[key]=value;self.refuse(bind_exact,altered,self.candidate)
    def test_all_graph_edges_callbacks_nodes_and_frontiers_are_bound(self):
        for key in ('roots','edges','external_frontier','source_str_assignments','direct_str_parameters'):
            altered=copy.deepcopy(self.graph);altered[key]=altered[key][1:];self.refuse(bind_artifact,altered,self.graph,'graph')
        altered=copy.deepcopy(self.graph);del altered['nodes'][next(iter(altered['nodes']))];self.refuse(bind_artifact,altered,self.graph,'graph')
        altered=copy.deepcopy(self.graph);altered['external_frontier'][0]['kind']='all-strings-small';self.refuse(bind_artifact,altered,self.graph,'graph')
        callbacks=[x for x in self.graph['edges'] if x['kind']=='authored-callback'];self.assertGreater(len(callbacks),100)
    def test_caller_contract_cannot_add_fault_failure_policy_or_callback(self):
        for value in ('Fault.code','SwiftRunFailure.code','RuntimeControl.first_failure','Policy::Frozen.imports','foreign callback'):
            altered=copy.deepcopy(self.contract);altered['root_incoming_authored_str_ports']=[value];self.refuse(bind_artifact,altered,self.contract,'caller')
    def test_actual_UTF8_extent_including_multibyte_and_boundary(self):
        self.assertEqual(bound_text('x'*5080,5080)['utf8_bytes'],5080)
        self.refuse(bound_text,'x'*5081,5080);self.refuse(bound_text,'😀'*1271,5080)
        self.assertEqual(bound_text('😀'*1270,5080)['scalar_leaves'],1270)
        self.refuse(bound_text,'\ud800',5080)
        for value in (5080,True,None,{'claimed_length':1,'static':True,'pointer_width':8}):self.refuse(bound_text,value,5080)
    def test_alternate_values_even_bounded_do_not_close_provenance(self):
        values={x['function']+':'+x['parameter']:['small'] for x in self.graph['direct_str_parameters']}
        result=alternate_caller_obligation(values,self.graph,self.contract,5080)
        for key in ('complete_provenance','new_caller_qualified','accepted_bound','operational_grant'):self.assertIs(result[key],False)
        self.refuse(alternate_caller_obligation,{},self.graph,self.contract,5080)
        bad=copy.deepcopy(values);bad['unknown:port']=['small'];self.refuse(alternate_caller_obligation,bad,self.graph,self.contract,5080)
        key=next(iter(values));bad=copy.deepcopy(values);bad[key]=['x'*5081];self.refuse(alternate_caller_obligation,bad,self.graph,self.contract,5080)
    def test_compiler_literals_decode_every_escape_without_silent_skip(self):
        text=r'''        _1 = const "quote\" slash// byte\x41 unicode\u{1f600}\0"; // ignored "suffix"
        _2 = const '"';
        _3 = const b"bytes do not become str";
'''
        result=literal_tokens(text);self.assertEqual(len(result),1);self.assertIn('😀\0',result[0]['value']);self.assertIn('slash//',result[0]['value'])
        self.refuse(literal_tokens,r'_1 = const "unsupported\q";')
        self.refuse(literal_tokens,'_1 = const "unclosed;')
    def test_allocation_hexdumps_are_not_misparsed_as_literals(self):
        result=literal_tokens('alloc1 (size: 7, align: 1) {\n    22 61 62 63 │ "abc\n}\n    _1 = const "actual";\n');self.assertEqual([r['value'] for r in result],['actual'])
        allocation=self.graph['constant_allocations'];self.assertEqual(allocation['count'],1958)
        self.assertEqual(max(x['bytes'] for x in allocation['members']),5080)
        self.assertEqual(self.graph['literal_pool']['max_utf8_bytes'],92)
        self.assertGreater(allocation['max_bytes'],self.graph['literal_pool']['max_utf8_bytes'])
    def test_nested_fn_type_arrow_and_tuple_do_not_drop_call_edge(self):
        target="Option::<&Error>::map::<String, for<'a> fn(&'a Error) -> String {Error::json}>"
        self.assertEqual(call_target(target+'(move _1, Error::json) -> [return: bb1];'),target)
        self.assertEqual(erase_generics(target),'Option::map')
        self.assertEqual(call_target('Result::<(), Error>::and::<()>(move _1, move _2) -> [return: bb1];'),'Result::<(), Error>::and::<()>')
    def test_unknown_external_and_byte_to_str_producers_refuse(self):
        for target,types in [('std::str::from_utf8',['Result<&str, Utf8Error>']),('std::env::var',['Result<String, VarError>']),('foreign::mint_string', ['&str']),('foreign::take',['SwiftRunFailure']),('<ForeignFailure as Default>::default',['SwiftRunFailure']),('<Foreign<Result<u64,Error>> as Try>::branch',['SwiftRunFailure']),('std::slice::from_raw_parts::<str>',['&str']),('control::Fault::new',['Fault'])]:
            self.refuse(classify_external,target,types)
    def test_str_assignments_are_literal_transfer_or_expanded_return(self):
        kinds={x['kind'] for x in self.graph['source_str_assignments']};self.assertEqual(kinds,{'compiled-literal','reference-or-field-transfer','callee-return'})
        for row in self.graph['nodes'].values():
            for call in row['calls']:
                if call['result_type']=='&str':self.assertEqual(call['target'],'swift::ValidatedSwiftReactor::policy_identity')
        names=[x['name'] for x in self.graph['nodes'].values()]
        self.assertTrue(any(x.endswith('::fail') for x in names));self.assertTrue(any(x.endswith('::cleanup_fault_with_wasi') for x in names))
        self.assertTrue(any(x=='swift::failure' for x in names));self.assertTrue(any(x.endswith('::drop') and 'host_account_v1' in x for x in names))
    def test_frozen_input_digests_cannot_be_replaced_with_equal_length(self):
        data=json.loads((D/'input-bindings.json').read_text());files=data['files'];self.assertGreater(len(files),200)
        for key in ('whole-source146.mir.gz','source146-manifest.json','source-reference-map.json','compiler-receipt.json'):
            value=next(v for p,v in files.items() if p.endswith('/'+key));self.assertEqual(len(value['sha256']),64)
            changed={'bytes':value['bytes'],'sha256':'0'*64};self.refuse(bind_artifact,changed,value,'input-digest')
    def test_existing_formula_coefficient_is_preserved(self):
        L=self.candidate['L_str'];shell=self.candidate['shell'];self.assertEqual(shell['fixed'],4236953);self.assertEqual(shell['L_str_coefficient'],4376)
        self.assertEqual(shell['substituted_candidate'],4236953+4376*L)
        self.assertEqual(self.candidate['whole_work_L_str_addition'],67424*L)
if __name__=='__main__':unittest.main(verbosity=2)
