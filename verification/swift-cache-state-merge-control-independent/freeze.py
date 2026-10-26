#!/usr/bin/env python3
"""Seal the final independent finite review exactly once."""
import datetime
import hashlib
import json
import pathlib
import sys

OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def sha(data):
    return hashlib.sha256(data).hexdigest()
def need(ok,msg):
    if not ok: raise ValueError(msg)
need(not (OUT/'seal.json').exists(),'immutable seal already exists')
result=json.loads((OUT/'result.json').read_bytes())
receipt=json.loads((OUT/'command-receipt.json').read_bytes())
need(result['necessary_G3']==dict(scalars=34929,copies=385,scalar_groups=2184,groups=2569),'result totals')
need(len(receipt['commands'])==2 and all(x['exit_code']==0 for x in receipt['commands']),'both Python modes required')
need((OUT/'normal.stdout.txt').read_bytes()==(OUT/'optimized.stdout.txt').read_bytes(),'mode output mismatch')
need(not (OUT/'normal.stderr.txt').read_bytes() and not (OUT/'optimized.stderr.txt').read_bytes(),'unexpected stderr')
need(sha((OUT/'check.py').read_bytes())==receipt['check_sha256'],'checker changed after receipt')
bindings=json.loads((OUT/'input-bindings.json').read_bytes())
for name,h in bindings.items(): need(sha((ROOT/name).read_bytes())==h,'input changed '+name)
members=[]
for p in sorted(OUT.iterdir()):
    need(p.is_file(),'unexpected nonfile in packet')
    members.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p.read_bytes())))
tree=''.join(x['path']+'\0'+x['sha256']+'\n' for x in members).encode()
input_tree=''.join(name+'\0'+h+'\n' for name,h in sorted(bindings.items())).encode()
seal=dict(schema=1,at=datetime.datetime.now(datetime.UTC).isoformat(),argv=[sys.executable,*sys.argv],
    python=sys.version,status='sealed independent unchanged-merge necessary G3 obstruction; root decision separate',
    source_sha256=result['source_sha256'],merge_fragment_sha256=result['merge_fragment_sha256'],
    input_tree_sha256=sha(input_tree),member_tree_sha256=sha(tree),
    members=members,member_count=len(members),member_bytes=sum(x['bytes'] for x in members),
    necessary_G3=result['necessary_G3'],G3_cap=2568,over_cap=1,
    public_file_reachability_proved=False,complete_upper_or_implementation_accepted=False,
    scoped_G2_selection_changed=False,G3_G4_owners_or_caps_changed=False,G5_reviewed=False,
    compiler_Rust_runtime_native_UI_capture_process_inventory_Git_or_hosted=False,
    owned_writes=['verification/swift-cache-state-merge-control-independent/**'])
(OUT/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(seal_sha256=sha((OUT/'seal.json').read_bytes()),member_count=seal['member_count'],
    member_bytes=seal['member_bytes'],necessary_G3=seal['necessary_G3']),sort_keys=True))
