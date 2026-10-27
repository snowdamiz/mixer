import copy, dataclasses, itertools, json, unittest
from pathlib import Path
import derive as D
import model as M
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
H='a'*64
def B(n,name='explicit synthetic source-bound obligation',unit='bytes'):return M.Bound(n,name,M.TREE,H,unit)
def synthetic():
    # Actual selected source constraint is used only to exercise arithmetic.
    # Every other preimage, path, budget and evidence label is synthetic, with
    # no accepted-bound or operational-grant route in this evaluator.
    source=(ROOT/'verification/swift-real-profile-loader-binding/source-preimages/genuine.wasm').read_bytes()
    identities=tuple(M.Identity(n,source if n=='source' else ('synthetic '+n).encode(),M.digest(source if n=='source' else ('synthetic '+n).encode()),B(len(source) if n=='source' else len('synthetic '+n))) for n in M.IDENTITIES)
    paths=tuple(M.PathInput(b'/synthetic/'+str(i).encode(),b'/synthetic/'+str(i).encode(),B(12),B(12),B(13),H) for i in range(5))
    budget={n:1 for n in M.BUDGET_FIELDS};budget.update(execution_work=1_000_000_000,combined_bytes=268435456)
    return M.BindingInput(M.TREE,identities,paths,tuple(bytes([i])*32 for i in range(8)),budget,H,B(128),B(64),B(512),B(8572),B(4097),B(73),B(32),B(396924,unit='count'),B(29394))
class Arithmetic(unittest.TestCase):
    def test_checked_u64_endpoints(self):self.assertEqual(M.add(M.U64,0),M.U64);self.assertEqual(M.mul(M.U64,1),M.U64)
    def test_invalid_numbers(self):
        for n in [True,False,-1,1.0,'1',None,M.U64+1]:
            with self.subTest(n=n),self.assertRaises(M.Refused):M.natural(n)
    def test_add_overflow(self):
        with self.assertRaises(M.Refused):M.add(M.U64,1)
    def test_mul_overflow(self):
        with self.assertRaises(M.Refused):M.mul(M.U64,2)
    def test_bound_positive_source_unit_and_provenance(self):
        for v in [B(0),dataclasses.replace(B(1),source_tree=M.OLD_TREE),dataclasses.replace(B(1),obligation=''),dataclasses.replace(B(1),evidence_sha256='x'),B(1,unit='work')]:
            with self.subTest(v=v),self.assertRaises(M.Refused):M.bound(v)
    def test_work_exact_positive_term_set(self):
        terms={n:B(1,unit='work') for n in M.WORK_TERMS};r=M.work(terms)
        self.assertEqual(r['whole_work'],895084428325956794+sum(M.WORK_TERMS.values()));self.assertFalse(r['accepted_bound']);self.assertFalse(r['operational_grant'])
        for name in M.WORK_TERMS:
            bad=dict(terms);bad.pop(name)
            with self.assertRaises(M.Refused):M.work(bad)
            bad=dict(terms);bad[name]=B(0,unit='work')
            with self.assertRaises(M.Refused):M.work(bad)
    def test_work_overflow(self):
        terms={n:B(1,unit='work') for n in M.WORK_TERMS};terms['L_str']=B(M.U64,unit='work')
        with self.assertRaises(M.Refused):M.work(terms)
    def test_work_rejects_unknown_and_wrong_units(self):
        terms={n:B(1,unit='work') for n in M.WORK_TERMS};terms['extra']=B(1,unit='work')
        with self.assertRaises(M.Refused):M.work(terms)
        terms.pop('extra');terms['L_str']=B(1)
        with self.assertRaises(M.Refused):M.work(terms)
