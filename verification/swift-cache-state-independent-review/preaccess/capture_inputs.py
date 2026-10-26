"""Reviewer-owned closed data capture. Never imports or executes consulted code."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ACCEPT = 'verification/swift-semantic-adapter-root-review/combined-contract-acceptance.json'
ACCEPT_SHA = 'aac275052af88c802b0594c2d47318898d383b90f20d99a3914a4080c1a76dcc'
SEALS = [
 ('verification/swift-semantic-adapter-prerequisite/seal.json','d145cda8cdde0915493f5c75102ae0dc11adb577891b1b773322b5c4d0f32cba'),
 ('verification/swift-semantic-adapter-contract-review/preaccess/seal.json','7ae911b982f2bf96f596969c2c282bd5bbdd7302033a6d1404278f1df23d9ae9'),
 ('verification/swift-semantic-adapter-contract-review/review-1/seal.json','d44b2edd19961ebeda7e197f549433e7a0d7f0630ce7d501e5465044340c6c02'),
 ('verification/swift-semantic-adapter-terminal-correction/seal.json','efa9288096a692780e195ac519ffb7ed0be1280a974e830d80fc9932d194aef7'),
 ('verification/swift-semantic-adapter-terminal-review/preaccess/seal.json','b71097292535a76631d787121c60e315f91343ed6da8c71fec9303cf9328e681'),
 ('verification/swift-semantic-adapter-terminal-review/review-1/seal.json','87428e8a867993a32b72579a7c8b5c19df5ae2e5da365707ab22e4cd2b4167d4'),
]
DATA = ['AGENTS.md','PLAN.md','mixer-product-plan.md',ACCEPT,
 'docs/swift-semantic-adapter-prerequisite.md','docs/swift-semantic-adapter-terminal-correction.md',
 'docs/swift-semantic-adapter-contract-review.md','docs/swift-semantic-adapter-terminal-review.md']
P = 'verification/swift-semantic-adapter-prerequisite/'
DATA += [P + n for n in ['contract.json','test-design.json','source-seams.json','input-manifest.json',
 'inputs/05-swift-ordered-retention-analyzer.md','inputs/07-swift-ordered-retention-analyzer-fsm-contract.md',
 'inputs/13-analyzer.rs','inputs/14-envelope.rs','inputs/23-candidate__src__experimental__cache__borrowed.rs',
 'inputs/24-candidate__src__experimental_swift_reactor__cache.rs',
 'inputs/25-verification__swift-ordered-retention-diagnostic-rust__writer.rs',
 'inputs/26-verification__swift-ordered-retention-diagnostic-rust__observer.rs']]
DATA += ['verification/swift-semantic-adapter-terminal-correction/'+n for n in
 ['terminal-contract.json','source-bindings.json','expected-cases.json','source-normalization-cases.json']]

def sha(b): return hashlib.sha256(b).hexdigest()
def write_json(path, value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def main():
 if sha((ROOT/ACCEPT).read_bytes()) != ACCEPT_SHA: raise ValueError('root acceptance identity')
 members={}; packets=[]
 for name, expected in SEALS:
  source=ROOT/name; raw=source.read_bytes()
  if sha(raw)!=expected: raise ValueError(name)
  seal=json.loads(raw); total=0
  for m in seal['members']:
   p=ROOT/m['path'] if m['path'].startswith(('verification/','docs/')) else source.parent/m['path']
   b=p.read_bytes(); digest=sha(b)
   if digest!=m['sha256'] or len(b)!=m['bytes']: raise ValueError(str(p))
   rel=str(p.relative_to(ROOT)); prior=members.get(rel)
   if prior and prior!=m: raise ValueError('inconsistent member identity')
   members[rel]={'path':rel,'bytes':len(b),'sha256':digest}; total+=len(b)
  declared=seal.get('member_bytes',seal.get('total_bytes'))
  if len(seal['members'])!=seal['member_count'] or total!=declared: raise ValueError('declared totals')
  packets.append({'path':name,'sha256':expected,'members':len(seal['members']),'bytes':total})
  dst=OUT/'inputs'/name; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(raw)
 if len(members)!=651 or sum(m['bytes'] for m in members.values())!=4801337: raise ValueError('combined totals')
 selected=[]
 for rel in DATA:
  b=(ROOT/rel).read_bytes(); dst=OUT/'inputs'/rel
  dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(b)
  selected.append({'path':rel,'snapshot':str(dst.relative_to(OUT)),'bytes':len(b),'sha256':sha(b),
    'authority':'current context only' if rel in DATA[:3] else 'accepted immutable data; not executed'})
 write_json(OUT/'input-custody.json',{'schema':1,'packets':packets,'unique_members':len(members),
  'unique_bytes':sum(m['bytes'] for m in members.values()),'verified_members':list(members.values()),
  'selected_snapshots':selected,'new_producer_source_accessed':False,'consulted_code_imported_or_executed':False})
 print(json.dumps({'packets':len(packets),'members':len(members),'bytes':4801337,'snapshots':len(selected)}))

if __name__=='__main__': main()
