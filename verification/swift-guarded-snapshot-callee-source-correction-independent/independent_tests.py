"""Fresh narrow R1-R3 witnesses; synthetic residuals provide no pricing authority."""
from dataclasses import replace
from pathlib import Path
import copy, importlib.util, json, re, sys, unittest
sys.dont_write_bytecode = True
from review_custody import HERE, ROOT, PRODUCER, TREE, SEAL, canonical, load, row, sha, snapshot

# These exact frozen authored modules only evaluate host arithmetic. No query,
# compiler executable, runtime, fixture harness or producer tests are imported.
sys.path.insert(0, str(PRODUCER))
spec = importlib.util.spec_from_file_location('independently_reviewed_correction', PRODUCER / 'model.py')
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)
P = M.provider()
PROPOSAL = load(PRODUCER / 'proposal.json')
FRONTIERS = load(PRODUCER / 'source-closure-frontiers.json')
OLD = ROOT / 'verification/swift-guarded-snapshot-owned-provider-callee-interfaces'
LABEL = 'c' * 64
ADVERSE = 0
EQUALITIES = 0

def bound(value, unit='bytes'):
    return P.Bound(value, 'independent synthetic obligation only; no selected price or authority', TREE, LABEL, unit)

def fixture():
    genuine = M.sealed_input(ROOT / 'verification/swift-real-profile-loader-binding/source-preimages/genuine.wasm')
    ids = []
    for i, name in enumerate(P.IDENTITIES):
        body = genuine if i == 0 else ('independent-source-correction-' + name).encode()
        ids.append(P.Identity(name, body, sha(body), bound(len(body))))
    paths = []
    for i, body in enumerate((b'/a', b'/longer/b', b'/\xff/c', b'/\xc3\xa9/d', b'/last/path/e')):
        paths.append(P.PathInput(body, body, bound(len(body)), bound(len(body)), bound(len(body) + 1), LABEL))
    budget = {name: 1 for name in P.BUDGET_FIELDS}
    budget.update(execution_work=1_000_000_000, combined_bytes=268435456)
    return P.BindingInput(TREE, tuple(ids), tuple(paths), tuple(bytes([i]) * 32 for i in range(8)), budget,
                          LABEL, bound(128), bound(64), bound(512), bound(8572), bound(4097),
                          bound(73), bound(32), bound(396924, 'count'), bound(29394))

def contexts(v):
    shape = P.describe(v)
    return ([('DIGEST_MEMCMP_FRONTIER', 0, (32, 32), ())]
            + [('PATH_MEMCMP_FRONTIER', i, (len(p.native_body), len(p.retained_byte_preimage)), ()) for i, p in enumerate(v.paths)]
            + [('CONTAINS_RESIDUAL_FRONTIER', i, (len(p.native_body),), ()) for i, p in enumerate(v.paths)]
            + [('RANGE_NEXT_SOURCE_CLOSURE_FRONTIER', i, (), ('identity', 12, i)) for i in range(13)]
            + [('RANGE_NEXT_SOURCE_CLOSURE_FRONTIER', i + 13, (), ('path', 5, i)) for i in range(6)])

def residuals(v, unit):
    result = []
    for i, (frontier, occurrence, lengths, invocation) in enumerate(contexts(v)):
        contract = PROPOSAL['positive_residual_contracts'][frontier]
        result.append(M.ResidualBound(101 + i, unit, frontier, occurrence, TREE, M.TARGET, M.COMPILER,
                                     contract['native_target'], tuple(contract['argument_types']), contract['return_type'],
                                     lengths, LABEL, 'independent synthetic full composite obligation; never a selected bound',
                                     PROPOSAL['source_closure_frontiers_sha256'], invocation))
    return tuple(result)

def evaluate(v, *, work=None, storage=None, inherited=None, acquisition=None, caller=None, outcome='normal'):
    return M.evaluate(v, inherited if inherited is not None else {k: bound(43, 'work') for k in P.INHERITED_WORK},
                      work if work is not None else residuals(v, 'work'), storage if storage is not None else residuals(v, 'bytes'),
                      acquisition if acquisition is not None else bound(47, 'work'), caller if caller is not None else bound(59, 'work'), outcome=outcome)

