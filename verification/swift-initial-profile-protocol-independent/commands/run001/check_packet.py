#!/usr/bin/env python3
"""Independent, finite offline data/custody checks; never product authority."""
from pathlib import Path
import copy
import hashlib
import json
import re
import unittest

OUT = Path(__file__).resolve().parent
PACKET = OUT.parent / 'swift-initial-profile-construction-protocol'
PRIOR = OUT.parent / 'swift-profile-header-contract-independent'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(name):
    return json.loads((PACKET / name).read_text())

def tree(members):
    return hashlib.sha256(''.join(
        f"{m['path']}\t{m['bytes']}\t{m['sha256']}\n"
        for m in sorted(members, key=lambda m: m['path'])
    ).encode()).hexdigest()

def check_seal(folder, expected_sha, count, byte_count, expected_tree=None):
    assert sha(folder / 'seal.json') == expected_sha
    seal = json.loads((folder / 'seal.json').read_text())
    members = seal['members']
    assert len(members) == seal['member_count'] == count
    assert len({m['path'] for m in members}) == count
    assert sum(m['bytes'] for m in members) == seal['total_bytes'] == byte_count
    assert tree(members) == seal['tree_sha256']
    if expected_tree:
        assert tree(members) == expected_tree
    for m in members:
        relative = Path(m['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        p = folder / relative
        assert not p.is_symlink() and p.is_file()
        assert p.stat().st_size == m['bytes'] and sha(p) == m['sha256']
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*')
              if p.is_file() and p.name not in ()}
    assert actual == {m['path'] for m in members} | {'seal.json', 'seal.sha256'}
    return seal

def norm(value):
    return ''.join(value.split())

class IndependentPacketChecks(unittest.TestCase):
    def test_01_assigned_packet_custody(self):
        check_seal(PACKET,
            'eee07facb219eaba5e135f3970d2f508a0acd20b3eb81f47f0dd9771412d5e91',
            210, 19883923,
            '15f6be2e2eb20c145167e01881d39e5473b29b963c766a151b5ee7b0932d644c')

    def test_02_prior_review_custody(self):
        check_seal(PRIOR,
            '3addafb44d2be614b7d859c8a329775ab7e7651d6078202686abc0430f2e5821',
            35, 536897)
        for name in ['review.md', 'continuation-shape.md', 'required-amendments.json']:
            self.assertEqual((PRIOR / name).read_bytes(),
                (PACKET / 'inputs/independent' / name).read_bytes())

    def test_03_root_selection_and_budget(self):
        root = PACKET / 'inputs/root'
        self.assertEqual(sha(root / 'profile-header-amendment-selection.json'),
            '31be99a2e0382267db3eb4722b322aec60369aeaaa3b54b323254aee37791b30')
        selected = read('inputs/root/profile-header-amendment-selection.json')
        self.assertEqual(sha(root / 'selected-host-budget.json'), selected['selected_host_budget_sha256'])
        self.assertEqual(sha(root / 'profile-header-selected-amendments.md'), selected['amendment_sha256'])
        self.assertFalse(selected['product_implementation_selected'])
        j = read('inputs/root/selected-host-budget.json')
        self.assertEqual(len(j['field_order']), 17)
        self.assertEqual(set(j['field_order']), set(j['budget']))
        self.assertEqual(j['budget'], read('inputs/preparation/contract.json')['canonical_budget_maxima'])
        self.assertFalse(j['historical_full_target_replay_selected'])

    def test_04_exact_source_base_and_probe_delta(self):
        custody = read('input-custody.json')
        base = {m['path']: m for m in read('base-source-manifest.json')['members']}
        probe = read('probe-source-manifest.json')
        final = {m['path']: m for m in probe['members']}
        canonical = {m['path']: m for m in custody['canonical']}
        row_delta = {m['path']: m for m in custody['row_additions_and_module_delta']}
        self.assertEqual(len(canonical), 132)
        self.assertEqual(base, canonical | row_delta)
        self.assertEqual(len(base), 134)
        self.assertEqual(set(final) - set(base), {
            'src/experimental_swift_reactor/cache/initial_profile_protocol_layout.rs',
            'src/bin/initial-profile-layout-probe.rs'})
        self.assertEqual({p for p in base if base[p] != final[p]}, {
            'src/experimental_swift_reactor/cache.rs',
            'src/experimental_swift_reactor/mod.rs', 'src/lib.rs'})
        self.assertEqual(tree(probe['members']), probe['tree_sha256'])
        for m in probe['members']:
            p = PACKET / 'source/vm' / m['path']
            self.assertEqual((p.stat().st_size, sha(p)), (m['bytes'], m['sha256']))
        for p in custody['unmerged_archived_instrumentation']:
            if p != 'src/experimental_swift_reactor/cache.rs':
                self.assertEqual(canonical[p], final[p])
        for name in ['mixer_vm.h', 'mixer_vm_capability.h', 'mixer_vm_guest_ui.h']:
            self.assertIn('include/' + name, base)

    def test_05_exact_data_model_in_compiled_probe(self):
        model = (PACKET / 'protocol-types.rs').read_text().replace('__LAYOUT_ENTRY_COUNT__', '165')
        compiled = (PACKET / 'source/vm/src/experimental_swift_reactor/cache/initial_profile_protocol_layout.rs').read_text()
        self.assertEqual(compiled.split('\npub(super) fn emit_layout_v1() {')[0], model)
        self.assertNotIn('fn construct_with_initial_profile_v1', compiled)
        self.assertNotIn('fn selected_initial_profile_v1', compiled)
        self.assertNotIn('fn encode_profile_header_v1', compiled)

    def test_06_every_raw_probe_entry_and_formula(self):
        measured = read('layout-measurements.json')
        for mode in ['debug', 'release']:
            rows, values = [], {}
            for line in (PACKET / f'commands/{mode}-probe/stdout').read_text().splitlines():
                fields = line.split('\t')
                if fields[0] == 'TYPE':
                    self.assertEqual(len(fields), 5)
                    rows.append(dict(id=int(fields[1]), type=fields[2], bytes=int(fields[3]), alignment=int(fields[4])))
                elif fields[0] == 'VALUE':
                    self.assertEqual(len(fields), 3)
                    self.assertNotIn(fields[1], values)
                    values[fields[1]] = int(fields[2])
                else:
                    self.fail('Unselected raw output row')
            self.assertEqual(rows, measured['modes'][mode]['types'])
            self.assertEqual(values, measured['modes'][mode]['derived_layout_values'])
            for command in [f'{mode}-build', f'{mode}-probe']:
                receipt = read(f'commands/{command}/receipt.json')
                self.assertEqual(receipt['exit_code'], 0)
                self.assertLessEqual(receipt['elapsed_seconds'], 60)
                self.assertEqual(sha(PACKET / f'commands/{command}/stdout'), receipt['stdout_sha256'])
                self.assertEqual(sha(PACKET / f'commands/{command}/stderr'), receipt['stderr_sha256'])
        self.assertEqual(measured['modes']['debug']['types'], measured['modes']['release']['types'])
        self.assertEqual(measured['modes']['debug']['derived_layout_values'], measured['modes']['release']['derived_layout_values'])

    def test_07_complete_local_selection_mapping(self):
        proposal = read('local-structure-proposal.json')
        rows = proposal['type_layout']
        self.assertEqual(rows, read('layout-measurements.json')['modes']['debug']['types'])
        self.assertEqual([dict(id=r['id'], type=r['type']) for r in rows], read('local-layout-type-index.json')['types'])
        self.assertEqual([r['id'] for r in rows], list(range(1, 166)))
        self.assertEqual(len({r['type'] for r in rows}), 165)
        for r in rows:
            self.assertGreater(r['alignment'], 0)
            self.assertEqual(r['alignment'] & (r['alignment'] - 1), 0)
            self.assertEqual(r['bytes'] % r['alignment'], 0)
        fixed = proposal['fixed_fields']
        self.assertEqual(fixed, dict(schema=1, entries=165, word_bytes=8, little_endian=1,
            header_bytes=512, row_bytes=32, rows=80000, header_words=16,
            digest_slots=8, digest_bytes=32, trailing_zero_bytes=128,
            outcome_variant_schema=1, header_error_schema=1, selected_slots_max=64, selected_pins=64))
        self.assertFalse(proposal['selected_by_root'])
        self.assertFalse(read('protocol.json')['local_layout_comparison_executed'])

    def test_08_independent_original_formula_arithmetic(self):
        source = (PACKET / 'source/vm/src/experimental_swift_reactor/cache.rs').read_text()
        sizes = {norm(r['type']): r['bytes'] for r in read('local-structure-proposal.json')['type_layout']}
        values = read('local-structure-proposal.json')['derived_fields']
        for suffix in ['cleanup_temporary', 'construction', 'operation']:
            body = source.split(f'const fn compute_cache_{suffix}_bytes() -> Option<usize> {{', 1)[1].split('\n}', 1)[0]
            terms = re.findall(r'\(\s*(\d+),\s*size_of::<(.*?)>\s*\(\s*\)\s*,?\s*\)', body, re.S)
            self.assertEqual(len(terms), body.count('size_of::'))
            total = sum(int(count) * sizes[norm(ty)] for count, ty in terms)
            self.assertEqual(total, values[f'cache_{suffix}_bytes'])
        h = sizes['SwiftFunctionCache'] - sizes['ValidatedSwiftReactor'] + values['cache_cleanup_temporary_bytes'] + 192 + 512 * sizes['Option<ScanPlan>']
        self.assertEqual(h, 92128)
        self.assertEqual(h, values['cache_header_bytes'])
        self.assertEqual(h + 64 * sizes['SwiftSlot'] + 64 * sizes['PinRecord'] + 512 * sizes['decode::Patch'], values['cache_fixed_64_slots_64_pins'])
        self.assertEqual(values, dict(cache_cleanup_temporary_bytes=62888, cache_construction_bytes=61880,
            cache_fixed_64_slots_64_pins=118240, cache_header_bytes=92128, cache_operation_bytes=92350))

    def test_09_named_new_complete_places(self):
        sizes = {r['type']: (r['bytes'], r['alignment']) for r in read('local-structure-proposal.json')['type_layout']}
        expected = {'ProfileHeaderErrorV1': 16, 'InitialProfileScalarsV1': 64,
            'UnverifiedProfileDigestBytesV1': 256, 'InitialProfileConstructionOutcomeV1': 2912,
            "InitialProfileBorrowV1<'static>": 88, 'SelectedInitialProfileV1': 4216,
            'WrapperCallerStorageV1': 12312, "WrapperPhaseStorageV1<'static>": 6912,
            "WrapperEmissionStorageV1<'static>": 4768, 'WrapperMoveStorageV1': 14040}
        for name, byte_count in expected.items():
            self.assertEqual(sizes[name], (byte_count, 8))
        self.assertEqual(sizes['UnverifiedProfileHeaderV1'], (512, 1))
        self.assertEqual(sizes['LocalTypeLayoutV1'], (24, 8))

    def test_10_outcome_inventory_and_ownership(self):
        variants = read('protocol.json')['variants']
        names = ['SlotOccupied', 'SelectionRefused', 'PreparationFailed', 'ConstructionFailed',
            'PhaseCompletionFailed', 'HeaderRefused', 'HeaderOwnerCheckFailed', 'HeaderEncoded']
        fields = [{'adopted': 'AdoptedProof'}, {'error': 'ProfileHeaderErrorV1', 'adopted': 'AdoptedProof'},
            {'failure': 'SwiftRunFailure', 'adopted': 'AdoptedProof'},
            {'failure': 'CacheConstructionFailure', 'completion': 'Result<(),SwiftRunFailure>'},
            {'failure': 'SwiftRunFailure'}, {'error': 'ProfileHeaderErrorV1'}, {'failure': 'SwiftRunFailure'},
            {'header': 'UnverifiedProfileHeaderV1', 'rows': 'Result<ProfileRowsObservationV1,ProfileAdapterErrorV1>'}]
        for tag, (v, name, expected_fields) in enumerate(zip(variants, names, fields), 1):
            self.assertEqual((v['tag'], v['name'], v['fields']), (tag, name, expected_fields))
            if tag >= 5:
                self.assertEqual(v['ownership'], 'cache_out Some')
        self.assertEqual(len(variants), 8)
        self.assertEqual(variants[3]['completion'], 'original-result')
        self.assertEqual(variants[7]['rows'], 'original-result')

    def test_11_complete_finite_budget_roster(self):
        j = read('test-budget-records.json')
        self.assertEqual(len(j['records']), 24)
        selected = read('inputs/root/selected-host-budget.json')['budget']
        self.assertEqual(j['records'][0]['budget'], selected)
        for record in j['records']:
            self.assertEqual(set(record['budget']), set(selected))
            for field, value in record['budget'].items():
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, selected[field])
        drifts = [r for r in j['records'] if r['id'].startswith('drift-')]
        self.assertEqual({r['id'] for r in drifts}, {'drift-' + name for name in selected})
        for r in drifts:
            self.assertEqual([k for k in selected if r['budget'][k] != selected[k]], r['altered_fields'])

    def test_12_exact_future_closure(self):
        j = read('protocol.json')
        prefix = 'src/experimental_swift_reactor/cache/initial_profile_v1'
        new = [prefix + '.rs'] + [prefix + '/' + name + '.rs'
            for name in ['header', 'selected', 'local_structure', 'tests', 'compile_contracts']]
        self.assertEqual(j['next_new_Rust_files'], new)
        base = {m['path'] for m in read('base-source-manifest.json')['members']}
        self.assertFalse(base & set(new))
        self.assertEqual(len(base | set(new)), j['next_distribution_paths'])
        self.assertEqual(j['next_distribution_paths'], 140)
        host = 'verification/swift-initial-profile-construction-host/'
        cases = ['positive_contract', 'guard_literal_from_sibling', 'guard_escape', 'proof_escape',
            'cache_move', 'cache_mutation', 'control_mutation', 'row_foreign_snapshot',
            'callback_reentry', 'external_selection_literal']
        self.assertEqual(j['future_fixed_compile_case_sources'], [host + 'compile_cases/' + n + '.rs' for n in cases])
        self.assertEqual(j['future_host_runner'], host + 'run_component.py')
        self.assertEqual(140 + len(cases) + 1, j['future_distribution_plus_named_host_support_sources'])

    def test_13_header_map_complete_opaque_and_disjoint(self):
        h = read('inputs/preparation/contract.json')['header']
        self.assertEqual([x['offset'] for x in h['words']], list(range(0, 128, 8)))
        self.assertEqual([x['offset'] for x in h['digests']], list(range(128, 384, 32)))
        self.assertTrue(all(x['bytes'] == 32 and x['verified_by_encoding'] is False for x in h['digests']))
        self.assertEqual(h['trailing_zero_offset'] + h['trailing_zero_bytes'], 512)
        self.assertFalse(h['final_selection_digest_included'])
        p = read('inputs/preparation/contract.json')['profile']
        self.assertEqual(p['row_body_bytes'], 80000 * 32)
        self.assertTrue(p['row_writer_requires_empty_zero_offset_file'])
        self.assertTrue(p['composition_requires_distinct_output'])

    def test_14_external_provenance_and_cleanup_only(self):
        environment = read('environment.json')
        self.assertEqual(environment['probe_source_tree_sha256'], read('probe-source-manifest.json')['tree_sha256'])
        self.assertEqual(environment['protocol_model_sha256'], sha(PACKET / 'protocol-types.rs'))
        self.assertIn('rustc 1.99.0', environment['rustc-vV']['stdout'])
        self.assertIn('host: aarch64-apple-darwin', environment['rustc-vV']['stdout'])
        self.assertTrue(environment['target_data_layout'])
        self.assertFalse(environment['native_UI_capture_or_process_inventory'])
        self.assertFalse(Path(environment['owned_scratch']).exists())
        self.assertTrue(environment['cleanup']['owned_scratch_removed'])
        self.assertTrue(environment['cleanup']['owned_children_reaped'])
        self.assertFalse(environment['cleanup']['compiler_products_retained'])

    def test_15_false_authority_and_unexecuted_claims(self):
        j = read('protocol.json')
        for name in ['external_build_attestation_inside_helper', 'local_layout_comparison_executed',
            'new_140_count_schema_or_product_or_runtime_or_GA_accepted', 'product_implementation_selected',
            'runtime_failure_reclassification', 'zero_byte_cache_ticket_exclusivity']:
            self.assertFalse(j[name])
        d = read('decision.json')
        self.assertFalse(d['actual_guard_lifetime_or_wrapper_semantic_or_combined_reservation_proof'])
        self.assertFalse(d['product_implementation'])
        self.assertFalse(d['real_binding_runtime_CI_native_FieldLog_or_GA_accepted'])

    def test_16_negative_data_controls(self):
        members = read('probe-source-manifest.json')['members']
        changed = copy.deepcopy(members)
        changed[0]['sha256'] = '0' * 64
        self.assertNotEqual(tree(changed), tree(members))
        changed = copy.deepcopy(members)
        changed[0]['bytes'] += 1
        self.assertNotEqual(tree(changed), tree(members))
        self.assertNotEqual(tree(members[:-1]), tree(members))
        table = read('local-structure-proposal.json')['type_layout']
        for field in ['id', 'bytes', 'alignment']:
            changed = copy.deepcopy(table)
            changed[0][field] += 1
            self.assertNotEqual(changed, table)
        variants = read('protocol.json')['variants']
        changed = copy.deepcopy(variants)
        del changed[3]['fields']['completion']
        self.assertNotEqual(changed, variants)

if __name__ == '__main__':
    unittest.main(verbosity=2)
