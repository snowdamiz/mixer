"""One exact selected commit and nonforce origin/main push; no retry."""
import hashlib, json
from owned import Commands,OUT,ROOT,now,row,save
s=json.loads((OUT/'selection.json').read_bytes());pre=json.loads((OUT/'preflight.json').read_bytes())
assert not (OUT/'delivery-once.json').exists()
c=Commands(240,18,'delivery-')
assert c.run('branch',['git','branch','--show-current']).decode().strip()=='main'
assert c.run('base',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[s['base'],s['baseTree']]
assert c.run('remote-before',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
assert not c.run('index-before',['git','diff','--cached','--name-only','-z'])
selected=set()
for directory,key in [('swift-dense512-completion-experiment','candidateSealSHA256'),('swift-dense512-completion-independent','independentSealSHA256')]:
    d=ROOT/'verification'/directory;seal=json.loads((d/'seal.json').read_bytes())
    assert row(d/'seal.json')['sha256']==s[key]
    selected.add(d/'seal.json')
    for path,m in seal['files'].items():
        assert all(row(d/path)[k]==m[k] for k in ('bytes','sha256'));selected.add(d/path)
selected.update(ROOT/f for f in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json',s['workflow']['destination']))
selected.update(OUT/f for f in ('selection.json','fieldlog-nested-group-result.json','preflight.json','metadata-validation.json','README.md'))
selected.update(ROOT/'verification/github-delivery-shared-input-v2'/f for f in ('diagnostic-result.json','diagnostic-result-seal.json'))
assert (ROOT/s['workflow']['destination']).read_bytes()==(ROOT/s['workflow']['source']).read_bytes()
for path,h in pre['protectedFiles'].items():assert row(ROOT/path)['sha256']==h
for r in json.loads((OUT/'metadata-validation.json').read_bytes())['after']:assert row(ROOT/r['path'])==r
g=json.loads((ROOT/'gates/ga.json').read_bytes());assert [sum(x['status']==v for x in g['gates']) for v in ('running','planned','verified')]==[8,30,0]
members=[row(p) for p in sorted(selected)];total=sum(m['bytes'] for m in members)
assert len(members)<80 and total<6*1024*1024
assert not any('/ci-review/' in m['path'] or '.wrangler' in m['path'] or m['path'] in pre['protectedFiles'] for m in members)
save('manifest.json',{'schema':1,'at':now(),'base':s['base'],'baseTree':s['baseTree'],'members':members,'bytesExcludingManifest':total,
    'sizeCapBytes':6*1024*1024,'trackedSparseDependenciesAlreadyPresent':121,'rawCIOrBasePackCopiesPublished':False,
    'helperAndIndividualCommandReceiptsLocalOnly':True,'workflowSHA256':s['workflow']['sha256'],
    'sourceAcceptanceOnly':True,'actualCompilationFiniteHarnessGeometryAndFullRun':'pending','productionOrGA':False})
paths=[m['path'] for m in members]+[str((OUT/'manifest.json').relative_to(ROOT))]
assert total+(OUT/'manifest.json').stat().st_size<=6*1024*1024
with (OUT/'paths.nul').open('xb') as f:f.write(b''.join(p.encode()+b'\0' for p in paths))
save('delivery-once.json',{'at':now(),'base':s['base'],'manifest':row(OUT/'manifest.json'),'pushLimit':1,'nonforce':True,'retrySelected':False})
c.run('stage',['git','add','--force','--pathspec-from-file='+str(OUT/'paths.nul'),'--pathspec-file-nul'])
for r in members:assert row(ROOT/r['path'])==r
assert set(filter(None,c.run('index-selected',['git','diff','--cached','--name-only','-z']).decode().split('\0')))==set(paths)
c.run('authored-check',['git','diff','--cached','--check','--',s['workflow']['destination'],'PLAN.md','STATUS.md','work-graph.json','gates/ga.json',str(OUT.relative_to(ROOT))])
raw=c.run('staged-objects',['git','diff','--cached','--raw','--no-abbrev','-z']).split(b'\0');assert len(raw)%2==1
for i in range(0,len(raw)-1,2):
    h=raw[i].decode().split();path=raw[i+1].decode();assert len(h)==5 and h[-1] in ('A','M') and h[1] in ('100644','100755') and path in paths
    b=(ROOT/path).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==h[3]
c.run('commit',['git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-m','Select one bounded dense512 two-corpus completion experiment'])
head,tree=c.run('committed-head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()
assert set(filter(None,c.run('committed-paths',['git','diff-tree','--no-commit-id','--name-only','-r','-z','HEAD']).decode().split('\0')))==set(paths)
assert c.run('remote-prepush',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
c.run('push',['git','push','origin','HEAD:refs/heads/main'],seconds=45)
assert c.run('remote-postpush',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==head
assert not c.run('index-after',['git','diff','--cached','--name-only','-z'])
for path,h in pre['protectedFiles'].items():assert row(ROOT/path)['sha256']==h
save('receipt.json',{'schema':1,'at':now(),'commit':head,'tree':tree,'base':s['base'],'pushed':True,'force':False,
    'manifest':row(OUT/'manifest.json'),'selectedFilesIncludingManifest':len(paths),'selectedBytesIncludingManifest':total+(OUT/'manifest.json').stat().st_size,
    'workflow':row(ROOT/s['workflow']['destination']),'commands':c.records,'allNewCommandsAdmittedReapedGroupsAbsentEOF':True,
    'protectedFilesPreserved':True,'wranglerUntouched':True,'dispatchPending':True,'compilerRuntimeNativeUICaptureOrHeldProbeStarted':False,'productionOrGA':False})
print(json.dumps({'head':head,'tree':tree,'pushed':True,'force':False,'selectedFiles':len(paths),'selectedBytes':total+(OUT/'manifest.json').stat().st_size,'cleanupVerified':True}))
