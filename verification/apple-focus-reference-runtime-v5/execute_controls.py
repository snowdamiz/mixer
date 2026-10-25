"""Run V5 controls inside an isolated copy of the explicitly enumerated packet."""
import argparse
from contextlib import redirect_stdout,redirect_stderr
import datetime
import json
import os
from pathlib import Path
import sys
import time
import unittest

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
assert os.environ.get('MIXER_V5_CLOSED_ROOT')==str(ROOT)
assert (ROOT/'closed-v5-root.json').is_file()
RUNTIME=Path(sys.base_prefix).resolve()
SPAWNS=[]
import hashlib
sha=lambda raw:hashlib.sha256(raw).hexdigest()
stable=lambda value:(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
from derive_v5 import namespace
meta=json.loads((BASE/'input-bindings.json').read_bytes())
programs={}
prefix='verification/apple-focus-reference-runtime-v4-independent-review/inspected-programs/'
for name in meta['bindings']:
    if name.startswith(prefix):
        raw=(ROOT/name).read_bytes();assert sha(raw)==Path(name).stem
        program=namespace(raw.decode());programs[sha(program.encode())]=program
assert len(programs)==4

def guard(event,args):
    if event=='subprocess.Popen':
        executable,argv=args[:2]
        assert Path(executable).resolve()==Path(sys.executable).resolve(),argv
        assert len(argv)==5 and argv[1:3]==['-B','-c'] and sha(argv[3].encode()) in programs,argv
        assert Path(argv[4]).resolve().is_relative_to(BASE),argv
        SPAWNS.append({'argv':argv,'programSHA256':sha(argv[3].encode()),'nativeDisabledByPinnedChildGuard':True})
    elif event in ('os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex','socket.getaddrinfo'):
        raise AssertionError('Closed V5 host forbids '+event)
    if event in ('os.scandir','os.listdir') and args and isinstance(args[0],(str,bytes)):
        path=Path(os.fsdecode(args[0])).resolve()
        assert path.is_relative_to(ROOT) or path.is_relative_to(RUNTIME),path
    if event=='open' and isinstance(args[0],(str,bytes)):
        path=Path(os.fsdecode(args[0])).resolve()
        assert not any(w in str(path).lower() for w in ('hosted','catalog','authority-driver','worker-transport')),path
        flags=args[2] if len(args)>2 else 0
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):
            fixtures=ROOT/'verification/apple-focus-diagnostic-runtime-v1/runtime/captures'
            assert path.is_relative_to(BASE) or path.is_relative_to(fixtures),path
        else:assert path.is_relative_to(ROOT) or path.is_relative_to(RUNTIME) or str(path)=='/dev/null',path
