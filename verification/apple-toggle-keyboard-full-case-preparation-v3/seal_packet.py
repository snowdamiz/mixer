#!/usr/bin/env python3
"""Seal only the prepared source/host packet; no native authority is selected."""
import datetime
import hashlib
import json
import pathlib
import sys
BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE.parents[1]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert not (BASE/'packet-seal.json').exists(),'Existing seal is immutable'
assert not (BASE/'.scratch').exists(),'Owned scratch must first be archived/verified/removed'
controls=json.loads((BASE/'host-controls.json').read_bytes());assert controls['passed'] and controls['hostMethods']==69
for name,digest in controls['sourceFiles'].items():assert sha(ROOT/name)==digest,'Host source changed: '+name
for name,digest in json.loads((BASE/'input-bindings.json').read_bytes()).items():
    path=pathlib.Path(name) if name.startswith('/') else ROOT/name
    assert path.is_file() and sha(path)==digest,'Bound input changed: '+name
files={}
for path in sorted(BASE.rglob('*')):
    assert not path.is_symlink(),'Packet symlinks are not permitted'
    if path.is_file():files[str(path.relative_to(ROOT))]=sha(path)
doc=ROOT/'docs/apple-toggle-keyboard-full-case-preparation-v3.md';files[str(doc.relative_to(ROOT))]=sha(doc)
seal=dict(schema='mixer.apple-toggle.keyboard-full-case-preparation-v3.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 command=[sys.executable,'-B',str(BASE/'seal_packet.py')],python=sys.version,files=files,
 sourceRevisionContext='67d6d0455c64ccb454c2e06e11edbdca2836a1cd',sourceRevisionContextMeaning='Inherited V9 label only; no Git query',
 runtimeImportSourceFiles=21,runtimeImportDataFiles=4,inputBindings=len(json.loads((BASE/'input-bindings.json').read_bytes())),hostMethods=69,selectedRuntimeSourceFiles=22,selectedRuntimeDataFiles=3,
 runnerSourceTreeSHA256=json.loads((BASE/'provenance.json').read_bytes())['runnerSourceTreeSHA256'],
 applicationCasesExecuted=0,nativeAcceptancePending=True,nativeInstancesQueried=False,nativeCompiled=False,nativeExecuted=False,
 physicalPhones='disconnected-deferred',nativeKeyboardQualification=False,carrierAccepted=False,gaAccepted=False,
 futureCompileAndRunSelected=False)
(BASE/'packet-seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(sealSHA256=sha(BASE/'packet-seal.json'),files=len(files),hostMethods=69,nativeCompiled=False,nativeExecuted=False)))
