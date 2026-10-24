from pathlib import Path
import hashlib,gzip,json
r=Path.cwd();v7=r/'verification/swift-calls-dispatch/v7-fixture-expectations';v6=r/'verification/swift-calls-dispatch/v6-fixture-expectation';h=json.loads((v7/'v6-history-bindings.json').read_bytes())['files'];p=v6/'inventory-v5.json';z=p.with_suffix(p.suffix+'.gz')
d=lambda x:hashlib.sha256(x).hexdigest();raw=p.read_bytes();packed=z.read_bytes();unpacked=gzip.decompress(packed)
assert unpacked==raw and len(raw)==h[p.name]['bytes']and d(raw)==h[p.name]['sha256'] and len(packed)==h[z.name]['bytes']and d(packed)==h[z.name]['sha256']
print(json.dumps({'logical':{'path':str(p.relative_to(r)),'sha256':d(raw),'bytes':len(raw)},'gzip':{'path':str(z.relative_to(r)),'sha256':d(packed),'bytes':len(packed)},'gzipExactOriginalBytes':unpacked==raw,'bothBoundInV7V6History':True},indent=2))
