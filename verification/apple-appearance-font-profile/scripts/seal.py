#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def entries():return [dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='receipt.json' and not any(x in ['build','__pycache__','xcuserdata'] for x in p.relative_to(ROOT).parts)]
def digest(entries):return hashlib.sha256(json.dumps(entries,sort_keys=True,separators=(',',':')).encode()).hexdigest()
with (ROOT/'logs/seal-verification.log').open('w') as out:r=subprocess.run([sys.executable,str(ROOT/'scripts/verify.py')],stdout=out,stderr=subprocess.STDOUT,cwd=ROOT)
assert r.returncode==0,(ROOT/'logs/seal-verification.log').read_text()
lock=json.loads((ROOT/'input-lock.json').read_text());files=entries();doc=ROOT.parents[1]/'docs/apple-appearance-font-profile.md'
result=json.loads((ROOT/'verification-result.json').read_text())
receipt=dict(format='mixer.apple-font-profile-receipt.1',status='native type-table and scoped contextual candidate measurements; shared recipe/root/Android/physical qualification pending',
 sealedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),baselineRevision=lock['baselineRevision'],baselineTree=lock['baselineTree'],priorMeasurementReceiptSHA256=lock['measurementReceiptSHA256'],priorMeasurementCollectionSHA256=lock['measurementCollectionSHA256'],
 checkoutRevision=(ROOT/'logs/git-revision.log').read_text().strip(),checkoutTree=(ROOT/'logs/git-tree.log').read_text().strip(),
 buildAndCaptureSourceCollectionSHA256=json.loads((ROOT/'capture-source-lock.json').read_text())['sourceCollectionSHA256'],postprocessSourceCollectionSHA256=json.loads((ROOT/'source-lock.json').read_text())['sourceCollectionSHA256'],
 simulator=json.loads((ROOT/'simulator.json').read_text()),tools=dict(xcode=(ROOT/'logs/xcode-version.log').read_text().strip(),swift=(ROOT/'logs/swift-version.log').read_text().strip(),simulatorSDK=(ROOT/'logs/sdk-version.log').read_text().strip()),
 scope=dict(profileCount=12,nativePreferenceExports=24,nativeOneTwoLineRolePairs=96,nativePNGs=18,nonperturbationComparisons=3,candidateComparisons=15,candidateMatches=result['candidateMatches'],
  fullTableEnvironment='typography fixture, light/LTR/en_US,12 Dynamic Type sizes, D/R',candidateMatrix='12 Debug cases across original fixtures and LTR accessibility additions;3 representative Release repeats',
  actualFontData='public Font.resolve/CoreText values, public actual expanded-title UIFont/lineHeight, hidden native SwiftUI one/two-line layout heights',
  candidate='Only public header.headline / Button.body / Toggle.body font modifiers in isolated renderer'),
 physicalDevices=dict(discovered=False,used=False,reconnectionRequested=False),productAndSchemaEdits=False,priorEvidenceModified=False,
 normalizationPolicy='Proposed12 immutable shared profiles; exact Apple preference mapping observed; Android body-anchor conversion and nearest-profile policy documented but not natively verified',
 pending=['Contextual font matching outside measured sizes/states/fixtures/locales/OS versions','Android native preference conversion, glyph/font matching and adapter implementation','Bold Text and other accessibility/contrast environment settings','Physical iOS/Android side-by-side design parity and native behavior/a11y/input','Signed display/health, immutable published FieldLog, signing/store/customer/operational/GA'],
 dependencies='Owned frozen SDK and Python standard library plus official Apple tools/frameworks; official Android documentation consulted; no third-party package added',
 ownership='Only verification/apple-appearance-font-profile/** and docs/apple-appearance-font-profile.md; no commits/pushes/tracker edits',
 externalDocument=dict(path='docs/apple-appearance-font-profile.md',bytes=doc.stat().st_size,sha256=hashlib.sha256(doc.read_bytes()).hexdigest()),
 artifactCollectionRule='SHA-256 of compact sorted-key JSON artifacts array; excludes receipt and ignored build/__pycache__/xcuserdata',artifactCollectionSHA256=digest(files),artifacts=files)
(ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(f'Sealed {len(files)} artifacts: {receipt["artifactCollectionSHA256"]}')
