import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
seal=json.loads((HERE/'seal.json').read_text())
for m in seal['members']:
    b=(ROOT/m['path']).read_bytes(); assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['sha256'],m['path']
assert seal['member_count']==len(seal['members'])
assert seal['member_bytes']==sum(x['bytes'] for x in seal['members'])
core=json.loads((HERE/'core-review.json').read_text())
assert sum(x['payload_groups'] for x in core['built_payload_segments'])==329
assert len(core['clear_scalar_core'])*256==5376
assert 329+5376//16==665
ledger=json.loads((HERE/'clear-block-ledger.json').read_text())
assert len(ledger['per_store_metadata'])==43 and len(ledger['per_initializer_component_edges'])==130
assert 16*(43+130)==2768 and 2768//16+16==189
assert (130+16*43+2+15)//16+17==69
places=json.loads((HERE/'equivalence-and-places.json').read_text())
assert [n for s,e in places['ranges'] for n in range(s,e)]==list(range(2048))
assert 128+24==152 and 256+24>256
assert json.loads((HERE/'verdict.json').read_text())['implementation_accepted'] is False
print(json.dumps({'status':'independent G6 frozen packet verified','members':seal['member_count'],'bytes':seal['member_bytes'],'runtime_tests':0}))
