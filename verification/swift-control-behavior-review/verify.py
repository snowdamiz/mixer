#!/usr/bin/env python3
"""Offline reviewer packet audit. No execution, integration or acceptance."""
from pathlib import Path
import collections,gzip,hashlib,json,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
enc=lambda v:(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
seal=json.loads((HERE/'seal.json').read_text())
for name,expected in seal['files'].items():assert sha(HERE/name)==expected,name
for name,expected in seal['externalBindings'].items():assert sha(ROOT/name)==expected,name
assert sha(ROOT/'docs/swift-control-behavior-review.md')==seal['documentSHA256']
r=json.loads((HERE/'receipt.json').read_text())
assert r['recommendation'] and not any(r[x] for x in ['rootAccepted','implementationAccepted','liveIntegrated','gaAcceptance','nativeRuntime','physicalRuntime','fullDispatcher','Ready','publicInvocation'])
assert r['baselineVMClosure']=='4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
assert r['implementationVMClosure']=='241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5'
commands=json.loads((HERE/'commands.json').read_text());assert len(commands)==r['commands']
for c in commands:
    path=HERE/c['receipt'];assert json.loads(path.read_text())=={k:v for k,v in c.items() if k not in ['receipt','passedTests','failedTests','ignoredTests']}
    for stream in ['stdout','stderr']:assert hashlib.sha256(gzip.decompress((path.parent/(stream+'.gz')).read_bytes())).hexdigest()==c[stream+'SHA256']
    if c['sourceManifest'] is not None:assert hashlib.sha256(enc(c['sourceManifest'])).hexdigest()==c['sourceTreeSHA256']
for q in r['qualifyingRuntimeAndCheckCommands']:
    c=next(c for c in commands if c['receipt']==q['receipt']);assert c['exitCode']==0
    if 'passedTests' in q:assert c['passedTests']==q['passedTests'] and c['failedTests']==c['ignoredTests']==0
assert len([q for q in r['qualifyingRuntimeAndCheckCommands'] if q.get('passedTests')==46])==4
assert len([q for q in r['qualifyingRuntimeAndCheckCommands'] if q.get('passedTests')==6])==4
assert len([q for q in r['qualifyingRuntimeAndCheckCommands'] if q.get('passedTests')==7])==4
assert len([q for q in r['qualifyingRuntimeAndCheckCommands'] if q.get('passedTests') in [168,197]])==4
probe=json.loads((HERE/'probe-manifest.json').read_text());assert hashlib.sha256(enc(probe)).hexdigest()==r['reviewProbeVMClosure']
for row in json.loads((HERE/'executable-manifest.json').read_text()):
    data=gzip.decompress((HERE/row['path']).read_bytes());assert len(data)==row['uncompressedBytes'];assert hashlib.sha256(data).hexdigest()==row['uncompressedSHA256']
assert all(x['identical'] and x['reservationBytes']==2912 for x in json.loads((HERE/'frozen-identity.json').read_text()).values())
canonical=json.loads((HERE/'canonical-roles.json').read_text());assert len(canonical)==2 and all(len(x['functions'])==38 and x['fields']==3752 for x in canonical)
assert json.loads((HERE/'hook-role-replay.json').read_text())['positiveFields']==400
layouts=json.loads((HERE/'layouts.json').read_text());assert len(layouts)==8
for x in layouts:
    expected=r['unit' if x['unit'] else 'production'];assert (x['totals']['header'],x['totals']['frame_bound'],x['totals']['new_permanent'],x['totals']['new_active'])==(expected['header'],expected['frame'],expected['controlPermanent'],expected['controlActive']);assert x['types']['FrameOperationStorage']['bytes']==6232
with tarfile.open(HERE/'metadata-source.tar.gz') as archive:
    actual={}
    for member in archive.getmembers():
        assert member.isfile() and member.name.startswith('vm/') and '..' not in Path(member.name).parts
        actual[member.name[3:]]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    assert actual==json.loads((HERE/'metadata-manifest.json').read_text())
clippy=json.loads((HERE/'clippy-comparison.json').read_text());norm=lambda rows:collections.Counter(json.dumps(x,sort_keys=True) for x in rows)
assert len(clippy['baseline'])==len(clippy['candidate'])==26 and norm(clippy['baseline'])==norm(clippy['candidate'])
attempts=json.loads((HERE/'attempts.json').read_text());assert len(attempts['authoringFailures'])==1 and len(attempts['excludedVerificationAttempts'])==4 and attempts['productCorrections']==[]
assert json.loads((HERE/'findings.json').read_text())['unresolvedFindings']==[]
cleanup=json.loads((HERE/'cleanup.json').read_text());assert cleanup['removed'] and cleanup['liveVMUnchanged'] and cleanup['nativeInstancesStarted']==cleanup['physicalRuns']==0
print('passed: independent private Swift control behavior recommendation; 4x46 original +4x6 Frozen +4x7 new probes +4 full libraries, 8 exact layouts, 38 canonical functions/config and400 hook fields; unchanged live baseline, no root/GA acceptance')
