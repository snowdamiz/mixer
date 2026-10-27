#!/usr/bin/env python3
"""Independent full membership/byte rehash, immutable data only."""
import gzip,hashlib,json,sys
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(j):return json.dumps(j,sort_keys=True,separators=(',',':')).encode()
def require(v,m):
 if not v:raise ValueError(m)
def check_packet(name,pin,count,size):
 p=V/name;raw=(p/'seal.json').read_bytes();require(sha(raw)==pin,'seal:'+name);j=json.loads(raw);rows=j['members'];actual=set()
 for f in p.rglob('*'):
  require(not f.is_symlink(),'symlink:'+str(f))
  if f.is_file() and f.name!='seal.json':actual.add(str(f.relative_to(p)))
 require(actual=={m['path'] for m in rows},'membership:'+name)
 for m in rows:
  path=Path(m['path']);require(not path.is_absolute() and '..' not in path.parts,'member-path')
  b=(p/path).read_bytes();require(len(b)==m['bytes'] and sha(b)==m['sha256'],'member:'+name+'/'+str(path))
 require(len(rows)==count and sum(m['bytes'] for m in rows)==size,'count:'+name)
 return {'seal_sha256':pin,'members':count,'bytes':size,'complete_membership':True,'all_bytes_rehashed':True}
def main():
 packets={}
 for name,pin,count,size in [('swift-guarded-snapshot-string-provenance-correction','4d2dcab90e7c9cfd7074a67fe8eac0d6807b6ed3704b74afe430ebc624b07994',358,56817849),('swift-guarded-snapshot-string-provenance-independent','741e104537fc3ddc57fc499a764cca9fedaa2b42d2fe109eeb590504b01241d9',108,6581268),('swift-guarded-snapshot-string-provenance','b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f',114,6305257)]:packets[name]=check_packet(name,pin,count,size)
 pins={'swift-semantic-adapter-root-review/guarded-snapshot-string-provenance-correction-frozen-release.json':'26d3c91aa535452ccb80b63f1d0bca8987b6e8c4688f1b283b57ff2ab13c7bc2','swift-semantic-adapter-root-review/guarded-snapshot-string-provenance-review-return.json':'142648fc21ef7e9dcd36b3e7849b17a18f7a94cc2ac2c6b848c362140fea668b','swift-guarded-snapshot-string-provenance-independent/correction-contract.json':'b699930771cb7980b1ced76867c4d8a9760014be80c7fa63e4057145e6883341'}
 for p,h in pins.items():require(sha((V/p).read_bytes())==h,'root/contract:'+p)
 c=V/'swift-guarded-snapshot-string-provenance-correction';bindings=json.loads((c/'input-bindings.json').read_text())['files']
 for p,m in bindings.items():
  b=(R/p).read_bytes();require(len(b)==m['bytes'] and sha(b)==m['sha256'],'input:'+p)
 base=V/'swift-guarded-snapshot-loader-work-source146';manifest=json.loads((base/'source146-manifest.json').read_text());refs=json.loads((base/'source-reference-map.json').read_text());source='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185';host='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
 require(len(manifest['members'])==146 and sha(canonical(manifest['members']))==source,'source146-tree')
 for m in refs['members']:
  b=(R/m['source']).read_bytes();require(len(b)==m['bytes'] and sha(b)==m['sha256'],'actual-source:'+m['path'])
 hm=json.loads((base/'host11-manifest.json').read_text());require(len(hm['members'])==11 and sha(canonical(hm['members']))==host,'host11-tree')
 for m in hm['members']:
  b=(V/'swift-real-profile-loader-binding/host'/m['path']).read_bytes();require(len(b)==m['bytes'] and sha(b)==m['sha256'],'host-file')
 receipt=json.loads((base/'compiler-receipt.json').read_text());archive=(base/'whole-source146.mir.gz').read_bytes();raw=gzip.decompress(archive)
 require(sha(archive)==receipt['MIR']['archive_sha256'] and len(archive)==receipt['MIR']['archive_bytes'],'archive');require(sha(raw)==receipt['MIR']['raw_sha256'] and len(raw)==receipt['MIR']['raw_bytes'],'retained-MIR')
 failures={}
 for name in ('producer-006','producer-007','independent-adverse-006'):
  p=c/'history'/name;r=json.loads((p/'receipt.json').read_text());require(r['exit_code']==1,'failure-preserved:'+name);failures[name]={'exit_code':1,'receipt_sha256':sha((p/'receipt.json').read_bytes())}
 newfailed=[p.parent.name for p in sorted((c/'commands').glob('*/receipt.json')) if json.loads(p.read_text())['exit_code']!=0];require(newfailed==[f'attempt-{i:03d}' for i in [1,2,3,4,5,6,7,8,13]],'nine-new-failures')
 j={'schema':1,'packets':packets,'root_and_contract_pins':pins,'input_files':len(bindings),'source_tree_sha256':source,'host_tree_sha256':host,'MIR_raw_sha256':sha(raw),'MIR_raw_bytes':len(raw),'original_failures':failures,'new_failed_attempts_retained':newfailed,'scope':'complete immutable member/input source rehash, no compiler executed','passed':True}
 if '--check' in sys.argv:require(json.loads((D/'custody.json').read_text())==j,'review-custody-exact')
 else:(D/'custody.json').write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:j[k] for k in ('passed','input_files','MIR_raw_bytes','source_tree_sha256','new_failed_attempts_retained')},sort_keys=True))
if __name__=='__main__':main()
