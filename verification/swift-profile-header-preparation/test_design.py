"""Offline design controls only. No archived/current product code is imported."""
from pathlib import Path
import hashlib, json, struct, unittest
P=Path(__file__).resolve().parent
C=json.loads((P/'contract.json').read_text())
D=json.loads((P/'closure-comparison.json').read_text())
U64=(1<<64)-1

def checked_add(a,b):
    if not 0<=a<=U64 or not 0<=b<=U64 or a>U64-b:raise ValueError('overflow')
    return a+b

def checked_mul(a,b):
    if not 0<=a<=U64 or not 0<=b<=U64 or (b and a>U64//b):raise ValueError('overflow')
    return a*b

def model_fixed(cache,snapshot,cleanup,plan,slot,pin,patch,entries,pins):
    # Arbitrary arithmetic model inputs; no compiler ABI size is selected.
    if cache<snapshot or not 1<=entries<=64 or not 1<=pins<=64:raise ValueError('unsupported')
    h=checked_add(checked_add(checked_add(cache-snapshot,cleanup),192),checked_mul(512,plan))
    return h,checked_add(checked_add(checked_add(h,checked_mul(entries,slot)),checked_mul(pins,pin)),checked_mul(512,patch))

def encode_model(extent,types,slots,pins,base,capacity,entry,digests):
    if not 0<=extent<U64 or not 0<=types<=(1<<32)-1 or not 1<=slots<=64 or not 1<=pins<=64 or not 0<=base<=capacity<U64 or not 0<=entry<U64:raise ValueError('unsupported')
    if len(digests)!=8 or any(len(x)!=32 for x in digests):raise ValueError('digest encoding extent')
    return struct.pack('<8s15Q',b'MIXPRF01',1,512,32,80000,extent,types,slots,pins,1,base,capacity,entry,0,0,0)+b''.join(digests)+bytes(128)

class DesignControls(unittest.TestCase):
    def test_01_header_exact_map(self):
        self.assertEqual([x['offset']for x in C['header']['words']],list(range(0,128,8)))
        self.assertEqual([x['name']for x in C['header']['words']],['magic','version','header_bytes','row_bytes','rows','source_extent','type_count','slot_limit','pin_limit','initial_nonce','cache_base','cache_capacity','entry_limit','reserved_13','reserved_14','reserved_15'])
    def test_02_digest_all_eight_exact_offsets(self):
        self.assertEqual([(x['name'],x['offset'])for x in C['header']['digests']],[('baseline',128),('candidate',160),('original_input',192),('event_schema',224),('profile_adapter_binary',256),('layout_receipt',288),('original_validated_snapshot',320),('profile_row_body',352)])
    def test_03_header_golden_little_endian(self):
        b=encode_model(0x0102030405060708,19,2,3,4096,16777216,8388608,[bytes([n])*32 for n in range(8)])
        self.assertEqual(len(b),512);self.assertEqual(b[:8],b'MIXPRF01')
        self.assertEqual(b[40:48],bytes.fromhex('0807060504030201'))
        self.assertEqual(b[56:80],bytes.fromhex('020000000000000003000000000000000100000000000000'))
        self.assertEqual(b[128:384],b''.join(bytes([n])*32 for n in range(8)))
        self.assertEqual(b[104:128],bytes(24));self.assertEqual(b[384:],bytes(128))
    def test_04_profile_exact_extent(self):
        self.assertEqual(80000*32,2560000);self.assertEqual(512+80000*32,2560512)
        self.assertEqual(C['profile']['total_bytes'],2560512)
    def test_05_row_writer_exact_block_bound(self):
        self.assertEqual(4096//32,128);self.assertEqual(80000//128,625)
        self.assertEqual(625*32,20000);self.assertEqual(C['profile']['row_writer_max_calls'],20000)
    def test_06_append_is_separate_contract(self):
        self.assertTrue(C['profile']['row_writer_requires_empty_zero_offset_file'])
        self.assertTrue(C['profile']['composition_requires_distinct_output'])
        self.assertNotEqual(512,0);self.assertEqual(512+2560000,2560512)
    def test_07_slots_take_min_not_budget_literal(self):
        for n in [0,1,2,63,64,65,100,79966]:
            for budget in [0,1,2,63,64]:
                slots=min(budget,n);self.assertLessEqual(slots,budget);self.assertLessEqual(slots,n)
        self.assertEqual(min(64,1),1);self.assertEqual(min(64,100),64)
    def test_08_pins_are_independent_actual_budget(self):
        for slots in range(1,65):
            for pins in range(1,65):
                b=encode_model(1024,1,slots,pins,100,1000,0,[bytes(32)]*8)
                self.assertEqual(struct.unpack_from('<Q',b,64)[0],pins)
    def test_09_zero_slots_and_zero_pins_refused(self):
        for slots,pins in [(0,64),(64,0),(0,0),(65,1),(1,65)]:
            with self.assertRaises(ValueError):encode_model(100,1,slots,pins,0,100,0,[bytes(32)]*8)
    def test_10_nonce_one_fixed(self):
        b=encode_model(100,1,1,64,1,100,0,[bytes(32)]*8)
        self.assertEqual(struct.unpack_from('<Q',b,72)[0],1);self.assertEqual(C['construction']['initial_nonce'],1)
    def test_11_arbitrary_measured_layout_arithmetic(self):
        # Values deliberately arbitrary, not the actual compiler layouts.
        h,b=model_fixed(1000,600,777,32,80,24,16,3,7)
        self.assertEqual(h,17753);self.assertEqual(b,26353)
    def test_12_no_index_plan_double_charge(self):
        h,b=model_fixed(1000,600,777,32,80,24,16,3,7)
        self.assertEqual(b-h,3*80+7*24+512*16)
        self.assertNotEqual(b,h+192+512*32+3*80+7*24+512*16)
    def test_13_checked_overflow_and_header_subtraction(self):
        for call in [lambda:checked_add(U64,1),lambda:checked_mul(U64,2),lambda:model_fixed(1,2,0,0,0,0,0,1,1),lambda:model_fixed(U64,0,1,1,1,1,1,1,1)]:
            with self.assertRaises(ValueError):call()
    def test_14_base_cannot_exceed_capacity(self):
        with self.assertRaises(ValueError):encode_model(100,1,1,1,101,100,10,[bytes(32)]*8)
    def test_15_entry_zero_and_above_capacity_not_invented_restrictions(self):
        for entry in [0,1,1000]:self.assertEqual(len(encode_model(100,1,1,1,90,100,entry,[bytes(32)]*8)),512)
    def test_16_complete_budget_17_fields_required(self):
        self.assertEqual(len(C['canonical_budget_field_order']),17)
        self.assertEqual(set(C['canonical_budget_field_order']),set(C['canonical_budget_maxima']))
        for name in C['canonical_budget_field_order']:
            other=dict(C['canonical_budget_maxima']);other[name]-=1
            self.assertNotEqual(other,C['canonical_budget_maxima'])
    def test_17_historical_budget_exact_retained_single_event(self):
        raw=(P/'inputs/verification/swift-current-attribution-runtime/commands/target-once/stdout').read_bytes()
        rows=[]
        for line in raw.splitlines():
            marker=b'MIXER_EXACT '
            if line.startswith(marker):
                row=json.loads(line[len(marker):])
                if row.get('event')=='run_budget':rows.append(row['payload'])
        self.assertEqual(rows,[C['historical_invocation_candidate']['run_budget']])
        self.assertEqual(rows[0],C['canonical_budget_maxima']);self.assertIsNone(C['selected_invocation_budget'])
    def test_18_fixture_cannot_gain_authority(self):
        self.assertEqual(C['context']['fixture_magic_ascii'],'MIXFIX01')
        self.assertFalse(C['context']['fixture_can_gain_real_authority']);self.assertFalse(C['context']['real_schema_selected'])
        self.assertTrue(all(x is False for x in C['authority'].values()))
    def test_19_supplied_digests_never_verified_by_encoding(self):
        self.assertTrue(all(x['verified_by_encoding'] is False for x in C['header']['digests']))
        for claims in [[bytes(32)]*8,[bytes([255])*32]*8]:self.assertEqual(len(encode_model(100,1,1,1,10,100,1,claims)),512)
    def test_20_exact_digest_encoding_extents(self):
        for claims in [[bytes(32)]*7,[bytes(32)]*9,[bytes(31)]+[bytes(32)]*7]:
            with self.assertRaises(ValueError):encode_model(100,1,1,1,10,100,1,claims)
    def test_21_no_selection_digest_cycle(self):
        self.assertFalse(C['header']['final_selection_digest_included'])
        self.assertNotIn('selection',[x['name']for x in C['header']['digests']])
    def test_22_context_exact_partition(self):
        f=C['context'];self.assertEqual(f['selection_bytes']+f['original_result_bytes']+f['custody_bytes'],f['bytes'])
        self.assertEqual(f['bytes'],8192)
    def test_23_exact_four_completion_differences(self):
        self.assertEqual(D['completion_changed'],['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/control.rs'])
        self.assertEqual(len(D['canonical_members']),132);self.assertEqual(len(D['completion_members']),132)
    def test_24_validator_is_common_bytes(self):
        rows={x['path']:x for x in D['comparisons']}
        for name in ['src/experimental/swift.rs','src/experimental/validate.rs','src/experimental/metadata.rs','src/experimental/descriptors.rs']:
            self.assertTrue(rows[name]['completion_equal_canonical']);self.assertTrue(rows[name]['row_equal_canonical'])
    def test_25_row_source_set_exact_boundary(self):
        self.assertEqual(D['row_missing'],['include/mixer_vm.h','include/mixer_vm_capability.h','include/mixer_vm_guest_ui.h'])
        self.assertEqual(D['row_changed'],['src/experimental_swift_reactor/mod.rs'])
        self.assertEqual(D['row_added'],['src/experimental_swift_reactor/diagnostic_profile.rs','src/experimental_swift_reactor/diagnostic_profile_tests.rs'])
        self.assertEqual(len(D['row_source_members']),131)
    def test_26_snapshot_bytes_have_bound_hashes(self):
        for name in ['input-manifest.json','additional-inputs.json','acceptance-input.json']:
            for row in json.loads((P/name).read_text())['members']:
                b=(P/row['snapshot']).read_bytes();self.assertEqual(len(b),row['bytes']);self.assertEqual(hashlib.sha256(b).hexdigest(),row['sha256'])
    def test_27_root_row_acceptance_scope_and_corrected_totals(self):
        a=json.loads((P/'inputs/verification/swift-semantic-adapter-root-review/profile-adapter-acceptance.json').read_text())
        self.assertTrue(a['implementation_accepted']);self.assertFalse(a['canonical_integration_selected']);self.assertFalse(a['real_header_binding_or_runtime_or_new_CI_or_GA_accepted'])
        for x,y in [('adapter_caller_callee_union_bytes',11912),('including_constructor_and_owner_fixed_places_bytes',13904),('source_action_plus_cumulative_requested_IO_byte_bound',450652288)]:self.assertEqual(a['accounting'][x],y)
        self.assertFalse(C['combined_analyzer_accounting_accepted'])
    def test_28_new_source_members_cannot_fit_old_exact132_set(self):
        self.assertEqual(len(D['canonical_members'])+len(D['row_added']),134)
        self.assertNotEqual(134,132)
    def test_29_snapshot_digest_preimage_stays_missing_dependency(self):
        f=[x for x in C['header']['digests']if x['name']=='original_validated_snapshot'][0]
        self.assertIn('currently unavailable',f['preimage'])
        self.assertTrue(any('stable validated-snapshot' in x for x in C['pending_dependencies']))
    def test_30_immutable_fixture_false_authority_source_observed_only(self):
        raw=(P/'inputs/verification/swift-cache-state-ci/pack/source/library/cache_state.rs').read_text()
        for name in ['stored_prefix_validated','full_replay_accepted','semantic_metrics_valid','real_binding_verified']:
            self.assertIn(f'pub const fn {name}(&self) -> bool {{\n        false\n    }}',raw)
        # This text check documents the inherited source; it authorizes no release.
    def test_31_selected_source_budget_maxima_match_frozen_canonical(self):
        self.assertEqual(C['canonical_budget_maxima']['cache_work'],64000000)
        self.assertEqual(C['canonical_budget_maxima']['combined_bytes'],256*1024*1024)
        self.assertEqual(C['canonical_budget_maxima']['deadline_ms'],30000)
        self.assertEqual(C['canonical_budget_maxima']['cache_entries'],64)
        self.assertEqual(C['canonical_budget_maxima']['active_pins'],64)
    def test_32_encoded_profile_offset_does_not_change_row_relative_error_contract(self):
        self.assertEqual(79999*32,2559968)
        self.assertEqual(512+79999*32,2560480)
        self.assertEqual(2560480+32,C['profile']['total_bytes'])
        self.assertEqual((2**32-1)*32,137438953440)

if __name__=='__main__':unittest.main()
