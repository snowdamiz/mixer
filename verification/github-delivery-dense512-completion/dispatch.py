"""Consume exactly one dispatch reservation, on the verified delivered main."""
import base64,json,re
from owned import Commands,OUT,ROOT,now,row,save
assert not (OUT/'dispatch-once.json').exists(),'one-dispatch reservation already consumed; never retry'
r=json.loads((OUT/'receipt.json').read_bytes());s=json.loads((OUT/'selection.json').read_bytes())
assert r['pushed'] and not r['force'] and r['allNewCommandsAdmittedReapedGroupsAbsentEOF']
head,tree=r['commit'],r['tree'];path=s['workflow']['destination'];name=path.rsplit('/',1)[1]
c=Commands(150,8,'dispatch-')
assert c.run('head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[head,tree]
assert c.run('remote',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==head
assert row(ROOT/path)==r['workflow']
content=json.loads(c.run('workflow-content',['gh','api','repos/snowdamiz/mixer/contents/'+path+'?ref='+head]))
assert content['encoding']=='base64' and base64.b64decode(content['content'])==(ROOT/path).read_bytes()
w=json.loads(c.run('workflow-state',['gh','api','repos/snowdamiz/mixer/actions/workflows/'+name]))
assert w['state']=='active' and w['path']==path
save('dispatch-once.json',{'schema':1,'at':now(),'head':head,'tree':tree,'workflow':name,'workflowSHA256':s['workflow']['sha256'],
    'dispatchLimit':1,'reservationConsumed':True,'retryOrFallbackSelected':False,'inputs':{'profile':s['profile']},'bounds':s['bounds']})
output=c.run('submit',['gh','workflow','run',name,'--ref','main','--repo','snowdamiz/mixer','-f','profile='+s['profile']],seconds=40)
match=re.search(rb'https://github\.com/snowdamiz/mixer/actions/runs/(\d+)',output)
if match:
    run=json.loads(c.run('run-binding',['gh','api','repos/snowdamiz/mixer/actions/runs/'+match[1].decode(),'--jq','{id,head_sha,event,run_attempt,status,conclusion,workflow_id,path,html_url}']))
else:
    runs=json.loads(c.run('run-binding',['gh','api','repos/snowdamiz/mixer/actions/workflows/'+name+'/runs?event=workflow_dispatch&head_sha='+head+'&per_page=5','--jq','.workflow_runs | map({id,head_sha,event,run_attempt,status,conclusion,workflow_id,path,html_url})']))
    assert len(runs)==1,'dispatch made once; read-only binding needs later observation'
    run=runs[0]
assert run['head_sha']==head and run['event']=='workflow_dispatch' and run['run_attempt']==1 and run['workflow_id']==w['id'] and run['path']==path
save('dispatch-receipt.json',{'schema':1,'at':now(),'head':head,'tree':tree,'workflow':name,'workflowSHA256':s['workflow']['sha256'],
    'dispatchCallsMade':1,'dispatchCommandSucceeded':True,'ref':'main','inputs':{'profile':s['profile']},'run':run,
    'resultingRunHeadBound':True,'commands':c.records,'allNewCommandsAdmittedReapedGroupsAbsentEOF':True,
    'runtimeResult':'pending exact-source result review','productionOrGA':False})
print(json.dumps({'head':head,'tree':tree,'dispatchCallsMade':1,'profile':s['profile'],'run':run,'cleanupVerified':True}))
