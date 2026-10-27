"""Record reviewed partial interfaces and explicit implementation amendments once."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RECEIPT = HERE / 'actual-owner-callee-CI-metadata.json'
AMENDMENT = HERE / 'guarded-snapshot-actual-owner-Rust-contract-amendment.json'
CORRECTION = HERE / 'callee-source-correction-acceptance-custody-field.json'
assert not any(p.exists() for p in (RECEIPT, AMENDMENT, CORRECTION))

def row(p):
    data = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(p, value):
    with p.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def read(p):
    return json.loads(p.read_bytes())

metadata = ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']
before = [row(ROOT / p) for p in metadata]
protected = {
    '.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57',
    'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299',
}
for name, digest in protected.items():
    assert row(ROOT / name)['sha256'] == digest

selection_path = HERE / 'guarded-snapshot-actual-owner-Rust-implementation-selection.json'
acceptance_path = HERE / 'guarded-snapshot-provider-callee-source-correction-host-acceptance.json'
assert row(selection_path)['sha256'] == '9551f5e447c600af27aa96146a757ea1452027c465baf76fd3c1d8c31b88ce61'
assert row(acceptance_path)['sha256'] == '5e416d8da36d082f44b22b6830b6feca65f08677e46e72bf048817972b5a3fee'
selection, acceptance = read(selection_path), read(acceptance_path)
at = datetime.now(timezone.utc).isoformat()
save(AMENDMENT, {
    'schema': 1, 'at': at, 'status': 'root-selected-contract-amendments-before-compiler-execution',
    'immutable_selection': row(selection_path),
    'basis': 'Explicit root and producer/preaccess coordination; this receipt does not read either active lane or certify its implementation.',
    'requirements': {
        'caller_retained_ledger': 'Zero-argument selector returns an opaque caller-retained BootstrapLedger. Any reservation/owner explicitly borrows it. Never return an arbitrary-lifetime AdmittedOwner from a zero-argument function. Production remains BootstrapPolicyPending before effects.',
        'actual_shared_owning_core': 'Production File and private test DropGuard specialize the same private generic owning core. Move the entire typed LoaderOutcomeV1, including proof, Files, error and usage, before any fallible association check. A separate synthetic structural mirror is insufficient.',
        'strict_admission': 'Keep production parsers and budget_valid unchanged. Before expected-state publication, admission must require positive extent and each of the five positive limits, the complete regular File identity, exact integer domains, and full signed-i64 timestamp fields. Parser/build-count/digest-shape success alone supplies no compile, custody or policy authority.',
        'same_live_owner': 'Expected and one-shot attempt must refer to the same admitted live owner. Overlapping lifetimes and equal metadata are insufficient. Test two overlapping equal-metadata owners and reject cross-owner pairs after whole carrier capture, preserving original diagnostics and preventing leaf dispatch. Private association generation is checked, non-renewable and cannot mint admission or native authority.',
        'actual_buffer_lifetimes': selection['A1'],
    },
    'compiler_plan_unchanged': selection['compiler_plan'],
    'source_ownership_unchanged': selection['source_ownership'],
    'implementation_or_test_pass_claim': False,
    'native_acquisition_fixture_loader_writer_execution_or_GA_selected': False,
})

# The accepted check completed before a local variable was reused for runner
# comparison. Preserve that receipt and correct only its serialized custody field.
assert isinstance(acceptance['custody'], str)
check_dir = HERE / 'callee-source-correction-root-check-after-runner-attribution'
plan = read(check_dir / 'plan.json')
custody = plan['custody_before']
assert len(custody) == 2
for packet in custody:
    assert row(ROOT / packet['path'] / 'seal.json')['sha256'] == packet['seal_sha256']
observed_check = read(check_dir / 'stdout')
assert observed_check['success'] and observed_check['frozen_files'] == 1769
save(CORRECTION, {
    'schema': 1, 'at': at, 'original_acceptance': row(acceptance_path),
    'correction': 'The original custody field accidentally serialized the retained test runner source after local variable reuse. The successful check and original plan retain the intended custody list; use the list below for that field only.',
    'custody': custody, 'original_check_plan': row(check_dir / 'plan.json'),
    'original_check_output': row(check_dir / 'stdout'),
    'check': observed_check, 'original_receipt_preserved': True,
    'acceptance_scope_or_test_result_changed': False, 'tests_replayed': False,
})

ci_path = ROOT / 'verification/github-delivery-source-rebind-services-checkout/ci-jobs-3.stdout'
ci = read(ci_path)
assert ci['headSha'] == 'd6af73813244c330a979afb83b45f53490ff5b29' and ci['databaseId'] == 40551094236
services, = [j for j in ci['jobs'] if j['name'] == 'services']
assert services['status'] == 'completed' and services['conclusion'] == 'success'
assert len(services['steps']) == 8 and all(s['conclusion'] == 'success' for s in services['steps'])
checkout, = [s for s in services['steps'] if s['name'].startswith('Run actions/checkout')]
seconds = (datetime.fromisoformat(checkout['completedAt'].replace('Z', '+00:00')) - datetime.fromisoformat(checkout['startedAt'].replace('Z', '+00:00'))).total_seconds()
assert seconds == 4
w, g = read(ROOT / 'work-graph.json'), read(ROOT / 'gates/ga.json')
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
b['provider_callee_source_correction'].update({
    'status': acceptance['status'], 'accepted': True,
    'root_acceptance': row(acceptance_path), 'custody_field_correction': row(CORRECTION),
    'independent_seal_sha256': '00db7ec194949f945acb86d78e051873be7792076f05793e009ed9c7325739b5',
    'fresh_checks': acceptance['fresh_checks'], 'known_shell_only': acceptance['known_shell_only'],
    'mandatory_positive_residuals': acceptance['mandatory_positive_residuals'],
    'complete_prices_root_funding_or_GA_selected': False,
})
b['actual_owner_Rust_selection'].update({
    'status': selection['status'], 'accepted': True, 'actual_implementation_started': True,
    'compiler_authorized': True, 'root_selection': row(selection_path), 'contract_amendment': row(AMENDMENT),
    'implementation_ownership': selection['implementation_ownership'],
    'independent_preaccess_ownership': selection['independent_preaccess_ownership'],
    'implementation_status': 'active-not-yet-reviewed-or-accepted',
    'native_acquisition_authorized': False, 'compiler_plan': selection['compiler_plan'],
})
d = c['guarded_snapshot_source_rebind_services_checkout_delivery']
d.update({'status': 'pushed-services-fix-remote-passed-workflow-in-progress', 'CI_pending': True})
d['CI'].update({'status': ci['status'], 'conclusion': ci['conclusion'], 'observation': row(ci_path),
    'passed': False, 'jobs': [{k: j[k] for k in ['name', 'status', 'conclusion']} for j in ci['jobs']]})
c['services_CI_sparse_checkout'].update({
    'status': 'pushed-local-and-remote-services-validation-passed', 'remote_fix_verified': True,
    'remote_full_service_race_suite_passed': True, 'remote_passed_steps': 8,
    'remote_checkout_seconds': seconds, 'remote_observation': row(ci_path),
    'full_service_race_suite_rerun_scope': 'Remote Linux services job; no full local rerun claimed.',
})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
assert w['packages'][3]['passiveLifecycleRuntimePreparation'].startswith('Root accepts')
w['packages'][3]['nextImplementation'] = 'The Sendable correction, generic build and V9 host runtime preparation already have bounded acceptance. Preserve the unresolved native focus result; native execution remains paused. Continue independent source work only when a concrete remaining defect is identified.'
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')

current = ('The actual Rust input-owner slice is selected and implementation is active in an isolated two-member source overlay. '
    'The contract now explicitly requires a caller-retained bootstrap ledger, the same owning core for real Files and test guards, strict positive admission checks, and same-live-owner correlation despite equal metadata. '
    'A separate preaccess review is preparing adversarial cases; compilation and independent implementation acceptance remain pending. '
    'The corrected callee interface has bounded partial acceptance after seven fresh methods, 1,473 adverse controls and 532 equalities; thirty work and storage contexts remain explicitly unpriced. '
    'No complete root funding, native acquisition or GA acceptance follows.')
for name in ['PLAN.md', 'STATUS.md']:
    p = ROOT / name
    text = p.read_text()
    old = next(s for s in text.split('\n\n') if s.startswith('Checkpoint `d6af738`'))
    new = old.replace('is queued for this exact changed workflow; full remote service race validation remains pending.',
        'has passed services, VM, Android host and the Swift cache fixture jobs. Services checkout took four seconds and all eight steps passed, including vet and race tests. The two remaining Swift jobs are still running.')
    assert new != old
    text = text.replace(old, current + '\n\n' + new, 1)
    text = text.replace('independent review and remote validation of that fix remain pending.', 'the later d6af738 checkpoint records its independent acceptance and remote validation.', 1)
    text = text.replace('The next Rust ownership interface is being mapped to actual loader lifetimes, which differ from the model buffers.', 'The subsequently selected Rust implementation preserves actual loader lifetimes, which differ from the model buffers.', 1)
    p.write_text(text)

assert len(w['packages']) == 18 and len(g['gates']) == 38
assert sum(x['status'] == 'running' for x in g['gates']) == 8
assert sum(x['status'] == 'planned' for x in g['gates']) == 30
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
for name, digest in protected.items(): assert row(ROOT / name)['sha256'] == digest
subprocess.run(['git', 'diff', '--check', '--', *metadata], cwd=ROOT, timeout=10, check=True)
save(RECEIPT, {'schema': 1, 'at': at, 'source_commit': ci['headSha'], 'python': sys.version,
    'script': row(Path(__file__).resolve()), 'before': before, 'after': [row(ROOT / p) for p in metadata],
    'contract_amendment': row(AMENDMENT), 'custody_field_correction': row(CORRECTION),
    'CI_observation': row(ci_path), 'protected_work_unchanged': True, 'GA_verified': 0,
    'scope': 'Metadata and explicit contract amendments only; active agent directories not read.'})
print(json.dumps({'metadata_updated': True, 'services_steps_passed': 8, 'checkout_seconds': seconds,
    'Rust_implementation_selected': True, 'partial_callee_interface_accepted': True, 'GA_verified': 0}))
