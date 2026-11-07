"""Exact frozen source and tracked sparse closure; no compiler/runtime child."""
import hashlib, json, platform
from owned import Commands, OUT, ROOT, now, row, save
s=json.loads((OUT/'selection.json').read_bytes())
c=Commands(180,12,'preflight-')
versions={k:c.run(k+'-version',[k,'--version']).decode().strip().splitlines()[0] for k in ('git','gh')}
assert c.run('branch',['git','branch','--show-current']).decode().strip()=='main'
assert c.run('base',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[s['base'],s['baseTree']]
assert not c.run('index',['git','diff','--cached','--name-only','-z'])
assert c.run('remote',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
packets=[]
for name,key,count in [('swift-dense512-completion-experiment','candidateSealSHA256',27),('swift-dense512-completion-independent','independentSealSHA256',11)]:
    d=ROOT/'verification'/name; seal=json.loads((d/'seal.json').read_bytes())
    assert row(d/'seal.json')['sha256']==s[key] and seal['filesCount']==count and len(seal['files'])==count
    for path,m in seal['files'].items(): assert all(row(d/path)[k]==m[k] for k in ('bytes','sha256')),path
    packets.append({'seal':row(d/'seal.json'),'members':count,'bytes':sum(m['bytes'] for m in seal['files'].values())})
source=ROOT/s['workflow']['source']; destination=ROOT/s['workflow']['destination']
assert row(source)['sha256']==s['workflow']['sha256'] and not destination.exists()
prefixes=[line.strip()[1:] for line in source.read_text().splitlines() if line.strip().startswith('/verification/')]
dependencies=[p for p in prefixes if p!='verification/swift-dense512-completion-experiment/']
raw=c.run('sparse-index',['git','ls-files','--stage','-z','--',*dependencies])
closure=[]; indexed={}
for record in filter(None,raw.split(b'\0')):
    h,path=record.split(b'\t',1);mode,oid,stage=h.decode().split();path=path.decode()
    assert stage=='0' and mode in ('100644','100755')
    p=ROOT/path; r=row(p); b=p.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid,path
    indexed[path]=oid; closure.append({**r,'indexOID':oid})
for prefix in dependencies:
    path=ROOT/prefix
    if path.is_file(): assert prefix in indexed,prefix
    else:
        seal=json.loads((path/'seal.json').read_bytes())
        for name,m in seal['files'].items():
            member=path/name; assert str(member.relative_to(ROOT)) in indexed,name
            assert all(row(member)[k]==m[k] for k in ('bytes','sha256')),name
        assert str((path/'seal.json').relative_to(ROOT)) in indexed
assert not c.run('dependency-diff',['git','diff','--name-only','--',*dependencies])
prior=json.loads(c.run('prior-engine',['gh','api','repos/snowdamiz/mixer/actions/runs/40793273875','--jq','{id,head_sha,status,conclusion,html_url,jobs_url}']))
assert prior['head_sha']==s['base']
protected={'.github/workflows/hosted.yml':'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57','hosted/lib/mixer_hosted/browser_auth/store.ex':'8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
for path,h in protected.items(): assert row(ROOT/path)['sha256']==h
assert row(ROOT/s['latestFixtureResult']['path'])['sha256']==s['latestFixtureResult']['sha256']
assert row(ROOT/s['latestFieldLogResult']['path'])['sha256']==s['latestFieldLogResult']['sha256']
summaryseal=json.loads((ROOT/'verification/github-delivery-shared-input-v2/diagnostic-result-seal.json').read_bytes())
assert summaryseal['member']['sha256']==s['latestFixtureResult']['sha256']
destination.write_bytes(source.read_bytes())
save('preflight.json',{'schema':1,'at':now(),'base':s['base'],'baseTree':s['baseTree'],'python':platform.python_version(),
    'versions':versions,'packets':packets,'workflow':row(destination),'trackedSparseDependencyClosure':closure,
    'trackedSparseDependencyMembers':len(closure),'priorEngineRun':prior,'protectedFiles':protected,
    'commands':c.records,'allNewCommandsAdmittedReapedGroupsAbsentEOF':True,'wranglerUntouched':True,
    'compilerRuntimeNativeCaptureProcessInventoryOrHeldProbeStarted':False,'sourceRuntimeOrGAAccepted':False})
print(json.dumps({'trackedSparseDependencies':len(closure),'candidateFiles':27,'independentFiles':11,'priorEngine':prior,'cleanupVerified':True}))
