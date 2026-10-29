"""Bind automatic Engine and the one selected manual workflow to the delivered revision."""
import sys
sys.dont_write_bytecode = True
assert sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('android_selection_common', Path(__file__).with_name('selection_common_delivery.py'))
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
import hashlib
import json
for name in ('StrictCommands','BASE','TREE','S','SELECTION','ROWS','SELECTED','PROTECTED','ROOT','OUT','now','row','save','check_sources','bound_context','dispatch_input','ORDINARY_NAME'): globals()[name] = getattr(common,name)
context = bound_context()
head = context['DELIVERED_SHA']
r = json.loads((OUT / 'delivery-selected-receipt.json').read_bytes())
c = StrictCommands('ci-binding-selected', context)
assert c.run('head').decode().splitlines() == [head, r['tree']]
assert c.run('remote-main').decode().split() == [head, 'refs/heads/main']
contents, registrations = {}, {}
for label, source in (('engine', S['ordinaryHost']), ('manual', S['manualHost'])):
    path = source['workflow']
    payload = (ROOT / path).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == source['workflowSHA256']
    oid = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
    content = json.loads(c.run(label + '-workflow-content'))
    assert content == {'sha': oid, 'size': len(payload), 'path': path, 'type': 'file'}
    contents[label] = content
# Registration is separately bound; an old registration is never byte evidence.
for label, source in (('engine', S['ordinaryHost']), ('manual', S['manualHost'])):
    registration = json.loads(c.run(label + '-workflow-registration'))
    assert type(registration['id']) is int and registration['id'] > 0
    assert registration['state'] == 'active' and registration['path'] == source['workflow']
    registrations[label] = registration
assert registrations['engine']['name'] == ORDINARY_NAME
assert registrations['manual']['name'] == 'Android JDK file data observation DRAFT'
runs = json.loads(c.run('engine-run'))
assert len(runs) == 1, 'Automatic Engine binding pending or ambiguous; never dispatch Engine'
engine = runs[0]
assert type(engine['id']) is int and engine['id'] > 0
assert engine['head_sha'] == head and engine['event'] == 'push' and engine['run_attempt'] == 1
assert engine['workflow_id'] == registrations['engine']['id'] and engine['path'] == S['ordinaryHost']['workflow']
assert engine['name'] == ORDINARY_NAME
manual_before = json.loads(c.run('manual-before-runs'))
assert manual_before == [], 'Do not create an additional selected manual run'
check_sources()
save('ci-binding-selected.json', {'schema': 1, 'at': now(), 'head': head, 'tree': r['tree'],
    'selection': row(ROOT / SELECTION), 'delivery': row(OUT / 'delivery-selected-receipt.json'),
    'manifest': row(OUT / 'argv-ci-binding-selected.json'), 'contents': contents,
    'registrations': registrations, 'engine': engine, 'engineExpectedJobs': 6,
    'manualBeforeCount': 0, 'manualExpectedJobs': 1, 'manualExpectedOwnedJavaCommands': 0, 'manualExpectedChildCommands': [], 'manualJobNames': ['jdk-data'],
    'manualDispatchesPerformed': 0, 'admissionAdapter': c.admission_adapter, 'authoritySnapshot': c.authority_row, 'commands': c.records,
    'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True,
    'runtimeResultsAccepted': False, 'artifactDownloaded': False, 'signedArtifactURLsStoredOrPrinted': False})
print(json.dumps({'head': head, 'engineRunID': engine['id'], 'manualBeforeCount': 0,
    'closedCommands': len(c.records), 'runtimeResultsAccepted': False}))
