#!/usr/bin/env python3
"""Seal V9 source and observed host evidence; native selection stays false."""
import datetime
import json
import pathlib
import sys
import packet as p
b=p.BASE
p.require(not (b/'packet-seal.json').exists(),'Never replace a sealed packet')
controls=p.read(b/'host-controls.json');p.require(controls['passed'],'Host implementation controls failed')
p.require(all(p.sha(p.ROOT/name)==expected for name,expected in controls['sourceFiles'].items()),'Executed source changed')
p.check_inputs(p.read(b/'input-bindings.json'))
cleanup=p.read(b/'cleanup.json');archive=p.read(b/'host-evidence-manifest.json')
p.require(cleanup['ownedScratchAbsent'] and not (b/'.scratch').exists() and p.sha(b/'host-evidence.tar.gz')==cleanup['verifiedArchiveSHA256']==archive['archiveSHA256'],'Synthetic evidence/cleanup incomplete')
excluded={'packet-seal.json','seal.stdout','seal.stderr','host-preflight.stdout','host-preflight.stderr','host-preflight.json'}
files={str(path.relative_to(p.ROOT)):p.sha(path) for path in sorted(b.rglob('*')) if path.is_file() and not path.is_symlink() and path.name not in excluded and path.relative_to(b).parts[0] not in ['runtime','runtime-direct','__pycache__','.scratch']}
doc=p.ROOT/'docs/apple-toggle-keyboard-focus-v9-preparation.md';files[str(doc.relative_to(p.ROOT))]=p.sha(doc)
old=p.read(p.V8/'packet-seal.json')
result=dict(schema='mixer.apple-toggle.keyboard-v9-diagnostic.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='sealed-source-and-host-controls-awaiting-independent-root-review',command=[sys.executable,'-B',str(pathlib.Path(__file__).resolve())],pythonVersion=sys.version,pythonExecutableSHA256=p.sha(pathlib.Path(sys.executable).resolve()),files=files,fileCount=len(files),sourceRevisionContext=controls['sourceRevisionContext'],rootSelectionSHA256=p.PINS[str(p.SELECTION.relative_to(p.ROOT))],producerSealSHA256=p.PINS[str((p.V8/'packet-seal.json').relative_to(p.ROOT))],independentSealSHA256=p.PINS['verification/apple-toggle-keyboard-focus-v8-independent-review/review-seal.json'],inputBindings=len(p.read(b/'input-bindings.json')),candidateSourceClosureSHA256=old['candidateSourceClosureSHA256'],candidateArchiveSHA256=old['candidateArchiveSHA256'],testRunnerSourceTreeSHA256=old['testRunnerSourceTreeSHA256'],testRunnerProductTreeSHA256=old['testRunnerProductTreeSHA256'],testRunnerArchiveSHA256=old['testRunnerArchiveSHA256'],runnerRecompiled=False,appOrOracleChanged=False,sharedTransportChanged=False,boundsChanged=False,actualSessionMethods=controls['sessionMethods'],actualPersistenceMethods=controls['persistenceMethods'],concretePersistenceHTTPControls=controls['persistenceConcreteHTTPControls'],unchangedSwiftResolverControls=71,unchangedTransportControls=[16,35],nativeExecutionSelected=False,nativeExecuted=False,nativeInstancesQueried=False,applicationCasesExecuted=0,applicationCasesUnrun=old['applicationCasesUnrun'],physicalPhones='disconnected-deferred',nativeKeyboardQualification=False,carrierAccepted=False,gaAccepted=False,excludedMutableSubtrees=['runtime','runtime-direct'],hostPreflightOutputsOutsideSealToAvoidSelfReference=True)
(b/'packet-seal.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(sealSHA256=p.sha(b/'packet-seal.json'),sealedFiles=len(files),nativeExecutionSelected=False,actualSessionMethods=controls['sessionMethods'],actualPersistenceMethods=controls['persistenceMethods'],concretePersistenceHTTPControls=controls['persistenceConcreteHTTPControls'])))
