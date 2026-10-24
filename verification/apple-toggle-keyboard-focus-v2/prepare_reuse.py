"""Bind exact app/runner/runtime reuse and the selected root-only v2 correction."""
import datetime
import json
import pathlib
import sys
import run
import keyboard_oracle as o
BASE,ROOT,OLD=run.BASE,run.ROOT,run.PREVIOUS
assert not (BASE/'packet-seal.json').exists(),'Sealed v2 preparation is immutable'
prior=run.read(OLD/'packet-seal.json');assert run.sha(OLD/'packet-seal.json')=='da6c8a03853d8fa3b3a0361030d063d841efe510eff8a6e8bc81ff36dc7e5378' and len(prior['files'])==81
assert all(run.sha(ROOT/n)==d for n,d in prior['files'].items()),'Original81sealed bytes changed'
paths=[p for folder in ['source','harness','official'] for p in sorted((BASE/folder).rglob('*')) if p.is_file()]
paths += [BASE/n for n in ['build.py','source-lock.json','selection.json','receipt.json','built-app-manifest.json','built-app.tar.gz','build-products-manifest.json','test-runner-products.tar.gz','cases.json','runner-build-attempt-1.json','runner-binary-receipt.json','binary-provenance-commands.json','immutable-app-reuse.json']]+list(BASE.glob('build-attempt-*.json'))
for p in paths:assert run.sha(p)==run.sha(OLD/p.relative_to(BASE)),'Copied app/runner/source differs'
runner=run.read(BASE/'build-products-manifest.json');assert run.runtime.inherited.tree(run.runtime.inherited.PRODUCTS)==runner['products'];run.runtime.inherited.product_archive_payload(runner)
selection=ROOT/'verification/apple-toggle-keyboard-focus-root-review/v2-repair-selection.json'
assert run.sha(selection)=='d3f709973ba6ba9d2e7dd58d88d2046293c2e87de08d737331c65d8fe63d9e61'
bindings={**prior['files'],str((OLD/'packet-seal.json').relative_to(ROOT)):run.sha(OLD/'packet-seal.json'),str(selection.relative_to(ROOT)):run.sha(selection)}
for n,d in run.read(selection)['bindings'].items():assert run.sha(ROOT/n)==d;bindings[n]=d
value={'schema':'mixer.apple-toggle.keyboard-v2-immutable-reuse.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve().relative_to(ROOT))],'pythonVersion':sys.version,
       'copiedFiles':{str(p.relative_to(ROOT)):run.sha(p) for p in sorted(set(paths))},'previousBindings':bindings,
       'previousSealedFilesPreserved':81,'sourceClosureSHA256':run.read(BASE/'source-lock.json')['sourceClosureSHA256'],
       'appArchiveSHA256':run.read(BASE/'built-app-manifest.json')['archiveSHA256'],'runnerProductTreeSHA256':runner['productTreeSHA256'],'runnerArchiveSHA256':runner['productArchiveSHA256'],
       'runtimeSource':str((OLD/'run.py').relative_to(ROOT)),'runtimeSourceSHA256':run.sha(OLD/'run.py'),
       'selectedChange':'Only v2 oracle/cursor wrapper and verifier path binding. Exact runtime, Settings gate, witnesses, command phases, attachment exporter, reader, lifecycle/cleanup, source and runner are reused.',
       'appOrCarrierChanged':False,'appOrRunnerRecompiled':False,'nativeExecuted':False,'nativeInstancesQueried':False,'physicalDevicesQueried':False}
(BASE/'immutable-reuse.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({k:v for k,v in value.items() if k not in ['copiedFiles','previousBindings','pythonVersion']},sort_keys=True))