class IdentityAndStorage(unittest.TestCase):
    def test_complete_storage_preserves_old_components(self):
        v=synthetic();r=M.storage(v)
        self.assertEqual(r['fixed_inline_owners'],292037);self.assertEqual(len(r['inherited_six_child_storage_parts']),6)
        self.assertEqual(r['whole_external_storage'],r['P0_preexisting']+r['inherited_child_prepaid']);self.assertFalse(r['binding_reviewed_or_accepted'])
        self.assertFalse(r['none_refusal_unwind_refund']);self.assertFalse(r['self_embedding_or_static_provider_proven'])
        self.assertEqual(r['P0_preexisting'],292037+128+64+512+sum(len(i.preimage) for i in v.identities)+120)
    def test_twelve_preimages_not_digest_only(self):
        v=synthetic()
        for j in range(12):
            ids=list(v.identities);ids[j]=dataclasses.replace(ids[j],preimage=b'')
            with self.subTest(j=j),self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,identities=tuple(ids)))
    def test_identity_omission_duplicate_order(self):
        v=synthetic()
        for ids in [v.identities[:-1],v.identities+(v.identities[-1],),(v.identities[1],v.identities[0])+v.identities[2:],(v.identities[0],)*12]:
            with self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,identities=ids))
    def test_identity_mismatch_and_backing(self):
        v=synthetic()
        for j in range(12):
            for change in [{'sha256':'b'*64},{'backing':B(1)}]:
                ids=list(v.identities);ids[j]=dataclasses.replace(ids[j],**change)
                with self.subTest(j=j,change=change),self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,identities=tuple(ids)))
    def test_exact_selected_source_required(self):
        v=synthetic();ids=list(v.identities);ids[0]=M.Identity('source',b'x'*1947,M.digest(b'x'*1947),B(1947))
        with self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,identities=tuple(ids)))
    def test_all_five_native_and_separate_byte_pointees(self):
        v=synthetic()
        for j in range(5):
            for change in [{'native_body':b''},{'retained_byte_preimage':b'changed'},{'native_backing':B(1)},{'byte_preimage_backing':B(1)},{'open_temporary':B(1)},{'correspondence_sha256':'bad'}]:
                ps=list(v.paths);ps[j]=dataclasses.replace(ps[j],**change)
                with self.subTest(j=j,change=change),self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,paths=tuple(ps)))
    def test_equal_path_content_does_not_credit_sharing(self):
        v=synthetic();v=dataclasses.replace(v,paths=(v.paths[0],)*5);r=M.storage(v)
        self.assertEqual(r['five_native_Path_pointee_backing'],60);self.assertEqual(r['five_separate_retained_byte_body_backing'],60)
    def test_paths_missing_unknown_position(self):
        v=synthetic()
        for ps in [v.paths[:-1],v.paths+(v.paths[0],),list(v.paths)]:
            with self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,paths=ps))
    def test_all17_product_fields_explicit_and_constraints(self):
        v=synthetic()
        for name in M.BUDGET_FIELDS:
            b=dict(v.product_budget);b.pop(name)
            with self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,product_budget=b))
            b=dict(v.product_budget);b[name]=0
            with self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,product_budget=b))
        b=dict(v.product_budget);b['execution_work']+=1
        with self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,product_budget=b))
    def test_all_claims_and_reviews_required(self):
        v=synthetic()
        for claims in [v.claims[:-1],tuple(b'x' for _ in range(8))]:
            with self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,claims=claims))
        with self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,binding_review_sha256=''))
    def test_native_original_owner_and_teardown_bounds_positive(self):
        v=synthetic()
        for field in ['loader_native_temporaries','executable_open_temporary','file_resource_backing_each','error_backing_each','error_owner_count','all_payload_destructor_temporaries']:
            value=getattr(v,field);bad=dataclasses.replace(value,value=value.value-1)
            with self.subTest(field=field),self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,**{field:bad}))
    def test_future_root_backing_and_diagnostic_omission(self):
        v=synthetic()
        for field in ['future_root_inline','future_root_owned_backing','immutable_diagnostic_backing']:
            with self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,**{field:B(0)}))
    def test_count_bytes_not_interchangeable(self):
        v=synthetic()
        with self.assertRaises(M.Refused):M.check_inputs(dataclasses.replace(v,error_owner_count=B(396924)))
    def test_storage_checked_overflow(self):
        v=synthetic()
        with self.assertRaises(M.Refused):M.storage(dataclasses.replace(v,future_root_inline=B(M.U64)))
