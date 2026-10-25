#!/usr/bin/env python3
"""Read-only independent preparation review: no restore, build or child guest."""
from pathlib import Path
import ast,datetime,gzip,hashlib,importlib.util,json,sys
from unittest.mock import patch
H=Path(__file__).resolve().parent;ROOT=H.parent.parent
P=ROOT/'verification/swift-retention-target-preparation'
F=ROOT/'verification/swift-cache-retention-review'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
assert sha(P/'prepared-seal.json')=='1411f9d65c9e74193707378e044436a2152f451b41b6ac86429cf1a362ca4bea'
assert sha(F/'seal.json')=='0d9c15a69baff78ff097f50c0fa8edaa402a6147811742407bdb76fd04c1868f'
sys.path.insert(0,str(P))
import packetlib as p
sealed=p.verify_prepared_seal();p.verify_candidate()
assert not(P/'owned-scratch').exists() and not(P/'bin/exact-tests').exists()
assert not(P/'root-selection.json').exists() and not(P/'target-attempt-started.json').exists()
original=ROOT/'verification/swift-exact-reactor-after-plan-reuse'
assert sha(P/'harness.rs')==sha(original/'harness.rs')==p.HARNESS_HASH
assert sha(P/'historical-code/diagnostic.py')==sha(original/'diagnostic.py')
assert sha(P/'historical-code/test_driver.py')==sha(P/'test_driver.py')==sha(original/'test_driver.py')
old=(original/'diagnostic.py').read_text();new=(P/'diagnostic.py').read_text()
def functions(source):
    lines=source.splitlines(True)
    return {n.name:''.join(lines[n.lineno-1:n.end_lineno])for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
before,after=functions(old),functions(new)
literal=json.loads((P/'source-audit.json').read_text())['literalUnchangedFunctions']
assert len(literal)==15 and all(before[n]==after[n]for n in literal)
assert 'prepare'not in after
# Byte identity above binds the actual original parser, event order and phase
# sequence. The added guard must leave the final dispatch/parse core unchanged.
old_tail=before['execute'][before['execute'].index('    control_count ='):]
new_tail=after['execute'][after['execute'].index('    control_count ='):]
old_tail=old_tail.replace('"exact real Swift reactor after accepted private decode plan reuse"','"exact real Swift reactor with isolated retention candidate; no live integration or attribution"')
assert old_tail==new_tail
source=p.read(P/'candidate-manifest.json');built=p.read(P/'copied-build-manifest.json')
payloads=p.archive_payloads(P/'prepared-source.tar.gz',built)
candidate=p.candidate_payloads()
append='\n// Isolated diagnostic only; isolated candidate production bytes are unchanged.\ninclude!('+json.dumps(str(P/'harness.rs'))+');\n'
candidate['src/experimental_swift_reactor/lifecycle_tests.rs']+=append.encode()
assert candidate==payloads and p.closure(built)=='090ce41c7cebca128502f3c04f366674c826cdfa85a3560b615ebbea6903771e'
assert [n for n in source if source[n]!=built[n]]==['src/experimental_swift_reactor/lifecycle_tests.rs']
assert source['src/experimental_swift_reactor/control.rs']==p.read(P/'live-baseline-manifest.json')['src/experimental_swift_reactor/control.rs']
assert source['src/experimental_wasi/mod.rs']==p.read(P/'live-baseline-manifest.json')['src/experimental_wasi/mod.rs']
binary=p.read(P/'binary.json')['retained']
with gzip.open(P/'bin/exact-tests.gz','rb')as stream:data=stream.read(binary['bytes']+1)
assert len(data)==binary['bytes']==4986496 and hashlib.sha256(data).hexdigest()==binary['sha256']=='76927bc5239984cf39520cbcaa0fb7871cce199e7278124b8998facd5b04de70'
for name in ['build-001','list-001','control-001','control-002','driver-observation-controls']:
    receipt=p.read(P/'commands'/name/'receipt.json')
    assert receipt['passed']and receipt['exitCode']==0 and not receipt['timedOut']
    assert receipt['sourceClosure']==p.closure(built) and receipt['processGroupEmpty']and receipt['rawStreamEOFConfirmed']
    assert not receipt['signalSent']and all(receipt[k]for k in ['sourceUnchanged','toolsUnchanged','allBoundInputsUnchanged','harnessUnchanged','driverUnchanged','argvFilesUnchanged'])
for name in ['list-001','control-001','control-002']:
    argv=p.read(P/'commands'/name/'receipt.json')['argvFileIdentities']
    assert any(i['sha256']==binary['sha256']and i['bytes']==binary['bytes']for i in argv)
proposal=p.read(P/'proposed-command.json');scope=p.read(P/'proposal-scope.json')
assert proposal['outerDeadlineSeconds']==scope['outerDeadlineSeconds']==170
assert proposal['terminationGraceSeconds']==proposal['killWaitSeconds']==5
assert scope['liveTicketsCap']==86 and scope['sameBudget']['run_budget']['cache_work']==64000000
assert proposal['validationDeadlineMs']==120000 and proposal['cumulativeRuntimeDeadlineMs']==proposal['cumulativeWasiDeadlineMs']==30000
assert proposal['argv']==[str(P/'bin/exact-tests'),'experimental_swift_reactor::execution::frame_operations::memory_growth_operations::lifecycle::tests::exact_diagnostic::exact_reactor_target_once','--exact','--nocapture','--test-threads=1']
# Check the actual finalized finite review against the guard, rather than a
# mocked planned acceptance. No root selection is created here.
selection=p.read(P/'root-selection-template.json')
selection.update(reviewSealSHA256=sha(F/'seal.json'),reviewSummarySHA256=sha(F/'result-summary.json'))
assert p.accepted_review(selection)['finitePrerequisiteAccepted'] is True
rejections=0
for field in ['reviewSealSHA256','reviewSummarySHA256','reviewSealPath','reviewSummaryPath']:
    bad=dict(selection);bad[field]='wrong'
    try:p.accepted_review(bad)
    except (AssertionError,KeyError,FileNotFoundError):rejections+=1
    else:raise AssertionError(field)
actual=p.read(F/'result-summary.json');read_original=p.read
for field,value in [('finitePrerequisiteAccepted',False),('blockingFindings',['issue']),('candidateSealSHA256','other'),('candidateManifestSHA256',p.LIVE_BASELINE_CLOSURE),('baselineClosureSHA256',p.CANDIDATE_CLOSURE),('fullDiagnosticSelected',True),('liveIntegrationAccepted',True),('gaAccepted',True)]:
    bad=dict(actual);bad[field]=value
    def substituted(path):return bad if Path(path)==F/'result-summary.json'else read_original(path)
    with patch.object(p,'read',side_effect=substituted):
        try:p.accepted_review(selection)
        except AssertionError:rejections+=1
        else:raise AssertionError(field)
assert rejections==12
assert 'with (HERE / "target-attempt-started.json").open("x")' in after['execute']
assert after['execute'].index('.open("x")')<after['execute'].index('record_command(name, argv, 170 if target else 60')
assert 'assert not (HERE / "target-attempt-started.json").exists()'in after['execute']
restore=(P/'restore.py').read_text()
assert 'archive_payloads' in restore and 'write_source(source, scratch / \'vm\')'in restore and 'binary.open(\'xb\')'in restore
assert restore.index('source = archive_payloads')<restore.index('scratch.mkdir(')
assert 'not (H / \'root-selection.json\').exists()'in restore and 'not (H / \'target-attempt-started.json\').exists()'in restore
for name in ['/a','../a','a/../b','./a','a//b','']:
    try:p.safe_name(name)
    except AssertionError:pass
    else:raise AssertionError(name)
assert all(not(P/n).exists()for n in ['owned-scratch','bin/exact-tests','root-selection.json','target-attempt-started.json'])
assert sha(F/'seal.json')=='0d9c15a69baff78ff097f50c0fa8edaa402a6147811742407bdb76fd04c1868f'
write(H/'source-and-command-audit.json',{'schema':1,'auditedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'preparationSealSHA256':sha(P/'prepared-seal.json'),'preparationFiles':len(sealed['files']),'preparationExternalFiles':len(sealed['externalFiles']),'finiteReviewSealSHA256':sha(F/'seal.json'),'originalHarnessSHA256':p.HARNESS_HASH,'harnessByteIdentical':True,'originalDriverSHA256':sha(original/'diagnostic.py'),'preparedDriverSHA256':sha(P/'diagnostic.py'),'literalUnchangedFunctions':literal,'executionAndParserTailUnchangedExceptScopeLabel':True,'candidateManifestSHA256':p.CANDIDATE_CLOSURE,'liveBaselineClosureSHA256':p.LIVE_BASELINE_CLOSURE,'copiedBuildManifestSHA256':p.closure(built),'sourceFiles':len(built),'preparedSourceBytes':sum(len(b)for b in payloads.values()),'retainedBinary':binary,'realFinalizedReviewGuardAccepted':True,'invalidReviewBindingsRejected':rejections,'oneAttemptExclusiveMarkerBeforeChildDispatch':True,'closedArchiveNamesChecked':True,'sourceAndExecutableReadInMemoryOnly':True,'sourceRestored':False,'compilerRun':False,'targetRun':False,'productEdits':False,'rootSelectionCreated':False,'nativeOrNetworkRun':False,'producerScratchAndBinaryAbsent':True,'priorFiniteSealPreserved':True,'scope':'Read-only isolated preparation prerequisite review; root must separately select any actual same-budget target.'})
print(json.dumps({'audited':True,'originalFunctionsPreserved':len(literal),'sourceFiles':len(built),'invalidReviewBindingsRejected':rejections,'sourceRestored':False,'compilerOrGuestRun':False,'priorFiniteSealPreserved':True}))
