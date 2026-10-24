"""Seal the separate v2 host harness; immutable app/runner provenance is reused."""
import datetime
import json
import pathlib
import run

BASE,ROOT=run.BASE,run.ROOT
path=BASE/'packet-seal.json';assert not path.exists(),'Archive a rejected sealed v2 attempt before editing'
lock=run.read(BASE/'source-lock.json');app=run.read(BASE/'built-app-manifest.json');runner=run.read(BASE/'build-products-manifest.json')
assert lock['sourceClosureSHA256']=='f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46'
assert app['archiveSHA256']=='b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393'
assert runner['productTreeSHA256']=='741d8adef8bcd17d60819cb25f4caa4a9883620e090e62c06bd2f2f32cd897e9'
controls=run.read(BASE/'host-controls.json');assert controls['exitCode']==0 and controls['testsRun']==37
replay=run.read(BASE/'offline-replay.json');assert replay['status']=='DIAGNOSTIC_ONLY' and len(replay['cases'])==16 and replay['diagnosticPredicatesSatisfied']==16
reuse=run.read(BASE/'immutable-reuse.json');assert run.prior_tree(BASE.parent/'apple-toggle-pan-commit')==run.read(BASE/'prior-packet-tree.json')['entries']
files=[]
for p in sorted(BASE.rglob('*')):
    parts=p.relative_to(BASE).parts
    if parts[0] in {'build','runtime','runtime-direct','__pycache__'} or '__pycache__' in parts:continue
    if p.is_file():assert not p.is_symlink();files.append(p)
files += [ROOT/'docs/apple-toggle-pan-commit-contract.md',ROOT/'docs/apple-toggle-pan-commit-harness-v2.md',
          ROOT/'verification/apple-toggle-pan-commit/packet-seal.json',ROOT/reuse['failedRuntimeReview']]
value={'schema':'mixer.apple-toggle.pan-commit-harness-v2.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'status':'sealed-host-harness-correction-awaiting-root-review-and-fresh-native-run',
       'candidateSourceClosureSHA256':lock['sourceClosureSHA256'],'candidateArchiveSHA256':app['archiveSHA256'],
       'testRunnerProductTreeSHA256':runner['productTreeSHA256'],'testRunnerArchiveSHA256':runner['productArchiveSHA256'],
       'priorFailedPacketSealSHA256':reuse['priorPacketSealSHA256'],'priorEntirePacketTreeSHA256':reuse['priorEntirePacketTreeSHA256'],
       'files':{str(p.relative_to(ROOT)):run.sha(p) for p in sorted(set(files))},
       'excludedMutableSubtrees':[str((BASE/'runtime').relative_to(ROOT))+'/',str((BASE/'runtime-direct').relative_to(ROOT))+'/'],
       'generatedBuildScope':'Exact prepared runner Products restored from identical prior archive. Intermediate compiler outputs are not qualification evidence.',
       'selectedCorrection':'Startup prefix uses strict shape/metadata with nonnegative layout; before/after/hooks/all new input events require attached positive finite scale and geometry. Stable canonical singlelink reader retries only superseded/missing snapshots.',
       'explicitAdapterExtension':'Dedicated-process Bridge subclass overrides observe for explicit absolute deadline and wait only to set/restore min(session,existing operation deadline) around inherited wait loop. Other parent methods/endpoints/commands/cleanup unchanged. Direct reads min(session,50ms),max4attempts,no sleeps/no deadline refresh.',
       'hostTestMethods':37,'offlineReplay':'DIAGNOSTIC_ONLY;16historical failed captures satisfy revised predicates; no retroactive pass',
       'appOrRunnerRecompiled':False,'nativeExecuted':False,'nativeInstancesQueried':False,'physicalDevicesQueried':False,
       'nativeQualification':False,'productionAppleAdapterAcceptance':False,'gaAccepted':False,
       'scope':'Fresh43method/45native-action plus one scoped36component suite still required. Original failed native attempt and failed19strict diagnostic checks remain retained.'}
with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps({'sealSHA256':run.sha(path),'sealedFiles':len(value['files']),'nativeExecuted':False}))
