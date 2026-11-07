import json
from owned import Commands,OUT,ROOT,row,save,now
r=json.loads((OUT/'receipt.json').read_bytes());s=json.loads((OUT/'selection.json').read_bytes());submit=json.loads((OUT/'dispatch-submit.command.json').read_bytes())
assert submit['exit']==1 and submit['stopReason'] is None and all(submit[k] for k in ('directChildReaped','ownedGroupAbsent','stdoutEOF','stderrEOF'))
commands=[]
for p in sorted(OUT.glob('dispatch-*.command.json')):
 d=json.loads(p.read_bytes());commands.append({'name':p.name,**{k:d[k] for k in ('exit','stopReason','directChildReaped','ownedGroupAbsent','stdoutEOF','stderrEOF')}})
message=(OUT/'dispatch-submit.stderr').read_text().strip();assert 'HTTP 422' in message and "Unrecognized named-value: 'runner'" in message
save('dispatch-receipt.json',{'schema':1,'at':now(),'head':r['commit'],'tree':r['tree'],'workflow':s['workflow']['destination'],'dispatchCallsMade':1,'dispatchCommandSucceeded':False,'ref':'main','inputs':{},'runId':None,'runCreated':False,'resultingRunHeadBound':False,'failure':{'httpStatus':422,'workflowLine':22,'workflowColumn':20,'reason':"runner.temp is unavailable in the job-level env expression context",'message':message},'commands':commands,'allCommandsReapedGroupsAbsentAndEOF':True,'compilerInstallStarted':False,'fixtureStarted':False,'retryOrFallbackSelected':False,'runtimeReleaseOrGAAccepted':False})
c=Commands(60,2,'observe-')
runs=json.loads(c.run('push-runs',['gh','api','repos/snowdamiz/mixer/actions/runs?head_sha='+r['commit']+'&per_page=20','--jq','[.workflow_runs[]|{id,name,path,head_sha,event,run_attempt,status,conclusion,html_url}]']))
assert all(x['head_sha']==r['commit'] for x in runs)
save('workflow-status-summary.json',{'schema':1,'at':now(),'head':r['commit'],'tree':r['tree'],'runs':runs,'soleDispatch':'rejected HTTP422 before run creation','commands':c.records,'allCommandsReapedGroupsAbsentAndEOF':True,'compilerOrFixtureStarted':False,'sourceRuntimeOrGAAccepted':False})
print(json.dumps({'head':r['commit'],'tree':r['tree'],'dispatch':'HTTP422; no run','runs':runs}))
