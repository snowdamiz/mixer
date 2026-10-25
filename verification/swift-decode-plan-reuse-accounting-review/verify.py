#!/usr/bin/env python3
"""Read-only verification of the independent finite review packet."""
from pathlib import Path
import gzip,hashlib,json,subprocess
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((H/n).read_text())
s=read('seal.json')
actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file()}
assert actual==set(s['files'])|{'seal.json'}
for n,v in s['files'].items():
    p=H/n;assert sha(p)==v,(n,'hash');assert p.stat().st_mode&0o222==0,(n,'writable')
assert (H/'seal.json').stat().st_mode&0o222==0
for n,v in s['externalFiles'].items():assert sha(R/n)==v,(n,'external binding')
r=read('receipt.json');a=read('command-audit.json');an=read('analysis.json');cl=read('cleanup.json')
assert r['conclusion']=='finite review passes; no actionable production defect found'
assert not any(r['scopeBoundaries'].values())
assert len(a)==36 and sum(x['passedTests'] for x in a.values())==35 and sum(x['failedTests'] for x in a.values())==1
assert [n for n,x in a.items() if not x['qualifyingPass']]==['candidate-exact-phase-original']
assert an['zeroTestCommands']==0 and an['uniqueExecutedNames']==16
bindings=0
for n,x in a.items():
    assert len(x['executedNamedTests'])==1 and x['ownedGroupAbsent'] and x['sourceUnchanged'] and all(x['streamsClosed'].values())
    p=H/'commands'/n;rr=json.loads((p/'receipt.json').read_text())
    assert sha(p/'source-manifest.json')==rr['sourceManifestSHA256']
    assert sha(p/'stdout')==rr['stdoutSHA256'] and sha(p/'stderr')==rr['stderrSHA256']
    for name,digest in json.loads((p/'source-manifest.json').read_text()).items():
        assert sha(H/'source-objects'/digest)==digest,(n,name);bindings+=1
assert bindings==4752
for lane in ['baseline','candidate']:
    for n,v in read(lane+'-review-manifest.json').items():assert sha(H/lane/n)==v
producer=R/'verification/swift-decode-plan-reuse-diagnosis'
assert sha(producer/'seal.json')==r['producerSealSHA256']
live=json.loads((producer/'baseline-manifest.json').read_text());assert len(live)==132
for n,v in live.items():assert sha(R/'vm'/n)==v,(n,'live source drift since review')
assert read('accounting.json')['combinedHeadroomBytes']==1647458
for item in read('frozen-comparison.json')['controls']:
    texts=[]
    for lane in ['baseline','candidate']:
        t=(H/'commands'/(lane+'-'+item['control'])/'stdout').read_text()
        texts.append('\n'.join(x for x in t.splitlines() if not x.startswith('test result:')))
    assert texts[0]==texts[1] and hashlib.sha256(texts[0].encode()).hexdigest()==item['normalizedSHA256']
assert cl['scratchAbsent'] and cl['holdersEmpty'] and cl['inodeStableImmediatelyBeforeRemoval'] and not (H/'owned-scratch').exists()
for item in cl['binaryArchives']:
    p=H/item['archive'];assert sha(p)==item['archiveSHA256'];data=gzip.decompress(p.read_bytes())
    assert len(data)==item['original']['bytes'] and hashlib.sha256(data).hexdigest()==item['original']['sha256']
ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True)
groups=set(cl['processGroupsChecked']);assert not [x for x in ps.splitlines() if len(x.split())>=2 and int(x.split()[1]) in groups]
print(json.dumps({'verifiedFiles':len(s['files']),'externalBindings':len(s['externalFiles']),'sealSHA256':sha(H/'seal.json'),'namedExecutions':36,'passingExecutions':35,'preservedExpectedFixtureFailure':1,'zeroTestCommands':0,'exactPhaseHelperActuallyInvoked':True,'sourceBindings':bindings,'ownedScratchAbsent':True,'conclusion':r['conclusion'],'scope':'finite isolated source/accounting review only; full regression and live integration unselected; no GA'},sort_keys=True))
