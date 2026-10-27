"""Select accepted console source and completed ownership-contract evidence only."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = 'd6af73813244c330a979afb83b45f53490ff5b29'
PARENT = ROOT / 'verification/github-delivery-source-rebind-services-checkout'
REVIEW = ROOT / 'verification/swift-semantic-adapter-root-review'
PACKETS = [
    ('swift-guarded-snapshot-provider-callee-source-correction', 'e80dd24b7cb7e18c97abb1effa705cbc2b7882b36ac8e439a181bc6cf3a6dfb1'),
    ('swift-guarded-snapshot-callee-source-correction-independent', '00db7ec194949f945acb86d78e051873be7792076f05793e009ed9c7325739b5'),
    ('swift-guarded-snapshot-actual-owner-rust-selection', '1b0c3234a22f559280f5eb461bab5bf367a2ee0b7acda45c744b1da92b10d0f7'),
    ('swift-guarded-snapshot-actual-owner-rust-preaccess', '050d4920ee51014748d0c62aec832c13a65bef09673fff41bbc62310635e4a66'),
]
ACTIVE = ['swift-guarded-snapshot-actual-owner-rust-implementation',
    'swift-guarded-snapshot-actual-owner-rust-independent', 'console-session-integration-selection']

def row(p):
    raw = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def save(p, value):
    with p.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def untracked(folder):
    paths = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z', '--', folder], cwd=ROOT, timeout=10)
    return [row(ROOT / p) for p in paths.decode().split('\0') if p]

assert not (OUT / 'release-selection.json').exists()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, timeout=10, text=True).strip() == BASE
assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT, timeout=10)
accept = ROOT / 'verification/console-pagination-root-review/acceptance.json'
assert row(accept)['sha256'] == 'f16f2e1d93e9ced391d53f8eb8e614e44901c616888c3499962cbd15aea608bb'
console = json.loads(accept.read_bytes())
assert console['verification']['outer_tests_passed'] == 57 and console['verification']['project_typecheck_passed']
canonical = [x['path'] for x in console['owned_source']]
assert len(canonical) == 11
for item in console['owned_source']: assert row(ROOT / item['path']) == item
for name, digest in PACKETS: assert row(ROOT / 'verification' / name / 'seal.json')['sha256'] == digest
terminal = json.loads((PARENT / 'terminal-ci-attempt1.json').read_bytes())
assert terminal['commit'] == BASE and terminal['passed_jobs'] == 6 and terminal['passed_steps'] == 64
scope = 'Accepted console first-page return; bounded partial callee correction; selected actual Rust ownership contract and frozen preaccess oracles; terminal parent CI. Active Rust implementation/review and next session selection excluded.'
w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
delivery = {'status': 'prepared-for-authorized-nonforce-push', 'base': BASE,
    'directory': str(OUT.relative_to(ROOT)), 'scope': scope, 'frozen_packets': 4,
    'canonical_paths': canonical, 'excluded_active_lanes': ACTIVE, 'CI_pending': True,
    'root_funding_native_or_GA': False}
for target in [w['packages'][13], g['gates'][21]]:
    target['firstPageReturn']['delivery'] = copy.deepcopy(delivery)
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
c['guarded_snapshot_actual_owner_selection_console_delivery'] = copy.deepcopy(delivery)
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
assert [p['id'] for p in w['packages']] == [f'W{i:02}' for i in range(1,19)]
assert [p['id'] for p in g['gates']] == [f'G{i:02}' for i in range(1,39)]
assert sum(x['status'] == 'running' for x in g['gates']) == 8
assert sum(x['status'] == 'planned' for x in g['gates']) == 30
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
for name in ['PLAN.md', 'STATUS.md']:
    p = ROOT / name
    text = p.read_text()
    old = 'compilation and independent implementation acceptance remain pending.'
    assert text.count(old) == 1
    p.write_text(text.replace(old, 'the producer reports passing final compiler and focused host checks, with frozen release and independent implementation acceptance pending.'))
subprocess.run(['git','diff','--check','--','PLAN.md','STATUS.md','work-graph.json','gates/ga.json',*canonical], cwd=ROOT, timeout=10, check=True)

source = (PARENT / 'deliver.py').read_text()
replacements = [
    ('BASE = "9398732c23648a82097d5a72b02b1c77af818e41"', 'BASE = "' + BASE + '"'),
    ('release["packet_count"] == 8', 'release["packet_count"] == 4'),
    ('startswith("verification/github-delivery-host-proof-and-vm-checkout/")', 'startswith("verification/github-delivery-source-rebind-services-checkout/")'),
    ('"verification/swift-guarded-snapshot-provider-callee-source-correction/"', '"verification/swift-guarded-snapshot-actual-owner-rust-implementation/"'),
    ('"verification/swift-guarded-snapshot-callee-source-correction-independent/"', '"verification/swift-guarded-snapshot-actual-owner-rust-independent/"'),
    ('"verification/swift-guarded-snapshot-actual-owner-rust-selection/"', '"verification/console-session-integration-selection/"'),
    ('Record source rebind reviews and narrow services CI checkout', 'Restore first-page console navigation and record ownership contracts'),
    ('active_callee_correction_review_and_Rust_selection_lanes_excluded', 'active_Rust_implementation_review_and_session_selection_excluded'),
    ('"canonical_product_changed": False', '"canonical_product_changed": True'),
]
for old, new in replacements:
    assert source.count(old) == 1, old
    source = source.replace(old, new)
with (OUT / 'deliver.py').open('x') as stream: stream.write(source)
root_files = untracked(str(REVIEW.relative_to(ROOT)))
assert len(root_files) == 28
root_files += untracked('verification/console-pagination-root-review')
root_files += untracked('verification/console-workflow-next-slice-review')
root_files += console['owned_source']
save(OUT / 'release-selection.json', {'schema': 1, 'ready': True,
    'packets': [{'path': name, 'seal_sha256': digest} for name, digest in PACKETS], 'packet_count': 4,
    'root_and_source_files': root_files, 'parent_delivery_files': untracked(str(PARENT.relative_to(ROOT))),
    'canonical_paths': canonical, 'scope': scope, 'active_lanes_excluded': ACTIVE})
save(OUT / 'metadata-validation.json', {'schema': 1, 'passed': True,
    'at': datetime.now(timezone.utc).isoformat(), 'command': sys.argv, 'python': sys.version,
    'script_sha256': row(Path(__file__).resolve())['sha256'], 'source_revision': BASE,
    'metadata_files': [row(ROOT / n) for n in ['PLAN.md','STATUS.md','work-graph.json','gates/ga.json']],
    'console_acceptance': row(accept), 'terminal_parent_CI': row(PARENT / 'terminal-ci-attempt1.json'),
    'gates': {'running': 8, 'planned': 30, 'passed': 0}})
print(json.dumps({'prepared': True, 'canonical_paths': 11, 'packets': 4, 'root_and_source_files': len(root_files), 'commit_or_push_executed': False}))