class Ownership(unittest.TestCase):
    def active(self):
        r=M.Retirement();r.provision_p0();r.enter();return r
    def test_P0_before_entry(self):
        with self.assertRaises(M.Refused):M.Retirement().enter()
    def test_view_ends_before_consuming_originals(self):
        r=self.active();r.borrow()
        for route in ('some','none','unwind'):
            with self.assertRaises(M.Refused):r.destroy(route)
        r.end_view();r.destroy('some');r.release();r.final_result();r.consume_result();self.assertTrue(r.p0)
    def test_none_and_unwind_never_refund(self):
        for route in ('none','unwind'):
            r=self.active();r.borrow();r.end_view();r.destroy(route)
            with self.assertRaises(M.Refused):r.release()
            self.assertTrue(r.held)
    def test_early_duplicate_and_repeated_entry_rejected(self):
        r=self.active()
        with self.assertRaises(M.Refused):r.release()
        r.borrow();r.end_view()
        with self.assertRaises(M.Refused):r.borrow()
        r.destroy('some');r.release()
        for action in [r.release,r.enter,lambda:r.destroy('some')]:
            with self.assertRaises(M.Refused):action()
    def test_no_result_borrow_escape_or_postP0_disposal(self):
        r=self.active();r.borrow()
        with self.assertRaises(M.Refused):r.final_result()
        r.end_view();r.destroy('some');r.release();r.final_result();r.p0=False
        with self.assertRaises(M.Refused):r.consume_result()
class Binder(unittest.TestCase):
    def test_source_addition_keeps_all_old_bytes(self):
        old=b'mod old { fn retained() {}\n}\n';snippet=b'mod new {}\n';new=old[:-2]+b'\n\n    // Private outer caller candidate; all prior bodies remain exact.\n'+snippet+b'}\n'
        D.check_exact_addition(old,new,snippet)
        for bad in [new.replace(b'retained',b'changed'),new+b'x',new[1:],new.replace(b'mod new',b'pub mod new')]:
            with self.assertRaises(ValueError):D.check_exact_addition(old,bad,snippet)
    def test_cycle_unknown_terminal_and_unknown_role_fail_closed(self):
        for blocks in [{'bb0':{'operations':['goto -> bb0;']}},{'bb0':{'operations':['new_terminal;']}}]:
            with self.assertRaises(ValueError):D.paths(blocks)
        with self.assertRaises(ValueError):D.price('_3 = copy _4;',{},None)
    def test_inventory_keeps_every_role_and_moved_place(self):
        a=json.loads((HERE/'phase-roster.json').read_bytes());self.assertEqual(len(a['all_new_roles']),130)
        self.assertEqual(sum(r['bytes'] for r in a['all_new_roles']),56414);self.assertEqual(len({r['id'] for r in a['all_new_roles']}),130)
        self.assertTrue(all(r['funded_by']=='P0' and r['reserved_last']=='P0_AFTER_FINAL_RESULT_CONSUMPTION' for r in a['all_new_roles']))
        self.assertEqual(set(a['new_slot_reserved_bytes_each_phase'].values()),{56414});self.assertFalse(a['move_alias_sharing_refund_credit'])
    def test_exact_path_convention_preserved(self):
        a=json.loads((HERE/'candidate.json').read_bytes());self.assertEqual(a['producer_successor_leaf_paths'],43);self.assertEqual(a['terminal_paths_including_unwind'],56)
        self.assertEqual(a['consumer_terminal_paths'],32);self.assertEqual(sum(r['additional_explicit_unwind_or_terminate_terminals'] for r in a['terminal_convention_reconciliation']),13)
    def test_whole_fixed_addition_and_account_once(self):
        a=json.loads((HERE/'candidate.json').read_bytes());self.assertEqual(a['conditional_whole_work_fixed_with_new_outer'],895084428323053276+194231+1039*3+2706170)
        self.assertEqual(a['conditional_account_surface_once'],2628088+194231+1039*3);self.assertFalse(a['L_str5080_selected'])
if __name__=='__main__':unittest.main(verbosity=2)
