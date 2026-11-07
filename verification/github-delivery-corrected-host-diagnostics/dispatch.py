"""One separately reserved dispatch per exact root-selected diagnostic; no retries."""
import hashlib
import json
import re
import sys

from owned import Commands, OUT, ROOT, now, row, save

selection_path = 'verification/next-host-diagnostics-selection-2026-10-29/selection.json'
assert row(ROOT / selection_path)['sha256'] == '60ab18bb4ebfd736c64f8a56f9ca597086309f1c7bc49ccaa242f42f4d37511c'
s = json.loads((ROOT / selection_path).read_bytes())
r = json.loads((OUT / 'receipt.json').read_bytes())
m = json.loads((OUT / 'manifest.json').read_bytes())
assert r['pushed'] and not r['force'] and r['allCommandsDirectlyReapedOwnedGroupsAbsentPipesEOF']
head, tree = r['head'], r['tree']
assert len(sys.argv) == 2 and sys.argv[1] in ('lifecycle', 'envelope')
label = sys.argv[1]
workflow_names = {'lifecycle': 'swift-pin-bitmap-lifecycle-admission.yml',
                  'envelope': 'envelope-partition-diagnostic.yml'}
name = workflow_names[label]
dispatch = next(d for d in s['dispatches'] if d['workflow'] == name)
assert dispatch['maxAttempts'] == 1 and dispatch['attempt'] == 1
reservation = 'dispatch-' + label + '-once.json'
assert not (OUT / reservation).exists(), 'One-shot reservation consumed; do not retry'
inputs = {'profile': 'pin-bitmap-lifecycle-v2'} if label == 'lifecycle' else {'reviewed_sha': head}
if label == 'lifecycle':
    assert dispatch['profile'] == inputs['profile'] and dispatch['wholeReactorAttempts'] == 0
else:
    assert dispatch['inputs'] == {'reviewed_sha': 'exact delivered full HEAD'}
path = '.github/workflows/' + name
assert row(ROOT / path)['sha256'] == dispatch['workflowSHA256']
for expected in m['members']:
    assert row(ROOT / expected['path']) == expected, expected['path']
for protected, expected in s['protectedPaths'].items():
    actual = row(ROOT / protected)
    assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256']

c = Commands(150, 9, 'dispatch-' + label + '-')
assert c.run('head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines() == [head, tree]
assert c.run('remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [head, 'refs/heads/main']
assert not c.run('index', ['git', 'diff', '--cached', '--name-only', '-z'])
raw = (ROOT / path).read_bytes()
oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
content = json.loads(c.run('workflow-content', ['gh', 'api', 'repos/snowdamiz/mixer/contents/' + path + '?ref=' + head,
    '--jq', '{sha,size,path,type}']))
assert content == {'sha': oid, 'size': len(raw), 'path': path, 'type': 'file'}
workflow = json.loads(c.run('workflow-state', ['gh', 'api', 'repos/snowdamiz/mixer/actions/workflows/' + name,
    '--jq', '{id,path,state}']))
assert workflow['state'] == 'active' and workflow['path'] == path
assert c.run('remote-before-submit', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [head, 'refs/heads/main']
save(reservation, {
    'schema': 1, 'at': now(), 'selection': row(ROOT / selection_path), 'head': head, 'tree': tree,
    'workflow': name, 'workflowSHA256': dispatch['workflowSHA256'], 'dispatchLimit': 1,
    'reservationConsumedBeforeSubmit': True, 'inputs': inputs, 'ref': 'main',
    'retryOnUnknownOutcome': False, 'previousCommandsClosed': c.records,
})
argv = ['gh', 'workflow', 'run', name, '--ref', 'main', '--repo', 'snowdamiz/mixer']
for key, value in inputs.items():
    argv += ['-f', key + '=' + value]
output = c.run('submit', argv, seconds=40)
match = re.search(rb'https://github\.com/snowdamiz/mixer/actions/runs/(\d+)', output)
if match:
    run = json.loads(c.run('run-binding', ['gh', 'api', 'repos/snowdamiz/mixer/actions/runs/' + match[1].decode(),
        '--jq', '{id,name,head_sha,event,run_attempt,status,conclusion,workflow_id,path,html_url}']))
else:
    runs = json.loads(c.run('run-list', ['gh', 'api', 'repos/snowdamiz/mixer/actions/workflows/' + name +
        '/runs?event=workflow_dispatch&head_sha=' + head + '&per_page=5',
        '--jq', '[.workflow_runs[]|{id,name,head_sha,event,run_attempt,status,conclusion,workflow_id,path,html_url}]']))
    assert len(runs) <= 1, 'Ambiguous exact-head run binding; do not retry'
    run = runs[0] if runs else None
if run:
    assert run['head_sha'] == head and run['event'] == 'workflow_dispatch' and run['run_attempt'] == 1
    assert run['workflow_id'] == workflow['id'] and run['path'] == path
save('dispatch-' + label + '-receipt.json', {
    'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'workflow': name,
    'workflowSHA256': dispatch['workflowSHA256'], 'workflowID': workflow['id'],
    'dispatchCallsMade': 1, 'dispatchCommandSucceeded': True, 'ref': 'main', 'inputs': inputs,
    'runID': run['id'] if run else None, 'run': run, 'exactHeadBound': run is not None,
    'commands': c.records, 'allCommandsDirectlyReapedOwnedGroupsAbsentPipesEOF': True,
    'actualHostResult': 'pending', 'manualBudgetRemaining': 0,
    'retryOrFallback': False, 'runtimeNativeReleaseOrGAAcceptance': False,
})
print(json.dumps({'head': head, 'diagnostic': label, 'run': run,
     'dispatchCallsMade': 1, 'commands': len(c.records), 'retryOnUnknownOutcome': False}))
