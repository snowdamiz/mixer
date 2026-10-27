"""Producer hostile host controls. A fresh independent review is still required.

All inputs apart from the frozen selected1947-byte source are synthetic. No Rust
function, input acquisition, executable or native runtime is invoked.
"""
from dataclasses import replace
from pathlib import Path
import copy, json, random, re, unittest
import derive as D
import model as M
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LABEL='a'*64
def B(value,unit='bytes',name='explicit synthetic obligation only'):
    return M.Bound(value,name,M.TREE,LABEL,unit)
def synthetic():
    source=(ROOT/'verification/swift-real-profile-loader-binding/source-preimages/genuine.wasm').read_bytes()
    identities=tuple(M.Identity(name,source if name=='source' else ('synthetic '+name).encode(),M.digest(source if name=='source' else ('synthetic '+name).encode()),B(len(source) if name=='source' else len('synthetic '+name))) for name in M.IDENTITIES)
    paths=tuple(M.PathInput(b'/synthetic/'+str(i).encode(),b'/synthetic/'+str(i).encode(),B(12),B(12),B(13),LABEL) for i in range(5))
    budget={name:1 for name in M.BUDGET_FIELDS};budget.update(execution_work=1_000_000_000,combined_bytes=268435456)
    return M.BindingInput(M.TREE,identities,paths,tuple(bytes([i])*32 for i in range(8)),budget,LABEL,B(128),B(64),B(512),B(8572),B(4097),B(73),B(32),B(396924,'count'),B(29394))
def terms(): return ({name:B(1,'work') for name in M.INHERITED_WORK},{name:B(1,'work') for name in M.candidate()['new_required_std_interface_terms']},B(1,'work'),B(1,'work'))
def independent_price(code, roles, operand_body):
    """Separate arithmetic reconstruction, including each repeated operand."""
    total=2+sum(code.count(char) for char in '()[].*&')+len(re.findall(r'\bas\b',code))
    for name in re.findall(r'\b_\d+\b',code):
        role=roles[name]
        total += 2*role['scalar_leaves']+2*role['bytes']
        for field in ('pointee_bytes','pointee_scalar_leaves'):
            total += 2*(role[field]['fixed']+operand_body*role[field]['input_operand_bytes'])
    # Match the audited fixed literal list separately from the producer scanner.
    for tail in code.split('const ')[1:]:
        token=tail.split(',',1)[0].split(')',1)[0].split(';',1)[0].strip()
        if token.startswith('('): width,leaves=0,1
        elif token.startswith(('true','false')) or re.match(r'\d+_u8\b',token): width,leaves=1,1
        elif 'SELECTED_SOURCE_SHA256_V1' in token: width,leaves=32,32
        else: width,leaves=8,1
        total += 2*width+2*leaves
    if code=='return;':
        role=roles['_0'];total += 2*role['scalar_leaves']+2*role['bytes']
        for field in ('pointee_bytes','pointee_scalar_leaves'): total += 2*(role[field]['fixed']+operand_body*role[field]['input_operand_bytes'])
    return total
