#!/usr/bin/env python3
"""Root artifact review of executor v2; grants no implementation or target run."""
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROPOSAL = ROOT / 'verification/swift-executor-stage-contract'
sha = lambda data: hashlib.sha256(data).hexdigest()
read = lambda path: json.loads(path.read_text())
r = read(PROPOSAL / 'receipt.json')
assert sha((PROPOSAL / 'receipt.json').read_bytes()) == 'a606a282f1c8a0c5b3aa1c5f16287ccd09e20be1c2328a7a8c0c4d0e34c44185'
assert (PROPOSAL / 'receipt.json').read_bytes() == (PROPOSAL / 'proposal-receipt.json').read_bytes()
assert r['artifact_checks_passed'] and r['implementation_tests_executed'] == 0
assert not r['cache_implementation_accepted'] and not r['target_executed']
assert r['device_operations'] == r['commits_or_pushes'] == r['ga_gate_changes'] == []
bindings = {}
def bind(item):
    data = (ROOT / item['path']).read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
    bindings[item['path']] = item['sha256']

for item in [r['source_binding'], r['history_preservation'], *r['reference_bindings'], *r['artifact_bindings']]:
    bind(item)
for c in r['commands']:
    assert c['exit_code'] == 0
    bind(c['stdout']); bind(c['stderr'])
history = read(ROOT / r['history_preservation']['path'])
assert len(history['files']) == 24
for p in history['files']:
    bind({'path': p['preserved_path'], 'bytes': p['bytes'], 'sha256': p['sha256']})
source = read(ROOT / r['source_binding']['path'])
assert len(source['files']) == 23
assert sha(json.dumps(source['files'], sort_keys=True, separators=(',', ':')).encode()) == source['manifest_entries_sha256']
for p in source['files']:
    data = subprocess.check_output(['git', 'show', p['revision'] + ':' + p['path']], cwd=ROOT)
    assert len(data) == p['bytes'] and sha(data) == p['sha256']
old = read(PROPOSAL / 'historical-v1/verification/swift-executor-stage-contract/acceptance.json')
new = read(PROPOSAL / 'acceptance.json')
assert [x['function'] for x in old['required_synthetic_tests']] == [x['function'] for x in new['required_synthetic_tests']]
assert len(new['required_synthetic_tests']) == 20
assert len(new['measured_layout_map']) == 8
assert all(x['status'] == 'pending' for x in new['measured_layout_map'])
assert sum(len(x['assertions']) for x in new['required_synthetic_tests']) == 75
for a, b in zip(old['required_synthetic_tests'], new['required_synthetic_tests']):
    assert [x['id'] for x in a['assertions']] == [x['id'] for x in b['assertions']]
    assert b['status'] == 'pending'
assert new['cleanup']['foundation_counts'] == {'SwiftRunFailure': 4, 'SwiftRunUsage': 4,
                                              'ReservationTicket': 6, 'Option<WasiUsage>': 6}
commands = []
for label, args in [('check', []), ('mutations', ['--mutation-checks'])]:
    argv = [sys.executable, '-B', str(PROPOSAL / 'check_contract.py'), *args]
    c = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = HERE / (label + '.log'); log.write_bytes(c.stdout)
    assert c.returncode == 0
    commands.append({'argv': argv, 'cwd': str(ROOT), 'exit': c.returncode,
                     'log': str(log.relative_to(ROOT)), 'sha256': sha(c.stdout)})
assert all(sha((ROOT / p).read_bytes()) == h for p, h in bindings.items())
result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/swift-executor-contract-root-review/audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__).read_bytes()),
    'accepted_contract_revision': 2, 'baseline_revision': r['baseline_revision'],
    'proposal_receipt_sha256': sha((PROPOSAL / 'receipt.json').read_bytes()),
    'artifact_bindings': bindings, 'committed_source_bindings': source['files'],
    'verified_bindings': len(bindings) + len(source['files']), 'commands': commands,
    'prior_independent_review': 'verification/swift-executor-contract-review/decision.json',
    'root_review': 'R1 corrected to six optional shapes with explicit disjoint final execution envelope and no last-use or payload-padding assumptions. Algorithm/authority/private API intent preserved; fixed import work1 matches legacy source. All20 functions/75 assertion IDs and eight measured phases retained. Explicit type/layout prerequisite sequencing resolves the original preimplementation measurement ambiguity without granting an assignment.',
    'decision': 'Accept revised algorithm, authority, private API intent and named accounting contract only.',
    'implementation_assignment_authorized': False, 'cache_implementation_accepted': False,
    'target_execution_authorized': False, 'physical_device_runs_authorized': False,
    'ga_gate_state_changes': False,
    'pending': ['Root acceptance of actual cache implementation',
                'Separately assigned compiling executor type/lifetime/layout prerequisite',
                'Actual executor implementation, all20 tests and75 assertions, eight concrete layout maps',
                'Separate exact bounded full-target runner acceptance',
                'Physical devices, immutable published consumer and specified external GA qualification'],
}
(HERE / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'accepted_contract_revision': 2, 'bindings': result['verified_bindings'],
                  'implementation_authorized': False}))
