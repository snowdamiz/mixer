#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok, why):
    if not ok: raise RuntimeError(why)
inputs = json.loads((HERE / 'inputs.json').read_text())
require(len(inputs['files']) == 141, 'input count')
require(digest(HERE / 'source-manifest.sha256') == inputs['source_manifest_sha256'], 'input manifest')
for path, expected in inputs['files'].items():
    require(digest(Path(inputs['source']) / path) == expected, 'frozen input ' + path)
review = json.loads((HERE / 'independent-source-review.json').read_text())
require(review['status'] == 'source_review_no_actionable_findings' and not review['findings'], 'independent review')
for path, expected in dict(review['reviewedSource'], **review['supportingPaths']).items():
    require(digest(ROOT / path) == expected and inputs['files'][path] == expected, 'reviewed source ' + path)
host = json.loads((HERE / 'receipt.json').read_text())
cross = json.loads((HERE / 'cross-receipt.json').read_text())
opacity = json.loads((HERE / 'opacity-receipt.json').read_text())
require(host['status'] == 'host tests passed' and cross['status'] == opacity['status'] == 'passed', 'matrix status')
for command in host['commands'] + cross['commands']:
    raw = (HERE / (command['name'] + '.log')).read_bytes()
    require(command['exit_code'] == 0 and hashlib.sha256(raw).hexdigest() == command['log_sha256'], 'command log')
    if command['name'] in ('debug', 'release'):
        require(re.findall(rb'Executed (\d+) tests, with 0 failures', raw) == [b'7', b'7', b'16', b'30', b'30'], '30 tests')
for command in opacity['commands']:
    require(command['exit_code'] == command['expected_exit'] and digest(ROOT / command['log']) == command['log_sha256'], 'opacity command')
for artifacts in cross['artifacts'].values():
    for path, expected in artifacts.items(): require(digest(Path(path)) == expected, 'cross artifact')
receipt = {
    'status': 'pure internal policy qualified with independent source review; frozen evidence audited',
    'source_manifest_sha256': inputs['source_manifest_sha256'], 'sources_verified': 141,
    'host_tests_per_mode': 30, 'new_policy_tests': 7, 'host_modes': ['debug', 'release'],
    'official_cross_artifacts_verified': sum(len(x) for x in cross['artifacts'].values()), 'public_opacity_commands': 2,
    'independent_source_review_sha256': digest(HERE / 'independent-source-review.json'),
    'swift_version_command': ['swift', '--version'],
    'evidence_sha256': {p.name: digest(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name != 'final-receipt.json'},
    'scope': 'Internal enclosing-evidence derivation only; fixed frozen dependencies, no adapters/session/selection or committed-health provenance.',
    'limitations': ['Independent source review did not rerun tests.', 'Official iOS/Android module/object compilation only; no final app link or execution.',
        'New bridge lifecycle and private recovery store excluded from this frozen qualification; combined coordinator work remains open.',
        'No physical-device, immutable publication, FieldLog or GA qualification.']
}
(HERE / 'final-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(receipt['status'])
