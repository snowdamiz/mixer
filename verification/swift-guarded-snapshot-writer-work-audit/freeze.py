#!/usr/bin/env python3
"""Freeze/check only this compact source-work proposal; never run an engine."""
from pathlib import Path
import hashlib,json,sys

HERE=Path(__file__).resolve().parent
ROSTER=[
 'README.md','cost-convention.md','ledger.json','audit.py','source-bindings.json',
 'results.json','command-receipt.json','freeze.py',
 'attempt-history/001-provisional-ledger.json','attempt-history/001-correction.json',
 'attempt-history/002-before-wrapper-and-binding-correction.json','attempt-history/002-correction.json',
 'attempt-history/003-pre-review-seal.json','attempt-history/003-text-correction.json',
]
def digest(raw):return hashlib.sha256(raw).hexdigest()
def main():
 actual=sorted(str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file()
               and p.name not in ('seal.json','freeze-receipt.json'))
 assert actual==sorted(ROSTER),('unexpected/missing member',actual)
 members=[]
 for name in sorted(ROSTER):
  raw=(HERE/name).read_bytes()
  members.append({'path':name,'bytes':len(raw),'sha256':digest(raw)})
 canonical=json.dumps(members,sort_keys=True,separators=(',',':')).encode()
 seal={'schema':1,'member_count':len(members),'members':members,
       'tree_sha256':digest(canonical),
       'scope':'writer/control/wrapper source logical-work proposal; Python finite models only; independent review and full operational selection pending'}
 if '--check' in sys.argv:
  assert json.loads((HERE/'seal.json').read_text())==seal,'frozen member drift'
 else:
  (HERE/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
  raw=(HERE/'seal.json').read_bytes()
  (HERE/'freeze-receipt.json').write_text(json.dumps({'schema':1,'seal_bytes':len(raw),
     'seal_sha256':digest(raw),'member_count':len(members),'tree_sha256':seal['tree_sha256'],
     'operational_work_selected':False,'WorkAuditPending_preserved':True,
     'native_or_writer_execution':False,'GA_gates_verified':0},indent=2,sort_keys=True)+'\n')
 print(json.dumps({'verified_members':len(members),'tree_sha256':seal['tree_sha256'],
                   'seal_sha256':digest((HERE/'seal.json').read_bytes())},sort_keys=True))
if __name__=='__main__':main()
