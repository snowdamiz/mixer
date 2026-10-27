#!/usr/bin/env python3
"""Seal/check only this owned independent-review packet."""
import hashlib
import json
from pathlib import Path
import platform
import sys

here=Path(__file__).resolve().parent
members=[]
for path in sorted(here.rglob('*')):
    if not path.is_file() or path==here/'seal.json':
        continue
    if path.is_symlink():
        raise SystemExit('symlinks forbidden')
    raw=path.read_bytes()
    members.append({'path':path.relative_to(here).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
review=json.loads((here/'review.json').read_text())
seal={'schema':1,'status':'frozen-independent-source146-P0-account-surface-transfer-only','members':members,'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'checks':review['checks'],'source_members':146,'source_tree_sha256':review['source_tree_sha256'],'formula':review['formula'],'compiler_or_product_runtime':False,'selected_I_U_root_policy_fixture_or_grant':False,'complete_P0_or_host_quote':False,'P5_actual_payload_destruction_required_nonzero':True,'python':platform.python_version()}
raw=(json.dumps(seal,indent=2,sort_keys=True)+'\n').encode()
if '--check-only' in sys.argv:
    if (here/'seal.json').read_bytes()!=raw:
        raise SystemExit('seal mismatch')
else:
    (here/'seal.json').write_bytes(raw)
print(json.dumps({'passed':True,'members':len(members),'member_bytes':seal['member_bytes'],'seal_sha256':hashlib.sha256(raw).hexdigest(),'checks':review['checks']}))
