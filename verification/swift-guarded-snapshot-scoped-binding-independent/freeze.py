#!/usr/bin/env python3
"""One-shot seal of this owned independent packet only."""
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
from audit import HERE,SEAL,SOURCE_TREE,row,sha,canonical,require

require(sys.argv[1:]==['--freeze'],'one-shot --freeze only')
require(not (HERE/'seal.json').exists(),'packet already sealed')
members=[row(str(x.relative_to(HERE)),x.read_bytes()) for x in sorted(HERE.rglob('*')) if x.is_file()]
seal=dict(schema=1,members=members,member_count=len(members),member_bytes=sum(x['bytes'] for x in members),tree_sha256=sha(canonical(members)),
    status='independent-scoped-source-lifetime-and-retained-compiler-evidence-pass',
    candidate_seal_sha256=SEAL,candidate_source_tree_sha256=SOURCE_TREE,
    production_functions=2020,braced_const_static_anonymous_bodies=248,standalone_constants=1785,
    allocation_blocks=1953,distinct_allocation_ids=1459,production_constructs=6006,layouts=46,adversarial_controls=38,
    producer_4221_block_claim_requires_standalone_amendment=True,compiler_invocations=0,
    operational_provider_or_authority=False,whole_pricing_rebind_or_P0_funding=False,
    executable_closure_or_healthy_cleanup=False,native_FieldLog_OTA_GA=False)
(HERE/'seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
for path in HERE.rglob('*'):
    if path.is_file():path.chmod(0o444)
for path in sorted([x for x in HERE.rglob('*') if x.is_dir()],key=lambda x:len(x.parts),reverse=True):path.chmod(0o555)
HERE.chmod(0o555)
print(json.dumps(dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),member_count=len(members),member_bytes=seal['member_bytes'],tree_sha256=seal['tree_sha256'])))
