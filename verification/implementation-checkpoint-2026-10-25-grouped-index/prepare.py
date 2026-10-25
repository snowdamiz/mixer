#!/usr/bin/env python3
"""Curate sealed evidence and the accepted two-file live integration only."""
from pathlib import Path
import datetime
import hashlib
import json
import stat
import subprocess

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    (BASE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT)
names = {'STATUS.md','PLAN.md','work-graph.json','gates/ga.json',
         'docs/swift-resident-index-grouped-reservation-integration.md',
         'docs/swift-exact-reactor-after-resident-index-result.md'}
checks = []
for name, file, expected in [
    ('swift-exact-reactor-after-resident-index','result-seal.json','05d31bc936466d9dd6c2b21c411e30e75087396e6f6903a0e6fc597f401948fd'),
    ('swift-index-ticket-storage-diagnosis','seal.json','44e3aeedcbca786326a565683929ffb1a4e30428898356b50633985ce9f1812d'),
    ('swift-resident-index-grouped-reservation','seal.json','75d680a75b8fc49dcf9fa4999b981d7013cd9416dbd7c72d4534740958602ae6'),
    ('swift-resident-index-grouped-reservation-review','seal.json','3e26c015bf401844a8f265413598bc434229f0dfd855ed1ed307e4385c4f7830'),
]:
    p = ROOT/'verification'/name/file
    assert sha(p)==expected,p
    d=json.loads(p.read_bytes()); names.add(str(p.relative_to(ROOT)))
    for n,h in d['files'].items():
        f=p.parent/n;assert sha(f)==h,f;names.add(str(f.relative_to(ROOT)))
    for n,h in d['externalFiles'].items():
        f=ROOT/n;assert sha(f)==h,f
        if not n.startswith('compiler/experiments/fieldlog-reactor/local/'):
            names.add(n)
    checks.append(dict(packet=str(p.relative_to(ROOT)),members=len(d['files']),sha256=expected))
for name,expected in [
    ('apple-settings-fixed-chunk-implementation','2d01866f3fa0f88b283ba8f2774f03092eb93d9616daeaa7d5d2875618cf6748'),
    ('apple-settings-fixed-chunk-review','43f2ee87e461d28a8d05d113adf7a9581ea34c6d16e0dfe5caee26773febc092'),
    ('apple-settings-fixed-chunk-native-build','3e6dc04dd9d2f314f3ccf5a9dc363e88c327936f2e9719b9365000f81859cc21'),
    ('apple-settings-fixed-chunk-runtime-preparation','bcb2b7135eaa594b6a6ac0a84866cf0877ec1a3cb0264b1a51fcc33afd0860b2'),
]:
    p=ROOT/'verification'/name/'handoff.json';assert sha(p)==expected,p
    d=json.loads(p.read_bytes());names.add(str(p.relative_to(ROOT)))
    for n,row in d['members'].items():
        f=ROOT/n;assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'],f;names.add(n)
    for n in ['handoff.sha256','verification-result.json']:
        if (p.parent/n).is_file():names.add(str((p.parent/n).relative_to(ROOT)))
    checks.append(dict(packet=str(p.relative_to(ROOT)),members=len(d['members']),sha256=expected))
for name,expected in [
    ('hosted-worker-pending-terminal-consistency-review','2a5646144c8696d6ff2c02d935a6942a18d61dd0c5f8ddf7e99314f5aa0dab13'),
    ('hosted-worker-pending-migration-history','5bce543f307a07666aa5bc70b4f9e5da6f59ac82edc5956c26d859a8f64d288e'),
    ('hosted-worker-pending-migration-history-review','43992550d3fff245b10e0d019c484f904f24f6de1b4de6bb2645635e0cc3aa06'),
    ('hosted-worker-pending-migration-outbox','a27b0ce3438705f0bd30ae4dd088f19d4ece3367cb91f78ad42eab8b1413bca1'),
]:
    p=ROOT/'verification'/name/'receipt.json';assert sha(p)==expected,p
    d=json.loads(p.read_bytes());names.add(str(p.relative_to(ROOT)));names.add('docs/'+name+'.md')
    for row in d['artifacts']:
        f=ROOT/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'],f;names.add(row['path'])
    checks.append(dict(packet=str(p.relative_to(ROOT)),members=len(d['artifacts']),sha256=expected))
for directory in [
    'swift-exact-reactor-after-resident-index-root-selection',
    'swift-resident-index-grouped-reservation-root-integration',
    'apple-settings-fixed-chunk-root-review',
    'apple-settings-fixed-chunk-build-root-review',
    'apple-settings-fixed-chunk-runtime-root-review',
    'hosted-worker-pending-migration-history-root-review',
    'hosted-worker-pending-migration-outbox-root-review',
    'github-ci-be472ce6-engine','github-delivery-resident-index',
]:
    for p in (ROOT/'verification'/directory).rglob('*'):
        assert not p.is_symlink(),p
        if p.is_file():names.add(str(p.relative_to(ROOT)))
candidate=ROOT/'verification/swift-resident-index-grouped-reservation'
manifest=json.loads((candidate/'source-manifest.json').read_bytes())
assert len(manifest)==132 and {n:sha(ROOT/'vm'/n) for n in manifest}==manifest
names.update('vm/'+n for n in json.loads((candidate/'selection.json').read_bytes())['changedFiles'])
integration=json.loads((ROOT/'verification/swift-resident-index-grouped-reservation-root-integration/receipt.json').read_bytes())
assert integration['status']=='accepted-live-private-grouped-index-reservation' and integration['ownedTargetRemoved']
assert sum(c['expectedTests'] for c in integration['commands'])==32
for name in names:
    p=ROOT/name;info=p.lstat()
    assert stat.S_ISREG(info.st_mode) and not p.is_symlink() and info.st_size<50_000_000,p
    assert not {'node_modules','owned-target','owned-scratch','owned-build','target','tmp'}.intersection(p.relative_to(ROOT).parts),p
    assert 'native-run-v6-' not in name,p
packages=json.loads((ROOT/'work-graph.json').read_bytes())['packages'];gates=json.loads((ROOT/'gates/ga.json').read_bytes())['gates']
assert [p['id'] for p in packages]==[f'W{i:02}' for i in range(1,19)]
assert [g['id'] for g in gates]==[f'G{i:02}' for i in range(1,39)]
assert all(g['evidence'] and g['reviewer'] for g in gates if g['status']=='passed')
save('verification.json',dict(schema=1,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),parentRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),checks=checks,trackerIntegrity='passed',sourceDigest=sha(candidate/'source-manifest.json'),liveIntegrationTestsPassed=32,scope='Accepted grouped reservation live slice and independent review; failed prior full target and worker reviews; sealed worker correction and native build/preparation. Active reviews and new full-reactor preparation excluded.',nativeAccepted=False,gaAccepted=False))
names.update(str(p.relative_to(ROOT)) for p in BASE.iterdir() if p.is_file())
listed=str(BASE.relative_to(ROOT)/'selected-files.json');hashes=str(BASE.relative_to(ROOT)/'source-hashes.json');names.update([listed,hashes]);names=sorted(names)
save('selected-files.json',names);save('source-hashes.json',{n:sha(ROOT/n) for n in names if n not in [listed,hashes]})
print(json.dumps(dict(selectedFiles=len(names),bytes=sum((ROOT/n).stat().st_size for n in names),frozenPackets=len(checks))))
