"""One bounded exact-head metadata snapshot; no runtime acceptance inferred."""
import json
from owned import Commands, OUT, ROOT, now, row, save

r = json.loads((OUT / 'receipt.json').read_bytes())
d = json.loads((OUT / 'dispatch-receipt.json').read_bytes())
a = json.loads((OUT / 'automatic-runs.json').read_bytes())
head, tree = r['head'], r['tree']
engine = [x for x in a['runs'] if x['path'] == '.github/workflows/verify.yml']
assert len(engine) == 1 and d['exactHeadBound'] and d['dispatchCallsMade'] == 1
c = Commands(90, 7, 'observe-')
engine_run = json.loads(c.run('engine-run', ['gh', 'api', 'repos/snowdamiz/mixer/actions/runs/' + str(engine[0]['id']),
    '--jq', '{id,head_sha,event,run_attempt,status,conclusion,path,html_url}']))
assert engine_run['head_sha'] == head and engine_run['event'] == 'push' and engine_run['path'] == '.github/workflows/verify.yml'
engine_jobs = json.loads(c.run('engine-jobs', ['gh', 'api', 'repos/snowdamiz/mixer/actions/runs/' + str(engine_run['id']) + '/jobs?per_page=20',
    '--jq', '[.jobs[]|{id,name,status,conclusion,steps:[.steps[]|{name,status,conclusion,number}]}]']))
manual_run = json.loads(c.run('manual-run', ['gh', 'api', 'repos/snowdamiz/mixer/actions/runs/' + str(d['runID']),
    '--jq', '{id,head_sha,event,run_attempt,status,conclusion,path,html_url}']))
assert manual_run['head_sha'] == head and manual_run['event'] == 'workflow_dispatch' and manual_run['run_attempt'] == 1
assert manual_run['path'] == '.github/workflows/swift-pin-bitmap-admission.yml'
manual_jobs = json.loads(c.run('manual-jobs', ['gh', 'api', 'repos/snowdamiz/mixer/actions/runs/' + str(d['runID']) + '/jobs?per_page=20',
    '--jq', '[.jobs[]|{id,name,status,conclusion,steps:[.steps[]|{name,status,conclusion,number}]}]']))
assert c.run('head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines() == [head, tree]
assert not c.run('index', ['git', 'diff', '--cached', '--name-only', '-z'])
assert c.run('remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == head
selection = json.loads((ROOT / 'verification/host-slice-selection-2026-10-29/selection.json').read_bytes())
for path, expected in selection['preservation']['protectedLocalFiles'].items():
    assert row(ROOT / path)['sha256'] == expected['sha256']
save('workflow-status-summary.json', {
    'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'automaticEngine': engine_run,
    'engineJobs': engine_jobs, 'manualPinBitmap': manual_run, 'manualJobs': manual_jobs,
    'manualDispatches': 1, 'manualBudgetRemaining': 0, 'retryOrFallback': False,
    'commands': c.records, 'allCommandsDirectlyReapedOwnedGroupsAbsentPipesEOF': True,
    'scope': 'GitHub metadata only; actual retained compiler/test evidence and final cleanup review pending',
    'nativePublishedPackageDogfoodReleaseOrGAAcceptance': False,
})
records = []
for p in sorted(OUT.glob('*.command.json')):
    value = json.loads(p.read_bytes())
    records.append({'file': p.name, **{k: value[k] for k in ('exit', 'stopReason', 'directChildReaped', 'ownedGroupAbsent', 'stdoutEOF', 'stderrEOF')}})
assert len(records) == 42
assert all(x['directChildReaped'] and x['ownedGroupAbsent'] is True and x['stdoutEOF'] and x['stderrEOF'] for x in records)
assert sum(x['exit'] == 0 and x['stopReason'] is None for x in records) == 41
assert [x['file'] for x in records if x['stopReason']] == ['preflight-status.command.json']
save('handoff.json', {
    'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'remoteMainMatches': True,
    'indexEmpty': True, 'commitPushes': 1, 'force': False, 'selectedPaths': r['selectedPaths'],
    'selection': r['selection'], 'manifest': r['manifest'], 'manualDispatches': 1,
    'manualBudgetRemaining': 0, 'manualPinBitmap': manual_run, 'automaticEngine': engine_run,
    'workflowStatusSummary': row(OUT / 'workflow-status-summary.json'),
    'ownedCommandCount': len(records), 'successfulCommands': 41,
    'retainedBoundedFailure': 'full recursive inventory reached 1MiB stream cap; SIGTERM and complete cleanup verified',
    'all42DirectReapsOwnedGroupsAbsentAndPipesEOF': True,
    'unresolvedOwnedLocalCommands': 0, 'retryOnUnknownOutcome': False,
    'protectedFilesPreserved': True, 'canonicalVMSourceChanged': False,
    'rootGlobalsWrittenByThisLane': False, 'fieldlogOperations': 0,
    'localCompilerProductRuntimeNativeUICaptureInventoryHeldProbeStarted': False,
    'gates': selection['gates'], 'releaseOrGAPromotion': False,
    'helperRawOutputInventoryArtifactCommitted': False,
    'next': 'Root reviews actual remote results and may publish a small sanitized delivery summary separately.',
})
print(json.dumps({'head': head, 'engine': engine_run,
    'engineJobs': [{k:x[k] for k in ('name','status','conclusion')} for x in engine_jobs],
    'manual': manual_run, 'manualJobs': [{k:x[k] for k in ('name','status','conclusion')} for x in manual_jobs],
    'ownedCommands': len(records), 'allOwnedCommandsClosed': True, 'rootGlobalsReleased': True}))
