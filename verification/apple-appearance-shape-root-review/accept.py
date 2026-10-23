from pathlib import Path
import json,hashlib,subprocess,datetime
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
producer=ROOT/'verification/apple-appearance-shape-measurement'
bindings={};commands=[]
def bind(path,expected=None):
    value=hashlib.sha256(path.read_bytes()).hexdigest()
    assert expected is None or value==expected,str(path)
    bindings[str(path.relative_to(ROOT))]=value
    return value
for name in ['test-analysis.py','verify-seal.py']:
    cmd=['python3','-B',str(producer/'scripts'/name)]
    r=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=HERE/(name+'.log');log.write_bytes(r.stdout)
    commands.append({'command':cmd,'exit':r.returncode,'log':str(log.relative_to(ROOT)),'sha256':bind(log)})
    assert r.returncode==0,r.stdout.decode()
receipt=json.loads((producer/'receipt.json').read_bytes())
assert len(receipt['artifacts'])==243
for entry in receipt['artifacts']:
    path=producer/entry['path'];assert path.stat().st_size==entry['bytes'];bind(path,entry['sha256'])
bind(producer/'receipt.json')
bind(ROOT/receipt['externalDocument']['path'],receipt['externalDocument']['sha256'])
analysis=json.loads((producer/'analysis.json').read_bytes());assert len(analysis['captures'])==12
for capture in analysis['captures']:
    a=producer/capture['sourcePNG'];b=ROOT/'verification/apple-appearance-measurement'/capture['sourcePNG']
    assert a.read_bytes()==b.read_bytes(),capture['name']
    bind(b);bind(a,capture['pngSHA256'])
    assert capture['parentNodesEqual'] and capture['parentPixelComparison']['differentPixels']==0
    if 'historicalPixelComparison' in capture:assert capture['historicalPixelComparison']['differentPixels']==0
assert len(analysis['switches'])==10 and len(analysis['groupCornerComparisons'])==12
for group in analysis['groupCornerComparisons']:
    a=group['nativeFirstHalfCoverageXPixelByRow'];b=group['candidateFirstHalfCoverageXPixelByRow']
    assert len(a)==len(b)==group['rows']==100
    assert sum(x==y for x,y in zip(a,b))==group['matchingRows']
    assert max(abs(x-y) for x,y in zip(a,b))==group['maximumAbsoluteFrontierDifferencePixels']
    assert abs(sum(abs(x-y) for x,y in zip(a,b))/100-group['meanAbsoluteFrontierDifferencePixels'])<1e-9
proposal=json.loads((producer/'proposed-shared-recipe.json').read_bytes())
assert proposal['switch']['thumbXRule']=='on != rightToLeft ? 24 : 2'
assert proposal['switch']['paints']['dark']['disabledThumb']=='#8E8E8F'
bind(HERE/'accept.py')
result={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'root','decision':'accepted-bounded-unchanged-native-shape-measurements-not-authored-defaults','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'commands':commands,'binding_count':len(bindings),'bindings':dict(sorted(bindings.items())),'scope':{'byte_identical_parent_pngs':12,'independently_recomputed_group_frontier_comparisons':12,'fully_visible_switches':10},'limitations':['Public layer cornerRadius zero is not evidence for native drawn curve. Authored continuous group/switch paths are not accepted as exact native shapes.','Header gaps, row floors and separators are bounded contextual observations, not universal native layout rules.','Disabled-off/pressed/dragged/focused/animated states and other displays are unmeasured.','No native renderer consumes these measurements; Android interaction/accessibility/design parity, physical evidence, signed release and all GA gates remain pending.']}
(HERE/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS',len(bindings),'root bindings;12 exact PNGs and12 independently recomputed curve comparisons')
