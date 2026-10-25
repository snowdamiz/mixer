#!/usr/bin/env python3
"""Run host controls with retained immutable attempts; no compiler/native/service tools."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
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
        if not permitted:raise AssertionError('V3 host boundary rejected subprocess: '+repr(argv))
        HOST_SPAWNS.append({'argv':argv,'scope':'Inspected native-disabled Python composition probe'})
    if event in ('os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex'):
        raise AssertionError('V3 host boundary rejected '+event)
sys.addaudithook(host_boundary)
import prepare


def main(attempt):
    require=prepare.require
    require(type(attempt) is int and attempt>0,'Positive host attempt required')
    base=prepare.BASE/f'host-attempt-{attempt}';require(not base.exists(),'Preserve previous host attempt');base.mkdir()
    started=time.monotonic();before=prepare.inputs()[3]
    with (base/'stdout.log').open('w') as out,(base/'stderr.log').open('w') as err,redirect_stdout(out),redirect_stderr(err):
        import test_importer
        suite=unittest.defaultTestLoader.loadTestsFromModule(test_importer)
        expected=suite.countTestCases()
        result=unittest.TextTestRunner(stream=err,verbosity=2).run(suite)
    import replay_review
    replay=replay_review.run(base)
    with (base/'repair.stdout.log').open('w') as out,(base/'repair.stderr.log').open('w') as err,redirect_stdout(out),redirect_stderr(err):
        import test_repair
        repair_result=unittest.TextTestRunner(stream=err,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_repair))
    (base/'actual-composition-outcomes.json').write_bytes(prepare.stable({'syntheticOnly':True,'nativeExecuted':False,'probeProgramSHA256':prepare.sha(test_repair.PRODUCTION_PROGRAM.encode()),'records':test_repair.FocusRepairControls.records}))
    after=prepare.inputs()[3]
    scratch=[str(path) for path in prepare.BASE.iterdir() if path.is_dir() and path.name.startswith(('pure-oracle-','archive-control-','host-packet-','composition-control-','adapter-control-','orchestration-control-','actual-composition-'))]
    owned={name:prepare.row(prepare.BASE/name) for name in prepare.OWNED}
    receipt={'schema':'mixer.apple-focus-reference-runtime-host-receipt.3','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(prepare.BASE/'verify_host.py'),'--attempt',str(attempt)],'cwd':str(prepare.ROOT),'python':sys.version,'pythonExecutable':str(prepare.Path(sys.executable).resolve()),'hostUname':dict(zip(('sysname','nodename','release','version','machine'),os.uname())),'elapsedSeconds':time.monotonic()-started,'sourceRevisionLabel':'ba9ad4372f94463ba4d363cdfd76dd565c96413f','sourceRevisionMeaning':'Inherited frozen label; exact source hashes define scope; no Git query','ownedSources':owned,'ownedSourceTreeSHA256':prepare.sha(prepare.stable(owned)),'inputBindings':after,'inputTreeSHA256':prepare.sha(prepare.stable(after)),'sourceTreeSHA256':prepare.SOURCE,'productArchiveSHA256':prepare.PRODUCT,'testsExpected':expected,'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful() and result.testsRun==111 and result.testsRun==expected and replay['expectedReplayOutcome'] and repair_result.wasSuccessful() and before==after and not scratch,'historicalReview':{'controls':replay['testsRun'],'passed':replay['controlsPassed'],'retainedHistoricalFixtureFailures':len(replay['failures']),'sourceSHA256':replay['originalReviewerSourceSHA256']},'repairControls':{'testsRun':repair_result.testsRun,'failures':len(repair_result.failures),'errors':len(repair_result.errors),'skipped':len(repair_result.skipped),'passed':repair_result.wasSuccessful()},'hostPythonSubprocesses':HOST_SPAWNS,'outputs':{path.name:prepare.row(path) for path in base.iterdir() if path.is_file()},'cleanup':{'ownedHostTemporaryDirectoriesAbsent':not scratch,'remainingOwnedScratch':scratch,'allFrozenInputsUnchanged':before==after,'nativeInstancesCreatedOrQueried':0,'servicesStarted':0,'otherProjectsTouched':False},'scope':'Synthetic-only host controls of selected-run importer and source composition; no native acceptance','syntheticOnly':True,'nativeExecuted':False,'runtimeSelected':False,'compileRerun':False,'gitMutationPerformed':False,'uiOrCapturePerformed':False,'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred'}
    (base/'receipt.json').write_bytes(prepare.stable(receipt))
    print(f"{'PASS' if receipt['passed'] else 'FAIL'}: {result.testsRun}/111 retained producer; {replay['controlsPassed']}/33 exact historical reviewer controls with {len(replay['failures'])} retained invalid-fixture failure; {repair_result.testsRun} focused controls; no native execution")
    if not receipt['passed']:raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--attempt',type=int,default=1);main(p.parse_args().attempt)
