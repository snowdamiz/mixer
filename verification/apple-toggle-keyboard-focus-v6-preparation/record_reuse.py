#!/usr/bin/env python3
"""Record byte-exact V5 reuse; no compiler, native instance or Git operation."""
import datetime
import difflib
import json
import sys
import run as r
b=r.BASE;old=r.V5
assert not (b/'packet-seal.json').exists(),'Sealed V6 is immutable'
selection=b.parent/'apple-toggle-keyboard-focus-v5-root-review/v6-repair-selection.json'
review=b.parent/'apple-toggle-keyboard-focus-v5-independent-review/review-seal.json'
expected={old/'packet-seal.json':'8626e01f8622b0a27176cb37331edd7076d50b566f61b5c52bc5d4b1703770aa',selection:'a687f64d09bc04df73842b3a45a4014551497a452cdf5092cd24ee60cbb9a3d7',review:'dbe9f176e1f32d418fb70592b976dcb3ff84789d10104d50816b720c54d7af6d'}
for p,digest in expected.items():r.require(r.sha(p)==digest,'Selected immutable seal changed')
for p in [old/'packet-seal.json',review]:
 for name,digest in r.read(p)['files'].items():r.require(r.sha(r.ROOT/name)==digest,'Immutable historical file changed: '+name)
copy_names=['built-app-manifest.json','built-app.tar.gz','source-lock.json','keyboard_oracle.py','build-products-manifest.json','runner-binary-receipt.json','runner-build-attempt-1.json','runner-build-attempt-2.json','binary-provenance-commands.json','test-runner-products.tar.gz','TransportControls.swift']
copy_paths=[b/name for name in copy_names]
for folder in ['source','harness','official','build/Build/Products']:
 copy_paths.extend(p for p in (b/folder).rglob('*') if p.is_file())
copy_paths.append(b/'host-tools/transport-controls')
exact={str(p.relative_to(r.ROOT)):str((old/p.relative_to(b)).relative_to(r.ROOT)) for p in sorted(copy_paths)}
exact[str((b/'TransportAdversarial.swift').relative_to(r.ROOT))]='verification/apple-toggle-keyboard-focus-v5-independent-review/TransportAdversarial.swift'
exact[str((b/'host-tools/transport-adversarial').relative_to(r.ROOT))]='verification/apple-toggle-keyboard-focus-v5-independent-review/transport-adversarial'
for name,source in exact.items():r.require(r.sha(r.ROOT/name)==r.sha(r.ROOT/source),'Reuse differs: '+name)
manifest=r.read(b/'build-products-manifest.json')
r.require(r.h.tree(r.h.PRODUCTS)==manifest['products'],'Copied runner modes/contents changed');r.h.product_archive_payload(manifest)
r.require(r.sha(b/'test-runner-products.tar.gz')==manifest['productArchiveSHA256']=='40365412907c311d421ce94d63e147b67a55b0543d5b6ba6f56211497dbea479','Runner archive changed')
r.require(r.sha(b/'built-app.tar.gz')=='b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393','App archive changed')
value={'schema':'mixer.apple-toggle.keyboard-v6-exact-reuse.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'appRecompiled':False,'runnerRecompiled':False,'transportRecompiled':False,'copiedFiles':{name:r.sha(r.ROOT/name) for name in exact},'exactCopySources':exact,'previousBindings':{str(p.relative_to(r.ROOT)):digest for p,digest in expected.items()},'runnerSourceTreeSHA256':manifest['sourceTreeSHA256'],'runnerSourceHashPathContext':'Exact unchanged V5 sourceFiles mapping; corresponding V6 files separately compared byte-for-byte. No new build is claimed.','runnerProductTreeSHA256':manifest['productTreeSHA256'],'runnerArchiveSHA256':manifest['productArchiveSHA256'],'sharedSwiftTransportSourceSHA256':r.sha(b/'harness/UITests/DiagnosticTransport.swift'),'strictV2OracleSHA256':r.sha(b/'keyboard_oracle.py'),'previousOfficialBinaryReceipt':str((b/'runner-binary-receipt.json').relative_to(r.ROOT)),'officialToolFilesCurrentlyIdentical':all(r.sha(__import__('pathlib').Path(p))==d for p,d in manifest['toolFiles'].items()),'command':[sys.executable,'-B',str(__import__('pathlib').Path(__file__).resolve().relative_to(r.ROOT))],'nativeExecuted':False,'nativeInstancesQueried':False,'compiled':False}
r.require(value['officialToolFilesCurrentlyIdentical'],'Official tools drifted')
(b/'immutable-reuse.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
patch=''
for name in ['settings_telemetry.py','run.py','replay.py']:
 patch+=''.join(difflib.unified_diff((old/name).read_text().splitlines(True),(b/name).read_text().splitlines(True),fromfile='v5/'+name,tofile='v6/'+name))
(b/'production-source-delta.diff').write_text(patch)
source=review.parent/'test_review.py'
(b/'independent26-adaptation.diff').write_text(''.join(difflib.unified_diff(source.read_text().splitlines(True),(b/'test_v5_independent26.py').read_text().splitlines(True),fromfile='sealed-v5-review/test_review.py',tofile='v6/test_v5_independent26.py')))
print(json.dumps({'exactCopies':len(exact),'runnerSource':manifest['sourceTreeSHA256'],'runnerProduct':manifest['productTreeSHA256'],'runnerArchive':manifest['productArchiveSHA256'],'compiled':False,'nativeExecuted':False}))
