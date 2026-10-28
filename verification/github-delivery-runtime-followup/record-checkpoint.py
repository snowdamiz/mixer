"""Reconcile sealed observations without executing retained artifact code."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal
import sys

signal.alarm(50)
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
BASE = 'cc350d3303ca71c5d57e87846f6a61304b658fa7'
OLD = ROOT / 'verification/github-delivery-blocker-campaign'


def read(path):
    return json.loads(path.read_bytes())


def row(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def audit(path, digest=None, count=None):
    binding = row(path)
    if digest:
        assert binding['sha256'] == digest
    value = read(path)
    files = value['files']
    assert isinstance(files, dict) and 0 < len(files) <= 1000
    if count:
        assert len(files) == count
    total = 0
    for name, expected in files.items():
        relative = Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        member = path.parent / relative
        assert member.resolve().is_relative_to(path.parent.resolve())
        observed = row(member)
        assert {k: observed[k] for k in ('bytes', 'sha256')} == expected, name
        total += observed['bytes']
        assert total <= 256 * 1024 * 1024
    return {'manifest': binding, 'files_rehashed': len(files), 'bytes_rehashed': total,
            'declared_tree_sha256': value.get('tree_digest_sha256')}


assert not (OUT / 'observed-checkpoint.json').exists(), 'write once'
network = audit(OLD / 'network-review/packet-manifest.json', count=213)
assert network['declared_tree_sha256'] == '5fdd6d383517487f5df12cbd81086da7e8c0e713fd63fcbd026ce78389b2e293'
cache = audit(OLD / 'cache-campaign-review/seal.json',
              '4dcf3f8bf9533d0234a5966d111b1d3373299cbfb816ab871d0764c0a1024cec', 108)
cache_ci = audit(OLD / 'cache-controls-pass-review/packet-manifest.json',
                 '64f3c49af31f21965a7d6c842c8a2823ea26d4846a57a9e7e9988b9bc93d16db', 46)
phoenix = audit(OLD / 'phoenix-pass-review/packet-manifest.json',
                '661f52f30cd1e24661e7a42e7d9a10c9042070095c4526fef855703a3ff693ab', 176)
n = read(OLD / 'network-review/decision.json')
c = read(OLD / 'cache-campaign-review/verified-results.json')
assert n['delivery_revision'] == c['head'] == BASE
assert n['run_id'] == 40740023326 and n['cleanup']['exact_absence_verified']
assert c['fullAttempts'] == 4 and c['hostFeasibilityProfiles'] == 0
assert c['allConsumingCleanupAndOwnedGroupChecksPassed'] and c['originalHarnessControlsPassed'] == 4
for folder, run in [('cache-controls-pass-review', 40740023152), ('phoenix-pass-review', 40740023060)]:
    receipt = read(OLD / folder / 'receipt.json')
    assert receipt['source_revision'] == BASE and receipt['run_id'] == run
    assert not receipt['artifact_code_executed']

observed = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'revision': BASE,
    'python': sys.version, 'command': 'python3 -B verification/github-delivery-runtime-followup/record-checkpoint.py',
    'scope': 'Root audit of sealed source/data evidence; no retained artifact code or runtime executed',
    'network': {**network, 'run_id': 40740023326,
        'decision': row(OLD / 'network-review/decision.json'),
        'status': 'tools, OpenSSL and selected CA prerequisites passed; Rebar direct execution failed EACCES',
        'actual_prior_mount_flags_retained': False, 'source_supported_noexec_inference': True,
        'owned_prepare_cleanup_verified': True, 'product_methods_executed': 0,
        'next_selection': 'Carve 64MiB executable tooling tmpfs from existing 1GiB workspace, observe exact mount policy, copy verified Rebar across filesystems exclusively before execution; fresh remote CI after focused review'},
    'cache_campaign': {**cache, 'run_id': 40740382537, 'full_attempts': 4,
        'host_feasible_profiles': 0, 'closed': True, 'fifth_selected': False,
        'result': row(OLD / 'cache-campaign-review/verified-results.json'),
        'profiles': [{k: p[k] for k in ['name', 'residents', 'cacheWorkAllowance', 'firstFailureKind',
            'firstFailureResource', 'instructionsAtFailure', 'cacheWorkAtFailure', 'corpus1Complete', 'corpus2',
            'consumingCleanup', 'originalCleanupEmptyFlag', 'originalFinalFailurePreserved', 'processGroupEmpty']}
            for p in c['profiles']],
        'RSS_comparison_available': False, 'timing_speedup_claim': False,
        'next_selection': '256 residents, 64M work, coherent cumulative Runtime/WASI 60s; only verified CacheWork permits one conditional128M attempt;100M fuel and memory/capability/oracle safeguards unchanged'},
    'engine': {**cache_ci, 'run_id': 40740023152, 'passed_jobs': 6,
        'cache_runner_controls_passed': 32, 'current_fixture_commands': 103,
        'review': row(OLD / 'cache-controls-pass-review/receipt.json'),
        'historical_fixture_receipt_excluded': True, 'original_unknown_failure_cause_resolved': False},
    'phoenix': {**phoenix, 'run_id': 40740023060, 'passed': 697, 'skipped': 2,
        'review': row(OLD / 'phoenix-pass-review/receipt.json'), 'source_files': 181, 'frozen_product_files': 177,
        'required_sparse_readset_files': 194, 'current_receipts': 4, 'lifecycle_methods': 9,
        'HTTP2_methods': 5, 'HTTP2_wire_cases': 7, 'scoped_postgres_and_scratch_cleanup': True},
    'holds_unchanged': True, 'native_or_GA_acceptance': False,
}
save(OUT / 'observed-checkpoint.json', observed)

wpath, gpath = ROOT / 'work-graph.json', ROOT / 'gates/ga.json'
w, g = read(wpath), read(gpath)
assert len(w['packages']) == 18 and len(g['gates']) == 38
assert Counter(x['status'] for x in g['gates']) == {'running': 8, 'planned': 30}
selection = row(OUT / 'observed-checkpoint.json')
capacity = w['packages'][7]['empiricalCacheCapacityCampaign']
capacity.update(status='closed after four actual attempts; no host-feasible profile',
                full_workload_attempts_run=4, fifth_attempt_implemented_or_selected=False,
                remote_CI_selected=False, remote_CI_integration_pending_focused_review=False,
                observed_result=selection, next_candidate_residents=256, retired_candidate_residents=128)
g['gates'][1]['empiricalCacheCapacityCampaign'] = capacity
deadline = {'schema': 1, 'status': 'second bounded experiment selected; corrected runner source review pending',
    'basis': selection, 'residents': 256, 'primary_cache_work': 64000000,
    'conditional_cache_work': 128000000, 'conditional_rule': 'first actual CacheWork exhaustion with original cause, complete resource emptiness and proven command closure',
    'runtime_and_WASI_cumulative_deadline_ms': 60000, 'instruction_fuel': 100000000,
    'maximum_full_attempts': 2, 'full_attempts_run': 0,
    'named_unlock': 'both original full corpus calls match all11 native fields on one initialized owner then consume to zero resources',
    'next_if_milestone_unmet': 'Astra architecture comparison of algorithm, resource policy and different implementation',
    'production_or_GA_accepted': False, 'holds_unchanged': True}
w['packages'][7]['empiricalCacheDeadlineCampaign'] = deadline
g['gates'][1]['empiricalCacheDeadlineCampaign'] = deadline
identity = w['packages'][13]['identityProductionNetworkCI']
identity['status'] = 'ordinary Engine/Phoenix evidence accepted; isolated prerequisites pass then Rebar EACCES; bounded tooling execution correction under review'
identity['image_amendment_remote_observation'] = observed['network']
identity['preceding_Engine_CI'] = identity['current_Engine_CI']
identity['current_Engine_CI'] = observed['engine']
identity['current_Phoenix_CI'] = observed['phoenix']
g['gates'][21]['identityProductionNetworkCI'] = identity
flow = w['packages'][16]['activePublicSDKFlow']
flow['remote_host_preparation'] = {
    'status': 'user approved private snowdamiz/fieldlog creation, selected app push and one manual host CI; bounded delivery active',
    'user_authorization': 'Create private FieldLog repo and run host CI',
    'repository': 'snowdamiz/fieldlog', 'private_required': True, 'expected_host_tests': 26,
    'new_presentation_tests': 9, 'public_Mixer_pin_unchanged': 'd8c6965a277ca21e685f3ef9e0f68a7d59b46156',
    'new_host_runtime_observed': False, 'prior_local_cleanup_unverified_hold_remains': True,
    'native_runtime_or_published_release_qualification': False}
for path, value in [(wpath, w), (gpath, g)]:
    path.write_text(json.dumps(value, indent=2) + '\n')

checkpoint = ('Checkpoint `cc350d3` passes all six Engine jobs and ordinary Phoenix with697 tests and two explicit skips. '
    'The cache runner passes32 controls and103 current fixture commands; this does not diagnose the earlier unknown cleanup error. '
    'The isolated image now passes tool/OpenSSL/CA prerequisites, then Rebar fails with EACCES; exact preparation cleanup is verified and product network methods remain unrun. '
    'A bounded executable tooling mount carved from the existing workspace allowance is under review. '
    'All four full cache experiments ran: none completed Corpus1, and Corpus2 remained unrun. '
    'The256-entry profile sharply reduced repeated decoding and reached the30-second deadline with cache credits remaining;128 entries stopped earlier on cache work. '
    'The first campaign is closed without feasibility or speedup acceptance. The next selected comparison keeps256 entries and100M instruction fuel, raises cumulative Runtime/WASI deadlines to60 seconds, and permits one work-budget increase only after actual CacheWork exhaustion and verified cleanup. '
    'FieldLog has a prepared shared task editor and nine new tests; the user approved its private separate repository and one remote host run. '
    'Its previous local dependency-fetch timeout remains unverified for cleanup and further local compiler work stays held. '
    'All native, custody and UnitA holds remain; no GA gate is verified.')
checkpoint = checkpoint.replace('with697', 'with 697').replace('passes32', 'passes 32').replace('and103', 'and 103')
checkpoint = checkpoint.replace('Corpus1', 'Corpus 1').replace('Corpus2', 'Corpus 2').replace('The256', 'The 256')
checkpoint = checkpoint.replace('the30', 'the 30').replace(';128', '; 128').replace('keeps256', 'keeps 256')
checkpoint = checkpoint.replace('and100M', 'and 100M').replace('to60', 'to 60')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name
    text = path.read_text()
    anchor = 'Checkpoint `0b99469d`'
    assert anchor in text and 'Checkpoint `cc350d3` passes' not in text
    text = text.replace(anchor, checkpoint + '\n\n' + anchor, 1)
    path.write_text(text)
print(json.dumps({'packets_rehashed': 4, 'files_rehashed': sum(v['files_rehashed'] for v in [network, cache, cache_ci, phoenix]),
                  'full_cache_attempts': 4, 'host_feasible_profiles': 0, 'gate_counts': dict(Counter(x['status'] for x in g['gates']))}))
