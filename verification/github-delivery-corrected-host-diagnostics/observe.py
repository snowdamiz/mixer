"""One exact-head metadata snapshot and final local custody audit; no host acceptance."""
import json

from owned import Commands, OUT, ROOT, now, row, save

r = json.loads((OUT / 'receipt.json').read_bytes())
head, tree = r['head'], r['tree']
s = json.loads((ROOT / r['selection']['path']).read_bytes())
assert row(ROOT / r['selection']['path']) == r['selection']
manual = {name: json.loads((OUT / ('dispatch-' + name + '-receipt.json')).read_bytes())
          for name in ('lifecycle', 'envelope')}
assert all(d['exactHeadBound'] and d['dispatchCallsMade'] == 1 and d['head'] == head
           and d['manualBudgetRemaining'] == 0 for d in manual.values())
c = Commands(150, 10, 'observe-')
push_runs = json.loads(c.run('automatic-runs', ['gh', 'api',
    'repos/snowdamiz/mixer/actions/runs?head_sha=' + head + '&event=push&per_page=20',
    '--jq', '[.workflow_runs[]|{id,name,head_sha,event,run_attempt,status,conclusion,path,html_url}]']))
assert all(x['head_sha'] == head and x['event'] == 'push' for x in push_runs)
engine = [x for x in push_runs if x['path'] == '.github/workflows/verify.yml']
assert len(engine) == 1
engine_run = json.loads(c.run('engine-run', ['gh', 'api', 'repos/snowdamiz/mixer/actions/runs/' + str(engine[0]['id']),
    '--jq', '{id,name,head_sha,event,run_attempt,status,conclusion,path,html_url}']))
assert engine_run['head_sha'] == head and engine_run['event'] == 'push' and engine_run['run_attempt'] == 1
assert engine_run['path'] == '.github/workflows/verify.yml'
engine_jobs = json.loads(c.run('engine-jobs', ['gh', 'api', 'repos/snowdamiz/mixer/actions/runs/' + str(engine_run['id']) + '/jobs?per_page=20',
    '--jq', '[.jobs[]|{id,name,status,conclusion,steps:[.steps[]|{name,status,conclusion,number}]}]']))
observed = {}
for label, dispatch in manual.items():
    run_id = str(dispatch['runID'])
    run = json.loads(c.run(label + '-run', ['gh', 'api', 'repos/snowdamiz/mixer/actions/runs/' + run_id,
        '--jq', '{id,name,head_sha,event,run_attempt,status,conclusion,path,html_url}']))
    assert run['head_sha'] == head and run['event'] == 'workflow_dispatch' and run['run_attempt'] == 1
    assert run['path'] == '.github/workflows/' + dispatch['workflow']
    jobs = json.loads(c.run(label + '-jobs', ['gh', 'api', 'repos/snowdamiz/mixer/actions/runs/' + run_id + '/jobs?per_page=20',
        '--jq', '[.jobs[]|{id,name,status,conclusion,steps:[.steps[]|{name,status,conclusion,number}]}]']))
    observed[label] = {'run': run, 'jobs': jobs}
assert c.run('head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines() == [head, tree]
assert not c.run('index', ['git', 'diff', '--cached', '--name-only', '-z'])
assert c.run('remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [head, 'refs/heads/main']
for path, expected in s['protectedPaths'].items():
    actual = row(ROOT / path)
    assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256']
manifest = json.loads((OUT / 'manifest.json').read_bytes())
for expected in manifest['members']:
    assert row(ROOT / expected['path']) == expected
dependencies = json.loads((OUT / 'delivery-dependency-inventory.json').read_bytes())
for expected in dependencies['members']:
    actual = row(ROOT / expected['path'])
    assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256']
save('workflow-status-summary.json', {
    'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'automaticPushRuns': push_runs,
    'automaticEngine': engine_run, 'engineJobs': engine_jobs, 'manualDiagnostics': observed,
    'manualDispatches': 2, 'manualBudgetRemaining': 0, 'retryOrFallback': False,
    'commands': c.records, 'allCommandsDirectlyReapedOwnedGroupsAbsentPipesEOF': True,
    'scope': 'GitHub metadata only; actual retained compiler/test and final remote cleanup review pending',
    'nativePublishedPackageDogfoodReleaseOrGAAcceptance': False,
})
records = []
for p in sorted(OUT.glob('*.command.json')):
    value = json.loads(p.read_bytes())
    records.append({'file': p.name, **{k: value[k] for k in ('exit', 'admitted', 'stopReason', 'directChildReaped', 'ownedGroupAbsent', 'stdoutEOF', 'stderrEOF', 'sensitiveOutputRejected')}})
assert len(records) == 54
assert all(x['exit'] == 0 and x['admitted'] and x['stopReason'] is None and x['directChildReaped']
           and x['ownedGroupAbsent'] is True and x['stdoutEOF'] and x['stderrEOF']
           and not x['sensitiveOutputRejected'] for x in records)
assert not (OUT / 'CUSTODY-UNRESOLVED.json').exists()
save('handoff.json', {
    'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'remoteMainMatches': True,
    'indexEmpty': True, 'commitPushes': 1, 'force': False, 'selectedPaths': r['selectedPaths'],
    'selection': r['selection'], 'manifest': r['manifest'], 'manualDispatches': 2,
    'manualBudgetRemaining': 0, 'manualDiagnostics': {k: v['run'] for k, v in observed.items()},
    'automaticEngine': engine_run, 'workflowStatusSummary': row(OUT / 'workflow-status-summary.json'),
    'ownedCommandCount': len(records), 'successfulCommands': len(records),
    'allDirectReapsOwnedGroupsAbsentAndPipesEOF': True, 'unresolvedOwnedLocalCommands': 0,
    'retryOnUnknownOutcome': False, 'protectedFilesPreserved': True,
    'trackedDependenciesStillMatch': len(dependencies['members']),
    'canonicalVMSourceChanged': False, 'rootGlobalsWrittenByThisLane': False,
    'fieldlogOperations': 0, 'localCompilerProductRuntimeNativeUICaptureProcessInventoryHeldProbeStarted': False,
    'gates': s['gates'], 'releaseOrGAPromotion': False,
    'helperRawOutputInventoryArtifactCommitted': False, 'rootGlobalsReleased': True,
    'next': 'Root reviews actual remote results and may publish a small sanitized delivery summary separately.',
})
print(json.dumps({'head': head, 'automaticEngine': engine_run,
    'engineJobs': [{k: x[k] for k in ('name', 'status', 'conclusion')} for x in engine_jobs],
    'manualDiagnostics': {k: v['run'] for k, v in observed.items()},
    'ownedCommands': len(records), 'allOwnedCommandsClosed': True, 'indexEmpty': True,
    'protectedFilesPreserved': True, 'rootGlobalsReleased': True}))
