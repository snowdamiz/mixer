#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent/'apple-appearance-measurement'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 subprocess.run([sys.executable,str(BASE/'scripts/verify-seal.py')],check=True)
 lock=json.loads((ROOT/'input-lock.json').read_text());assert sha(BASE/'receipt.json')==lock['measurementReceiptSHA256']
 source=json.loads((ROOT/'capture-source-lock.json').read_text());assert source['sourceStableAcrossBuildAndCapture']
 for e in source['files']:assert sha(ROOT/e['path'])==e['sha256'],e['path']
 commands=json.loads((ROOT/'commands.json').read_text());assert all(c['exitCode']==0 for c in commands)
 for config in ['debug','release']:assert '** BUILD SUCCEEDED **' in (ROOT/f'logs/build-{config}.log').read_text()
 manifest=json.loads((ROOT/'observation-manifest.json').read_text());assert len(manifest['profiles'])==24 and len(manifest['captures'])==18
 for o in manifest['profiles']+manifest['captures']:
  folder=ROOT/o['path']
  for e in o['files']:assert sha(folder/e['path'])==e['sha256'],o['path']+'/'+e['path']
  env=json.loads((folder/'environment.json').read_text());font=json.loads((folder/'font-profile.json').read_text())
  assert env['swiftUIColorScheme']==o['requestedAppearance']
  assert env['swiftUILayoutDirection']==('rightToLeft' if o['rtl'] else 'leftToRight')
  assert env['hostSnapshotEqualsSourceDocument'] and env['screenScale']==3
  assert font['candidateFontsApplied']==o['candidateFontsApplied']
  assert (folder/'rendered-document.json').read_bytes()==(BASE/'harness/Fixtures'/f"{o['fixture']}.json").read_bytes()
  if 'expectedSwiftUIDynamicTypeSize' in o:assert env['swiftUIDynamicTypeSize']==o['expectedSwiftUIDynamicTypeSize']
 profiles=json.loads((ROOT/'type-profiles.json').read_text())['profiles'];assert len(profiles)==12
 assert [p['normalizedProfileID'] for p in profiles]==['xs','s','m','l','xl','xxl','xxxl','a1','a2','a3','a4','a5']
 assert all(p['debugReleaseSemanticFontsEqual'] and p['debugReleaseExpandedUIFontEqual'] and p['debugReleaseLineBoxProbesEqual'] for p in profiles)
 for p in profiles:
  assert len(p['nativeLineBoxProbes'])==8
  assert all(p['nativeLineBoxProbes'][r+'.two']['height']>p['nativeLineBoxProbes'][r+'.one']['height']>0 for r in ['body','headline','title','caption'])
 assert all(p['fontLargeTitleBoldMatchesActualExpandedSizeAndName'] for p in profiles)
 assert len(set(p['nativePreferredContentSizeCategory'] for p in profiles))==12
 for role in ['body','headline','title','caption']:
  sizes=[p['fonts'][role]['pointSize'] for p in profiles];assert sizes==sorted(sizes)
 comparisons=json.loads((ROOT/'candidate-comparisons.json').read_text())['comparisons'];assert len(comparisons)==18
 controls=[c for c in comparisons if not c['candidateFontsApplied']];assert len(controls)==3
 assert all(c['equalDecodedPixels'] for c in controls),'new harness perturbs immutable reference'
 candidates=[c for c in comparisons if c['candidateFontsApplied']];assert len(candidates)==15
 # Candidate mismatch must be retained as a rejection rather than hidden.
 matched=sum(c['equalDecodedPixels'] for c in candidates)
 print(f'PASS: all12 actual preferences exported in D/R; public semantic and expanded UIFont records equal.3 nonperturbation PNG controls exact. Candidate matches: {matched}/15; only matching matrix cases support the proposed fonts.')
 print('PENDING: other contextual font states/profiles/locales/OS versions, Android normalization/rendering, physical parity, native behavior/accessibility, signed display/dogfood/GA.')
 (ROOT/'verification-result.json').write_text(json.dumps(dict(status='passed-scoped-measurement-integrity; contextual support bounded to observed matches',profileCount=12,nativeProfileExports=24,nonperturbationMatches=3,candidateMatches=matched,candidateComparisons=15),indent=2)+'\n')
if __name__=='__main__':main()
