#!/usr/bin/env python3
"""Finite offline custody/schema/layout controls, never product authority."""
from pathlib import Path
import hashlib,json,unittest
OUT=Path(__file__).resolve().parent
def read(name):return json.loads((OUT/name).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def valid_member(root,m):
    p=root/m['path'];return p.is_file() and p.stat().st_size==m['bytes'] and sha(p)==m['sha256']

class PacketControls(unittest.TestCase):
    def test_assigned_seal_counts(self):
        j=read('input-custody.json');self.assertEqual((j['preparation']['members_verified'],j['preparation']['bytes_verified']),(200,23038631))
        self.assertEqual((j['independent']['members_verified'],j['independent']['bytes_verified']),(35,536897))
    def test_root_hash_inputs(self):
        for m in read('input-custody.json')['root_inputs']:self.assertTrue(valid_member(OUT,m))
    def test_fresh_base134(self):
        j=read('base-source-manifest.json');self.assertEqual(j['member_count'],134);self.assertEqual(len({m['path'] for m in j['members']}),134)
        self.assertEqual(len(read('input-custody.json')['canonical']),132)
    def test_probe136_exact_members(self):
        j=read('probe-source-manifest.json');self.assertEqual(j['member_count'],136)
        self.assertEqual(set(m['path'] for m in j['members']),{str(p.relative_to(OUT/'source/vm')) for p in (OUT/'source/vm').rglob('*') if p.is_file()})
        for m in j['members']:self.assertTrue(valid_member(OUT/'source/vm',m))
    def test_manifest_negative(self):
        m=dict(read('probe-source-manifest.json')['members'][0]);m['sha256']='0'*64
        self.assertFalse(valid_member(OUT/'source/vm',m))
    def test_manifest_tree(self):
        j=read('probe-source-manifest.json');b=''.join(f"{m['path']}\t{m['bytes']}\t{m['sha256']}\n" for m in sorted(j['members'],key=lambda m:m['path'])).encode()
        self.assertEqual(hashlib.sha256(b).hexdigest(),j['tree_sha256'])
    def test_C_headers_retained(self):
        names={m['path'] for m in read('probe-source-manifest.json')['members']}
        for n in ['mixer_vm.h','mixer_vm_capability.h','mixer_vm_guest_ui.h']:self.assertIn('include/'+n,names)
    def test_no_archived_instrumentation_merged(self):
        c=read('input-custody.json');base={m['path']:m for m in c['canonical']};final={m['path']:m for m in read('probe-source-manifest.json')['members']}
        self.assertEqual(len(c['unmerged_archived_instrumentation']),4)
        for name in c['unmerged_archived_instrumentation']:
            if name!='src/experimental_swift_reactor/cache.rs':self.assertEqual(base[name],final[name])
        cache=(OUT/'source/vm/src/experimental_swift_reactor/cache.rs').read_bytes()
        self.assertTrue(cache.startswith((OUT.parents[1]/'verification/swift-profile-header-preparation/inputs/vm/src/experimental_swift_reactor/cache.rs').read_bytes()))
    def test_complete17_budget_records(self):
        j=read('test-budget-records.json');self.assertEqual(len(j['field_order']),17)
        for r in j['records']:self.assertEqual(set(r['budget']),set(j['field_order']))
        selected=read('inputs/root/selected-host-budget.json')['budget'];self.assertEqual(j['records'][0]['budget'],selected)
    def test_all17_drift_records(self):
        j=read('test-budget-records.json');s=j['records'][0]['budget'];drifts=[r for r in j['records'] if r['id'].startswith('drift-')]
        self.assertEqual(len(drifts),17)
        for r in drifts:self.assertEqual([k for k in s if s[k]!=r['budget'][k]],r['altered_fields'])
    def test_boundary_budgets_no_widening(self):
        j=read('test-budget-records.json');s=j['records'][0]['budget']
        for r in j['records']:
            for k,n in r['budget'].items():self.assertGreaterEqual(n,0);self.assertLessEqual(n,s[k])
        above=next(r for r in j['records'] if r['id']=='test-selected-entry-above-capacity')['budget'];self.assertGreater(above['cache_entry_bytes'],above['cache_bytes'])
    def test_exact_outcome_inventory(self):
        j=read('protocol.json');self.assertEqual([v['tag'] for v in j['variants']],list(range(1,9)))
        self.assertEqual(j['variants'][0]['fields'],{'adopted':'AdoptedProof'})
        self.assertEqual(j['variants'][3]['fields'],{'failure':'CacheConstructionFailure','completion':'Result<(),SwiftRunFailure>'})
        self.assertFalse(j['runtime_failure_reclassification'])
    def test_layout_both_modes_and_index(self):
        j=read('layout-measurements.json');self.assertTrue(j['all_selected_builds_and_layout_probes_passed'])
        d=j['modes']['debug'];r=j['modes']['release'];self.assertEqual(d['types'],r['types']);self.assertEqual(d['derived_layout_values'],r['derived_layout_values'])
        self.assertEqual(len(d['types']),165);self.assertEqual([{'id':x['id'],'type':x['type']} for x in d['types']],read('local-layout-type-index.json')['types'])
        for x in d['types']:self.assertGreater(x['alignment'],0);self.assertEqual(x['alignment'] & (x['alignment']-1),0)
    def test_actual_formula_values(self):
        j=read('layout-measurements.json')['modes']['debug'];v=j['derived_layout_values'];s={x['type']:x['bytes'] for x in j['types']}
        self.assertEqual(v['cache_header_bytes'],s['SwiftFunctionCache']-s['ValidatedSwiftReactor']+v['cache_cleanup_temporary_bytes']+192+512*s['Option<ScanPlan>'])
        self.assertEqual(v['cache_fixed_64_slots_64_pins'],v['cache_header_bytes']+64*s['SwiftSlot']+64*s['PinRecord']+512*s['decode::Patch'])
        self.assertLessEqual(v['cache_fixed_64_slots_64_pins'],read('inputs/root/selected-host-budget.json')['budget']['cache_bytes'])
    def test_proposal_not_self_comparison_or_attestation(self):
        j=read('local-structure-proposal.json');p=read('protocol.json');self.assertFalse(j['selected_by_root']);self.assertFalse(p['local_layout_comparison_executed']);self.assertFalse(p['external_build_attestation_inside_helper'])
        self.assertEqual(j['type_layout'],read('layout-measurements.json')['modes']['debug']['types'])
        self.assertEqual(j['fixed_fields']['entries'],165)
    def test_tool_and_source_binding(self):
        e=read('environment.json');self.assertEqual(e['probe_source_tree_sha256'],read('probe-source-manifest.json')['tree_sha256'])
        self.assertEqual(e['rustc-vV']['exit_code'],0);self.assertIn('rustc 1.99.0',e['rustc-vV']['stdout']);self.assertIn('aarch64-apple-darwin',e['rustc-vV']['stdout'])
        self.assertTrue(e['target_data_layout']);self.assertEqual(sha(OUT/'protocol-types.rs'),e['protocol_model_sha256'])
    def test_owned_cleanup(self):
        e=read('environment.json');self.assertTrue(e['cleanup']['owned_scratch_removed']);self.assertFalse(Path(e['owned_scratch']).exists());self.assertTrue(e['cleanup']['owned_children_reaped']);self.assertFalse(e['cleanup']['compiler_products_retained'])
    def test_next_closure_and_scope(self):
        j=read('protocol.json');self.assertEqual(len(j['next_new_Rust_files']),6);self.assertEqual(134+len(j['next_new_Rust_files']),j['next_distribution_paths'])
        self.assertFalse(j['product_implementation_selected']);self.assertFalse(j['new_140_count_schema_or_product_or_runtime_or_GA_accepted']);self.assertFalse(j['zero_byte_cache_ticket_exclusivity'])

if __name__=='__main__':unittest.main(verbosity=2)
