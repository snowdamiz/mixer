#!/usr/bin/env python3
"""Curate finished reviews and observed runtime results; exclude active lanes."""
from pathlib import Path
import datetime
import hashlib
import json
import stat
import subprocess

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names={'STATUS.md','PLAN.md','work-graph.json','gates/ga.json',
       'docs/apple-settings-fixed-chunk-native-result.md',
       'docs/hosted-worker-pending-migration-outbox-review.md'}
checks=[]

def save(name,value):
    (BASE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT)
p=ROOT/'verification/swift-exact-reactor-after-grouped-index/result-seal.json'
assert sha(p)=='91c71f2c6b6520e141b9226f7675a4578d0d37865aa1dfcfafc9e4dad31acb8c'
seal=json.loads(p.read_bytes());names.add(str(p.relative_to(ROOT)))
for n,h in seal['files'].items():
    f=p.parent/n;assert sha(f)==h;names.add(str(f.relative_to(ROOT)))
for n,h in seal['externalFiles'].items():
    f=ROOT/n;assert sha(f)==h
    if not n.startswith('compiler/experiments/fieldlog-reactor/local/'):names.add(n)
checks.append(dict(packet=str(p.relative_to(ROOT)),members=len(seal['files']),sha256=sha(p)))
p=ROOT/'verification/apple-settings-fixed-chunk-runtime-review/handoff.json'
assert sha(p)=='e1c8b2345056742eacbc2b2faa415e760f75ba351b639adb410124322e3f4035'
seal=json.loads(p.read_bytes());names.add(str(p.relative_to(ROOT)))
for n,row in seal['members'].items():
    f=ROOT/n;assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'];names.add(n)
checks.append(dict(packet=str(p.relative_to(ROOT)),members=len(seal['members']),sha256=sha(p)))
p=ROOT/'verification/hosted-worker-pending-migration-outbox-review/receipt.json'
assert sha(p)=='27b5a51b9eaecff3973f03eb5f66b13bdfe3e94145879f489cc9337779188c18'
seal=json.loads(p.read_bytes());names.add(str(p.relative_to(ROOT)))
assert seal['groupsPassed']==37 and seal['actionableFindings']==0
for row in seal['artifacts']:
    f=ROOT/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'];names.add(row['path'])
checks.append(dict(packet=str(p.relative_to(ROOT)),members=len(seal['artifacts']),sha256=sha(p)))
p=ROOT/'verification/apple-settings-fixed-chunk-native/result-manifest.json'
assert sha(p)=='ccb7ce47693677fcfc43f68939fdb9eeaa86bdeb6090ee9cfb5a5257a232382c'
seal=json.loads(p.read_bytes());names.add(str(p.relative_to(ROOT)))
assert seal['nativeAttempts']==1 and not seal['runPassed'] and seal['ownedDeviceAbsent']
assert len(seal['cleanupResults'])==5 and all(row['passed'] for row in seal['cleanupResults'])
for n,row in seal['files'].items():
    f=ROOT/n;assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'];names.add(n)
checks.append(dict(packet=str(p.relative_to(ROOT)),members=len(seal['files']),sha256=sha(p)))
for directory in ['swift-exact-reactor-after-grouped-index-root-selection',
        'apple-settings-fixed-chunk-runtime-root-review',
        'hosted-worker-pending-migration-outbox-root-review',
        'github-delivery-grouped-index','github-ci-4a28261b-engine']:
    for p in (ROOT/'verification'/directory).rglob('*'):
        assert not p.is_symlink(),p
        if p.is_file():names.add(str(p.relative_to(ROOT)))
for name in ['observe_dispatch.py','observer-binding.patch','observer-review.json']:
    names.add('verification/apple-settings-fixed-chunk-native/'+name)
for n in names:
    p=ROOT/n;info=p.lstat()
    assert stat.S_ISREG(info.st_mode) and not p.is_symlink() and info.st_size<50_000_000,p
    assert not {'node_modules','owned-target','owned-scratch','owned-build','target','tmp'}.intersection(p.relative_to(ROOT).parts),p
    assert not any(s in n for s in ['swift-decode-plan-reuse-diagnosis','hosted-worker-pending-entry-integration/','apple-settings-fixed-chunk-native-result-review/']),p
packages=json.loads((ROOT/'work-graph.json').read_bytes())['packages']
gates=json.loads((ROOT/'gates/ga.json').read_bytes())['gates']
assert [p['id'] for p in packages]==[f'W{i:02}' for i in range(1,19)]
assert [g['id'] for g in gates]==[f'G{i:02}' for i in range(1,39)]
assert all(g['evidence'] and g['reviewer'] for g in gates if g['status']=='passed')
save('verification.json',dict(schema=1,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    parentRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    checks=checks,trackerIntegrity='passed',liveSourceChanged=False,
    scope='Finished independent Worker Engine and native packaging reviews; exact Swift CacheWork failure and native Settings pass/first-Tab failure, with complete owned cleanup. Active implementation/review lanes excluded.',
    nativeAccepted=False,gaAccepted=False))
names.update(str(p.relative_to(ROOT)) for p in BASE.iterdir() if p.is_file())
listed=str(BASE.relative_to(ROOT)/'selected-files.json');hashes=str(BASE.relative_to(ROOT)/'source-hashes.json')
names.update([listed,hashes]);names=sorted(names)
save('selected-files.json',names)
save('source-hashes.json',{n:sha(ROOT/n) for n in names if n not in [listed,hashes]})
print(json.dumps(dict(selectedFiles=len(names),bytes=sum((ROOT/n).stat().st_size for n in names),verifiedPackets=len(checks))))
