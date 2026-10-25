from pathlib import Path
import datetime,hashlib,json,os,subprocess,shutil,tarfile,io,platform
H=Path(__file__).resolve().parent;R=H.parents[1];S=H/'owned-scratch'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def write(n,x):(H/n).write_bytes(enc(x))
original=json.loads((H/'input-source-manifest.json').read_text())
assert all(sha(R/'vm'/n)==v for n,v in original.items())
input_packets={n:sha(R/n) for n in ('verification/swift-exact-reactor-after-resident-index/result-seal.json','verification/swift-exact-reactor-after-resident-index/result-receipt.json')}
assert input_packets['verification/swift-exact-reactor-after-resident-index/result-seal.json']=='05d31bc936466d9dd6c2b21c411e30e75087396e6f6903a0e6fc597f401948fd'
assert input_packets['verification/swift-exact-reactor-after-resident-index/result-receipt.json']=='2f5d03babfa28f8fad02dced2fc480f68fdd0ff5a8b2f9e2286da42447022d77'
write('input-result-audit.json',{'expectedHashesVerified':input_packets,'sourceLiveMembersStillUnchanged':132,'targetReexecuted':False})
trace={}
for kind in ('baseline','grouped'):
    raw=(H/'commands'/f'{kind}-frozen/stdout').read_bytes()
    start=raw.index(b'layout FunctionCache ');end=raw.rindex(b'\nok\n')
    trace[kind]=raw[start:end]+b'\n'
