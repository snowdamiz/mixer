import hashlib,json,platform
from owned import Commands,OUT,ROOT,now,row,save
s=json.loads((OUT/'selection.json').read_bytes());pre=json.loads((OUT/'preflight.json').read_bytes());meta=json.loads((OUT/'metadata-binding.json').read_bytes())
assert not (OUT/'delivery-once.json').exists(),'Commit/push admission consumed; no automatic replay'
c=Commands(240,16,'delivery-')
assert c.run('head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[s['base'],s['baseTree']]
assert c.run('branch',['git','branch','--show-current']).decode().strip()=='main'
assert c.run('remote-before',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
assert not c.run('index-before',['git','diff','--cached','--name-only','-z'])
for r in meta['after'].values():assert row(ROOT/r['path'])==r,r['path']
for p,h in pre['protectedFiles'].items():assert row(ROOT/p)['sha256']==h,p
d=ROOT/'verification/cache-fixture-workflow-context-v4';seal=json.loads((d/'seal.json').read_bytes());assert row(d/'seal.json')['sha256']==s['candidateSealSHA256']
selected={d/'seal.json',*(d/m['path'] for m in seal['members']),*(ROOT/p for p in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json',s['workflow']['destination'])),*(d/'logs'/p for p in ('pure-controls.json','pure-controls.stdout')),*(OUT/p for p in ('selection.json','fieldlog-absent-probe-result.json','dependency-bindings.json','metadata-binding.json','candidate-verification.json','ordinary-engine-observation.json')),*(ROOT/'verification/github-delivery-dense512-completion/ci-review'/p for p in ('receipt.json','seal.json'))}
for m in seal['members']:assert all(row(d/m['path'])[k]==m[k] for k in ('bytes','sha256'))
assert (ROOT/s['workflow']['destination']).read_bytes()==(ROOT/s['workflow']['source']).read_bytes();assert not (ROOT/s['retireCanonical']['path']).exists()
deps=json.loads((OUT/'dependency-bindings.json').read_bytes())
for r in deps['members']:
 b=(ROOT/r['path']).read_bytes();assert row(ROOT/r['path'])=={k:r[k] for k in ('path','bytes','sha256')};assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['gitBlob']
assert not c.run('dependencies',['git','diff','--name-only','-z','--',*[r['path'] for r in deps['members']]])
g=json.loads((ROOT/'gates/ga.json').read_bytes());assert [sum(x['status']==status for x in g['gates']) for status in ('running','planned','verified')]==[8,30,0]
rows=[row(p) for p in sorted(selected)];total=sum(r['bytes'] for r in rows);assert total<6*1024*1024 and len(rows)<40
assert not any('.wrangler' in r['path'] or r['path'] in pre['protectedFiles'] or '/ci-review/local/' in r['path'] or 'owned.py' in r['path'] for r in rows)
assert [r['path'] for r in rows if '/ci-review/' in r['path']]==['verification/github-delivery-dense512-completion/ci-review/receipt.json','verification/github-delivery-dense512-completion/ci-review/seal.json']
save('manifest.json',{'schema':1,'at':now(),'base':s['base'],'baseTree':s['baseTree'],'members':rows,'deletions':[s['retireCanonical']],'selectedBytesExcludingManifest':total,'capBytes':6*1024*1024,'versions':pre['versions'],'python':platform.python_version(),'trackedSparseDependencies':deps['trackedMembers'],'dependencies':row(OUT/'dependency-bindings.json'),'rawCIOrLocalHelpersIncluded':False,'basePackDuplicated':False,'sealedCandidateMembers':13,'candidateSeal':row(d/'seal.json'),'frozenV2AndV3SourceModified':False,'installedV2WorkflowModified':False,'retiredOnlyExactInvalidV3Canonical':True,'publicVMReviewOnly':True,'localCompilerRustSwiftElixirProductRuntimeNativeUICaptureInventoryOrHeldProbeStarted':False,'runtimeReleaseOrGAAccepted':False})
paths=[r['path'] for r in rows]+[str((OUT/'manifest.json').relative_to(ROOT)),s['retireCanonical']['path']]
assert total+(OUT/'manifest.json').stat().st_size<6*1024*1024
with (OUT/'paths.nul').open('xb') as f:f.write(b''.join(p.encode()+b'\0' for p in paths))
save('delivery-once.json',{'at':now(),'base':s['base'],'manifest':row(OUT/'manifest.json'),'oneCommitAndNonforceOriginMainPushAuthorized':True,'retrySelected':False})
c.run('stage',['git','add','--force','--pathspec-from-file='+str(OUT/'paths.nul'),'--pathspec-file-nul'])
for r in rows:assert row(ROOT/r['path'])==r,r['path']
assert set(filter(None,c.run('index-selected',['git','diff','--cached','--name-only','--no-renames','-z']).decode().split('\0')))==set(paths)
authored=[p for p in paths if not p.startswith('verification/cache-fixture-workflow-context-v4/')]
c.run('authored-check',['git','diff','--cached','--check','--',*authored])
raw=c.run('staged-objects',['git','diff','--cached','--raw','--no-abbrev','--no-renames','-z']).split(b'\0');assert len(raw)%2==1
for i in range(0,len(raw)-1,2):
 h=raw[i].decode().split();p=raw[i+1].decode();assert len(h)==5 and p in paths
 if p==s['retireCanonical']['path']:assert h[-1]=='D' and h[1]=='000000';continue
 assert h[-1] in ('A','M') and h[1] in ('100644','100755')
 b=(ROOT/p).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==h[3]
c.run('commit',['git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-m','Correct cache fixture workflow contexts and record accepted host evidence'])
head,tree=c.run('committed-head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()
assert set(filter(None,c.run('committed-paths',['git','diff-tree','--no-commit-id','--no-renames','--name-only','-r','-z','HEAD']).decode().split('\0')))==set(paths)
assert c.run('remote-prepush',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
c.run('push',['git','push','origin','HEAD:refs/heads/main'],seconds=45)
assert c.run('remote-postpush',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==head
assert not c.run('index-after',['git','diff','--cached','--name-only','-z'])
for p,h in pre['protectedFiles'].items():assert row(ROOT/p)['sha256']==h,p
save('receipt.json',{'schema':1,'at':now(),'commit':head,'tree':tree,'base':s['base'],'pushed':True,'force':False,'manifest':row(OUT/'manifest.json'),'selectedMembersIncludingManifestAndDeletion':len(paths),'selectedBytesIncludingManifest':total+(OUT/'manifest.json').stat().st_size,'workflow':row(ROOT/s['workflow']['destination']),'retiredCanonicalV3':s['retireCanonical'],'commands':c.records,'allCommandsReapedGroupsAbsentAndEOF':True,'dispatchPending':True,'protectedFilesPreserved':True,'wranglerUntouched':True,'localCompilerRuntimeNativeUICaptureInventoryOrHeldProbeStarted':False,'runtimeReleaseOrGAAccepted':False})
print(json.dumps({'head':head,'tree':tree,'pushed':True,'selectedPaths':len(paths),'selectedBytes':total+(OUT/'manifest.json').stat().st_size,'commands':len(c.records)}))
