"""Seal build-only preparation once. A sealed attempt must be archived before edits."""
import datetime
import json
import pathlib
import run

BASE,ROOT=run.BASE,run.ROOT
path=BASE/'packet-seal.json'
assert not path.exists(),'Sealed preparation is immutable; archive its rejected attempt first'
lock=run.read(BASE/'source-lock.json');app=run.read(BASE/'built-app-manifest.json');runner=run.read(BASE/'build-products-manifest.json')
assert lock['sourceClosureSHA256']=='f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46'
assert app['archiveSHA256']=='b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393'
controls=run.read(BASE/'host-controls.json');assert controls['exitCode']==0 and controls['testsRun']==10
files=[]
for p in sorted(BASE.rglob('*')):
    relative=p.relative_to(BASE)
    if relative.parts[0] in {'build','runtime','runtime-direct','__pycache__'} or '__pycache__' in relative.parts:continue
    if p.is_file():
        assert not p.is_symlink(),'No symlinks in sealed packet'
        files.append(p)
files += [ROOT/'docs/apple-toggle-pan-commit-contract.md',ROOT/'docs/apple-toggle-pan-commit-qualification.md',
          ROOT/'verification/apple-toggle-native-interruption/packet-seal.json',ROOT/'verification/apple-toggle-semantic-activation/packet-seal.json',
          ROOT/'verification/apple-toggle-pan-origin-correction/packet-seal.json']
value={'schema':'mixer.apple-toggle.pan-commit.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'status':'sealed-preparation-awaiting-root-review-and-native-execution',
       'sourceRevisionContext':run.read(BASE/'selection.json')['baseRevision'],
       'candidateSourceClosureSHA256':lock['sourceClosureSHA256'],'candidateArchiveSHA256':app['archiveSHA256'],
       'testRunnerProductTreeSHA256':runner['productTreeSHA256'],'testRunnerArchiveSHA256':runner['productArchiveSHA256'],
       'files':{str(p.relative_to(ROOT)):run.sha(p) for p in sorted(set(files))},
       'excludedMutableSubtrees':[str((BASE/'runtime').relative_to(ROOT))+'/',str((BASE/'runtime-direct').relative_to(ROOT))+'/'],
       'unsealedGeneratedBuildScope':'App/archive byte manifests and runner Products/archive are verified separately. Intermediate compiler caches are not acceptance evidence.',
       'hostControls':'10test methods;16synthetic pan positives;317negative evidence/type/order controls; unchanged13original action and16interruption oracle replays; separate36semantic rows and summary separation controls.',
       'nativeExecuted':False,'nativeInstancesQueried':False,'simulatorCreated':False,'physicalDevicesQueried':False,
       'nativeQualification':False,'productionAppleAdapterAcceptance':False,'gaAccepted':False,
       'scope':'43publicXCTest methods:45native input actions plus one scoped36direct-component result. Original19strict diagnostic suite remains failed with four raw reference failures.'}
with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps({'sealSHA256':run.sha(path),'sealedFiles':len(value['files']),'nativeExecuted':False}))
