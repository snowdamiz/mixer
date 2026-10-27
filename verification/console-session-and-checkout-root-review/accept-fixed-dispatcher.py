"""Accept only the independently reviewed private dispatcher component slice."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / 'fixed-dispatcher-acceptance.json'
PRODUCER = ROOT / 'verification/console-fixed-workspace-dispatcher'
REVIEW = ROOT / 'verification/console-fixed-workspace-dispatcher-independent'

def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def read(path):
    return json.loads(path.read_bytes())

def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

assert not DEST.exists(), 'One-shot; do not replay'
packets = []
for directory, digest, count in [(PRODUCER, 'fb45ab6c0574170596f5665f8cdfac6b352f02c1086839de5ed7a0f49a11e175', 90),
        (REVIEW, '2674d87e5efb9d51d734fd617d86e9745caf2cbf12ebceb940756fa6ee0eb907', 14)]:
    assert row(directory / 'freeze.json')['sha256'] == digest
    seal = read(directory / 'freeze.json')
    assert len(seal['members']) == count
    for expected in seal['members']:
        actual = row(directory / expected['path'])
        assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256']
    members = [row(path) for path in sorted(directory.rglob('*')) if path.is_file()]
    assert len(members) == count + 1
    packets.append({'directory': str(directory.relative_to(ROOT)), 'members': members})
validation = read(REVIEW / 'validation.json')
assert validation['status'] == 'passed' and validation['findings'] == []
assert len(validation['checks']) == 14 and all(c['pass'] for c in validation['checks'])
for directory, receipt_name, output_name, tests, pins in [(PRODUCER, 'host-attempt-3-receipt.json', 'host-attempt-3.stdout.txt', 19, 985),
        (REVIEW, 'host-receipt.json', 'host.stdout.txt', 8, 983)]:
    receipt = read(directory / receipt_name)
    assert receipt['status'] == 'passed' and receipt['exit_code'] == 0
    assert receipt['scratch_removed'] and receipt['direct_child_reaped'] and receipt['owned_group_absent']
    assert receipt['postrun_original_changes'] == [] and receipt['postrun_original_hashes_verified'] == pins
    assert row(directory / output_name)['sha256'] == receipt['output_sha256']
    output = (directory / output_name).read_text()
    assert 'compile_warnings=0 runtime_warnings=0' in output
    assert f'RESULT {{"total":{tests},"failures":0,"excluded":0,"skipped":0}}' in output
manifest = read(PRODUCER / 'source-manifest.json')
owned = []
for entry in manifest['members']:
    actual = row(ROOT / entry['path'])
    assert actual['bytes'] == entry['bytes'] and actual['sha256'] == entry['sha256']
    if entry['category'] != 'ordinary':
        owned.append(actual)
assert len(owned) == 6
value = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
    'status': 'accepted-private-fixed-dispatcher-source-and-component-host-slice',
    'source_revision': validation['source_revision'], 'source_tree': validation['source_tree'],
    'owned_files': owned, 'packets': packets, 'producer_host_tests': 19, 'independent_host_tests': 8,
    'compile_and_runtime_warnings': 0, 'skipped_tests': 0, 'earlier_harness_failures_preserved': 2,
    'root_review': 'Fixed same-process default bearer/controller join, exact typed request encoding, nondefault Repo refusal without reset, private single response capture and strict complete response projection reviewed. Independent adversarial controls pass; no actionable selected-scope finding.',
    'root_runtime_replay': False, 'actual_default_verifier_Repo_success_accepted': False,
    'private_malformed_projection_runtime_tested': False, 'synthetic_controller_positives_are_authority': False,
    'pending': validation['pending'], 'GA_verified': 0, 'delivery_pending': True}
w = read(ROOT / 'work-graph.json'); g = read(ROOT / 'gates/ga.json')
assert w['packages'][7]['fixtureCacheStateContractCandidate'] == g['gates'][1]['fixtureCacheStateContractCandidate']
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text()
    old = 'its corrected bounded host run compiles 35 modules with no warnings and passes all nineteen tests. Both earlier harness failures and confirmed cleanup remain preserved; fresh independent source/host review is active.'
    new = 'it has bounded source/component acceptance after nineteen producer tests and eight fresh independent adversarial tests pass, with 35 compiled modules and no warnings. Both earlier harness failures and confirmed cleanup remain preserved. Actual default verifier/default Repo success and database authority remain pending.'
    assert text.count(old) == 1
    texts[name] = text.replace(old, new)
save(DEST, value)
for target in [w['packages'][13], g['gates'][21]]:
    target['fixedWorkspaceDispatcher'].update({'status': value['status'], 'root_acceptance': row(DEST),
        'implementation_accepted': True, 'accepted_scope': 'Private source/component host slice only',
        'independent_host_tests': 8, 'independent_validation': row(REVIEW / 'validation.json'),
        'independent_freeze': row(REVIEW / 'freeze.json'), 'delivery_pending': True,
        'actual_default_Repo_success_accepted': False, 'session_or_cookie_authority_accepted': False,
        'GA_accepted': False})
w['packages'][13]['nextImplementation'] = 'Qualify the accepted private dispatcher with the actual default verifier/default Repo and ordinary current-authorization transaction behavior in a separately selected bounded scope. Session/cookie lifecycle/provider and active-token provenance remain pending; stopped callback review is not replayed.'
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name, text in texts.items():
    (ROOT / name).write_text(text)
subprocess.run(['git', 'diff', '--check', '--', *[r['path'] for r in owned], 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], check=True, timeout=10)
save(OUT / 'fixed-dispatcher-metadata-validation.json', {'passed': True,
    'metadata_files': [row(ROOT / name) for name in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
    'packages': 18, 'gates': 38, 'W08_G02_equal': True, 'W05_G05_equal': True, 'GA_verified': 0})
print(json.dumps({'accepted': value['status'], 'producer_tests': 19, 'independent_tests': 8, 'frozen_files': 106, 'full_session_authority_pending': True}))
