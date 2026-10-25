#!/usr/bin/env python3
"""Archive context, seal finite recorded evidence and verify without guest execution."""
from pathlib import Path
import datetime,hashlib,json,shutil,subprocess,sys
H=Path(__file__).resolve().parent;R=H.parent.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
def save(n,v):(H/n).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
binding=load(H/'input-bindings.json');archived={}
for n,d in binding.items():
    now=sha(R/n)
    if now!=d:assert n in ('PLAN.md','STATUS.md'),n
    p=H/'inputs'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/n,p)
    archived[n]={'observedBeforeFiniteSHA256':d,'archivedAtSealSHA256':sha(p),'concurrentRootContextUpdate':now!=d}
save('archived-inputs.json',archived)
baseline=load(H/'baseline-manifest.json');modified=load(H/'copied-source-manifest.json')
for n,d in baseline.items():
    assert sha(R/'vm'/n)==d,n
    if d!=modified[n]:
        p=H/'originals'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/'vm'/n,p)
tools=load(H/'tools.json');q=subprocess.run(['/usr/sbin/lsof','-v'],capture_output=True,text=True,timeout=10)
tools['lsof']={'path':'/usr/sbin/lsof','sha256':sha('/usr/sbin/lsof'),'argv':q.args,'exitCode':q.returncode,'stdout':q.stdout,'stderr':q.stderr}
tools['ps']={'path':'/bin/ps','sha256':sha('/bin/ps'),'versionSource':tools['platform'],'argv':['/bin/ps','-axo','pid=,pgid=,comm=']}
save('tools.json',tools)
c=load(H/'command.json');cleanup=load(H/'cleanup.json')
save('receipt.json',{
 'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'bounded offline diagnosis after decode-plan integration; one copied finite actual-cache observer test; module inspected only as data',
 'sourceRevisionContext':'6403eea98031207f6e40a72b55dfd3bd4e7e6ec2','sourceRevisionMeaning':'root-supplied exact committed integration context; content closure authoritative; no Git query',
 'sourceClosure':'16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd','sourceFiles':132,
 'fullResultSealSHA256':'8f04098c444d63e9d638c32e22297eccdad346222241529ef710c524473e7526',
 'finiteTestsPassed':1,'finiteTestsFailed':0,'finiteTestsIgnored':0,'filteredOut':386,'finiteObservationRows':13,'coldWorkPrefixControls':164,'cancellationControls':3,
 'inheritedCompilerWarnings':2,'finiteCommand':'command.json','finiteSourceDiff':'instrumentation.patch','exactIsolatedSourceArchive':'isolated-source.tar.gz','tools':'tools.json',
 'finiteElapsedSeconds':c['elapsedSeconds'],'hostTimeoutSeconds':120,'timedOut':False,
 'guestInstructions':0,'guestInitializeCalls':0,'guestInvokeCalls':0,'fullTargetAttempts':0,
 'moduleDataInspection':'module-data-inspection.json','analysisCommand':[sys.executable,'-B',str(H/'analyze.py')],'arithmetic':'arithmetic.json',
 'planningCreditsExact':11828480,'lastFailureInsideBuildDecoder':True,
 'currentTargetPlanHitsOrConflictsMeasured':False,'currentTargetRepeatedDecodeCountMeasured':False,'cpuSpeedupMeasured':False,
 'nextRecommended':'complete minimal fixed-memory observer and its finite controls, then separately root-select any diagnostic full attempt',
 'observerProposal':'observer-proposal.json','productionSourceChanged':False,'productionAlgorithmImplemented':False,'budgetsIncreased':False,
 'negativeFixtureBudgetExplanation':'164 cold failure-prefix controls use smaller synthetic cache_work budgets; ordinary fixtures use default production budgets',
 'liveSourceBeforeAfterUnchanged':True,'contextOnlyConcurrentRootUpdates':[n for n,row in archived.items() if row['concurrentRootContextUpdate']],
 'cleanup':'cleanup.json','logicalBytesRemoved':cleanup['removedLogicalBytes'],'ownedGroupAbsent':True,'holdersEmpty':True,'ownedDirectoryDeviceInodeChecked':True,
 'ownedPathsAbsent':True,'otherProjectsTouched':False,'networkUsed':False,'gitUsed':False,'nativeDeviceOrUIUsed':False,'signingUsed':False,'frozenHostedLanesReadImportedOrExecuted':False,
 'initialReadErrors':['nonexistent guessed experimental/swift cache/decode paths','nonexistent guessed experimental_swift_reactor/decode.rs','nonexistent guessed verification/swift-decode-plan-reuse directory'],
 'verificationCommand':[sys.executable,'-B',str(H/'verify.py')],'sealedPacketAndReportReadOnly':True,'gaAccepted':False,
 'limitations':['target attribution is bounded from counters/source, not new measured semantic stages','a blocked build is not proof of the dominant prior cost','finite observer lacks target bitmap/repeat partitions proposed next','no complete new regression or production accounting acceptance','Corpus 2/native/public/signed/published FieldLog/final phones/GA remain pending']})
report='docs/swift-plan-cache-remaining-work-diagnosis.md'
def seal():
    save('seal.json',{'schema':1,'status':'sealed-offline-finite-diagnosis-no-target-retry',
      'files':{str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='seal.json'},
      'externalFiles':{report:sha(R/report),'verification/swift-exact-reactor-after-plan-reuse/result-seal.json':sha(R/'verification/swift-exact-reactor-after-plan-reuse/result-seal.json')}})
seal()
q=subprocess.run([sys.executable,'-B',str(H/'verify.py')],capture_output=True,text=True,cwd=R,timeout=30)
(H/'verify.stdout').write_text(q.stdout);(H/'verify.stderr').write_text(q.stderr)
save('verification.json',{'argv':q.args,'cwd':str(R),'exitCode':q.returncode,'stdoutSHA256':sha(H/'verify.stdout'),'stderrSHA256':sha(H/'verify.stderr'),'readOnly':True,'compilerOrGuestExecution':False})
assert q.returncode==0,q.stderr
seal()
print(q.stdout.strip())
print(json.dumps({'sealSHA256':sha(H/'seal.json'),'sealedMembers':len(load(H/'seal.json')['files']),'reportSHA256':sha(R/report)}))
for p in H.rglob('*'):
    if p.is_file():p.chmod(0o444)
for p in sorted([p for p in H.rglob('*') if p.is_dir()],key=lambda p:len(p.parts),reverse=True):p.chmod(0o555)
H.chmod(0o555);(R/report).chmod(0o444)
