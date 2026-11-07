import hashlib, importlib.util,json,platform,shutil,sys
from owned import Commands,OUT,ROOT,now,row,save
s=json.loads((OUT/'selection.json').read_bytes());c=Commands(150,12,'preflight-')
assert c.run('head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[s['base'],s['baseTree']]
assert c.run('branch',['git','branch','--show-current']).decode().strip()=='main'
assert not c.run('index',['git','diff','--cached','--name-only','-z'])
assert c.run('remote',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
versions={x:c.run(x+'-version',[x,'--version']).decode().strip() for x in ('git','gh')}
d=ROOT/'verification/cache-fixture-workflow-context-v4';seal=json.loads((d/'seal.json').read_bytes())
assert row(d/'seal.json')['sha256']==s['candidateSealSHA256']
assert seal['member_count']==13 and seal['total_bytes']==62018 and seal['tree_sha256']==s['candidateTreeSHA256']
for m in seal['members']:assert all(row(d/m['path'])[k]==m[k] for k in ('bytes','sha256'))
old=ROOT/s['retireCanonical']['path'];assert row(old)['sha256']==s['retireCanonical']['mustMatchSHA256']
assert old.read_bytes()==(ROOT/s['retireCanonical']['preservedSource']).read_bytes()
dest=ROOT/s['workflow']['destination'];assert not dest.exists();shutil.copyfile(ROOT/s['workflow']['source'],dest)
assert row(dest)['sha256']==s['workflow']['sha256'];old.unlink()
sys.path.insert(0,str(d));spec=importlib.util.spec_from_file_location('fixture_v4_verify',d/'verify_candidate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
save('candidate-verification.json',{'at':now(),'source':row(d/'seal.json'),'installed':m.verify(True),'localCompilerOrRuntime':False,'officialValidatorPassed':False})
prior=json.loads((ROOT/'verification/github-delivery-fixture-compiler-v3/dependency-bindings.json').read_bytes());dep={r['path'] for r in prior['members']}
v3=ROOT/'verification/cache-fixture-compiler-admission-v3';v3seal=json.loads((v3/'seal.json').read_bytes());dep|={str((v3/'seal.json').relative_to(ROOT)),*(str((v3/x['path']).relative_to(ROOT)) for x in v3seal['members'])}
raw=c.run('dependency-index',['git','ls-files','--stage','-z','--',*sorted(dep)]);tracked={}
for item in raw.split(b'\0'):
 if item:
  meta,path=item.decode().split('\t');mode,oid,stage=meta.split();assert mode in ('100644','100755') and stage=='0';tracked[path]=oid
assert set(tracked)==dep
bindings=[]
for path in sorted(dep):
 b=(ROOT/path).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==tracked[path],path
 bindings.append({**row(ROOT/path),'gitBlob':tracked[path]})
assert not c.run('dependency-diff',['git','diff','--name-only','-z','--',*sorted(dep)])
protected={'.github/workflows/hosted.yml':'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57','hosted/lib/mixer_hosted/browser_auth/store.ex':'8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
for p,h in protected.items():assert row(ROOT/p)['sha256']==h,p
for record in (s['vmActualReview'],s['fieldlogLatest']):
 r=row(ROOT/record['path']);assert all(r[k]==record[k] for k in ('path','bytes','sha256'))
assert row(ROOT/'verification/github-delivery-dense512-completion/ci-review/seal.json')['sha256']==s['vmActualReview']['sealSHA256']
assert row(d/'logs/pure-controls.json')['sha256']==s['sourceControlReceiptSHA256']
engine=json.loads(c.run('previous-engine',['gh','api','repos/snowdamiz/mixer/actions/runs/40799063645','--jq','{id,head_sha,status,conclusion,html_url,jobs_url}']))
save('ordinary-engine-observation.json',{'at':now(),'run':engine,'oneInspectionOnly':True,'scope':'metadata only; job/test acceptance not inferred'})
save('dependency-bindings.json',{'schema':1,'at':now(),'base':s['base'],'members':bindings,'trackedMembers':len(bindings),'basePackDuplicated':False,'frozenV2AndV3SourcesUnchanged':True,'invalidV3CanonicalExcluded':True})
save('preflight.json',{'schema':1,'at':now(),'base':s['base'],'baseTree':s['baseTree'],'candidateSeal':row(d/'seal.json'),'retiredCanonicalV3':s['retireCanonical'],'dependencyBinding':row(OUT/'dependency-bindings.json'),'versions':versions,'python':platform.python_version(),'protectedFiles':protected,'allCommands':c.records,'allCommandsReapedGroupsAbsentAndEOF':True,'localCompilerRustSwiftElixirRuntimeNativeUICaptureInventoryOrHeldProbeStarted':False})
print(json.dumps({'preflight':'passed','candidateMembers':len(seal['members']),'trackedDependencyMembers':len(bindings),'commands':len(c.records),'previousEngine':engine}))
