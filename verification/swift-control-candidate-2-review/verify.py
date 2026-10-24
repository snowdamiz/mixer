#!/usr/bin/env python3
"""Offline audit of the sealed independent candidate 2 preflight recommendation."""
from pathlib import Path
import gzip,hashlib,json,tarfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def raw(p):return p.read_bytes() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes())
def read(p):return json.loads(raw(p))
def sha(b):return hashlib.sha256(b).hexdigest()
seal=read(HERE/'seal.json')
for name,expected in seal['files'].items():assert sha(raw(HERE/name))==expected,name
for name,expected in seal['externalBindings'].items():assert sha(raw(ROOT/name))==expected,name
producer=ROOT/'verification/swift-control-accounting-candidate-2'
for name,expected in read(producer/'seal.json')['files'].items():assert sha(raw(producer/name))==expected,name
for name,expected in read(producer/'seal.json')['externalBindings'].items():assert sha(raw(ROOT/name))==expected,name
receipt=read(HERE/'receipt.json')
assert receipt['status']=='recommend-accept-source-accounting-preflight-only'
assert receipt['sourceAccountingPreflightRecommendation'] and receipt['metadataConfigurations']==8
assert receipt['liveVMUnchanged'] and not any(receipt[k] for k in ['controlOperationsExecuted','sc01Through12Passed','sourceAccountingPreflightAccepted','implementationAccepted','nativeRuntime','physicalRuntime','gaAcceptance'])
for command_file in [HERE/'commands.json',*sorted((HERE/'attempts').glob('*/commands.json'))]:
    for command in read(command_file):
        for stream in ['stdout','stderr']:assert sha(raw(command_file.parent/command[stream]))==command[stream+'SHA256'],command['name']
for path,item in read(HERE/'compression-index.json').items():
    data=gzip.decompress((HERE/(path+'.gz')).read_bytes())
    assert sha(data)==item['uncompressedSHA256'] and len(data)==item['uncompressedBytes'],path
assert read(HERE/'baseline-frozen-bodies.json')==read(HERE/'candidate-frozen-bodies.json')
assert all(v['identical'] for v in read(HERE/'independent-frozen-identity.json').values())
for label in ['production','unit']:
    assert len(read(HERE/'independent-typed-census.json')[label])==38
    fresh=read(HERE/'fresh-canonical-mir-census.json')[label]
    assert len(fresh['functions'])==38 and sha(raw(HERE/f'fresh-{label}.mir'))==fresh['mirSHA256']
delta=read(HERE/'independent-delta.json')
assert (delta['oldFields'],delta['newFields'],delta['addedFields'],delta['removedFields'])==(7520,7640,136,16)
assert delta['sourceLifecycleFields']==120 and delta['changedFiles']==['src/experimental_swift_reactor/control_operations.rs']
assert read(HERE/'supplement.json')['status']=='passed'
assert len(read(HERE/'independent-layouts.json'))==8
manifest=read(HERE/'independent-metadata-manifest.json')
with tarfile.open(HERE/'independent-metadata-source.tar.gz') as tar:
    actual={str(Path(m.name).relative_to('vm')):sha(tar.extractfile(m).read()) for m in tar.getmembers() if m.isfile()}
assert actual==manifest
assert read(HERE/'cleanup.json')['removed'] and not read(HERE/'cleanup.json')['nativeInstancesStarted']
assert read(HERE/'findings.json')['unresolvedFindings']==[]
assert read(HERE/'findings.json')['resolvedPriorFindings']==['SCPR-01']
print('passed: independent candidate 2 source/accounting preflight recommendation; 7640 fields, fresh MIR/8 metadata configurations, Frozen identity; no control execution or root acceptance')
