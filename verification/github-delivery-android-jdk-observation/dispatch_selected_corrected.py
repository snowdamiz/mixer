"""Consume exactly one selected manual allowance before submit; unknown outcomes never replay."""
import sys
sys.dont_write_bytecode = True
assert sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('android_selection_common', Path(__file__).with_name('selection_common_delivery_corrected.py'))
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
import hashlib
import json
for name in ('StrictCommands','BASE','TREE','S','SELECTION','ROWS','SELECTED','PROTECTED','ROOT','OUT','now','row','save','check_sources','bound_context','dispatch_input'): globals()[name] = getattr(common,name)
assert not (OUT / 'manual-dispatch-selected-corrected-once.json').exists()
context = bound_context()
head = context['DELIVERED_SHA']
r = json.loads((OUT / 'delivery-selected-corrected-receipt.json').read_bytes())
b = json.loads((OUT / 'ci-binding-selected-corrected.json').read_bytes())
assert b['head'] == head and b['tree'] == r['tree'] and b['manualBeforeCount'] == 0
assert b['selection'] == row(ROOT / SELECTION) and b['delivery'] == row(OUT / 'delivery-selected-corrected-receipt.json')
assert b['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF']
context['DISPATCH_JSON'] = dispatch_input(head)
c = StrictCommands('dispatch-selected-corrected', context)
assert c.run('head').decode().splitlines() == [head, r['tree']]
assert json.loads(c.run('manual-workflow-content')) == b['contents']['manual']
assert json.loads(c.run('manual-workflow-registration')) == b['registrations']['manual']
assert json.loads(c.run('manual-before-runs')) == []
# The committed template remains false/unbound. Only this local exact copy is enabled.
save('manual-dispatch-selected-corrected-input.json', json.loads(context['DISPATCH_JSON']))
assert c.run('remote-predispatch').decode().split() == [head, 'refs/heads/main']
submit = c.vector('dispatch')
save('manual-dispatch-selected-corrected-once.json', {'schema': 1, 'at': now(), 'head': head,
    'selection': row(ROOT / SELECTION), 'binding': row(OUT / 'ci-binding-selected-corrected.json'),
    'workflow': S['manualHost']['workflow'], 'workflowSHA256': S['manualHost']['workflowSHA256'],
    'input': row(OUT / 'manual-dispatch-selected-corrected-input.json'), 'dispatchNonce': S['manualHost']['dispatchNonce'],
    'argvSHA256': hashlib.sha256(json.dumps(submit, separators=(',', ':')).encode()).hexdigest(),
    'allowanceConsumedBeforeSubmit': True, 'dispatchLimit': 1, 'retryRerunFallbackAllowed': False,
    'unknownOutcomeMustNeverBeRetried': True})
c.run('dispatch', submit, seconds=45)
save('manual-dispatch-selected-corrected-submitted.json', {'schema': 1, 'at': now(), 'head': head,
    'reservation': row(OUT / 'manual-dispatch-selected-corrected-once.json'), 'submitTerminal': c.records[-1],
    'remoteRunBindingPending': True, 'retryAllowed': False})
runs = json.loads(c.run('manual-after-runs'))
assert len(runs) == 1, 'Selected run not uniquely visible; allowance remains consumed, no dispatch retry'
manual = runs[0]
assert type(manual['id']) is int and manual['id'] > 0
assert manual['head_sha'] == head and manual['event'] == 'workflow_dispatch' and manual['run_attempt'] == 1
assert manual['workflow_id'] == b['registrations']['manual']['id'] and manual['path'] == S['manualHost']['workflow']
assert manual['name'] == b['registrations']['manual']['name']
check_sources()
save('manual-run-selected-corrected-binding.json', {'schema': 1, 'at': now(), 'head': head, 'tree': r['tree'],
    'selection': row(ROOT / SELECTION), 'reservation': row(OUT / 'manual-dispatch-selected-corrected-once.json'),
    'submitted': row(OUT / 'manual-dispatch-selected-corrected-submitted.json'), 'manual': manual,
    'dispatches': 1, 'retries': 0, 'expectedJobs': 1, 'expectedOwnedJavaCommands': 0, 'expectedChildCommands': [], 'jobNames': ['jdk-data'],
    'admissionAdapter': c.admission_adapter, 'authoritySnapshot': c.authority_row, 'commands': c.records, 'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True,
    'runtimeResultsAccepted': False, 'artifactDownloaded': False, 'signedArtifactURLsStoredOrPrinted': False,
    'allExistingHoldsUntouched': True})
print(json.dumps({'head': head, 'manualRunID': manual['id'], 'dispatches': 1,
    'closedCommands': len(c.records), 'runtimeResultsAccepted': False}))
