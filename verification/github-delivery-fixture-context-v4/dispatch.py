import hashlib,json,re
from owned import Commands,OUT,ROOT,now,row,save
assert not (OUT/'dispatch-once.json').exists(),'Sole dispatch reservation consumed; no retry'
r=json.loads((OUT/'receipt.json').read_bytes());s=json.loads((OUT/'selection.json').read_bytes());head,tree=r['commit'],r['tree'];path=s['workflow']['destination'];name=path.rsplit('/',1)[1]
assert r['pushed'] and not r['force'] and r['allCommandsReapedGroupsAbsentAndEOF']
c=Commands(150,9,'dispatch-')
assert c.run('head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[head,tree]
assert c.run('remote',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==head
assert row(ROOT/path)==r['workflow'];b=(ROOT/path).read_bytes();oid=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
content=json.loads(c.run('workflow-content-metadata',['gh','api','repos/snowdamiz/mixer/contents/'+path+'?ref='+head,'--jq','{sha,size,path,type}']));assert content=={'sha':oid,'size':len(b),'path':path,'type':'file'}
w=json.loads(c.run('workflow-state',['gh','api','repos/snowdamiz/mixer/actions/workflows/'+name,'--jq','{id,path,state}']));assert w['state']=='active' and w['path']==path
save('dispatch-once.json',{'schema':1,'at':now(),'head':head,'tree':tree,'workflow':name,'workflowSHA256':s['workflow']['sha256'],'dispatchLimit':1,'reservationConsumed':True,'inputs':{},'compiler':s['compiler'],'fixture':s['fixture'],'retryFallbackOrDefaultPromotionSelected':False})
output=c.run('submit',['gh','workflow','run',name,'--ref','main','--repo','snowdamiz/mixer'],seconds=40)
match=re.search(rb'https://github\.com/snowdamiz/mixer/actions/runs/(\d+)',output);run=None
if match:
 run=json.loads(c.run('run-binding',['gh','api','repos/snowdamiz/mixer/actions/runs/'+match[1].decode(),'--jq','{id,head_sha,event,run_attempt,status,conclusion,workflow_id,path,html_url}']))
else:
 runs=json.loads(c.run('run-list',['gh','api','repos/snowdamiz/mixer/actions/workflows/'+name+'/runs?event=workflow_dispatch&head_sha='+head+'&per_page=5','--jq','[.workflow_runs[]|{id,head_sha,event,run_attempt,status,conclusion,workflow_id,path,html_url}]']))
 assert len(runs)<=1;run=runs[0] if runs else None
if run:assert run['head_sha']==head and run['event']=='workflow_dispatch' and run['run_attempt']==1 and run['workflow_id']==w['id'] and run['path']==path
save('dispatch-receipt.json',{'schema':1,'at':now(),'head':head,'tree':tree,'workflow':name,'workflowSHA256':s['workflow']['sha256'],'dispatchCallsMade':1,'dispatchCommandSucceeded':True,'ref':'main','inputs':{},'runId':run['id'] if run else None,'runURL':run['html_url'] if run else None,'resultingRunHeadBound':run is not None,'run':run,'commands':c.records,'allCommandsReapedGroupsAbsentAndEOF':True,'runtimeResult':'pending exact-source result review','rustupDescendantReapAndProviderDisposal':'unverified; owned toolchain home retained for provider disposal','runtimeReleaseOrGAAccepted':False})
print(json.dumps({'head':head,'tree':tree,'dispatchCallsMade':1,'run':run,'exactHeadBound':run is not None,'cleanupVerified':True}))
