#!/usr/bin/env python3
"""Seal the failing, exact-source candidate4 F09 witness without changing inputs."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'disposal-priority-finding'
OUT.mkdir()
def record(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
def write(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2)+'\n')

run = HERE/'disposal-priority-1'
command = json.loads((run/'02-run.command.json').read_text())
assert command['exit_code'] == 1 and command['forced_termination'] is None
for name, expected in command['source_map'].items():
    assert record(HERE/name) == expected, name
    if name == 'IndependentOwnerContractReview.java':
        shutil.copyfile(HERE/name, OUT/name)
rows = [json.loads(line) for line in (run/'02-run.stdout').read_text().splitlines()]
assert [r['variant'] for r in rows] == ['ordinary-only', 'fatal-only', 'ordinary-then-fatal']
assert rows[0]['ownerPrimaryIsA'] and rows[1]['ownerPrimaryIsE']
failed = rows[2]
assert failed['coordinatorPrimaryIsA'] and failed['coordinatorFatalIsE']
assert failed['ownerPrimaryIsE'] and not failed['ownerPrimaryIsA']
assert failed['ownerFatalIsE'] and failed['escapingIsE']
assert all(r['destroyAttempts'] == 1 and r['coreRetired'] and not r['draw'] and not r['input'] for r in rows)
write('finding.json', {
    'id': 'F09', 'candidate': 4, 'status': 'confirmed; implementation rejected',
    'subject': 'NativeOwnerV2.closePending fails to collect retained coordinator primary before later thrown fatal',
    'variants': rows,
    'controls_passed': ['ordinary-only', 'fatal-only'],
    'failing_variant': 'ordinary-then-fatal',
    'ordinary_identity': 'suppression-disabled ordinary A thrown by actual current-gate disposal View.setVisibility entry',
    'fatal_identity': 'fatal E thrown by actual engine destroy leaf',
    'contract': {
        'correction': {'path': 'verification/android-private-owner-independent-review/preaccess/inputs/docs/android-private-owner-effect-integration-correction.md', 'lines': ['94-99', '215-220']},
        'proposal': {'path': 'verification/android-private-owner-independent-review/preaccess/inputs/docs/android-private-owner-effect-integration-proposal.md', 'lines': ['110-114', '305-313']},
        'root_interpretation': 'Owner collects component retained first primary and first fatal; nested retention alone is insufficient. Existing earlier owner primary/fatal wins.'
    },
    'source_anchors': [
        {'path': 'native/android/app/src/dev/mixer/android/NativeOwnerV2.java', 'lines': '390-400', 'observation': 'closePending remembers only caught throwable'},
        {'path': 'native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java', 'lines': '188-195', 'observation': 'closeFromOwner throws retained fatal when a disposal slot throws Error'},
        {'path': 'native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java', 'lines': '218-235', 'observation': 'Independent renderer then engine disposal retains first primary A and first fatal E'}
    ],
    'narrow_repair_direction': 'Collect retained coordinator primary and first fatal before remembering the caught throwable, preserving existing owner priorities. Preserve thrown E, exact coordinator failure/outcome, core cleanup completion token/failure and closed gates.',
    'limits': ['Host-only actual14 + admitted leaf3, no native/JNI reclamation claim', 'No candidate source edits', 'Three variants invoked; no manufactured assertion count or implementation acceptance'],
    'cleanup': json.loads((run/'cleanup.json').read_text())
})
paths = set(run.rglob('*'))
paths |= {HERE/name for name in command['source_map'] if name != 'IndependentOwnerContractReview.java'}
paths |= {OUT/'IndependentOwnerContractReview.java', OUT/'finding.json', Path(__file__), HERE/'run_independent_subject.py', HERE/'run_targeted_review.py', HERE/'descriptor.json', HERE/'matrix-packet-base.json'}
paths |= set((HERE/'tools').rglob('*'))
paths |= {ROOT/'verification/android-private-owner-independent-review/leaf-review-1/run_leaf_sanity.py'}
paths |= {ROOT/'verification/android-private-owner-independent-review/preaccess/inputs/docs'/('android-private-owner-effect-integration-'+name+'.md') for name in ['proposal','correction']}
paths |= {HERE/'admission/candidate-4-admission.json', HERE/'admission/candidate-4-manifest.json'}
files = {str(p.relative_to(ROOT)): record(p) for p in sorted(paths) if p.is_file()}
write('manifest.json', {'schema': 1, 'scope': 'Exact candidate4 F09 failing witness and two positive controls only; no implementation acceptance', 'members': len(files), 'bytes': sum(v['bytes'] for v in files.values()), 'files': files})
print(json.dumps({'manifest': str((OUT/'manifest.json').relative_to(ROOT)), **record(OUT/'manifest.json'), 'members': len(files), 'member_bytes': sum(v['bytes'] for v in files.values())}))
