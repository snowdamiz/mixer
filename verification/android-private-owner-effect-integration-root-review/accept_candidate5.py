"""Accept exact C5 private development evidence; native and GA gates stay open."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name('candidate-5-owner-acceptance.json')
REVIEW = ROOT / 'verification/android-private-owner-independent-review/implementation-review-4'
assert not OUT.exists(), 'one-shot acceptance already recorded'

def bind(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

manifest_path = REVIEW / 'manifest.json'
assert bind(manifest_path)['sha256'] == '8836f488f6f6c0c56b0c27a91968d29ce187cd1b6f5a66bcc9b3727ee07a527a'
manifest = json.loads(manifest_path.read_bytes())
assert manifest['members'] == len(manifest['files']) == 8550
assert manifest['bytes'] == sum(row['bytes'] for row in manifest['files'].values()) == 169660880
for name, row in manifest['files'].items():
    path = ROOT / name
    assert not path.is_symlink() and '..' not in Path(name).parts
    assert bind(path) == row, name
source_map = ROOT / 'verification/android-private-owner-integration-implementation/candidate-5/source-map.json'
assert bind(source_map)['sha256'] == 'da250cd1e7560f8d702753769a132b70f60ea05477d133c32afd0c7372c542a1'
sources = json.loads(source_map.read_bytes())
assert len(sources) == 311
for name, row in sources.items():
    assert bind(ROOT / name) == row, name

final = REVIEW / 'final-evidence'
summary = json.loads((final / 'summary.json').read_bytes())
matrix = json.loads((final / 'matrix-credit.json').read_bytes())
assert matrix['qualified_unique_rows'] == len(matrix['qualified']) == 1323
assert len({(r['id'], r['variant']) for r in matrix['qualified']}) == 1323
assert len({r['id'] for r in matrix['qualified']}) == 189
assert matrix['direct_leaf_or_opaque_rows'] + matrix['direct_JDI_rows'] == 1295 + 28 == 1323
assert matrix['remaining_direct_rows'] == 0
assert not json.loads((final / 'tail-disposition.json').read_bytes())['unresolved']
remaining = json.loads((final / 'remaining-host-obligations.json').read_bytes())
raw_case_keys = set()
raw_assertions = 0
for family in remaining['families']:
    command = json.loads((REVIEW / family['command']).read_bytes())
    assert command['exit_code'] == 0 and command['forced_termination'] is None
    rows = [json.loads(line) for line in (REVIEW / family['evidence']).read_text().splitlines() if line.strip()]
    cases = [row for row in rows if 'passed' in row]
    summaries = [row for row in rows if 'cases' in row]
    assert len(summaries) == 1 and len(cases) == family['cases'] == summaries[0]['cases']
    assert summaries[0]['assertions'] == family['assertions']
    raw_assertions += family['assertions']
    for row in cases:
        assert row['passed'] is True
        key = (row['family'], row['name'], row['variant'])
        assert key not in raw_case_keys
        raw_case_keys.add(key)
assert len(raw_case_keys) == remaining['cases'] == summary['remaining_host_cases'] == 514
assert raw_assertions == remaining['assertions'] == summary['remaining_host_assertions'] == 30204
assert raw_case_keys == {(r['family'], r['name'], r['variant']) for r in remaining['exact_case_keys']}
jdi = json.loads((REVIEW / 'jdi-helper/verification.json').read_bytes())
assert len(jdi['rows']) == 28
for row in jdi['rows']:
    assert row['entry_return_continuation_distinct'] is True
    assert row['original_mutation_id'] > 0 and row['original_core_token_id'] > 0
    if 'throw' in row['variant']:
        assert row['exception_identity_verified'] is True
custody = json.loads((final / 'commands-and-custody.json').read_bytes())
assert len(custody['commands']) == custody['commands_count'] == 461
assert not custody['source_bytes_missing']
assert custody['all_owned_scratch_removed'] is True
assert len(custody['preserved_failed_commands']) == 16
assert len(custody['cleanup_receipts']) == 42
historical = json.loads((final / 'historical-migration.json').read_bytes())
assert historical['historical_group_count'] == 35 and historical['historical_check_call_sites'] == 153
assert historical['sum447_is_unique_outcomes'] is False
assert len(historical['source_only_native_pending_vector_ids']) == 2
assert summary['concrete_product_defects_observed_in_C5'] == 0
assert summary['all30_preaccess_families_reconciled'] is True
assert summary['native_or_publicV2_or_GA_accepted'] is False
cli_path = OUT.with_name('candidate-5-CLI-acceptance.json')
assert bind(cli_path)['sha256'] == '3dcaf8fdd82990b96254ceee3f0463762a12832a8b8a4f77401d23231f47dc19'
assert json.loads(cli_path.read_bytes())['CLI_scope_accepted'] is True
assert bind(ROOT / '.github/workflows/verify.yml')['sha256'] == 'd38e911270bc2660de414d7d62dd53bad54948ce2577af899dfb9b4ad9d96d41'

receipt = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'command': sys.argv,
    'python': sys.version, 'script': bind(Path(__file__)),
    'context_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'status': 'Exact candidate5 private owner accepted for bounded development host/source scope; coherent canonical delivery selected',
    'review_manifest': manifest_path.relative_to(ROOT).as_posix(),
    'review_manifest_sha256': bind(manifest_path)['sha256'],
    'review_members': 8550, 'review_bytes': 169660880, 'current_source_bindings': 311,
    'source_map_sha256': bind(source_map)['sha256'],
    'selected_owner_sha256': summary['selected_owner_sha256'],
    'core_unchanged_sha256': summary['core_unchanged_sha256'],
    'independent_summary': summary,
    'root_raw_output_check': {'families': 9, 'unique_cases': 514, 'measured_assertions': 30204,
                             'matrix_unique_rows': 1323, 'matrix_sites': 189, 'JDI_rows': 28},
    'history_units': '35 groups/153 check sites;133 coordinator scenarios/162 Observer sequences/22 core groups are provenance, not447 unique passes',
    'source_only_native_pending_vectors': historical['source_only_native_pending_vector_ids'],
    'scope': 'Private owner, actual product subjects under controlled JVM Android/JNI leaves, source-profile CLI and cross-compilation evidence. Host evidence accepts this development slice; native/OS/JNI behavior and complete product qualification remain pending.',
    'limitations': summary['native_source_only_pending'],
    'CLI_acceptance': {'path': cli_path.relative_to(ROOT).as_posix(), **bind(cli_path)},
    'CI_wiring': 'Separately reviewed new JVM job; remote Ubuntu/JDK17 execution pending after delivery',
    'implementation_accepted': True, 'private_development_scope_accepted': True,
    'canonical_delivery_authorized': True, 'public_V2_selected': False,
    'native_runtime_or_capture_started': False, 'GA_qualified': False,
}
OUT.write_text(json.dumps(receipt, indent=2) + '\n')
node = {'path': OUT.relative_to(ROOT).as_posix(), **bind(OUT),
        'review_manifest_sha256': bind(manifest_path)['sha256'],
        'review_members': 8550, 'review_bytes': 169660880,
        'direct_matrix_rows': 1323, 'independent_continuation_cases': 514,
        'independent_continuation_assertions': 30204,
        'source_only_native_pending_vectors': historical['source_only_native_pending_vector_ids'],
        'scope': receipt['scope'], 'canonical_delivery_authorized': True,
        'native_runtime_or_capture_started': False, 'GA_qualified': False}
for name, top in (('work-graph.json', 'packages'), ('gates/ga.json', 'gates')):
    path = ROOT / name
    data = json.loads(path.read_bytes())
    target = next(row['privateOwnerEffectContractCandidate'] for row in data[top] if 'privateOwnerEffectContractCandidate' in row)
    target['implementation_status'] = 'Candidate5 exact private development host/source scope accepted; canonical delivery and remote JVM CI pending'
    target['implementation_accepted'] = True
    target['product_tests_accepted'] = True
    target['implementation_acceptance_scope'] = receipt['scope']
    target['frozen_candidate5'].update({'status': target['implementation_status'],
                                      'implementation_accepted': True,
                                      'canonical_delivery_authorized': True,
                                      'independent_owner_acceptance': node})
    path.write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'receipt': OUT.relative_to(ROOT).as_posix(), **bind(OUT),
                  'verified_review_members': 8550, 'raw_unique_continuation_cases': 514,
                  'canonical_delivery_authorized': True, 'GA_qualified': False}))
