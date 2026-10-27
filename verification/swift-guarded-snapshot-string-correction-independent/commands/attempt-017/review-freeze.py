#!/usr/bin/env python3
"""Freeze only this independent return. Never modifies any input or authority."""
import datetime,hashlib,json,sys
from pathlib import Path
import check
D=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 if (D/'seal.json').exists():raise SystemExit('already frozen')
 check.main();members=[]
 for p in sorted(D.rglob('*')):
  if p.is_symlink():raise ValueError('symlink')
  if not p.is_file():continue
  b=p.read_bytes();members.append({'path':str(p.relative_to(D)),'bytes':len(b),'sha256':sha(b)})
 receipts={}
 for p in sorted((D/'commands').glob('*/receipt.json')):
  r=json.loads(p.read_text());key=str(Path(r['argv'][2]).relative_to(D.parents[1]))+' '+' '.join(r['argv'][3:]);receipts[key.strip()]=str(p.relative_to(D))
 seal={'schema':1,'status':'frozen-independent-return-for-further-correction','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'member_count':len(members),'bytes':sum(m['bytes'] for m in members),'members':members,'candidate_seal_sha256':'4d2dcab90e7c9cfd7074a67fe8eac0d6807b6ed3704b74afe430ebc624b07994','source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','host_tree_sha256':'027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2','qualifying_or_adverse_receipts':receipts,'review_sha256':sha((D/'review.json').read_bytes()),'correction_contract_sha256':sha((D/'correction-contract.json').read_bytes()),'independent_adverse_failures':10,'actual_selected_header_discrepancies':6,'L_str_selected':False,'whole_host_bound_selected':False,'policy_or_operational_grant':False,'native_runtime_or_OTA_or_GA':False,'tool':{'python':sys.version,'executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),'argv':sys.argv,'scope':'pure host independent return freeze; no compiler/runtime/native/UI/capture/Git/global inventory'}}
 (D/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n');print(json.dumps({'seal_sha256':sha((D/'seal.json').read_bytes()),'members':len(members),'bytes':seal['bytes'],'status':seal['status']},sort_keys=True))
if __name__=='__main__':main()
