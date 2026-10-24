"""Bind byte-identical prepared app/runner reuse; never compiles or calls native tools."""
import datetime
import json
import pathlib
import sys
import run

BASE,ROOT=run.BASE,run.ROOT
OLD=BASE.parent/'apple-toggle-pan-commit'
assert not (BASE/'packet-seal.json').exists(),'Sealed preparation is immutable'
prior=run.read(BASE/'prior-packet-tree.json')
assert run.prior_tree(OLD)==prior['entries'],'Original failed packet/runtime changed'
assert run.sha(OLD/'packet-seal.json')=='606068bea3eb3bc3c82655920d1d30c111c0e3196e39162d591abbee330abdf2'
paths=[p for folder in ['source','harness'] for p in sorted((BASE/folder).rglob('*')) if p.is_file()]
paths += [BASE/name for name in ['build.py','source-lock.json','selection.json','receipt.json','built-app-manifest.json','built-app.tar.gz','build-products-manifest.json','test-runner-products.tar.gz','cases.json','runner-build-attempt-1.json']]
paths += list(BASE.glob('build-attempt-*.json'))
for path in paths:assert run.sha(path)==run.sha(OLD/path.relative_to(BASE)),'Copied bytes differ: '+str(path)
lock=run.read(BASE/'source-lock.json');app=run.read(BASE/'built-app-manifest.json');runner=run.read(BASE/'build-products-manifest.json')
assert lock['sourceClosureSHA256']=='f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46'
assert app['archiveSHA256']=='b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393'
assert runner['productTreeSHA256']=='741d8adef8bcd17d60819cb25f4caa4a9883620e090e62c06bd2f2f32cd897e9'
assert runner['productArchiveSHA256']=='887efde5c9b7db432b3cd9dbac57878f333b80e2e196774c5c613c82f8461e34'
assert run.inherited.tree(run.inherited.PRODUCTS)==runner['products']
run.inherited.product_archive_payload(runner)
review=ROOT/'verification/apple-toggle-pan-commit-root-review/failed-runtime-review.json'
value={'schema':'mixer.apple-toggle.pan-commit-harness-v2-immutable-reuse.1',
       'command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve().relative_to(ROOT))],
       'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pythonVersion':sys.version,
       'priorPacketSealSHA256':run.sha(OLD/'packet-seal.json'),'priorEntirePacketTreeSHA256':prior['treeSHA256'],
       'priorPacketEntries':len(prior['entries']),'copiedFiles':{str(p.relative_to(ROOT)):run.sha(p) for p in sorted(paths)},
       'sourceClosureSHA256':lock['sourceClosureSHA256'],'appArchiveSHA256':app['archiveSHA256'],
       'runnerProductTreeSHA256':runner['productTreeSHA256'],'runnerArchiveSHA256':runner['productArchiveSHA256'],
       'runnerBuildProvenance':'Exact original manifest/source paths/tools/build-for-testing receipt reused; copied Swift/harness sources and prepared product bytes are identical. No new compile or native qualification.',
       'failedRuntimeReview':str(review.relative_to(ROOT)),'failedRuntimeReviewSHA256':run.sha(review),
       'nativeExecuted':False,'nativeInstancesQueried':False,'simulatorCreated':False,'physicalDevicesQueried':False,
       'originalFailedRuntimePreserved':True,'newNativeQualification':False}
(BASE/'immutable-reuse.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({k:v for k,v in value.items() if k not in ['copiedFiles','pythonVersion']},sort_keys=True))
