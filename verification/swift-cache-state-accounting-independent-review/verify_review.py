"""Read-only integrity and static proof-table verifier; no product execution."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
seal=json.loads((HERE/'seal.json').read_text())
for member in seal['members']:
    data=(ROOT/member['path']).read_bytes()
    assert len(data)==member['bytes'],member['path']
    assert hashlib.sha256(data).hexdigest()==member['sha256'],member['path']
assert seal['member_count']==len(seal['members'])
assert seal['member_bytes']==sum(m['bytes'] for m in seal['members'])
tables=json.loads((HERE/'operation-tables.json').read_text())
assert sum(x['scalar_units'] for x in tables['restore_core'])==18
assert sum(x['scalar_units'] for x in tables['commit_core'])==19
assert len(tables['actual_commit_endpoints'])==12
assert sum(x['conditional_groups'] for x in tables['built_publication_segments'])==657
assert 50+18+4+36+513+24==645
assert sum([256,2560,2568,768,640,640,248])==7680
assert 7680+471==8151<=8192
literal=json.loads((HERE/'literal-restore-review.json').read_text())
assert len(literal['endpoints'])==12
for i,row in enumerate(literal['endpoints']):
    assert row['destination_start']==888+8*i
    assert row['destination_end']==896+8*i
    assert row['source_start']==7729760+8*row['cell']
    assert row['source_end']==row['source_start']+8
verdict=json.loads((HERE/'verdict.json').read_text())
assert not verdict['implementation_accepted']
assert not verdict['complete_fix_selected']
assert verdict['tests_run']==0
print(json.dumps({'status':'frozen independent static review packet verified','members':seal['member_count'],'bytes':seal['member_bytes'],'tests_run':0}))
