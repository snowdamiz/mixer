import hashlib,json,platform,shutil
from owned import Commands,OUT,ROOT,now,row,save
s=json.loads((OUT/'selection.json').read_bytes());c=Commands(120,12,'preflight-')
assert c.run('head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[s['base'],s['baseTree']]
assert c.run('branch',['git','branch','--show-current']).decode().strip()=='main'
assert not c.run('index',['git','diff','--cached','--name-only','-z'])
assert c.run('remote',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
versions={x:c.run(x+'-version',[x,'--version']).decode().strip() for x in ('git','gh')}
d=ROOT/'verification/cache-fixture-compiler-admission-v3';seal=json.loads((d/'seal.json').read_bytes())
assert row(d/'seal.json')['sha256']==s['candidateSealSHA256']
assert seal['member_count']==13 and seal['total_bytes']==49908 and seal['tree_sha256']==s['candidateTreeSHA256']
assert hashlib.sha256(json.dumps(seal['members'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==s['candidateTreeSHA256']
for m in seal['members']:assert all(row(d/m['path'])[k]==m[k] for k in ('bytes','sha256'))
dest=ROOT/s['workflow']['destination'];assert not dest.exists();shutil.copyfile(ROOT/s['workflow']['source'],dest)
assert row(dest)['sha256']==s['workflow']['sha256']
old=json.loads((ROOT/'verification/github-delivery-shared-input-v2/preflight.json').read_bytes())
dep={r['path'] for r in old['dependencyClosure']}
v2=ROOT/'verification/cache-fixture-shared-input-candidate-v2';v2seal=json.loads((v2/'seal.json').read_bytes())
dep|={str((v2/'seal.json').relative_to(ROOT)),*(str((v2/m['path']).relative_to(ROOT)) for m in v2seal['members'])}
dep|={'.github/workflows/cache-fixture-shared-input-controls-v2.yml'}
raw=c.run('dependency-index',['git','ls-files','--stage','-z','--',*sorted(dep)])
tracked={}
for item in raw.split(b'\0'):
 if item:
  meta,path=item.decode().split('\t');mode,oid,stage=meta.split();assert mode in ('100644','100755') and stage=='0';tracked[path]=oid
assert set(tracked)==dep
bindings=[]
for path in sorted(dep):
 b=(ROOT/path).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==tracked[path],path
 bindings.append({**row(ROOT/path),'gitBlob':tracked[path]})
assert not c.run('dependency-diff',['git','diff','--name-only','-z','--',*sorted(dep)])
protected={'.github/workflows/hosted.yml':'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57','hosted/lib/mixer_hosted/artifacts/store.ex':'8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
for p,h in protected.items():assert row(ROOT/p)['sha256']==h,p
assert row(OUT/'fieldlog-parent-sid-result.json')==s['fieldlogLatest']
save('dependency-bindings.json',{'schema':1,'at':now(),'base':s['base'],'members':bindings,'trackedMembers':len(bindings),'basePackDuplicated':False,'oldV2AndWorkflowUnchanged':True})
save('preflight.json',{'schema':1,'at':now(),'base':s['base'],'baseTree':s['baseTree'],'candidateSeal':row(d/'seal.json'),'dependencyBinding':row(OUT/'dependency-bindings.json'),'versions':versions,'python':platform.python_version(),'protectedFiles':protected,'allCommands':c.records,'allCommandsReapedGroupsAbsentAndEOF':True,'localCompilerRustSwiftElixirRuntimeNativeUICaptureInventoryOrHeldProbeStarted':False})
print(json.dumps({'preflight':'passed','candidateMembers':len(seal['members']),'trackedDependencyMembers':len(bindings),'commands':len(c.records)}))
