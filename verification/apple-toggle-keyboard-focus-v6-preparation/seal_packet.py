#!/usr/bin/env python3
"""Freeze the root-selected host-only V6 repair and byte-exact reused inputs."""
import datetime
import json
import pathlib
import run as r
b=r.BASE
assert not (b/'packet-seal.json').exists(),'Never overwrite sealed preparation'
selection=b.parent/'apple-toggle-keyboard-focus-v5-root-review/v6-repair-selection.json'
r.require(r.sha(selection)=='a687f64d09bc04df73842b3a45a4014551497a452cdf5092cd24ee60cbb9a3d7','V6 selection changed')
controls=r.read(b/'host-controls.json')
r.require(controls['allRequiredGroupsPassed'] and all(r.sha(r.ROOT/name)==digest for name,digest in controls['sourceFiles'].items()),'Final host proofs incomplete/changed')
reuse=r.read(b/'immutable-reuse.json')
r.require(all(r.sha(r.ROOT/name)==digest for group in ['copiedFiles','previousBindings'] for name,digest in reuse[group].items()),'Immutable inputs changed')
r.require(all(r.sha(r.ROOT/name)==r.sha(r.ROOT/source) for name,source in reuse['exactCopySources'].items()),'Exact reuse changed')
manifest=r.read(b/'build-products-manifest.json')
r.require(r.h.tree(r.h.PRODUCTS)==manifest['products'],'Product tree changed');r.h.product_archive_payload(manifest)
files={str(p.relative_to(r.ROOT)):r.sha(p) for p in sorted(b.rglob('*')) if p.is_file() and not p.is_symlink() and p.relative_to(b).parts[0] not in ['build','runtime','runtime-direct','__pycache__','.scratch']}
external=[r.ROOT/'docs/apple-toggle-keyboard-focus-v6-preparation.md',selection,r.V5/'packet-seal.json',b.parent/'apple-toggle-keyboard-focus-v5-independent-review/review-seal.json']+[r.ROOT/name for name in controls['sourceFiles']]+[r.ROOT/name for name in r.read(b/'fixed-stale-replay.json')['frozenFiles']]
for p in external:files[str(p.relative_to(r.ROOT))]=r.sha(p)
seal={'schema':'mixer.apple-toggle.keyboard-v6-diagnostic.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'sealed-host-only-ordering-repair-awaiting-independent-root-review','files':files,'excludedMutableSubtrees':[str(b.relative_to(r.ROOT))+'/runtime/',str(b.relative_to(r.ROOT))+'/runtime-direct/'],'rootSelectionSHA256':r.sha(selection),'v5IndependentReviewSHA256':'dbe9f176e1f32d418fb70592b976dcb3ff84789d10104d50816b720c54d7af6d','candidateSourceClosureSHA256':'f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46','candidateArchiveSHA256':'b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393','testRunnerSourceTreeSHA256':manifest['sourceTreeSHA256'],'testRunnerProductTreeSHA256':manifest['productTreeSHA256'],'testRunnerArchiveSHA256':manifest['productArchiveSHA256'],'sameRouteOrdering':'tap.finishedUptime <= route-opened.captureStartedUptime <= destination.observedUptime','focusedOrderingHostMethods':8,'boundaryContexts':{'preStartOverlapJustBeforeEqualAfterEachRoute':15,'wrongRouteTapAndOlderCompletionEachRoute':3,'HTTPStaleEachRoute':3,'offlineStaleEachRoute':3},'independentV5Methods':26,'independentV5MethodsUnchanged':25,'independentContractAdaptation':'Expect immediate transactional ValueError; retain no-setup assertion and compare accepted journal replay. No assertion relaxation.','priorRegressionMethods':[18,17,44,39,44,44,29],'historicalV5OrderingFinding':'Same failed CONTRACT assertion and three stale credited destinations retained on sealed V5; exact 32-record journal rejects in V6.','historicalV3Findings':'same3methods/5failure records','SwiftTransportHostChecks':[16,35],'expectedXCTestMethods':1,'applicationCasesUnrun':sorted(r.keyboard_oracle.CASES),'runnerRecompiled':False,'appOrOracleChanged':False,'nativeRunnerOrTransportChanged':False,'nativeExecuted':False,'nativeInstancesQueried':False,'boundsChanged':False,'nativeExecutionSelected':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False}
(b/'packet-seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
print(json.dumps({'sealSHA256':r.sha(b/'packet-seal.json'),'sealedFiles':len(files),'hostControlsSHA256':r.sha(b/'host-controls.json'),'runnerProduct':manifest['productTreeSHA256'],'runnerArchive':manifest['productArchiveSHA256'],'nativeExecuted':False}))
