"""Bind the actual failures, narrow corrections and source-reviewed public UI slice."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal

signal.alarm(50)
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
BASE = 'fb7c7f20f8a308424ef4b7092d19d3d4de2c7627'


def read(path):
    return json.loads(path.read_bytes())


def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def audit(path, digest, count):
    binding = row(path)
    assert binding['sha256'] == digest
    files = read(path)['files']
    assert len(files) == count
    total = 0
    for name, expected in files.items():
        member = path.parent / name
        assert member.resolve().is_relative_to(path.parent.resolve())
        actual = row(member)
        assert {k: actual[k] for k in ('bytes', 'sha256')} == expected, name
        total += actual['bytes']
        assert total <= 256 * 1024 * 1024
    return {'manifest': binding, 'files_rehashed': count, 'bytes_rehashed': total}


previous = ROOT / 'verification/github-delivery-runtime-followup'
network_observation = audit(previous / 'network-review/packet-manifest.json',
    '4ccc5ebe10600086473c96afd9aabf68ed63c46068419f5e599ac747f0d1800c', 256)
cache_observation = audit(previous / 'cache-deadline-review/seal.json',
    'c15eb4a779600d78adcb2b7e99bbe24c30bfed38d6cf3e087e431134a10457a8', 45)
network_dir = ROOT / 'verification/identity-network-binary-export-independent'
network_review = audit(network_dir / 'packet-manifest.json',
    '4741db79485adb733506ab95ff89f4e79275d5049b04d9965318d9d03828cb6d', 13)
decision = read(network_dir / 'decision.json')
assert not decision['runtime_acceptance'] and not decision['findings']
sources = []
for name, expected in decision['canonical_sources'].items():
    actual = row(ROOT / name)
    assert {k: actual[k] for k in ('bytes', 'sha256')} == expected
    sources.append(actual)
network = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'baseline': BASE,
    'status': 'reviewed byte-transparent export correction selected for fresh isolated identity CI',
    'canonical_sources': sources, 'independent_decision': row(network_dir / 'decision.json'),
    'independent_review': network_review, 'canonical_controls': 111, 'independent_controls': 12,
    'prior_run': 40746908101, 'prior_review': network_observation,
    'actual_prepare_mount_policy_Rebar_and_bootstrap_passed': True,
    'prior_failure': 'Unicode standard output transcoded the pinned Hex binary; exact Latin1-to-UTF8 length and SHA256 model matches observation',
    'prior_raw_failed_export_retained': False, 'prior_complete_stream_flags_retained': True,
    'prior_exact_prepare_cleanup_verified': True, 'prior_product_methods_run': 0,
    'correction': 'Checked Latin1 stdout and checked binary write; retain only bounded public Hex/Rebar exports before host length/SHA rejection',
    'pre_persistence_transport_exception_may_leave_no_capture': True,
    'images_metadata177_product_mounts_limits_and_checksums_unchanged': True,
    'remote_execution_selected': True, 'actual_corrected_runtime_or_GA_accepted': False}
network_path = ROOT / 'verification/console-session-and-checkout-root-review/identity-network-binary-selection.json'
save(network_path, network)

cache_dir = ROOT / 'verification/swift-cache-deadline-campaign-v2-finite-correction'
cache_seal = audit(cache_dir / 'seal.json',
    'd6bf688b0b1333bb10a5c946c14febedbbdac463a884d446da9f5460b66ebdde', 18)
cache_review_path = ROOT / 'verification/swift-cache-deadline-finite-root-review/receipt.json'
cache_review = read(cache_review_path)
assert cache_review['controls_passed'] == 19 and not cache_review['forbidden_process_socket_custody_events']
workflow = ROOT / '.github/workflows/swift-cache-deadline-campaign-v2.yml'
old_selection = read(ROOT / 'verification/swift-semantic-adapter-root-review/cache-deadline-campaign-selection.json')
assert row(workflow) == old_selection['workflow']
workflow.write_bytes((cache_dir / 'workflow.yml').read_bytes())
cache = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'baseline': BASE,
    'status': 'literal finite-test expectation corrected; full campaign still awaits execution',
    'prior_run': 40747548560, 'prior_review': cache_observation,
    'prior_primary_compiled': True, 'prior_finite_passed': 3, 'prior_finite_failed': 1,
    'prior_full_attempts': 0, 'prior_all_five_commands_closed_and_scratch_removed': True,
    'correction': 'Only the generated finite-test expected tuple deadline changes from literal30000 to literal60000; runtime source and pending custody guard unchanged',
    'packet_seal': cache_seal['manifest'], 'review': row(cache_review_path),
    'campaign': row(cache_dir / 'campaign.py'), 'workflow': row(workflow), 'pure_controls_passed': 19,
    'maximum_full_attempts': 2, 'full_attempts_run': 0, 'full_attempts_remaining': 2,
    'primary': {'residents': 256, 'cache_work': 64000000, 'runtime_and_WASI_deadline_ms': 60000},
    'conditional': {'residents': 256, 'cache_work': 128000000, 'runtime_and_WASI_deadline_ms': 60000,
        'requires': 'actual primary CacheWork exhaustion with preserved cause, zero resources and proven command closure'},
    'instruction_fuel': 100000000, 'driver_seconds': 540, 'full_external_seconds': 200, 'workflow_minutes': 15,
    'exceptional_unproven_command_retains_scratch_and_stops': True,
    'same_full_artifact_two_corpus_one_owner_and11_field_oracle': True,
    'remote_execution_selected': True, 'actual_feasibility_or_GA_accepted': False,
    'manual_dispatch_pending_API_reset_UTC': '2026-10-28T19:37:21Z',
    'next_if_milestone_unmet': 'Astra comparison of algorithm, resource policy and different implementation'}
cache_path = ROOT / 'verification/swift-semantic-adapter-root-review/cache-deadline-finite-selection.json'
save(cache_path, cache)

ui_dir = ROOT / 'verification/public-ui-text-field-axis-independent'
ui_receipt = row(ui_dir / 'receipt.json')
assert ui_receipt['sha256'] == '7a85399259a547db365c42794736529613cf08db887e08a545925891ab462e00'
ui_review = read(ui_dir / 'receipt.json')
assert not ui_review['blocking_findings']
ui_sources = []
for name, digest in ui_review['reviewed_source_sha256'].items():
    actual = row(ROOT / name)
    assert actual['sha256'] == digest
    ui_sources.append(actual)
assert len(ui_sources) == 6
ui = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'baseline': BASE,
    'status': 'six-file public multiline source slice reviewed and selected for ordinary remote Engine CI',
    'canonical_sources': ui_sources, 'independent_review': ui_receipt,
    'root_source_review': 'Reviewed all six files and current host/reconciler/portable consumer paths; no blocking source finding',
    'prepared_UI_tests': 7, 'prepared_Apple_host_tests': 2, 'executable_tests_run': 0,
    'default_horizontal_schema1_wire_unchanged': True,
    'portable_default_horizontal_only': True, 'Apple_default_both_axes_with_explicit_caller_restrictions_preserved': True,
    'native_packet_appearance_Android_and_default_guest_vertical_rejected': True,
    'named_unlock': 'Preserve multiline title behavior when a separately qualified FieldLog revision adopts the public Apple renderer',
    'FieldLog_pin_or_private_sources_changed': False,
    'pending': ['remote compiler and nine tests', 'native editing/wrapping/focus/IME/accessibility',
        'shared-theme integration', 'Android multiline support', 'immutable separate FieldLog adoption', 'physical and GA gates'],
    'native_runtime_or_GA_accepted': False, 'holds_unchanged': True}
ui_path = OUT / 'public-ui-axis-selection.json'
save(ui_path, ui)

wpath, gpath = ROOT / 'work-graph.json', ROOT / 'gates/ga.json'
w, g = read(wpath), read(gpath)
assert Counter(x['status'] for x in g['gates']) == {'running': 8, 'planned': 30}
identity = w['packages'][13]['identityProductionNetworkCI']
identity['status'] = 'actual prepare mounts/Rebar/bootstrap passed; binary export transcoding identified; reviewed byte-transparent correction selected for fresh CI'
identity['execution_amendment_runtime_observation'] = network_observation
identity['binary_export_source_selection'] = network
identity['current_canonical_files'] = sources + [row(ROOT / '.github/workflows/identity-network.yml')]
g['gates'][21]['identityProductionNetworkCI'] = identity
deadline = w['packages'][7]['empiricalCacheDeadlineCampaign']
deadline['status'] = cache['status']
deadline['failed_pre_full_attempt'] = cache_observation
deadline['root_selection'] = row(cache_path)
deadline['full_attempts_run'] = 0
deadline['compiled_primary_finite_correction_pending_fresh_CI'] = True
g['gates'][1]['empiricalCacheDeadlineCampaign'] = deadline
w['packages'][3]['publicTextFieldAxisCandidate'] = row(ui_path)
g['gates'][5]['publicTextFieldAxisCandidate'] = row(ui_path)
w['packages'][16]['activePublicSDKFlow']['publicMultilinePrerequisite'] = row(ui_path)
for path, value in [(wpath, w), (gpath, g)]:
    path.write_text(json.dumps(value, indent=2) + '\n')
checkpoint = ('Checkpoint `fb7c7f2` verified the isolated preparation mount policy, exclusive Rebar transfer and complete bootstrap. '
    'Its next failure is binary export: Unicode standard output changed the pinned Hex bytes, confirmed by an exact transformed size/hash match. '
    'Preparation cleanup is verified; dependency compilation and both product network methods remain unrun. '
    'The byte-transparent export and bounded rejected-public-byte retention correction passes 111 canonical and 12 independent pure checks and is selected for fresh CI. '
    'The second cache campaign compiled its primary profile but stopped at a stale finite test expecting 30 seconds instead of the selected 60; three controls passed, one failed, and zero full attempts ran. '
    'All five command groups closed and scratch was removed. A literal test-expectation correction passes 19 pure checks, preserving runtime budgets, the original two-call oracle and the command-custody guard. '
    'A six-file public multiline text-field addition has source review and nine prepared tests; Apple admission is explicit and unsupported consumers reject vertical fields. Runtime, shared-theme and private FieldLog adoption remain pending. '
    'FieldLog’s private workflow remains blocked before its 26 host tests by GitHub account billing/spending, and its earlier local compiler cleanup is still unverified. '
    'Shared GitHub API quota delays manual dispatch and further inspection until the reported 19:37:21 UTC reset. All native/custody/UnitA holds and all GA boundaries remain unchanged.')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name
    text = path.read_text()
    anchor = 'Checkpoint `cc350d3` passes'
    assert anchor in text and 'Checkpoint `fb7c7f2` verified' not in text
    path.write_text(text.replace(anchor, checkpoint + '\n\n' + anchor, 1))
save(OUT / 'selection.json', {'schema': 1, 'baseline': BASE, 'network': row(network_path),
    'cache': row(cache_path), 'public_UI': row(ui_path), 'private_app_raw_evidence_excluded': True,
    'raw_account_quota_observations_retained_locally_only': True})
print(json.dumps({'network_pure_checks': 123, 'cache_pure_checks': 19,
    'UI_tests_prepared_but_unrun': 9, 'full_cache_attempts': 0, 'GA_verified': 0}))
