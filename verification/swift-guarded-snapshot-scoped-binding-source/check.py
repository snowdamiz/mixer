#!/usr/bin/env python3
"""Read-only sealed source and evidence verifier; no compile/product execution."""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
from prepare import HERE,PROFILE,accepted_source,transform,manifest,query_source,row,sha,canonical
from review import derive

def verify():
    seal=json.loads((HERE/'seal.json').read_bytes())
    members=[row(str(p.relative_to(HERE)),p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json']
    assert members==seal['members']
    assert sha(canonical(members))==seal['tree_sha256']
    accepted,_=accepted_source();accepted[PROFILE],_=transform(accepted[PROFILE])
    candidate=json.loads((HERE/'source-manifest.json').read_bytes())
    assert manifest(accepted)==candidate
    for name,data in accepted.items():assert data==(HERE/'source/vm'/name).read_bytes()
    for mode in ['positive','negative']:
        assert manifest(query_source(accepted,mode))==json.loads((HERE/(mode+'-source-manifest.json')).read_bytes())
    for filename,result in zip(['mir-comparison.json','layouts.json','negative-results.json'],derive()):
        assert result==json.loads((HERE/filename).read_bytes())
    assert json.loads((HERE/'commands/source-and-evidence-tests/receipt.json').read_bytes())['exit_code']==0
    assert not (HERE/'owned-work').exists()
    return dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),packet_tree_sha256=seal['tree_sha256'],
        source_tree_sha256=candidate['tree_sha256'],members=len(members),source_members=146,
        source_reproduced=True,mir_layout_negative_evidence_reproduced=True,read_only=True,
        compiler_invocations=0,product_test_native_runtime=False,independent_review=False)

def main():
    assert sys.argv[1:]==['--read-only']
    print(json.dumps(verify(),sort_keys=True))

if __name__=='__main__':main()
