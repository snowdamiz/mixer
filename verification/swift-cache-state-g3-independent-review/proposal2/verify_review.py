import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
seal=json.loads((HERE/'seal.json').read_text())
for m in seal['members']:
    b=(ROOT/m['path']).read_bytes()
    assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['sha256'],m['path']
assert len(seal['members'])==seal['member_count']
assert sum(x['bytes'] for x in seal['members'])==seal['member_bytes']
ops=json.loads((HERE/'operation-review.json').read_text())
assert sum(x['scalar_units'] for x in ops['independent_operations'])==64
assert len(set(ops['ordered_scalar_stream']))==64
assert [x for b in ops['scalar_blocks'] for x in b['operations']]==ops['ordered_scalar_stream']
assert all(len(b['operations'])==16 for b in ops['scalar_blocks'])
assert len(ops['payload_copies'])==4
assert ops['path_counts']=={'B_absent':{'scalars':33,'copies':2},'A_absent_B_eligible':{'scalars':35,'copies':2},'both_eligible':{'scalars':64,'copies':4}}
assert json.loads((HERE/'verdict.json').read_text())['final_G3_bound_accepted'] is False
print(json.dumps({'status':'independent proposal2 frozen packet verified','members':seal['member_count'],'bytes':seal['member_bytes'],'runtime_tests':0}))
