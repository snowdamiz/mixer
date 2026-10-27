#!/usr/bin/env python3
"""Read-only independent packet custody and reproducibility check."""
import json
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode=True
from audit import HERE,C,SEAL,SOURCE_TREE,derive,read,row,sha,canonical,require

def verify():
    seal=read(HERE/'seal.json')
    files=sorted(x for x in HERE.rglob('*') if x.is_file() and x.name!='seal.json')
    require(not any(x.is_symlink() for x in HERE.rglob('*')),'independent packet symlink')
    rows=[row(str(x.relative_to(HERE)),x.read_bytes()) for x in files]
    require(rows==seal['members'],'independent sealed membership')
    require(sha(canonical(rows))==seal['tree_sha256'],'independent sealed tree')
    require(all(stat.S_IMODE(x.stat().st_mode)==0o444 for x in files+[HERE/'seal.json']),'independent file modes')
    require(all(stat.S_IMODE(x.stat().st_mode)==0o555 for x in [HERE]+[y for y in HERE.rglob('*') if y.is_dir()]),'independent directory modes')
    report=derive()
    require(report==read(HERE/'report.json')==read(HERE/'commands/independent-review-final/stdout'),'independent full audit reproduction')
    require(report['standalone_constants_completeness_amendment']==read(HERE/'standalone-constants.json'),'complete standalone inventory')
    scripts={
        'independent-review-initial':HERE/'attempts/initial-audit.py',
        'independent-review-second':HERE/'attempts/second-audit.py',
        'independent-review-complete':HERE/'attempts/complete-audit.py',
        'independent-review-final':HERE/'audit.py',
        'producer-read-only-check':C/'check.py',
    }
    for name,script in scripts.items():
        output=HERE/'commands'/name;plan=read(output/'plan.json');receipt=read(output/'receipt.json')
        require(all(receipt[k]==v for k,v in plan.items()),'host command plan/receipt')
        require(receipt['script_sha256']==sha(script.read_bytes()),'host command script preimage '+name)
        require(receipt['exit_code']==(1 if name=='independent-review-initial' else 0),'host command terminal status')
        for key in ('child_reaped','owned_group_absent'):require(receipt[key],'host command cleanup '+name)
        for key in ('timed_out','product_test_native_runtime','global_process_inventory','owned_scratch_created'):require(not receipt[key],key)
        require(receipt['compiler_invocations']==0 and receipt['elapsed_seconds']<55,'host scope/bounds')
        for stream in ('stdout','stderr'):
            data=(output/stream).read_bytes()
            require(sha(data)==receipt[stream+'_sha256'] and len(data)==receipt[stream+'_bytes'],'host command stream')
    return dict(schema=1,status='independent-read-only-sealed-review-reproduced',seal_sha256=sha((HERE/'seal.json').read_bytes()),
        tree_sha256=seal['tree_sha256'],members=len(rows),member_bytes=sum(x['bytes'] for x in rows),
        candidate_seal_sha256=SEAL,candidate_source_tree_sha256=SOURCE_TREE,
        production_functions=2020,braced_const_static_anonymous=248,standalone_constants=1785,
        allocation_blocks=1953,distinct_allocation_ids=1459,production_constructs=6006,
        layouts=46,adversarial_controls=len(report['adversarial_controls']),compiler_invocations=0,
        new_product_or_native_runtime=False,read_only=True,operational_or_OTA_FieldLog_GA=False)

if __name__=='__main__':
    require(sys.argv[1:]==['--read-only'],'use --read-only')
    print(json.dumps(verify(),sort_keys=True))
