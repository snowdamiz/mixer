#!/usr/bin/env python3
"""Seal only this bounded audit after a successful exact-script receipt."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
def sha(raw): return hashlib.sha256(raw).hexdigest()
assert not (OUT/'seal.json').exists(), 'already sealed'
receipt=json.loads((OUT/'command-receipt.json').read_text())
assert receipt['exit_code']==0
assert receipt['audit_script_sha256']==sha((OUT/'audit.py').read_bytes())
for path,expected in receipt['outputs'].items():
    assert sha((OUT/path).read_bytes())==expected
for item in json.loads((OUT/'input-custody.json').read_text())['reads']:
    path=OUT.parent.parent/item['path']
    assert sha(path.read_bytes())==item['sha256']
freeze={'command':'python3 verification/swift-guarded-snapshot-encoder-work-audit/freeze.py',
        'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':platform.python_version(),
        'scope':'source work bound only; no original control/writer execution authorization',
        'fixed':14221,'block':'26+68I+39D+139W+Q','all_new_runtime_checks':'not run; paused',
        'cleanup':'No compiled artifacts, native instances, process inventories or capture activity created.'}
(OUT/'freeze-receipt.json').write_text(json.dumps(freeze,sort_keys=True,indent=2)+'\n')
members=[]
for path in sorted(OUT.rglob('*')):
    if path.is_file() and path.name!='seal.json':
        raw=path.read_bytes()
        members.append({'path':str(path.relative_to(OUT)),'bytes':len(raw),'sha256':sha(raw)})
seal={'schema':1,'member_count':len(members),'members':members,
      'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode()),
      'scope':freeze['scope']}
(OUT/'seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
print(json.dumps({'seal_sha256':sha((OUT/'seal.json').read_bytes()),
                  'tree_sha256':seal['tree_sha256'],'members':len(members)},sort_keys=True))
