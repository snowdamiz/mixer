"""One-shot freeze of the owned independent review, never a producer writer."""
import json
from common import *
def main():
 need(not (D/'seal.json').exists(),'already frozen')
 import check;check.main();members=[]
 for p in sorted(D.rglob('*')):
  if p.is_file():
   need(not p.is_symlink(),'member symlink');raw=p.read_bytes();members.append({'path':str(p.relative_to(D)),'bytes':len(raw),'sha256':sha(raw)})
 seal={'schema':1,'status':'frozen-independent-bounded-source146-exact-binding-review','candidate_seal_sha256':PACKETS[-1][1],'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,'member_count':len(members),'bytes':sum(m['bytes'] for m in members),'members':members,'L_str_selected':False,'policy_or_operational_grant_or_OTA_or_GA':False,'native_or_compiler_or_product_execution':False,'future_changed_source_covered':False}
 (D/'seal.json').write_bytes(encoded(seal))
 for p in D.rglob('*'):
  if p.is_file():p.chmod(0o444)
 for p in sorted((p for p in D.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):p.chmod(0o555)
 D.chmod(0o555);print(json.dumps({'seal_sha256':sha((D/'seal.json').read_bytes()),'members':seal['member_count'],'bytes':seal['bytes'],'read_only':True},sort_keys=True))
if __name__=='__main__':main()
