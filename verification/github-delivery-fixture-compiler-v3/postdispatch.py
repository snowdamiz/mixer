import json
from owned import Commands,OUT,ROOT,now,row,save
r=json.loads((OUT/'receipt.json').read_bytes());dispatch=json.loads((OUT/'dispatch-receipt.json').read_bytes());observed=json.loads((OUT/'workflow-status-summary.json').read_bytes())
assert dispatch['dispatchCallsMade']==1 and not dispatch['dispatchCommandSucceeded'] and not dispatch['compilerInstallStarted'] and not dispatch['fixtureStarted']
for name in ('PLAN.md','STATUS.md'):
 p=ROOT/name;text=p.read_text();old='Actual provisioning, compiler identity and complete fixture execution remain pending.'
 new='The slice is pushed as `c62f80e3`; its sole dispatch is consumed and GitHub rejected it with HTTP 422 before a workflow-dispatch run was created: `runner.temp` is unavailable in the job-level environment expression. Push validation [40799062311](https://github.com/snowdamiz/mixer/actions/runs/40799062311) fails for that workflow. No compiler install or fixture execution started. A source-only workflow-context correction is required before any separately selected run. Ordinary Engine [40799063645](https://github.com/snowdamiz/mixer/actions/runs/40799063645) remains in progress at the latest observation.'
 assert text.count(old)==1;p.write_text(text.replace(old,new))
for name in ('work-graph.json','gates/ga.json'):
 p=ROOT/name;j=json.loads(p.read_bytes())
 def update(x):
  if isinstance(x,dict):
   for k,v in x.items():
    if k in ('fixtureCompilerV3Selection','currentFixtureCompilerV3Selection'):
     v.update(commit=r['commit'],tree=r['tree'],deliveryStatus='pushed nonforce; sole dispatch consumed and refused HTTP422 before workflow-dispatch run creation',dispatchCallsMade=1,dispatchCommandSucceeded=False,workflowDispatchRun=None,compilerInstallStarted=False,fixtureStarted=False,pushValidationRun=40799062311,pushValidationConclusion='failure',ordinaryEngineRun=40799063645,ordinaryEngineLatestStatus='in_progress',actualCompilerAndCompleteFixture='not started: GitHub expression validation rejects runner.temp in job-level env',next='Source-only workflow-context correction required; no further run selected',dispatchRefusal=dispatch['failure'])
    update(v)
  elif isinstance(x,list):
   for v in x:update(v)
 update(j)
 if name=='work-graph.json':j['updated']=now()
 p.write_text(json.dumps(j,indent=2)+'\n')
c=Commands(60,4,'final-')
assert c.run('head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[r['commit'],r['tree']]
assert c.run('remote',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==r['commit']
assert not c.run('index',['git','diff','--cached','--name-only','-z'])
manifest=json.loads((OUT/'manifest.json').read_bytes());immutable=[m for m in manifest['members'] if m['path'] not in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json')]
for m in immutable:assert row(ROOT/m['path'])==m,m['path']
pre=json.loads((OUT/'preflight.json').read_bytes())
for p,h in pre['protectedFiles'].items():assert row(ROOT/p)['sha256']==h,p
commands=[]
for p in sorted(OUT.glob('*.command.json')):
 d=json.loads(p.read_bytes());assert all(d[k] for k in ('directChildReaped','ownedGroupAbsent','stdoutEOF','stderrEOF')),p.name
 commands.append({'name':p.name,**{k:d[k] for k in ('exit','stopReason','directChildReaped','ownedGroupAbsent','stdoutEOF','stderrEOF')}})
save('handoff.json',{'schema':1,'at':now(),'head':r['commit'],'tree':r['tree'],'pushed':True,'selectedFiles':r['selectedMembersIncludingManifest'],'selectedBytes':r['selectedBytesIncludingManifest'],'dispatchCallsMade':1,'dispatchRefusedHTTP422':True,'selectedWorkflowDispatchRun':None,'workflowValidationPushRun':40799062311,'ordinaryEngine':{'run':40799063645,'status':'in_progress'},'allLocalOwnedGitGhCommands':commands,'allCommandsReapedGroupsAbsentAndEOF':True,'globalsReleased':True,'globalsPostdispatchStatusUncommitted':{p:row(ROOT/p) for p in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json')},'sealedCandidateAndOldDependenciesUnchanged':True,'protectedFilesPreserved':True,'noFurtherCommitPushOrDispatchAuthorizedOrAttempted':True,'compilerRuntimeNativeUICaptureInventoryHeldProbeStarted':False,'gates':{'running':8,'planned':30,'verified':0},'runtimeReleaseOrGAAccepted':False})
print(json.dumps({'head':r['commit'],'tree':r['tree'],'dispatchCallsMade':1,'dispatchRun':None,'pushValidationRun':40799062311,'engineRun':40799063645,'allLocalGitGhCommandsClosed':len(commands),'globalsReleased':True}))