class ShapeAndArithmetic(unittest.TestCase):
    def test_integer_and_overflow_boundaries(self):
        self.assertEqual(M.add(M.U64,0),M.U64);self.assertEqual(M.mul(M.U64,1),M.U64)
        for value in (True,False,-1,1.0,'1',None,M.U64+1):
            with self.subTest(value=value),self.assertRaises(M.Refused):M.natural(value)
        for call in (lambda:M.add(M.U64,1),lambda:M.mul(M.U64,2)):
            with self.assertRaises(M.Refused):call()
    def test_checked_sum_actual22_lengths(self):
        value=synthetic();shape=M.describe(value)
        self.assertEqual(shape['logical_input_backing_bytes'],sum(len(x.preimage) for x in value.identities)+sum(len(p.native_body)+len(p.retained_byte_preimage) for p in value.paths))
        self.assertEqual(shape['input_operand_bytes'],1947)
        self.assertEqual(M.describe(value,limit=shape['logical_input_backing_bytes'])['logical_input_backing_bytes'],shape['logical_input_backing_bytes'])
        with self.assertRaises(M.Refused):M.describe(value,limit=shape['logical_input_backing_bytes']-1)
    def test_each_empty_identity_is_refused(self):
        value=synthetic()
        for i in range(12):
            identities=list(value.identities);identities[i]=replace(identities[i],preimage=b'')
            with self.subTest(i=i),self.assertRaises(M.Refused):M.describe(replace(value,identities=tuple(identities)))
    def test_identity_roster_order_mutability(self):
        value=synthetic()
        for identities in (value.identities[:-1],value.identities+(value.identities[0],),(value.identities[0],)*12,tuple(reversed(value.identities)),list(value.identities)):
            with self.assertRaises(M.Refused):M.describe(replace(value,identities=identities))
        identities=list(value.identities);identities[2]=replace(identities[2],preimage=bytearray(b'a'))
        with self.assertRaises(M.Refused):M.describe(replace(value,identities=tuple(identities)))
    def test_selected_source_claim_and_length(self):
        value=synthetic()
        for changes in ({'preimage':b'x'},{'sha256':'0'*64}):
            ids=list(value.identities);ids[0]=replace(ids[0],**changes)
            with self.assertRaises(M.Refused):M.describe(replace(value,identities=tuple(ids)))
    def test_provider_does_not_authenticate_digests(self):
        value=synthetic();ids=list(value.identities);ids[0]=replace(ids[0],preimage=b'X'*1947)
        forged=replace(value,identities=tuple(ids));shape=M.describe(forged)
        self.assertFalse(shape['digest_validation_performed']);self.assertFalse(shape['authenticated_owner'])
        with self.assertRaises(M.Refused):M.storage(forged)
        ids=list(value.identities);ids[4]=replace(ids[4],sha256='f'*64)
        self.assertFalse(M.describe(replace(value,identities=tuple(ids)))['accepted_bound'])
        with self.assertRaises(M.Refused):M.storage(replace(value,identities=tuple(ids)))
    def test_each_native_path_refusal_and_exact_count(self):
        value=synthetic()
        for i in range(5):
            for changes in ({'native_body':b''},{'native_body':b'a\0b'},{'retained_byte_preimage':b'wrong'},{'native_body':bytearray(b'a')}):
                paths=list(value.paths);paths[i]=replace(paths[i],**changes)
                with self.subTest(i=i,changes=changes),self.assertRaises(M.Refused):M.describe(replace(value,paths=tuple(paths)))
        for paths in (value.paths[:-1],value.paths+(value.paths[0],),list(value.paths)):
            with self.assertRaises(M.Refused):M.describe(replace(value,paths=paths))
    def test_non_UTF8_and_aliasing_give_no_credit(self):
        value=synthetic();p=replace(value.paths[0],native_body=b'/non-utf8-\xff',retained_byte_preimage=b'/non-utf8-\xff')
        value=replace(value,paths=(p,)*5);shape=M.describe(value);storage=M.storage(value)
        self.assertEqual(shape['native_path_bytes'],(11,)*5);self.assertEqual(storage['native_path_backing'],60);self.assertEqual(storage['separate_retained_path_backing'],60)
    def test_all_Pending_no_authority(self):
        value=synthetic()
        for report in (M.describe(value),M.storage(value),M.work(value,*terms())):
            self.assertFalse(report['accepted_bound']);self.assertFalse(report['operational_grant'])
        shape=M.describe(value);self.assertEqual(tuple(shape['upstream']),M.UPSTREAM);self.assertEqual(set(shape['upstream'].values()),{'Pending'});self.assertEqual(set(shape['selectors'].values()),{'Pending'})
    def test_typed_bound_source_unit_and_provenance(self):
        for item in (B(0),replace(B(1),source_tree=M.OLD_TREE),replace(B(1),evidence_sha256='x'),replace(B(1),obligation=''),B(1,'work'),1):
            with self.subTest(item=item),self.assertRaises(M.Refused):M.bound(item)
    def test_storage_addition_preserves_each_old_component(self):
        value=synthetic();old,converted=M.old_input(value);prior=old.storage(converted);new=M.storage(value)
        self.assertEqual(new['fixed_P0'],301733);self.assertEqual(new['provider_total_addition'],9696)
        self.assertEqual(new['P0_preexisting'],prior['P0_preexisting']+9696);self.assertEqual(new['whole_external_storage'],prior['whole_external_storage']+9696)
        self.assertEqual(new['inherited_six_child_storage_parts'],prior['inherited_six_child_storage_parts']);self.assertEqual(new['inherited_child_prepaid'],prior['inherited_child_prepaid'])
        self.assertEqual(new['original_binding_inline'],1168);self.assertFalse(new['None_refusal_unwind_refund']);self.assertTrue(new['P0_through_final_result_consumption'])
    def test_every_actual_backing_omission_refused(self):
        value=synthetic()
        for i in range(12):
            ids=list(value.identities);ids[i]=replace(ids[i],backing=B(1))
            with self.subTest(i=i),self.assertRaises(M.Refused):M.storage(replace(value,identities=tuple(ids)))
        for i in range(5):
            for field in ('native_backing','byte_preimage_backing','open_temporary'):
                paths=list(value.paths);paths[i]=replace(paths[i],**{field:B(1)})
                with self.subTest(i=i,field=field),self.assertRaises(M.Refused):M.storage(replace(value,paths=tuple(paths)))
    def test_original_native_error_diagnostic_upstream_obligations(self):
        value=synthetic()
        for field in ('future_root_inline','future_root_owned_backing','immutable_diagnostic_backing','loader_native_temporaries','executable_open_temporary','file_resource_backing_each','error_backing_each','error_owner_count','all_payload_destructor_temporaries'):
            item=getattr(value,field);bad=replace(item,value=0)
            with self.subTest(field=field),self.assertRaises(M.Refused):M.storage(replace(value,**{field:bad}))
        for field in ('loader_native_temporaries','executable_open_temporary','file_resource_backing_each','error_backing_each','error_owner_count','all_payload_destructor_temporaries'):
            item=getattr(value,field)
            with self.subTest(field=field),self.assertRaises(M.Refused):M.storage(replace(value,**{field:replace(item,value=item.value-1)}))
    def test_caps_are_conditional_upstream_not_provider_enforcement(self):
        value=synthetic();ids=list(value.identities);body=b'B'*(131072+1);ids[1]=M.Identity('build',body,M.digest(body),B(len(body)));value=replace(value,identities=tuple(ids))
        self.assertEqual(M.describe(value)['identity_bytes'][1],131073)
        with self.assertRaises(M.Refused):M.storage(value)
    def test_original_claims_and_budget_fields_not_lost(self):
        value=synthetic()
        for field in M.BUDGET_FIELDS:
            budget=dict(value.product_budget);del budget[field]
            with self.subTest(field=field),self.assertRaises(M.Refused):M.storage(replace(value,product_budget=budget))
        for claims in (value.claims[:-1],tuple(b'x' for _ in range(8))):
            with self.assertRaises(M.Refused):M.storage(replace(value,claims=claims))
    def test_work_all_old_and_new_callee_inputs_positive(self):
        value=synthetic();old,std,acquisition,caller=terms()
        for target in ('old','std'):
            original=old if target=='old' else std
            for name in original:
                for mode in ('missing','zero','wrong-source','wrong-unit'):
                    bad=dict(original)
                    if mode=='missing':del bad[name]
                    elif mode=='zero':bad[name]=B(0,'work')
                    elif mode=='wrong-source':bad[name]=replace(bad[name],source_tree=M.OLD_TREE)
                    else:bad[name]=B(1)
                    with self.subTest(target=target,name=name,mode=mode),self.assertRaises(M.Refused):M.work(value,bad if target=='old' else old,bad if target=='std' else std,acquisition,caller)
        for a,c in ((B(0,'work'),caller),(acquisition,B(0,'work')),(B(1),caller),(acquisition,B(1))):
            with self.assertRaises(M.Refused):M.work(value,old,std,a,c)
    def test_work_checked_fixed_and_dynamic_expression(self):
        value=synthetic();old,std,a,c=terms();report=M.work(value,old,std,a,c);candidate=M.candidate()
        expected=895084428325956794+sum(M.INHERITED_WORK.values())+276580+1324*1947+sum(candidate['new_required_std_interface_terms'].values())+2
        self.assertEqual(report['whole_work'],expected);self.assertEqual(report['provider_source_work'],276580+1324*1947);self.assertFalse(report['L_str_selected'])
    def test_work_and_storage_overflow(self):
        value=synthetic();old,std,a,c=terms()
        for target in ('old','std','acquisition','caller'):
            one,two=dict(old),dict(std);aa,cc=a,c
            if target=='old':one['L_str']=B(M.U64,'work')
            elif target=='std':two['slice_len']=B(M.U64,'work')
            elif target=='acquisition':aa=B(M.U64,'work')
            else:cc=B(M.U64,'work')
            with self.subTest(target=target),self.assertRaises(M.Refused):M.work(value,one,two,aa,cc)
        with self.assertRaises(M.Refused):M.storage(replace(value,future_root_inline=B(M.U64)))
class RetainedMIRControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.derived=D.derive();cls.report=cls.derived['candidate.json'];cls.functions=cls.derived['source-typed-MIR-map.json']['functions'];cls.main=next(f for f in cls.functions if f['header'].startswith('fn '+D.NAME+'('));cls.callback=next(f for f in cls.functions if f['header'].startswith('fn '+D.NAME+'::{closure#0}'))
    def test_complete_construct_role_operation_partition(self):
        self.assertEqual((self.report['constructs'],self.report['roles'],self.report['written_operations']),(11,193,565))
        self.assertEqual(sum(len(f['roles']) for f in self.functions),193);self.assertEqual(sum(r['bytes'] for f in self.functions for r in f['roles']),8344)
        self.assertEqual([len(f['roles']) for f in self.functions if f['kind']=='promoted-constant'],[2,2]);self.assertEqual(sum(f['kind']=='standalone-constant' for f in self.functions),7)
    def test_capture_is_actual_aggregate_and_uses_exact_two_fields(self):
        layout=self.derived['layouts.json']['anonymous_capture'];self.assertEqual((layout['bytes'],layout['alignment']),(16,8));self.assertFalse(layout['padding_inferred_from_fields'])
        code='\n'.join(self.main['blocks']['bb49']['operations'])
        self.assertIn('native_path_bodies: move _139, position: move _140',code)
        self.assertEqual(next(r for r in self.main['roles'] if r['local']=='_138')['bytes'],16);self.assertEqual(next(r for r in self.callback['roles'] if r['local']=='_1')['bytes'],16)
    def test_exact_loop_and_call_caps(self):
        blocks=self.main['blocks'];self.assertEqual(blocks['bb2']['per_invocation_cap'],13);self.assertEqual(blocks['bb3']['per_invocation_cap'],13);self.assertEqual(blocks['bb15']['per_invocation_cap'],12)
        self.assertEqual(blocks['bb26']['per_invocation_cap'],6);self.assertEqual(blocks['bb27']['per_invocation_cap'],6);self.assertEqual(blocks['bb53']['per_invocation_cap'],5)
        counts=self.report['new_required_std_interface_terms'];self.assertEqual((counts['range_next'],counts['slice_len'],counts['usize_checked_add'],counts['option_and_then_excluding_authored_callback']),(19,33,22,5));self.assertEqual(self.callback['per_request_invocation_cap'],5)
    def test_added_or_changed_loop_edges_fail_closed(self):
        for block,successors in [('bb15',['bb3']),('bb53',['bb27']),('bb42',['bb0'])]:
            changed=copy.deepcopy(self.main['blocks']);changed[block]['successors']=successors
            with self.subTest(block=block),self.assertRaises(ValueError):D.bounded_multiplicities(changed,True)
        changed=copy.deepcopy(self.main['blocks']);changed['bb0']['operations']=[x.replace('end: const 12_usize','end: const 13_usize') for x in changed['bb0']['operations']]
        with self.assertRaises(ValueError):D.bounded_multiplicities(changed,True)
    def test_unknown_typed_operand_and_constant_fail_closed(self):
        by={r['local']:r for r in self.main['roles']}
        for code in ('_999 = copy _1;','_41 = const 1_u128;','_41 = const UNREVIEWED_LENGTH_V1;'):
            with self.subTest(code=code),self.assertRaises(ValueError):D.price(code,by)
        for name in ('_1','_2','_3','_138','_147','_148','_152','_0'):
            mutated=dict(by);del mutated[name]
            code=next(x['code'] for b in self.main['blocks'].values() for x in b['rows'] if name in x['mentions'])
            with self.subTest(name=name),self.assertRaises(ValueError):D.price(code,mutated)
    def test_unknown_std_interfaces_fail_closed(self):
        for code in ('_1 = unreviewed::maybe_allocate() -> [return: bb0, unwind continue];','_4 = core::slice::<impl [u8]>::new_unreviewed(move _5) -> [return: bb2, unwind continue];'):
            with self.assertRaises(ValueError):D.classify_call(code)
    def test_all565_operations_reconstructed_at_three_actual_body_sizes(self):
        checks=0
        for f in self.functions:
            by={r['local']:r for r in f['roles']}
            for block in f['blocks'].values():
                for operation in block['rows']:
                    for size in (1,1947,67108864):
                        expected=independent_price(operation['code'],by,size);actual=operation['combined']['fixed']+size*operation['combined']['input_operand_bytes']
                        self.assertEqual(expected,actual);checks+=1
        self.assertEqual(checks,1695)
    def test_independent_weighted_totals_and_each_role_end(self):
        fixed=dynamic=0
        for f in self.functions:
            by={r['local']:r for r in f['roles']};params=[r for r in f['roles'] if r['kind']=='parameter']
            def at(size):
                total=2
                for role in params:
                    total+=2*(role['scalar_leaves']+role['bytes'])
                    for field in ('pointee_bytes','pointee_scalar_leaves'):total+=2*(role[field]['fixed']+size*role[field]['input_operand_bytes'])
                total+=sum(independent_price(x['code'],by,size)*b['per_invocation_cap'] for b in f['blocks'].values() for x in b['rows'])
                total+=sum(2+2*r['scalar_leaves']+2*r['bytes'] for r in f['roles'])
                return total*f['per_request_invocation_cap']
            a,b=at(0),at(1);fixed+=a;dynamic+=b-a
            self.assertEqual(f['work_per_request'],{'fixed':a,'input_operand_bytes':b-a})
        fixed+=self.report['external_result_end'];self.assertEqual((fixed,dynamic),(276580,1324))
    def test_every_written_slot_lives_through_all15_phases(self):
        phase=self.derived['phase-roster.json'];self.assertEqual(len(phase['all_new_roles']),193);self.assertEqual(len(phase['P0_new_total_each_phase']),15)
        self.assertEqual(set(phase['P0_new_total_each_phase'].values()),{9696})
        for role in phase['all_new_roles']:
            self.assertEqual(role['funded_by'],'P0');self.assertEqual(role['reserved_last'],'P0_AFTER_FINAL_OUTER_RESULT_CONSUMPTION');self.assertEqual(role['invocation_storage_instances'],1)
    def test_source_MIR_mutations_cannot_hide_under_comment_normalization(self):
        original=(ROOT/'verification/swift-guarded-snapshot-owned-provider-independent/provider.mir').read_text();constructs=D.provider_constructs(D.partition(original));count=0
        for body in constructs:
            if '\n' not in body:mutated=body.replace(' = const ',' = const 999999 + ',1)
            else:mutated=body.replace('return;','unreachable;',1)
            self.assertNotEqual(D.normalized(body),D.normalized(mutated));count+=1
        self.assertEqual(count,11)
        with self.assertRaises(ValueError):D.partition('fn truncated() -> () {\n    bb0: {\n        return;\n    }\n')
    def test_retained_result_constructor_error_and_unwind_endings(self):
        texts=[x['code'] for b in self.main['blocks'].values() for x in b['rows']]
        self.assertTrue(any('>::Ok(move _147)' in x for x in texts));self.assertEqual(sum('>::Err(' in x for x in texts),5)
        self.assertEqual(sum('from_residual' in x for x in texts),2)
        paths=self.main['bounded_cut_paths'];self.assertTrue(any(p['terminal']=='unwind-continue' for p in paths));self.assertTrue(any(p['terminal']=='unreachable' for p in paths));self.assertTrue(any(p['terminal']=='return' for p in paths));self.assertEqual(sum(p['terminal']=='bounded-loop-backedge' for p in paths),2)
if __name__=='__main__':unittest.main(verbosity=2)
