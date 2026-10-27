"""Record exact delivered slices, initial CI observations and next Rust execution release once."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / 'post-push-metadata.json'

def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def read(path):
    return json.loads(path.read_bytes())

assert not DEST.exists(), 'One-shot; do not replay'
r = read(OUT / 'receipt.json')
assert r['pushed'] and not r['force']
assert r['commit'] == 'd04fd5cc71bc72061f18203e414b90869129b4ca'
assert subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, check=True, timeout=10).stdout.decode().strip() == r['commit']
runs = read(OUT / 'ci-runs-1.stdout')
assert len(runs) == 2 and all(x['headSha'] == r['commit'] for x in runs)
delivery = {'status': 'pushed-Engine-and-Phoenix-CI-pending', 'commit': r['commit'], 'tree': r['tree'],
    'changed_paths': r['committed_paths'], 'canonical_paths': r['canonical_paths'], 'pushed': True, 'force': False,
    'receipt': row(OUT / 'receipt.json'), 'manifest': row(OUT / 'manifest.json'),
    'initial_CI_observation': row(OUT / 'ci-runs-1.stdout'), 'runs': runs,
    'active_Rust_implementation_review_and_checkout_contract_excluded': True, 'GA_accepted': False}
w = read(ROOT / 'work-graph.json'); g = read(ROOT / 'gates/ga.json')
for target in [w['packages'][13], g['gates'][21]]:
    target['fixedWorkspaceDispatcher'].update({'delivery_pending': False, 'delivery': copy.deepcopy(delivery)})
for target in [w['packages'][4], g['gates'][4]]:
    target['ownerHostSparseCheckout'].update({'delivery_pending': False, 'delivery': copy.deepcopy(delivery)})
c = w['packages'][7]['fixtureCacheStateContractCandidate']
assert c == g['gates'][1]['fixtureCacheStateContractCandidate']
b = c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
correction = b['actual_owner_Rust_selection']['correction']
correction['scoped_review_delivery'] = copy.deepcopy(delivery)
release_path = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-root-result-lifetime-execution-release.json'
release = read(release_path)
assert release['released'] and release['compiler_commands'] == 21 and release['filtered_host_runs'] == 2
correction['IR02_source_repair'].update({'status': 'isolated-source-frozen-exact-compiler-and-host-checks-released',
    'compiler_or_host_execution_released': True, 'root_execution_release': row(release_path),
    'source146_tree': release['source146_tree'], 'source_freeze': release['source_freeze'],
    'exact_roster': release['roster'], 'independent_ownership': 'verification/swift-guarded-snapshot-root-result-lifetime-independent',
    'independent_review_status': 'source-only-review-active-compiler-not-released',
    'implementation_accepted': False, 'full_funding_or_ownership_accepted': False})
g['gates'][1]['fixtureCacheStateContractCandidate'] = copy.deepcopy(c)
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
texts = {}
for name in ['PLAN.md', 'STATUS.md']:
    text = (ROOT / name).read_text()
    old = 'Delivery and the subsequent GitHub checkout/JVM result remain pending; the earlier base CI pass does not validate this new workflow.'
    new = 'The accepted dispatcher and Android checkout are pushed as `d04fd5cc` with 2,016 selected paths, including the frozen narrow Swift retention review and next lifetime contract. Engine and Phoenix CI are pending; active new Rust implementation/review and the next checkout proposal were excluded. The earlier base CI pass does not validate this new workflow.'
    assert text.count(old) == 1
    text = text.replace(old, new)
    old = 'Isolated source work proceeds in two files; exact compiler execution awaits root review.'
    new = 'The isolated two-file source is frozen and its exact 21 compiler, two filtered host and one version commands are released under a hardened bounded runner. Fresh independent source review is active; compiler/host results and implementation acceptance remain pending.'
    assert text.count(old) == 1
    texts[name] = text.replace(old, new)
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name, text in texts.items():
    (ROOT / name).write_text(text)
subprocess.run(['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], check=True, timeout=10)
for path, digest in r['protected_work_unchanged'].items():
    assert row(ROOT / path)['sha256'] == digest
assert not subprocess.run(['git', 'diff', '--cached', '--name-only'], capture_output=True, check=True, timeout=10).stdout
with DEST.open('x') as stream:
    json.dump({'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'delivery': delivery,
        'root_execution_release': row(release_path),
        'metadata_files': [row(ROOT / name) for name in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']],
        'packages': 18, 'gates': 38, 'W08_G02_equal': True, 'W05_G05_equal': True, 'GA_verified': 0}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'pushed': r['commit'], 'CI_runs_pending': len(runs), 'Rust_exact_execution_released': True, 'GA_verified': 0}))
