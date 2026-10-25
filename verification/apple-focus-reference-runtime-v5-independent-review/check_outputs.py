"""Independent checks of newly generated retained replay evidence."""
import hashlib
import json
from pathlib import Path
import tarfile

BASE=Path(__file__).resolve().parent
stable=lambda v:(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
sha=lambda b:hashlib.sha256(b).hexdigest()

def main():
    receipt=json.loads((BASE/'attempt-1/retained-replay-receipt.json').read_bytes())
    selected=json.loads((BASE.parent/'apple-focus-reference-runtime-v5/runtime-source-manifest.json').read_bytes())
    assert receipt['selectedSourceManifest']['files']==selected['files']
    manifest=json.loads((BASE/'attempt-1/retained-replay-output-manifest.json').read_bytes())
    archive=BASE/'attempt-1/retained-replay-outputs.tar.gz'
    assert sha(archive.read_bytes())==manifest['archive']['sha256']
    with tarfile.open(archive,'r:gz') as tar:
        members=tar.getmembers();assert len(members)==len(manifest['members'])
        assert {m.name for m in members}==set(manifest['members'])
        for m in members:
            raw=tar.extractfile(m).read();want=manifest['members'][m.name]
            assert {'kind':'file','mode':m.mode,'bytes':len(raw),'sha256':sha(raw)}==want
        def payload(name):return tar.extractfile('v4-independent-controls/'+name).read()
        original=payload('original-control-class.py').decode()
        adapted=original.replace('runtime-v4','runtime-v5').replace('runtime_v4','runtime_v5').replace('V4','V5')
        for part in ['root-selection','reference-runtime','runtime-import','runtime-packet','runtime-host-receipt','runtime-frozen-handoff']:
            adapted=adapted.replace(part+'.4',part+'.5')
        assert adapted.encode()==payload('namespace-control-class.py')
        before=payload('original-adapter-helper.py').decode();after=before
        after=after.replace("    namespace['configure_root'](f['root'])\n", "    deferred_root_error=None\n    try:namespace['configure_root'](f['root'])\n    except ValueError as error:\n        if str(error)!='Canonical exactly representable root ISO timestamp required':raise\n        deferred_root_error=error\n",1)
        end="    return namespace,invoke,calls,types.SimpleNamespace(RUN_DIR=output/'runtime')\n"
        after=after.replace(end,"    if deferred_root_error is not None:\n        deferred_root_errors.append({'root':copy.deepcopy(f['root']),'type':type(deferred_root_error).__name__,'message':str(deferred_root_error),'stage':'actual configure_root rejected before capture'})\n        def rejected_capture(*args,**kwargs):raise deferred_root_error\n        namespace['capture_official']=rejected_capture\n"+end,1)
        assert after.encode()==payload('early-root-replay-helper.py')
    v4=receipt['v4IndependentReplay'];assert len(v4['actuallyObservedEarlyRootRejections'])==2
    assert v4['testsRun']==v4['controlsPassed']==36
    assert receipt['historicalReview']['testsRun']==33 and receipt['historicalReview']['controlsPassed']==32
    rows={'schema':'mixer.apple-focus-reference-runtime-v5-independent-output-checks.1','passed':True,
          'selectedRuntimeTreeMatchesFrozenProducerExactly':True,'selectedRuntimeTreeSHA256':selected['treeSHA256'],
          'newReplayOutputArchiveMembersVerified':len(manifest['members']),'v4ControlClassOnlyExplicitNamespaceAdapted':True,
          'helperOnlyRoutesSameObservedCanonicalRootError':True,'schemaCalendarNameErrorsRemainEarly':True,
          'actualCanonicalRootRejections':v4['actuallyObservedEarlyRootRejections'],
          'historicalMalformedFixtureRetained':{'passed':32,'run':33},'nativeExecuted':False}
    (BASE/'post-review-output-checks.json').write_bytes(stable(rows))
    print(json.dumps({k:v for k,v in rows.items() if k!='actualCanonicalRootRejections'},indent=2))

if __name__=='__main__':main()
