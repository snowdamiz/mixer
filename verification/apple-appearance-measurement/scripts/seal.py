#!/usr/bin/env python3
"""Seal retained measurement artifacts only, never authorize an app release."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def entries():
 return [dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(ROOT.rglob('*'))
  if p.is_file() and p.name!='receipt.json' and not any(part in ['build','__pycache__','xcuserdata'] for part in p.relative_to(ROOT).parts)]
def collection(files):return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
with (ROOT/'logs/seal-verification.log').open('w') as out:
 result=subprocess.run([sys.executable,str(ROOT/'scripts/verify.py')],stdout=out,stderr=subprocess.STDOUT,cwd=ROOT)
assert result.returncode==0,(ROOT/'logs/seal-verification.log').read_text()
inputs=json.loads((ROOT/'input-lock.json').read_text());source=json.loads((ROOT/'source-lock.json').read_text());files=entries()
doc=ROOT.parents[1]/'docs/apple-appearance-measurement.md'
receipt=dict(format='mixer.apple-appearance-measurement-receipt.1',status='simulator-measurement-and-integrity-verified; accountable-design-and-physical-parity-pending',
 sealedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),baselineRevision=inputs['baselineRevision'],baselineTree=inputs['baselineTree'],
 baselineReceiptSHA256=inputs['baselineReceiptSHA256'],baselineArtifactCollectionSHA256=inputs['baselineArtifactCollectionSHA256'],
 buildCheckoutRevision=(ROOT/'logs/git-revision.log').read_text().strip(),buildCheckoutTree=(ROOT/'logs/git-tree.log').read_text().strip(),
 sourceCollectionSHA256=source['sourceCollectionSHA256'],comparisonInputCollectionSHA256=json.loads((ROOT/'comparison-inputs.json').read_text())['sourceCollectionSHA256'],
 simulator=json.loads((ROOT/'simulator.json').read_text()),tools=dict(xcode=(ROOT/'logs/xcode-version.log').read_text().strip(),swift=(ROOT/'logs/swift-version.log').read_text().strip(),simulatorSDK=(ROOT/'logs/sdk-version.log').read_text().strip()),
 scope=dict(nativeScreenshots=24,debugReleaseProfiles=12,historicalPixelComparisons=16,historicalDifferentPixels=0,debugReleasePixelComparisons=12,debugReleaseDifferentPixels=0,debugReleaseNodeAndFontRecordsEqual=True,
  originalReferenceModified=False,productRendererOrThemeModified=False,themeApplied=False,publicAPIsOnly=True,agentVisualQA='12 Debug originals inspected; Release decoded pixels identical; accessibility LTR has offscreen rows'),
 physicalDevices=dict(discovered=False,used=False,reconnectionRequested=False),dependencies='Owned frozen SDK, Python standard library, official Apple toolchain/platform frameworks only; no general-purpose dependency added.',
 limitations=['Exact contextual section header/control label fonts and glyph fallback unresolved','Public UISwitch outer frame is not a track/thumb dimension','Group corner model and separator geometry unresolved','New LTR accessibility profiles lack historical uninstrumented controls; offscreen nodes not visual proof','No interaction/input/keyboard/accessibility or navigation transition run','No native shared-theme adapter implementation or physical iOS/Android comparison','No signed/display/health, published FieldLog, store/customer/operational/GA qualification'],
 ownership='Only verification/apple-appearance-measurement/** and docs/apple-appearance-measurement.md; no trackers, commits or pushes',
 externalDocument=dict(path='docs/apple-appearance-measurement.md',bytes=doc.stat().st_size,sha256=hashlib.sha256(doc.read_bytes()).hexdigest()),
 artifactCollectionRule='SHA-256 of compact sorted-key JSON artifacts array; excludes receipt itself and ignored build/__pycache__/xcuserdata',artifactCollectionSHA256=collection(files),artifacts=files)
(ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(f'Sealed {len(files)} artifacts: {receipt["artifactCollectionSHA256"]}')