def at(poly, b):
    return poly['fixed'] + b * poly['B'] + b * b * poly['B2']

def source_row(code, roles, b):
    def occurrence(r):
        return 2 * (r['leaves'] + r['bytes'] + at(r['pointee_bytes'], b) + at(r['pointee_leaves'], b))
    value = 2 + sum(code.count(ch) for ch in '()[].*&') + len(re.findall(r'\bas\b', code))
    value += sum(occurrence(roles[name]) for name in re.findall(r'\b_\d+\b', code))
    for token in re.finditer(r'(?<!\*)\bconst\s+(\d+_(?:usize|isize|u8|i32)|true|false|\(\))', code):
        literal = token[1]
        width = 0 if literal == '()' else 1 if literal in ('true', 'false') or literal.endswith('_u8') else 4 if literal.endswith('_i32') else 8
        value += 2 * (1 + width)
    if code == 'return;':
        value += occurrence(roles['_0'])
    return value

class IndependentReview(unittest.TestCase):
    def equal(self, actual, expected):
        global EQUALITIES
        self.assertEqual(actual, expected)
        EQUALITIES += 1

    def rejects(self, function):
        global ADVERSE
        with self.assertRaises(ValueError):
            function()
        ADVERSE += 1

    def mutate_contract(self, mutate):
        proposal = copy.deepcopy(PROPOSAL)
        mutate(proposal)
        self.rejects(lambda: M.validate_proposal(proposal))

    def test_R1_source_casts_full_aggregate_and_positive_helper_end_contract(self):
        num = (PRODUCER / 'official-source/library/core/src/num/mod.rs').read_text().splitlines()
        self.equal(num[1449:1454], ['#[cfg(target_pointer_width = "64")]', 'impl usize {', '    uint_impl! {', '        Self = usize,', '        ActualT = u64,'])
        uint = (OLD / 'official-source/library/core/src/num/uint_macros.rs').read_text().splitlines()
        self.equal(uint[2988:2992], ['        pub const fn overflowing_add(self, rhs: Self) -> (Self, bool) {',
                                    '            let (a, b) = intrinsics::add_with_overflow(self as $ActualT, rhs as $ActualT);',
                                    '            (a as Self, b)', '        }'])
        r1 = FRONTIERS['range_next']['R1']
        self.equal([(x['id'], x['type']) for x in r1['roles']], [('self', 'usize'), ('rhs', 'usize'), ('self_cast', 'u64'), ('rhs_cast', 'u64'), ('intrinsic_result', '(u64, bool)'), ('a', 'u64'), ('b', 'bool'), ('result_cast', 'usize'), ('return', '(usize, bool)')])
        self.equal(r1['casts'], 3)
        self.equal((r1['unobserved_full_aggregate']['size'], r1['unobserved_full_aggregate']['align']), (None, None))
        self.equal((r1['observed_outer_return']['size'], r1['observed_outer_return']['align']), (16, 8))
        self.assertIn('positive finite ending for every argument/result/local/return place', r1['operations'])
        types = load(PRODUCER / 'source-ledger.json')['types']
        self.assertNotIn('(u64, bool)', types)
        self.equal((types['ProductionClosure']['bytes'], types['ProductionClosure']['align']), (16, 8))
        for i in range(9):
            self.mutate_contract(lambda p, i=i: p['source_closure_frontiers']['range_next']['R1']['roles'].pop(i))
        for i in range(9):
            self.mutate_contract(lambda p, i=i: p['source_closure_frontiers']['range_next']['R1']['operations'].pop(i))
        for value in (0, 1, 9, 16):
            self.mutate_contract(lambda p, value=value: p['source_closure_frontiers']['range_next']['R1']['unobserved_full_aggregate'].update(size=value))
        for value in ('usize', 'i64', 'u32'):
            self.mutate_contract(lambda p, value=value: p['source_closure_frontiers']['range_next']['exact_macro_selection'].update(ActualT=value))

    def test_R2_exact_macro_runtime_and_short_circuit_consumption(self):
        intrinsic = (OLD / 'official-source/library/core/src/intrinsics/mod.rs').read_text().splitlines()
        self.assertIn('fn runtime$(<$($binders)*>)?($($arg: $ty),*) $( -> $ret )?', intrinsic[2622])
        self.assertIn('const fn compiletime$(<$($binders)*>)?($($arg: $ty),*) $( -> $ret )?', intrinsic[2628])
        self.assertIn('const_eval_select(($($val,)*), compiletime, runtime)', intrinsic[2635])
        ub = '\n'.join((OLD / 'official-source/library/core/src/ub_checks.rs').read_text().splitlines()[95:108])
        for token in ('@capture { } -> bool:', 'false', '!cfg!(miri)', ') && intrinsics::ub_checks()'):
            self.assertIn(token, ub)
        r2 = FRONTIERS['range_next']['R2']
        self.equal([x['type'] for x in r2['roles']], ['()', 'function item check_language_ub::{compiletime}, signature fn() -> bool', 'function item check_language_ub::{runtime}, signature fn() -> bool', 'bool', 'bool', 'bool', 'bool', 'bool'])
        self.equal((r2['callable_layouts']['compiletime_item'], r2['callable_layouts']['runtime_item']), (None, None))
        self.assertIn('compiletime BODY unselected; compiletime function-item intrinsic argument is retained', r2['selection'])
        self.assertIn('macro-generated runtime function is inside mandatory residual', r2['private_intrinsic_implementation'])
        nodes = {n['id']: n for n in load(PRODUCER / 'source-ledger.json')['nodes']}
        codes = [x['code'] for x in nodes['language_ub_check']['rows']]
        self.equal(codes, ['_1 = ConstEvalSelectResidual();', 'switchInt(copy _1);', '_2 = ub_checks_intrinsic();', '_0 = copy _2;', '_0 = const false;', 'return;'])
        self.equal([x['type'] for x in nodes['language_ub_check']['roles']], ['bool', 'bool', 'bool'])
        self.equal(nodes['language_ub_check']['calls'], [{'node': 'ub_checks_intrinsic', 'count': 1}])
        for i in range(8):
            self.mutate_contract(lambda p, i=i: p['source_closure_frontiers']['range_next']['R2']['roles'].pop(i))
            self.mutate_contract(lambda p, i=i: p['source_closure_frontiers']['range_next']['R2']['operations'].pop(i))
        for key in ('selection', 'expanded', 'private_intrinsic_implementation'):
            self.mutate_contract(lambda p, key=key: p['source_closure_frontiers']['range_next']['R2'].pop(key))

    def test_R3_autoborrow_matches_full_prior_contains_contract(self):
        option = (OLD / 'official-source/library/core/src/option.rs').read_text().splitlines()
        self.equal(option[632:635], ['    pub const fn is_some(&self) -> bool {', '        matches!(*self, Some(_))', '    }'])
        macros = (PRODUCER / 'official-source/library/core/src/macros/mod.rs').read_text().splitlines()
        self.equal(macros[430:439], ['macro_rules! matches {', '    ($expression:expr, $pattern:pat $(if $guard:expr)? $(,)?) => {', '        #[allow(non_exhaustive_omitted_patterns)]', '        match $expression {', '            $pattern $(if $guard)? => true,', '            _ => false', '        }', '    };', '}'])
        contains = FRONTIERS['contains']
        self.equal(contains['expanded'], 'match *self { Some(_) => true, _ => false }')
        self.equal([x['type'] for x in contains['roles']], ['Option<usize>', '&Option<usize>', '&Option<usize>', 'Option<usize>', 'Some(_) of Option<usize>', 'bool', 'bool', 'bool', 'bool'])
        for token in ('transmute_copy', 'from_raw_parts', 'source tuple', 'assert_unchecked', 'installed memchr_aligned'):
            self.assertIn(token, ' '.join(contains['all_prior_obligations_preserved']))
        self.equal(contains['unit_pair'], ['work', 'bytes'])
        self.equal(contains['count'], 5)
        for field in ('roles', 'operations', 'all_prior_obligations_preserved'):
            for i in range(len(contains[field])):
                self.mutate_contract(lambda p, field=field, i=i: p['source_closure_frontiers']['contains'][field].pop(i))
        self.equal(PROPOSAL['source_closure_frontiers'], FRONTIERS)
        self.equal(PROPOSAL['source_closure_frontiers_sha256'], sha(canonical(FRONTIERS)))

    def test_all_thirty_contexts_fail_closed_for_each_work_and_storage_unit(self):
        v = fixture()
        expected = contexts(v)
        _, actual = M.contexts(v)
        self.equal([(x['frontier'], x['occurrence'], x['body_lengths'], x.get('invocation_context', ())) for x in actual], expected)
        self.equal(len(expected), 30)
        self.equal([x[3] for x in expected[11:]], [('identity', 12, i) for i in range(13)] + [('path', 5, i) for i in range(6)])
        self.equal([expected[i][3] for i in (23, 29)], [('identity', 12, 12), ('path', 5, 5)])
        for unit in ('work', 'bytes'):
            good = residuals(v, unit)
            self.equal(M.residuals(v, good, unit), sum(x.value for x in good))
            self.rejects(lambda: M.residuals(v, list(good), unit))
            self.rejects(lambda: M.residuals(v, good + good[:1], unit))
            for i in range(30):
                self.rejects(lambda i=i: M.residuals(v, good[:i] + good[i+1:], unit))
                item = good[i]
                changes = [{'value': 0}, {'value': True}, {'value': -1}, {'value': M.U64 + 1},
                           {'source_tree': '0' * 64}, {'target': 'x86_64-apple-darwin'}, {'compiler_sha256': '0' * 64},
                           {'unit': 'bytes' if unit == 'work' else 'work'}, {'frontier': 'unknown'}, {'occurrence': True},
                           {'source_contract_sha256': '0' * 64}, {'argument_types': list(item.argument_types)},
                           {'argument_types': item.argument_types + ('u64',)}, {'return_type': 'unknown'},
                           {'native_target': 'unknown'}, {'body_lengths': list(item.body_lengths)},
                           {'body_lengths': (1947,)}, {'invocation_context': list(item.invocation_context)},
                           {'invocation_context': ('identity', 12, True)}, {'evidence_sha256': '0' * 63}, {'obligation': ' '}]
                for change in changes:
                    bad = good[:i] + (replace(item, **change),) + good[i+1:]
                    self.rejects(lambda bad=bad: M.residuals(v, bad, unit))
                if i >= 11:
                    bad = good[:i] + (replace(item, invocation_context=('path' if i < 24 else 'identity', 12, i)),) + good[i+1:]
                    self.rejects(lambda bad=bad: M.residuals(v, bad, unit))

    def test_changed_known_shell_reconciliation_has_no_complete_price_decrease(self):
        nodes = {n['id']: n for n in load(PRODUCER / 'source-ledger.json')['nodes']}
        abi = {r['node']: r for r in load(PRODUCER / 'native-ABI-boundaries.json')['rows']}
        old = load(OLD / 'proposal.json')
        current_interfaces = {x['name']: x for x in PROPOSAL['interfaces']}
        old_interfaces = {x['name']: x for x in old['interfaces']}
        # Direct operation arithmetic for the changed range closure and contains
        # caller shell; no producer derive.operation/compose or test replay.
        def compose(name, b):
            n = nodes[name]
            roles = {r['id']: r for r in n['roles']}
            work = 2 + sum(2 * (r['bytes'] + r['leaves'] + at(r['pointee_bytes'], b) + at(r['pointee_leaves'], b)) for r in roles.values() if r['kind'] == 'parameter')
            work += sum(2 + 2 * (r['bytes'] + r['leaves']) for r in roles.values())
            for r in n['rows']:
                amount = source_row(r['code'], roles, b)
                self.equal(amount, at(r['combined'], b))
                work += amount * (b + 1 if r['body_iterations'] else 1)
            work += abi.get(name, {}).get('logical_native_boundary_supplement', 0)
            slots = sum(r['bytes'] for r in roles.values())
            native = abi.get(name, {}).get('additional_reserved_native_interface_fields', 0)
            for edge in n['calls']:
                if edge['node'] in PROPOSAL['positive_residual_contracts']:
                    continue
                self.assertNotEqual(edge['node'], 'AUTHORED_CALLBACK')
                child_work, child_slots, child_native = compose(edge['node'], b)
                count = edge['count']
                work += child_work * (b + 1 if count == 'body+1' else count)
                slots += child_slots * (1 if count == 'body+1' else count)
                native += child_native * (1 if count == 'body+1' else count)
            return work, slots, native
        for b in (0, 3, 17, 1947, 65537):
            for name in ('range_next', 'slice_contains_u8'):
                work, slots, native = compose(name, b)
                interface = current_interfaces[name]
                self.equal(work, at(interface['per_call_source_and_native_shell'], b))
                self.equal(slots * interface['call_cap'], interface['reserved_distinct_source_places'])
                self.equal(native * interface['call_cap'], interface['reserved_distinct_native_ABI_fields'])
        self.equal(current_interfaces['range_next']['per_call_source_and_native_shell'], {'fixed': 2246, 'B': 0, 'B2': 0})
        for name in current_interfaces.keys() - {'range_next', 'slice_contains_u8'}:
            self.equal(current_interfaces[name], old_interfaces[name])
        for key in ('per_call_source_and_native_shell', 'reserved_distinct_source_places', 'reserved_distinct_native_ABI_fields'):
            self.equal(current_interfaces['slice_contains_u8'][key], old_interfaces['slice_contains_u8'][key])
        for field in ('fixed', 'B', 'B2'):
            self.equal(sum(x['per_request_shell'][field] for x in current_interfaces.values()), PROPOSAL['callee_source_shell_work'][field])
        self.equal(PROPOSAL['callee_source_shell_work'], {'fixed': 187034, 'B': 6867, 'B2': 160})
        self.equal(sum(x['reserved_distinct_source_places'] for x in current_interfaces.values()), 19029)
        self.equal(sum(x['reserved_distinct_native_ABI_fields'] for x in current_interfaces.values()), 9882)
        self.equal(PROPOSAL['additional_total_slots'], 19029 + 9882)
        self.equal(PROPOSAL['proposed_conditional_P0_fixed_excluding_positive_residual_storage'], 301733 + 28911)
        self.equal(len(PROPOSAL['closed_interfaces']), 10)
        self.equal(len(PROPOSAL['partial_interfaces']), 4)
        phases = load(PRODUCER / 'phase-reservations.json')['phases']
        self.equal(len(phases), 15)
        for phase in phases.values():
            self.equal((phase['provider_9696_retained'], phase['new_source_ledger_places'], phase['new_native_ABI_fields'], phase['new_total']), (9696, 19029, 9882, 28911))
            self.assertIn('exact30 invocation contexts', phase['positive_external_residual_storage'])
        delta = load(PRODUCER / 'correction-delta.json')
        self.assertIn('never a complete price decrease', delta['scope'])
        self.assertFalse(delta['refund'])
        self.equal(delta['all_moved_work_storage_mandatory_in'], 'RANGE_NEXT_SOURCE_CLOSURE_FRONTIER exact19 individual work AND bytes contexts')
        self.equal(len(abi), 23)

    def test_preserved_inherited_backing_terms_callback_no_refund_and_no_authority(self):
        v = fixture()
        normal = evaluate(v)
        base = P.storage(v)
        total_storage = 28911 + sum(x.value for x in residuals(v, 'bytes'))
        self.equal(normal['P0_preexisting'] - base['P0_preexisting'], total_storage)
        self.equal(normal['whole_external_storage'] - base['whole_external_storage'], total_storage)
        self.equal(base['original_binding_inline'], 1168)
        self.equal(normal['inherited_six_child_storage_parts'], base['inherited_six_child_storage_parts'])
        self.equal(len(normal['inherited_six_child_storage_parts']), 6)
        self.equal(PROPOSAL['provider_source_work_unchanged'], {'fixed': 276580, 'input_operand_bytes': 1324})
        self.equal(PROPOSAL['provider_slots_unchanged'], 9696)
        self.equal(PROPOSAL['authored_callback_body_work_inherited'], {'fixed': 7675, 'input_operand_bytes': 120})
        self.equal((PROPOSAL['authored_callback_body_cap_inherited'], PROPOSAL['authored_callback_adapter_calls']), (5, 5))
        self.equal(PROPOSAL['all10_inherited_terms'], P.INHERITED_WORK)
        self.equal(PROPOSAL['all10_inherited_terms']['L_str'], 67424)
        self.equal(PROPOSAL['upstream2_work_terms'], ['actual_prepaid_acquisition_work', 'future_provider_caller_and_launcher_work'])
        self.equal(normal['B_from_all22_actual_bodies'], max([len(x.preimage) for x in v.identities] + [len(x.native_body) for x in v.paths] + [len(x.retained_byte_preimage) for x in v.paths]))
        for i in range(12):
            ids = list(v.identities)
            ids[i] = replace(ids[i], backing=bound(0))
            self.rejects(lambda ids=ids: evaluate(replace(v, identities=tuple(ids))))
        for i in range(5):
            for field in ('native_backing', 'byte_preimage_backing', 'open_temporary'):
                paths = list(v.paths)
                paths[i] = replace(paths[i], **{field: bound(0)})
                self.rejects(lambda paths=paths: evaluate(replace(v, paths=tuple(paths))))
        for field in ('future_root_inline', 'future_root_owned_backing', 'immutable_diagnostic_backing', 'loader_native_temporaries', 'executable_open_temporary', 'file_resource_backing_each', 'error_backing_each', 'all_payload_destructor_temporaries'):
            self.rejects(lambda field=field: evaluate(replace(v, **{field: bound(0)})))
        for key in P.INHERITED_WORK:
            work = {k: bound(43, 'work') for k in P.INHERITED_WORK if k != key}
            self.rejects(lambda work=work: evaluate(v, inherited=work))
        self.rejects(lambda: evaluate(v, acquisition=bound(0, 'work')))
        self.rejects(lambda: evaluate(v, caller=bound(0, 'work')))
        for outcome in ('refusal', 'unwind'):
            result = evaluate(v, outcome=outcome)
            for field in ('whole_conditional_work', 'P0_preexisting', 'whole_external_storage'):
                self.equal(result[field], normal[field])
            self.assertFalse(result['None_refusal_unwind_refund'])
        self.assertTrue(normal['normal_release_requires_actual_original_payload_carrier_destruction_Some_token'])
        for key in ('L_str_selected', 'frontier_prices_selected', 'actual_acquisition_authenticated_owner_or_root_funding', 'accepted_bound', 'operational_grant', 'native_FieldLog_OTA_GA'):
            self.assertFalse(normal[key])
        self.equal(normal['all_six_upstream'], 'Pending')
        self.equal(normal['all_three_selectors'], 'Pending')

    def test_full_frozen_custody_and_failed_history_remain_historical(self):
        custody = snapshot()
        self.equal((custody['producer_members'], custody['producer_bytes']), (219, 13305313))
        self.equal((custody['producer_files_0444'], custody['producer_directories_0555']), (220, 22))
        self.equal(custody['complete_frozen_packets_checked'], 18)
        self.equal(len(custody['excluded_cache_metadata_only']), 1)
        failure = load(ROOT / 'verification/swift-semantic-adapter-root-review/provider-callee-source-correction-release-preflight-failure.json')
        self.equal(failure['exit'], 1)
        self.assertFalse(failure['all_member_byte_loop_completed'])
        self.assertFalse(failure['release_written'])
        self.assertFalse(failure['first_preflight_replayed'])
        producer_history = load(PRODUCER / 'attempt-history.json')
        self.equal(producer_history['new_correction_failed_preflights_or_tests'][0]['exit_code'], 1)
        self.assertIn('tuple', producer_history['new_correction_failed_preflights_or_tests'][0]['reason'])
        self.assertIn('JSON array', producer_history['new_correction_failed_preflights_or_tests'][0]['reason'])

if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentReview))
    report = {'schema': 1, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'adverse_cases_rejected': ADVERSE, 'independent_equalities': EQUALITIES,
              'fresh_independent_R1_R3_tests': True, 'producer_or_previous_review_tests_replayed': False,
              'compiler_invocations': 0, 'synthetic_bounds_select_prices': False,
              'native_UI_capture_simulator_emulator_phones_global_process_inventory_or_Git': False,
              'source146_tree_sha256': TREE, 'producer_seal_sha256': SEAL}
    (HERE / 'test-results.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(not result.wasSuccessful())
