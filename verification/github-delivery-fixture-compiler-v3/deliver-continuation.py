import hashlib,json,platform
from owned import Commands,OUT,ROOT,now,row,save
s=json.loads((OUT/'selection.json').read_bytes());pre=json.loads((OUT/'preflight.json').read_bytes());meta=json.loads((OUT/'metadata-binding.json').read_bytes())
assert not (OUT/'delivery-once.json').exists(),'Commit/push admission consumed; no automatic replay'
c=Commands(240,21,'delivery2-')
assert c.run('head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[s['base'],s['baseTree']]
assert c.run('branch',['git','branch','--show-current']).decode().strip()=='main'
assert c.run('remote-before',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
assert not c.run('index-before',['git','diff','--cached','--name-only','-z'])
assert set(filter(None,c.run('old-workflows',['git','diff','--name-only','-z','--','.github/workflows']).decode().split('\0'))) <= {'.github/workflows/hosted.yml'}
for r in meta['after'].values():assert row(ROOT/r['path'])==r,r['path']
for p,h in pre['protectedFiles'].items():assert row(ROOT/p)['sha256']==h,p
d=ROOT/'verification/cache-fixture-compiler-admission-v3';seal=json.loads((d/'seal.json').read_bytes())
assert row(d/'seal.json')['sha256']==s['candidateSealSHA256']
selected={d/'seal.json',*(d/m['path'] for m in seal['members']),*(ROOT/p for p in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json',s['workflow']['destination'])),*(OUT/p for p in ('selection.json','fieldlog-parent-sid-result.json','dependency-bindings.json','metadata-binding.json','candidate-verification.json'))}
for m in seal['members']:assert all(row(d/m['path'])[k]==m[k] for k in ('bytes','sha256'))
assert (ROOT/s['workflow']['destination']).read_bytes()==(ROOT/s['workflow']['source']).read_bytes()
deps=json.loads((OUT/'dependency-bindings.json').read_bytes())
for r in deps['members']:
 b=(ROOT/r['path']).read_bytes();assert row(ROOT/r['path'])=={k:r[k] for k in ('path','bytes','sha256')};assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['gitBlob']
assert not c.run('dependencies',['git','diff','--name-only','-z','--',*[r['path'] for r in deps['members']]])
g=json.loads((ROOT/'gates/ga.json').read_bytes());assert [sum(x['status']==status for x in g['gates']) for status in ('running','planned','verified')]==[8,30,0]
rows=[row(p) for p in sorted(selected)];total=sum(r['bytes'] for r in rows)
assert total<6*1024*1024 and len(rows)<40
assert not any('.wrangler' in r['path'] or r['path'] in pre['protectedFiles'] or '/ci-review/' in r['path'] or 'owned.py' in r['path'] for r in rows)
save('manifest.json',{'schema':1,'at':now(),'base':s['base'],'baseTree':s['baseTree'],'members':rows,'selectedBytesExcludingManifest':total,'capBytes':6*1024*1024,'versions':pre['versions'],'python':platform.python_version(),'trackedSparseDependencies':deps['trackedMembers'],'dependencies':row(OUT/'dependency-bindings.json'),'rawCIOrLocalHelpersIncluded':False,'basePackDuplicated':False,'sealedCandidateMembers':13,'candidateSeal':row(d/'seal.json'),'originalCandidateOrOldWorkflowModified':False,'localCompilerRustSwiftElixirProductRuntimeNativeUICaptureInventoryOrHeldProbeStarted':False,'runtimeReleaseOrGAAccepted':False})
paths=[r['path'] for r in rows]+[str((OUT/'manifest.json').relative_to(ROOT))]
assert total+(OUT/'manifest.json').stat().st_size<6*1024*1024
with (OUT/'paths.nul').open('xb') as f:f.write(b''.join(p.encode()+b'\0' for p in paths))
save('delivery-once.json',{'at':now(),'base':s['base'],'manifest':row(OUT/'manifest.json'),'oneNonforceOriginMainPushAuthorized':True,'retrySelected':False})
c.run('stage',['git','add','--force','--pathspec-from-file='+str(OUT/'paths.nul'),'--pathspec-file-nul'])
for r in rows:assert row(ROOT/r['path'])==r,r['path']
assert set(filter(None,c.run('index-selected',['git','diff','--cached','--name-only','-z']).decode().split('\0')))==set(paths)
c.run('check',['git','diff','--cached','--check'])
raw=c.run('staged-objects',['git','diff','--cached','--raw','--no-abbrev','-z']).split(b'\0');assert len(raw)%2==1
for i in range(0,len(raw)-1,2):
 h=raw[i].decode().split();p=raw[i+1].decode();assert len(h)==5 and h[-1] in ('A','M') and h[1] in ('100644','100755') and p in paths
 b=(ROOT/p).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==h[3]
c.run('commit',['git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-m','Deliver exact pinned compiler admission for cache fixture v3'])
head,tree=c.run('committed-head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()
assert set(filter(None,c.run('committed-paths',['git','diff-tree','--no-commit-id','--name-only','-r','-z','HEAD']).decode().split('\0')))==set(paths)
assert c.run('remote-prepush',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
c.run('push',['git','push','origin','HEAD:refs/heads/main'],seconds=45)
assert c.run('remote-postpush',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==head
assert not c.run('index-after',['git','diff','--cached','--name-only','-z'])
for p,h in pre['protectedFiles'].items():assert row(ROOT/p)['sha256']==h,p
save('receipt.json',{'schema':1,'at':now(),'commit':head,'tree':tree,'base':s['base'],'pushed':True,'force':False,'manifest':row(OUT/'manifest.json'),'selectedMembersIncludingManifest':len(paths),'selectedBytesIncludingManifest':total+(OUT/'manifest.json').stat().st_size,'workflow':row(ROOT/s['workflow']['destination']),'commands':c.records,'allCommandsReapedGroupsAbsentAndEOF':True,'dispatchPending':True,'protectedFilesPreserved':True,'wranglerUntouched':True,'localCompilerRuntimeNativeUICaptureInventoryOrHeldProbeStarted':False,'runtimeReleaseOrGAAccepted':False})
print(json.dumps({'head':head,'tree':tree,'pushed':True,'selectedFiles':len(paths),'selectedBytes':total+(OUT/'manifest.json').stat().st_size,'commands':len(c.records)}))
