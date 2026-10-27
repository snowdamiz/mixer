"""One-shot root acceptance of the Swift checkout input closure, before CI."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / 'swift-checkout-acceptance.json'

def row(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def read(path):
    return json.loads((ROOT / path).read_bytes())

def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

assert not DEST.exists(), 'One-shot; do not replay'
producer = ROOT / 'verification/ci-swift-sparse-checkout'
independent = ROOT / 'verification/ci-swift-sparse-checkout-independent'
review = read('verification/ci-swift-sparse-checkout-independent/receipt.json')
assert review['finding_count'] == 0 and review['reviewed_source_unchanged'] and review['source_revision_unchanged']
assert review['selected']['files'] == 5054 and review['selected']['bytes'] == 208685831
assert review['workflow_only_delta']['all_commands_pins_triggers_timeouts_artifacts_other_jobs_equal']
assert review['policy']['omitted_paths'] == [] and review['policy']['all_basename_paths'] == 645
assert review['sealed_and_external_inputs']['distinct_canonical_content_hashes_verified'] == 1080
assert row(independent / 'seal.json')['sha256'] == 'bfe0091a12ed2cb30fb5961850d4c75beef85996b7cb2fb9505bbe64b27454dd'
seal = json.loads((independent / 'seal.json').read_bytes())
for item in seal['members']:
    assert row(ROOT / item['path']) == item
independent_rows = [row(path) for path in sorted(independent.rglob('*')) if path.is_file()]
assert len(independent_rows) == 7
producer_rows = [row(path) for path in sorted(producer.rglob('*')) if path.is_file()]
relative = [dict(item, path=str((ROOT / item['path']).relative_to(producer))) for item in producer_rows]
digest = hashlib.sha256(json.dumps(relative, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
assert len(producer_rows) == 160 and sum(item['bytes'] for item in producer_rows) == 6414704
assert digest == review['frozen_producer_before']['inventory_sha256'] == review['frozen_producer_after']['inventory_sha256']
source_inputs = read('verification/ci-swift-sparse-checkout-independent/reviewed-source-inputs.json')
for item in source_inputs:
    assert row(ROOT / item['path']) == item
materialization = read('verification/ci-swift-sparse-checkout/materialization-2/receipt.json')
assert materialization['materialization']['passed'] and materialization['cleanup']['removed']
assert all(c['exit'] == 0 and c['owned_group_gone'] and c['child_reaped'] for c in materialization['commands'])
workflow = row(ROOT / '.github/workflows/verify.yml')
assert workflow['sha256'] == review['candidate_workflow_sha256'] == '80d09b839d91a8be0a50bb19fc84b63b421193af26e1b2a95aa668f98b7a4680'
value = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
    'status': 'accepted-offline-Swift-checkout-closure-for-remote-validation', 'workflow': workflow,
    'source_revision': review['canonical_revision'], 'tracked_tree': review['canonical_tree'],
    'packets': [{'directory': str(producer.relative_to(ROOT)), 'members': producer_rows},
        {'directory': str(independent.relative_to(ROOT)), 'members': independent_rows}],
    'producer_materialization': row(producer / 'materialization-2/receipt.json'),
    'independent_review': row(independent / 'receipt.json'), 'selected': review['selected'],
    'workflow_only_delta': review['workflow_only_delta'], 'policy_manifest_count': 645,
    'independently_hashed_canonical_content_inputs': 1080, 'root_runtime_replay': False,
    'root_review': 'Exact checkout-only diff, every Swift step closure, complete packet/manifest inclusion, materialization and independent canonical blob checks reviewed; no missing required input found.',
    'remote_CI_passed': False, 'limitations': review['limitations'], 'GA_verified': 0}
w = read('work-graph.json'); g = read('gates/ga.json')
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
assert sum(x['status'] == 'running' for x in g['gates']) == 8
assert sum(x['status'] == 'planned' for x in g['gates']) == 30
paragraph = 'The Swift CI checkout optimization has bounded offline acceptance after independent source review: it retains all required source, 645 policy manifests, complete consumed evidence packets and full Git history. The selected checkout is 5,054 files / 208,685,831 bytes, versus 330,288 files / 17,638,540,012 bytes. Only the checkout configuration changes; commands, pins, limits and other jobs remain identical. Remote validation of this candidate remains pending.'
texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text()
    marker = 'The isolated actual Rust input-owner candidate is returned for correction'
    assert text.count(marker) == 1
    texts[name] = text.replace(marker, paragraph + '\n\n' + marker)
save(DEST, value)
c['SwiftSparseCheckout'] = {'status': value['status'], 'root_acceptance': row(DEST),
    'ownership': str(producer.relative_to(ROOT)), 'independent_ownership': str(independent.relative_to(ROOT)),
    'selected_files': 5054, 'selected_bytes': 208685831, 'all_commands_pins_limits_unchanged': True,
    'accepted': True, 'remote_CI_passed': False, 'delivery_pending': True, 'GA_accepted': False}
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name, text in texts.items():
    (ROOT / name).write_text(text)
subprocess.run(['git', 'diff', '--check', '--', '.github/workflows/verify.yml', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], cwd=ROOT, timeout=10, check=True)
save(OUT / 'swift-checkout-metadata-validation.json', {'passed': True,
    'metadata_files': [row(ROOT / name) for name in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
    'packages': 18, 'gates': 38, 'W08_G02_equal': True, 'W05_G05_equal': True, 'GA_verified': 0})
print(json.dumps({'accepted': value['status'], 'frozen_packet_files': 167, 'selected_files': 5054, 'remote_pending': True}))
