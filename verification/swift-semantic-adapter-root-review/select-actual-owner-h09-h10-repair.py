"""Select the specific proof/error lifetime oracles identified during preaccess."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'guarded-snapshot-actual-owner-Rust-H09-H10-amendment.json'
assert not OUT.exists()

def row(p):
    raw = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

preaccess = ROOT / 'verification/swift-guarded-snapshot-actual-owner-rust-preaccess'
assert row(preaccess / 'seal.json')['sha256'] == '050d4920ee51014748d0c62aec832c13a65bef09673fff41bbc62310635e4a66'
seal = json.loads((preaccess / 'seal.json').read_bytes())
members = seal['members']
assert len(members) == 51 and sum(x['bytes'] for x in members) == 918074
names = set()
for member in members:
    relative = Path(member['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    assert member['path'] not in names
    names.add(member['path'])
    p = preaccess / relative
    assert not p.is_symlink()
    actual = row(p)
    assert actual['bytes'] == member['bytes'] and actual['sha256'] == member['sha256']
assert {str(p.relative_to(preaccess)) for p in preaccess.rglob('*') if p.is_file()} == names | {'seal.json'}

value = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'selected-targeted-H09-H10-test-corrections-and-final-source-compiler-evidence',
    'script': row(Path(__file__).resolve()), 'python': sys.version,
    'source_commit': 'd6af73813244c330a979afb83b45f53490ff5b29',
    'original_selection': row(HERE / 'guarded-snapshot-actual-owner-Rust-implementation-selection.json'),
    'prior_contract_amendment': row(HERE / 'guarded-snapshot-actual-owner-Rust-contract-amendment.json'),
    'frozen_preaccess_seal': row(preaccess / 'seal.json'),
    'frozen_preaccess_members_checked': 51, 'frozen_preaccess_bytes_checked': 918074,
    'observed_basis': 'Producer explicitly reports both evidence gaps after preaccess identified them. Existing 15-method Debug and optimized passes are producer-reported and do not resolve these gaps; all prior results stay retained.',
    'required_corrections': {
        'H09': 'Sentinel returns an owned result retaining the actual validator-created CorrelatedSelectedProfile, four test guards and usage. Inspect proof/source pointer and owner survival before explicit result retirement; a counter after temporary destruction is insufficient.',
        'H10': 'Embed a unique Send+Sync boxed error marker, verify original downcast heap identity and delayed destruction after refusal inspection. A moved stack address or raw OS code alone is insufficient.',
    },
    'additional_selected_commands': {'final_source_production_metadata_and_full_MIR': 1,
        'corrected_test_builds': ['Debug', 'opt-level2'], 'corrected_filtered_host_runs': 2},
    'cumulative_limits': {'compiler_invocations_max': 16, 'planned_invocations': 11,
        'targeted_repair_and_final_source_invocations_max': 5, 'filtered_host_runs_max': 5,
        'negative_compiler_probes': 8, 'layout_queries': 0, 'simultaneous_compilers': 1,
        'each_command_seconds_max': 55, 'stdout_stderr_each_bytes_max': 4194304},
    'further_retry_budget_implied': False,
    'preserve_all_old_source_preimages_failures_and_passes': True,
    'active_producer_source_read_by_root': False,
    'actual_implementation_test_acceptance_native_acquisition_root_funding_or_GA': False,
}
with OUT.open('x') as stream:
    json.dump(value, stream, indent=2)
    stream.write('\n')

w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
s = b['actual_owner_Rust_selection']
s.update({'targeted_H09_H10_amendment': row(OUT), 'current_command_limits': value['cumulative_limits'],
    'preaccess': {'status': 'frozen-source-and-oracle-preparation-complete', 'seal': row(preaccess / 'seal.json'),
        'members': 51, 'bytes': 918074, 'implementation_acceptance': False},
    'independent_review_ownership': 'verification/swift-guarded-snapshot-actual-owner-rust-independent',
    'independent_review_status': 'preparing-from-frozen-contracts-producer-access-not-released'})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'amendment': row(OUT), 'preaccess_members_checked': 51, 'compiler_ceiling': 16, 'host_run_ceiling': 5}))
