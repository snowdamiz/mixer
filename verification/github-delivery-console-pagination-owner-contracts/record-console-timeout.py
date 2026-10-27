"""Record the checkout-only Console failure and the released Rust review state."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'console-checkout-timeout.json'
assert not OUT.exists()

def row(p):
    data = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

ci = json.loads((HERE / 'ci-jobs-4.stdout').read_bytes())
assert ci['headSha'] == 'b231f3d405c06bfb348f193d46a348af0529bd84'
assert ci['databaseId'] == 40556161476 and ci['status'] == 'completed' and ci['conclusion'] == 'cancelled'
job, = ci['jobs']
checkout, = [s for s in job['steps'] if s['name'] == 'Run actions/checkout@v4']
assert checkout['conclusion'] == 'cancelled'
skipped = [s['name'] for s in job['steps'] if s['conclusion'] == 'skipped']
assert len(skipped) == 4 and 'Release-check model and Solid view' in skipped
value = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'commit': ci['headSha'],
    'run': ci['databaseId'], 'status': 'completed', 'conclusion': 'cancelled',
    'checkout_started': checkout['startedAt'], 'checkout_cancelled': checkout['completedAt'],
    'job_started': job['startedAt'], 'job_completed': job['completedAt'], 'skipped_steps': skipped,
    'test_failure_observed': False, 'remote_console_tests_or_build_ran': False,
    'observation': row(HERE / 'ci-jobs-4.stdout'), 'command_receipt': row(HERE / 'ci-jobs-4.command.json'),
    'scope': 'Console job reached its five-minute limit during checkout; compiler/test setup was never reached. Root selected a separate six-entry sparse checkout repair preserving commands and timeout.',
    'python': sys.version, 'script': row(Path(__file__).resolve()),
    'repair_owner': 'verification/ci-console-sparse-checkout', 'remote_repair_passed': False}
with OUT.open('x') as stream:
    json.dump(value, stream, indent=2)
    stream.write('\n')
w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
d = w['packages'][13]['firstPageReturn']['delivery']
d.update({'status': 'pushed-Console-checkout-cancelled-other-workflows-pending', 'Console_terminal': row(OUT)})
for run in d['CI']['runs']:
    if run['databaseId'] == ci['databaseId']:
        run.update({'status': 'completed', 'conclusion': 'cancelled'})
g['gates'][21]['firstPageReturn']['delivery'] = copy.deepcopy(d)
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
c['guarded_snapshot_actual_owner_selection_console_delivery'] = copy.deepcopy(d)
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
release = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-actual-owner-Rust-frozen-release.json'
b['actual_owner_Rust_selection'].update({'implementation_status': 'frozen-candidate-independent-source-MIR-review-active',
    'root_frozen_release': row(release), 'candidate_source146_tree': '338ef290399450c712b140736fb714031a333891dc1acf5439c758ae97602564',
    'independent_review_status': 'source-MIR-review-active-one-targeted-ownership-order-witness-selected',
    'independent_witness_budget': {'Debug_test_build': 1, 'exact_filtered_host_run': 1, 'each_seconds_max': 55,
        'scope': 'Test whether an owned correlated result can outlive acquisition retirement; no broad matrix or native File execution.'},
    'implementation_accepted': False})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
repair = {'status': 'implementation-and-offline-input-closure-validation-selected',
    'ownership': 'verification/ci-console-sparse-checkout', 'terminal_original': row(OUT),
    'runtime_pins_commands_timeout_unchanged': True, 'accepted': False, 'remote_passed': False}
for target in [w['packages'][13], g['gates'][21]]: target['ConsoleSparseCheckout'] = copy.deepcopy(repair)
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name in ['PLAN.md', 'STATUS.md']:
    p = ROOT / name
    text = p.read_text()
    old = 'Console and Phoenix CI are running, while Engine CI is queued; none is yet terminal.'
    assert text.count(old) == 1
    text = text.replace(old, 'Console CI is cancelled at its five-minute limit during checkout; setup, tests and build were skipped. '
        'A separate sparse checkout repair is selected. Phoenix and Engine workflows remain pending.')
    old = 'the producer reports passing final compiler and focused host checks, with frozen release and independent implementation acceptance pending.'
    assert text.count(old) == 1
    text = text.replace(old, 'the candidate is frozen after final compiler and 15-method host passes in each mode. '
        'Independent source/MIR review is active and is testing a possible result-versus-acquisition retirement ordering gap; implementation acceptance remains pending.')
    p.write_text(text)
print(json.dumps({'Console_checkout_cancelled': True, 'console_tests_skipped': True,
    'Rust_frozen_for_independent_review': True, 'GA_verified': 0}))
