"""Retain terminal service timeout and synchronize bounded root review decisions."""
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
REV = ROOT / 'verification/swift-semantic-adapter-root-review'
SHA = lambda data: hashlib.sha256(data).hexdigest()


def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': SHA(data)}


def save(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


assert not (OUT / 'reviewed-source-terminal-metadata.json').exists()
obs = OUT / 'ci-jobs-6.stdout'
ci = json.loads(obs.read_bytes())
assert ci['headSha'] == '9398732c23648a82097d5a72b02b1c77af818e41'
assert ci['status'] == 'completed' and ci['conclusion'] == 'cancelled' and ci['attempt'] == 1
assert len(ci['jobs']) == 6 and sum(j['conclusion'] == 'success' for j in ci['jobs']) == 5
service = next(j for j in ci['jobs'] if j['name'] == 'services')
assert service['databaseId'] == 122334424079 and service['conclusion'] == 'cancelled'
assert service['steps'][1]['name'] == 'Run actions/checkout@v4' and service['steps'][1]['conclusion'] == 'cancelled'
assert all(s['conclusion'] == 'skipped' for s in service['steps'][2:5])
annotations = json.loads((OUT / 'services-cancellation-annotations.stdout').read_bytes())
assert any('maximum execution time of 15m0s' in a['message'] for a in annotations)
terminal_path = OUT / 'terminal-ci-attempt1.json'
terminal = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'commit': ci['headSha'],
            'run': ci['databaseId'], 'attempt': 1, 'status': 'completed', 'conclusion': 'cancelled',
            'jobs_passed': 5, 'jobs_cancelled': 1, 'jobs_running': 0,
            'passed_job_steps': sum(len(j['steps']) for j in ci['jobs'] if j['conclusion'] == 'success'),
            'service_job': service['databaseId'], 'service_failure_stage': 'checkout at fifteen-minute job limit',
            'service_tool_setup_and_all_test_steps_skipped': True, 'CI_passed': False,
            'observation': row(obs), 'annotations': row(OUT / 'services-cancellation-annotations.stdout'),
            'earlier_log_fetch_failed_while_workflow_running': row(OUT / 'services-cancellation-log.command.json'),
            'services_retry_requested': False, 'url': ci['url']}
save(terminal_path, terminal)

# One new exact-job log request after terminal status; preserve the earlier failure.
argv = ['gh', 'run', 'view', '40545367451', '--repo', 'snowdamiz/mixer', '--job', '122334424079', '--log']
prefix = OUT / 'services-terminal-log'
assert not prefix.with_suffix('.stdout').exists()
start = time.monotonic()
child = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
timed = False
try:
    stdout, stderr = child.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timed = True
    if group_exists(child.pid): os.killpg(child.pid, signal.SIGTERM)
    try:
        stdout, stderr = child.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        if group_exists(child.pid): os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate(timeout=5)
for suffix, body in [('stdout', stdout), ('stderr', stderr)]:
    with prefix.with_suffix('.' + suffix).open('xb') as stream: stream.write(body)
log_receipt = {'argv': argv, 'exit': child.returncode, 'timed_out': timed,
               'elapsed_seconds': time.monotonic() - start, 'owned_pid': child.pid, 'owned_pgid': child.pid,
               'owned_child_reaped': child.returncode is not None, 'owned_group_absent': not group_exists(child.pid),
               'python_version': sys.version, 'script': row(Path(__file__).resolve()),
               'stdout': row(prefix.with_suffix('.stdout')), 'stderr': row(prefix.with_suffix('.stderr')),
               'scope': 'read-only exact remote CI job log; no retry or runtime invocation'}
save(prefix.with_suffix('.command.json'), log_receipt)
assert log_receipt['owned_group_absent'] and not timed

