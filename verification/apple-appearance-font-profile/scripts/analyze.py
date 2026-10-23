#!/usr/bin/env python3
from pathlib import Path
from fractions import Fraction
import hashlib,json,math
from png import png,compare
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent/'apple-appearance-measurement'
def choose_profile(scale1024,profiles):
 if not isinstance(scale1024,int) or isinstance(scale1024,bool) or not 1<=scale1024<=0xffffffff:raise ValueError('bounded positive UInt32 preference required')
 return min(enumerate(profiles),key=lambda pair:(abs(Fraction(pair[1]['fonts']['body']['pointSize']*1024,17)-scale1024),-pair[0]))[1]['normalizedProfileID']
def main():
 manifest=json.loads((ROOT/'observation-manifest.json').read_text());profiles=[]
 for observation in manifest['profiles']:
  if observation['configuration']!='Debug':continue
  folder=ROOT/observation['path'];d=json.loads((folder/'font-profile.json').read_text())
  release=next(o for o in manifest['profiles'] if o['configuration']=='Release' and o['profileID']==observation['profileID'])
  rd=json.loads((ROOT/release['path']/'font-profile.json').read_text())
  actual=d['largestNavigationTitleUILabel']['font'];ractual=rd['largestNavigationTitleUILabel']['font']
  measurement=json.loads((folder/'measurements.json').read_text())
  profiles.append(dict(normalizedProfileID=observation['profileID'],simctlContentSize=observation['requestedContentSize'],swiftUIDynamicTypeSize=d['swiftUIDynamicTypeSize'],
   nativePreferredContentSizeCategory=d['nativePreferredContentSizeCategory'],fonts=d['resolvedSemanticFonts'],actualExpandedNavigationUIFont=actual,
   nativeLineBoxProbes=d['nativeLineBoxProbes'],
   debugReleaseLineBoxProbesEqual=d['nativeLineBoxProbes']==rd['nativeLineBoxProbes'],
   observedRepeatLineHeightIncrements={r:d['nativeLineBoxProbes'][r+'.two']['height']-d['nativeLineBoxProbes'][r+'.one']['height'] for r in ['body','headline','title','caption']},
   semanticUIFontReferences=measurement['semanticUIFontReferences'],
   observedSwiftUITextBounds=[n for n in measurement['nodes'] if n['id'] in ['type.body','type.headline','type.title','type.caption']],
   actualExpandedNavigationFrame=d['largestNavigationTitleUILabel']['frameInWindowPoints'],
   debugReleaseSemanticFontsEqual=d['resolvedSemanticFonts']==rd['resolvedSemanticFonts'],debugReleaseExpandedUIFontEqual=actual==ractual,
   fontLargeTitleBoldMatchesActualExpandedSizeAndName=(d['resolvedSemanticFonts']['expandedNavigationCandidate']['pointSize']==actual['pointSize'] and d['resolvedSemanticFonts']['expandedNavigationCandidate']['postScriptName']==actual['fontName'])))
 result=dict(format='mixer.native-type-profile-observations.1',scope='Actual simulator environment exports for all12 SwiftUI DynamicTypeSize cases, D/R, typography fixture light/LTR. No claim about glyph fallback or Android native fonts.',profiles=profiles)
 (ROOT/'type-profiles.json').write_text(json.dumps(result,indent=2)+'\n')
 comparisons=[]
 for observation in manifest['captures']:
  path=ROOT/observation['path']/'screenshot.png';baseline=BASE/'captures/debug'/observation['baselineCase']/'screenshot.png'
  comparison=compare(png(path),png(baseline))
  comparisons.append(dict(name=observation['name'],configuration=observation['configuration'],candidateFontsApplied=observation['candidateFontsApplied'],baselineCase=observation['baselineCase'],
   screenshotSHA256=hashlib.sha256(path.read_bytes()).hexdigest(),baselineSHA256=hashlib.sha256(baseline.read_bytes()).hexdigest(),**comparison))
 (ROOT/'candidate-comparisons.json').write_text(json.dumps(dict(format='mixer.font-candidate-comparisons.1',candidate='Section header Text.font(.headline); Button.font(.body); Toggle.font(.body); every other style unchanged',comparisons=comparisons),indent=2)+'\n')
 anchors=[dict(normalizedProfileID=p['normalizedProfileID'],bodySizePoints=p['fonts']['body']['pointSize'],bodyScaleNumerator=p['fonts']['body']['pointSize'],bodyScaleDenominator=17,nearestAnchorScale1024=round(p['fonts']['body']['pointSize']*1024/17)) for p in profiles]
 proposal=dict(format='mixer.proposed-type-normalization.1',status='proposed shared policy; root review and Android native implementation/observation pending',
  defaultProfileID='l',profiles=anchors,appleMapping=[dict(nativePreferredContentSizeCategory=p['nativePreferredContentSizeCategory'],swiftUIDynamicTypeSize=p['swiftUIDynamicTypeSize'],normalizedProfileID=p['normalizedProfileID']) for p in profiles],
  scalarMapping=dict(input='positive UInt32 app preferredBodyScale1024, not an instruction to multiply every role size',algorithm='choose nearest rational body size /17 anchor; exact midpoint chooses the larger profile; values outside anchors clamp naturally to first/last; invalid/nonfinite host preferences reject before normalization',
   androidAdapterBoundary='PROPOSED: using current window metrics, obtain platformPreferredBodyDp = TypedValue.applyDimension(COMPLEX_UNIT_SP,17,metrics) / TypedValue.applyDimension(COMPLEX_UNIT_DIP,1,metrics); validate finite positive results, normalize round(platformPreferredBodyDp/17*1024) to positive UInt32, then select nearest profile. This measures the platform preference at the shared body anchor instead of multiplying fonts by Configuration.fontScale. Android native execution and accessibility/rounding equivalence remain pending.',
   output='one of12 immutable shared profile IDs; all role sizes/weights/metrics come from that selected profile together'),
  caveats=['Section/control candidate support is limited to actual candidate matrix results','Actual expanded title UIFont differs from Font.largeTitle.bold at high accessibility preferences if data shows a cap','Font metrics do not establish common Android font family, glyph coverage or shaped line boxes'])
 (ROOT/'normalization-proposal.json').write_text(json.dumps(proposal,indent=2)+'\n')
 print('profile,body,headline,title,caption,actual expanded nav,semantic largeTitle bold,metric baseline advances(body/title/caption)')
 for p in profiles:
  f=p['fonts'];print(','.join(map(str,[p['normalizedProfileID'],*[f[r]['pointSize'] for r in ['body','headline','title','caption']],p['actualExpandedNavigationUIFont']['pointSize'],f['expandedNavigationCandidate']['pointSize'],*[f[r]['metricBaselineAdvanceIncludingLeadingPoints'] for r in ['body','title','caption']]])))
 for c in comparisons:print(c['configuration'],c['name'],'differentPixels=',c['differentPixels'])
if __name__=='__main__':main()
