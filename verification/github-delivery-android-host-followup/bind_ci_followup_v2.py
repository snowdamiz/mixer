"""Bind automatic Engine and both independently selected manual workflows to delivered bytes."""
import sys
sys.dont_write_bytecode = True
assert sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('android_host_followup_delivery_common', Path(__file__).with_name('selection_common_delivery_followup_v2.py'))
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
import hashlib
import json
for name in ('StrictCommands', 'S', 'SELECTION', 'ROOT', 'OUT', 'now', 'row', 'save', 'check_sources', 'bound_context', 'manual_binding', 'ORDINARY_NAME'):
    globals()[name] = getattr(common, name)
context = bound_context()
head = context['DELIVERED_SHA']
r = json.loads((OUT / 'delivery-followup-receipt.json').read_bytes())
c = StrictCommands('ci-binding-followup', context)
assert c.run('head').decode().splitlines() == [head, r['tree']]
assert c.run('remote-main').decode().split() == [head, 'refs/heads/main']
contents, registrations = {}, {}
sources = [('engine', S['ordinaryHost']), ('axis', S['manualHosts']['axis']), ('package', S['manualHosts']['package'])]
for label, source in sources:
    path = source['workflow']
    payload = (ROOT / path).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == source['workflowSHA256']
    oid = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
    content = json.loads(c.run(label + '-workflow-content'))
    assert content == {'sha': oid, 'size': len(payload), 'path': path, 'type': 'file'}
    contents[label] = content
for label, source in sources:
    registration = json.loads(c.run(label + '-workflow-registration'))
    assert type(registration['id']) is int and registration['id'] > 0
    assert registration['state'] == 'active' and registration['path'] == source['workflow']
    registrations[label] = registration
assert registrations['engine']['name'] == ORDINARY_NAME
for key in ('axis', 'package'):
    assert registrations[key]['name'] == S['manualHosts'][key]['workflowName']
runs = json.loads(c.run('engine-run'))
assert len(runs) == 1, 'Automatic Engine binding pending or ambiguous; never dispatch Engine'
engine = runs[0]
assert type(engine['id']) is int and engine['id'] > 0
assert engine['head_sha'] == head and engine['event'] == 'push' and engine['run_attempt'] == 1
assert engine['workflow_id'] == registrations['engine']['id'] and engine['path'] == S['ordinaryHost']['workflow']
assert engine['name'] == ORDINARY_NAME
manuals = {}
for key in ('axis', 'package'):
    assert json.loads(c.run(key + '-before-runs')) == [], 'Existing selected manual run; never create an additional run'
    manuals[key] = {'beforeCount': 0, 'binding': manual_binding(key), 'expectedJobs': S['manualHosts'][key]['expectedJobs'], 'expectedJobName': S['manualHosts'][key]['expectedJobName']}
c.complete()
check_sources()
save('ci-binding-followup.json', {'schema': 1, 'at': now(), 'head': head, 'tree': r['tree'],
     'selection': row(ROOT / SELECTION), 'delivery': row(OUT / 'delivery-followup-receipt.json'),
     'manifest': row(OUT / 'argv-ci-binding-followup.json'), 'contents': contents, 'registrations': registrations,
     'engine': engine, 'engineExpectedJobs': 6, 'manuals': manuals, 'manualDispatchesPerformed': 0,
     'admissionAdapter': c.admission_adapter, 'authoritySnapshot': c.authority_row, 'commands': c.records,
     'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True,
     'runtimeResultsAccepted': False, 'artifactDownloaded': False, 'signedArtifactURLsStoredOrPrinted': False})
print(json.dumps({'head': head, 'engineRunID': engine['id'], 'manualBeforeCounts': {key: 0 for key in manuals}, 'closedCommands': len(c.records), 'runtimeResultsAccepted': False}))
