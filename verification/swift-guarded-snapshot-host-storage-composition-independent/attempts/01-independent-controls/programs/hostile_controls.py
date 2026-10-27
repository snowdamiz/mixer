"""Independent executable adversarial evaluator/graph/lifetime controls.

All successful evaluations use explicitly synthetic, unselected inputs. They
demonstrate conditional equations only and never qualify a reservation.
"""
from pathlib import Path
import copy, dataclasses, importlib.util, json, random, sys, unittest
sys.dont_write_bytecode = True
from audit import CANDIDATE, V, ROOT, SOURCE, HOST, source_path, js, oracle_parts, source_edges, assert_dag, graph_closure, layout_catalog, concrete_extent, generic_roster

spec = importlib.util.spec_from_file_location('storage_candidate_under_test', CANDIDATE / 'model.py')
target = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = target
spec.loader.exec_module(target)

def bound(n=1): return target.Bound(n, 'SYNTHETIC ONLY: no actual-source extent qualification')
def inputs():
    return target.RequiredStorage(SOURCE, HOST,
        tuple(target.PathBacking(bound(12 + n), bound(20 + n), bound(33 + n)) for n in range(5)),
        bound(1024), bound(1024), bound(512), bound(1024),
        target.OriginalValidationBudget(bound(65536), bound(8192), bound(4096)),
        bound(4096), bound(8192), bound(512), bound(256), bound(1024), bound(4097),
        bound(1024), bound(1024), target.CountBound(16, 'SYNTHETIC count only'), bound(2048))

class HostileStorageControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv = js(CANDIDATE / 'inline-inventory.json')
        cls.table = layout_catalog()
        cls.ledger = js(V / 'swift-guarded-snapshot-loader-work-source146/mir-ledger.json')
    def setUp(self): self.x = inputs()
    def result(self, x=None): return target.evaluate(self.inv, x or self.x)
    def reject(self, x):
        with self.assertRaises(target.Refused): self.result(x)

    def test_independent_integer_oracle_across_128_different_geometry_cuts(self):
        rng = random.Random(0x7300A146)
        for index in range(128):
            source_limit = rng.randrange(1, 67108865)
            p = tuple(target.PathBacking(bound(n), bound(n + rng.randrange(0,1024)), bound(n + rng.randrange(1,1024))) for n in [rng.randrange(1,200000) for _ in range(5)])
            x = dataclasses.replace(self.x, paths=p,
                original_validation=target.OriginalValidationBudget(bound(source_limit), bound(rng.randrange(1,16777217)), bound(rng.randrange(1,1048577))),
                source_file_bytes=bound(rng.randrange(1,source_limit+1)), executable_file_bytes=bound(rng.randrange(1,67108865)),
                build_file_bytes=bound(rng.randrange(1,131073)), session_file_bytes=bound(rng.randrange(1,65537)),
                error_owner_count=target.CountBound(rng.randrange(1,1024), 'synthetic count'), error_backing_each=bound(rng.randrange(1,10000)))
            p0, parts, buffers = oracle_parts(x); actual = self.result(x)
            self.assertEqual((actual['P0_preexisting_required_before_policy_quote_account_entry'], actual['six_child_storage_parts'], actual['loader_buffer_peak']), (p0, parts, buffers), index)
            self.assertEqual(actual['whole_external_storage'], p0 + sum(parts.values()))
            self.assertTrue(actual['conditional_storage_interface_only'])
            self.assertTrue(all(actual[x] for x in ['RootPolicyPending','WholeQuotePending','WorkAuditPending']))
            self.assertFalse(actual['whole_host_grant'])

    def test_every_required_byte_bound_rejects_nonpositive_noninteger_or_overflow(self):
        fields = [f.name for f in dataclasses.fields(self.x) if type(getattr(self.x, f.name)) is target.Bound]
        for field in fields:
            for bad in [0, -1, True, False, 1.0, float('inf'), float('nan'), None, '1024', 1 << 64]:
                self.reject(dataclasses.replace(self.x, **{field:bound(bad)}))
            for wrong in [None, 1, target.CountBound(1,'synthetic'), object()]:
                self.reject(dataclasses.replace(self.x, **{field:wrong}))

    def test_no_missing_default_inputs_or_inherited_input_class(self):
        for field in dataclasses.fields(target.RequiredStorage):
            self.assertIs(field.default, dataclasses.MISSING)
            self.assertIs(field.default_factory, dataclasses.MISSING)
        self.reject(None)
        self.reject(dataclasses.asdict(self.x))
        class Subclass(target.RequiredStorage): pass
        self.reject(Subclass(**{f.name:getattr(self.x,f.name) for f in dataclasses.fields(self.x)}))

    def test_every_path_dimension_and_all_five_slots_are_mandatory(self):
        for index in range(5):
            for field in ['encoded_bytes','p0_backing_bytes','open_temporary_bytes']:
                for bad in [0, -1, True, None, 1 << 64]:
                    paths = list(self.x.paths); paths[index] = dataclasses.replace(paths[index], **{field:bound(bad)})
                    self.reject(dataclasses.replace(self.x, paths=tuple(paths)))
                paths = list(self.x.paths); paths[index] = dataclasses.replace(paths[index], **{field:target.CountBound(1,'count')})
                self.reject(dataclasses.replace(self.x, paths=tuple(paths)))
        for paths in [(), self.x.paths[:4], self.x.paths + (self.x.paths[0],), list(self.x.paths)]: self.reject(dataclasses.replace(self.x, paths=paths))
        self.reject(dataclasses.replace(self.x, paths=(None,) + self.x.paths[1:]))

    def test_path_pointees_and_native_conversions_are_distinct(self):
        for p in [target.PathBacking(bound(4097),bound(4096),bound(4098)), target.PathBacking(bound(4097),bound(4097),bound(4097)), target.PathBacking(bound((1<<64)-1),bound((1<<64)-1),bound((1<<64)-1))]:
            self.reject(dataclasses.replace(self.x, paths=(p,) + self.x.paths[1:]))
        p = target.PathBacking(bound(1<<32), bound((1<<32)+3), bound((1<<32)+1))
        result = self.result(dataclasses.replace(self.x, paths=(p,) + self.x.paths[1:]))
        self.assertFalse(result['whole_host_grant'])
        self.assertGreater(result['P0_preexisting_required_before_policy_quote_account_entry'], 1 << 32)
        for n in [1,4096]: self.reject(dataclasses.replace(self.x, executable_open_temporary=bound(n)))

    def test_count_and_bytes_are_not_interchangeable(self):
        for n in [0, -1, None, False, True, 2.0, '1', 1 << 64]: self.reject(dataclasses.replace(self.x,error_owner_count=target.CountBound(n,'synthetic')))
        self.reject(dataclasses.replace(self.x,error_owner_count=bound(1)))
        self.reject(dataclasses.replace(self.x,error_backing_each=target.CountBound(1,'synthetic')))
        for label in ['', ' ', None, 1]:
            self.reject(dataclasses.replace(self.x,error_owner_count=target.CountBound(1,label)))
            self.reject(dataclasses.replace(self.x,outer_parent_inline=target.Bound(1,label)))

    def test_binding_must_dominate_all_512_declared_fields(self):
        for n in [8,16,80,256,511]: self.reject(dataclasses.replace(self.x,reviewed_binding_object=bound(n)))
        self.assertEqual(self.result()['late_returned_payload_owners']['whole_outer_carrier_bytes'],13624)
        self.assertTrue(self.result()['late_returned_payload_owners']['carrier_inline_already_in_P0_roster'])

    def test_original_limits_and_actual_fixture_extents_refuse_widening(self):
        for field, cap in [('source_bytes',67108864),('metadata_bytes',16777216),('scratch_bytes',1048576)]:
            for value in [0,-1,True,cap+1]:
                self.reject(dataclasses.replace(self.x, original_validation=dataclasses.replace(self.x.original_validation, **{field:bound(value)})))
            self.reject(dataclasses.replace(self.x, original_validation=dataclasses.replace(self.x.original_validation, **{field:target.CountBound(1,'synthetic')})))
        for field, cap in [('source_file_bytes',65536),('executable_file_bytes',67108864),('build_file_bytes',131072),('session_file_bytes',65536)]:
            self.reject(dataclasses.replace(self.x,**{field:bound(cap+1)}))
        self.reject(dataclasses.replace(self.x,original_validation=object()))

    def test_inventory_digest_binds_role_identity_extent_recursion_and_source(self):
        for category in ['caller_slots','leaf_slots','loader_slots']:
            for field, value in [('id','duplicate'),('type','other-scope::Error')]:
                inv = copy.deepcopy(self.inv); inv[category][0][field] = value
                with self.assertRaises(target.Refused): target.evaluate(inv,self.x)
        for field, value in [('source_tree_sha256','0'*64),('host_tree_sha256','0'*64),('all_authored_frame_call_graph_acyclic',False),('required_layouts',['invented'])]:
            inv=copy.deepcopy(self.inv);inv[field]=value
            with self.assertRaises(target.Refused):target.evaluate(inv,self.x)
        for field in ['source_tree_sha256','host_tree_sha256']: self.reject(dataclasses.replace(self.x, **{field:'0'*64}))
        with self.assertRaises(target.Refused):target.checked_inventory(self.inv, {'invented':bound(1)})

    def test_fully_qualified_error_records_and_wrapper_bounds(self):
        self.assertEqual(concrete_extent('std::result::Result<usize, Error>',self.table),56)
        self.assertEqual(concrete_extent('std::result::Result<usize, std::io::Error>',self.table),16)
        self.assertNotEqual(concrete_extent('Error',self.table),concrete_extent('std::io::Error',self.table))
        rows=[x for x in self.inv['loader_slots'] if x['layout_proof']['rule']=='observed-inline-containing-wrapper-upper-bound']
        self.assertEqual(len(rows),21)
        self.assertTrue(all(x['layout_proof']['compiler_key'] in self.table for x in rows))

    def test_source_closed_generic_roster_is_not_arbitrary_T_D_or_N(self):
        extracted=js(V/'swift-guarded-snapshot-loader-work-source146/mir-extraction146.json')
        roster=generic_roster(extracted)
        self.assertEqual((len(roster['elements']),roster['N']),(10,[4096,16384]))
        changed=copy.deepcopy(extracted)
        next(iter(changed['functions'].values()))['calls'].append('_0 = retained_profile_loader_v1::Bytes::<32768>::new() -> [return: bb0];')
        with self.assertRaises(AssertionError):generic_roster(changed)
        changed=copy.deepcopy(extracted)
        next(iter(changed['functions'].values()))['calls'].append('_0 = experimental::account::Buffer::<u64>::new(move _1) -> [return: bb0];')
        with self.assertRaises(AssertionError):generic_roster(changed)

    def test_callback_graph_missing_edge_target_or_reentrancy_refuses(self):
        nodes=self.ledger['nodes'];root=self.ledger['roots']['loader']
        self.assertEqual(assert_dag(nodes),219);self.assertEqual(len(graph_closure(nodes,root)),219)
        for callee in [root,'unpriced::callback']:
            changed=copy.deepcopy(nodes);changed[root]['calls'].append({'callee':callee})
            with self.assertRaises(AssertionError):assert_dag(changed)
        changed=copy.deepcopy(nodes);changed.pop(next(iter(changed[root]['calls']))['callee'])
        with self.assertRaises(AssertionError):graph_closure(changed,root)

    def test_executable_peak_uses_disjoint_lifetimes_and_proof_copy_coexists(self):
        small=self.result(); large=self.result(dataclasses.replace(self.x, executable_file_bytes=bound(67108864)))
        self.assertEqual(small['loader_buffer_peak'],512+256+4096+65536+8192+4096)
        self.assertEqual(large['loader_buffer_peak'],512+256+67108864)
        path='src/experimental_swift_reactor/retained_profile_loader_v1.rs'; source=source_path(path).read_text()
        with self.assertRaises(AssertionError):source_edges({path:source.replace('drop(executable);','/* removed drop */',1)})
        with self.assertRaises(AssertionError):source_edges({path:source.replace('if !source_bytes_equal(&proof, &input)','if true',1)})

    def test_exact_source_prepayment_and_destruction_token_edges_are_required(self):
        path='src/experimental_swift_reactor/cache/initial_profile_v1.rs'; source=source_path(path).read_text()
        with self.assertRaises(AssertionError):source_edges({path:source.replace('let reservation = account.reserve_whole_v1(quote)?;','/* removed prepay */',1)})
        path='src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'; source=source_path(path).read_text()
        with self.assertRaises(AssertionError):source_edges({path:source.replace('drop(self);','/* carrier still alive */',1)})
        path='src/experimental_swift_reactor/control.rs'; source=source_path(path).read_text()
        with self.assertRaises(AssertionError):source_edges({path:source.replace('Err(failure)=>{cache_retirement=Some(failure);drop(cache);}','Err(failure)=>{cache_retirement=Some(failure);}',1)})

    def test_six_positive_parts_never_charge_product_H_twice(self):
        y=self.result(); owners=y['source_object_owner_roster']
        self.assertEqual(len(y['six_child_storage_parts']),6)
        self.assertTrue(all(v>0 for v in y['six_child_storage_parts'].values()))
        self.assertEqual(y['six_child_storage_parts']['P4_leaf'],111770+1899541+54976)
        self.assertEqual([x['bytes'] for x in owners if x['id']=='product-accepted-full-retention'],[1899541])
        self.assertEqual(y['product_recipe']['H_unit'],81327);self.assertEqual(y['product_recipe']['H_added_again'],0)
        self.assertEqual(y['inline_subtotals'],{'P0':234375,'child':76696,'leaf':320766,'loader':644008,'validator':171197})
        self.assertNotIn(3597716,[x['bytes'] for x in owners])

    def test_late_original_files_errors_arc_and_full_charge_survive_payload(self):
        y=self.result(); owners={x['id']:x for x in y['source_object_owner_roster']}
        for name in ['actual-six-File-resource-envelope','actual-original-Error-backing-envelope','actual-shared-Cancellation-ArcInner']:
            self.assertEqual(owners[name]['last'],'P5_DESTROYING')
        self.assertEqual(owners['actual-six-File-resource-envelope']['bytes'],6144)
        self.assertEqual(owners['actual-original-Error-backing-envelope']['bytes'],16384)
        self.assertEqual(owners['actual-shared-Cancellation-ArcInner']['bytes'],24)
        self.assertEqual(owners['original-proof-source-Box']['last'],'P4_LEAF')
        self.assertEqual(owners['initial-cache-requested-allocation-pool']['last'],'P4_LEAF')
        self.assertFalse(y['late_returned_payload_owners']['proof_or_cache_dynamic_backing_survives_P5'])
        child=y['child_prepaid_storage']; trace=y['conservative_held_charge_trace']
        self.assertEqual([r['child_held'] for r in trace[:2]],[0,0])
        self.assertTrue(all(r['child_held']==child for r in trace[2:-1]))
        self.assertEqual(trace[-1]['child_held'],0)
        self.assertTrue(all(v<=y['whole_external_storage'] for v in y['logical_owner_and_reservation_union_by_phase'].values()))

    def test_retention_unwind_missing_token_early_refund_and_double_use(self):
        for mode in ['success','missing-token','unwind','ordinary-drop','unused-ticket']:
            q=target.RetentionControl()
            for action in [q.quote_after_p0,lambda:q.reserve(7),q.dispatch,q.retire]:
                with self.assertRaises(target.Refused):action()
            q.provision_p0(1024);q.quote_after_p0();q.reserve(7)
            if mode!='unused-ticket':q.dispatch()
            if mode=='success':
                with self.assertRaises(target.Refused):q.retire()
                q.destroy(True);self.assertEqual(q.held,7);q.retire();self.assertEqual(q.held,0)
                for action in [q.retire,q.dispatch,lambda:q.destroy(True)]:
                    with self.assertRaises(target.Refused):action()
            else:
                if mode=='missing-token':q.destroy(True);q.token=False
                elif mode=='unwind':q.destroy(False)
                else:q.implicit_drop_or_unwind()
                self.assertEqual(q.held,7)
                with self.assertRaises(target.Refused):q.retire()

    def test_every_monotone_positive_cut_and_each_count_increases_its_funding(self):
        baseline=self.result()
        for field in [f.name for f in dataclasses.fields(self.x) if type(getattr(self.x,f.name)) is target.Bound]:
            if field in ['source_file_bytes','executable_file_bytes','build_file_bytes','session_file_bytes']:continue
            changed=dataclasses.replace(self.x,**{field:bound(getattr(self.x,field).bytes+1)})
            self.assertGreater(self.result(changed)['whole_external_storage'],baseline['whole_external_storage'],field)
        changed=dataclasses.replace(self.x,error_owner_count=target.CountBound(17,'synthetic'))
        self.assertEqual(self.result(changed)['whole_external_storage']-baseline['whole_external_storage'],1024)

    def test_checked_boundary_overflow_never_wraps_or_creates_authority(self):
        self.assertEqual(target.add((1<<64)-1,0),(1<<64)-1)
        for action in [lambda:target.add((1<<64)-1,1),lambda:target.mul(1<<63,2)]:
            with self.assertRaises(target.Refused):action()
        for field in ['outer_parent_inline','outer_parent_owned_backing','file_resource_backing_each','error_backing_each','all_payload_destructor_temporaries']:
            self.reject(dataclasses.replace(self.x,**{field:bound((1<<64)-1)}))

    def test_cache_source_capacity_remains_conditional_and_no_dynamic_runtime_claim(self):
        y=self.result(); basis=y['resource_capacity_basis']
        self.assertEqual(basis['initial_cache_max_requested_bytes'],64*136+64*16+512*32+512*56+192)
        self.assertFalse(basis['acceptance']);self.assertTrue(basis['compiled_std_correspondence_pending'])
        self.assertFalse(basis['allocator_footprint']);self.assertFalse(y['native_runtime_or_GA'])

if __name__=='__main__':unittest.main(verbosity=2)
