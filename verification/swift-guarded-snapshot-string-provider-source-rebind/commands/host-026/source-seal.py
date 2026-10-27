"""Seal or read-only check this owned packet; no upstream file is written."""
from common import *
def members():
 out=[]
 for p in sorted(D.rglob('*')):
  require(not p.is_symlink(),'packet symlink')
  if p.is_file() and p.name!='seal.json':out.append(row(p.relative_to(D),p.read_bytes()))
 return out
def main():
 rows=members();seal={'schema':1,'source_tree_sha256':TREES[3],'members':rows,'member_count':len(rows),'member_bytes':sum(r['bytes'] for r in rows),'member_table_sha256':sha(canon(rows)),'scope':'candidate for fresh independent review; conditional source/MIR conservation only; no L_str/current caller/whole-host/OTA/GA authority'}
 if '--check' in sys.argv:require(load(D/'seal.json')==seal,'complete candidate seal membership')
 else:
  require(not (D/'seal.json').exists(),'seal only once');save('seal.json',seal)
  for p in D.rglob('*'):
   if p.is_file():p.chmod(0o444)
  for p in sorted([p for p in D.rglob('*') if p.is_dir()],reverse=True):p.chmod(0o555)
  D.chmod(0o555)
 print(json.dumps({'seal_sha256':sha((D/'seal.json').read_bytes()),'members':len(rows),'bytes':sum(r['bytes'] for r in rows)}))
if __name__=='__main__':main()
