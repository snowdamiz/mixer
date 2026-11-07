import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
seal=json.loads((HERE/'seal.json').read_text())
for m in seal['members']:
    b=(ROOT/m['path']).read_bytes()
    assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['sha256'],m['path']
assert seal['member_count']==len(seal['members'])
assert seal['member_bytes']==sum(x['bytes'] for x in seal['members'])
table=json.loads((HERE/'operation-table.json').read_text())
for load in table['loads']:
    assert sum(x['scalar_units'] for x in load['operations'])==16
assert sum(sum(x['scalar_units'] for x in load['operations']) for load in table['loads'])==64
assert sum(x['scalar_units'] for x in table['comparison_operations'])==6
assert 64+6==70>4*16
assert 4+(70+15)//16==9
paths=json.loads((HERE/'path-and-boundary-table.json').read_text())['paths']
for p in paths:
    assert p['G3_payload_copies']==len(p['G3_loads'])
assert paths[-1]['G3_scalar_core']==70
assert not json.loads((HERE/'verdict-and-options.json').read_text())['implementation_accepted']
proposal=json.loads((HERE/'proposal-disposition.json').read_text())
core=proposal['independent_conservative_core']
assert len(core['operations'])==64
assert len(core['ordered_operations'])==64
assert len(set(core['ordered_operations']))==64
assert set(core['ordered_operations'])==set(core['operations'])
assert all(len(block['operations'])==16 for block in core['scalar_blocks'])
assert [op for block in core['scalar_blocks'] for op in block['operations']]==core['ordered_operations']
assert core['path_core_totals']=={'B_absent':33,'A_absent_B_eligible':35,'both_eligible':64}
assert core['complete_upper_bound'] is False
assert proposal['remaining_explicit_source_edges'][0]['conditional_total_with_core']==68
assert proposal['cost_bound_accepted'] is False
print(json.dumps({'status':'frozen independent G3 packet verified','members':seal['member_count'],'bytes':seal['member_bytes'],'runtime_tests':0}))
