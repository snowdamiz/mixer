#!/usr/bin/env python3
"""One-shot offline finalization; inventory checker does not invoke this file."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

root=Path(__file__).resolve().parent
assert not (root/'seal.json').exists(), 'frozen seal already exists'
members=[]
total=0
for path in sorted(root.rglob('*')):
    if path.is_file():
        assert path.suffix not in ['.pyc','.rmeta','.rlib','.mir'], 'unintended generated artifact'
        b=path.read_bytes()
        total+=len(b)
        assert total<6000000, 'packet-byte-bound'
        members.append({'path':str(path.relative_to(root)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
tree=hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest()
final=json.loads((root/'result.json').read_text())
seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':'frozen-offline-delta-preparation-awaiting-independent-review',
      'tree_hash_algorithm':'sha256 canonical sorted-key compact JSON of sorted member records (excludes seal.json)',
      'python':sys.version,'member_count':len(members),'member_bytes':total,'tree_sha256':tree,'members':members,
      'candidate_source146_tree':final['candidate_source146_tree'],'baseline_source146_tree':final['baseline_source146_tree'],
      'claim_limits':final['claim_limits'],'compiler_or_layout_probe_executed':False,'native_runtime_or_process_inventory_executed':False,
      'counts':final['counts'],'adverse_controls_passed':final['adverse_controls_passed']}
(root/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
raw=(root/'seal.json').read_bytes()
print(json.dumps({'seal_sha256':hashlib.sha256(raw).hexdigest(),'member_count':len(members),'member_bytes':total,'tree_sha256':tree}))
