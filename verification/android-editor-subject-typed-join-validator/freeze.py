#!/usr/bin/env python3
"""Freeze the bounded review packet once; refuses replacement."""
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def main():
    target=HERE/'seal.json'
    assert not target.exists(),'packet is immutable after release'
    receipt=json.loads((HERE/'receipt.json').read_text())
    members=[]
    for path in sorted(HERE.rglob('*')):
        if path.is_file():
            assert '__pycache__' not in path.parts
            data=path.read_bytes()
            members.append({'path':str(path.relative_to(HERE)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'frozen bounded host validator and focused association review; root selection pending',
        'policy_sha256':receipt['source_tree_identities']['policy_sha256'],
        'members':members,'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),
        'host_tests_passed':42,'editor_subjects':103,'historical_editor_replacements':9,
        'full_matrix':'pending','execution_closure':'pending','native':'pending','OTA':'pending','GA':'pending','qualified':False}
    target.write_text(json.dumps(seal,indent=2)+'\n')
    print(json.dumps({'seal_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'members':len(members),'bytes':seal['member_bytes'],'qualified':False}))

if __name__=='__main__':main()
