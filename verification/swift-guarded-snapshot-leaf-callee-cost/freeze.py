#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest()
if (H/'seal.json').exists():raise SystemExit('already frozen')
r=json.loads((H/'verification-results.json').read_text())
if (r['test_methods'],r['failures'],r['errors'],r['required_input_negative_cases'])!=(20,0,0,616):raise ValueError('controls incomplete')
ms=[dict(path=str(p.relative_to(H)),bytes=len(p.read_bytes()),sha256=sha(p.read_bytes())) for p in sorted(H.rglob('*')) if p.is_file() and p!=H/'seal.json']
seal=dict(schema=1,status='bounded-source146-callee-pricing-candidate-pending-independent-review',member_count=len(ms),members=ms,tree_sha256=sha(json.dumps(ms,sort_keys=True,separators=(',',':')).encode()),source_tree_sha256=r.get('source_tree_sha256','690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'),complete_host_quote=False,actual_runtime=False)
(H/'seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(path=str(H),seal_sha256=sha((H/'seal.json').read_bytes()),members=len(ms),bytes=sum(r['bytes'] for r in ms))))
