#!/usr/bin/env python3
"""Seal this isolated review; rerun only to add the initial offline-verifier result."""
from pathlib import Path
import gzip,hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(name,value):(HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
index=json.loads((HERE/'compression-index.json').read_text()) if (HERE/'compression-index.json').exists() else {}
for path in sorted(HERE.rglob('*')):
    if not path.is_file() or path.suffix not in ['.stdout','.json'] or path.name in ['seal.json','compression-index.json']:continue
    data=path.read_bytes()
    if len(data)<100000:continue
    name=str(path.relative_to(HERE));compressed=gzip.compress(data,mtime=0)
    Path(str(path)+'.gz').write_bytes(compressed);path.unlink()
    index[name]=dict(uncompressedSHA256=sha(data),uncompressedBytes=len(data),compressedSHA256=sha(compressed))
save('compression-index.json',index)
bindings=[
    'AGENTS.md','docs/swift-control-invocation-contract.md','docs/swift-control-accounting-preflight.md',
    'docs/swift-control-preflight-review.md','docs/swift-control-accounting-candidate-2.md','docs/swift-control-candidate-2-review.md',
    'verification/swift-control-invocation-root-review/contract.json',
    'verification/swift-control-invocation-root-review/accounting-scope-interpretation.json',
    'verification/swift-control-accounting-preflight/seal.json',
    'verification/swift-control-preflight-review/seal.json','verification/swift-control-preflight-review/frozen.json',
    'verification/swift-control-accounting-candidate-2/seal.json',
    'verification/swift-control-accounting-candidate-2/qualifying.json',
]
save('seal.json',dict(schema=1,status='sealed-independent-source-accounting-preflight-recommendation',
    candidateTreeSHA256='e1b88be22eb683c40bfe53cd32f5b48d391b475b6097bab233aaf00b5303453d',
    rootAcceptanceRequired=True,sourceAccountingPreflightAccepted=False,controlExecutionAuthorized=False,
    implementationAccepted=False,gaAcceptance=False,
    files={str(p.relative_to(HERE)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json'},
    externalBindings={name:sha((ROOT/name).read_bytes()) for name in bindings}))
print('sealed',sha((HERE/'seal.json').read_bytes()))
