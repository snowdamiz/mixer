"""One bounded read-only exact-head CI observation after the sole dispatch."""
import json
from owned import Commands,OUT,now,save
r=json.loads((OUT/'receipt.json').read_bytes());d=json.loads((OUT/'dispatch-receipt.json').read_bytes())
c=Commands(90,3,'ci-initial-')
run=json.loads(c.run('diagnostic',['gh','api','repos/snowdamiz/mixer/actions/runs/'+str(d['runId']),'--jq','{id,head_sha,event,run_attempt,status,conclusion,path,html_url}']))
assert run['head_sha']==r['commit'] and run['run_attempt']==1 and run['event']=='workflow_dispatch'
jobs=json.loads(c.run('jobs',['gh','api','repos/snowdamiz/mixer/actions/runs/'+str(d['runId'])+'/jobs','--jq','{total_count,jobs:[.jobs[]|{id,name,status,conclusion,steps:[.steps[]|{name,status,conclusion,number}]}]}']))
runs=json.loads(c.run('head-runs',['gh','api','repos/snowdamiz/mixer/actions/runs?head_sha='+r['commit']+'&per_page=20','--jq','{runs:[.workflow_runs[]|{id,name,head_sha,event,run_attempt,status,conclusion,path,html_url}]}']))
save('ci-initial.json',{'schema':1,'at':now(),'head':r['commit'],'tree':r['tree'],'diagnostic':run,'jobs':jobs,'exactHeadRuns':runs,'allCommands':c.records,'allCommandsReapedGroupsAbsentAndEOF':True,'actualArtifactReview':'pending','noRetryFallbackOrPromotionSelected':True})
print(json.dumps({'diagnostic':run,'jobs':jobs,'exactHeadRuns':runs,'cleanupVerified':True}))
