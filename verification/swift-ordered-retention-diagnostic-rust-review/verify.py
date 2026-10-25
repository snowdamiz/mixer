"""Read-only integrity audit; executes no archived product code."""
from pathlib import Path
import hashlib,json,re,tarfile
P=Path(__file__).resolve().parent;R=P.parents[1];F=P.parent/'swift-ordered-retention-diagnostic-rust'
def sha(b):return hashlib.sha256(b).hexdigest()
sealraw=(P/'seal.json').read_bytes();assert sha(sealraw)==(P/'seal.sha256').read_text().strip();seal=json.loads(sealraw)
for e in seal['members']:
 p=R/e['path'];assert p.is_file() and not p.is_symlink();b=p.read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'],e['path']
assert sha((F/'seal.json').read_bytes())=='c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf'
for e in json.loads((F/'seal.json').read_bytes())['members']:
 b=(R/e['path']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256']
base=json.loads((F/'baseline-source-manifest.json').read_bytes());assert {n:sha((R/'vm'/n).read_bytes())for n in base}==base
for d in (P/'commands').iterdir():
 r=json.loads((d/'result.json').read_bytes())
 for n,v in r['outputs'].items():
  raw=(d/(n+'.txt')).read_bytes();assert len(raw)==v['bytes'] and sha(raw)==v['sha256']
manifest=json.loads((P/'raw-review-fixtures-manifest.json').read_bytes())
with tarfile.open(P/'raw-review-fixtures.tar.gz','r:gz')as t:
 assert sorted(t.getnames())==sorted(manifest)
 for m in t:
  assert m.isfile();raw=t.extractfile(m).read();assert len(raw)==manifest[m.name]['bytes'] and sha(raw)==manifest[m.name]['sha256']
assert json.loads((P/'cleanup.json').read_bytes())['scratchRemoved'] and not(P/'.scratch').exists()
assert json.loads((P/'custody-adversity.json').read_bytes())['falseValidMalformedCases']==3
assert json.loads((P/'custody-inventory.json').read_bytes())['missingNamedFileIOOwnerBytes']==64
private=[(P/f'commands/{s}-generic-private/stdout.txt').read_bytes()for s in ['baseline','candidate']];assert private[0]==private[1]
integration=[(P/f'commands/{s}-generic-integration/stdout.txt').read_bytes()for s in ['baseline','candidate']];assert integration[0]!=integration[1]
assert re.sub(rb'finished in [0-9.]+s',b'finished in <elapsed>s',integration[0])==re.sub(rb'finished in [0-9.]+s',b'finished in <elapsed>s',integration[1])
print(json.dumps({'sealedReviewMembers':len(seal['members']),'producerSealVerified':True,'live132Unchanged':True,'scratchRemoved':True,'status':'finite feasibility supported; complete Rust diagnostic not accepted'},sort_keys=True))
