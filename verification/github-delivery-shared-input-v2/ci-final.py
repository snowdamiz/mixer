"""Fresh bounded read-only final Engine observation; no retry or dispatch."""
import json
from owned import Commands,OUT,now,save
r=json.loads((OUT/'receipt.json').read_bytes());c=Commands(90,2,'ci-final-')
run=json.loads(c.run('engine',['gh','api','repos/snowdamiz/mixer/actions/runs/40793273875','--jq','{id,head_sha,event,run_attempt,status,conclusion,path,html_url}']))
assert run['head_sha']==r['commit'] and run['event']=='push' and run['run_attempt']==1
jobs=json.loads(c.run('engine-jobs',['gh','api','repos/snowdamiz/mixer/actions/runs/40793273875/jobs','--jq','{total_count,jobs:[.jobs[]|{id,name,status,conclusion}]}']))
save('ci-final.json',{'schema':1,'at':now(),'head':r['commit'],'tree':r['tree'],'engine':run,'jobs':jobs,'allCommands':c.records,'allCommandsReapedGroupsAbsentAndEOF':True,'diagnosticResult':'diagnostic-result.json','nativeRuntimeReleaseOrGAAccepted':False})
print(json.dumps({'engine':run,'jobs':jobs,'allReapedGroupsAbsentEOF':True}))
