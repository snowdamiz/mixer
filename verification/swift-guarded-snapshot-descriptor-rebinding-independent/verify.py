"""Read-only frozen review validation. Never invokes compiler or runtime."""
from pathlib import Path
import hashlib,json,os,struct
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
KEYS=['MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256']
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def read(p):return json.loads(p.read_bytes())
def identity(p):
    b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def packed(items):
    bs=[os.fsencode(v) for v in items];return struct.pack('<Q',len(bs))+b''.join(struct.pack('<Q',len(v))+v for v in bs)
def main():
    seal=read(HERE/'seal.json');members=seal['members'];assert len(members)==seal['member_count'] and sum(m['bytes'] for m in members)==seal['member_bytes'] and sha(canonical(members))==seal['tree_sha256']
    assert {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file()}=={m['path'] for m in members}|{'seal.json'}
    for m in members:
        b=(HERE/m['path']).read_bytes();assert len(b)==m['bytes'] and sha(b)==m['sha256'],m['path']
    r=read(HERE/'results.json');assert all(r['checks'].values()) and len(r['checks'])==63
    assert r['source_tree_sha256']=='450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a' and r['host_support_tree_sha256']=='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
    assert not r['actual_loader_ingress_executed'] and not r['engine_VM_guest_writer_executed'] and not r['GA_verified']
    source=ROOT/'verification/swift-guarded-snapshot-descriptor-rebinding';assert sha((source/'seal.json').read_bytes())=='5e11885ef1a1189dc10ef8de5b82f4cd969573a8a1130e0a25f146725c23d7ea'
    for m in read(source/'seal.json')['members']:
        b=(source/m['path']).read_bytes();assert sha(b)==m['sha256'] and len(b)==m['bytes']
    index=read(HERE/'command-index.json');assert len(index)==19
    receipts={}
    for e in index:
        p=HERE/'commands'/e['label']/'receipt.json';assert identity(p)==e['receipt'];v=read(p);assert v['exit_code']==0 and v['owned_group_absent'] and v['child_reaped'];receipts[e['label']]=v
        for k in ['stdout','stderr']:assert identity(p.parent/k)==v[k]
    assert b'independent_pure_controls=53' in (HERE/'commands/run-positive/stdout').read_bytes()
    for i in range(5):assert b'independent_identity_refusal=stale' in (HERE/'commands'/('run-stale-'+str(i))/'stdout').read_bytes()
    for name in ['missing','malformed']:assert b'independent_identity_refusal=unsupported' in (HERE/'commands'/('run-'+name)/'stdout').read_bytes()
    for artifact in r['artifacts_measured_then_removed']:
        label=artifact['label'];p=HERE/'preimages'/label;v=receipts[label];parts=[(p/n).read_bytes() for n in ['manifest.json','argv.bin','environment.bin','compiler-version.txt']]
        m=json.loads(parts[0]);assert canonical(m)==parts[0];assert parts[1]==packed(v['argv'])
        clean={k:w for k,w in v['environment'].items() if k not in KEYS};assert parts[2]==packed([k+'='+w for k,w in sorted(clean.items(),key=lambda e:os.fsencode(e[0]))])
        keys=dict(zip(KEYS,[sha(parts[0]),sha(parts[1]),sha(parts[2]),r['compiler']['sha256'],sha(parts[3])]))
        binding=read(p/'keys.json');assert binding['derived_keys']==keys and binding['actual_keys']=={k:v['environment'][k] for k in KEYS if k in v['environment']}
        if label.startswith('pure-stale-'):keys[KEYS[int(label[-1])]]='0'*64
        elif label=='pure-missing':del keys[KEYS[0]]
        elif label=='pure-malformed':keys[KEYS[4]]='G'*64
        assert keys==binding['actual_keys']
        record=(p/'build-preimage.bin').read_bytes();at=512
        for i,part in enumerate(parts):assert record[at:at+len(part)]==part and struct.unpack_from('<Q',record,48+8*i)[0]==len(part) and record[152+32*i:184+32*i].hex()==sha(part);at+=len(part)
        assert at==len(record) and record[280:312].hex()==r['compiler']['sha256'] and record[312:344].hex()==artifact['sha256'] and struct.unpack_from('<Q',record,80)[0]==artifact['bytes']
        assert not Path(artifact['path']).exists()
    cleanup=read(HERE/'cleanup.json');assert cleanup['completed'] and cleanup['recorded_owned_groups_absent'] and cleanup['owned_scratch_removed'] and not (HERE/'owned-work').exists()
    print(json.dumps({'all_pass':True,'review_members':seal['member_count'],'review_bytes':seal['member_bytes'],'independent_static_checks':len(r['checks']),'independent_pure_controls':53,'independent_identity_negative_build_run_pairs':7,'independent_metadata_builds':1,'actual_loader_VM_guest_writer_executed':False,'GA_verified':False},sort_keys=True))
if __name__=='__main__':main()
