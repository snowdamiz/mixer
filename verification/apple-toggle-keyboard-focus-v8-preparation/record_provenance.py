#!/usr/bin/env python3
"""Bind exact selected packets and reused app/runner source; host reads only."""
import datetime
import difflib
import json
import pathlib
import packet as p
b=p.BASE
p.require(not (b/'packet-seal.json').exists(),'Sealed V8 packet is immutable')
exact={}
old=p.V7
for folder in ['source','harness']:
    for path in sorted((b/folder).rglob('*')):
        if path.is_file():
            exact[str(path.relative_to(p.ROOT))]=str((old/path.relative_to(b)).relative_to(p.ROOT))
for name in ['keyboard_oracle.py','built-app-manifest.json','built-app.tar.gz','source-lock.json','build-products-manifest.json','swift-public-witness.json']:
    exact[str((b/name).relative_to(p.ROOT))]=str((old/name).relative_to(p.ROOT))
for name,source in exact.items():p.require(p.sha(p.ROOT/name)==p.sha(p.ROOT/source),'Unchanged source differs: '+name)
reuse=dict(schema='mixer.apple-toggle.keyboard-v8-immutable-reuse.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exactCopies=exact,
           runnerProductTreePath=str((old/'build/Build/Products').relative_to(p.ROOT)),runnerArchivePath=str((old/'test-runner-products.tar.gz').relative_to(p.ROOT)),
           runnerRecompiled=False,appRecompiled=False,oracleChanged=False,sharedSwiftTransportChanged=False,nativeExecuted=False,nativeInstancesQueried=False)
(b/'immutable-reuse.json').write_text(json.dumps(reuse,indent=2,sort_keys=True)+'\n')
bindings=p.inputs()
bindings.update(p.read(old.parent/'apple-toggle-keyboard-focus-v7-independent-review/review-inputs.json'))
p.check_inputs(bindings)
(b/'input-bindings.json').write_text(json.dumps(bindings,indent=2,sort_keys=True)+'\n')
patch=''
for name in ['settings_telemetry.py','replay.py','run.py','fixtures.py']:
    patch+=''.join(difflib.unified_diff((old/name).read_text().splitlines(True),(b/name).read_text().splitlines(True),fromfile='v7/'+name,tofile='v8/'+name))
(b/'production-source-delta.diff').write_text(patch)
print(json.dumps(dict(exactCopies=len(exact),inputBindings=len(bindings),selectedInputs=p.PINS,runnerRecompiled=False,nativeExecuted=False)))
