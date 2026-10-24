#!/usr/bin/env python3
"""Seal every command receipt and retire only this replay's owned scratches."""
from pathlib import Path
import datetime, gzip, hashlib, json, shutil, subprocess, sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
enc=lambda value:(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
sha=lambda data:hashlib.sha256(data).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,value):(HERE/name).write_bytes(enc(value))
def source_manifest(vm):
    paths=[vm/'Cargo.toml',vm/'Cargo.lock']
    for name in ['src','tests','include']:paths+=sorted(p for p in (vm/name).rglob('*') if p.is_file())
    return {str(p.relative_to(vm)):sha(p.read_bytes()) for p in paths}
def main():
    seal_path=HERE/'receipt.json';assert not seal_path.exists()
    preflight=subprocess.run([sys.executable,str(HERE/'verify.py'),'--preseal'],cwd=ROOT,capture_output=True,timeout=60)
    for stream in ['stdout','stderr']:
        with gzip.open(HERE/('preseal-verification-'+stream+'.gz'),'wb') as z:z.write(getattr(preflight,stream))
    assert preflight.returncode==0,preflight.stderr.decode()
    checked=json.loads(preflight.stdout);assert checked['status']=='verified'
    save('verification-summary.json',checked)
    sources=json.loads((HERE/'source-closures.json').read_text())
    sessions=[('final',json.loads((HERE/'session.json').read_text())),
        ('historical-attempt-1',json.loads((HERE/'historical-attempt-1/session.json').read_text()))]
    cleanup=[]
    for label,session in sessions:
        scratch=Path(session['scratch'])
        assert scratch.parent==Path('/tmp') and scratch.name.startswith('mixer-host-layout-replay-')
        before={name:source_manifest(scratch/('source-'+digest)) for name,digest in sources.items()}
        for name,m in before.items():assert sha(enc(m))==sources[name]
        started=now();argv=['/usr/sbin/lsof','-nP','+D',str(scratch)]
        p=subprocess.run(argv,capture_output=True,timeout=60)
        for stream in ['stdout','stderr']:
            with gzip.open(HERE/('cleanup-'+label+'-'+stream+'.gz'),'wb') as z:z.write(getattr(p,stream))
        assert p.returncode==1 and not p.stdout,(label,p.returncode,p.stdout.decode(errors='replace'))
        after={name:source_manifest(scratch/('source-'+digest)) for name,digest in sources.items()}
        assert before==after
        files=[p for p in scratch.rglob('*') if p.is_file()]
        count=len(files);bytes_before=sum(p.stat().st_size for p in files)
        shutil.rmtree(scratch)
        cleanup.append(dict(label=label,scratch=str(scratch),startedUTC=started,completedUTC=now(),
            lsofArgv=argv,lsofExitCode=p.returncode,lsofObservedNoOpenHolders=True,
            sourceClosuresBefore=sources,sourceClosuresAfter=sources,sourceUnchanged=True,
            files=count,logicalFileBytes=bytes_before,removed=not scratch.exists(),processesTerminated=False))
    save('cleanup.json',dict(directories=cleanup,otherProjectDataTouched=False,deviceInstancesCreated=0,
        simulatorOrEmulatorStarted=False,liveVMEdited=False,gitOrTrackersEdited=False))
    frozen=json.loads((HERE/'frozen-original-file-bindings.json').read_text())
    for name,digest in frozen.items():assert sha((ROOT/name).read_bytes())==digest,name
    records=json.loads((HERE/'layouts.json').read_text())
    commands=sorted((HERE/'commands').glob('*/receipt.json'));assert len(commands)==44
    # Only the exact self seal is omitted. All nested receipt.json files bind.
    bindings={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and p!=seal_path}
    doc=ROOT/'docs/swift-host-dispatch-layout-replay.md';bindings[str(doc.relative_to(ROOT))]=sha(doc.read_bytes())
    assert all(str(p.relative_to(ROOT)) in bindings for p in commands)
    receipt=dict(schema=1,status='fresh-source-and-executable-bound-layout-replay',observedUTC=now(),
        baselineGitRevision='a1f78d1e88d6e1e934a08cdb85ce90f87f6ff343',
        exactArchivedMetadataSourceClosures=sources,metadataSourceFiles=126,
        finalContexts=16,distinctInitiallyEmptyCargoTargets=16,cargoSelectedArtifactsFreshFalse=16,
        retainedExactExecutables=16,exactExecutableRuns=16,fullUnitTestLists=8,
        unitTestCounts={'swift':201,'all':230},unitLayoutTestsRun=8,unitLayoutTestsPassed=8,
        sourceBoundCommandReceipts=44,allPerCommandReceiptsSealed=True,
        sourceFilesAndFullClosureCheckedBeforeAfterEveryCommand=True,
        executableHashesCheckedBeforeAfter=True,
        matchedAllFrozenProposedTypeOwnerFieldAndTotalValues=True,positivePositions=4768,
        originalFrozenPacketFilesUnchanged=len(frozen),frozenOriginalReceiptSHA256=sha((ROOT/'verification/swift-host-dispatch-contract/receipt.json').read_bytes()),
        earlierAmbiguousMetadataOutputsUsedAsFinalSourceAcceptanceEvidence=False,
        historicalOutputUse='Numeric proposal comparison only; all accepted measurements come from fresh context targets and exact archived executables.',
        logicalAccountingOnly=True,preGrowthAdditiveBoundsOnly=True,
        proposedAccounting={kind:next(x['layout']['totals'] for x in records if x['label']=='candidate' and x['unit']==unit) for kind,unit in [('production',False),('unit',True)]},
        verification=checked,cleanup=json.loads((HERE/'cleanup.json').read_text()),bindings=bindings,boundFiles=len(bindings),
        hostOperationExecuted=False,interpreterExecuted=False,runtimeAccepted=False,accountingIntegrated=False,
        fullSwiftExecuted=False,Ready=False,publicInvocation=False,nativeRuntime=False,physicalRuntime=False,
        gaAcceptance=False,committed=False,pushed=False,
        limitations=[
          'Only exact metadata printing artifacts and one exact layout unit test per unit context execute; host imports and interpreter instructions never run.',
          'Amounts remain pre-growth proposed additions; source-bound rebase/re-measure is required after accepted growth integration.',
          'All H01-H16 runtime behavior, counters, allocation, cleanup and first-failure groups remain pending.',
          'Logical named object reservations only; no stack, optimizer temporary, allocator overhead or RSS bound.',
          'No native/device/UI/full Swift/Ready/public/release/store/customer/operational/GA acceptance.',
        ])
    save('receipt.json',receipt)
    print('Sealed',len(bindings),'files including all',len(commands),'command receipts; both owned scratches removed')
if __name__=='__main__':main()
