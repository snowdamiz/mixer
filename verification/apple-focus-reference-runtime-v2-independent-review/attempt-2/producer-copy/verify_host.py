#!/usr/bin/env python3
"""Run host controls with retained immutable attempts; no compiler/native/service tools."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
import datetime
import platform
import sys
import time
import unittest
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
    after=prepare.inputs()[3]
    scratch=[str(path) for path in prepare.BASE.iterdir() if path.is_dir() and path.name.startswith(('pure-oracle-','archive-control-','host-packet-','composition-control-','adapter-control-','orchestration-control-'))]
    owned={name:prepare.row(prepare.BASE/name) for name in prepare.OWNED}
    receipt={'schema':'mixer.apple-focus-reference-runtime-host-receipt.2','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(prepare.BASE/'verify_host.py'),'--attempt',str(attempt)],'cwd':str(prepare.ROOT),'python':sys.version,'pythonExecutable':str(prepare.Path(sys.executable).resolve()),'platform':platform.platform(),'elapsedSeconds':time.monotonic()-started,'sourceRevisionLabel':'ba9ad4372f94463ba4d363cdfd76dd565c96413f','sourceRevisionMeaning':'Inherited frozen label; exact source hashes define scope; no Git query','ownedSources':owned,'ownedSourceTreeSHA256':prepare.sha(prepare.stable(owned)),'inputBindings':after,'inputTreeSHA256':prepare.sha(prepare.stable(after)),'sourceTreeSHA256':prepare.SOURCE,'productArchiveSHA256':prepare.PRODUCT,'testsExpected':expected,'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful() and result.testsRun==expected and before==after and not scratch,'outputs':{name:prepare.row(base/name) for name in ['stdout.log','stderr.log']},'cleanup':{'ownedHostTemporaryDirectoriesAbsent':not scratch,'remainingOwnedScratch':scratch,'allFrozenInputsUnchanged':before==after,'nativeInstancesCreatedOrQueried':0,'servicesStarted':0,'otherProjectsTouched':False},'scope':'Synthetic-only host controls of selected-run importer and source composition; no native acceptance','syntheticOnly':True,'nativeExecuted':False,'runtimeSelected':False,'compileRerun':False,'gitMutationPerformed':False,'uiOrCapturePerformed':False,'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred'}
    (base/'receipt.json').write_bytes(prepare.stable(receipt))
    print(f"{'PASS' if receipt['passed'] else 'FAIL'}: {result.testsRun} host controls; {len(result.failures)} failures; {len(result.errors)} errors; no native execution")
    if not receipt['passed']:raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--attempt',type=int,default=1);main(p.parse_args().attempt)