assert trace['baseline']==trace['grouped']
(H/'literal-frozen-trace.txt').write_bytes(trace['grouped'])
write('frozen-comparison.json',{'baselineCommand':'commands/baseline-frozen','groupedCommand':'commands/grouped-frozen','equal':True,'bytes':len(trace['grouped']),'sha256':sha(H/'literal-frozen-trace.txt'),'extraction':'From literal layout FunctionCache through final allocation release line, excluding libtest prefix/footer.'})
tools=[]
for argv in (['/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc','--version','--verbose'],['/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo','--version'],['python3','--version'],['/usr/bin/uname','-a']):
    p=subprocess.run(argv,capture_output=True,text=True,check=True)
    tools.append({'argv':argv,'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
write('tools.json',{'commands':tools,'platform':platform.platform(),'pythonVersion':platform.python_version()})
receipts={str(p.parent.relative_to(H)):json.loads(p.read_text()) for p in sorted((H/'commands').glob('*/receipt.json'))}
assert len(receipts)==11
expected={'baseline-diagnosis':(0,2),'grouped-diagnosis':(0,2),'baseline-diagnosis-final':(0,2),'grouped-diagnosis-final':(0,2),'grouped-cache':(101,29),'grouped-cache-final':(101,30),'grouped-cache-qualified':(0,31),'baseline-frozen':(0,1),'grouped-frozen':(0,1),'grouped-execution':(0,21),'grouped-lifecycle':(0,49)}
ps=subprocess.run(['/bin/ps','-axo','pid=,pgid=,command='],capture_output=True,text=True,check=True)
observed_groups={}
for path,r in receipts.items():
    label=Path(path).name;code,count=expected[label]
    assert r['exitCode']==code and int(r['testResults'][0][1])==count
    assert not r['timedOut'] and r['signals']==[] and r['sourceUnchanged']
    assert r['streamEOF']=={'stdout':True,'stderr':True}
    group=r['processGroup']
    observed_groups[str(group)]=[l.strip() for l in ps.stdout.splitlines() if len(l.split())>=2 and l.split()[1]==str(group)]
    assert not observed_groups[str(group)]
    assert sha(H/path/'stdout')==r['stdoutSHA256'] and sha(H/path/'stderr')==r['stderrSHA256']
# Preserve exact executed source snapshots without retaining build products.
archive=H/'prototype-sources.tar.gz'
with tarfile.open(archive,'w:gz') as tf:
    for kind in ('baseline','grouped'):
        names=json.loads((H/(kind+'-final-diagnosis-source-manifest.json')).read_text())
        for n,v in names.items():
            p=S/kind/n;assert sha(p)==v
            data=p.read_bytes();info=tarfile.TarInfo(kind+'/'+n);info.size=len(data);info.mode=0o644;info.mtime=0
            tf.addfile(info,io.BytesIO(data))
with tarfile.open(archive,'r:gz') as tf:
    for member in tf.getmembers():
        kind,n=member.name.split('/',1)
        names=json.loads((H/(kind+'-final-diagnosis-source-manifest.json')).read_text())
        assert hashlib.sha256(tf.extractfile(member).read()).hexdigest()==names[n]
stat=S.stat();logical=sum(p.stat().st_size for p in S.rglob('*') if p.is_file())
holders=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(S)],capture_output=True,text=True)
(H/'holders.stdout').write_text(holders.stdout);(H/'holders.stderr').write_text(holders.stderr)
assert holders.returncode==1 and not holders.stdout and not holders.stderr
assert S.stat().st_ino==stat.st_ino and S.stat().st_dev==stat.st_dev
shutil.rmtree(S)
write('cleanup.json',{'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedProcessGroups':observed_groups,'allOwnedGroupsAbsent':True,'signalsSent':[],'holderArgv':['/usr/sbin/lsof','-nP','+D',str(S)],'holderExitCode':holders.returncode,'holderStdoutSHA256':sha(H/'holders.stdout'),'holderStderrSHA256':sha(H/'holders.stderr'),'pathAndInodeRechecked':True,'removedOnlyOwnedScratch':str(S),'removedScratchLogicalBytes':logical,'scratchAbsent':not S.exists(),'prototypeSourcesArchiveSHA256':sha(archive),'prototypeSourceMembersVerified':264,'otherProjectsOrDevicesTouched':False})
write('receipt.json',{'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Diagnosis and finite copied actual-cache/original-owner prototypes only','inputClosureSHA256':sha(H/'input-source-manifest.json'),'inputCommitContext':'be472ce6424a691de5673e3438d2768264827d23','resultPackets':input_packets,'commands':{p:sha(H/p/'receipt.json') for p in receipts},'preservedFailures':['commands/grouped-cache','commands/grouped-cache-final'],'allCommandsExitExpectedAndNoTimeoutOrSignals':True,'frozenTraceComparisonSHA256':sha(H/'frozen-comparison.json'),'cleanupSHA256':sha(H/'cleanup.json'),'cleanHandoffSHA256':sha(H/'clean-handoff.json'),'cleanHandoffExecutedOrSelected':False,'prototypeOverlayDistinctFromCleanImplementation':True,'recommendation':'Group exact192Vec payload under existing header; preserve allocator/init/mutations/limits; three buffer-ticket slots','headroomEvidence':'Actual finite composed owner22→21 constructed,86→85 resident64; extra real transient0→1,attempt87 refuses against86; zero consuming cleanup and first failure retained','inlineArray':'Layout-only minimum; no initialization/runtime candidate or complete inventory qualification','fullTargetOrNativeOrPhonesOrSigningOrPublication':False,'gitOrLiveEngineEdits':False,'liveSourceMembersStillUnchanged':132,'newDependencies':False})
external={'docs/swift-index-ticket-storage-diagnosis.md':sha(R/'docs/swift-index-ticket-storage-diagnosis.md')}
members={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='seal.json'}
write('seal.json',{'files':members,'filesSHA256':hashlib.sha256(enc(members)).hexdigest(),'externalFiles':external,'scope':'Frozen finite diagnosis packet; not implementation selection or full-target authorization'})
print(json.dumps({'receiptSHA256':sha(H/'receipt.json'),'sealSHA256':sha(H/'seal.json'),'sealedMembers':len(members),'frozenBytes':len(trace['grouped']),'scratchRemovedLogicalBytes':logical},indent=2))
