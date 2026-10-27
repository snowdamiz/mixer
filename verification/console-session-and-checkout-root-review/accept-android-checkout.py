"""Accept the frozen Android owner checkout closure for subsequent CI validation."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / 'android-checkout-acceptance.json'
PRODUCER = ROOT / 'verification/ci-android-owner-host-sparse-checkout'
REVIEW = ROOT / 'verification/ci-android-owner-host-sparse-checkout-independent'

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
for directory, digest in [(PRODUCER, '27c7a3c226cc1b38fa835f59ce4d7ef12753f05bbd416a17463814b9b45a889f'),
        (REVIEW, 'c294d800c2ed97096147fe220f1b9c69779c9d22652a27af4fc0702a06f838e8')]:
    assert row(directory / 'manifest.json')['sha256'] == digest
    manifest = read(directory / 'manifest.json')
    for name, expected in manifest['members'].items():
        actual = row(directory / name)
        assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256']
    members = [row(path) for path in sorted(directory.rglob('*')) if path.is_file()]
    assert len(members) == len(manifest['members']) + 1
    packets.append({'directory': str(directory.relative_to(ROOT)), 'members': members})
r = read(REVIEW / 'receipt.json')
assert r['status'] == 'passed-independent-offline-checkout-coverage-only'
assert r['only_change_is_android_owner_checkout_with_block']
assert r['other_workflow_bytes_pins_commands_limits_triggers_and_default_fetch_depth_unchanged']
assert r['producer_packet_and_candidate_unchanged_through_checks']
assert (r['selected_files'], r['selected_bytes'], r['required_files_covered'], r['unique_java_sources']) == (304, 2108263, 199, 193)
workflow = row(ROOT / '.github/workflows/verify.yml')
assert workflow['sha256'] == r['workflow_after']['sha256'] == 'fa8fd8887391ffc00f55bc70b370e725cf99ee330c744387f498bea7a2626a88'
assert row(PRODUCER / 'workflow.diff')['sha256'] == r['workflow_delta']['sha256']
value = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
    'status': 'accepted-offline-Android-owner-checkout-closure-for-remote-validation',
    'source_revision': r['source_revision'], 'source_tree': r['source_git_tree'], 'workflow': workflow,
    'packets': packets, 'selected_files': 304, 'selected_bytes': 2108263, 'required_inputs': 199,
    'independent_receipt': row(REVIEW / 'receipt.json'), 'root_runtime_replay': False,
    'root_review': 'Reviewed exact nine-line checkout-only delta, both finite runner closures and selected Java I/O boundary. Independent canonical blob and sparse-rule checks cover every required input. Commands, pins, limits and default fetch depth remain unchanged.',
    'remote_CI_passed': False, 'pending': r['pending'], 'qualification': r['qualification'], 'GA_verified': 0}
w = read(ROOT / 'work-graph.json'); g = read(ROOT / 'gates/ga.json')
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
assert w['packages'][7]['fixtureCacheStateContractCandidate'] == g['gates'][1]['fixtureCacheStateContractCandidate']
assert sum(x['status'] == 'running' for x in g['gates']) == 8
assert sum(x['status'] == 'planned' for x in g['gates']) == 30
paragraph = 'The Android owner host CI checkout has bounded offline acceptance after fresh independent review. It retains all 199 required inputs in 304 canonical files / 2,108,263 bytes; every command, pin, limit and the default fetch depth remains unchanged. The producer materialization and independent canonical-blob/rule checks pass with owned cleanup. Delivery and the subsequent GitHub checkout/JVM result remain pending; the earlier base CI pass does not validate this new workflow.'
texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text()
    marker = 'The isolated actual Rust input-owner candidate is returned for correction'
    assert text.count(marker) == 1
    texts[name] = text.replace(marker, paragraph + '\n\n' + marker)
save(DEST, value)
entry = {'status': value['status'], 'root_acceptance': row(DEST), 'accepted': True,
    'selected_files': 304, 'selected_bytes': 2108263, 'required_inputs': 199,
    'all_commands_pins_limits_default_fetch_depth_unchanged': True,
    'delivery_pending': True, 'remote_CI_passed': False, 'GA_accepted': False}
w['packages'][4]['ownerHostSparseCheckout'] = entry
g['gates'][4]['ownerHostSparseCheckout'] = copy.deepcopy(entry)
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name, text in texts.items():
    (ROOT / name).write_text(text)
subprocess.run(['git', 'diff', '--check', '--', '.github/workflows/verify.yml', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], check=True, timeout=10)
save(OUT / 'android-checkout-metadata-validation.json', {'passed': True,
    'metadata_files': [row(ROOT / name) for name in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
    'packages': 18, 'gates': 38, 'W08_G02_equal': True, 'W05_G05_equal': True, 'GA_verified': 0})
print(json.dumps({'accepted': True, 'files': 304, 'inputs': 199, 'packet_files': sum(len(p['members']) for p in packets), 'remote_pending': True}))
