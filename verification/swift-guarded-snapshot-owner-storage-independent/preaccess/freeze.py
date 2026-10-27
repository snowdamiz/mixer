"""Seal only this preaccess directory after its source/method controls pass."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
receipt=json.loads((HERE/'receipt.json').read_text())
assert receipt['status']=='ready for frozen owner/caller producer release'
assert len(receipt['finite_review_controls'])==22 and all(receipt['finite_review_controls'].values())
assert receipt['producer_packet_accessed'] is False
assert receipt['source_tree_sha256']=='575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896'
members=[]
for path in sorted(HERE.iterdir()):
    if path.is_file() and path.name!='seal.json':
        data=path.read_bytes()
        members.append(dict(path=path.name,bytes=len(data),sha256=sha(data)))
seal=dict(schema=1,members=members,member_count=len(members),total_bytes=sum(m['bytes'] for m in members),
          scope='Independent owner/caller preaccess method and source expectations frozen before producer access; no final inventory/floor/runtime acceptance')
(HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
for member in members:
    data=(HERE/member['path']).read_bytes()
    assert len(data)==member['bytes'] and sha(data)==member['sha256']
print(json.dumps(dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),members=len(members),bytes=seal['total_bytes'])))
