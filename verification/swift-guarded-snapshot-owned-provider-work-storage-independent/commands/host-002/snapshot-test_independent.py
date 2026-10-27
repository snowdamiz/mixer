"""Independent hostile controls; synthetic labels never constitute evidence.

Raw-MIR graph unrolling, separately parsed source shapes, native query and full
slot reconstruction live in independent.py. These tests attack their frontiers
and the frozen host arithmetic with caller-owned synthetic input only.
"""
from pathlib import Path
from dataclasses import fields, replace
import copy, gzip, hashlib, importlib.util, json, random, sys, unittest
import independent as I
sys.dont_write_bytecode=True
P=I.P
spec=importlib.util.spec_from_file_location('frozen_provider_host_model',P/'model.py')
M=importlib.util.module_from_spec(spec);sys.modules[spec.name]=M;spec.loader.exec_module(M)
LABEL='c'*64
CONTROLS=[]
def b(value,unit='bytes',obligation='Independent synthetic obligation only'):
    return M.Bound(value,obligation,I.TREE,LABEL,unit)
def fixture():
    source=(I.V/'swift-real-profile-loader-binding/source-preimages/genuine.wasm').read_bytes()
    I.require(len(source)==1947 and I.digest(source)=='9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806','test selected source immutable')
    ids=tuple(M.Identity(name,source if pos==0 else ('review synthetic '+name).encode(),I.digest(source if pos==0 else ('review synthetic '+name).encode()),b((len(source) if pos==0 else len('review synthetic '+name))+31+pos)) for pos,name in enumerate(M.IDENTITIES))
    paths=tuple(M.PathInput(b'/review/\xff'+str(i).encode(),b'/review/\xff'+str(i).encode(),b(100+i),b(110+i),b(121+i),LABEL) for i in range(5))
    budget={n:1 for n in M.BUDGET_FIELDS};budget.update(execution_work=1_000_000_000,combined_bytes=268435456)
    return M.BindingInput(I.TREE,ids,paths,tuple(bytes([i])*32 for i in range(8)),budget,LABEL,b(137),b(271),b(509),b(8572),b(4097),b(73),b(32),b(396924,'count'),b(29394))
def terms():
    return ({n:b(7+i,'work',n) for i,n in enumerate(M.INHERITED_WORK)}, {n:b(37+i,'work',n) for i,n in enumerate(I.EXPECTED_CALLS)}, b(127,'work'),b(257,'work'))
