#!/usr/bin/env python3
"""Retain output, source-stage and immutable parent checks, then seal scoped evidence."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
from png_reader import png,compare
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
commands=[]
def command(name,args):
    log=ROOT/'logs'/('finish-'+name+'.log');start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with log.open('w') as out:result=subprocess.run(args,cwd=REPO,stdout=out,stderr=subprocess.STDOUT)
    print(name,result.returncode,flush=True)
    commands.append(dict(name=name,argv=args,cwd=str(REPO),startedUTC=start,finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=result.returncode,output=str(log.relative_to(ROOT))))
    (ROOT/'commands-finish.json').write_text(json.dumps(commands,indent=2)+'\n')
    assert result.returncode==0,log
command('analyze',['python3',str(ROOT/'scripts/analyze.py')])
command('test-analysis',['python3',str(ROOT/'scripts/test-analysis.py')])
command('original-seal',['python3',str(ROOT.parent/'apple-appearance-reference/scripts/verify-seal.py')])
command('parent-seal',['python3',str(ROOT.parent/'apple-appearance-measurement/scripts/verify-seal.py')])
supplement=compare(png(ROOT/'path-supplement/screenshot.png'),png(ROOT/'captures/debug/controls-light/screenshot.png'))
assert supplement['equalDecodedPixels']
stage1=json.loads((ROOT/'source-lock-stage1.json').read_text())
for e in stage1['files']:
    path=ROOT/e['path']
    if e['path']=='instrumented-sdk/Sources/MixerApple/ShapeProbe.swift':path=ROOT/'source-stages/stage1/ShapeProbe.swift'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==e['sha256'],path
stage2=json.loads((ROOT/'source-lock-stage2.json').read_text())
for e in stage2['files']:assert hashlib.sha256((ROOT/e['path']).read_bytes()).hexdigest()==e['sha256'],e['path']
parent=json.loads((ROOT/'parent-input-lock.json').read_text())
for e in parent['files']:assert hashlib.sha256((REPO/e['path']).read_bytes()).hexdigest()==e['sha256'],e['path']
assert hashlib.sha256((ROOT.parent/'apple-appearance-measurement/receipt.json').read_bytes()).hexdigest()==parent['receiptSHA256']
analysis=json.loads((ROOT/'analysis.json').read_text())
result={'status':'passed-scoped-native-measurement-integrity; authored-shapes-and-parity-unaccepted',
    'parentExactPixelAndNodePairs':len(analysis['captures']),'originalExactPixelPairs':sum('historicalPixelComparison' in c for c in analysis['captures']),
    'supplementExactPixelComparison':supplement,'fullyVisibleSwitches':len(analysis['switches']),
    'physicalDevices':'not inventoried or used; remain pending','acceptance':'No design/parity/release/GA acceptance'}
(ROOT/'verification-result.json').write_text(json.dumps(result,indent=2)+'\n')
doc=REPO/'docs/apple-appearance-shapes.md'
artifacts=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='receipt.json' and not any(t in ['build','__pycache__','xcuserdata'] for t in p.relative_to(ROOT).parts)]
receipt={'format':'mixer.apple-appearance-shape-receipt.1','sealedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':result['status'],'parentMeasurementReceiptSHA256':parent['receiptSHA256'],
    'baselineRevision':'958998d92f1c2ba205de09a83d957d738b619572',
    'buildCheckoutRevision':(ROOT/'logs/git-revision.log').read_text().strip(),'buildCheckoutTree':(ROOT/'logs/git-tree.log').read_text().strip(),
    'sourceStages':{'stage1':'source-lock-stage1.json; ShapeProbe preserved under source-stages/stage1','stage2':'source-lock-stage2.json'},
    'simulator':json.loads((ROOT/'simulator.json').read_text()),
    'tools':{n:(ROOT/f'logs/{n}.log').read_text().strip() for n in ['xcode-version','swift-version','sdk-version','sdk-path','host-version']},
    'scope':result,'dependencies':'Owned frozen SDK, Python standard library, official Apple toolchain and public platform frameworks only. No dependency or font asset added.',
    'limitations':['Public cell/background radius values are zero; no native path exposed','Authored cubic paths differ measurably from native contours','Bounded simulator static cases only','Native exact group/cell clipping and antialiasing unresolved','Disabled-off/pressed/dragged/shadow/other OS widths scales unmeasured','No physical iOS or Android parity, release, dogfood or GA receipt'],
    'ownership':'Only verification/apple-appearance-shape-measurement/** and docs/apple-appearance-shapes.md; no product/tracker/commit/push changes',
    'externalDocument':{'path':'docs/apple-appearance-shapes.md','sha256':hashlib.sha256(doc.read_bytes()).hexdigest()},
    'artifactCollectionSHA256':hashlib.sha256(json.dumps(artifacts,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'artifacts':artifacts}
(ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('Sealed',len(artifacts),'artifacts; exact parent12, original8, supplementary1. Design, parity, physical and GA remain pending.')
