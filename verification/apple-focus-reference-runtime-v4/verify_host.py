#!/usr/bin/env python3
"""Host-only exact V4 controls; every attempt is retained and no native tool runs."""
import argparse
from contextlib import redirect_stderr,redirect_stdout
import datetime
import os
from pathlib import Path
import sys
import time
import unittest

BASE=Path(__file__).resolve().parent
HOST_SPAWNS=[]

def host_boundary(event,args):
    if event=='subprocess.Popen':
        executable,argv=args[:2]
        permitted=(str(Path(executable).resolve())==str(Path(sys.executable).resolve()) and len(argv)==5 and argv[1:3]==['-B','-c'] and all(marker in argv[3] for marker in ['subprocess.Popen=forbidden','socket.socket.bind=forbidden','socket.socket.connect=forbidden']) and Path(argv[4]).resolve().is_relative_to(BASE))
        if not permitted:raise AssertionError('V4 host boundary rejected subprocess: '+repr(argv))
        HOST_SPAWNS.append({'argv':argv,'programSHA256':__import__('hashlib').sha256(argv[3].encode()).hexdigest(),'scope':'Inspected native-disabled Python composition only'})
    if event in ('os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex'):
        raise AssertionError('V4 host boundary rejected '+event)
sys.addaudithook(host_boundary)
import prepare


def main(attempt):
    prepare.require(type(attempt) is int and attempt>0,'Positive attempt required')
    base=BASE/f'host-attempt-{attempt}';prepare.require(not base.exists(),'Preserve prior attempt');base.mkdir()
    started=time.monotonic();before=prepare.inputs()[3]
    outcomes={}
    def suite(label,tests):
        with (base/(label+'.stdout.log')).open('w') as out,(base/(label+'.stderr.log')).open('w') as err,redirect_stdout(out),redirect_stderr(err):
            result=unittest.TextTestRunner(stream=err,verbosity=2).run(tests)
        outcomes[label]={'testsRun':result.testsRun,'failures':[{'name':str(c),'traceback':tb} for c,tb in result.failures],'errors':[{'name':str(c),'traceback':tb} for c,tb in result.errors],'skipped':result.skipped,'passed':result.wasSuccessful()}
        return result
    import test_importer
    producer=suite('producer',unittest.defaultTestLoader.loadTestsFromModule(test_importer))
    import replay_review
    historical=replay_review.run(base)
    import test_repair
    repair=suite('repair',unittest.defaultTestLoader.loadTestsFromModule(test_repair))
    (base/'actual-composition-outcomes.json').write_bytes(prepare.stable({'syntheticOnly':True,'nativeExecuted':False,'probeProgramSHA256':prepare.sha(test_repair.PRODUCTION_PROGRAM.encode()),'records':test_repair.FocusRepairControls.records}))
    import replay_v3_review
    review=replay_v3_review.run(base)
    import test_precision
    precision=suite('precision',unittest.defaultTestLoader.loadTestsFromModule(test_precision))
    (base/'exact-time-adapter-outcomes.json').write_bytes(prepare.stable(test_precision.ExactTimestampControls.records))
    # The replay installs a no-process boundary; run after every composed probe.
    import replay_precision
    adapter=replay_precision.run(base)
    after=prepare.inputs()[3]
    prefixes=('pure-oracle-','archive-control-','host-packet-','composition-control-','adapter-control-','orchestration-control-','actual-composition-','independent-composition-','precision-adapter-','exact-time-adapter-')
    scratch=[str(p) for p in BASE.iterdir() if p.is_dir() and p.name.startswith(prefixes)]
    owned={n:prepare.row(BASE/n) for n in prepare.OWNED}
    passed=(producer.wasSuccessful() and producer.testsRun==111 and historical['expectedReplayOutcome'] and repair.wasSuccessful() and repair.testsRun==25 and review['passed'] and precision.wasSuccessful() and precision.testsRun==19 and adapter['controls']==8 and adapter['controlsPassed']==8 and before==after and not scratch)
    output_rows={str(p.relative_to(base)):prepare.row(p) for p in sorted(base.rglob('*')) if p.is_file()}
    receipt={'schema':'mixer.apple-focus-reference-runtime-host-receipt.4','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(BASE/'verify_host.py'),'--attempt',str(attempt)],'cwd':str(prepare.ROOT),'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),'hostUname':dict(zip(('sysname','nodename','release','version','machine'),os.uname())),'elapsedSeconds':time.monotonic()-started,'sourceRevisionLabel':'ba9ad4372f94463ba4d363cdfd76dd565c96413f','sourceRevisionMeaning':'Inherited compilation label; exact file and tree hashes define this host-only derivative; no Git query','ownedSources':owned,'ownedSourceTreeSHA256':prepare.sha(prepare.stable(owned)),'inputBindings':after,'inputTreeSHA256':prepare.sha(prepare.stable(after)),'sourceTreeSHA256':prepare.SOURCE,'productArchiveSHA256':prepare.PRODUCT,'suiteResults':outcomes,'testsRun':producer.testsRun,'passed':passed,'historicalReview':{'controls':historical['testsRun'],'passed':historical['controlsPassed'],'retainedHistoricalFixtureFailures':len(historical['failures']),'sourceSHA256':historical['originalReviewerSourceSHA256'],'expectedReplayOutcome':historical['expectedReplayOutcome']},'repairControls':{'testsRun':repair.testsRun,'passed':repair.wasSuccessful()},'v3ReviewReplay':{'testsRun':review['testsRun'],'passed':review['controlsPassed'],'unchangedControlBodiesMutationsAssertions':True,'composedInventoryControls':review['composedInventoryControls']},'precisionControls':{'testsRun':precision.testsRun,'passed':precision.wasSuccessful(),'actualAdapterCases':len(test_precision.ExactTimestampControls.records)},'frozenV3ActualAdapterReplay':{'controls':adapter['controls'],'passed':adapter['controlsPassed'],'failed':adapter['controlsFailed']},'hostPythonSubprocesses':HOST_SPAWNS,'outputs':output_rows,'outputTreeSHA256':prepare.sha(prepare.stable(output_rows)),'cleanup':{'ownedHostTemporaryDirectoriesAbsent':not scratch,'remainingOwnedScratch':scratch,'allFrozenInputsUnchanged':before==after,'nativeCommandsInvoked':0,'nativeInstancesCreatedOrQueried':0,'servicesStarted':0,'otherProjectsTouched':False},'scope':'Synthetic-only host controls of exact timestamp ordering and unchanged selected source composition; no native acceptance','syntheticOnly':True,'nativeExecuted':False,'runtimeSelected':False,'compileRerun':False,'gitMutationPerformed':False,'uiOrCapturePerformed':False,'hostedCatalogAuthorityOrWorkerReviewReadImportedOrExecuted':False,'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred'}
    (base/'receipt.json').write_bytes(prepare.stable(receipt))
    print(prepare.stable({'passed':passed,'producer':{'run':producer.testsRun,'passed':producer.wasSuccessful()},'focused':{'run':repair.testsRun,'passed':repair.wasSuccessful()},'historical':receipt['historicalReview'],'v3Reviewer':receipt['v3ReviewReplay'],'precision':receipt['precisionControls'],'actualAdapterReplay':receipt['frozenV3ActualAdapterReplay'],'cleanup':receipt['cleanup'],'receiptSHA256':prepare.sha((base/'receipt.json').read_bytes())}).decode(),end='')
    if not passed:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--attempt',type=int,required=True);main(p.parse_args().attempt)
