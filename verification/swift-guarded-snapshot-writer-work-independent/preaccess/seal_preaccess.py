#!/usr/bin/env python3
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,sys
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'verification/swift-guarded-snapshot-composition-source-preparation/source/vm/src'
def h(b):return sha256(b).hexdigest()
def function(s,name,occurrence=0):
    marker='fn '+name+'('
    start=-1
    for _ in range(occurrence+1):start=s.index(marker,start+1)
    end=s.index('{',start);depth=1;end+=1
    while depth:
        depth+=(s[end]=='{')-(s[end]=='}');end+=1
    if s[end:end+1]=='\n':end+=1
    return start,end,s[start:end].encode()
ranges={
 'experimental_swift_reactor/cache/initial_profile_v1.rs':[(285,442),(442,515),(517,541)],
 'experimental_swift_reactor/control.rs':[(20,120),(132,234),(289,301),(343,356),(953,966),(1817,2056)],
 'experimental_swift_reactor/cache.rs':[(266,281),(1320,1335),(1497,1500),(4868,4898)],
 'experimental_wasi/accounted.rs':[(18,24),(70,76),(123,126),(434,451)],
 'experimental_wasi/mod.rs':[(92,135),(243,246)],
 'experimental_swift_reactor/retained_profile_loader_v1.rs':[(142,155)],
 'experimental/swift.rs':[(59,71),(164,167),(756,777),(1304,1312),(1696,1705)],
 'experimental/account.rs':[(219,238)],
 'execute.rs':[(7,33)],
}
bindings=[]
for rel,spans in ranges.items():
    p=SOURCE/rel;b=p.read_bytes();lines=b.splitlines(keepends=True)
    bindings.append(dict(path=str(p.relative_to(ROOT)),bytes=len(b),sha256=h(b),segments=[dict(start_line=a,end_line=z,bytes=len(b''.join(lines[a-1:z])),sha256=h(b''.join(lines[a-1:z]))) for a,z in spans]))
s=(SOURCE/'experimental_swift_reactor/cache/initial_profile_v1.rs').read_text()
a,z,b=function(s,'write_snapshot_v1')
assert len(b)==5113 and h(b)=='0de141d7c07db571a576fc343c3d43841614937c9ac07fd4cb64512761373343'
functions=[]
for rel,names in {
 'experimental_swift_reactor/cache/initial_profile_v1.rs':['checked_add_v1','checked_mul_v1','snapshot_shape_v1','proposed_emission_work_v1','begin_snapshot_access_v1','error','stop','io_result','encode_result','write_snapshot_v1','retire_v1'],
 'experimental_swift_reactor/control.rs':['snapshot_existing_v1','snapshot_observe_stop_v1','snapshot_ticket_v1','snapshot_owner_v1','snapshot_ticket_identity_v1','snapshot_adopted_pair_v1','snapshot_foundation_pair_v1','snapshot_totals_v1','snapshot_debit_v1','snapshot_storage_preflight_v1','snapshot_commit_storage_v1','adopt_snapshot_body_v1','attach_wasi_v1','attach_wasi_inner_v1','construct_v1','finish_v1'],
 'experimental_swift_reactor/cache.rs':['snapshot_pair_v1'],
 'experimental_wasi/accounted.rs':['snapshot_pair_v1'],
}.items():
    s=(SOURCE/rel).read_text()
    for name in names:
        # Generic method names have a '<' before the argument list.
        marker='fn '+name
        start=s.index(marker)
        brace=s.index('{',start);end=brace+1;depth=1
        while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
        if s[end:end+1]=='\n':end+=1
        b=s[start:end].encode()
        functions.append(dict(path=str((SOURCE/rel).relative_to(ROOT)),function=name,start_line=s[:start].count('\n')+1,bytes=len(b),sha256=h(b)))
refs=[]
for rel,expected in [
 ('verification/swift-semantic-adapter-root-review/guarded-snapshot-encoder-work-host-acceptance.json','757345abe9013a4d5d880738c794e8a9783061fb733f4de24f432698861e9351'),
 ('verification/swift-guarded-snapshot-export-admission-design/seal.json','b60d1ba0790076b35b6df30dd8df407486f89144e6914f40d2d0d55e4e20e1f5'),
 ('verification/swift-guarded-snapshot-encoder-work-correction/cost-convention.md','9e166f6faaca7b74f639d8ddd1da30331737ee2f88a97ddce349d8ba1cddd9a5'),
 ('verification/swift-guarded-snapshot-encoder-work-correction/geometry.md','72a0ae0d689903e68e3a652ddbf0e0f9215b6b55c8a7795bf3f02f4fd1dfaa34'),
]:
    b=(ROOT/rel).read_bytes()
    refs.append(dict(path=rel,bytes=len(b),sha256=h(b)))
    assert h(b)==expected,(rel,h(b))
p=ROOT/'verification/swift-guarded-snapshot-export-admission-design/design.md';b=p.read_bytes();lines=b.splitlines(keepends=True)
refs.append(dict(path=str(p.relative_to(ROOT)),bytes=len(b),sha256=h(b),segments=[dict(start_line=291,end_line=307,sha256=h(b''.join(lines[290:307])))]))
custody=dict(schema=1,at=datetime.now(timezone.utc).isoformat(),status='sealed-before-producer-ledger-access',source_revision_reference='79b948a7b361e537cfdd03285f68ea8c50d1a382 from accepted encoder interface; no Git query',whole_file_hashes_are_observed='Measurement-only cfg edits may change whole-file hashes; exact function and segment hashes bind reviewed stable behavior.',source_files=bindings,functions=functions,references=refs,producer_lane_read=False)
(OUT/'source-custody.json').write_text(json.dumps(custody,indent=2)+'\n')
receipt=dict(schema=1,at=custody['at'],command='python3 verification/swift-guarded-snapshot-writer-work-independent/preaccess/arithmetic_controls.py; python3 verification/swift-guarded-snapshot-writer-work-independent/preaccess/seal_preaccess.py',python=sys.version,source_behavior_sha256='0de141d7c07db571a576fc343c3d43841614937c9ac07fd4cb64512761373343',scope='Host Python arithmetic and immutable source inspection only',native_runtime=False,process_inventory=False,git=False,work_selected=False,storage_floor_selected=False,producer_lane_read=False)
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
members=[]
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.name!='seal.json':
        b=p.read_bytes();members.append(dict(path=p.name,bytes=len(b),sha256=h(b)))
wire=json.dumps(members,sort_keys=True,separators=(',',':')).encode()
seal=dict(schema=1,status='independent-preaccess-sealed',at=custody['at'],member_count=len(members),bytes=sum(m['bytes'] for m in members),members=members,tree_sha256=h(wire),producer_lane_read=False)
(OUT/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps(dict(status=seal['status'],seal_sha256=h((OUT/'seal.json').read_bytes()),tree_sha256=seal['tree_sha256'],members=len(members),bytes=seal['bytes'])))
