#!/usr/bin/env python3
"""Select the exact accepted finite candidate, without changing production bytes."""
from pathlib import Path
import datetime, hashlib, json, shutil
H = Path(__file__).resolve().parent
R = H.parents[1]
P = H.parent / 'swift-decode-plan-reuse-diagnosis'
A = H.parent / 'swift-decode-plan-reuse-accounting-review'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, v): p.write_text(json.dumps(v, indent=2, sort_keys=True) + '\n')
assert sha(P/'seal.json') == '975085349286df4f467942eaf3f1704d8983fa3ea103277c60dea4e885af43c5'
assert sha(A/'seal.json') == '771b3da1c543f0171b59dade5a7e998b56e86b1b44e753b26f30980025530dc1'
assert sha(R/'docs/swift-decode-plan-regression-contract.md') == '19772ccebe8775b1693d2648d1bdb968bcc2362c796095ffc83f8b37252b0cc4'
source = json.loads((P/'source-manifest.json').read_text())
assert sha(P/'source-manifest.json') == 'cc52d92302ed81a71eeb8856644686b94657c1a505cf67b3f26c3bd91ad073c3'
live = {n: sha(R/'vm'/n) for n in source}
save(H/'live-input-manifest.json', live)
assert sha(H/'live-input-manifest.json') == '3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f'
assert all(sha(P/'source'/n) == v for n,v in source.items())
shutil.copytree(P/'source', H/'source')
for p in (H/'source').rglob('*'):
    if p.is_file(): p.chmod(0o644)
save(H/'candidate-input-manifest.json', source)
shutil.copyfile(P/'pending-full-suite-updates.json', H/'pending-full-suite-updates.json')
bindings = ['AGENTS.md', 'PLAN.md', 'mixer-product-plan.md', 'docs/swift-decode-plan-regression-contract.md', 'docs/swift-decode-plan-reuse-diagnosis.md', 'docs/swift-decode-plan-reuse-accounting-review.md', 'verification/swift-decode-plan-reuse-diagnosis/seal.json', 'verification/swift-decode-plan-reuse-accounting-review/seal.json', 'verification/swift-decode-plan-reuse-diagnosis-root-review/accounting-review-acceptance.json']
save(H/'input-bindings.json', {n: sha(R/n) for n in bindings})
save(H/'selection.json', {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'rootSuppliedSourceRevision': '9102ad3ee1247187c01ea5f55c42caaac882961b', 'candidateClosure': sha(H/'candidate-input-manifest.json'), 'liveClosure': sha(H/'live-input-manifest.json'), 'productionEditsAllowed': False, 'fixtureFilesAllowed': ['src/experimental_swift_reactor/cache_tests.rs', 'src/experimental_swift_reactor/execution_tests.rs', 'src/experimental_swift_reactor/lifecycle_tests.rs'], 'liveIntegration': False, 'full53MBReactor': False, 'nativeDeviceNetworkGit': False})
print('Selected exact 132-file candidate and bound live closure; copied inventory is not observed evidence.')