affine_path = REV / 'guarded-snapshot-prepaid-affine-refusal-host-acceptance.json'
string_path = REV / 'guarded-snapshot-string-provider-source-rebind-host-acceptance.json'
return_path = REV / 'guarded-snapshot-owned-provider-callee-interfaces-return.json'
assert row(affine_path)['sha256'] == 'cc2a0954afd77ccd843d93f37f71bad22504391844e2edcaaa46bae98c51fd28'
assert row(string_path)['sha256'] == '07dcf216a6371f54e6ceb85a16d55614a23388395eab212c79f5ec9f3de73a90'
assert row(return_path)['sha256'] == 'd497b65fed7324ffa52b5a90a2c8b8c2bdd323c59a2a574a5b38d44667f0dc49'
w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
b['prepaid_input_owner_affine_refusal'].update({'status': 'root-accepted-bounded-synthetic-trusted-local-model',
    'accepted': True, 'root_acceptance': row(affine_path), 'independent_methods': 35,
    'independent_small_extent_read_schedules': 58904, 'independent_blocking_findings': 0,
    'independent_review_seal_sha256': '25eb5a5f02059ab38953f9435bef2e308e2e946290c231ebd922459e20dd679d',
    'actual_Rust_implementation_or_native_authority': False,
    'finite_replay_not_unlimited_external_caller_work': True})
b['string_provider_source_rebind'].update({'status': 'root-accepted-bounded-conditional-current-source-MIR-rebind',
    'accepted': True, 'root_acceptance': row(string_path), 'independent_qualifying_commands': 12,
    'independent_targeted_controls': 1139, 'independent_blocking_findings': 0,
    'independent_review_seal_sha256': '7048717734e68adc9ee56be046217232818322b4baad0dabb978444e02c229af',
    'conditional_envelope_bytes': 5080, 'current_provider_L_str_selected': False,
    'five_COMPILED_None_is_substantive_UnsupportedBuild': True, 'actual_success_path_qualified': False})
b['owned_provider_callee_interfaces'].update({'status': 'returned-R1-R2-R3-source-completeness-corrections-required',
    'accepted': False, 'root_return': row(return_path),
    'independent_review_seal_sha256': '050da55a398e839075dd841e81d4da580f74a97adf2d6346b0d8e44587680e16',
    'findings': ['overflowing_add written casts and exact ActualT substitution',
        'const_eval_select macro-selected runtime callable/unit/return/end interface',
        'Option is_some auto-borrow/helper/matches source expansion'],
    'old_arithmetic_consistency_not_source_completeness': True})
b['provider_callee_source_correction'] = {'status': 'isolated-correction-active-awaiting-freeze-and-independent-review',
    'owner': '/root/swift_provider_callee_source_correction',
    'ownership': 'verification/swift-guarded-snapshot-provider-callee-source-correction',
    'root_return': row(return_path), 'accepted': False, 'compiler_authorized': False,
    'allowed_boundary': 'range_next may retain explicit strictly positive exact-context work and storage obligations; no unobserved layout substitution'}
b['actual_owner_Rust_selection'] = {'status': 'bounded-source-interface-selection-preparation-active',
    'owner': '/root/swift_actual_owner_rust_selection',
    'ownership': 'verification/swift-guarded-snapshot-actual-owner-rust-selection',
    'actual_implementation_started': False, 'compiler_authorized': False, 'accepted': False,
    'minimum_direction': 'existing loader opens and private nine-group provenance correlation before leaf',
    'required_correspondence_amendment': 'actual loader temporary buffer and retained proof lifetimes differ from four synthetic selected buffers; preserve actual source lifetimes and charge all actual overlap',
    'larger_same_handle_or_four_buffer_retention_rewrite_selected': False}
delivery = c['guarded_snapshot_host_proof_vm_checkout_delivery']
delivery.update({'status': 'pushed-terminal-five-jobs-pass-services-checkout-cancelled', 'CI_pending': False})
delivery['CI'].update({'status': 'completed', 'conclusion': 'cancelled', 'attempt': 1, 'passed': False,
    'jobs_passed': 5, 'jobs_cancelled': 1, 'jobs_in_progress': 0, 'passed_job_steps': 56,
    'observation': row(obs), 'observation_sha256': row(obs)['sha256'],
    'terminal_receipt': row(terminal_path), 'services_tests_ran': False})