sys.addaudithook(guard);sys.dont_write_bytecode=True
os.environ['PYTHONPATH']=str(BASE/'child-guard')
import prepare
import frozen_inputs

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    out=Path(args.output).resolve();assert out.is_relative_to(BASE) and not out.exists();out.mkdir()
    started=time.monotonic();before=frozen_inputs.verify();outcomes={}
    def suite(label,module):
        with (out/(label+'.stdout.log')).open('w') as stdout,(out/(label+'.stderr.log')).open('w') as stderr,redirect_stdout(stdout),redirect_stderr(stderr):
            result=unittest.TextTestRunner(stream=stderr,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
        outcomes[label]={'testsRun':result.testsRun,'controlsPassed':result.testsRun-len(result.failures)-len(result.errors),
             'failures':[{'name':str(c),'traceback':tb} for c,tb in result.failures],
             'errors':[{'name':str(c),'traceback':tb} for c,tb in result.errors],'skipped':result.skipped,'passed':result.wasSuccessful()}
        return outcomes[label]
    runtime,accepted,products,_=prepare.inputs();derived,selection=prepare.derive(runtime)
    helpers=prepare.helpers();source_rows=prepare.manifest(derived)
    selected=out/'selected-sources';helpers.materialize(selected,source_rows,derived)
    archive=helpers.archive_sources(out/'runtime-sources.tar.gz',selected,source_rows)
    (out/'runtime-source-manifest.json').write_bytes(stable(archive))
    (out/'selection-template.json').write_bytes(stable(selection))
    import test_importer
    suite('producer',test_importer)
    import replay_review
    historical=replay_review.run(out)
    import test_repair
    suite('repair',test_repair)
    (out/'actual-composition-outcomes.json').write_bytes(stable(test_repair.FocusRepairControls.records))
    import replay_v3_review
    v3=replay_v3_review.run(out)
    import test_precision
    suite('precision',test_precision)
    (out/'exact-time-adapter-outcomes.json').write_bytes(stable(test_precision.ExactTimestampControls.records))
    import replay_v4_review
    v4=replay_v4_review.run(out)
    import test_v5
    test_v5.OUT=out/'v5-adapter-cases';test_v5.OUT.mkdir()
    suite('v5-focused',test_v5)
    (out/'v5-adapter-results.json').write_bytes(stable(test_v5.V5Controls.records))
    import replay_precision
    adapter=replay_precision.run(out)
    after=frozen_inputs.verify()
    prefixes=('pure-oracle-','archive-control-','host-packet-','composition-control-','adapter-control-','orchestration-control-',
              'actual-composition-','independent-composition-','precision-adapter-','exact-time-adapter-',
              'independent-v5-','v5-adapter-','v5-schema-','v5-namespace-')
    scratch=[str(p) for p in BASE.iterdir() if p.is_dir() and p.name.startswith(prefixes)]
    expected={'producer':111,'repair':25,'precision':19,'v5-focused':16}
    passed=(all(outcomes[n]['passed'] and outcomes[n]['testsRun']==count for n,count in expected.items())
            and historical['expectedReplayOutcome'] and v3['passed'] and v4['passed']
            and adapter['controls']==8 and adapter['controlsPassed']==8 and before==after and not scratch)
    receipt={'schema':'mixer.apple-focus-reference-runtime-host-receipt.5','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'command':[sys.executable,'-B',str(Path(__file__).resolve()),'--output',str(out)],'python':sys.version,
             'pythonExecutable':str(Path(sys.executable).resolve()),'hostUname':list(os.uname()),'elapsedSeconds':time.monotonic()-started,
             'sourceRevisionLabel':'ba9ad4372f94463ba4d363cdfd76dd565c96413f','sourceRevisionMeaning':'Inherited compile label only; closed hashes define source; no Git query',
             'inputTreeSHA256':meta['bindingTreeSHA256'],'inputFiles':len(before),'isolatedClosedTree':True,'workspaceFallbackReadsPermitted':False,
             'passed':passed,'suiteResults':outcomes,'historicalReview':historical,'v3ReviewReplay':v3,'v4IndependentReplay':v4,
             'precisionAdapterCases':len(test_precision.ExactTimestampControls.records),'v5AdapterCases':len(test_v5.V5Controls.records),
             'frozenV3ActualAdapterReplay':{'run':adapter['controls'],'passed':adapter['controlsPassed']},
             'hostPythonSubprocesses':SPAWNS,'pinnedCompositionPrograms':programs,
             'selectedSourceManifest':archive,'sourceTreeSHA256':prepare.SOURCE,'productArchiveSHA256':prepare.PRODUCT,
             'cleanup':{'allFrozenInputsUnchanged':before==after,'ownedHostTemporaryDirectoriesAbsent':not scratch,'remainingOwnedScratch':scratch,
                        'nativeCommandsInvoked':0,'nativeInstancesCreatedOrQueried':0,'servicesStarted':0,'otherProjectsTouched':False},
             'nativeExecuted':False,'compileRerun':False,'gitMutationPerformed':False,'uiOrCapturePerformed':False,
             'hostedCatalogAuthorityOrWorkerReviewReadImportedOrExecuted':False,'independentV5ReviewPending':True,'runtimeSelected':False,
             'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,
             'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred'}
    (out/'receipt.json').write_bytes(stable(receipt))
    print(json.dumps({'passed':passed,'suites':{k:{'run':v['testsRun'],'passed':v['controlsPassed'],'errors':len(v['errors'])} for k,v in outcomes.items()},
                      'v3':{'run':v3['testsRun'],'passed':v3['controlsPassed']},'v4':{'run':v4['testsRun'],'passed':v4['controlsPassed']},
                      'historical':{'run':historical['testsRun'],'passed':historical['controlsPassed']},'adapter':receipt['frozenV3ActualAdapterReplay'],
                      'cleanup':receipt['cleanup']},sort_keys=True))
    if not passed:raise SystemExit(1)

if __name__=='__main__':main()
