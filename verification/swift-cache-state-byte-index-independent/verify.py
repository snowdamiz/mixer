#!/usr/bin/env python3
"""Verify the independent seal and all frozen bytes without executing them."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
raw=(HERE/'seal.json').read_bytes();s=json.loads(raw)
assert len(s['members'])==s['member_count']
assert sum(r['bytes'] for r in s['members'])==s['member_bytes']
for row in s['members']:
 p=ROOT/row['path'];assert p.is_relative_to(HERE)
 b=p.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],p
result={'at':datetime.now(timezone.utc).isoformat(),'python':sys.version,
 'command':'python3 -B verification/swift-cache-state-byte-index-independent/verify.py',
 'seal_sha256':hashlib.sha256(raw).hexdigest(),'member_count':s['member_count'],
 'member_bytes':s['member_bytes'],'all_sealed_bytes_verified':True,
 'compiler_runtime_native_capture_or_product_execution':False}
(HERE/'seal-verification.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2))
