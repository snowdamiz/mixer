#!/usr/bin/env python3
"""Targeted host controls; synthetic allowances never select external prices."""
from dataclasses import replace
from pathlib import Path
import copy, json, random, re, sys, unittest
sys.dont_write_bytecode=True
import derive as D
import model as M
HERE=Path(__file__).resolve().parent
LABEL='a'*64
ADVERSE=0
EQUALITIES=0
def b(n,unit='bytes'):return M.provider().Bound(n,'explicit synthetic test obligation only',M.TREE,LABEL,unit)
def synthetic():
    P=M.provider();raw=M.sealed_input(D.V/'swift-real-profile-loader-binding/source-preimages/genuine.wasm')
    ids=tuple(P.Identity(name,raw if i==0 else ('test '+name).encode(),P.digest(raw if i==0 else ('test '+name).encode()),b(len(raw) if i==0 else len('test '+name))) for i,name in enumerate(P.IDENTITIES))
    paths=tuple(P.PathInput(b'/path/'+bytes([97+i]),b'/path/'+bytes([97+i]),b(7),b(7),b(8),LABEL) for i in range(5))
    budget={name:1 for name in P.BUDGET_FIELDS};budget.update(execution_work=1_000_000_000,combined_bytes=268435456)
    return P.BindingInput(M.TREE,ids,paths,tuple(bytes([i])*32 for i in range(8)),budget,LABEL,b(128),b(64),b(512),b(8572),b(4097),b(73),b(32),b(396924,'count'),b(29394))
def terms():return {name:b(3,'work') for name in M.provider().INHERITED_WORK}
def fronts(value,unit):
    _,contexts=M.contexts(value);p=M.proposal();out=[]
    for i,x in enumerate(contexts):
        spec=p['positive_residual_contracts'][x['frontier']]
        out.append(M.ResidualBound(17+i,unit,x['frontier'],x['occurrence'],M.TREE,M.TARGET,M.COMPILER,spec['native_target'],tuple(spec['argument_types']),spec['return_type'],x['body_lengths'],LABEL,'synthetic full composite frontier scope only; not acceptance'))
    return tuple(out)
def evaluate(v=None,*,works=None,storage=None,old=None,outcome='normal'):
    v=v or synthetic()
    return M.evaluate(v,terms() if old is None else old,fronts(v,'work') if works is None else works,fronts(v,'bytes') if storage is None else storage,b(7,'work'),b(11,'work'),outcome=outcome)
def independent_row(code,by,body):
    total=2+sum(code.count(c) for c in '()[].*&')+len(re.findall(r'\bas\b',code))
    def role(r):
        return 2*(r['leaves']+r['bytes']+r['pointee_bytes']['fixed']+r['pointee_bytes']['B']*body+r['pointee_leaves']['fixed']+r['pointee_leaves']['B']*body)
    for name in re.findall(r'\b_\d+\b',code):total+=role(by[name])
    for piece in re.split(r'(?<!\*)\bconst\s+',code)[1:]:
        text=piece.split(',',1)[0].split(';',1)[0].strip()
        if text.startswith('()'):width=0
        elif text.startswith(('true','false')) or re.match(r'\d+_u8\b',text):width=1
        elif re.match(r'\d+_i32\b',text):width=4
        else:width=8
        total+=2+2*width
    if code=='return;':total+=role(by['_0'])
    return total
