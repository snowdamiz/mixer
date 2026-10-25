#!/usr/bin/env python3
"""Read-only sealed independent review audit, including retained blocking failures."""
from pathlib import Path
import copy,hashlib,importlib.util,json,subprocess,sys,tarfile
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parent.parent
P=H.parent/'swift-current-attribution-full-preparation';C=H.parent/'swift-cache-current-attribution-observer'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
seal=load(H/'seal.json')
files={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='seal.json'}
assert files==set(seal['files'])
for n,d in seal['files'].items():assert sha(H/n)==d,n
for n,d in seal['externalFiles'].items():assert sha(R/n)==d,n
assert sha(P/'prepared-seal.json')=='c40ab937f218baa54b45e5a5846e4dd12d05edcfb2c3786a75d27f026f70a7f1'
candidate=load(P/'prepared-seal.json');assert len(candidate['files'])==104
assert {str(p.relative_to(P)) for p in P.rglob('*') if p.is_file() and p.name!='prepared-seal.json'}==set(candidate['files'])
for n,d in candidate['files'].items():assert sha(P/n)==d,n
for n,d in candidate['externalFiles'].items():assert sha(R/n)==d,n
audit=load(H/'source-audit.json')
for n,d in audit['inputSnapshots'].items():assert sha(H/'input-snapshots'/n)==d,n
assert audit['preparedSealSHA256']==sha(P/'prepared-seal.json') and audit['sourceFiles']==132
assert not audit['liveVmRead'] and not audit['gitQueried']
with tarfile.open(C/'isolated-source.tar.gz','r:gz') as t:
    members=t.getmembers();assert len(members)==132 and len({m.name for m in members})==132
    assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
    source={m.name:t.extractfile(m).read() for m in members}
accepted=load(C/'copied-source-manifest.json')
assert {n:hashlib.sha256(b).hexdigest() for n,b in source.items()}==accepted
test='src/experimental_swift_reactor/cache_tests.rs';life='src/experimental_swift_reactor/lifecycle_tests.rs'
source[test]+=b'\n'+(P/'adapter.rs').read_bytes()+b'\n'+(P/'adapter-controls.rs').read_bytes()
source[life]+=('\n// Isolated diagnostic only; baseline production bytes are unchanged.\ninclude!('+json.dumps(str(P/'harness.rs'))+');\n').encode()
prepared=load(P/'copied-build-manifest.json')
assert {n:hashlib.sha256(b).hexdigest() for n,b in source.items()}==prepared
assert [n for n in accepted if accepted[n]!=prepared[n]]==[test,life]
source[test]+=b'\n'+(H/'independent-controls.rs').read_bytes()
review=load(H/'review-source-manifest.json')
assert {n:hashlib.sha256(b).hexdigest() for n,b in source.items()}==review
assert [n for n in prepared if prepared[n]!=review[n]]==[test]
assert audit['reviewManifestSHA256']==sha(H/'review-source-manifest.json')=='8f46d1fe3924e7763b5c128ffd6e36d82a9ebdd4e9abb1633e642cbe276e19d3'
commands={}
for path in sorted((H/'commands').glob('*/receipt.json')):
    command=load(path);name=path.parent.name;commands[name]=command
    assert command['stdoutSHA256']==sha(path.parent/'stdout') and command['stderrSHA256']==sha(path.parent/'stderr')
    assert command['preparedSealSHA256']==sha(P/'prepared-seal.json') and command['preparedSealUnchanged'] and command['sourceUnchanged']
    assert not command['timedOut'] and not command['signalsSent'] and command['processGroupEmpty'] and command['rawStreamEOFConfirmed']
    assert not command['fullTargetSelected'] and command['fullTargetAttempts']==command['realTargetValidations']==command['realTargetInitializeCalls']==command['realTargetCorpusCalls']==0
    if 'runnerSHA256' in command:assert command['runnerSHA256']==sha(path.parent/'runner.py')
    for info in command.get('argvFiles',[]):
        if info['path'].endswith('.py'):assert info['sha256']==sha(path.parent/'executed-file.py')
