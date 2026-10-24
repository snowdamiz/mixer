#!/usr/bin/env python3
"""Bind official APIs/tools/binaries and exact historical input closure."""
import datetime
import difflib
import hashlib
import json
import pathlib
import shutil
import sys
import run as r
b=r.BASE;old=r.V6
r.require(not (b/'packet-seal.json').exists(),'Never change sealed preparation')
exact={}
for name in ['keyboard_oracle.py','harness/UITests/DiagnosticTransport.swift','built-app-manifest.json','built-app.tar.gz','source-lock.json']:
 exact[str((b/name).relative_to(r.ROOT))]=str((old/name).relative_to(r.ROOT))
for p in (b/'source').rglob('*'):
 if p.is_file():exact[str(p.relative_to(r.ROOT))]=str((old/p.relative_to(b)).relative_to(r.ROOT))
for name,source in exact.items():r.require(r.sha(r.ROOT/name)==r.sha(r.ROOT/source),'Immutable copy changed: '+name)
analysis=b.parent/'apple-toggle-keyboard-focus-v6-analysis';seal=r.read(analysis/'analysis-seal.json');inputs=r.read(analysis/'review-inputs.json')
r.require(r.sha(analysis/'analysis-seal.json')=='3fe5b5cb0639e709a21b32f7785e929895f428ed0a4597536574a9b17eddedc3' and len(seal['files'])==17 and len(inputs)==660,'Selected analysis changed')
historical={str((analysis/'analysis-seal.json').relative_to(r.ROOT)):r.sha(analysis/'analysis-seal.json')}
for name,digest in seal['files'].items():historical[name]=digest
for name,v in inputs.items():historical[name]=v['sha256']
for packet in [old/'packet-seal.json',old.parent/'apple-toggle-keyboard-focus-v6-independent-review/review-seal.json']:
 historical[str(packet.relative_to(r.ROOT))]=r.sha(packet)
 historical.update(r.read(packet)['files'])
selection=b.parent/'apple-toggle-keyboard-focus-v6-root-review/v7-preparation-selection.json'
r.require(r.sha(selection)=='a56b15d641c3dd71fcb7e3472b19c5b8156736091c9fea905c07f6ba1ea8b6da','Root selection changed')
historical[str(selection.relative_to(r.ROOT))]=r.sha(selection)
for name,digest in historical.items():
 p=pathlib.Path(name) if name.startswith('/') else r.ROOT/name
 r.require(p.is_file() and not p.is_symlink() and r.sha(p)==digest,'Historical binding changed: '+name)
reuse=dict(schema='mixer.apple-toggle.keyboard-v7-immutable-reuse.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exactCopySources=exact,copiedFiles={name:r.sha(r.ROOT/name) for name in exact},historicalBindings=historical,selectedAnalysisFilesVerified=17,selectedExactInputsVerified=660,appRecompiled=False,oracleChanged=False,sharedSwiftTransportChanged=False,runnerRecompiled=True,nativeExecuted=False,nativeInstancesQueried=False)
r.h.write(b/'immutable-reuse.json',reuse)
headers=b/'official';headers.mkdir(exist_ok=True)
base=r.h.DEVELOPER/'Platforms/iPhoneSimulator.platform/Developer/Library/Frameworks/XCUIAutomation.framework/Headers'
entries=[]
for name in ['XCUIElement.h','XCUIElementAttributes.h','XCUIElementQuery.h','XCUIElementTypes.h','XCUIApplication.h','XCUICoordinate.h']:
 source=base/name;dest=headers/name;dest.write_bytes(source.read_bytes());entries.append(dict(source=str(source),snapshot=name,sha256=r.sha(source),bytes=source.stat().st_size))
r.h.write(headers/'manifest.json',dict(schema='mixer.apple-toggle.keyboard-v7-official-public-query-and-coordinate-apis.1',installedOfficialHeaders=entries,selectedPublicAPIs=['matching(NSPredicate exact identifier and label)','query.count and element(boundBy:)','children(matching: .switch)','descendants(matching: .switch)','public element properties and application.frame','leaf.coordinate(withNormalizedOffset: CGVector(dx:0.5,dy:0.5)).tap()'],debugDescription='Diagnostic upload only; never parsed to select or authorize input'))
commands=r.h.Commands(b/'binary-provenance-commands.json');manifest=r.read(b/'build-products-manifest.json');binaries={}
for relative in ['Debug-iphonesimulator/MixerToggleUITests-Runner.app/MixerToggleUITests-Runner','Debug-iphonesimulator/MixerToggleUITests-Runner.app/PlugIns/MixerToggleUITests.xctest/MixerToggleUITests']:
 path=r.h.PRODUCTS/relative
 v=commands.run(['/usr/bin/xcrun','vtool','-show-build',str(path)])[1];arch=commands.run(['/usr/bin/xcrun','lipo','-info',str(path)])[1]
 r.require('IOSSIMULATOR' in v and 'arm64' in arch,'Wrong runner binary platform')
 binaries[relative]=dict(sha256=r.sha(path),bytes=path.stat().st_size,vtool=v,lipo=arch)
r.h.write(b/'runner-binary-receipt.json',dict(schema='mixer.apple-toggle.keyboard-v7-fresh-runner-binary.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceRevisionContext=manifest['sourceRevisionContext'],sourceFiles=manifest['sourceFiles'],sourceTreeSHA256=manifest['sourceTreeSHA256'],productTreeSHA256=manifest['productTreeSHA256'],productArchiveSHA256=manifest['productArchiveSHA256'],binaries=binaries,buildCommands='runner-build-attempt-1.json',binaryCommands='binary-provenance-commands.json',appRecompiled=False,sharedTransportBytesExact=True,nativeExecuted=False))
patch=''
for name in ['settings_telemetry.py','run.py','replay.py','harness/UITests/ToggleUITests.swift','harness/MixerToggleUITests.xcodeproj/project.pbxproj']:
 patch+=''.join(difflib.unified_diff((old/name).read_text().splitlines(True),(b/name).read_text().splitlines(True),fromfile='v6/'+name,tofile='v7/'+name))
(b/'production-source-delta.diff').write_text(patch)
print(json.dumps(dict(exactCopies=len(exact),historicalBindings=len(historical),analysisFiles=17,exactInputs=660,runnerSource=manifest['sourceTreeSHA256'],runnerProduct=manifest['productTreeSHA256'],runnerArchive=manifest['productArchiveSHA256'],nativeExecuted=False)))