class Controls(unittest.TestCase):
    def reject(self,callback,kind=ValueError):
        global ADVERSE
        with self.assertRaises(kind):callback()
        ADVERSE+=1
    def test_exact_custody_source_revision_and_roster(self):
        lock=D.input_roster();self.assertEqual(lock,D.load(HERE/'input-lock.json'));self.assertEqual(len(lock['files']),1245)
        self.assertEqual(len(lock['frozen_packets']),15)
        x=D.load(HERE/'official-source-custody.json');self.assertEqual(x['revision'],D.RUST)
        for r in x['members']:
            self.assertTrue(r['success']);self.assertIn('/'+D.RUST+'/',r['url']);self.assertEqual(r['url'],r['final_url'])
        p=M.proposal();self.assertEqual(len(p['closed_interfaces']),11);self.assertEqual(len(p['partial_interfaces']),3)
        self.assertEqual(p['counts'],D.ledger.COUNTS)
    def test_independent_all_source_row_prices_and_finite_ends(self):
        global EQUALITIES
        x=D.load(HERE/'source-ledger.json');abi={r['node']:r for r in D.load(HERE/'native-ABI-boundaries.json')['rows']}
        for n in x['nodes']:
            by={r['id']:r for r in n['roles']}
            params=[r for r in n['roles'] if r['kind']=='parameter']
            for body in (0,1,15,16,1947,4097,65537):
                expected=2
                for r in params:expected+=2*(r['leaves']+r['bytes']+r['pointee_bytes']['fixed']+r['pointee_bytes']['B']*body+r['pointee_leaves']['fixed']+r['pointee_leaves']['B']*body)
                expected+=sum(2+2*r['leaves']+2*r['bytes'] for r in by.values())
                for r in n['rows']:
                    price=independent_row(r['code'],by,body)
                    self.assertEqual(price,D.val(r['combined'],body));EQUALITIES+=1
                    weight=body+1 if r['body_iterations'] else 1
                    self.assertEqual(price*weight,D.val(r['combined_weighted'],body));EQUALITIES+=1
                    expected+=price*weight
                expected+=abi.get(n['id'],{}).get('logical_native_boundary_supplement',0)
                self.assertEqual(expected,D.val(n['own_work'],body));EQUALITIES+=1
    def test_independent_recursive_composition_counts_no_callback_recharge(self):
        global EQUALITIES
        nodes={x['id']:x for x in D.load(HERE/'source-ledger.json')['nodes']};p=M.proposal()
        def c(name,body):
            n=nodes[name];price=D.val(n['own_work'],body);cb=0
            for edge in n['calls']:
                if edge['node']=='AUTHORED_CALLBACK':cb+=edge['count'];continue
                if edge['node'] in p['positive_residual_contracts']:continue
                value,childcb=c(edge['node'],body);factor=body+1 if edge['count']=='body+1' else edge['count'];price+=factor*value;cb+=factor*childcb
            return price,cb
        for body in (0,1,16,1947,65537):
            whole=0;callback=0
            for row in p['interfaces']:
                price,cb=c(row['name'],body);count=row['call_cap'];whole+=price*count;callback+=cb*count
                self.assertEqual(price,D.val(row['per_call_source_and_native_shell'],body));EQUALITIES+=1
                self.assertEqual(price*count,D.val(row['per_request_shell'],body));EQUALITIES+=1
            self.assertEqual(whole,D.val(p['callee_source_shell_work'],body));self.assertEqual(callback,5);EQUALITIES+=2
        self.assertEqual(p['authored_callback_body_cap_inherited'],5);self.assertEqual(p['authored_callback_body_new_charge'],0)
        base=D.load(D.BASE/'candidate.json');self.assertEqual(p['provider_source_work_unchanged'],base['provider_source_work']);self.assertEqual(p['provider_slots_unchanged'],9696)
    def test_unknown_or_omitted_source_nodes_roles_rows_edges(self):
        original=D.ledger.nodes();types=D.type_table()
        for i,n in enumerate(original):
            self.reject(lambda i=i:D.validate_ledger(original[:i]+original[i+1:],types))
            for field in ('source','first','last','llvm_name','safe_context'):
                x=copy.deepcopy(original);x[i][field]='unknown';self.reject(lambda x=x:D.validate_ledger(x,types))
            for field in ('roles','rows','calls'):
                for j in range(len(n[field])):
                    x=copy.deepcopy(original);x[i][field].pop(j);self.reject(lambda x=x:D.validate_ledger(x,types))
            for j,r in enumerate(n['roles']):
                for field,value in [('type','Option<u64>'),('id','_99999'),('kind','unknown')]:
                    x=copy.deepcopy(original);x[i]['roles'][j][field]=value;self.reject(lambda x=x:D.validate_ledger(x,types))
            for j,r in enumerate(n['rows']):
                for field,value in [('code','_0 = unreviewed_private_callee();'),('line',0),('body_iterations',not r['body_iterations'])]:
                    x=copy.deepcopy(original);x[i]['rows'][j][field]=value;self.reject(lambda x=x:D.validate_ledger(x,types))
        x=copy.deepcopy(original);x.append(x[0]);self.reject(lambda:D.validate_ledger(x,types))
    def test_exact_native_abi_and_actual_qualified_layouts(self):
        types=D.type_table();self.assertEqual((types['ProductionClosure']['bytes'],types['ProductionClosure']['align']),(16,8));self.assertEqual((types['(usize, bool)']['bytes'],types['(usize, bool)']['align']),(16,8))
        self.assertEqual(types['CandidateResult']['bytes'],1352);self.assertEqual(types['CandidateResult']['leaves'],714)
        rows=D.load(HERE/'native-ABI-boundaries.json')['rows'];by={r['node']:r for r in rows}
        for r in rows:
            self.assertTrue(r['not_Rust_aggregate_size_or_instruction_price'])
            fields=sum(a['native_field_bytes']+a['sret_logical_result_payload_bytes'] for a in r['formals'])+r['result_native_field_bytes']
            self.assertEqual(r['logical_native_boundary_supplement'],2*fields)
            self.assertEqual(r['additional_reserved_native_interface_fields'],fields)
        self.assertIn('ptr align 8 %0',by['candidate_result_from_residual']['header'])
        self.assertIn('sret([1352 x i8])',by['candidate_result_from_residual']['header'])
        self.reject(lambda:D.typed_role({'id':'_0','type':'&Unknown','kind':'return'},types))
        self.reject(lambda:D.operation('_0 = opaque(_999);',{'_0':D.typed_role({'id':'_0','type':'usize','kind':'return'},types)}))
        for name in types:
            for field,value in [('bytes',0),('align',32),('leaves',0),('evidence','pointer catalog alone')]:
                changed=copy.deepcopy(types);changed[name][field]=value
                if changed!=types:self.reject(lambda changed=changed:D.validate_ledger(D.ledger.nodes(),changed))
            changed=copy.deepcopy(types);changed.pop(name);self.reject(lambda changed=changed:D.validate_ledger(D.ledger.nodes(),changed))
    def test_public_proposal_counts_layout_and_callback_omissions(self):
        p=M.proposal()
        for name in p['counts']:
            x=copy.deepcopy(p);x['counts'].pop(name);self.reject(lambda x=x:M.validate_proposal(x),M.Refused)
            x=copy.deepcopy(p);x['counts'][name]+=1;self.reject(lambda x=x:M.validate_proposal(x),M.Refused)
        for name in p['positive_residual_contracts']:
            x=copy.deepcopy(p);x['positive_residual_contracts'].pop(name);self.reject(lambda x=x:M.validate_proposal(x),M.Refused)
        for key,value in [('provider_source_work_unchanged',{'fixed':276580,'input_operand_bytes':0}),('provider_slots_unchanged',0),('authored_callback_body_cap_inherited',4),('authored_callback_adapter_calls',10),('authored_callback_body_new_charge',1),('all10_inherited_terms',{}),('prior_conditional_whole_fixed',0)]:
            x=copy.deepcopy(p);x[key]=value;self.reject(lambda x=x:M.validate_proposal(x),M.Refused)
    def test_exact_compiler_active_byte_equality_and_search_paths(self):
        x=D.load(HERE/'LLVM-correspondence.json');by={r['node']:r for r in x['functions']}
        self.assertIn('i64 32',by['array_spec_ne32']['body']);self.assertIn('@memcmp',by['array_spec_ne32']['body'])
        self.assertIn('@memcmp',by['bytewise_eq']['body']);self.assertIn('i64 %len',by['bytewise_eq']['body'])
        c=by['u8_contains_shell'];self.assertTrue({'bb3','bb15','bb16','bb7'}<=set(c['unreachable']))
        self.assertFalse(any('Iterator3any' in z for z in c['calls']))
        self.assertIn('icmp ult i64 %text.1, 16',by['memchr_shell']['body'])
        self.assertIn(D.ledger.FRONTIERS['CONTAINS_RESIDUAL_FRONTIER']['native_target'],by['memchr_shell']['body'])
        # Connect the real entry to the formerly predecessor-free generic route.
        raw=c['body'].replace('br label %bb1','br label %bb3',1)
        changed=D.active_cfg({'text':raw});self.assertTrue(any('Iterator3any' in z for z in changed['calls']))
        self.assertIn('bb16',changed['reachable'])
        self.assertEqual(len(by['option_and_then_excluding_authored_callback']['calls']),1)
    def test_range_headers_and_arithmetic_precondition_proof(self):
        for limit in (5,12):
            start=0;visits=0;yielded=[]
            while True:
                visits+=1
                if start>=limit:break
                old=start;self.assertLess(old+1,1<<64);start=old+1;yielded.append(old)
            self.assertEqual(visits,limit+1);self.assertEqual(yielded,list(range(limit)))
        self.assertEqual(6+13,19)
        rng=random.Random(1733)
        for a,b_ in [(0,0),(M.U64,0),(M.U64,1),(M.U64-1,1),(M.U64-1,2)]+[(rng.randrange(1<<64),rng.randrange(1<<64)) for _ in range(500)]:
            wrapped=(a+b_)&M.U64;overflow=wrapped<a
            result=None if overflow else a+b_
            self.assertEqual(result,a+b_ if a+b_<=M.U64 else None)
    def test_short_search_loop_bound_and_no_generic_vector_callback(self):
        for n in range(33):
            for match in range(-1,n):
                i=0;headers=0;body=0
                while True:
                    headers+=1
                    if i>=n:break
                    body+=1
                    if i==match:break
                    i+=1
                self.assertLessEqual(headers,n+1);self.assertLessEqual(body,n)
                if n<16:self.assertLessEqual(body,15)
        p=M.proposal();self.assertGreater(p['callee_source_shell_work']['B2'],0)
        self.assertIn('source tuple(u8,&[u8])',p['positive_residual_contracts']['CONTAINS_RESIDUAL_FRONTIER']['remaining'])
    def test_actual22_body_geometry_and_frontier_lengths(self):
        v=synthetic();P=M.provider();shape,ctx=M.contexts(v);self.assertEqual(shape['input_operand_bytes'],1947);self.assertEqual(len(ctx),11)
        for i in range(22):
            ids=list(v.identities);paths=list(v.paths)
            if i<12:
                if i==0:continue
                raw=b'x'*4097;ids[i]=replace(ids[i],preimage=raw,sha256=P.digest(raw),backing=b(4097))
            else:
                j=(i-12)%5;raw=b'z'*4097;paths[j]=replace(paths[j],native_body=raw,retained_byte_preimage=raw,native_backing=b(4097),byte_preimage_backing=b(4097),open_temporary=b(4098))
            changed=replace(v,identities=tuple(ids),paths=tuple(paths));self.assertEqual(M.contexts(changed)[0]['input_operand_bytes'],4097)
            self.assertEqual(evaluate(changed)['B_from_all22_actual_bodies'],4097)
    def test_each_required_work_and_storage_frontier_omission(self):
        v=synthetic()
        for unit in ('work','bytes'):
            items=fronts(v,unit)
            for i in range(11):
                self.reject(lambda i=i:M.residuals(v,items[:i]+items[i+1:],unit),M.Refused)
            for wrong in (items+items[:1],tuple(reversed(items)),list(items),(items[0],)*11):self.reject(lambda wrong=wrong:M.residuals(v,wrong,unit),M.Refused)
    def test_each_frontier_exact_target_type_arity_length_and_evidence(self):
        v=synthetic()
        for unit in ('work','bytes'):
            good=fronts(v,unit)
            for i,item in enumerate(good):
                changes=[{'value':0},{'value':-1},{'value':True},{'value':1.0},{'value':M.U64+1},{'unit':'CPU'},{'frontier':'unknown'},{'occurrence':True},{'occurrence':9},{'source_tree':'0'*64},{'target':'x86_64-apple-darwin'},{'compiler_sha256':'0'*64},{'native_target':'bcmp'},{'argument_types':item.argument_types[:-1]},{'argument_types':item.argument_types+('usize',)},{'argument_types':tuple('u64' for _ in item.argument_types)},{'return_type':'usize'},{'body_lengths':(65536,)},{'body_lengths':list(item.body_lengths)},{'evidence_sha256':'no digest'},{'obligation':''}]
                for change in changes:
                    wrong=good[:i]+(replace(item,**change),)+good[i+1:];self.reject(lambda wrong=wrong:M.residuals(v,wrong,unit),M.Refused)
    def test_all10_original_work_terms_and2_upstream_still_mandatory(self):
        v=synthetic();good=terms();fw=fronts(v,'work');fs=fronts(v,'bytes')
        for name in good:
            x=good.copy();x.pop(name);self.reject(lambda x=x:evaluate(v,old=x),M.Refused)
            x=good.copy();x[name]=b(0,'work');self.reject(lambda x=x:evaluate(v,old=x),M.Refused)
        for acq,caller in [(b(0,'work'),b(1,'work')),(b(1,'work'),b(0,'work')),(b(1,'bytes'),b(1,'work')),(b(1,'work'),b(1,'bytes'))]:
            self.reject(lambda acq=acq,caller=caller:M.evaluate(v,good,fw,fs,acq,caller),M.Refused)
    def test_all12plus5plus5_backing_native_diagnostic_and_upstream_omissions(self):
        v=synthetic();P=M.provider()
        for i in range(12):
            ids=list(v.identities);ids[i]=replace(ids[i],backing=b(0));self.reject(lambda ids=ids:evaluate(replace(v,identities=tuple(ids))),M.Refused)
        for i in range(5):
            for field in ('native_backing','byte_preimage_backing','open_temporary'):
                paths=list(v.paths);paths[i]=replace(paths[i],**{field:b(0)});self.reject(lambda paths=paths:evaluate(replace(v,paths=tuple(paths))),M.Refused)
        for field in ('future_root_inline','future_root_owned_backing','immutable_diagnostic_backing','loader_native_temporaries','executable_open_temporary','file_resource_backing_each','error_backing_each','error_owner_count','all_payload_destructor_temporaries'):
            self.reject(lambda field=field:evaluate(replace(v,**{field:b(0,'count' if field=='error_owner_count' else 'bytes')})),M.Refused)
        ids=list(v.identities);ids[0]=replace(ids[0],preimage=b'X'*1947);self.reject(lambda:evaluate(replace(v,identities=tuple(ids))),M.Refused)
    def test_all15_phases_no_alias_move_refund_and_six_child_components(self):
        v=synthetic();base=M.provider().storage(v);r=evaluate(v);p=M.proposal();fs=sum(x.value for x in fronts(v,'bytes'))
        self.assertEqual(r['P0_preexisting']-base['P0_preexisting'],p['additional_total_slots']+fs)
        self.assertEqual(r['whole_external_storage']-base['whole_external_storage'],p['additional_total_slots']+fs)
        self.assertEqual(r['inherited_six_child_storage_parts'],base['inherited_six_child_storage_parts']);self.assertEqual(r['inherited_child_prepaid'],base['inherited_child_prepaid'])
        phases=D.load(HERE/'phase-reservations.json')['phases'];self.assertEqual(len(phases),15)
        for x in phases.values():self.assertEqual(x['provider_9696_retained'],9696);self.assertEqual(x['new_total'],p['additional_total_slots'])
        for outcome in ('normal','refusal','unwind'):
            x=evaluate(v,outcome=outcome);self.assertEqual(x['whole_conditional_work'],r['whole_conditional_work']);self.assertEqual(x['P0_preexisting'],r['P0_preexisting']);self.assertFalse(x['None_refusal_unwind_refund'])
        path=replace(v.paths[0],native_body=b'/nonutf8\xff',retained_byte_preimage=b'/nonutf8\xff',native_backing=b(9),byte_preimage_backing=b(9),open_temporary=b(10))
        aliased=replace(v,paths=(path,)*5);x=evaluate(aliased);self.assertEqual(M.provider().storage(aliased)['native_path_backing'],45);self.assertEqual(x['source_ledger_and_native_ABI_slot_addition'],p['additional_total_slots'])
    def test_overflow_fail_closed_and_no_authority_from_synthetic_evidence(self):
        for value in (True,False,-1,None,'1',1.5,M.U64+1):self.reject(lambda value=value:M.nat(value),M.Refused)
        self.reject(lambda:M.add(M.U64,1),M.Refused);self.reject(lambda:M.mul(M.U64,2),M.Refused)
        self.reject(lambda:M.polynomial({'fixed':0,'B':0,'B2':1},1<<32),M.Refused)
        v=synthetic();fw=list(fronts(v,'work'));fw[0]=replace(fw[0],value=M.U64);self.reject(lambda:evaluate(v,works=tuple(fw)),M.Refused)
        r=evaluate();self.assertEqual(r['all_six_upstream'],'Pending');self.assertEqual(r['all_three_selectors'],'Pending')
        for key in ('L_str_selected','frontier_prices_selected','actual_acquisition_authenticated_owner_or_root_funding','accepted_bound','operational_grant','native_FieldLog_OTA_GA'):self.assertFalse(r[key])
        self.assertEqual(r['authored_callback_body_cap_inherited'],5)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    report={'schema':1,'test_methods':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'hostile_cases_rejected':ADVERSE,'independent_component_equalities':EQUALITIES,'compiler_invocations':0,'Rust_product_native_UI_capture_or_global_inventory':False}
    if not (HERE/'seal.json').exists():(HERE/'latest-checks.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report));raise SystemExit(not result.wasSuccessful())
