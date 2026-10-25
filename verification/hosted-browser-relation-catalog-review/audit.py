"""Independent frozen-source, representation lineage and coverage audit."""
import base64
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
checks = []
inputs = {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    inputs[str(path)] = sha(ROOT / path)
    return json.loads((ROOT / path).read_text())


def demand(name, condition):
    assert condition, name
    checks.append(name)


producer_path = 'verification/hosted-browser-relation-catalog/receipt.json'
producer = read(producer_path)
demand('parent-supplied final producer seal', inputs[producer_path] == '3ecd63d6349f454a9029f0655c8a3b99af55df8c00cb24355698fcc2976e7a2d')
for path, digest in producer['artifact_sha256'].items():
    demand('producer artifact ' + path, sha(ROOT / path) == digest)
    inputs[path] = digest

manifests = {major: read(f'hosted/priv/browser_auth/relation_surface_v1_pg{major}.json') for major in [16, 17]}
matrix_path = 'verification/hosted-browser-relation-admission-contract/relation-matrix.json'
matrix = read(matrix_path)
accept_path = 'verification/hosted-browser-relation-representation-review/root-acceptance.json'
accepted = read(accept_path)
demand('accepted source representation boundary', accepted['status'] == 'accepted-local-PG16-PG17-representation-only')
capture = 'verification/hosted-browser-relation-representation-review/ordinary-source-capture.stdout'
inputs[capture] = sha(ROOT / capture)
functions = {parts[1]: base64.b64decode(parts[2]).decode() for line in (ROOT / capture).read_text().splitlines() if (parts := line.split('\t'))[0] == 'function_source'}

for major, manifest in manifests.items():
    demand(f'{major}: exact handwritten structure', manifest['structure'] == matrix)
    demand(f'{major}: exact independently compiled function bytes', manifest['trigger_sources'] == functions)
    demand(f'{major}: matrix lineage hash', manifest['reviewed_inputs']['matrix'] == inputs[matrix_path])
    demand(f'{major}: acceptance lineage hash', manifest['reviewed_inputs']['root_acceptance'] == inputs[accept_path])
    demand(f'{major}: source-capture lineage hash', manifest['reviewed_inputs']['ordinary_source_capture'] == inputs[capture])
    checks_actual = collections.Counter((r['relation'], r['expression']) for r in manifest['check_keys'])
    checks_expected = collections.Counter((r['relation'], r['expression']) for r in manifest['expressions']['checks'])
    demand(f'{major}: 80 CHECK dependency multisets retain expression identity', len(manifest['check_keys']) == 80 and checks_actual == checks_expected)
    for check in manifest['check_keys']:
        known_columns = {column['name'] for column in matrix['relations'][check['relation']]['columns']}
        demand(f'{major}: CHECK dependency column membership {len(checks)}', bool(check['columns']) and set(check['columns']) <= known_columns)
    packet = next(p for p in accepted['producer_packets'] if int(p['major']) == major)
    receipt = read(packet['receipt'])
    demand(f'{major}: independently accepted packet seal', inputs[packet['receipt']] == packet['receipt_sha256'])
    packet_root = Path(packet['receipt']).parent
    oracle_path = str(packet_root / 'source-compiled-oracle.json')
    oracle = read(oracle_path)
    clean_path = str(packet_root / 'clean-baseline.json')
    clean = read(clean_path)
    clean_keys = collections.Counter((r['relation'], r['expression'], tuple(r['columns'])) for r in clean['constraints'] if r['contype'] == 'c')
    literal_keys = collections.Counter((r['relation'], r['expression'], tuple(r['columns'])) for r in manifest['check_keys'])
    demand(f'{major}: CHECK-key literals equal original clean-source packet', literal_keys == clean_keys)
    demand(f'{major}: source-compiled oracle lineage', manifest['reviewed_inputs']['source_compiled_oracle'] == inputs[oracle_path])
    demand(f'{major}: clean CHECK-key packet lineage', manifest['reviewed_inputs']['check_keys_clean_packet'] == inputs[clean_path])
    demand(f'{major}: source and clean packet were sealed', receipt['outputs_sha256']['source-compiled-oracle.json'] == inputs[oracle_path] and receipt['outputs_sha256']['clean-baseline.json'] == inputs[clean_path])
    # Original-source compiled expressions are the expected values, not live attacks.
    demand(f'{major}: exact original-source compiled expressions', manifest['expressions'] == {key: oracle[key] for key in ['checks', 'defaults', 'policies', 'predicates']})

bindings = manifests[16]['source_bindings']
demand('majors share exact semantic source closure', bindings == manifests[17]['source_bindings'])
expected_migrations = ['20261024000000_add_oban.exs','20261025000000_add_build_journals.exs','20261025000001_add_build_admission.exs','20261025000002_add_build_aggregate_limits.exs','20261025000003_add_customer_authorization.exs','20261025000004_add_authorization_state_revisions.exs','20261025000005_add_customer_artifact_storage.exs','20261025000006_add_customer_workspace_discovery.exs','20261025000007_add_browser_sessions.exs']
demand('explicit original nine migration names only', sorted(Path(p).name for p in bindings if '/migrations/' in p and p.endswith('.exs')) == sorted(expected_migrations))
demand('approved exact sixteen-file Oban source closure', len([p for p in bindings if p.startswith('hosted/deps/oban/')]) == 16)
demand('source bindings never import verification fixtures', len(bindings) == 29 and all(p.startswith('hosted/') and '/test/' not in p for p in bindings))
for path, digest in bindings.items():
    demand('current semantic closure ' + path, sha(ROOT / path) == digest)
    inputs[path] = digest

for packet in producer['selected']:
    receipt = read(packet['path'])
    base = Path(packet['path']).parent
    demand(f"PG{packet['major']}: selected producer receipt seal", inputs[packet['path']] == packet['sha256'])
    demand(f"PG{packet['major']}: successful observed cleanup", receipt['success'] and all(receipt['cleanup'].values()))
    for path, digest in receipt['source_sha256'].items():
        demand(f"PG{packet['major']}: frozen input " + path, sha(ROOT / base / 'inputs' / path) == digest and sha(ROOT / path) == digest)
    for path, digest in receipt['output_sha256'].items():
        demand(f"PG{packet['major']}: immutable output " + path, sha(ROOT / base / path) == digest)
    selected_checks = read(str(base / 'checks.json'))
    demand(f"PG{packet['major']}: advertised methods and mutations", selected_checks['passed'] == packet['methods'] and selected_checks['live_mutations'] == packet['actual_mutations'])
    effects = read(str(base / 'mutation-effects.json'))
    demand(f"PG{packet['major']}: every live attack has independent observed effect", len(effects) == packet['actual_mutations'] and all(e['observed'] is True for e in effects))
    names = {method['name'] for method in selected_checks['checks']}
    coverage = read('verification/hosted-browser-relation-catalog/coverage.json')
    for case in coverage['cases']:
        demand(f"PG{packet['major']}: real named methods for " + case['id'], set(case['component_methods'][str(packet['major'])]) <= names)
original = read('verification/hosted-browser-relation-admission-contract/runtime-adversity-matrix.json')
demand('all 48 contract IDs mapped without broad runtime pass', len(coverage['cases']) == 48 and coverage['full_contract_cases_claimed_passed'] == 0)
demand('all original requirements preserved verbatim', [(c['id'],c['requirement']) for c in coverage['cases']] == [(c['id'],c['requirement']) for c in original])
demand('every mapped contract case retains a limitation', all(case['limitations'] and case['status'] != 'passed' for case in coverage['cases']))
(BASE / 'audit.json').write_text(json.dumps({'passed': len(checks), 'checks': checks, 'input_sha256': inputs, 'scope': 'Independent artifact, source-oracle lineage, semantic closure and honest method mapping; source inspection is not runtime acceptance.'}, indent=2, sort_keys=True) + '\n')
print('passed independent artifact/source assertions:', len(checks))
