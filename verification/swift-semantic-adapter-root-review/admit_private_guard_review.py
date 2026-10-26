"""Select seven separately seeded private guard witnesses, not public reachability."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PROPOSAL = ROOT / 'verification/swift-cache-state-independent-review/implementation-review-1/private-guard-proposal'
PRODUCER = ROOT / 'verification/swift-cache-state-implementation/source/library'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

seal = PROPOSAL / 'proposal-seal.json'
assert sha(seal) == 'b16b233b1144f05d13852101a2119c70f4a49f1df9334cae75aa309775edc1c5'
data = json.loads(seal.read_bytes())
assert data['member_count'] == 5 and data['member_bytes'] == 29471
assert len({m['path'] for m in data['members']}) == 5
for m in data['members']:
    p = ROOT / m['path']
    assert p.parent == PROPOSAL and not p.is_symlink()
    assert p.stat().st_size == m['bytes'] and sha(p) == m['sha256']
sidecar = PROPOSAL / 'proposal-seal.sha256'
assert sidecar.read_text().strip() == sha(seal) + '  proposal-seal.json'
assert {p.relative_to(ROOT).as_posix() for p in PROPOSAL.iterdir()} == {m['path'] for m in data['members']} | {seal.relative_to(ROOT).as_posix(), sidecar.relative_to(ROOT).as_posix()}
public_path = OUT / 'candidate-public-review-admission.json'
assert sha(public_path) == 'c238edff3f5ef05a770640a0f67b2d748e6e95108dfe00d93e7d890e42333df0'
public = json.loads(public_path.read_bytes())
assert sha(ROOT / public['candidate_seal']) == public['candidate_seal_sha256']
delta = json.loads((PROPOSAL / 'delta.json').read_bytes())
assert set(delta['baseline_sha256']) == set(delta['append_only_utf8']) == {'analyzer.rs', 'envelope.rs', 'cache_state.rs'}
transformed = {}
for name, digest in delta['baseline_sha256'].items():
    assert sha(PRODUCER / name) == digest
    raw = (PRODUCER / name).read_bytes() + delta['append_only_utf8'][name].encode()
    transformed[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
assert sha(PROPOSAL / delta['additional_file']) == delta['additional_file_sha256']
expected = json.loads((PROPOSAL / 'expected-cases.json').read_bytes())
assert sha(ROOT / expected['full32_fixture_path']) == expected['full32_fixture_sha256']
assert sha(ROOT / expected['machine_table_path']) == expected['machine_table_sha256'] == sha(PROPOSAL / 'accepted-terminal-contract.json')
original = {row['id']: row for row in json.loads((ROOT / expected['full32_fixture_path']).read_bytes())}
assert len(expected['cases']) == 7
for case in expected['cases']:
    assert case['expected_words'] == original[case['sealed_expected_origin']]['expected_words']
    assert len(case['q']) == 16 and len(case['expected_words']) == 32
    assert (case['SS'], case['SF'], case['NC'], case['N'], case['calls'], case['latch']) == (1, 1, 4, 4, 4, 0)
receipt = {
    'schema': 1, 'status': 'admitted-seven-private-seeded-finalizer-guard-witnesses',
    'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': sys.argv,
    'python': sys.version, 'script_sha256': sha(Path(__file__)),
    'public_admission_sha256': sha(public_path),
    'candidate_seal': public['candidate_seal'], 'candidate_seal_sha256': public['candidate_seal_sha256'],
    'proposal_seal': seal.relative_to(ROOT).as_posix(), 'proposal_seal_sha256': sha(seal),
    'verified_members': 5, 'verified_bytes': 29471, 'cases': [c['id'] for c in expected['cases']],
    'seal_hash_sidecar_sha256': sha(sidecar),
    'prior_root_preflight': 'Initial root directory-closure assertion refused the unlisted proposal-seal.sha256 sidecar before any admission or compilation. Exact sidecar now verified as the seal digest plus its filename; source and proposal bytes unchanged.',
    'expected_from_immutable_full32': True, 'transformed_source_hashes': transformed,
    'glue_source_sha256': delta['additional_file_sha256'],
    'rustc': public['rustc'], 'rustc_sha256': public['rustc_sha256'], 'rustc_version': public['rustc_version'],
    'edition': '2021', 'compiler_modes': ['default', 'optimized'],
    'output_directory': 'verification/swift-cache-state-independent-review/implementation-review-1/private-guard-run-1',
    'allowed_operations': 'Copy exactly three source members into owned scratch, append exact admitted delta, copy reviewer_private.rs, compile default bin and optimized bin without cfg(test), execute only seven cases, retain exact source/tools/commands/stdout/stderr/expected comparisons and cleanup.',
    'per_command_wall_seconds': 60, 'output_bytes_per_stream': 2097152,
    'source_product_mutation_authorized': False, 'producer_harness_or_models_execution_authorized': False,
    'other_private_or_bulk_cases_admitted': False,
    'scope': 'Deliberately seeded private Progress/child/config projection and actual shape_q guards only. Does not establish from-empty public reachability, arena rows, work/memory accounting, native or release qualification.',
    'cleanup': 'Hash returned owned binaries and remove only this run owned scratch after all children are joined; preserve overlay source and raw results.',
    'implementation_accepted': False, 'native_runtime_or_capture_started': False, 'GA_qualified': False,
}
path = OUT / 'private-guard-review-admission.json'
assert not path.exists()
path.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'cases': 7}))
