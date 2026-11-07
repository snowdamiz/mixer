"""Bounded read-only artifact acquisition; raw archive stays local."""
import hashlib,io,json,stat,zipfile
from pathlib import PurePosixPath
from owned import Commands,OUT,now,save
d=json.loads((OUT/'dispatch-receipt.json').read_bytes());c=Commands(150,2,'ci-artifact-')
response=json.loads(c.run('inventory',['gh','api','repos/snowdamiz/mixer/actions/runs/'+str(d['runId'])+'/artifacts','--jq','{total_count,artifacts:[.artifacts[]|{id,name,size_in_bytes,digest,expired}]}']))
assert response['total_count']==1 and len(response['artifacts'])==1
a=response['artifacts'][0];assert not a['expired'] and a['size_in_bytes']<2*1024*1024 and str(d['runId']) in a['name'] and d['head'] in a['name']
data=c.run('download',['gh','api','repos/snowdamiz/mixer/actions/artifacts/'+str(a['id'])+'/zip'],seconds=50)
h=hashlib.sha256(data).hexdigest();assert a['digest']=='sha256:'+h,(a['digest'],h)
review=OUT/'ci-review';review.mkdir(exist_ok=False);(review/'artifact.zip').write_bytes(data)
target=review/'artifact';target.mkdir();members=[]
with zipfile.ZipFile(io.BytesIO(data)) as z:
    infos=z.infolist();assert len(infos)<500 and sum(i.file_size for i in infos)<32*1024*1024
    names=set()
    for i in infos:
        p=PurePosixPath(i.filename);assert not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename and i.filename not in names
        assert not stat.S_ISLNK(i.external_attr>>16);names.add(i.filename)
        if i.is_dir():continue
        b=z.read(i);f=target/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b)
        members.append({'path':i.filename,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
save('ci-review/acquisition.json',{'schema':1,'at':now(),'head':d['head'],'tree':d['tree'],'runId':d['runId'],'attempt':1,'artifact':a,'archiveBytes':len(data),'archiveSHA256':h,'rawLocalOnly':True,'members':members,'allCommands':c.records,'allCommandsReapedGroupsAbsentAndEOF':True})
print(json.dumps({'run':d['runId'],'artifactId':a['id'],'archiveBytes':len(data),'sha256':h,'members':len(members),'rawLocalOnly':True,'allReapedGroupsAbsentEOF':True}))