c['VM_CI_sparse_checkout']['status'] = 'changed-VM-job-all-twelve-steps-passed-terminal-workflow-services-checkout-cancelled'
c['services_CI_sparse_checkout'] = {'status': 'local-focused-positive-and-negative-checks-pass-independent-review-active',
    'ownership': 'verification/ci-services-sparse-checkout',
    'seal_sha256': '244417580cacbd04fcb79685e5a15d376314320d9c70f40be49d2df2194f071f',
    'members': 31, 'bytes': 120762, 'selected_files': 153, 'selected_bytes': 4379716,
    'commands_unchanged': True, 'Go_version': '1.26.4', 'host': 'darwin-arm64',
    'focused_descriptor_test_passed': True, 'missing_external_contract_control_failed_as_expected': True,
    'full_service_race_suite_rerun': False, 'remote_fix_verified': False, 'accepted': False,
    'independent_owner': '/root/services_sparse_checkout_independent',
    'independent_ownership': 'verification/ci-services-sparse-checkout-independent',
    'producer_cleanup_receipt_limit': 'cleanup booleans retained; numeric producer command PID/PGID not recorded and cannot be reconstructed',
    'original_terminal_failure': row(terminal_path)}
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
assert len(w['packages']) == 18 and len(g['gates']) == 38
assert sum(x['status'] == 'running' for x in g['gates']) == 8
assert sum(x['status'] == 'planned' for x in g['gates']) == 30
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
lead = ('Checkpoint `9398732` is pushed with 547 selected paths and six frozen packets. '
    '[CI](https://github.com/snowdamiz/mixer/actions/runs/40545367451) is terminal: five jobs pass, while services is cancelled during checkout at its fifteen-minute job limit; service setup and tests are skipped. '
    'The changed VM job passes all twelve steps after a seven-second checkout. Parent `a96712b` retains six passing jobs and 64 steps after its VM-only retry, with the original cancellation preserved. '
    'A local services sparse checkout now preserves all commands, materializes all 153 selected inputs, and passes the focused descriptor test and intended missing-contract negative control; independent review and remote validation of that fix remain pending. '
    'Canonical product sources, actual root funding, runtime/native and GA acceptance remain unchanged.')
reviews = ('Root accepts the affine input-owner correction only as a synthetic trusted-local Python host model after 35 fresh independent methods and 58,904 independently enumerated small-extent read schedules. '
    'The current-provider string rebind has bounded exact-source/MIR acceptance after twelve qualifying command groups and 1,139 targeted controls; five `COMPILED=None` identities still cause `UnsupportedBuild`, and the conditional 5,080-byte envelope is not a selected whole-host string bound. '
    'The callee proposal is returned for omitted casts, macro-selected runtime interfaces and Option auto-borrow/helper work; a separate correction preserves explicit positive unresolved work/storage obligations. '
    'The next Rust ownership interface is being mapped to actual loader lifetimes, which differ from the model buffers. No actual acquisition authority, source policy, root funding, successful fixture execution or operational grant is selected.')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name
    content = path.read_text()
    old = next(p for p in content.split('\n\n') if p.startswith('Checkpoint `9398732` is pushed'))
    content = content.replace(old, lead, 1)
    old = next(p for p in content.split('\n\n') if p.startswith('All three new candidates are now frozen and under fresh independent review'))
    path.write_text(content.replace(old, reviews, 1))
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json', '.github/workflows/verify.yml'], cwd=ROOT, timeout=10, check=True)
assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT, timeout=10)
for name, expected in [('.github/workflows/hosted.yml', 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57'),
    ('hosted/lib/mixer_hosted/browser_auth/store.ex', '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299')]:
    assert row(ROOT / name)['sha256'] == expected
save(OUT / 'reviewed-source-terminal-metadata.json', {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'terminal': row(terminal_path), 'terminal_log': row(prefix.with_suffix('.command.json')),
    'affine_acceptance': row(affine_path), 'current_string_acceptance': row(string_path), 'callee_return': row(return_path),
    'metadata': [row(ROOT / n) for n in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
    'protected_files_unchanged': True, 'index_empty': True, 'GA_verified': 0})
print(json.dumps({'CI': 'five-pass-services-checkout-cancelled', 'terminal': row(terminal_path),
    'terminal_log_exit': child.returncode, 'new_bounded_acceptances': 2, 'GA_verified': 0}))
