#!/usr/bin/env python3
"""Seal selected V5 source/host/crossbuild evidence; never run native tests."""
import datetime
import json
import pathlib
import run as r
b = r.BASE
assert not (b/'packet-seal.json').exists(), 'Never overwrite a sealed packet'
selection=b.parent/'apple-toggle-keyboard-focus-v4-root-review/v5-preparation-selection.json'
r.require(r.sha(selection)=='d9849baa4dadc9285e5b95f1ec35ff560d9926aec6d66e2d9f9e01e98b1cd8ca','V5 root selection changed')
controls=r.read(b/'host-controls.json')
r.require(controls['allRequiredGroupsPassed'] is True and all(r.sha(r.ROOT/name)==digest for name,digest in controls['sourceFiles'].items()),'Final V5 controls incomplete/changed')
manifest=r.read(b/'build-products-manifest.json');r.require(r.h.tree(r.h.PRODUCTS)==manifest['products'],'Runner products changed');r.h.product_archive_payload(manifest)
r.require(all(r.sha(r.ROOT/name)==digest for name,digest in manifest['sourceFiles'].items()),'Built runner sources changed')
reuse=r.read(b/'immutable-reuse.json');r.require(all(r.sha(r.ROOT/name)==digest for group in ['copiedFiles','previousBindings'] for name,digest in reuse[group].items()),'App/oracle/prior selection changed')
files={str(p.relative_to(r.ROOT)):r.sha(p) for p in sorted(b.rglob('*')) if p.is_file() and not p.is_symlink() and p.relative_to(b).parts[0] not in ['build','runtime','runtime-direct','__pycache__','.scratch']}
external=[r.ROOT/'docs/apple-toggle-keyboard-focus-v5-preparation.md',selection,r.V4/'packet-seal.json']+[r.ROOT/name for name in controls['sourceFiles'] if not pathlib.Path(name).is_absolute()]
for p in external:files[str(p.relative_to(r.ROOT))]=r.sha(p)
seal={'schema':'mixer.apple-toggle.keyboard-v5-diagnostic.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'sealed-selected-source-host-crossbuild-awaiting-root-review','files':files,'excludedMutableSubtrees':['verification/apple-toggle-keyboard-focus-v5-preparation/runtime/','verification/apple-toggle-keyboard-focus-v5-preparation/runtime-direct/'],'rootSelectionSHA256':r.sha(selection),'candidateSourceClosureSHA256':'f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46','candidateArchiveSHA256':'b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393','testRunnerProductTreeSHA256':manifest['productTreeSHA256'],'testRunnerArchiveSHA256':manifest['productArchiveSHA256'],'focusedHostMethods':18,'adaptedIndependentMethods':17,'same44AssertionsV5':44,'legacyRegressionMethods':[39,44,44,29],'priorV3Findings':'same3methods/5failure records reproduced','expectedXCTestMethods':1,'applicationCasesUnrun':sorted(r.keyboard_oracle.CASES),'sharedSwiftTransportSourceSHA256':controls['sharedSwiftTransportSourceSHA256'],'runnerCrosscompiled':True,'appOrOracleChanged':False,'nativeExecuted':False,'nativeInstancesQueried':False,'rejectedBodyQuarantine':False,'boundsChanged':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False}
(b/'packet-seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
print(json.dumps({'sealSHA256':r.sha(b/'packet-seal.json'),'sealedFiles':len(files),'runnerProduct':manifest['productTreeSHA256'],'runnerArchive':manifest['productArchiveSHA256'],'nativeExecuted':False}))
