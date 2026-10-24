#!/usr/bin/env python3
"""Verify this historical, rejected preflight review without compiler execution."""
from pathlib import Path
import gzip,hashlib,json,tarfile
HERE=Path(__file__).resolve().parent
def raw(p):return p.read_bytes() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes())
def read(p):return json.loads(raw(p))
sha=lambda b:hashlib.sha256(b).hexdigest()
seal=read(HERE/'seal.json')
for name,expected in seal['files'].items():assert sha(raw(HERE/name))==expected,name
root=HERE.parents[1]
for name,expected in seal['externalBindings'].items():assert sha(raw(root/name))==expected,name
receipt=read(HERE/'receipt.json')
assert receipt['status']=='revision-required-preflight-only'
assert receipt['metadataConfigurations']==8 and receipt['liveVMUnchanged']
assert not any(receipt[k] for k in ['controlOperationsExecuted','sc01Through12Passed','sourceAccountingPreflightAccepted','implementationAccepted','nativeRuntime','physicalRuntime','gaAcceptance'])
assert len(read(HERE/'findings.json'))==1
for commands in [HERE/'commands.json',*sorted((HERE/'attempts').glob('*/commands.json'))]:
 for command in read(commands):
  for stream in ['stdout','stderr']:
   assert sha(raw(commands.parent/command[stream]))==command[stream+'SHA256'],command['name']
assert read(HERE/'baseline-frozen-bodies.json')==read(HERE/'candidate-frozen-bodies.json')
assert all(v['identical'] for v in read(HERE/'independent-frozen-identity.json').values())
manifest=read(HERE/'independent-metadata-manifest.json')
with tarfile.open(HERE/'independent-metadata-source.tar.gz') as tar:
 actual={str(Path(m.name).relative_to('vm')):sha(tar.extractfile(m).read()) for m in tar.getmembers() if m.isfile()}
assert actual==manifest
assert len(read(HERE/'independent-layouts.json'))==8
assert read(HERE/'cleanup.json')['removed'] and not read(HERE/'cleanup.json')['nativeInstancesStarted']
assert read(HERE/'metadata-archive-cleanup.json')['removed']
print('passed: historical independent preflight review; exact compiler/layout evidence; one required source revision; no control execution or acceptance')
