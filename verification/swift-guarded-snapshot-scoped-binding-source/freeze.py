#!/usr/bin/env python3
"""Seal exactly owned packet files once, then make them read-only."""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
from prepare import HERE,row,sha,canonical,write

def main():
    assert sys.argv[1:]==['--seal']
    assert not (HERE/'seal.json').exists(), 'Never replace an immutable seal'
    assert not (HERE/'owned-work').exists()
    for name in ['compiler-positive','compiler-negative','mir-layout-review-final','source-and-evidence-tests']:
        receipt=json.loads((HERE/'commands'/name/'receipt.json').read_bytes())
        assert receipt['owned_group_absent'] and receipt['child_reaped']
        assert receipt['exit_code']==(1 if name=='compiler-negative' else 0)
    assert json.loads((HERE/'mir-comparison.json').read_bytes())['equality']
    members=[row(str(p.relative_to(HERE)),p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file()]
    seal=dict(schema=1,members=members,member_count=len(members),member_bytes=sum(x['bytes'] for x in members),
        tree_sha256=sha(canonical(members)),candidate_source_tree_sha256=json.loads((HERE/'source-manifest.json').read_bytes())['tree_sha256'],
        source_members=146,compiler_invocations=2,production_functions_compared=2020,
        all_production_mir_operations_and_layouts_preserved=True,actual_provider=False,selected_authority=False,
        pricing_rebind_complete_executable_closure=False,independent_review=False,product_test_native_runtime=False,
        native_OTA_FieldLog_GA=False,read_only_verifier='python3 -B '+str(HERE/'check.py')+' --read-only')
    write(HERE/'seal.json',seal)
    for p in HERE.rglob('*'):
        if p.is_file():p.chmod(0o444)
    for p in sorted((p for p in HERE.rglob('*') if p.is_dir()),reverse=True):p.chmod(0o555)
    HERE.chmod(0o555)
    print(json.dumps(dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),packet_tree_sha256=seal['tree_sha256'],member_count=len(members),read_only_files=True)))

if __name__=='__main__':main()