assert set(commands)=={'prepare','verify-prepared','finite-cache','host-controls','host-controls-corrected','parser-contract'}
assert all(commands[n]['passed'] and commands[n]['exitCode']==0 for n in ('prepare','verify-prepared','finite-cache','host-controls-corrected'))
assert not commands['host-controls']['passed'] and commands['host-controls']['exitCode']==1
assert not commands['parser-contract']['passed'] and commands['parser-contract']['exitCode']==1
assert 'FAILED (failures=1)' in (H/'commands/host-controls/stderr').read_text()
assert 'Ran 6 tests' in (H/'commands/host-controls-corrected/stderr').read_text() and (H/'commands/host-controls-corrected/stderr').read_text().endswith('OK\n')
assert 'independent_binding_drift_rejections=15' in (H/'commands/host-controls-corrected/stdout').read_text()
cache=commands['finite-cache'];assert cache['sourceManifestSHA256']==sha(H/'review-source-manifest.json')
assert cache['argv'][1:]==['test','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor','--release','experimental_swift_reactor::cache_tests::independent_full_attribution_','--','--nocapture','--test-threads=1']
assert cache['environment']['CARGO_NET_OFFLINE']=='true' and cache['environment']['CARGO_BUILD_JOBS']=='2'
stdout=(H/'commands/finite-cache/stdout').read_text()
assert '2 passed; 0 failed; 0 ignored; 0 measured; 395 filtered out' in stdout
assert stdout.count('REVIEW_FULL_CANCEL ')==4 and stdout.count('REVIEW_FULL_LIFETIME ')==2
assert all('guest_instructions=0 cleanup_zero=true' in line for line in stdout.splitlines() if 'REVIEW_FULL_' in line)
original=load(H/'parser-original-events.json');assert original==load(P/'control-001-events.json')
spec=importlib.util.spec_from_file_location('sealed_review_telemetry',H/'input-snapshots/telemetry.py')
telemetry=importlib.util.module_from_spec(spec);spec.loader.exec_module(telemetry)
recorded=load(H/'parser-classifications.json')
assert recorded['testsRun']==recorded['failed']==6 and recorded['errors']==0
assert len(recorded['cases'])==6
for case in recorded['cases']:
    before=copy.deepcopy(original);result=telemetry.classify(H/case['path'],original)
    assert result==case['classification'] and original==before
    assert result['status']=='valid' and not result['issues'] and not result['originalResultReplaced'] and not result['cleanupTruthInferredFromTelemetry']
assert 'FAILED (failures=6)' in (H/'commands/parser-contract/stderr').read_text()
contract=load(H/'contract-review.json')
assert contract['harnessReverseDeltaRecoversOriginalBytes'] and contract['exactSingleOccurrenceReversals']==7 and contract['targetTestByteIdentical']
assert contract['reservationTicketLimit']==86 and contract['nativeSuffixBytes']==65536
assert contract['outerDeadlineSeconds']==170 and contract['terminationGraceSeconds']==contract['killWaitSeconds']==5
assert contract['telemetryEnvelopeBytes']==4608 and contract['telemetryLifetimeBytes']==27648
cleanup=load(H/'cleanup.json');pre=load(H/'cleanup-preflight.json')
assert cleanup['ownedPathsAbsent'] and cleanup['allOwnedProcessGroupsAbsent'] and cleanup['holderChecksEmpty'] and cleanup['deviceInodeChecksPassed']
assert not cleanup['signalsSent'] and cleanup['logicalBytesRemoved']==pre['logicalBytesToRemove']==24334739
assert all(v['exitCode']==1 and v['empty'] for v in pre['holders'].values())
assert all(not (H/n).exists() for n in ('owned-source','owned-target','owned-tmp','unmaterialized-guard-fixture'))
assert all(not (P/n).exists() for n in ('owned-scratch','bin/exact-tests','root-selection.json','target-attempt-started.json','commands/target-once'))
pgids={c['processGroup'] for c in commands.values()}
ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True,timeout=10)
assert not [row for row in ps.splitlines() if len(row.split())>=2 and int(row.split()[1]) in pgids]
receipt=load(H/'receipt.json');findings=load(H/'findings.json')
assert receipt['verdict']==findings['verdict']=='changes-required-classifier-validation'
assert len(findings['blockingFindings'])==receipt['blockingFindings']==1
assert receipt['independentRustTestsPassed']==2 and receipt['independentHostMethodsPassed']==6 and receipt['independentParserNegativeTestsFailed']==6
assert receipt['fullTargetSelectionWithheld'] and not receipt['preparationAccepted'] and not receipt['gaAccepted']
assert receipt['fullTargetAttempts']==receipt['tinySyntheticGuestInstructions']==receipt['realTargetValidations']==0
assert not receipt['producerEdited'] and not receipt['productionSourceChanged'] and not receipt['rootSelectionCreated'] and not receipt['attemptMarkerCreated']
print(json.dumps({'reviewIntegrityVerified':True,'sealedMembers':len(files),'sourceFiles':132,'independentRustTestsPassed':2,'independentHostMethodsPassed':6,'schemaNegativeFailuresPreserved':6,'reviewerAuthoringFailurePreserved':1,'blockingFindings':1,'fullTargetAttempts':0,'guestInstructions':0,'cleanupComplete':True,'verdict':receipt['verdict'],'fullTargetSelectionWithheld':True,'gaAccepted':False},sort_keys=True))
