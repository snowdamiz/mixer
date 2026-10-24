#!/usr/bin/env python3
"""Read/hash all inherited contracts, imports, data, and tools without native queries."""
import datetime
import difflib
import hashlib
import json
import pathlib
import platform
import plistlib
import sys
BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE.parents[1]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
read=lambda path:json.loads(path.read_bytes())
def save(name,value):(BASE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
assert not (BASE/'packet-seal.json').exists()
bindings=dict(read(BASE/'source-composition.json')['originalInputs'])
for file in ['verification/apple-toggle-keyboard-focus-v9-preparation/input-bindings.json','verification/apple-toggle-keyboard-focus-v9-independent-review/review-inputs.json']:
    bindings.update(read(ROOT/file));bindings[file]=sha(ROOT/file)
for file in ['verification/apple-toggle-keyboard-focus-v9-preparation/packet-seal.json','verification/apple-toggle-keyboard-focus-v9-independent-review/review-seal.json','verification/apple-toggle-keyboard-focus-v9-preparation/execution-seal.json']:
    seal=read(ROOT/file);bindings.update({name:value['sha256'] if isinstance(value,dict) else value for name,value in seal['files'].items()});bindings[file]=sha(ROOT/file)
expected='d5209edf1f03c2282b73c0d2c08b2635bf310364896c7289fa6c88802d875ae3'
assert sha(ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/execution-seal.json')==expected
for file in ['verification/apple-toggle-keyboard-focus-v9-root-review/runtime-review.json','verification/apple-toggle-keyboard-focus-v9-preparation/fixtures.py','verification/apple-toggle-keyboard-focus/test_keyboard.py','verification/apple-toggle-keyboard-focus/test_adapters.py','verification/apple-toggle-native-failure-analysis/sdk26-comparator/built-app.tar.gz','verification/apple-toggle-native-failure-analysis/sdk26-comparator/built-app-manifest.json']:
    bindings[file]=sha(ROOT/file)
imports=read(BASE/'runtime-import-bindings.json')
bindings.update(imports['sourceFiles']);bindings.update(imports['dataFiles'])
# All snapshot copies carry the original source binding as well as their own hash.
for path in sorted((BASE/'inputs/runtime').rglob('*')):
    if not path.is_file():continue
    origin=ROOT/path.relative_to(BASE/'inputs/runtime')
    assert origin.is_file() and sha(path)==sha(origin),(path,origin)
    bindings[str(origin.relative_to(ROOT))]=sha(origin)
    bindings[str(path.relative_to(ROOT))]=sha(path)
runner=read(ROOT/'verification/apple-toggle-keyboard-focus-v7-preparation/build-products-manifest.json')
bindings.update(runner['toolFiles'])
xcode=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Info.plist');bindings[str(xcode)]=sha(xcode)
python=pathlib.Path(sys.executable).resolve();bindings[str(python)]=sha(python)
for name,expected_hash in bindings.items():
    path=pathlib.Path(name) if name.startswith('/') else ROOT/name
    assert path.is_file() and sha(path)==expected_hash,'Bound input changed: '+name
save('input-bindings.json',bindings)
info=plistlib.loads(xcode.read_bytes())
app=read(ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/built-app-manifest.json')
source={str(p.relative_to(BASE/'harness')):sha(p) for p in sorted((BASE/'harness').rglob('*')) if p.is_file()}
save('provenance.json',dict(schema=1,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=[sys.executable,'-B',str(BASE/'record_provenance.py')],cwd=str(ROOT),
    sourceRevisionContext='67d6d0455c64ccb454c2e06e11edbdca2836a1cd',sourceRevisionContextSource='Inherited V9 label; no Git query',
    python=sys.version,platform=platform.platform(),pythonExecutable=str(python),pythonExecutableSHA256=sha(python),
    XcodeVersionFromBundleMetadata=info.get('CFBundleShortVersionString'),XcodeBundleBuild=info.get('CFBundleVersion'),
    nativeToolCommandsExecuted=False,inputBindings=len(bindings),runtimeLoadedSources=len(imports['sourceFiles']),runtimeImportData=len(imports['dataFiles']),
    runnerSourceFiles=source,runnerSourceTreeSHA256=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
    appArchiveSHA256=app['archiveSHA256'],appSourceClosureSHA256='f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46',
    acceptedV9ExecutionSealSHA256='d5209edf1f03c2282b73c0d2c08b2635bf310364896c7289fa6c88802d875ae3',
    sourceSnapshotIsolation=True,readOnlyVerifyImportsRuntime=False,runnerCompiled=False,applicationCasesExecuted=0,nativeInstancesQueried=False,physicalPhones='disconnected-deferred',nativeAcceptancePending=True))
diff=''
for prior,name in [('apple-toggle-keyboard-focus/test_keyboard.py','test_keyboard.py'),('apple-toggle-keyboard-focus/test_adapters.py','test_adapters.py'),('apple-toggle-keyboard-focus-v9-preparation/fixtures.py','fixtures.py')]:
    diff+=''.join(difflib.unified_diff((ROOT/'verification'/prior).read_text().splitlines(True),(BASE/name).read_text().splitlines(True),fromfile='verification/'+prior,tofile=str((BASE/name).relative_to(ROOT))))
(BASE/'host-control-adaptation.diff').write_text(diff)
print(json.dumps(dict(inputBindings=len(bindings),runnerCompiled=False,nativeInstancesQueried=False)))
