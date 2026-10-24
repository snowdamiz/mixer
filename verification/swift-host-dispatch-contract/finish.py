#!/usr/bin/env python3
"""Verify the retained compiler packet, then retire only its owned scratch."""
from pathlib import Path
import collections, gzip, json, re, shutil, subprocess, tarfile
import probe
from probe import HERE, ROOT, enc, save, sha, manifest, digest, now

def main():
    session=json.loads((HERE/'session.json').read_text());scratch=Path(session['scratch'])
    assert scratch.parent==Path('/tmp') and scratch.name.startswith('mixer-host-contract-')
    schema=json.loads((HERE/'inventory-schema.json').read_text())
    layouts=json.loads((HERE/'layouts.json').read_text())
    assert len(layouts)==16
    for features in ['swift','all']:
        for profile in ['debug','release']:
            for unit in [False,True]:
                base=next(x for x in layouts if (x['label'],x['features'],x['profile'],x['unit'])==('baseline',features,profile,unit))
                current=next(x for x in layouts if (x['label'],x['features'],x['profile'],x['unit'])==('candidate',features,profile,unit))
                assert base['types']==current['types'] and base['owners']==current['owners']
                for key,value in base['totals'].items():assert current['totals'][key]==value
                assert current['totals']['ticket_max']==86
                assert current['totals']['state_limit']==134217728 and current['totals']['combined_limit']==268435456
                expected={r['field'] for r in schema if unit or r['config']!='unit'}
                assert set(current['fields'])==expected
                occupied={}
                for row in sorted((r for r in schema if r['field'] in expected),key=lambda r:(r['ownerClass'],current['fields'][r['field']]['offset'])):
                    field=current['fields'][row['field']];cls=row['ownerClass']
                    assert field['offset']>=occupied.get(cls,0)
                    assert field['offset']%field['alignment']==0
                    occupied[cls]=field['offset']+field['bytes']
                    assert occupied[cls]<=current['classes'][cls]['bytes']
    closure_layouts={}
    for config,name in [('production','actual-closure-layouts'),('unit','actual-closure-layouts-unit')]:
        output=gzip.decompress((HERE/'commands'/name/'stdout.gz').read_bytes()).decode()
        found={}
        for site,size,alignment in re.findall(r'print-type-size type: `(\{closure@src/experimental_wasi/accounted.rs:[^}]+\})`: (\d+) bytes, alignment: (\d+) bytes',output):
            if site in json.loads((HERE/'closure-captures.json').read_text())[config]:
                found[site]=dict(bytes=int(size),alignment=int(alignment))
        assert len(found)==2 and all(x==dict(bytes=8,alignment=8) for x in found.values()),found
        closure_layouts[config]=found
    save('actual-closure-layouts.json',dict(actualCompilerLayout=closure_layouts,
        attribution='Each one-reference closure has its independently measured 8-byte/8-alignment positive position; no prior alias supplies credit.'))
    archives={}
    for p in sorted(HERE.glob('*source-manifest.json')):
        name=p.name.removesuffix('-source-manifest.json');m=json.loads(p.read_text())
        archive=HERE/(name+'-source.tar.gz')
        assert archive.exists(),archive
        with tarfile.open(archive) as tar:
            actual={x.name:sha(tar.extractfile(x).read()) for x in tar.getmembers() if x.isfile()}
        assert actual==m,(name,set(actual)^set(m))
        archives[name]=dict(files=len(m),sourceTreeSHA256=digest(m),archiveSHA256=sha(archive.read_bytes()))
    save('verified-source-archives.json',archives)
    save('metadata-source-closures.json',{name:archives[name]['sourceTreeSHA256'] for name in ['metadata-baseline','metadata-candidate']})
    expected_trees={a['sourceTreeSHA256'] for a in archives.values()}
    commands={}
    for p in sorted((HERE/'commands').glob('*/receipt.json')):
        result=json.loads(p.read_text());name=p.parent.name
        if result['sourceTreeSHA256']:
            assert result['sourceUnchanged'] and result['sourceTreeSHA256'] in expected_trees,(name,result['sourceTreeSHA256'])
            assert digest(json.loads((p.parent/'source-manifest.json').read_text()))==result['sourceTreeSHA256']
        for stream in ['stdout','stderr']:
            assert sha(gzip.decompress((p.parent/(stream+'.gz')).read_bytes()))==result[stream+'SHA256']
        commands[name]=result
    qualifying={name:row for name,row in commands.items() if not name.startswith(('draft','negative-')) or name.startswith('negative-final-')}
    for name,row in qualifying.items():assert row['exitCode']==(101 if name.startswith('negative-final-') else 0),(name,row['exitCode'])
    negative=json.loads((HERE/'negative-final-borrows.json').read_text())
    assert set(negative)=={'arguments','cache-view','cache-phase'}
    frozen=json.loads((HERE/'frozen-identity.json').read_text())
    assert frozen['methodCount']==39 and frozen['containingOwnerCount']==14
    assert frozen['unchangedMemoryBulkRows']=={'memory_operations':4800,'bulk_memory_operations':4324}
    live_now=digest(manifest(ROOT/'vm'))
    # Retire only this unique source/build directory. Finished child processes
    # are already reaped; an open holder aborts cleanup without killing it.
    started=now()
    command=['/usr/sbin/lsof','-nP','+D',str(scratch)]
    holders=subprocess.run(command,capture_output=True,timeout=60)
    for stream in ['stdout','stderr']:
        with gzip.open(HERE/('cleanup-lsof-'+stream+'.gz'),'wb') as z:z.write(getattr(holders,stream))
    assert holders.returncode==1 and not holders.stdout,holders.stdout.decode(errors='replace')
    files=[p for p in scratch.rglob('*') if p.is_file()]
    count=len(files);bytes_before=sum(p.stat().st_size for p in files)
    shutil.rmtree(scratch)
    cleanup=dict(startedUTC=started,completedUTC=now(),scratch=str(scratch),lsofArgv=command,
        lsofExitCode=holders.returncode,lsofObservedNoOpenFiles=True,files=count,logicalFileBytes=bytes_before,
        ownedScratchRemoved=not scratch.exists(),processesTerminated=False,deviceInstancesCreated=0,
        simulatorOrEmulatorStarted=False,otherProjectDataTouched=False,sourceArchivesVerifiedBeforeRemoval=sorted(archives))
    save('cleanup.json',cleanup)
    for p in (HERE/'__pycache__').glob('*'):p.unlink()
    if (HERE/'__pycache__').exists():(HERE/'__pycache__').rmdir()
    counts=dict(collections.Counter(r['config'] for r in schema))
    totals={label:next(x for x in layouts if x['label']=='candidate' and x['unit']==unit)['totals'] for label,unit in [('production',False),('unit',True)]}
    historical=[dict(command=name,exitCode=row['exitCode'],sourceTreeSHA256=row['sourceTreeSHA256']) for name,row in commands.items() if name not in qualifying]
    save('historical-attempts.json',dict(commands=historical,
        limitations='Draft compiler witnesses passed. Three metadata generator spellings needed public re-export paths; corrected metadata passed all eight candidate configurations. Early identity scan counted six ordinary struct-literal fields outside accounting; corrected scanner counts only the immutable accounting region.'))
    bindings={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='receipt.json'}
    doc=ROOT/'docs/swift-host-dispatch-contract.md';bindings[str(doc.relative_to(ROOT))]=sha(doc.read_bytes())
    versions={name:gzip.decompress((HERE/'commands'/('tool-'+name)/'stdout.gz').read_bytes()).decode().strip() for name in ['rustc','cargo','host','git','python']}
    receipt=dict(schema=1,status='selected-contract-with-uncalled-compiler-feasibility-evidence',observedUTC=now(),
        authority='Root selected bounded contract/uncalled feasibility; no runtime specimen authorization.',
        baselineGitRevision='a1f78d1e88d6e1e934a08cdb85ce90f87f6ff343',
        baselineSourceClosure=archives['baseline']['sourceTreeSHA256'],candidateSourceClosure=archives['candidate']['sourceTreeSHA256'],
        baselineSourceFiles=125,currentLiveVMClosure=live_now,thisLaneEditedLiveVM=False,
        compiledPrerequisitePassed=True,actualPairedMetadataLayouts=16,positiveFields=len(schema),positiveFieldClasses=counts,
        actualCompilerBodies=len(json.loads((HERE/'function-manifest.json').read_text())),
        unchangedFrozenExpandedMethods=39,unchangedContainingOwners=14,unchangedMemoryFields=4800,unchangedBulkFields=4324,
        proposedAccounting=totals,accountingIntegrated=False,logicalAccountingOnly=True,actualClosureLayouts=closure_layouts,
        frozenReservationSourceUnchanged=True,frozenAcceptedReservationBytes=2912,ticketMaximum=86,
        stateLimit=134217728,combinedLimit=268435456,
        negativeBorrowCases=negative,qualifyingCommandCount=len(qualifying),qualifyingCommands=sorted(qualifying),
        tools=versions,cleanup=cleanup,sourceArchives=archives,bindings=bindings,boundEvidenceFiles=len(bindings),
        runtimeGroups={f'H{i:02}':'pending' for i in range(1,17)},runtimeAccepted=False,hostOperationExecuted=False,
        fullDispatcher=False,fullSwiftExecuted=False,Ready=False,publicInvocation=False,nativeRuntime=False,
        physicalRuntime=False,publishedFieldLogConsumer=False,gaAcceptance=False,committed=False,pushed=False,
        limitations=[
            'The probe methods are uncalled: compilation, MIR and metadata do not prove host semantics, counters, allocation or cleanup behavior.',
            'Positive amounts are proposed additions against the pre-growth baseline, not live integrated bounds; rebase/remeasure after accepted growth integration.',
            'The fixed entry slot remains sole outcome; outer publication Ok is not operation success.',
            'Ordinary defined/indirect call dispatch, full instruction loop, Ready/public invocation and full Swift execution are pending.',
            'Frozen expanded/source identity is observed; this lane executes no new Frozen runtime trace.',
            'Logical named objects only; no compiler stack, optimizer temporary, allocator overhead or RSS bound.',
            'Existing absent-cursor cleanup diagnostic remains an open G08 limitation.',
            'No native/device/UI, physical phone, published separate-repository FieldLog, signing/store/customer/operational/GA qualification.',
        ])
    save('receipt.json',receipt)
    print('Verified',len(bindings),'bindings,',len(qualifying),'qualifying compiler/layout/negative commands; owned scratch removed')
if __name__=='__main__':main()
