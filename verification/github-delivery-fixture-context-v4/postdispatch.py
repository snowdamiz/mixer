import json
from owned import Commands,OUT,ROOT,now,row,save
r=json.loads((OUT/'receipt.json').read_bytes());d=json.loads((OUT/'dispatch-receipt.json').read_bytes());head,tree=r['commit'],r['tree'];assert d['runId'] and d['dispatchCallsMade']==1 and d['resultingRunHeadBound']
c=Commands(90,6,'observe-')
run=json.loads(c.run('fixture-run',['gh','api','repos/snowdamiz/mixer/actions/runs/'+str(d['runId']),'--jq','{id,head_sha,event,run_attempt,status,conclusion,workflow_id,path,html_url}']))
assert run['head_sha']==head and run['event']=='workflow_dispatch' and run['run_attempt']==1 and run['path']==r['workflow']['path']
jobs=json.loads(c.run('fixture-jobs',['gh','api','repos/snowdamiz/mixer/actions/runs/'+str(d['runId'])+'/jobs?per_page=20','--jq','[.jobs[]|{id,name,status,conclusion,steps:[.steps[]|{name,status,conclusion,number}]}]']))
push=json.loads(c.run('push-runs',['gh','api','repos/snowdamiz/mixer/actions/runs?head_sha='+head+'&event=push&per_page=20','--jq','[.workflow_runs[]|{id,name,head_sha,event,status,conclusion,path,html_url}]']))
assert all(x['head_sha']==head and x['event']=='push' for x in push)
save('workflow-status-summary.json',{'schema':1,'at':now(),'head':head,'tree':tree,'fixtureRun':run,'fixtureJobs':jobs,'automaticPushRuns':push,'scope':'GitHub metadata only; no compiler/fixture acceptance without actual retained result review','oneManualDispatchConsumed':True,'retryOrFallback':False,'rustupDescendantReapAndDisposalUnverified':True,'commands':c.records,'allCommandsReapedGroupsAbsentAndEOF':True,'runtimeReleaseOrGAAccepted':False})
before={p:row(ROOT/p) for p in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json')}
old='Actual GitHub parsing, compiler provisioning/identity and complete fixture execution remain pending.'
new=f'The slice is pushed as `{head[:8]}` and its sole new dispatch created [run {run["id"]}]({run["html_url"]}) at the exact source on attempt 1; the latest metadata status is {run["status"]}'+(f'/{run["conclusion"]}' if run['conclusion'] else '')+'. Dispatch authority is consumed. Compiler provisioning/identity and complete fixture acceptance remain pending actual result review.'
for name in ('PLAN.md','STATUS.md'):
 p=ROOT/name;text=p.read_text();assert text.count(old)==1;p.write_text(text.replace(old,new))
for name in ('work-graph.json','gates/ga.json'):
 p=ROOT/name;j=json.loads(p.read_bytes());rec=j['executionPolicy']['currentFixtureWorkflowContextV4Selection'];rec.update({'commit':head,'tree':tree,'deliveryStatus':'pushed nonforce; sole exact-head manual dispatch created','dispatchCallsMade':1,'run':run,'workflowStatusSummary':row(OUT/'workflow-status-summary.json'),'actualGitHubCompilerAndCompleteFixture':'GitHub service accepted manual dispatch; compiler/fixture result review pending','retryFallbackOrDefaultPromotion':False})
 for item in j.get('packages',j.get('gates',[])):
  if 'fixtureWorkflowContextV4Selection' in item:item['fixtureWorkflowContextV4Selection']=rec
 if name=='work-graph.json':j['updated']=now()
 p.write_text(json.dumps(j,indent=2)+'\n')
assert c.run('head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[head,tree]
assert not c.run('index',['git','diff','--cached','--name-only','-z'])
assert c.run('remote',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==head
pre=json.loads((OUT/'preflight.json').read_bytes())
for p,h in pre['protectedFiles'].items():assert row(ROOT/p)['sha256']==h
save('handoff.json',{'schema':1,'at':now(),'head':head,'tree':tree,'remoteMainMatches':True,'indexEmpty':True,'commitAndPushes':1,'manualDispatches':1,'manualDispatchBudgetRemaining':0,'fixtureRun':run,'fixtureJobs':jobs,'automaticPushRuns':push,'globalsHaveUncommittedConcreteDeliveryAndRunUpdate':True,'metadataBefore':before,'metadataAfter':{p:row(ROOT/p) for p in before},'doNotDispatchAgain':True,'allOwnedCommandsReapedGroupsAbsentAndEOF':True,'protectedFilesPreserved':True,'wranglerUntouched':True,'localCompilerRuntimeNativeUICaptureInventoryOrHeldProbeStarted':False,'runtimeReleaseOrGAAccepted':False})
print(json.dumps({'head':head,'tree':tree,'run':run,'jobs':jobs,'automaticPushRuns':push,'globalsReleased':True,'indexEmpty':True}))
