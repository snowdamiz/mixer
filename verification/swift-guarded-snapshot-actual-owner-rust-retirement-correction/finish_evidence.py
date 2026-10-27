#!/usr/bin/env python3
"""Finish immutable input custody and lossless MIR archival; no compiler/tests."""
from pathlib import Path
import collections,gzip,hashlib,json,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
def row(path,base=HERE):
    raw=path.read_bytes();return {'path':str(path.relative_to(base)),'bytes':len(raw),'sha256':sha(raw)}
def write(name,value):(HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
custody=[]
for name,expected,count,byte_count in [
    ('swift-guarded-snapshot-actual-owner-rust-implementation','3592011c00794c12dcb76cecc41d4d2913e01a3d6e97612f3ce90f10cb4e5e23',1799,209640941),
    ('swift-guarded-snapshot-actual-owner-rust-independent','e9d55089795d317048040be973e518ff9ce841d7f39cb1449b930d7ae066990c',49,2172470),
]:
    base=ROOT/'verification'/name;assert sha((base/'seal.json').read_bytes())==expected
    seal=json.loads((base/'seal.json').read_text());assert len(seal['members'])==count and sum(r['bytes'] for r in seal['members'])==byte_count
    assert digest(seal['members'])==seal['tree_sha256']
    for member in seal['members']:assert row(base/member['path'],base)==member
    custody.append({'packet':name,'seal_sha256':expected,'members_verified':count,'member_bytes_verified':byte_count,'tree_sha256':seal['tree_sha256'],'all_members_unchanged':True})
write('final-custody.json',{'schema':1,'python':sys.version,'frozen_packets':custody,'source146_tree':json.loads((HERE/'source-manifest.json').read_text())['tree_sha256'],'host11_tree':json.loads((HERE/'host-manifest.json').read_text())['tree_sha256'],'no_contemporaneous_Git_HEAD_claim':True,'compiler_test_native_UI_capture_execution':False})
path=HERE/'mir/actual.mir';raw=path.read_bytes();text=raw.decode();items=[];current=[];kind=None
def emit():
    if current:
        body=''.join(current).encode();items.append({'kind':kind,'header':current[0].rstrip(),'bytes':len(body),'sha256':sha(body)})
for line in text.splitlines(keepends=True):
    new=None
    if line.startswith('fn '):new='fn'
    elif line.startswith('const '):new='const'
    elif line.startswith('static '):new='static'
    elif line.startswith('alloc') and len(line)>5 and line[5].isdigit():new='alloc'
    elif line and not line[0].isspace() and line.rstrip().endswith(' = {') and ': ' in line:new='standalone_const'
    elif line and not line[0].isspace() and not line.startswith(('//','}','\n')):raise AssertionError(('unaccounted top-level MIR',line[:120]))
    if new:
        emit();kind=new;current=[line]
    elif current:current.append(line)
    elif line.strip() and not line.startswith('//'):raise AssertionError('unaccounted MIR prefix')
emit()
archive=HERE/'mir/actual.mir.gz';assert not archive.exists();archive.write_bytes(gzip.compress(raw,compresslevel=9,mtime=0));assert gzip.decompress(archive.read_bytes())==raw
binding={'archive':row(archive),'uncompressed_bytes':len(raw),'uncompressed_sha256':sha(raw),'lossless_round_trip_verified':True}
write('complete-mir-item-inventory.json',{'schema':1,'full_MIR':binding,'complete_item_count':len(items),'counts':dict(collections.Counter(item['kind'] for item in items)),'items':items,'new_source_only':True,'layout_or_price_authority':False})
for name,key in [('mir-review.json','full_MIR'),('mir-function-inventory.json','full_MIR'),('artifact-cleanup.json','retained_full_MIR')]:
    value=json.loads((HERE/name).read_text());value[key]=binding;write(name,value)
path.unlink()
write('mir-archive.json',{'schema':1,**binding,'removed_owned_uncompressed_duplicate':True,'full_MIR_bytes_preserved':True,'all_six_exact_selected_items_retained':True,'compiler_test_execution':False})
print(json.dumps({'frozen_packets_verified':len(custody),'frozen_members_verified':sum(r['members_verified'] for r in custody),'MIR_complete_items':len(items),'MIR_counts':dict(collections.Counter(item['kind'] for item in items)),'MIR_uncompressed_bytes':len(raw),'MIR_archive_bytes':archive.stat().st_size}))
