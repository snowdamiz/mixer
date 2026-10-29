"""One exact manifest-limited v2 commit and nonforce origin/main push."""
import hashlib, json, platform
from owned import Commands, OUT, ROOT, now, row, save
s=json.loads((OUT/'selection.json').read_bytes());pre=json.loads((OUT/'preflight.json').read_bytes())
assert not (OUT/'delivery-once.json').exists(),'delivery reserved; no automatic retry'
c=Commands(240,18,'delivery-')
assert c.run('branch',['git','branch','--show-current']).decode().strip()=='main'
assert c.run('base',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[s['base'],s['baseTree']]
assert c.run('remote-before',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
assert not c.run('index-before',['git','diff','--cached','--name-only','-z'])
for r in pre['metadataAfter']:assert row(ROOT/r['path'])==r,r['path']
for path,h in pre['protectedFilesUnchanged'].items():assert row(ROOT/path)['sha256']==h
d=ROOT/'verification/cache-fixture-shared-input-candidate-v2';seal=json.loads((d/'seal.json').read_bytes())
assert row(d/'seal.json')==pre['candidateSeal'] and row(d/'seal.json')['sha256']==s['candidateSealSHA256']
selected={d/'seal.json',*(d/m['path'] for m in seal['members']),*(ROOT/f for f in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json',s['workflow']['destination']))}
for m in seal['members']:assert all(row(d/m['path'])[k]==m[k] for k in ('bytes','sha256'))
owned=('selection.json','capacity-window-result.json','capacity-window-summary-seal.json','prior-diagnostic-summary.json','candidate-verification.json','preflight.json','owned.py','prepare.py','deliver.py','dispatch.py','README.md')
selected.update(OUT/f for f in owned)
assert (ROOT/s['workflow']['destination']).read_bytes()==(ROOT/s['workflow']['source']).read_bytes()
assert row(ROOT/s['workflow']['destination'])['sha256']==s['workflow']['sha256']
g=json.loads((ROOT/'gates/ga.json').read_bytes());assert [sum(x['status']==status for x in g['gates']) for status in ('running','planned','verified')]==[8,30,0]
members=[row(p) for p in sorted(selected)];total=sum(m['bytes'] for m in members)
assert total<6*1024*1024 and len(members)<80
assert not any('.wrangler' in m['path'] or m['path'] in pre['protectedFilesUnchanged'] or '/ci-review/' in m['path'] for m in members)
save('manifest.json',{'schema':1,'at':now(),'base':s['base'],'baseTree':s['baseTree'],'members':members,'selectedBytesExcludingManifest':total,'packetSizeCapBytes':6*1024*1024,'trackedExistingDependencyMembersVerified':pre['requiredTrackedSparseMembers'],'frozenPackDuplicated':False,'rawCIIncluded':False,'originalCandidateOrWorkflowModified':False,'otherOwnerFilesIncluded':False,'python':platform.python_version(),'versions':pre['versions'],'compilerRuntimeNativeUICaptureOrHeldProbeStarted':False,'runtimeReleaseOrGAAccepted':False})
paths=[m['path'] for m in members]+[str((OUT/'manifest.json').relative_to(ROOT))]
assert total+(OUT/'manifest.json').stat().st_size<6*1024*1024
with (OUT/'paths.nul').open('xb') as f:f.write(b''.join(p.encode()+b'\0' for p in paths))
save('delivery-once.json',{'at':now(),'base':s['base'],'manifest':row(OUT/'manifest.json'),'nonforcePushAuthorized':True,'retrySelected':False})
c.run('stage',['git','add','--force','--pathspec-from-file='+str(OUT/'paths.nul'),'--pathspec-file-nul'])
for r in members:assert row(ROOT/r['path'])==r,r['path']
index=set(filter(None,c.run('index-selected',['git','diff','--cached','--name-only','-z']).decode().split('\0')))
assert index==set(paths),(index-set(paths),set(paths)-index)
c.run('authored-check',['git','diff','--cached','--check','--',s['workflow']['destination'],'PLAN.md','STATUS.md','work-graph.json','gates/ga.json',*[str((OUT/f).relative_to(ROOT)) for f in owned]])
raw=c.run('staged-objects',['git','diff','--cached','--raw','--no-abbrev','-z']).split(b'\0');assert len(raw)%2==1
for i in range(0,len(raw)-1,2):
    h=raw[i].decode().split();path=raw[i+1].decode();assert len(h)==5 and h[-1] in ('A','M') and h[1] in ('100644','100755') and path in paths
    b=(ROOT/path).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==h[3]
c.run('commit',['git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-m','Deliver cwd-corrected shared-input fixture v2 diagnostic'])
head,tree=c.run('committed-head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()
assert set(filter(None,c.run('committed-paths',['git','diff-tree','--no-commit-id','--name-only','-r','-z','HEAD']).decode().split('\0')))==set(paths)
assert c.run('remote-prepush',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
c.run('push',['git','push','origin','HEAD:refs/heads/main'],seconds=45)
assert c.run('remote-postpush',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==head
assert not c.run('index-after',['git','diff','--cached','--name-only','-z'])
for path,h in pre['protectedFilesUnchanged'].items():assert row(ROOT/path)['sha256']==h
save('receipt.json',{'schema':1,'at':now(),'commit':head,'tree':tree,'base':s['base'],'pushed':True,'force':False,'manifest':row(OUT/'manifest.json'),'selectedMembersIncludingManifest':len(paths),'selectedBytesIncludingManifest':total+(OUT/'manifest.json').stat().st_size,'workflow':row(ROOT/s['workflow']['destination']),'allCommands':c.records,'allNewCommandsReapedGroupsAbsentAndEOF':True,'protectedFilesPreserved':True,'wranglerUntouched':True,'dispatchPending':True,'compilerRuntimeNativeUICaptureOrHeldProbeStarted':False,'runtimeReleaseOrGAAccepted':False})
print(json.dumps({'head':head,'tree':tree,'pushed':True,'force':False,'selectedFiles':len(paths),'selectedBytes':total+(OUT/'manifest.json').stat().st_size,'ownedCommands':len(c.records)}))