class Review(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=I.reconstruct();cls.docs=(I.load(P/'candidate.json'),I.load(P/'phase-roster.json'),I.load(P/'required-input-contracts.json'))
        cls.value=fixture();cls.raw=gzip.decompress((P/'commands/capture-layout/query.mir.gz').read_bytes()).decode();cls.constructs=I.selected_constructs(cls.raw);cls.main=next(x for x in cls.constructs if x.startswith('fn '+I.NAME+'('));cls.callback=next(x for x in cls.constructs if x.startswith('fn '+I.NAME+'::{closure#0}'))
    def reject(self,label,fn,kind=(M.Refused,ValueError,KeyError)):
        with self.assertRaises(kind,msg=label):fn()
        CONTROLS.append(label)
    def check_docs(self,docs):return I.validate_documents(self.report,*docs)
    def test_01_complete_reconstruction_and_terms(self):
        self.assertTrue(self.check_docs(self.docs));self.assertEqual((self.report['roles'],self.report['operations']),(193,565))
        self.assertEqual(sum(c['roles'] for c in self.report['constructs'] if c['name'].startswith('const ') and 'promoted' not in c['name']),7)
        self.assertEqual(sum(c['roles'] for c in self.report['constructs'] if 'promoted' in c['name']),4)
        self.assertEqual(self.report['external_call_counts'],I.EXPECTED_CALLS)
    def test_02_full_old_source_transport_is_mandatory(self):
        expected={'owned-binding-provider':'998a7f6de2918e6b643360b4e67475fdc9a468d69792eb5cda3bb773272fcba3','scoped-binding-source':'1bc55306a1f6cf220660efa8ab9e34485d610ae806ebd56a1733d892ddfcd2e1','outer-parent-work-storage':'8b6190049be7d5c995b6bd01c477454e503ac1dcad518602370416f510779d9c','host-storage':'9862bbe187dea2e1c6999218604ec43db3d3c9bc28d4fd815615d81dd98df432'}
        receipts={}
        for name,sha in expected.items():
            p=I.V/'swift-semantic-adapter-root-review'/('guarded-snapshot-'+name+'-host-acceptance.json');self.assertEqual(I.digest(p.read_bytes()),sha);receipts[name]=I.load(p)
        self.assertEqual(receipts['owned-binding-provider']['old_production_MIR_constructs_preserved'],6006)
        self.assertEqual(receipts['scoped-binding-source']['standalone_constants'],1785)
        self.assertTrue(receipts['scoped-binding-source']['explicit_conditional_source_work_storage_rebind']['selected'])
        self.assertFalse(receipts['scoped-binding-source']['actual_bounded_input_acquisition_or_authenticated_owner'])
    def test_03_loop_headers_callback_and_refusals(self):
        blocks=I.basic_blocks(self.main);maxima=I.finite_maxima(blocks,True)
        self.assertEqual((maxima['bb2'],maxima['bb3'],maxima['bb26'],maxima['bb27']),(13,13,6,6))
        self.assertEqual((maxima['bb15'],maxima['bb53']),(12,5))
        for node in ('bb9','bb16','bb19','bb22','bb34','bb37','bb41','bb54','bb59'):self.assertEqual(maxima[node],1)
        self.assertEqual(I.finite_maxima(I.basic_blocks(self.callback),False),{'bb0':1,'bb1':1,'bb2':1,'bb3':1})
        self.assertEqual(next(c for c in self.report['constructs'] if 'closure#0' in c['name'])['authored_invocations'],5)
        for old,new in [('end: const 12_usize','end: const 11_usize'),('end: const 5_usize','end: const 4_usize'),('goto -> bb2;','goto -> bb15;'),('goto -> bb26;','goto -> bb53;')]:
            changed=self.main.replace(old,new)
            self.reject('raw graph mutation '+old,lambda changed=changed:I.finite_maxima(I.basic_blocks(changed),True))
    def test_04_missing_roles_unknown_operands_and_calls(self):
        changed=self.main.replace('let mut _170:', 'let mut _990:')
        self.reject('missing/renumbered actual role',lambda:I.role_roster(changed))
        roles={'_0':{'leaves':1,'bytes':8,'pointee_bytes':(0,0),'pointee_leaves':(0,0)}}
        for code in ('_0 = copy _99;','deinit(_0);'):
            self.reject('unbound or unsupported source primitive '+code,lambda code=code:I.price_operation(code,roles,1))
        for code in ('_0 = evil::len(copy _0) -> [return: bb1, unwind continue];','_0 = generic::unproved::<u8>(copy _0) -> [return: bb1, unwind continue];'):
            self.reject('unpriced callee target '+code,lambda code=code:I.call_interface(code))
        for code in ('_0 = const UNKNOWN_V1;','_0 = const 5_u128;'):
            self.reject('unpriced constant '+code,lambda code=code:I.price_operation(code,roles,1))
    def test_05_all_slot_and_lifetime_mutations(self):
        for i in range(193):
            docs=copy.deepcopy(self.docs);del docs[1]['all_new_roles'][i]
            self.reject('omitted written slot '+str(i),lambda docs=docs:self.check_docs(docs))
        for field in ('reserved_first','reserved_last','funded_by','invocation_storage_instances','bytes','alignment','type'):
            docs=copy.deepcopy(self.docs);row=docs[1]['all_new_roles'][3];row[field]=0 if type(row[field]) is int else 'bad'
            self.reject('slot lifetime/ownership mutation '+field,lambda docs=docs:self.check_docs(docs))
        docs=copy.deepcopy(self.docs);docs[1]['all_new_roles'].append(docs[1]['all_new_roles'][0])
        self.reject('duplicate alias role',lambda:self.check_docs(docs))
    def test_06_every_phase_stays_reserved(self):
        for field in ('provider_slots_bytes_each_phase','external_result_bytes_each_phase','P0_new_total_each_phase'):
            for phase in self.docs[1][field]:
                docs=copy.deepcopy(self.docs);docs[1][field][phase]-=1
                self.reject('phase undercharge '+field+'/'+phase,lambda docs=docs:self.check_docs(docs))
            docs=copy.deepcopy(self.docs);docs[1][field].pop(next(iter(docs[1][field])))
            self.reject('phase omission '+field,lambda docs=docs:self.check_docs(docs))
    def test_07_no_callee_omission_zero_or_synthetic_selection(self):
        for name in I.EXPECTED_CALLS:
            docs=copy.deepcopy(self.docs);del docs[0]['new_required_std_interface_terms'][name]
            self.reject('candidate missing external '+name,lambda docs=docs:self.check_docs(docs))
            for field,value in (('count',0),('count',1),('selected',True),('unit','CPU'),('price','one invented unit')):
                if field=='count' and I.EXPECTED_CALLS[name]==value:continue
                docs=copy.deepcopy(self.docs);next(r for r in docs[2]['std_interfaces'] if r['name']==name)[field]=value
                self.reject('contract external mutation '+name+'/'+field+'/'+str(value),lambda docs=docs:self.check_docs(docs))
        for i in range(26):
            docs=copy.deepcopy(self.docs);docs[2]['full_call_roster'][i]['call_cap']=0
            self.reject('omitted actual call '+str(i),lambda docs=docs:self.check_docs(docs))
    def test_08_inherited_terms_and_authority_flags(self):
        for name in self.docs[0]['inherited_residual_work_terms']:
            docs=copy.deepcopy(self.docs);del docs[0]['inherited_residual_work_terms'][name]
            self.reject('inherited term omission '+name,lambda docs=docs:self.check_docs(docs))
        for name in ('new_callee_contracts_selected','actual_acquisition_or_authenticated_owner','L_str_selected','whole_quote_or_root_funding_or_operational_grant','native_runtime_FieldLog_OTA_GA'):
            docs=copy.deepcopy(self.docs);docs[0][name]=True
            self.reject('authority escalation '+name,lambda docs=docs:self.check_docs(docs))
        for name in ('zero_alias_move_or_sharing_credit','original_binding1168_preserved','no_refund_on_None_refusal_unwind'):
            docs=copy.deepcopy(self.docs);docs[0][name]=False
            self.reject('storage/refund weakening '+name,lambda docs=docs:self.check_docs(docs))
    def test_09_storage_matches_independent_sum(self):
        s=M.storage(self.value)
        expected=301733+self.value.future_root_inline.value+self.value.future_root_owned_backing.value+self.value.immutable_diagnostic_backing.value+sum(x.backing.value for x in self.value.identities)+sum(x.native_backing.value+x.byte_preimage_backing.value for x in self.value.paths)
        self.assertEqual(s['P0_preexisting'],expected);self.assertEqual(s['provider_total_addition'],9696);self.assertEqual(s['original_binding_inline'],1168)
        old,converted=M.old_input(self.value);inherited=old.storage(converted)
        self.assertEqual(s['inherited_six_child_storage_parts'],inherited['inherited_six_child_storage_parts'])
        self.assertEqual(s['whole_external_storage'],inherited['whole_external_storage']+9696)
        self.assertEqual(len(s['inherited_six_child_storage_parts']),6)
    def test_10_alias_moves_descriptor_and_oversized_backing_no_credit(self):
        aliased=replace(self.value,paths=tuple(replace(p,native_body=self.value.paths[0].native_body,retained_byte_preimage=self.value.paths[0].native_body) for p in self.value.paths))
        s=M.storage(aliased);self.assertEqual(s['native_path_backing'],sum(p.native_backing.value for p in aliased.paths));self.assertEqual(s['separate_retained_path_backing'],sum(p.byte_preimage_backing.value for p in aliased.paths))
        shape=M.describe(aliased);self.assertEqual(shape['logical_input_backing_bytes'],sum(len(x.preimage) for x in aliased.identities)+sum(len(p.native_body)+len(p.retained_byte_preimage) for p in aliased.paths))
        larger=replace(aliased,identities=tuple(replace(x,backing=b(x.backing.value+17)) for x in aliased.identities),paths=tuple(replace(p,native_backing=b(p.native_backing.value+19),byte_preimage_backing=b(p.byte_preimage_backing.value+23)) for p in aliased.paths))
        ls=M.storage(larger);self.assertEqual(ls['P0_preexisting']-s['P0_preexisting'],12*17+5*(19+23));self.assertEqual(M.describe(larger),shape)
    def test_11_all12_full_preimages_and5plus5_paths(self):
        for i in range(12):
            ids=list(self.value.identities);ids[i]=replace(ids[i],backing=b(len(ids[i].preimage)-1));v=replace(self.value,identities=tuple(ids))
            self.reject('identity underbacking '+str(i),lambda v=v:M.storage(v))
            ids=list(self.value.identities);ids[i]=replace(ids[i],preimage=b'');v=replace(self.value,identities=tuple(ids))
            self.reject('empty identity '+str(i),lambda v=v:M.describe(v))
        for i in range(5):
            for field in ('native_backing','byte_preimage_backing'):
                ps=list(self.value.paths);ps[i]=replace(ps[i],**{field:b(len(ps[i].native_body)-1)});v=replace(self.value,paths=tuple(ps))
                self.reject('path underbacking '+str(i)+'/'+field,lambda v=v:M.storage(v))
            for field,value in (('native_body',b''),('native_body',b'/bad\x00path'),('retained_byte_preimage',b'/other')):
                ps=list(self.value.paths);ps[i]=replace(ps[i],**{field:value});v=replace(self.value,paths=tuple(ps))
                self.reject('path refusal '+str(i)+'/'+field+'/'+repr(value),lambda v=v:M.describe(v))
    def test_12_every_upstream_byte_bound_and_original_minimum(self):
        names=[f.name for f in fields(M.BindingInput) if isinstance(getattr(self.value,f.name),M.Bound)]
        for name in names:
            for value in (0,-1,True,M.U64+1):
                v=replace(self.value,**{name:replace(getattr(self.value,name),value=value)})
                self.reject('upstream invalid bound '+name+'/'+str(value),lambda v=v:M.storage(v))
            for field,value in (('unit','work'),('source_tree','0'*64),('evidence_sha256','bad'),('obligation',' ')):
                v=replace(self.value,**{name:replace(getattr(self.value,name),**{field:value})})
                self.reject('upstream binding mutation '+name+'/'+field,lambda v=v:M.storage(v))
        for name in ('loader_native_temporaries','executable_open_temporary','file_resource_backing_each','error_backing_each','error_owner_count','all_payload_destructor_temporaries'):
            bound=getattr(self.value,name);v=replace(self.value,**{name:replace(bound,value=bound.value-1)})
            self.reject('original native/destructor minimum '+name,lambda v=v:M.storage(v))
    def test_13_shape_accepts_forgery_stronger_condition_refuses(self):
        ids=list(self.value.identities);ids[0]=replace(ids[0],preimage=b'X'*1947);forged=replace(self.value,identities=tuple(ids))
        self.assertFalse(M.describe(forged)['digest_validation_performed']);self.assertFalse(M.describe(forged)['authenticated_owner'])
        self.reject('forged selected source content',lambda:M.storage(forged));self.reject('forged source work',lambda:M.work(forged,*terms()))
        for i in range(1,12):
            ids=list(self.value.identities);ids[i]=replace(ids[i],sha256='0'*64);forged=replace(self.value,identities=tuple(ids))
            self.assertFalse(M.describe(forged)['authenticated_owner']);self.reject('forged identity content '+str(i),lambda forged=forged:M.storage(forged))
    def test_14_shape_and_conditional_loader_caps_stay_distinct(self):
        for index,cap in ((1,128*1024),(2,64*1024),(3,64*1024**2)):
            # The large executable cap is audited in byte-bound source, avoiding
            # unnecessary giant fixture allocation in this finite host test.
            if index==3:
                self.assertIn("sizes['executable']>64*1024**2",(I.V/'swift-guarded-snapshot-outer-parent-work-storage/model.py').read_text());continue
            ids=list(self.value.identities);body=b'x'*(cap+1);ids[index]=replace(ids[index],preimage=body,sha256=I.digest(body),backing=b(len(body)));v=replace(self.value,identities=tuple(ids))
            self.assertEqual(M.describe(v)['input_operand_bytes'],cap+1);self.reject('conditional loader geometry '+str(index),lambda v=v:M.storage(v))
    def test_15_B_is_max_actual22_lengths_never_backing_sum_or_selected_cap(self):
        for pos in range(12):
            v=self.value
            if pos:
                ids=list(v.identities);body=b'z'*(2000+pos);ids[pos]=replace(ids[pos],preimage=body,sha256=I.digest(body),backing=b(len(body)+9999));v=replace(v,identities=tuple(ids))
            shape=M.describe(v);lengths=[len(x.preimage) for x in v.identities]+[len(p.native_body) for p in v.paths]+[len(p.retained_byte_preimage) for p in v.paths]
            self.assertEqual(shape['input_operand_bytes'],max(lengths));self.assertEqual(shape['logical_input_backing_bytes'],sum(lengths))
        for pos in range(5):
            ps=list(self.value.paths);body=b'q'*(2500+pos);ps[pos]=replace(ps[pos],native_body=body,retained_byte_preimage=body,native_backing=b(len(body)),byte_preimage_backing=b(len(body)),open_temporary=b(len(body)+1));v=replace(self.value,paths=tuple(ps))
            self.assertEqual(M.describe(v)['input_operand_bytes'],2500+pos)
    def test_16_work_arithmetic_and_each_term_sensitivity(self):
        inherited,std,acq,caller=terms();r=M.work(self.value,inherited,std,acq,caller);B=M.describe(self.value)['input_operand_bytes']
        expected=895084428326233374+1324*B+sum(M.INHERITED_WORK[n]*x.value for n,x in inherited.items())+sum(I.EXPECTED_CALLS[n]*x.value for n,x in std.items())+acq.value+caller.value
        self.assertEqual(r['whole_work'],expected);self.assertEqual(r['provider_source_work'],276580+1324*B)
        for which,mapping,coeffs in (('old',inherited,M.INHERITED_WORK),('new',std,I.EXPECTED_CALLS)):
            for name in mapping:
                changed={**mapping,name:replace(mapping[name],value=mapping[name].value+13)}
                other=M.work(self.value,changed if which=='old' else inherited,changed if which=='new' else std,acq,caller)
                self.assertEqual(other['whole_work']-expected,13*coeffs[name])
    def test_17_all_work_prices_positive_typed_exact_source_units(self):
        inherited,std,acq,caller=terms()
        for which,source in ((0,inherited),(1,std)):
            for name in source:
                changed=dict(source);del changed[name];args=[inherited,std,acq,caller];args[which]=changed
                self.reject('missing work input '+str(which)+'/'+name,lambda args=args:M.work(self.value,*args))
                for field,value in (('value',0),('value',-1),('value',True),('value',M.U64+1),('source_tree','0'*64),('unit','bytes'),('evidence_sha256','broken'),('obligation','')):
                    changed={**source,name:replace(source[name],**{field:value})};args=[inherited,std,acq,caller];args[which]=changed
                    self.reject('work price mutation '+str(which)+'/'+name+'/'+field+'/'+str(value),lambda args=args:M.work(self.value,*args))
        for pos in (2,3):
            for value in (0,-1,M.U64+1):
                args=[inherited,std,acq,caller];args[pos]=replace(args[pos],value=value)
                self.reject('upstream work positive '+str(pos)+'/'+str(value),lambda args=args:M.work(self.value,*args))
    def test_18_integer_overflow_and_exact_boundaries(self):
        rng=random.Random(33017)
        for _ in range(160):
            a=rng.randrange(0,M.U64+1);c=rng.randrange(0,M.U64+1)
            if a+c<=M.U64:self.assertEqual(M.add(a,c),a+c)
            else:self.reject('checked add overflow '+str(a)+'/'+str(c),lambda a=a,c=c:M.add(a,c))
            if a*c<=M.U64:self.assertEqual(M.mul(a,c),a*c)
            else:self.reject('checked mul overflow '+str(a)+'/'+str(c),lambda a=a,c=c:M.mul(a,c))
        self.assertEqual(M.add(M.U64,0),M.U64);self.assertEqual(M.mul(M.U64,1),M.U64)
        inherited,std,acq,caller=terms();std={**std,'range_next':b(M.U64,'work')}
        self.reject('whole work multiplication overflow',lambda:M.work(self.value,inherited,std,acq,caller))
        v=replace(self.value,future_root_owned_backing=b(M.U64));self.reject('whole storage overflow',lambda:M.storage(v))
        shape=M.describe(self.value);self.assertEqual(M.describe(self.value,limit=shape['logical_input_backing_bytes']),shape)
        self.reject('logical22 sum overflow',lambda:M.describe(self.value,limit=shape['logical_input_backing_bytes']-1))
    def test_19_destroy_then_some_only_no_refusal_or_unwind_credit(self):
        old,_=M.old_input(self.value)
        for route in ('none','unwind'):
            life=old.Retirement();life.provision_p0();life.enter();life.borrow();life.end_view();life.destroy(route)
            self.reject('no release after '+route,life.release,kind=old.Refused);self.assertTrue(life.held);self.assertTrue(life.p0)
        life=old.Retirement();life.provision_p0();life.enter();life.borrow()
        self.reject('no destroy while original view live',lambda:life.destroy('some'),kind=old.Refused)
        self.reject('no early refund',life.release,kind=old.Refused);life.end_view();life.destroy('some');life.release();self.assertFalse(life.held);self.assertTrue(life.p0);life.final_result();life.consume_result();self.assertTrue(life.p0)
        self.assertFalse(M.storage(self.value)['None_refusal_unwind_refund'])
    def test_20_pending_requirements_and_three_selectors_no_runtime(self):
        for result in (M.describe(self.value),M.storage(self.value),M.work(self.value,*terms())):
            upstream=result.get('upstream',result.get('all6_upstream'));selectors=result.get('selectors',result.get('all3_selectors'))
            self.assertEqual(len(upstream),6);self.assertEqual(set(upstream.values()),{'Pending'});self.assertEqual(len(selectors),3);self.assertEqual(set(selectors.values()),{'Pending'})
            self.assertFalse(result['operational_grant']);self.assertFalse(result['accepted_bound'])
    @classmethod
    def tearDownClass(cls):
        (I.HERE/'controls.json').write_text(json.dumps({'schema':1,'methods':20,'adverse_cases':len(CONTROLS),'controls':CONTROLS,'independent_reconstruction_assertions':sum(I.ASSERTIONS.values()),'assertion_counts':dict(I.ASSERTIONS),'fixture_source':I.record(I.V/'swift-real-profile-loader-binding/source-preimages/genuine.wasm'),'synthetic_labels_are_not_evidence':True,'Rust_or_compiler_or_native_runtime':False},sort_keys=True,indent=2)+'\n')
if __name__=='__main__':unittest.main()
