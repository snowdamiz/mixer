"""Bind independently reproduced Q9/Q10 defects and select isolated correction."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'verification/swift-cache-state-independent-review/implementation-review-1/private-guard-run-1'
def bind(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

summary = json.loads((RUN / 'summary.json').read_bytes())
assert summary['case_observations'] == 14 and summary['failing_case_observations'] == 8 and summary['passing_case_observations'] == 6
assert not summary['public_reachability_established'] and not summary['product_source_changed']
for mode in summary['modes']:
    assert len(mode['cases']) == 7
    assert sum(c['full32_matches'] and c['shape_matches'] for c in mode['cases']) == 3
    for case in mode['cases']:
        assert len(case['expected_words']) == len(case['observed_words']) == 32
        assert case['full32_matches'] == (case['expected_words'] == case['observed_words'])
        assert case['shape_matches'] == (case['expected_shape'] == case['observed_shape'])
cleanup = json.loads((RUN / 'cleanup.json').read_bytes())
assert len(cleanup['owned_binary_products']) == 2
assert all(r['all_owned_commands_returned'] and r['removed'] and not Path(r['path']).exists() for r in cleanup['owned_binary_products'])
assert not cleanup['unrelated_paths_removed']
candidate = ROOT / 'verification/swift-cache-state-implementation/candidate-repo-seal.json'
assert bind(candidate)['sha256'] == 'caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3'
for member in json.loads(candidate.read_bytes())['members']:
    assert bind(ROOT / member['path']) == member
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'Q9-Q10-private-guard-defects-confirmed-isolated-correction-selected',
    'python': sys.version, 'command': sys.argv, 'script': bind(Path(__file__)),
    'baseline_candidate': bind(candidate),
    'private_admission': bind(OUT / 'private-guard-review-admission.json'),
    'observed_evidence': [bind(RUN / name) for name in ('summary.json', 'source-receipt.json', 'tool-receipt.json', 'cleanup.json', 'expected-cases.json')],
    'private_observations_per_mode': {'passed': 3, 'failed': 4},
    'scope': 'Actual frozen shape_q/projection invoked with deliberately seeded private state in two binary modes; public39 still pass, ordinary-input reachability not established.',
    'findings': [
        'Q10: masks must not be checked outside planned stages6..10; inactive selected/taken values wrongly suppress the observation.',
        'Q9: pending stages7/8 require feasible=true; false feasibility wrongly exposes the live observation instead of T09 poison.'
    ],
    'selected_change': 'Condition masks/feasibility read set on exact selected stage predicates; require feasible=true for pending. Preserve full32 projection, terminal precedence, old prefixes/API and all resource caps. Add independent producer controls for all stages and relevant guard boundaries.',
    'ownership': ['verification/swift-cache-state-implementation/correction-1/**'],
    'immutable': 'Every original454 member, candidate-repo-seal.json, intermediate seals and external original implementation doc remain byte-identical; new files only under correction-1.',
    'validation': 'Own focused guard controls plus applicable public/regression/API/layout and work/caller/lifetime reconciliation in both modes against exact new bytes; immutable final source/evidence manifest. Do not import/read independent expected fixtures, glue or oracle as producer implementation.',
    'correction_doc': 'Keep new correction documentation inside correction-1; do not modify the original sealed external doc.',
    'remaining_source_review': 'Independent P01-P35 and coarse scalar-block accounting reconciliation continue; further findings must be coordinated, never hidden by widening caps or changing oracle.',
    'implementation_accepted': False, 'native_runtime_or_capture_started': False, 'GA_qualified': False,
}
output = OUT / 'guard-correction-selection.json'
assert not output.exists()
output.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(bind(output)))
