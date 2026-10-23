#!/usr/bin/env python3
"""Create the review evidence index after all frozen-source probes have completed."""
import datetime
import hashlib
import json
import pathlib

OUT=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for label in ['', '-repair']:
    source=OUT/('.local/source'+label)
    for line in (OUT/('frozen-source'+label+'.sha256')).read_text().splitlines():
        expected,relative=line.split('  ',1)
        assert sha(source/relative)==expected,relative
assert '19 tests' in (OUT/'cli-repaired-frozen-tests.log').read_text()
assert '6 tests in 1 suite passed' in (OUT/'runtime-probe-attempt-2.log').read_text()
assert '1 test in 1 suite passed' in (OUT/'consumer-actual-abi-probe.log').read_text()
for filename in ['staging-regressions-normal.log','staging-regressions-optimized.log']:
    assert 'Ran 9 tests' in (OUT/filename).read_text() and 'OK' in (OUT/filename).read_text()
final=json.loads((OUT/'final-artifact-audit.json').read_text())
fixed=json.loads((OUT/'staging-fix-replay.json').read_text())
assert all(all(result.get('sentinels_preserved',{}).values()) for result in fixed['results'])
source=OUT/'.local/source'
commands=[
    {'command':['/usr/bin/swift','test','--package-path',str(source/'cli')],'exit_code':0,'output':'cli-frozen-tests.log'},
    {'command':['/usr/bin/swift','test','--package-path',str(source/'native/android/engine')],'exit_code':0,'output':'engine-frozen-tests.log'},
    {'command':['/usr/bin/swift','test','--package-path',str(OUT/'.local/harness')],'exit_code':1,'output':'runtime-probe-attempt-1.log','scope':'Retained harness decoder mistake; source attempts/RuntimeProbe.attempt1.swift'},
    {'command':['/usr/bin/swift','test','--package-path',str(OUT/'.local/harness')],'exit_code':0,'output':'runtime-probe-attempt-2.log'},
    {'command':['/usr/bin/swift','test','--package-path',str(OUT/'.local/source-repair/cli')],'exit_code':0,'output':'cli-repaired-frozen-tests.log'},
    {'command':['python3',str(OUT/'driver_probe.py')],'exit_code':0,'output':'driver-probe-run.log','scope':'Recorded original negative cases and confirmed staging finding'},
    {'command':['python3',str(OUT/'staging_leaf_probe.py'),'original',str(source/'cli/Sources/MixerBuild/Resources/android-build.py')],'exit_code':0,'output':'staging-leaf-original-run.log'},
    {'command':['python3',str(OUT/'staging_fix_replay.py')],'exit_code':0,'output':'staging-fix-replay-run.log'},
    {'command':['python3',str(OUT/'.local/source-repair/cli/build-tests/test_android_staging.py')],'exit_code':0,'output':'staging-regressions-normal.log'},
    {'command':['python3','-O',str(OUT/'.local/source-repair/cli/build-tests/test_android_staging.py')],'exit_code':0,'output':'staging-regressions-optimized.log'},
    {'command':['python3',str(OUT/'consumer_probe.py')],'exit_code':0,'output':'consumer-probe-run.log'},
    {'command':['python3',str(OUT/'source_and_tool_probe.py')],'exit_code':0,'output':'source-and-tool-probe-run.log'},
    {'command':['python3',str(OUT/'audit_artifact.py')],'exit_code':0,'output':'artifact-audit-run.log'},
    {'command':['python3',str(OUT/'audit_final_artifact.py')],'exit_code':0,'output':'final-artifact-audit-run.log'},
]
for command in commands:command['output_sha256']=sha(OUT/command['output'])
files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and '.local' not in p.relative_to(OUT).parts and '__pycache__' not in p.relative_to(OUT).parts and p.name not in {'receipt.json','review-evidence.sha256'}]
manifest=''.join(sha(path)+'  '+path.relative_to(OUT).as_posix()+'\n' for path in files)
(OUT/'review-evidence.sha256').write_text(manifest)
receipt={
    'schema':1,'status':'passed scoped independent local Android generator review after repaired staging containment',
    'reviewed_source_revision':final['revision'],'initial_source_revision':json.loads((OUT/'freeze.json').read_text())['revision'],
    'source_snapshots_unchanged_after_execution':True,
    'source_freezes':{name:json.loads((OUT/name).read_text()) for name in ['freeze.json','freeze-repair.json']},
    'tools':json.loads((OUT/'review-tools.json').read_text()),'commands':commands,
    'test_results':{'frozen_cli_initial':19,'frozen_cli_repaired':19,'frozen_reusable_runtime':3,'frozen_existing_engine':5,'independent_runtime':6,'independent_generated_shared_host':4,'independent_generated_actual_C_ABI':1,'permanent_staging_normal':9,'permanent_staging_optimized':9,'independent_staging_fix_cases':9,'final_pinned_official_artifact_commands':22},
    'finding':{'priority':'P1','title':'Staging links could mutate files outside project output before rejected build','original_reproductions':['.mixer directory symlink','android-build directory symlink','build-input.json.tmp file symlink','build-input.json.tmp hardlink'],'fixed_revision':final['revision'],'state':'resolved','replay':'staging-fix-replay.json'},
    'final_artifact_audit':'final-artifact-audit.json','final_artifact':next(check for check in final['checks'] if check['name']=='actual-fixed-driver-rebuilt-apk'),
    'review_evidence_manifest':'review-evidence.sha256','review_evidence_manifest_sha256':hashlib.sha256(manifest.encode()).hexdigest(),'review_evidence_files':len(files),
    'scope':'Independent frozen source generation/runtime/negative probes and actual unsigned APK evidence/tool audit. Real cross-build and cached rebuild were audited; duplicate full cross-build not run.',
    'limitations':['Trusted value-state callbacks are synchronous, non-reentrant and free of external effects; Sendable does not isolate reference graphs','Local staging preflight and before/after source observations are not concurrent same-user filesystem isolation or arbitrary package-code sandboxing'],
    'pending':['physical iOS/Android (phones disconnected)','production signing/installability','native resources/capabilities','persistence/process restoration/navigation','device UI/IME/accessibility/performance','independent clean CI APK builds','published immutable separate-repository packages','external FieldLog D2','store acceptance','GA'],
    'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'source':receipt['reviewed_source_revision'],'evidence_files':len(files),'final_apk':receipt['final_artifact']},indent=2))
