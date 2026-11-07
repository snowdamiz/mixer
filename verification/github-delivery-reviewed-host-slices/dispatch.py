"""Exactly one manual pin bitmap dispatch after verified root-selected delivery."""
import hashlib
import json
import re
from owned import Commands, OUT, ROOT, now, row, save

r = json.loads((OUT / 'receipt.json').read_bytes())
s = json.loads((ROOT / 'verification/host-slice-selection-2026-10-29/selection.json').read_bytes())
assert row(ROOT / 'verification/host-slice-selection-2026-10-29/selection.json')['sha256'] == '48c02d1231ad81f13320ac914ac636f90b7f84eda2e97ecaaf3c096deaa941b6'
assert r['pushed'] and not r['force'] and r['allCommandsDirectlyReapedOwnedGroupsAbsentPipesEOF']
assert not (OUT / 'dispatch-once.json').exists(), 'Dispatch reservation consumed; no second attempt'
head, tree = r['head'], r['tree']
path = s['pinBitmap']['workflow']
name = path.rsplit('/', 1)[1]
assert name == 'swift-pin-bitmap-admission.yml' and s['pinBitmap']['input'] == {'profile': 'pin-bitmap-v1'}
c = Commands(150, 9, 'dispatch-')
assert c.run('head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines() == [head, tree]
assert c.run('remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == head
assert row(ROOT / path)['sha256'] == s['pinBitmap']['workflowSHA256']
raw = (ROOT / path).read_bytes()
oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
content = json.loads(c.run('workflow-content', ['gh', 'api', 'repos/snowdamiz/mixer/contents/' + path + '?ref=' + head,
    '--jq', '{sha,size,path,type}']))
assert content == {'sha': oid, 'size': len(raw), 'path': path, 'type': 'file'}
workflow = json.loads(c.run('workflow-state', ['gh', 'api', 'repos/snowdamiz/mixer/actions/workflows/' + name,
    '--jq', '{id,path,state}']))
assert workflow['state'] == 'active' and workflow['path'] == path
save('dispatch-once.json', {
    'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'workflow': name,
    'workflowSHA256': s['pinBitmap']['workflowSHA256'], 'dispatchLimit': 1,
    'reservationConsumedBeforeSubmit': True, 'inputs': {'profile': 'pin-bitmap-v1'},
    'ref': 'main', 'retryOnUnknownOutcome': False, 'wholeReactorAttempts': 0,
})
output = c.run('submit', ['gh', 'workflow', 'run', name, '--ref', 'main', '--repo', 'snowdamiz/mixer',
    '-f', 'profile=pin-bitmap-v1'], seconds=40)
match = re.search(rb'https://github\.com/snowdamiz/mixer/actions/runs/(\d+)', output)
if match:
    run = json.loads(c.run('run-binding', ['gh', 'api', 'repos/snowdamiz/mixer/actions/runs/' + match[1].decode(),
        '--jq', '{id,head_sha,event,run_attempt,status,conclusion,workflow_id,path,html_url}']))
else:
    runs = json.loads(c.run('run-list', ['gh', 'api', 'repos/snowdamiz/mixer/actions/workflows/' + name +
        '/runs?event=workflow_dispatch&head_sha=' + head + '&per_page=5',
        '--jq', '[.workflow_runs[]|{id,head_sha,event,run_attempt,status,conclusion,workflow_id,path,html_url}]']))
    assert len(runs) <= 1
    run = runs[0] if runs else None
if run:
    assert run['head_sha'] == head and run['event'] == 'workflow_dispatch' and run['run_attempt'] == 1
    assert run['workflow_id'] == workflow['id'] and run['path'] == path
save('dispatch-receipt.json', {
    'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'workflow': name,
    'workflowSHA256': s['pinBitmap']['workflowSHA256'], 'dispatchCallsMade': 1,
    'dispatchCommandSucceeded': True, 'ref': 'main', 'inputs': {'profile': 'pin-bitmap-v1'},
    'runID': run['id'] if run else None, 'run': run, 'exactHeadBound': run is not None,
    'commands': c.records, 'allCommandsDirectlyReapedOwnedGroupsAbsentPipesEOF': True,
    'actualHostRegressionResult': 'pending', 'manualBudgetRemaining': 0,
    'retryOrFallback': False, 'runtimeNativeReleaseOrGAAcceptance': False,
})
push_runs = json.loads(c.run('automatic-runs', ['gh', 'api',
    'repos/snowdamiz/mixer/actions/runs?head_sha=' + head + '&event=push&per_page=20',
    '--jq', '[.workflow_runs[]|{id,name,head_sha,event,status,conclusion,path,html_url}]']))
assert all(x['head_sha'] == head and x['event'] == 'push' for x in push_runs)
save('automatic-runs.json', {'schema': 1, 'at': now(), 'head': head, 'runs': push_runs,
    'command': c.records[-1], 'scope': 'metadata only; no test acceptance inferred'})
print(json.dumps({'head': head, 'manualRun': run, 'automaticPushRuns': push_runs,
                  'dispatchCallsMade': 1, 'commands': len(c.records)}))
