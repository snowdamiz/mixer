"""Rehash inputs, retire owned scratch on every path, and freeze report/hints."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import traceback
from bind_inputs import OWNED, ROOT, EXPECTED, bind, row, sha, stable

def guard(event,args):
    if event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex','socket.getaddrinfo'):
        raise AssertionError('Final review binding forbids '+event)
sys.addaudithook(guard)
REPORT=ROOT/'docs/apple-focus-reference-runtime-v4-independent-review.md'

def verify():
    path=OWNED/'handoff.json';handoff=json.loads(path.read_bytes())
    assert handoff['producerHandoffSHA256']==EXPECTED['handoff.json']
    assert handoff['packetSHA256']==EXPECTED['packet.json']
    assert handoff['producerHostReceiptSHA256']==EXPECTED['host-attempt-2/receipt.json']
    assert sha(stable(handoff['members']))==handoff['memberTreeSHA256']
    for name,expected in handoff['members'].items():assert row(ROOT/name)==expected,name
    assert not list(OWNED.glob('.scratch-*'))
    assert handoff['reviewAccepted'] is False and handoff['dispatchAuthorized'] is False
    return {'handoffSHA256':sha(path.read_bytes()),'memberTreeSHA256':handoff['memberTreeSHA256'],
            'members':len(handoff['members']),'reviewAccepted':False,'dispatchAuthorized':False,
            'scope':'Frozen independent host-review files only; no native execution'}

def finish():
    assert not (OWNED/'handoff.json').exists(),'Preserve frozen handoff'
    meta=json.loads((OWNED/'input-bindings.json').read_bytes());scratch=Path(meta['scratch'])
    assert scratch.parent==OWNED and scratch.name.startswith('.scratch-')
    cleanup_error=None;unchanged=False;copy_unchanged=False;supplement_unchanged=False
    try:
        after,_,_,_=bind()
        assert after==meta['bindings'];unchanged=True
        repo=Path(meta['scratchRepo'])
        for name,expected in after.items():
            path=scratch/('external' if name.startswith('/') else 'repo')/name.lstrip('/')
            assert row(path)==expected,name
        copy_unchanged=True
        supplemental=json.loads((OWNED/'supplemental-inputs.json').read_bytes())
        for name,expected in supplemental['members'].items():
            original=ROOT/name;info=original.lstat();raw=original.read_bytes()
            observed={'kind':'file','mode':info.st_mode & 0o777,'bytes':len(raw),'sha256':sha(raw)}
            assert observed==expected,name
            assert row(repo/name)==expected,name
        supplement_unchanged=True
        latest=json.loads((OWNED/'independent-attempt-2/receipt.json').read_bytes())
        assert latest['testsRun']==36 and latest['controlsPassed']==30 and len(latest['failures'])==6 and latest['errors']==[] and latest['skipped']==[]
        replay=json.loads((OWNED/'replay-attempt-3/controls/receipt.json').read_bytes())
        assert replay['passed'] is True
        assert replay['historicalReview']['controls']==33 and replay['historicalReview']['passed']==32 and replay['historicalReview']['retainedHistoricalFixtureFailures']==1
        original_replay=json.loads((OWNED/'replay-attempt-1/controls/receipt.json').read_bytes())
        assert len(original_replay['suiteResults']['repair']['failures'])==18
        assert original_replay['v3ReviewReplay']['composedInventoryControls']=={'run':25,'passed':0}
        (OWNED/'input-bindings-after.json').write_bytes(stable({'bindings':after,'bindingTreeSHA256':sha(stable(after)),
            'allFrozenInputsUnchanged':True,'scratchCopyFrozenInputsUnchanged':True,'supplementalInputsUnchanged':True}))
        mistakes={'schema':'mixer.apple-focus-reference-runtime-v4-reviewer-harness-errors.1',
          'preservedAttempts':[
            {'attempt':'supplemental binding initial execution','reviewerError':'Canonical native Settings journals have st_nlink=2; initial use of frozen regular-row nlink=1 assertion rejected the snapshot before copying any file.',
             'correction':'Record native source device/inode/link identity separately; bind read-only file bytes/mode and create ordinary independent copies.'},
            {'attempt':'replay-attempt-2','reviewerError':'Wrapper was launched despite prior supplemental snapshot assertion; the copied closure replay ran without supplemental journals and final wrapper receipt write raised FileNotFoundError for supplemental-inputs.json.',
             'evidence':'replay-attempt-2/controls/receipt.json and complete logs/results survive unchanged.',
             'correction':'Require supplemental manifest before launching; successful supplemental execution is replay-attempt-3.'},
            {'attempt':'independent-attempt-1','reviewerError':'test_27 replaced a timestamp with a prefix of another original timestamp, creating two raw match candidates.',
             'correction':'Replace all old raw timestamp tokens with unique placeholders before substituting new numeric tokens; test_27 passes in independent-attempt-2.'}],
          'producerFindingsUnaffectedByReviewerHarnessErrors':True}
        (OWNED/'reviewer-harness-errors.json').write_bytes(stable(mistakes))
    except BaseException:
        cleanup_error=traceback.format_exc()
        raise
    finally:
        if scratch.exists():shutil.rmtree(scratch)
        cleanup={'schema':'mixer.apple-focus-reference-runtime-v4-independent-cleanup.1',
            'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'command':[sys.executable,'-B',str(Path(__file__).resolve())],
            'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),'hostUname':list(os.uname()),
            'allFrozenInputsUnchanged':unchanged,'copiedFrozenInputsUnchanged':copy_unchanged,
            'supplementalInputBytesUnchanged':supplement_unchanged,'ownedHostScratchAbsent':not scratch.exists(),
            'remainingOwnedScratch':[str(p) for p in OWNED.glob('.scratch-*')],
            'nativeCommandsInvoked':0,'nativeInstancesCreatedOrQueried':0,'servicesStarted':0,
            'uiOrCapturePerformed':False,'gitQueryOrMutationPerformed':False,'sharedTrackingEdited':False,
            'excludedHostedLanesReadImportedOrExecuted':False,'otherProjectsTouched':False,'cleanupError':cleanup_error}
        (OWNED/'cleanup.json').write_bytes(stable(cleanup))
    assert not cleanup['remainingOwnedScratch'] and cleanup_error is None
    members={str(REPORT.relative_to(ROOT)):row(REPORT)}
    for path in sorted(OWNED.rglob('*')):
        assert not path.is_symlink(),path
        if path.is_file():members[str(path.relative_to(ROOT))]=row(path)
    hints=json.loads((OWNED/'hints.json').read_bytes())
    handoff={'schema':'mixer.apple-focus-reference-runtime-v4-independent-frozen-handoff.1',
        'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,
        'producerHandoffSHA256':EXPECTED['handoff.json'],'packetSHA256':EXPECTED['packet.json'],
        'producerHostReceiptSHA256':EXPECTED['host-attempt-2/receipt.json'],
        'sourceRevisionLabel':meta['sourceRevisionLabel'],'sourceRevisionMeaning':meta['sourceRevisionMeaning'],
        'sourceTreeSHA256':hints['sourceTreeSHA256'],'productArchiveSHA256':hints['productArchiveSHA256'],
        'reportSHA256':sha(REPORT.read_bytes()),'hintsSHA256':sha((OWNED/'hints.json').read_bytes()),
        'members':members,'memberTreeSHA256':sha(stable(members)),
        'reviewAccepted':False,'dispatchAuthorized':False,'disposition':'rejected-for-dispatch',
        'findings':{'P1':['F1','F2'],'P2':['F3','F4']},
        'frozenProducerMembersVerified':535,'frozenDependenciesVerified':621,'explicitClosureCopiedBeforeReplay':True,
        'supplementalHistoricalInputFiles':276,'supplementalWasBoundByProducer':False,
        'exactClosureReplay':{'producer':{'run':111,'passed':111},'repair':{'run':25,'passed':7},
            'v3Reviewer':{'run':37,'passed':12,'compositionSubset':{'run':25,'passed':0}},'precision':{'run':19,'passed':19,'adapterCases':35},
            'frozenAdapter':{'run':8,'passed':8},'historical':{'run':33,'passed':32,'retainedMalformedFixtureFailures':1}},
        'supplementalReplay':{'producer':{'run':111,'passed':111},'repair':{'run':25,'passed':25},
            'v3Reviewer':{'run':37,'passed':37,'compositionSubset':{'run':25,'passed':25}},'precision':{'run':19,'passed':19,'adapterCases':35},
            'frozenAdapter':{'run':8,'passed':8},'historical':{'run':33,'passed':32,'retainedMalformedFixtureFailures':1}},
        'independentControls':{'run':36,'passed':30,'failed':6,'errors':0,'skipped':0,
            'actualAdapterAttempts':89,'actualCapturedDerivedSummaryCalls':84,'hostileContextProfiles':32,
            'independentExactScalarCases':1800,'independentSubnanosecondScalarCases':800},
        'cleanup':cleanup,'freshRootSelectionRequiredForAnyLaterReviewedDispatch':True,
        'nativeExecuted':False,'runtimeSelected':False,'compileRerun':False,'runPassed':False,
        'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,
        'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,
        'physicalPhones':'disconnected-deferred','scope':'Independent host-only frozen-source review; synthetic adapters and composition probes; rejected packet'}
    with (OWNED/'handoff.json').open('xb') as stream:stream.write(stable(handoff))
    return verify()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    print(json.dumps(verify() if args.verify else finish(),sort_keys=True))
