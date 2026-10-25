"""Archive only identity-owned review evidence and seal the bounded verdict."""
from pathlib import Path
import datetime,difflib,gzip,hashlib,json,os,sys,tarfile
from review import P,R,F,O,S,BASE,sha,put,tree,live,check_seal

EXPECTED='2e427447a34357ab4ff70eb220f56754f685a930edf4a89ebc29096fff3b73ba'
def captures():
    manifest={}
    with tarfile.open(P/'raw-fixtures.tar.gz','w:gz') as archive:
        for folder in ['tmp','host']:
            for p in sorted((S/folder).rglob('*')):
                if not p.is_file():continue
                name=str(p.relative_to(S));raw=p.read_bytes();manifest[name]={'bytes':len(raw),'sha256':sha(raw)}
                archive.add(p,arcname=name,recursive=False)
    put('raw-fixtures-manifest.json',manifest)
    binaries={};out=P/'binaries';out.mkdir(exist_ok=False)
    for folder in ['build-baseline','build-candidate']:
        for p in sorted((S/folder/'release/deps').glob('*')):
            if not p.is_file() or not os.stat(p).st_mode&0o111:continue
            raw=p.read_bytes();digest=sha(raw);name=str(p.relative_to(S));target=out/(digest+'.gz')
            if not target.exists():target.write_bytes(gzip.compress(raw,mtime=0))
            binaries[name]={'bytes':len(raw),'sha256':digest,'archive':str(target.relative_to(P)),'archiveSHA256':sha(target.read_bytes())}
    put('binary-manifest.json',binaries)
    put('closure-capture.json',{'rawFixtureMembers':len(manifest),'rawArchiveSHA256':sha((P/'raw-fixtures.tar.gz').read_bytes()),'binaries':len(binaries),'candidateRestored':tree(S/'candidate')==json.loads((P/'inputs/candidate-manifest.json').read_bytes()),'live132Unchanged':live()==BASE})
def summarize():
    assert live()==BASE
    seals={'completion':check_seal(F,EXPECTED),'original':check_seal(O,'c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf'),'originalReview':check_seal(P.parent/'swift-ordered-retention-diagnostic-rust-review','b5436299c6f89fd8cdb89d870d4816ecc66080588ce5867085df44f1ad791e78')}
    commands={}
    for p in sorted((P/'commands').iterdir()):
        if not (p/'result.json').exists():continue
        result=json.loads((p/'result.json').read_bytes());commands[p.name]=result
        for name,binding in result['outputs'].items():
            raw=(p/(name+'.txt')).read_bytes();assert len(raw)==binding['bytes'] and sha(raw)==binding['sha256']
    comparisons={}
    for kind in ['generic-private','generic-integration']:
        a=(P/'commands'/('baseline-'+kind)/'stdout.txt').read_bytes();b=(P/'commands'/('candidate-'+kind)/'stdout.txt').read_bytes()
        changes=list(difflib.unified_diff(a.decode().splitlines(),b.decode().splitlines()))
        comparisons[kind]={'rawStdoutEqual':a==b,'rawDiff':changes}
    inv=json.loads((P/'inventory-supplement.json').read_bytes());controls=json.loads((P/'independent-controls-2.json').read_bytes())
    assert controls['passed']==6 and not controls['errors'] and not controls['failures']
    assert json.loads((P/'cleanup.json').read_bytes())['scratchRemoved']
    put('result.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verdict':'accepted-selected-finite-completion-with-reviewer-inventory-supplement','scope':'six selected completion paths, finite custody and source logical inventory only; complete Rust diagnostic acceptance withheld','seals':seals,'counts':{'freshExactCandidateSwift':362,'originalMethodsIncluded':340,'inheritedFiniteIncluded':16,'newFiniteIncluded':6,'freshGenericPrivateEach':5,'freshGenericIntegrationsEach':[9,1],'freshProducerCustody':21,'independentControls':6,'reviewerActualLayoutMethod':1},'suiteCountsOverlap':True,'genericComparisons':comparisons,'selectedInventory':'independent supplement supersedes producer provisional16114; all19phases retained','correctedLogicalPeak':inv['correctedPeak'],'logicalCeiling':16384,'correctedMargin':inv['correctedMargin'],'correctedAllPhaseNamedRoleUnion':inv['correctedAllPhaseNamedRoleUnion'],'unionIsSimultaneousPeak':False,'hostCopyLogicalPeak':103777,'hostCopyLogicalCeiling':131072,'foreignCleanupInvariant':1,'foreignQuarantineBytes':1,'foreignQuarantineTickets':1,'fullReplayAccepted':False,'live132Unchanged':True,'noNativeCaptureUIProcessDiscovery':True,'commitsOrPushes':False,'reviewerFailuresRetained':['history/independent-attempt-1','history/layout-runner-syntax','history/raw-archive-verification'],'provisionalInventoryRetained':'history/inventory-supplement-1','commands':commands,'remaining':['inherited CODE partial-buffer discard/stored-count mismatch','inherited finite receipt full logical inventory','full event replay/analyzer and complete source-code coverage','general concurrent INIT/finalization','live integration/target driver/full Swift workload','physical compiler/TLS/OS/RSS memory','native/device/signing/store/customer/operational/published-package FieldLog/GA qualification']})
def seal():
    assert not S.exists();members=[]
    files=[R/'docs/swift-ordered-retention-diagnostic-completion-review.md']+[p for p in P.rglob('*') if p.is_file() and p.name not in ['seal.json','seal.sha256']]
    for p in sorted(files):
        assert not p.is_symlink();raw=p.read_bytes();members.append({'path':str(p.relative_to(R)),'bytes':len(raw),'sha256':sha(raw)})
    put('seal.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'bounded independent completion review; no GA or full replay acceptance','members':members,'excluded':[str((P/n).relative_to(R)) for n in ['seal.json','seal.sha256']]})
    (P/'seal.sha256').write_text(sha((P/'seal.json').read_bytes())+'\n')
    print(json.dumps({'sealSHA256':sha((P/'seal.json').read_bytes()),'members':len(members)}))
def verify():
    expected=(P/'seal.sha256').read_text().strip();info=check_seal(P,expected)
    assert live()==BASE and not S.exists()
    check_seal(F,EXPECTED)
    print(json.dumps({'review':info,'completionSealUnchanged':True,'live132Unchanged':True,'scope':'selected finite review only'}))
if __name__=='__main__':{'capture':captures,'summary':summarize,'seal':seal,'verify':verify}[sys.argv[1]]()
