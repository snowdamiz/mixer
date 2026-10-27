"""Exact frozen input custody. No compiler query module is imported or executed."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL=ROOT/'verification/swift-guarded-snapshot-owned-provider-callee-interfaces'
REVIEW=ROOT/'verification/swift-guarded-snapshot-owned-provider-callee-independent'
TREE='acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'
def sha(b):return hashlib.sha256(b).hexdigest()
def need(x,s):
 if not x:raise ValueError(s)
def row(p):
 b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b)}
def load(p):return json.loads(p.read_bytes())
def roster():
 old=load(ORIGINAL/'input-lock.json');need(len(old['files'])==1245 and len(old['frozen_packets'])==15,'frozen original 1245 / 15')
 by={x['path']:x for x in old['files']};packets={x['path']:x for x in old['frozen_packets']}
 for packet,digest,count,total in [(ORIGINAL,'e98916beff1a3c8b912e96591fbd573b8d570aa38cc4390a13fa20658290dce0',230,14925640),(REVIEW,'050da55a398e839075dd841e81d4da580f74a97adf2d6346b0d8e44587680e16',90,6113083)]:
  raw=(packet/'seal.json').read_bytes();seal=json.loads(raw);need(sha(raw)==digest and len(seal['members'])==count and sum(x['bytes'] for x in seal['members'])==total,'original producer/review seal')
  info={'path':packet.relative_to(ROOT).as_posix(),'seal_sha256':digest,'members':count,'bytes':total};packets[info['path']]=info
 for info in packets.values():
  p=ROOT/info['path'];raw=(p/'seal.json').read_bytes();need(sha(raw)==info['seal_sha256'],'frozen packet seal');s=json.loads(raw)
  members={x['path'] for x in s['members']};actual={q.relative_to(p).as_posix() for q in p.rglob('*') if q.is_file() and '__pycache__' not in q.parts}
  need(actual==members|{'seal.json'},'complete frozen packet membership '+str(p))
  need(len(members)==info['members'] and sum(x['bytes'] for x in s['members'])==info['bytes'],'frozen packet envelope')
  by[row(p/'seal.json')['path']]=row(p/'seal.json')
  for r in s['members']:
   q=p/r['path'];a=row(q);need(a['bytes']==r['bytes'] and a['sha256']==r['sha256'],'frozen member '+str(q));by[a['path']]=a
 for name,digest in [('verification/swift-guarded-snapshot-owned-provider-callee-independent/correction-contract.json','85161323e1ea8d101dd71db0f0466d452d964a7b3f25ad80b209891e14fb6320'),('verification/swift-semantic-adapter-root-review/guarded-snapshot-owned-provider-callee-interfaces-return.json','d497b65fed7324ffa52b5a90a2c8b8c2bdd323c59a2a574a5b38d44667f0dc49')]:
  a=row(ROOT/name);need(a['sha256']==digest,'binding correction contract/root return');by[name]=a
 for r in by.values():need(row(ROOT/r['path'])==r,'frozen priced input drift '+r['path'])
 excluded=[]
 for p in old['frozen_packets']:
  folder=ROOT/p['path']
  excluded.extend(row(q) for q in folder.rglob('*') if q.is_file() and '__pycache__' in q.parts)
 expected=[{'path':'verification/swift-guarded-snapshot-source146-callee-storage-layouts/__pycache__/query-named.cpython-314.pyc','bytes':22721,'sha256':'2f9c1c9950e0ec3c6edd4b9a9439a96d3ecfade9a0e14c4bfdc2521b4c309b5a'}]
 need(excluded==expected,'inherited excluded cache metadata preserved untouched')
 fetch=HERE/'additional-official-source-custody.json'
 additional=[]
 if fetch.exists():
  x=load(fetch);need(x['revision']=='b940084d7eb6a299eb4bfeb8e34901bc051e7ac4','exact added source revision')
  additional.append(row(fetch))
  for r in x['members']:
   a=row(HERE/'official-source'/r['path']);need(a['bytes']==r['bytes'] and a['sha256']==r['sha256'],'added official source custody');additional.append(a)
 return {'schema':1,'source_tree_sha256':TREE,'rust_revision':old['rust_revision'],'inherited_priced_input_count':1245,'inherited_frozen_packet_count':15,'frozen_packets':sorted(packets.values(),key=lambda x:x['path']),'files':sorted(by.values(),key=lambda x:x['path'])+additional,'excluded_inherited_cache_metadata':excluded,'exclusion_policy':'Frozen producer derive.py:31 excludes __pycache__; excluded metadata is separately hashed, never imported or mutated.','mutable_PLAN_HEAD_priced':False}
