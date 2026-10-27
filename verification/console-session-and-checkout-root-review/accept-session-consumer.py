"""One-shot root custody/acceptance of the closed frontend slice and terminal CI."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / 'session-consumer-acceptance.json'

def row(path):
    assert path.is_file() and not path.is_symlink(), path
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def read(path):
    return json.loads((ROOT / path).read_bytes())

def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

assert not DEST.exists(), 'One-shot; do not replay'
producer = 'verification/console-browser-session-consumer'
independent = 'verification/console-browser-session-consumer-independent'
packets = []
for directory, seal_name, key, relative in [(producer, 'seal.json', 'files', True), (independent, 'review-seal.json', 'members', False)]:
    seal = read(directory + '/' + seal_name)
    members = []
    for item in seal[key]:
        name = PurePosixPath(item['path'])
        assert not name.is_absolute() and '..' not in name.parts
        path = ROOT / directory / name if relative else ROOT / name
        assert path.is_relative_to(ROOT / directory)
        actual = row(path)
        assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256'], path
        members.append(actual)
    members.append(row(ROOT / directory / seal_name))
    assert len({r['path'] for r in members}) == len(members)
    assert {r['path'] for r in members} == {str(p.relative_to(ROOT)) for p in (ROOT / directory).rglob('*') if p.is_file()}
    packets.append({'directory': directory, 'members': members})
assert len(packets[0]['members']) == 145 and len(packets[1]['members']) == 28
manifest = read(producer + '/source-manifest.json')
assert len(manifest['files']) == 65
assert manifest['source_digest_sha256'] == '7cd673b6b2c729c60586b0506ef57e0d063183046c76ffab5c44f6b3f88314b8'
for item in manifest['files']:
    assert row(ROOT / item['path']) == item
    frozen = row(ROOT / producer / 'frozen-inputs' / item['path'])
    assert frozen['bytes'] == item['bytes'] and frozen['sha256'] == item['sha256']
producer_receipt = read(producer + '/receipt.json')
review = read(independent + '/review-receipt.json')
assert review['source_files_and_product_unchanged'] and review['unique_probe_ids_with_final_successful_observation'] == 42
assert review['actionable_product_findings'] == []
assert [r['exit_code'] for r in review['runs']] == [0, 0, 1, 0]
assert all(r['captured_group_absent'] and r['unchanged'] for r in review['runs'])
assert review['cleanup']['scratch_removed'] and review['cleanup']['scratch_node_modules_symlink_removed_without_touching_target']
assert review['count_attribution']['no_12_of_12_same_run_claim']
assert producer_receipt['producer_validation']['complete_console_regression']['outer_pass'] == 149
assert len(producer_receipt['owned_files']) == 8
for item in producer_receipt['owned_files']:
    assert row(ROOT / item['path']) == item
value = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
    'status': 'accepted-closed-frontend-source-and-host-slice', 'implementation_accepted': True,
    'source_revision': manifest['revision'], 'tracked_tree': manifest['tracked_tree'],
    'source_digest': manifest['source_digest_sha256'], 'source_files_verified': 65,
    'owned_files': producer_receipt['owned_files'], 'packets': packets,
    'producer_validation': producer_receipt['producer_validation'],
    'independent_review': row(ROOT / independent / 'review-receipt.json'),
    'independent_attribution': review['count_attribution'], 'unique_probes_with_final_success': 42,
    'scope': 'Strict fixed session response decoder, expiry/epoch fencing, cookie-client admission, Solid visibility and cross-tab invalidation; synthetic host evidence.',
    'root_source_review': 'All four product files and current workspace/cookie seam reviewed. No actionable blocker; scoped tests and independent adversarial probes support delivery.',
    'preserved_failures': 'Two producer attempts and original independent SO09 harness failure retained; targeted corrected SO09 passes without product delta.',
    'root_runtime_replay': False, 'cleanup': review['cleanup'], 'pending': review['pending'],
    'authenticated_workspace_accepted': False, 'backend_session_and_cookie_routes_exist': False,
    'browser_provider_native_customer_or_GA_acceptance': False, 'GA_verified': 0}

terminals = []
for directory, observation, commit, run in [
    ('verification/github-delivery-console-pagination-owner-contracts', 'ci-jobs-11.stdout', 'b231f3d405c06bfb348f193d46a348af0529bd84', 40556161461),
    ('verification/github-delivery-console-sparse-checkout', 'ci-jobs-4.stdout', '114a2632fd58076574bd5b2444c511861c3b30d4', 40558815569)]:
    data = read(directory + '/' + observation)
    assert data['headSha'] == commit and data['databaseId'] == run and data['attempt'] == 1
    assert data['status'] == 'completed' and data['conclusion'] == 'success' and len(data['jobs']) == 6
    steps = [step for job in data['jobs'] for step in job['steps']]
    assert len(steps) == 64 and all(step['conclusion'] == 'success' for step in steps)
    terminal = {'schema': 1, 'source_revision': commit, 'run': run, 'url': data['url'], 'attempt': 1,
        'jobs_passed': 6, 'steps_passed': 64, 'skipped_steps': 0, 'status': 'passed',
        'raw_observation': row(ROOT / directory / observation),
        'scope': 'Exact historical pushed source; no new session or Swift checkout candidate qualification.', 'GA_accepted': False}
    terminals.append((ROOT / directory / 'terminal-engine-attempt1.json', terminal))

w = read('work-graph.json'); g = read('gates/ga.json')
assert [x['id'] for x in w['packages']] == [f'W{i:02}' for i in range(1,19)]
assert [x['id'] for x in g['gates']] == [f'G{i:02}' for i in range(1,39)]
assert sum(x['status'] == 'running' for x in g['gates']) == 8
assert sum(x['status'] == 'planned' for x in g['gates']) == 30
assert w['packages'][7]['fixtureCacheStateContractCandidate'] == g['gates'][1]['fixtureCacheStateContractCandidate']
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
old_session = 'The strict frontend session consumer is frozen for independent review: all 149 outer producer host tests, ten new and four existing nested Solid tests, typecheck and production build pass. Root verifies all 65 selected source files and the frozen evidence. Two initial failed attempts remain preserved. Current missing server endpoints still produce unavailable state; implementation acceptance remains pending.'
new_session = 'The strict frontend session consumer has bounded source/host acceptance: all 149 outer producer tests, ten new and four existing nested Solid tests, typecheck and production build pass. Independent review qualifies 42 unique probes through 30 protocol/controller passes, eleven original Solid passes and one corrected targeted SO09 pass; its original harness failure remains preserved. Root verifies all 65 selected inputs and both frozen packets. Missing server endpoints still produce unavailable state; authenticated backend integration remains pending.'
old_ci = 'The preceding b231f3d Phoenix run passes all thirteen steps; five of its six Engine jobs pass and the remaining Swift job is still running. New Engine CI remains pending.'
new_ci = 'The preceding b231f3d Phoenix run passes all thirteen steps. Both b231f3d and 114a2632 Engine runs are now terminal with all six jobs and 64 steps passing on attempt one, with no skipped steps.'
texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text()
    assert text.count(old_session) == 1 and text.count(old_ci) == 1
    texts[name] = text.replace(old_session, new_session).replace(old_ci, new_ci)
save(DEST, value)
for path, terminal in terminals:
    save(path, terminal)
for target in [w['packages'][13], g['gates'][21]]:
    target['browserSessionConsumer'].update({'status': value['status'], 'implementation_accepted': True,
        'root_acceptance': row(DEST), 'independent_unique_probes_qualified': 42,
        'independent_attribution': review['count_attribution'], 'delivery_pending': True})
    target['firstPageReturn']['delivery'].update({'status': 'pushed-original-Console-cancelled-Phoenix-and-Engine-passed',
        'CI_pending': False, 'Engine_terminal': row(terminals[0][0])})
    target['ConsoleSparseCheckout']['delivery'].update({'status': 'pushed-Console-and-Engine-CI-passed',
        'Engine_terminal': row(terminals[1][0])})
c = w['packages'][7]['fixtureCacheStateContractCandidate']
c['guarded_snapshot_actual_owner_selection_console_delivery'].update({'Engine_terminal': row(terminals[0][0]), 'CI_pending': False})
c['console_sparse_checkout_IR01_delivery'].update({'Engine_terminal': row(terminals[1][0]), 'CI_pending': False})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name, text in texts.items():
    (ROOT / name).write_text(text)
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], cwd=ROOT, timeout=10, check=True)
save(OUT / 'session-acceptance-metadata-validation.json', {'passed': True,
    'metadata_files': [row(ROOT / name) for name in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
    'W08_G02_equal': True, 'W05_G05_equal': True, 'packages': 18, 'gates': 38, 'GA_verified': 0})
print(json.dumps({'accepted': value['status'], 'source_files': 65, 'frozen_members': 171, 'historical_Engine_runs_passed': 2}))
