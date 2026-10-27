#!/usr/bin/env python3
"""Freeze only the separate original495 correction; source-only evidence."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
ROSTER=['README.md','correct.py','corrected-ledger.json','ledger-diff.json',
        'input-custody.json','source-bindings.json','results.json','commands.json','freeze.py']
def sha(raw):return hashlib.sha256(raw).hexdigest()
actual=sorted(str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file()
              and p.name not in ('seal.json','freeze-receipt.json'))
assert actual==sorted(ROSTER),actual
members=[]
for name in sorted(ROSTER):
 raw=(HERE/name).read_bytes();members.append({'path':name,'bytes':len(raw),'sha256':sha(raw)})
tree=sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())
seal={'schema':1,'member_count':len(members),'member_bytes':sum(x['bytes'] for x in members),
      'members':members,'tree_sha256':tree,
      'scope':'Separate original495 writer/control ledger correction W1/W2/W3; no product source delta or later225 authority candidate; independent correction review and operational selection pending'}
if '--check' in sys.argv:assert json.loads((HERE/'seal.json').read_text())==seal
else:
 (HERE/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
 (HERE/'freeze-receipt.json').write_text(json.dumps({'schema':1,
    'seal_sha256':sha((HERE/'seal.json').read_bytes()),'tree_sha256':tree,
    'member_count':len(members),'source_delta':False,'WorkAuditPending_preserved':True,
    'operational_work_selected':False,'later225_authority_candidate_included':False,
    'engine_runtime_native_or_UI_executed':False},indent=2,sort_keys=True)+'\n')
print(json.dumps({'members_verified':len(members),'tree_sha256':tree,
   'seal_sha256':sha((HERE/'seal.json').read_bytes())},sort_keys=True))
