"""Independent review pins and complete read-only input inventories."""
import gzip, hashlib, json
from pathlib import Path
D=Path(__file__).resolve().parent; R=D.parents[1]; V=R/'verification'
C=V/'swift-guarded-snapshot-string-exact-binding-correction'
S=V/'swift-guarded-snapshot-loader-work-source146'
SOURCE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
PACKETS=(('swift-guarded-snapshot-string-provenance','b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f',114,6305257),('swift-guarded-snapshot-string-provenance-independent','741e104537fc3ddc57fc499a764cca9fedaa2b42d2fe109eeb590504b01241d9',108,6581268),('swift-guarded-snapshot-string-provenance-correction','4d2dcab90e7c9cfd7074a67fe8eac0d6807b6ed3704b74afe430ebc624b07994',358,56817849),('swift-guarded-snapshot-string-correction-independent','7c101623fa53d9207c467f196cca729085fff23a195f873a46da7a1369135f65',248,6817047),('swift-guarded-snapshot-string-exact-binding-correction','4eb0437b5ed1f7ec056340ffac08a0221cfd5f6f216a9d3aebb6fd4d25cc5f4b',895,70066404))
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,why):
 if not ok:raise ValueError(why)
def encoded(v):return (json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
def save(name,data):
 raw=encoded(data)
 if '--check' in __import__('sys').argv:need((D/name).read_bytes()==raw,'review reproduction:'+name)
 else:
  need(not (D/'seal.json').exists(),'frozen review');(D/name).write_bytes(raw)
def inventory():
 seen={}
 def read(p,expected=None):
  need(not p.is_symlink(),'symlink:'+str(p));b=p.read_bytes();v={'bytes':len(b),'sha256':sha(b)}
  if expected is not None:need(v==expected,'changed input:'+str(p))
  seen[str(p.relative_to(R))]=v;return b
 for name,digest,count,size in PACKETS:
  base=V/name;b=read(base/'seal.json');need(sha(b)==digest,'seal:'+name);seal=json.loads(b);names=[]
  for m in seal['members']:
   q=Path(m['path']);need(not q.is_absolute() and '..' not in q.parts,'member path');names.append(str(q));read(base/q,{k:m[k] for k in ('bytes','sha256')})
  need(len(names)==len(set(names))==count and sum(m['bytes'] for m in seal['members'])==size,'member count/bytes')
  need({str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()}==set(names)|{'seal.json'},'complete membership:'+name)
 bindings=json.loads(read(C/'input-bindings.json'))['files']
 for name,e in bindings.items():read(R/name,e)
 for name in ('source146-manifest.json','host11-manifest.json','source-reference-map.json','compiler-receipt.json','whole-source146.mir.gz'):read(S/name)
 for name,digest in [('guarded-snapshot-string-exact-binding-frozen-release.json','0db523c86614cc925a532a857a0ca3e64eab89c337308830386569106f2ceec6'),('guarded-snapshot-string-correction-second-return.json','9dba765988b0e464fe58245520586696945e9f4bbd87f1ca2b8bc4051cf68440')]:need(sha(read(V/'swift-semantic-adapter-root-review'/name))==digest,'root receipt:'+name)
 for name,digest,count in [('source146-manifest.json',SOURCE,146),('host11-manifest.json',HOST,11)]:
  m=json.loads((S/name).read_text())['members'];need(len(m)==count and sha(json.dumps(m,sort_keys=True,separators=(',',':')).encode())==digest,'tree identity')
 ref=json.loads((S/'source-reference-map.json').read_text())
 for m in ref['members']:read(R/m['source'],{k:m[k] for k in ('bytes','sha256')})
 for m in json.loads((S/'host11-manifest.json').read_text())['members']:read(V/'swift-real-profile-loader-binding/host'/m['path'],{k:m[k] for k in ('bytes','sha256')})
 raw=gzip.decompress((S/'whole-source146.mir.gz').read_bytes());rec=json.loads((S/'compiler-receipt.json').read_text())['MIR'];need(sha(raw)==rec['raw_sha256'] and len(raw)==rec['raw_bytes'],'raw MIR custody')
 return seen
def inputs():
 refs=json.loads((S/'source-reference-map.json').read_text())
 source={m['path']:(R/m['source']).read_text() for m in refs['members'] if m['path'].endswith('.rs')}
 return gzip.decompress((S/'whole-source146.mir.gz').read_bytes()).decode(),source
