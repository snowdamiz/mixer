"""Freeze receipts and remove only this packet's recorded owned scratch."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,re,runpy,shutil,subprocess,tarfile
P=Path(__file__).resolve().parent;R=P.parents[1];S=P/'.scratch';O=P.parent/'swift-ordered-retention-diagnostic-rust'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def files(root,names):return {n:sha((root/n).read_bytes())for n in names}
def command(name):return json.loads((P/'commands'/name/'result.json').read_bytes())
def stdout(name):return (P/'commands'/name/'stdout.txt').read_text()
def cases(name):return re.findall(r'^test ([^ ]+) \.\.\.',stdout(name),re.M)
def counts(name):return [int(n)for n in re.findall(r'test result: ok\. (\d+) passed;',stdout(name))]
def main():
    verify=runpy.run_path(str(P/'prepare.py'));verify['verify_original']()
    base=json.loads((P/'baseline-manifest.json').read_bytes());candidate=json.loads((P/'candidate-manifest.json').read_bytes());assert len(base)==len(candidate)==132
    assert files(R/'vm',base)==base and files(S/'baseline',base)==base and files(S/'candidate',base)==candidate
    selected=['baseline-original-swift','candidate-final-exact-swift','baseline-generic-private','candidate-generic-private','baseline-generic-integration','candidate-generic-integration','host-custody-final','host-capture-final-exact','host-literal-final-exact']
    for n in selected:
        v=command(n);assert v['status']=='exited'and v['exitCode']==0 and v['live132Unchanged'],n
    assert counts('baseline-original-swift')==[340]and counts('candidate-final-exact-swift')==[362]
    original_cases=set(cases('baseline-original-swift'));new_cases=set(cases('candidate-final-exact-swift'));assert len(original_cases)==340 and original_cases<=new_cases and len(new_cases)==362
    comparisons={}
    for label in ('generic-private','generic-integration'):
        a='baseline-'+label;b='candidate-'+label
        assert cases(a)==cases(b) and counts(a)==counts(b)
        comparisons[label]={'namedCasesEqual':True,'passedCounts':counts(a),'rawStdoutSHA256':{a:sha((P/'commands'/a/'stdout.txt').read_bytes()),b:sha((P/'commands'/b/'stdout.txt').read_bytes())},'rawStdoutEqual':(P/'commands'/a/'stdout.txt').read_bytes()==(P/'commands'/b/'stdout.txt').read_bytes(),'scope':'semantic named cases/counts agree; raw outputs are retained without timing normalization'}
    ownership=json.loads((P/'scratch-ownership.json').read_bytes())
    reverse=S/'reversal';reverse.mkdir(exist_ok=False);st=reverse.stat();ownership['reversal']={'dev':st.st_dev,'ino':st.st_ino};dump(P/'scratch-ownership.json',ownership)
    for n in candidate:
        d=reverse/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(S/'candidate'/n,d)
    argv=['/usr/bin/patch','--batch','-R','-p1','-i',str(P/'candidate.patch')]
    result=subprocess.run(argv,cwd=reverse,capture_output=True,timeout=30);(P/'reversal-stdout.txt').write_bytes(result.stdout);(P/'reversal-stderr.txt').write_bytes(result.stderr)
    assert result.returncode==0 and files(reverse,base)==base
    dump(P/'reversal.json',{'argv':argv,'cwd':str(reverse),'exitCode':result.returncode,'all132Restored':True,'patchSHA256':sha(Path('/usr/bin/patch').read_bytes()),'patchVersion':subprocess.check_output(['/usr/bin/patch','--version'],text=True).strip()})
    artifacts={};(P/'binaries').mkdir(exist_ok=True)
    for label in ('build-baseline','build-candidate'):
        for f in sorted((S/label/'release/deps').glob('*')):
            if f.is_file()and os.access(f,os.X_OK)and f.name.startswith(('mixer_vm-','span_function_cache-','span_function_cache_allocations-')):
                raw=f.read_bytes();h=sha(raw);destination=P/'binaries'/(h+'.gz')
                if not destination.exists():destination.write_bytes(gzip.compress(raw,mtime=0))
                artifacts[str(f.relative_to(S))]={'bytes':len(raw),'sha256':h,'gzip':str(destination.relative_to(P))}
    dump(P/'binary-manifest.json',artifacts)
    raw_manifest={}
    with tarfile.open(P/'raw-fixtures.tar.gz','w:gz')as archive:
        for label in ('tmp-baseline','tmp-candidate'):
            for f in sorted((S/label).rglob('*')):
                if f.is_file()and not f.is_symlink():
                    relative=str(f.relative_to(S));raw=f.read_bytes();raw_manifest[relative]={'bytes':len(raw),'sha256':sha(raw)};archive.add(f,arcname=relative,recursive=False)
    dump(P/'raw-fixture-manifest.json',raw_manifest)
    out=stdout('candidate-final-exact-swift');line=re.search(r'COMPLETION_LAYOUT (.*)',out).group(1)
    layout={k:int(v)for k,v in re.findall(r'(\w+)=(\d+)',line)}
    phases={k:int(v)for k,v in re.findall(r'COMPLETION_PHASE ([\w-]+)=(\d+) cap=16384',out)}
    assert len(phases)==18 and max(phases.values())<=16384
    # A union of named owners/roles is reported separately from simultaneous
    # phase peaks; several full buffers intentionally coexist only on paper.
    union_roles={'tls':layout['tls'],'atomics':layout['atomics'],'supportedCodeLiterals':502,'receiptLiteralCharge':1024,'fourPaths':4*512,'writerLocal':layout['writer'],'writerOption':layout['writer_option'],'threeReceiptWriters':3*layout['receipt_writer'],'threeFormatterGroups':3*layout['formatter'],'debugHelpers':layout['debug_helpers'],'twoOutcomes':2*layout['outputs'],'threeCallbacks':3*layout['callback'],'fiveFrames':5*512,'digests':128,'twoEndReceipts':2*layout['receipt'],'guard':24,'beginRoles':layout['begin'],'metadataRoles':layout['metadata'],'formatBoundaryText':4096,'twoReadBlocks':2*512,'fourRecordRoles':4*128}
    row_roles=phases['post-retirement-row-reader']-(layout['tls']+layout['atomics']+502+2*512+layout['outputs']+4*128+3*layout['callback']+layout['metadata']+layout['receipt']+1024)
    union_roles.update(twoOriginalPinResults=2*layout['pin_result'],twoOriginalReleaseResults=2*layout['release_result'],threeCleanupFailureReturns=3*layout['failure'],threeCleanupUsageReturns=3*layout['usage'],displacedReservationTicket=24,returnedPinToken=24,rowSummary=row_roles)
    dump(P/'logical-inventory.json',{'layout':layout,'phases':phases,'peak':max(phases.values()),'ceiling':16384,'marginBytes':16384-max(phases.values()),'allPhaseNamedUnion':sum(union_roles.values()),'unionRoles':union_roles,'scope':'six selected completion paths/serializer/readers; pending independent lifetime review; no physical compiler/TLS/runtime/RSS claim'})
    sidecars=list((P/'streams').rglob('*.sidecar.json'));assert sidecars
    for f in sidecars:
        value=json.loads(f.read_bytes());assert value['status']=='invalid'and value['failure']==15 and 'fullReplayAccepted'not in value
    result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'bounded finite completion pending independent review; not complete Rust diagnostic acceptance','counts':{'baselineSwift':340,'candidateSwift':362,'inheritedFinite':16,'newFinite':6,'custodyControls':21},'genericComparisons':comparisons,'selectedCommands':{n:command(n)for n in selected},'allSidecarsInvalid':True,'sidecarCount':len(sidecars),'live132Unchanged':True,'originalPacketUnchanged':True,'cargoUnchanged':True,'noTargetNativeCaptureProcessDiscoveryCommitPush':True,'originalResultParityScope':'complete semantic fields excluding disclosed clock observations; raw originals preserved','foreignQuarantine':{'bytes':1,'liveTickets':1,'syntheticTicketOwnershipAdversity':True},'remaining':['independent completion source-lifetime/custody review','inherited CODE partial-buffer discard and stored-count mismatch','inherited receipt helper complete logical inventory','full semantic event replay/analyzer and complete source-code coverage','general concurrent INIT/finalization','target binding/driver/full Swift workload','physical compiler/TLS/OS/RSS memory','native/device/signing/store/provider/customer/operational/FieldLog/GA qualification']}
    dump(P/'result.json',result)
    for name,identity in ownership.items():
        f=S if name=='.'else S/name;st=f.stat();assert not f.is_symlink()and(st.st_dev,st.st_ino)==(identity['dev'],identity['ino']),name
    assert {f.name for f in S.iterdir()}==set(ownership)-{'.'}
    shutil.rmtree(S)
    if (P/'__pycache__').exists():shutil.rmtree(P/'__pycache__')
    verify['verify_original']();assert files(R/'vm',base)==base
    dump(P/'cleanup.json',{'ownedScratchRemoved':not S.exists(),'ownershipChecked':True,'removedNames':sorted(ownership),'rawFixturesPreserved':len(raw_manifest),'binariesPreserved':len(artifacts),'live132UnchangedAfterCleanup':True,'originalPacketUnchanged':True,'nativeCaptureOrOtherProjectProcessesTouched':False})
    contract=json.loads((P/'contract.json').read_bytes());contract.update(status='implemented-frozen-pending-independent-review',copiedCandidateMutated=True,syntheticTicketAdversityNeedsRootApproval=False,rootApproved=True,commandsRun=selected);dump(P/'contract.json',contract)
    print(json.dumps({'counts':result['counts'],'peak':max(phases.values()),'margin':16384-max(phases.values()),'sidecars':len(sidecars),'cleanup':True}))
if __name__=='__main__':main()
