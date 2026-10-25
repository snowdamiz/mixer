"""Freeze or verify the V5 host-only handoff. Never dispatches native work."""
import argparse
import datetime
import gzip
import io
import json
from pathlib import Path
import sys
import tarfile
from verify_host import BASE,ROOT,SOURCES,row,sha,stable

def verify():
    handoff=json.loads((BASE/'handoff.json').read_bytes())
    assert sha(stable(handoff['members']))==handoff['memberTreeSHA256']
    for name,expected in handoff['members'].items():assert row(ROOT/name)==expected,name
    packet=json.loads((BASE/'packet.json').read_bytes())
    assert row(BASE/'packet.json')['sha256']==handoff['packetSHA256']
    for name,expected in packet['files'].items():assert row(BASE/name)==expected,name
    print(json.dumps({'members':len(handoff['members']),'memberTreeSHA256':handoff['memberTreeSHA256'],'packetSHA256':handoff['packetSHA256'],
                      'handoffSHA256':row(BASE/'handoff.json')['sha256'],'nativeExecuted':False},sort_keys=True))

def freeze(attempt):
    assert not (BASE/'handoff.json').exists() and not (BASE/'packet.json').exists()
    output=BASE/('host-attempt-'+str(attempt));receipt=json.loads((output/'receipt.json').read_bytes());assert receipt['passed']
    controls=json.loads((output/'controls/receipt.json').read_bytes());assert controls['passed']
    for name in ['runtime-sources.tar.gz','runtime-source-manifest.json','selection-template.json']:
        raw=(output/'controls'/name).read_bytes();(BASE/name).write_bytes(raw)
    # Bind actual data and all selected composed source paths, not prose counts.
    inputs=json.loads((BASE/'input-bindings.json').read_bytes())
    (BASE/'input-lock.json').write_bytes(stable(inputs['bindings']))
    with tarfile.open(BASE/'frozen-inputs.tar.gz','r:gz') as tar:
        old_manifest=json.loads(tar.extractfile('verification/apple-focus-reference-runtime-v4/runtime-source-manifest.json').read())
        old_raw=tar.extractfile('verification/apple-focus-reference-runtime-v4/runtime-sources.tar.gz').read()
    with tarfile.open(fileobj=io.BytesIO(old_raw),mode='r:gz') as tar:
        old={m.name.removeprefix('selected/'):tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    with tarfile.open(BASE/'runtime-sources.tar.gz','r:gz') as tar:
        new={m.name.removeprefix('selected/'):tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    assert set(old)==set(new)==set(old_manifest['files']) and len(new)==31
    changed=sorted(name for name in new if old[name]!=new[name]);assert changed==['importer.py','join_support.py']
    unchanged={name:{'bytes':len(raw),'sha256':sha(raw)} for name,raw in new.items() if name not in changed}
    identity={'schema':'mixer.apple-focus-reference-runtime-v5-selected-source-identity.1',
              'selectedFiles':json.loads((BASE/'runtime-source-manifest.json').read_bytes())['files'],
              'changedSelectedPaths':changed,'unchangedSelectedPaths':unchanged,'unchangedSelectedCount':29,
              'inputFiles':len(inputs['bindings']),'inputTreeSHA256':inputs['bindingTreeSHA256'],
              'supplementalSettingsMembers':inputs['supplementalSettings']['members'],
              'supplementalSettingsTreeSHA256':inputs['supplementalSettings']['treeSHA256'],
              'v4DidNotBindSupplementalBytes':True,
              'sourceTreeSHA256':controls['sourceTreeSHA256'],'productArchiveSHA256':controls['productArchiveSHA256'],
              'originalOracleActionBudgetTimingNativeProductsUnchanged':True,'nativeExecuted':False}
    (BASE/'selected-source-identity.json').write_bytes(stable(identity))
    tested=json.loads((output/'closed-packet-manifest.json').read_bytes())['members']
    final_sources={str((BASE/name).relative_to(ROOT)):row(BASE/name) for name in SOURCES}
    doc=ROOT/'docs/apple-focus-reference-runtime-v5.md';final_sources[str(doc.relative_to(ROOT))]=row(doc)
    finalization_changes=[name for name,expected in final_sources.items() if expected!=tested[name]]
    allowed={str((BASE/name).relative_to(ROOT)) for name in ['freeze.py','v4-to-v5-repair.patch']}
    allowed.add(str(doc.relative_to(ROOT)))
    assert set(finalization_changes)<=allowed, finalization_changes
    assert new['importer.py']==(BASE/'importer.py').read_bytes()
    assert new['join_support.py'].endswith((BASE/'adapter.py').read_bytes())
    with (BASE/'v5-final-sources.tar.gz').open('xb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0,filename='') as zipped,tarfile.open(fileobj=zipped,mode='w') as tar:
        for name,expected in final_sources.items():
            raw=(ROOT/name).read_bytes();member=tarfile.TarInfo(name);member.size=len(raw);member.mode=expected['mode'];member.mtime=0;tar.addfile(member,io.BytesIO(raw))
    final_manifest={'schema':'mixer.apple-focus-reference-runtime-v5-final-source-manifest.1','members':final_sources,
                    'memberTreeSHA256':sha(stable(final_sources)),'archive':row(BASE/'v5-final-sources.tar.gz'),
                    'metadataFinalizationChangesAfterTestedSnapshot':finalization_changes,
                    'meaning':'Runtime implementation and all controls match passing isolated attempt 3; only finalizer bookkeeping, its repair diff and completed report changed afterward',
                    'executedFinalizerSHA256':row(BASE/'freeze.py')['sha256'],'nativeExecuted':False}
    (BASE/'v5-final-source-manifest.json').write_bytes(stable(final_manifest))
    files={name:row(BASE/name) for name in ['input-bindings.json','input-lock.json','frozen-inputs.tar.gz','runtime-sources.tar.gz','runtime-source-manifest.json','selection-template.json',
                                          'namespace-adaptation.patch','v4-to-v5-repair.patch','selected-source-identity.json','v5-final-sources.tar.gz','v5-final-source-manifest.json']}
    # Preserve the preparer's closed verification contract for a future separately
    # reviewed isolated materialization; this does not select or dispatch a run.
    import ast
    tree=ast.parse((BASE/'prepare.py').read_text())
    owned=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OWNED' for t in n.targets)))
    owned_rows={name:row(BASE/name) for name in owned}
    packet={'schema':'mixer.apple-focus-reference-runtime-packet.5','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'sourceTreeSHA256':controls['sourceTreeSHA256'],'productArchiveSHA256':controls['productArchiveSHA256'],
            'sourceRevisionLabel':controls['sourceRevisionLabel'],'sourceRevisionMeaning':controls['sourceRevisionMeaning'],
            'ownedSources':owned_rows,'ownedSourceTreeSHA256':sha(stable(owned_rows)),
            'documentation':row(ROOT/'docs/apple-focus-reference-runtime-v5.md'),
            'hostAttempt':attempt,'hostReceipt':row(output/'receipt.json'),'closedPacketArchive':row(output/'closed-packet.tar.gz'),
            'closedPacketManifest':row(output/'closed-packet-manifest.json'),'files':files,'rootSelectionSchema':'mixer.apple-focus-reference-root-selection.5',
            'ownedNamePrefix':'MixerFocusReferenceV5-','outputPrefix':'native-run-v5-',
            'canonicalRootTime':'ISO calendar date/time; no fraction or exactly six digits; canonical whole-minute ±HH:MM offset; exact calendar/isoformat roundtrip before ordering; emitter UTC',
            'independentV5ReviewPending':True,'freshRootSelectionRequired':True,'runtimeSelected':False,'nativeExecuted':False,
            'compileRerun':False,'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,
            'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred'}
    (BASE/'packet.json').write_bytes(stable(packet))
    # Full output archive is explicit and separate from the immutable input packet.
    attempts=[p for p in BASE.iterdir() if p.is_dir() and (p.name.startswith('host-attempt-') or p.name.startswith('bootstrap-attempt-'))]
    output_rows={str(p.relative_to(BASE)):row(p) for directory in sorted(attempts) for p in sorted(directory.rglob('*')) if p.is_file()}
    with (BASE/'host-outputs.tar.gz').open('xb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0,filename='') as zipped,tarfile.open(fileobj=zipped,mode='w') as tar:
        for name,expected in output_rows.items():
            raw=(BASE/name).read_bytes();member=tarfile.TarInfo(name);member.size=len(raw);member.mode=expected['mode'];member.mtime=0;tar.addfile(member,io.BytesIO(raw))
    (BASE/'host-output-manifest.json').write_bytes(stable({'members':output_rows,'memberTreeSHA256':sha(stable(output_rows)),'archive':row(BASE/'host-outputs.tar.gz')}))
    paths=[p for p in BASE.rglob('*') if p.is_file()]
    members={str(p.relative_to(ROOT)):row(p) for p in sorted(paths)}
    doc=ROOT/'docs/apple-focus-reference-runtime-v5.md';members[str(doc.relative_to(ROOT))]=row(doc)
    handoff={'schema':'mixer.apple-focus-reference-runtime-frozen-handoff.5','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'command':[sys.executable,'-B',str(Path(__file__).resolve()),'freeze','--attempt',str(attempt)],'python':sys.version,
             'packetSHA256':row(BASE/'packet.json')['sha256'],'hostReceiptSHA256':row(output/'receipt.json')['sha256'],
             'members':members,'memberTreeSHA256':sha(stable(members)),
             'frozenV4ProducerHandoffSHA256':'79a8a2d5070b1f9466831089be0f2f89d1e67d3785c707879414ea2edac9ca07',
             'frozenRejectedV4ReviewHandoffSHA256':'93c6505ba122b532aafe3fdcd65a3a09273d046fafc37d633b9ec860dd503233',
             'results':{'producer':111,'repair':25,'v3Reviewer':37,'v3ComposedSubset':25,'precision':19,'precisionAdapterCases':controls['precisionAdapterCases'],
                        'frozenAdapter':8,'historical':{'run':33,'passed':32,'retainedMalformedFixtureFailures':1},
                        'v4Independent':{'run':36,'passed':36},'v5Focused':16,'v5AdapterCases':controls['v5AdapterCases']},
             'cleanup':receipt['cleanup'],'independentV5ReviewPending':True,'freshRootSelectionRequired':True,'runtimeSelected':False,
             'nativeExecuted':False,'compileRerun':False,'uiOrCapturePerformed':False,'gitMutationPerformed':False,
             'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,
             'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred',
             'scope':'Host-only repair; frozen inputs, synthetic adapter and actual Bridge/Session/TransactionStore composition; no dispatch credit'}
    (BASE/'handoff.json').write_bytes(stable(handoff));verify()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','verify']);p.add_argument('--attempt',type=int);args=p.parse_args()
    if args.action=='freeze':freeze(args.attempt)
    else:verify()
