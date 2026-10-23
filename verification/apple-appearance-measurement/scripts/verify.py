#!/usr/bin/env python3
"""Executable evidence admission. Does not confer native parity or release approval."""
from pathlib import Path
import hashlib, json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent/'apple-appearance-reference'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def check(condition,message):
    if not condition: raise AssertionError(message)
def main():
    subprocess.run([sys.executable,str(BASE/'scripts/verify-seal.py')],check=True)
    lock=json.loads((ROOT/'input-lock.json').read_text())
    check(digest(BASE/'receipt.json')==lock['baselineReceiptSHA256'],'baseline receipt changed')
    check(lock['baselineRevision']=='958998d92f1c2ba205de09a83d957d738b619572','unexpected source revision')
    for entry in lock['baselineInputs']:
        source=BASE/'frozen'/entry['path'];check(digest(source)==entry['sha256'],'baseline input changed: '+entry['path'])
        if entry['path'].startswith('sdk/Sources/') or entry['path']=='sdk/Package.swift':
            target=ROOT/'instrumented-sdk'/Path(entry['path']).relative_to('sdk')
            if entry['path'].endswith('/MixerNativeView.swift'):
                check(target.read_text().count('MeasurementProbe(')==2,'probe renderer change admission')
            else: check(digest(target)==entry['sha256'],'non-probe SDK input changed: '+entry['path'])
    for entry in json.loads((ROOT/'comparison-inputs.json').read_text())['files']:
        check(digest(ROOT/'comparison-inputs'/entry['path'])==entry['sha256'],'comparison snapshot changed')
    commands=json.loads((ROOT/'commands.json').read_text())
    check(all(c['exitCode']==0 for c in commands),'capture command failed')
    for configuration in ['debug','release']:
        build=next(c for c in commands if c['name']=='build-'+configuration)
        check('** BUILD SUCCEEDED **' in (ROOT/build['output']).read_text(),'missing build success')
    captures=json.loads((ROOT/'capture-manifest.json').read_text())['captures']
    check(len(captures)==24,'expected 12 profiles in Debug and Release')
    summaries=[]
    for capture in captures:
        folder=ROOT/'captures'/capture['name'];e=json.loads((folder/'environment.json').read_text());m=json.loads((folder/'measurements.json').read_text())
        for entry in capture['files']:
            check(digest(folder/entry['path'])==entry['sha256'],'capture changed: '+capture['name']+'/'+entry['path'])
        fixture=ROOT/'harness/Fixtures'/f"{capture['fixture']}.json"
        check((folder/'rendered-document.json').read_bytes()==fixture.read_bytes(),'document bytes changed')
        check(fixture.read_bytes()==(BASE/'harness/Fixtures'/fixture.name).read_bytes(),'fixture no longer exact baseline')
        check(e['hostSnapshotEqualsSourceDocument'] is True and e['screenScale']==3,'window environment mismatch')
        check(e['windowBoundsPoints']=={'width':402,'height':874},'window dimensions changed')
        check(e['swiftUIColorScheme']==capture['requestedAppearance'],'appearance mismatch')
        check(e['swiftUILayoutDirection']==capture['requestedDirection'],'direction mismatch')
        expected='accessibility1' if capture['requestedContentSize']=='accessibility-medium' else 'large'
        check(e['swiftUIDynamicTypeSize']==expected,'dynamic type mismatch')
        ids=[n['id'] for n in m['nodes']];check(len(set(ids))==len(ids),'duplicate node geometry')
        check(any(n['kind']=='sectionHeader' for n in m['nodes']),'section header geometry missing')
        check(any(n['publicType']=='UINavigationBar' and n['prefersLargeTitles'] for n in m['publicUIKitObservations']),'large navigation absent')
        summaries.append(dict(name=capture['name'],measuredNodeOrHeaderCount=len(ids)))
    analysis=json.loads((ROOT/'analysis.json').read_text())['captures']
    check(len(analysis)==24,'pixel analysis missing captures')
    historical=[a for a in analysis if 'historicalUninstrumentedReferenceComparison' in a]
    check(len(historical)==16,'expected eight historical reference cases in D/R')
    check(all(a['historicalUninstrumentedReferenceComparison']['equalDecodedPixels'] for a in historical),'instrumented output differs from historical reference')
    release=[a for a in analysis if 'debugReleasePixelComparison' in a]
    check(len(release)==12 and all(a['debugReleasePixelComparison']['equalDecodedPixels'] for a in release),'D/R pixel difference')
    # Node coordinates may differ by floating rounding; exact comparison is reported,
    # then bounded numeric comparison protects the 1/3 pt display geometry.
    for capture in captures:
        if capture['configuration']!='Release':continue
        name=capture['name'].split('/',1)[1]
        d=json.loads((ROOT/'captures/debug'/name/'measurements.json').read_text())['nodes'];r=json.loads((ROOT/'captures/release'/name/'measurements.json').read_text())['nodes']
        check([n['id'] for n in d]==[n['id'] for n in r],'D/R geometry coverage differs')
        for dn,rn in zip(d,r):
            check(all(abs(dn['frameGlobalPoints'][key]-rn['frameGlobalPoints'][key])<1e-8 for key in ['x','y','width','height']),'D/R geometry differs')
            check(dn.get('font')==rn.get('font'),'D/R resolved font differs')
    print('PASS: isolated frozen derivative, 24 native captures; 16 historical comparisons and 12 D/R pixel comparisons exact; 24 environment/document records checked.')
    print('PENDING: exact section-header font, control label fonts, switch track/thumb internals, dynamic/interaction/accessibility behavior, accountable design review, physical iOS/Android parity, signed/dogfood/GA qualification.')
    (ROOT/'verification-result.json').write_text(json.dumps(dict(status='passed-scoped-measurement-integrity; parity-pending',captures=summaries),indent=2)+'\n')
if __name__=='__main__': main()
