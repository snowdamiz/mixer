#!/usr/bin/env python3
"""Finite guarded source/control bootstrap, with raw output kept locally."""
import unittest.mock
import offline
offline.install()
import ast, contextlib, datetime, hashlib, io, json, sys, unittest
from pathlib import Path
import admit as a
import bounded_commands as b
import host_controls as h
import controls as c
import verify as v

HERE = Path(__file__).resolve().parent


def write(name,value):
    (HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')


def main():
    local=HERE/'local';local.mkdir(exist_ok=True)
    outputs=HERE/'outputs';outputs.mkdir(exist_ok=True)
    # Guarded whole-source parsing is syntax/source evidence only.
    for path in HERE.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
    check=v.check(verify_seal=False)
    write('outputs/source-check.json',check)
    results={}
    for name,module in (('host',h),('release',c)):
        stream=io.StringIO();stdout=io.StringIO()
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stream):
            result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(module.Controls))
        raw=stream.getvalue()+stdout.getvalue()
        (local/(name+'-controls-output.txt')).write_text(raw)
        results[name]={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'passed':result.wasSuccessful(),'rawOutput':{'bytes':len(raw.encode()),'sha256':hashlib.sha256(raw.encode()).hexdigest()}}
    total=sum(x['tests'] for x in results.values())
    assert all(x['passed'] and not x['skips'] for x in results.values()), 'Controls failed; local output retained'
    assert not list(HERE.glob('pure-*')) and not list(HERE.rglob('__pycache__'))
    assert offline.ATTEMPTS==[]
    summary={'schema':1,'suites':results,'totalTests':total,'failures':0,'errors':0,'skips':0,'pythonVersion':sys.version,'guardBeforeSubjectImports':True,'realProcessSessionGroupSignalTimerWaitSocketCalls':0,'liveApiAttempts':offline.ATTEMPTS,'runtimeRuns':0,'scope':'Guarded source and synthetic/mock controls only; no runtime or live custody proof'}
    write('outputs/controls-summary.json',summary)
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':'python3 -B verification/swift-pin-bitmap-release-completion-admission/prepare.py','commandExit':0,'pythonVersion':sys.version,'parentSuppliedRevision':'1eec8e0fc270c0409c8920ee22fd2374f3bd249f','parentSuppliedGitTree':'f20be7de5a047f1983931961cc3d774e56de80a3','GitVerified':False,'decision':'Source-only bounded Release completion proposal for independent root review','attemptSelected':False,'workflowInstalled':False,'canonicalPromotionSelected':False,'GAQualified':False,'profile':a.PROFILE,'workflowPath':a.WORKFLOW_PATH,'candidateMembers':136,'overlays':15,'candidateTreeSHA256':a.CANDIDATE,'baselineTreeSHA256':a.BASELINE,'priorActualEvidence':a.prior_evidence(),'controls':summary,'sourceCheck':check,'frozenHelperSHA256':v.row(HERE/'bounded_commands.py')['sha256'],'source':{n:v.row(HERE/n) for n in ('admit.py','workflow.yml','host_controls.py','controls.py','verify.py')},'bounds':{'plannedCommands':['compiler-identity','node-identity','release-regression'],'childSeconds':[30,30,600],'activeSeconds':660,'cleanupSeconds':60,'runStepMinutes':14,'jobMinutes':22,'installerMinutes':2,'installerCustodyWithinHelper':False,'streamBytes':8388608,'aggregateBytes':33554432},'cleanup':{'pureScratchRemaining':[],'ownedRuntimeInstancesStarted':0,'otherProjectsTouched':False,'heldProcessesProbed':False,'onlyOwnedFolderWritten':True},'prohibitedActions':{'compilerProductNodeOracleRuntime':0,'GitGhNetwork':0,'nativeUICapturePhones':0,'heldProbes':0,'memoryEdits':0,'releaseTagSDKRepo':0,'extraAgents':0},'limitations':['Source/mock evidence only; no newly executed Release result','Structural workflow validation only; no YAML parser or actionlint','Existing installer, same-group descendant, pipe/reap, shared-library and evidence-I/O limitations preserved'],'pending':['Independent root source/control review','Workflow installation and one initial manual attempt selection','Actual hosted Release evidence and independent review','Canonical integration, native/physical, published-package FieldLog, operational/store/customer and GA acceptance']}
    write('receipt.json',receipt)
    rows={p.relative_to(HERE).as_posix():v.row(p) for p in HERE.rglob('*') if p.is_file() and p.name not in v.RUNTIME_NAMES and p.name!='seal.json' and not p.relative_to(HERE).is_relative_to('local')}
    write('seal.json',{'schema':1,'scope':'Source-only bounded Release completion admission proposal; no attempt selected or runtime executed','files':rows,'treeSHA256':v.tree(rows),'rawControlOutputLocalOnly':True})
    final=v.check()
    print(json.dumps({'tests':total,'failures':0,'errors':0,'sealSHA256':v.row(HERE/'seal.json')['sha256'],'treeSHA256':v.tree(rows),'admitSHA256':v.row(HERE/'admit.py')['sha256'],'workflowSHA256':v.row(HERE/'workflow.yml')['sha256'],'liveApiAttempts':offline.ATTEMPTS,'runtimeRuns':0,'staticSealChecked':final['staticSealChecked']},sort_keys=True))


if __name__=='__main__':main()
