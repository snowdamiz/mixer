#!/usr/bin/env python3
"""One-shot seal of owned packet and its accompanying document."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
assert not (HERE/'owned-target').exists()
assert not (HERE/'seal.json').exists(),'existing seal is immutable; do not replace it'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}
doc='docs/swift-reactor-lifecycle-remaining-matrix.md'
seal={'schema':'mixer.swift-lifecycle.remaining-matrix.seal.1','files':files,'externalFiles':{doc:sha(ROOT/doc)},'scope':'Host synthetic test-only evidence; no fullSL row or accounting/GA acceptance.'}
(HERE/'seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
print(json.dumps({'files':len(files),'sealSHA256':sha(HERE/'seal.json')}))
