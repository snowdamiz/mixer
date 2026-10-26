"""Freeze only reviewer-owned packet bytes; source/product code is never executed."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
members=[]
for path in sorted(HERE.rglob('*')):
    if path.is_file() and path.name!='seal.json':
        data=path.read_bytes()
        members.append({'path':path.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
seal={
    'schema':1,'at':datetime.now(timezone.utc).isoformat(),
    'status':'frozen independent source-only accounting review; no implementation acceptance or repair selection',
    'member_path_base':'repository-root',
    'command':[sys.executable,'-B',str(Path(__file__).resolve())],
    'python':sys.version,
    'owned_scope':['verification/swift-cache-state-accounting-independent-review/**'],
    'excluded':['verification/swift-cache-state-accounting-independent-review/seal.json'],
    'members':members,'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),
    'source_authority_sha256':'1ffc4ee5bb37c4ca2794c456f66bfcd9f1916090a0de3a548c19b6c82a3767b9',
    'parent_supplement_sha256':'7558f957bfe4b8cb62703b76e064f87d2e70a535cf5d61d55b826244c6770c77',
    'source_accounting_accepted':False,'repair_selected':False,
    'native_capture_ui_runtime_process_inventory_or_product_execution':False,
}
(HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'seal':str((HERE/'seal.json').relative_to(ROOT)),'sha256':hashlib.sha256((HERE/'seal.json').read_bytes()).hexdigest(),'members':len(members),'bytes':seal['member_bytes']}))
