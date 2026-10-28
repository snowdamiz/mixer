#!/usr/bin/env python3
"""Bind saved observations and reviewed corrections; no runtime or remote actions."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import ast
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
BASE = '56ff14c925168284761c5aca4f0bd4129cf3c995'
TREE = '75989099938ed5256c4144cbc9e62979ee323183'
SELECTION = ROOT / 'verification/console-session-and-checkout-root-review/identity-network-rebar-selection.json'
FIELDLOG = ROOT / 'verification/fieldlog-public-sdk-root-review/public-host-ci-observation.json'
CANONICAL = [ROOT / p for p in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']]
WRITES = set(CANONICAL + [SELECTION, FIELDLOG, OUT / 'checkpoint.json'])
PUBLIC_INPUTS = [(ROOT.parent / 'fieldlog/.codex-publication-and-ci' / name).resolve()
                 for name in ['visibility-receipt.json', 'dispatch-receipt.json']]
events = {}


def audit(event, args):
    events[event] = events.get(event, 0) + 1
    if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.posix_spawnp',
                 'os.fork', 'os.forkpty', 'os.exec', 'pty.spawn', 'ctypes.dlopen', 'os.kill'} or event.startswith('socket.'):
        raise RuntimeError('checkpoint forbids process, network, native and custody operations')
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0])).absolute()
        if str(path).startswith(('/proc/', '/dev/')) or any(p in path.parts for p in ('.ssh', '.aws', '.wrangler')):
            raise RuntimeError('checkpoint forbids credential and custody paths')
        mode, flags = args[1:3]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing and path not in WRITES:
            raise RuntimeError('checkpoint write outside assigned paths: ' + str(path))
        if not writing and path.is_relative_to(ROOT.parent / 'fieldlog') and path.resolve() not in PUBLIC_INPUTS:
            raise RuntimeError('checkpoint may read only the two sanitized FieldLog receipts')


sys.addaudithook(audit)
signal.alarm(50)
started = time.monotonic()
at = datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_bytes())


def identity(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def row(path):
    return {'path': str(path.relative_to(ROOT)), **identity(path)}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def distribution_digest(files):
    return hashlib.sha256(''.join(name + '\0' + files[name]['sha256'] + '\n'
                                 for name in sorted(files)).encode()).hexdigest()


def save(path, value, exclusive=True):
    with path.open('x' if exclusive else 'w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def packet(name, expected_sha, count):
    path = ROOT / name
    assert identity(path)['sha256'] == expected_sha, name
    manifest = read(path)
    assert len(manifest['files']) == count
    total = 0
    for name, expected in manifest['files'].items():
        member = path.parent / name
        assert member.resolve().is_relative_to(path.parent.resolve())
        actual = identity(member)
        assert actual == expected, str(member)
        total += actual['bytes']
        assert total <= 256 * 1024 * 1024
    if 'tree_digest_sha256' in manifest:
        assert digest(manifest['files']) == manifest['tree_digest_sha256']
    return {'manifest': row(path), 'files_rehashed': count, 'bytes_rehashed': total}


def current_sources(bindings):
    result = []
    for name, expected in bindings.items():
        actual = row(ROOT / name)
        assert {k: actual[k] for k in ('bytes', 'sha256')} == expected, name
        result.append(actual)
    return result


def evidence(target, name):
    if name not in target['evidence']:
        target['evidence'].append(name)


assert not any(p.exists() for p in [SELECTION, FIELDLOG, OUT / 'checkpoint.json'])
before_metadata = [row(p) for p in CANONICAL]
w, g = read(CANONICAL[2]), read(CANONICAL[3])
old_w, old_g = deepcopy(w), deepcopy(g)
gate_states = {x['id']: x['status'] for x in g['gates']}
assert Counter(gate_states.values()) == {'running': 8, 'planned': 30}

network_packet = packet('verification/github-delivery-binary-export-and-ui/network-review/packet-manifest.json',
    '148912f1c031a1bdd757376436cd4959235b170f7dd2ae60e6c38df2d6a96d8c', 483)
correction_packet = packet('verification/identity-network-rebar-output-correction/packet-manifest.json',
    'd56a5dde00bc61888d5cdf690cf0e44bf11430ac3bb82a819d3206de390349ac', 48)
review_packet = packet('verification/identity-network-rebar-output-independent/packet-manifest.json',
    '400f86a85ab267f3fa72502056c3d0e93f15724979f22d1181a56589c5124a75', 10)
cache_packet = packet('verification/github-delivery-binary-export-and-ui/cache-deadline-review/seal.json',
    'c6bde1201697149bfa84d2f31b112d14d8c1e35ac005fc908a16433941f23df8', 74)
cli_packet = packet('verification/android-sdk-axis-pair-correction/seal.json',
    '48bddc83a55fe07b2295f8250fb7352f1031910d07e74c172635fe632c788110', 10)
review_dir = ROOT / 'verification/identity-network-rebar-output-independent'
decision = read(review_dir / 'decision.json')
source_review = read(review_dir / 'source-verification.json')
assert decision['decision'] == 'accept-source-correction-for-fresh-isolated-CI-only'
assert not decision['blocking_findings'] and not decision['runtime_qualification'] and not decision['GA_accepted']
assert decision['source_revision_observed_by_readonly_git'] == BASE and decision['git_tree_observed'] == TREE
bindings = source_review['canonical_source']['files']
assert digest(bindings) == decision['canonical_three_file_tree_digest_sha256'] == '163073180bacc272e3d19209508cf9e625950f1afb8bc7a5b6b1b1c27ae9bf91'
network_sources = current_sources(bindings)
protected = {name: identity(ROOT / name) for name in source_review['protected_sha256']}
assert all(protected[name]['sha256'] == expected for name, expected in source_review['protected_sha256'].items())
collector_source = (ROOT / 'hosted/scripts/test-identity-network.py').read_text()
assignments = {n.targets[0].id: n.value for n in ast.parse(collector_source).body
               if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
manifest_helper = ast.literal_eval(assignments['MANIFEST_EXS']).encode()
assert len(manifest_helper) == 3380 and hashlib.sha256(manifest_helper).hexdigest() == 'a3d8461e7b399df162c0110892cd9cc32fbac2b3b3b552d76769745977173d30'
workflow = row(ROOT / '.github/workflows/identity-network.yml')
assert workflow['sha256'] == '4b5fa14bfa80601354bd063f3e93f728fa1175e52de3d5c6bcc62a99b044eb19'
actual_network = read(ROOT / 'verification/github-delivery-binary-export-and-ui/network-review/decision.json')
assert actual_network['run_id'] == 40753111388 and actual_network['product_methods_run'] == 0
assert actual_network['source_and_command_joins']['commands_verified'] == 107
assert actual_network['first_causal_failure']['after_command'] == 89
assert len(actual_network['first_causal_failure']['manifest_diff']) == 1
assert all(x['exact_absence_verified'] for x in actual_network['cleanup'].values())
network = {'schema': 1, 'at': at, 'baseline': BASE, 'tree': TREE,
    'status': 'reviewed exact generated-Rebar-output correction selected for fresh isolated CI only',
    'prior_run': 40753111388, 'prior_review': network_packet,
    'prior_binary_exports_bootstrap_archive_restore_PG_isolation_and_offline_compile_passed': True,
    'prior_first_failure': actual_network['first_causal_failure'],
    'prior_product_methods_run': 0, 'prior_complete_commands': 107, 'prior_three_owned_CIDs_closed': True,
    'correction_packet': correction_packet, 'independent_review': review_packet,
    'independent_decision': row(review_dir / 'decision.json'), 'canonical_sources': network_sources,
    'canonical_source_tree_digest_sha256': digest(bindings), 'canonical_controls_passed': 126,
    'independent_pure_methods_passed': 6,
    'policy': 'Only the exact fresh postcompile telemetry source.dag is classified as generated output, retained opaquely within 64KiB and joined to compiled-manifest bytes/hash. Prepared/restored absence, every other input equality and final DAG-inclusive equality remain strict.',
    'MANIFEST_EXS_explicit_change': {'old_bytes': 1717, 'new_bytes': 3380,
        'new_sha256': hashlib.sha256(manifest_helper).hexdigest()},
    'other_helpers_104_metadata_177_product_images_and_caps_unchanged': True,
    'point_in_time_lstat_and_nonatomic_host_capture_limitations_retained': True,
    'pre_persistence_command_exception_may_leave_no_raw_capture': True,
    'hostile_compiler_or_concurrent_writer_integrity_accepted': False,
    'boundary_limitations': decision['boundary_limitations'],
    'remote_execution_selected': True, 'corrected_actual_CI_product_or_GA_accepted': False,
    'required_next_evidence': decision['required_next_evidence'], 'holds_unchanged': True}

cache_dir = ROOT / 'verification/github-delivery-binary-export-and-ui/cache-deadline-review'
cache_review = read(cache_dir / 'receipt.json')
cache_verified = read(cache_dir / 'verification.json')
assert cache_review['runId'] == 40755988137 and cache_review['checksPassed'] == 335
assert cache_review['fullAttempts'] == 2 and cache_review['fullAttemptsRemaining'] == 0
assert cache_review['allFinalLogicalReservationsAndLiveCountersZero'] and cache_review['all11CommandCustodyClosed'] and cache_review['ownedRemoteScratchRemoved']
profiles = []
for profile in cache_verified['profiles']:
    failure = profile['failure']
    profiles.append({'name': profile['name'], 'resource': failure['resource'], 'attempted': failure['attempted'],
        'limit': failure['limit'], 'at_failure_elapsed_micros': failure['at_failure']['elapsed_micros'],
        'Corpus1_completed': False, 'Corpus2_started': profile['corpus2Started']})
assert [(p['resource'], p['attempted'], p['at_failure_elapsed_micros']) for p in profiles] == [
    ('CacheWork', 64000001, 41736968), ('InstructionFuel', 100000001, 44335205)]

swift_dir = ROOT / 'verification/github-delivery-binary-export-and-ui/swift-host-review'
swift = read(swift_dir / 'receipt.json')
assert identity(swift_dir / 'job.log') == swift['log']
assert swift['run'] == 40753111254 and swift['job'] == 123044761924
assert swift['SDK_tests_passed'] == 132 and len(swift['new_axis_tests_passed']) == 9 and swift['update_tests_passed'] == 69
assert swift['CLI_tests_total'] == 31 and swift['CLI_recorded_issues'] == 32 and swift['whole_job_conclusion'] == 'failure'
ui_selection = read(ROOT / 'verification/github-delivery-binary-export-and-ui/public-ui-axis-selection.json')
assert all(row(ROOT / item['path']) == item for item in ui_selection['canonical_sources'])
ui_host = {'schema': 1, 'status': 'nine axis host tests passed within a failed Swift host job',
    'run': swift['run'], 'job': swift['job'], 'commit': BASE, 'runner': swift['runner'],
    'Xcode': swift['Xcode'], 'Swift': swift['Swift'], 'SDK_tests_passed': 132,
    'new_axis_tests_passed': 9, 'update_tests_passed': 69, 'CLI_tests_total': 31, 'CLI_recorded_issues': 32,
    'whole_job_conclusion': 'failure', 'first_CLI_cause': swift['first_CLI_cause'],
    'later_VM_and_generated_consumer_steps': 'skipped', 'receipt': row(swift_dir / 'receipt.json'),
    'job_log': row(swift_dir / 'job.log'), 'native_UI_input_rendering_device_or_GA_accepted': False}
cli_dir = ROOT / 'verification/android-sdk-axis-pair-correction'
cli_review = read(cli_dir / 'source-review.json')
cli_sources = current_sources(cli_review['canonical_sources'])
profile = read(cli_dir / 'selected-profile.json')
previous_profile = read(cli_dir / 'previous-profile.json')
assert profile['id'] == cli_review['profile_id'] == 'mixer.android-source-pair.5'
assert distribution_digest(profile['sdk_files']) == cli_review['SDK_digest'] == 'bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0'
assert len(profile['sdk_files']) == 22 and len(profile['adapter_files']) == 23
assert {name for name in profile['sdk_files'] if profile['sdk_files'][name] != previous_profile['sdk_files'][name]} == {'Sources/MixerUI/Authoring.swift', 'Sources/MixerUI/Validation.swift'}
assert profile['adapter_files'] == previous_profile['adapter_files']
assert all(profile[k] == previous_profile[k] for k in ['wire', 'default_descriptor', 'adapter_compatibility_sha256'])
for name, expected in profile['sdk_files'].items():
    assert identity(ROOT / 'sdk' / name) == expected
for name, expected in profile['adapter_files'].items():
    path = ROOT / 'native/android' / ('engine/' + name if name.startswith('Sources/') else name)
    assert identity(path) == expected
assert cli_review['in_process_controls_passed'] == 8 and not cli_review['forbidden_actions']
cli = {'status': 'reviewed two SDK row refresh selected for fresh remote CLI validation',
    'profile_id': profile['id'], 'SDK_digest': cli_review['SDK_digest'], 'canonical_sources': cli_sources,
    'packet': cli_packet, 'source_review': row(cli_dir / 'source-review.json'),
    'changed_SDK_entries': cli_review['changed_SDK_entries'], 'other20_SDK_and23_adapter_rows_unchanged': True,
    'wire_descriptor_and_admission_logic_unchanged': True, 'legacy4_refusal_cases_added': True,
    'in_process_controls_passed': 8, 'full_Swift_CLI_and_Python_suites_pending_remote': True,
    'distribution_pair5_is_held_Android_candidate_v5': False, 'held_Android_actor_changed_or_retried': False,
    'native_runtime_release_or_GA_accepted': False}

visibility, dispatch = [read(p) for p in PUBLIC_INPUTS]
assert visibility['after']['id'] == 1437474527 and visibility['after']['full_name'] == 'snowdamiz/fieldlog'
assert visibility['after']['private'] is False and dispatch['repository_public_verified']
assert visibility['head'] == dispatch['head'] == '4062256839c192645a9ba271d4244f482f9aa811'
assert dispatch['dispatch_output'] == 'https://github.com/snowdamiz/fieldlog/actions/runs/40762789024'
assert dispatch['tests_result'] == 'pending'
fieldlog = {'schema': 1, 'at': at, 'scope': 'Sanitized visibility and single-dispatch observation only; no raw source, log or adoption draft copied',
    'latest_human_authorization': 'make repo pubilc and contineu', 'repository': 'snowdamiz/fieldlog',
    'repository_id': 1437474527, 'private': False, 'visibility_verified_at': visibility['at'],
    'code_commit': dispatch['head'], 'run_id': 40762789024, 'run_url': dispatch['dispatch_output'],
    'dispatches_observed': 1, 'dispatch_at': dispatch['at'], 'expected_host_tests': 26,
    'tests_result': 'pending', 'observed_host_test_passes': None,
    'sanitized_input_bindings': [{'name': p.name, **identity(p)} for p in PUBLIC_INPUTS],
    'prior_private_billing_failure_historical': True, 'prior_local_compiler_cleanup_hold_unchanged': True,
    'public_SDK_adoption_draft': {'files': 12, 'prepared_tests': 38, 'source_reviewed': True,
        'applied': False, 'executed': False, 'basis': 'coordinator observation; draft source excluded'},
    'native_UI_published_package_D_milestone_or_GA_accepted': False}

# All proof and canonical checks finish before any metadata write.
save(SELECTION, network)
save(FIELDLOG, fieldlog)
identity_lane = w['packages'][13]['identityProductionNetworkCI']
identity_lane['status'] = 'binary export and offline compilation passed; exact generated Rebar metadata correction selected for fresh isolated CI; product methods remain unrun'
identity_lane['binary_export_runtime_observation'] = network_packet
identity_lane['rebar_generated_output_source_selection'] = row(SELECTION)
identity_lane['current_canonical_files'] = network_sources + [workflow]
identity_lane['current_Swift_host_CI'] = ui_host
g['gates'][21]['identityProductionNetworkCI'] = deepcopy(identity_lane)
deadline = w['packages'][7]['empiricalCacheDeadlineCampaign']
deadline['status'] = 'closed after both full attempts; Corpus1 failed and Corpus2 unrun; feasibility unmet'
deadline['full_attempts_run'] = 2
deadline['full_attempts_remaining'] = 0
deadline['compiled_primary_finite_correction_pending_fresh_CI'] = False
deadline['actual_remote_review'] = cache_packet
deadline['actual_remote_receipt'] = row(cache_dir / 'receipt.json')
deadline['actual_profiles'] = profiles
deadline['all_final_logical_reservations_and_live_counters_zero'] = True
deadline['all11_commands_closed_and_remote_scratch_removed'] = True
deadline['failure_cleanup_empty_false_is_preserved_failure_oracle_not_resource_leak'] = True
deadline['replay_or_default_promotion_selected'] = False
deadline['architecture_comparison'] = {'status': 'prepared; under independent review',
    'candidate_directory': 'verification/swift-execution-architecture-comparison',
    'planned': ['existing lookup versus dense map', 'pin bitmap', 'common finite calibration'],
    'actual_full_attempts': 0, 'runtime_selection': False, 'workflow_installed': False,
    'candidate_packet_delivery_selected': False, 'source_custody_and_policy_review_pending': True}
g['gates'][1]['empiricalCacheDeadlineCampaign'] = deepcopy(deadline)
w['packages'][3]['publicTextFieldAxisHostCI'] = ui_host
g['gates'][5]['publicTextFieldAxisHostCI'] = deepcopy(ui_host)
w['packages'][1]['androidSourcePairAxisCorrection'] = cli
flow = w['packages'][16]['activePublicSDKFlow']
flow['publicMultilineHostCI'] = ui_host
flow['remote_public_host_observation'] = fieldlog
flow['remote_host_status_receipt'] = row(FIELDLOG)
flow['public_SDK_adoption_draft_state'] = fieldlog['public_SDK_adoption_draft']
remote = w['fieldlogRepository']['remoteDelivery']
old_remote = deepcopy(remote)
remote.update({'private': False, 'codeRevision': dispatch['head'], 'hostWorkflowRun': 40762789024,
    'hostTestsExecuted': None, 'expectedHostTests': 26,
    'state': 'public repository verified; one host workflow dispatch observed; result pending',
    'sanitizedStatusReceipt': row(FIELDLOG), 'priorPrivateHostWorkflow': old_remote})
for target, path in [(w['packages'][3], ui_host['receipt']['path']), (g['gates'][5], ui_host['receipt']['path']),
    (w['packages'][7], cache_packet['manifest']['path']), (g['gates'][1], cache_packet['manifest']['path']),
    (w['packages'][13], row(SELECTION)['path']), (g['gates'][21], row(SELECTION)['path']),
    (w['packages'][1], cli_packet['manifest']['path']), (w['packages'][16], row(FIELDLOG)['path'])]:
    evidence(target, path)
assert gate_states == {x['id']: x['status'] for x in g['gates']}
assert [p['state'] for p in old_w['packages']] == [p['state'] for p in w['packages']]
assert old_w['executionPolicy'] == w['executionPolicy'] and old_g['executionPolicy'] == g['executionPolicy']
assert old_w['verificationPolicy'] == w['verificationPolicy'] and old_g['verificationPolicy'] == g['verificationPolicy']
assert old_w['executionPause'] == w['executionPause']
save(CANONICAL[2], w, exclusive=False)
save(CANONICAL[3], g, exclusive=False)
checkpoint_text = (
    'Checkpoint `56ff14c` passes exact binary exports, locked dependency preparation, archive/restore, PostgreSQL isolation and offline compilation in the isolated network lane. '
    'It then rejects one fresh 895-byte Rebar `source.dag` after command 89; zero product methods ran, all 107 commands closed and all three owned containers were removed. '
    'The exact generated-output classification and opaque 64KiB retention correction passes 126 producer plus six independent pure methods and is selected only for fresh isolated CI. '
    'Both second-campaign full attempts are closed: 64M cache work exhausts at 64,000,001 after 41.737 seconds; 128M reaches the original instruction-fuel limit at 100,000,001 after 44.335 seconds. '
    'Neither finishes Corpus 1; Corpus 2 remains unrun. All final resources are zero, eleven commands closed and scratch was removed. No replay or default promotion is selected; the prepared Astra algorithm/resource-policy/implementation comparison remains under independent review, with zero runs and no installed workflow. '
    'The Swift host job passes 132 SDK tests including all nine axis cases and 69 update tests, then fails its 31 CLI tests with 32 issues from stale compiled source-pair4; later VM/generated-consumer steps were skipped. '
    'Reviewed source-pair5 refreshes only two SDK rows and passes eight in-process controls; full CLI/Python validation remains pending. This distribution ID does not authorize the held Android candidate v5. '
    'The user authorized public FieldLog publication: repository visibility is verified and one 26-test host run is dispatched at `4062256`, with results pending. The 12-file/38-test adoption draft is source-reviewed but unapplied and unexecuted. '
    'All native, custody, UnitA and GA holds remain; gates stay 8 running, 30 planned and 0 verified. '
    'Bindings and limits are in [the checkpoint receipt](verification/github-delivery-source-pair-and-rebar/checkpoint.json).')
for path in CANONICAL[:2]:
    prior = path.read_text()
    anchor = 'Checkpoint `fb7c7f2` verified'
    assert anchor in prior and 'Checkpoint `56ff14c` passes' not in prior
    path.write_text(prior.replace(anchor, checkpoint_text + '\n\n' + anchor, 1))
assert identity(ROOT / '.github/workflows/hosted.yml') == protected['.github/workflows/hosted.yml']
assert identity(ROOT / 'hosted/lib/mixer_hosted/browser_auth/store.ex') == protected['hosted/lib/mixer_hosted/browser_auth/store.ex']
assert read(CANONICAL[2])['packages'][13]['identityProductionNetworkCI'] == read(CANONICAL[3])['gates'][21]['identityProductionNetworkCI']
assert read(CANONICAL[2])['packages'][7]['empiricalCacheDeadlineCampaign'] == read(CANONICAL[3])['gates'][1]['empiricalCacheDeadlineCampaign']
save(OUT / 'checkpoint.json', {'schema': 1, 'at': at,
    'command': ['python3', '-B', 'verification/github-delivery-source-pair-and-rebar/prepare-checkpoint.py'],
    'tool': {'python': sys.version}, 'source': {'base_commit': BASE, 'base_tree': TREE,
        'basis': 'coordinator-supplied delivery base and sealed independent review; no new Git subprocess'},
    'script': row(Path(__file__)), 'scope': 'offline metadata binding only; saved reviews were not executed',
    'preparation_failures_preserved': [{'stage': 'before any metadata write',
        'failure': 'initial preflight used JSON packet digest for the Android distribution profile; assertion refused the mismatch',
        'correction': 'use the reviewed path-NUL-SHA256-newline distribution algorithm; retain canonical JSON digest for network manifests',
        'product_runtime_or_remote_actions': False}],
    'proof_packets': [network_packet, correction_packet, review_packet, cache_packet, cli_packet],
    'proof_member_files_rehashed': 625, 'current_network_sources': network_sources,
    'network_selection': row(SELECTION), 'CLI_source_selection': cli,
    'Swift_host_observation': ui_host, 'FieldLog_sanitized_observation': row(FIELDLOG),
    'cache_campaign': {'run_id': 40755988137, 'review_checks_passed': 335,
        'full_attempts': 2, 'full_attempts_remaining': 0, 'profiles': profiles,
        'all_final_resources_zero': True, 'all11_commands_closed_and_scratch_removed': True,
        'architecture_comparison': deadline['architecture_comparison']},
    'protected_sources_unchanged': protected, 'before_metadata': before_metadata,
    'after_metadata': [row(p) for p in CANONICAL],
    'GA_status_counts': {'running': 8, 'planned': 30, 'verified': 0},
    'history_execution_policy_pause_package_states_and_all_gate_statuses_preserved': True,
    'new_GitHub_API_process_compiler_custody_native_UI_capture_actions': False,
    'unreviewed_architecture_packet_read_copied_installed_or_selected': False,
    'private_FieldLog_sources_logs_or_draft_copied': False,
    'commit_push_or_dispatch_performed': False, 'elapsed_seconds': round(time.monotonic() - started, 3)})
print(json.dumps({'proof_member_files_rehashed': 625, 'network_sources_bound': 3,
    'CLI_sources_bound': 4, 'SDK_adapter_profile_rows_bound': 45, 'new_runtime_actions': 0,
    'GA_status_counts': {'running': 8, 'planned': 30, 'verified': 0}}))
