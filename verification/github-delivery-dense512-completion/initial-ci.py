"""One bounded read-only initial snapshot; no dispatch or wait."""
import json
from owned import Commands,OUT,now,save
r=json.loads((OUT/'dispatch-receipt.json').read_bytes());head=r['head'];runid=r['run']['id']
c=Commands(120,4,'initial-ci-')
runs=json.loads(c.run('head-runs',['gh','api','repos/snowdamiz/mixer/actions/runs?head_sha='+head+'&per_page=20','--jq','.workflow_runs | map({id,name,head_sha,event,run_attempt,status,conclusion,path,html_url})']))
assert all(x['head_sha']==head for x in runs)
jobs=json.loads(c.run('completion-jobs',['gh','api','repos/snowdamiz/mixer/actions/runs/'+str(runid)+'/jobs?per_page=20','--jq','{total_count,jobs:[.jobs[]|{id,name,status,conclusion,started_at,completed_at,steps:[.steps[]|{number,name,status,conclusion}]}]}']))
save('initial-ci.json',{'schema':1,'at':now(),'head':head,'tree':r['tree'],'dispatchRun':runid,'headRuns':runs,'completionJobs':jobs,
    'commands':c.records,'allNewCommandsAdmittedReapedGroupsAbsentEOF':True,'actualRuntimeEvidenceReviewed':False,'productionOrGA':False})
print(json.dumps({'head':head,'runs':runs,'completionJobs':jobs,'cleanupVerified':True}))
