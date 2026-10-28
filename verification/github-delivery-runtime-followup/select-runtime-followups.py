"""Select reviewed remote follow-ups and record a sanitized private-app status."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal

signal.alarm(50)
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent


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
    assert row(path)['sha256'] == digest
    value = read(path)
    assert len(value['files']) == count
    for name, expected in value['files'].items():
        member = path.parent / name
        assert member.resolve().is_relative_to(path.parent.resolve())
        actual = row(member)
        assert {k: actual[k] for k in ['bytes', 'sha256']} == expected
    return row(path)


network_dir = ROOT / 'verification/identity-network-execution-amendment-independent'
manifest = audit(network_dir / 'packet-manifest.json',
    '06b88b237855842dab6fea63410ba4c532e7c83bac2ad6692a59688247d8ac71', 13)
decision = read(network_dir / 'decision.json')
assert not decision['blocking_findings'] and not decision['runtime_acceptance']
assert decision['canonical_controls']['tests'] == 103 and decision['canonical_controls']['passed']
assert decision['independent_controls']['tests'] == 16 and decision['independent_controls']['passed']
canonical = []
for name, expected in decision['canonical_bindings'].items():
    actual = row(ROOT / name)
    assert {k: actual[k] for k in ['bytes', 'sha256']} == expected
    canonical.append(actual)
network = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'reviewed bounded tooling execution amendment selected for one fresh remote identity attempt',
    'baseline': 'cc350d3303ca71c5d57e87846f6a61304b658fa7', 'canonical_sources': canonical,
    'independent_decision': row(network_dir / 'decision.json'), 'independent_manifest': manifest,
    'canonical_controls': 103, 'independent_controls': 16, 'review_packet_members_rehashed': 13,
    'workspace_bytes': 1006632960, 'executable_tooling_bytes': 67108864,
    'workspace_partition_total_bytes': 1073741824, 'full_workspace_execution_allowed': False,
    'exclusive_size_and_SHA512_verified_Rebar_copy_before_execution': True,
    'actual_mount_policy_evidence_required': True, 'same177_product_blobs_and_image_pins': True,
    'remote_execution_selected': True, 'remote_attempts_run': 0,
    'runtime_or_GA_acceptance': False, 'holds_unchanged': True}
network_path = ROOT / 'verification/console-session-and-checkout-root-review/identity-network-execution-selection.json'
save(network_path, network)

cache_dir = ROOT / 'verification/swift-cache-deadline-campaign-v2-correction'
cache_seal = audit(cache_dir / 'seal.json',
    'd8079bacfbb5fee222ac55354ad5a9aaa2a320327d50acd181426fea0d46a2d3', 15)
review = read(ROOT / 'verification/swift-cache-deadline-campaign-root-review/receipt.json')
assert review['controls_passed'] == 17 and not review['forbidden_process_socket_custody_events']
assert review['remote_execution_selected'] and review['seal'] == cache_seal
workflow = ROOT / '.github/workflows/swift-cache-deadline-campaign-v2.yml'
with workflow.open('xb') as stream:
    stream.write((cache_dir / 'workflow.yml').read_bytes())
cache = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'corrected second campaign selected for one manual dispatch; max two conditionally admitted full attempts',
    'packet_seal': cache_seal, 'review': row(ROOT / 'verification/swift-cache-deadline-campaign-root-review/receipt.json'),
    'campaign': row(cache_dir / 'campaign.py'), 'workflow': row(workflow),
    'pure_controls_passed': 17, 'maximum_full_attempts': 2, 'full_attempts_run': 0,
    'primary': {'residents': 256, 'cache_work': 64000000, 'runtime_and_WASI_deadline_ms': 60000},
    'conditional': {'residents': 256, 'cache_work': 128000000, 'runtime_and_WASI_deadline_ms': 60000,
        'requires': 'first actual CacheWork exhaustion with preserved cause, zero resources, exact group absence and proven terminal command closure'},
    'instruction_fuel': 100000000, 'driver_seconds': 540, 'full_external_seconds': 200, 'workflow_minutes': 15,
    'original_two_corpus_one_owner_11_field_oracle_unchanged': True,
    'exceptional_unproven_command_retains_scratch_and_stops': True,
    'if_milestone_unmet': 'Astra comparison of algorithm, resource-policy and different-implementation alternatives',
    'first_campaign_closed_fifth_unselected': True, 'remote_execution_selected': True,
    'actual_feasibility_or_GA_accepted': False, 'holds_unchanged': True}
cache_path = ROOT / 'verification/swift-semantic-adapter-root-review/cache-deadline-campaign-selection.json'
save(cache_path, cache)

fieldlog = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'scope': 'Sanitized integration status only; private source/diffs/raw workflow evidence excluded from public Mixer delivery',
    'user_authorization': 'Create private FieldLog repo and run host CI',
    'repository': 'snowdamiz/fieldlog', 'repository_id': 1437474527, 'private': True,
    'code_commit': '70f3aa1d28f29e7c327a17fd46199480d41ca749',
    'code_tree': '8d962e2f3b52aad4b417f98b5553bc5762fde908',
    'run_id': 40744921829, 'run_attempt': 1, 'job_id': 123016069558,
    'status': 'workflow blocked before runner assignment by GitHub account payment or spending restriction',
    'runner_assigned': False, 'steps_executed': 0, 'artifacts': 0, 'expected_host_tests': 26, 'observed_host_tests': 0,
    'public_Mixer_pin': 'd8c6965a277ca21e685f3ef9e0f68a7d59b46156',
    'new_remote_compiler_or_SDK_fetch_executed': False,
    'retry_or_billing_change_performed': False,
    'prior_local_compiler_cleanup_unverified_and_held': True,
    'native_or_published_release_or_GA_accepted': False}
fieldlog_path = ROOT / 'verification/fieldlog-public-sdk-root-review/private-host-ci-observation.json'
save(fieldlog_path, fieldlog)

wpath, gpath = ROOT / 'work-graph.json', ROOT / 'gates/ga.json'
w, g = read(wpath), read(gpath)
identity = w['packages'][13]['identityProductionNetworkCI']
identity['status'] = 'ordinary Engine/Phoenix accepted; isolated image prerequisites passed then Rebar EACCES; reviewed bounded tooling execution correction selected for fresh CI'
identity['execution_amendment_source_acceptance'] = network
identity['current_canonical_files'] = canonical
g['gates'][21]['identityProductionNetworkCI'] = identity
deadline = w['packages'][7]['empiricalCacheDeadlineCampaign']
deadline['status'] = cache['status']
deadline['root_selection'] = row(cache_path)
deadline['remote_CI_selected'] = True
g['gates'][1]['empiricalCacheDeadlineCampaign'] = deadline
w['packages'][16]['activePublicSDKFlow']['remote_host_preparation'] = fieldlog
w['packages'][16]['activePublicSDKFlow']['remote_host_status_receipt'] = row(fieldlog_path)
for path, value in [(wpath, w), (gpath, g)]:
    path.write_text(json.dumps(value, indent=2) + '\n')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name
    text = path.read_text()
    text = text.replace('A bounded executable tooling mount carved from the existing workspace allowance is under review.',
        'A bounded executable tooling mount carved from the existing workspace allowance passes 103 canonical and 16 independent pure controls and is selected for fresh remote CI.', 1)
    text = text.replace('FieldLog has a prepared shared task editor and nine new tests; the user approved its private separate repository and one remote host run.',
        'FieldLog’s shared task editor and nine new tests are pushed to its private separate repository. GitHub blocked its first workflow before runner assignment because of an account payment or spending restriction; none of the 26 host tests ran. The corrected cache experiment runner passes 17 pure controls and preserves unresolved command custody on exceptional exits.', 1)
    path.write_text(text)
save(OUT / 'selected-followups.json', {'network': row(network_path), 'cache': row(cache_path),
    'private_app_sanitized_status': row(fieldlog_path), 'private_app_full_packet_excluded': True})
print(json.dumps({'network_controls': 119, 'cache_controls': 17, 'selected_for_remote_CI': True,
                  'FieldLog_host_tests_executed': 0, 'private_source_excluded': True}))
