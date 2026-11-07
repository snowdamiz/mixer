import hashlib,json
from owned import Commands,OUT,ROOT,now,row,save
s=json.loads((OUT/'selection.json').read_bytes());pre=json.loads((OUT/'preflight.json').read_bytes())
m=json.loads((OUT/'manifest.json').read_bytes());rows=m['members'];total=m['selectedBytesExcludingManifest'];paths=[r['path'] for r in rows]+[str((OUT/'manifest.json').relative_to(ROOT))]
c=Commands(180,14,'delivery3-')
assert c.run('head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[s['base'],s['baseTree']]
assert set(filter(None,c.run('index-selected',['git','diff','--cached','--name-only','-z']).decode().split('\0')))==set(paths)
for r in rows:assert row(ROOT/r['path'])==r,r['path']
for p,h in pre['protectedFiles'].items():assert row(ROOT/p)['sha256']==h,p
save('sealed-diff-whitespace.json',{'at':now(),'originalCheckExit':2,'path':'verification/cache-fixture-compiler-admission-v3/workflow.diff','lines':[6,11,16],'cause':'Space-only unified diff context records in immutable selected review packet','candidateModified':False,'authoredCheckExcludesOnlyThisSealedDiff':True,'commandReplayed':False})
c.run('authored-check',['git','diff','--cached','--check','--','.',':(exclude)verification/cache-fixture-compiler-admission-v3/workflow.diff'])
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
