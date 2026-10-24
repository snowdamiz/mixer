#!/usr/bin/env python3
"""Freeze selected V7 implementation and build evidence for independent review."""
import datetime
import hashlib
import json
import pathlib
import run as r
b=r.BASE
r.require(not (b/'packet-seal.json').exists(),'Never replace a sealed packet')
controls=r.read(b/'host-controls.json');r.require(controls['allRequiredGroupsPassed'],'Actual controls failed')
r.require(all(r.sha(r.ROOT/name)==digest for name,digest in controls['sourceFiles'].items()),'Actual control sources changed')
reuse=r.read(b/'immutable-reuse.json')
r.require(all(r.sha(r.ROOT/name)==r.sha(r.ROOT/source)==reuse['copiedFiles'][name] for name,source in reuse['exactCopySources'].items()),'App/oracle/transport changed')
r.require(all(r.sha(r.ROOT/name)==digest for name,digest in reuse['historicalBindings'].items()),'Historical packet changed')
runner=r.read(b/'build-products-manifest.json');r.require(r.h.tree(r.h.PRODUCTS)==runner['products'],'Runner changed');r.h.product_archive_payload(runner)
r.require(all(r.sha(r.ROOT/name)==digest for name,digest in runner['sourceFiles'].items()),'Compiled source changed')
files={str(p.relative_to(r.ROOT)):r.sha(p) for p in sorted(b.rglob('*')) if p.is_file() and not p.is_symlink() and p.name not in ['seal.stdout','seal.stderr'] and p.relative_to(b).parts[0] not in ['build','runtime','runtime-direct','__pycache__','.scratch']}
doc=r.ROOT/'docs/apple-toggle-keyboard-focus-v7-preparation.md';files[str(doc.relative_to(r.ROOT))]=r.sha(doc)
selection=b.parent/'apple-toggle-keyboard-focus-v6-root-review/v7-preparation-selection.json';files[str(selection.relative_to(r.ROOT))]=r.sha(selection)
seal=dict(schema='mixer.apple-toggle.keyboard-v7-diagnostic.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='sealed-implementation-and-official-build-awaiting-independent-root-review',sourceRevisionContext=runner['sourceRevisionContext'],files=files,fileCount=len(files),excludedMutableSubtrees=[str(b.relative_to(r.ROOT))+'/runtime/',str(b.relative_to(r.ROOT))+'/runtime-direct/'],rootSelectionSHA256=r.sha(selection),analysisSealSHA256='3fe5b5cb0639e709a21b32f7785e929895f428ed0a4597536574a9b17eddedc3',selectedAnalysisFiles=17,selectedExactInputs=660,candidateSourceClosureSHA256=r.read(b/'source-lock.json')['sourceClosureSHA256'],candidateArchiveSHA256=r.read(b/'built-app-manifest.json')['archiveSHA256'],testRunnerSourceTreeSHA256=runner['sourceTreeSHA256'],testRunnerProductTreeSHA256=runner['productTreeSHA256'],testRunnerArchiveSHA256=runner['productArchiveSHA256'],actualSessionTestMethods=21,actualSwiftResolverControls=71,unchangedTransportControls=[16,35],reviewModel37CountedAsImplementationTests=False,runnerRecompiled=True,appOrOracleChanged=False,sharedTransportChanged=False,expectedXCTestMethods=1,applicationCasesExecuted=0,applicationCasesUnrun=sorted(r.keyboard_oracle.CASES),nativeExecutionSelected=False,nativeExecuted=False,nativeInstancesQueried=False,physicalPhones='disconnected-deferred',nativeKeyboardQualification=False,carrierAccepted=False,gaAccepted=False,boundsChanged=False)
r.h.write(b/'packet-seal.json',seal)
print(json.dumps(dict(sealSHA256=r.sha(b/'packet-seal.json'),sealedFiles=len(files),testRunnerSource=runner['sourceTreeSHA256'],testRunnerProduct=runner['productTreeSHA256'],testRunnerArchive=runner['productArchiveSHA256'],nativeExecutionSelected=False)))
