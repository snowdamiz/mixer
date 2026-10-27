"""Offline custody verification and one additive independent test tree; no compiler."""
from pathlib import Path
import datetime, difflib, hashlib, json, shutil, struct, sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CANDIDATE=ROOT/'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction'
PRE=ROOT/'verification/swift-guarded-snapshot-actual-owner-rust-preaccess'
EXPECTED='46d811b1264770604106b061386e6eba01ea07e55590240eff722c36af4bcaa0'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def digest(x): return sha(json.dumps(x,sort_keys=True,separators=(',',':')).encode())
def write(p,x): p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def row(p,base):
    b=p.read_bytes(); return dict(path=str(p.relative_to(base)),bytes=len(b),sha256=sha(b))
def rows(p): return [row(f,p) for f in sorted(p.rglob('*')) if f.is_file()]
def verify(base,expected=None):
    raw=(base/'seal.json').read_bytes()
    if expected: assert sha(raw)==expected
    d=json.loads(raw)
    for m in d['members']: assert row(base/m['path'],base)==m,m
    assert len(d['members'])==d['member_count']
    assert sum(m['bytes'] for m in d['members'])==d['member_bytes']
    return dict(seal=row(base/'seal.json',ROOT),members=d['member_count'],member_bytes=d['member_bytes'])
def bytes_rs(x): return '&['+','.join(map(str,x))+']'
def u64(n): return n & ((1<<64)-1)
def main():
    custody={'candidate':verify(CANDIDATE,EXPECTED),'preaccess':verify(PRE),
        'original_independent':verify(ROOT/'verification/swift-guarded-snapshot-actual-owner-rust-independent', 'e9d55089795d317048040be973e518ff9ce841d7f39cb1449b930d7ae066990c')}
    release=ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-actual-owner-Rust-retirement-correction-release.json'
    custody['root_release']=row(release,ROOT)
    manifest=json.loads((CANDIDATE/'source-manifest.json').read_text())
    assert rows(CANDIDATE/'source/vm')==manifest['members']
    assert digest(manifest['members'])=='c3a33b76eef6bf9ad86ef1cb0320e94bcefa5a0609ec1a30872a9d83371bd0db'
    assert digest(rows(CANDIDATE/'source/host'))=='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
    source=HERE/'source'
    assert not source.exists()
    shutil.copytree(CANDIDATE/'source',source)
    d=json.loads((PRE/'oracles.json').read_text())
    frozen=HERE/'frozen-oracles.json'; frozen.write_bytes((PRE/'oracles.json').read_bytes())
    binary=[]
    for magic,record in d['binary'].items():
        base=bytes.fromhex(record['bytes_hex']); assert sha(base)==record['sha256']
        for m in record['mutations']:
            raw=bytearray(base); replacement=bytes.fromhex(m['replace_hex']); raw[m['offset']:m['offset']+len(replacement)]=replacement
            assert sha(raw)==m['result_sha256']
            binary.append((magic,m,bytes(raw)))
    assert len(binary)==51
    chunks=['// Generated only from immutable preaccess vector bytes; no production authority.\n']
    chunks.append('fn independent_binary_vectors_v1() -> Vec<(&\'static str,u8,Vec<u8>,bool,&\'static str)> { vec![\n')
    for magic,m,raw in binary:
        kind={'MIXLBD01':0,'MIXLSE01':1,'MIXPTH01':2}[magic]
        chunks.append(f'({json.dumps(m["id"])},{kind},{bytes_rs(raw)}.to_vec(),{str(m["reject_at"]=="owner admission only").lower()},{json.dumps(m["diagnostic"])}),\n')
    chunks.append('] }\n')
    for magic,record in d['binary'].items(): chunks.append(f'const INDEPENDENT_{magic}: &[u8] = {bytes_rs(bytes.fromhex(record["bytes_hex"]))};\n')
    chunks.append('fn independent_provenance_vectors_v1() -> Vec<(&\'static str,usize,usize,usize,u64)> { vec![\n')
    mapping=[];baseline=d['correlation_baseline']
    groups=['source','manifest','build','session','executable','nonce','validation_budget','source_extent','identities']
    for m in d['correlation_mutations']:
        path=m['path'];group=groups.index(path[0]);a=b=0
        if group<6:
            old=bytes.fromhex(baseline[path[0]]);new=bytes.fromhex(m['replacement']);diff=[(i,x^y) for i,(x,y) in enumerate(zip(old,new)) if x!=y]
            assert len(diff)==1;a,delta=diff[0]
        elif group==6: a=path[1];delta=u64(baseline[path[0]][a])^u64(m['replacement'])
        elif group==7: delta=u64(baseline[path[0]])^u64(m['replacement'])
        else: a,b=path[1:];delta=u64(baseline[path[0]][a][b])^u64(m['replacement'])
        assert delta
        chunks.append(f'({json.dumps(m["id"])},{group},{a},{b},{delta}u64),\n')
        mapping.append(dict(id=m['id'],path=path,frozen_replacement=m['replacement'],xor_delta_u64=delta,
            actual_mapping='actual owner-derived field bits XOR exact frozen baseline-to-replacement delta'))
    assert len(mapping)==230
    chunks.append('] }\n')
    chunks.append('fn independent_read_vectors_v1() -> Vec<(&\'static str,usize,usize,usize,Vec<i64>,u8)> { vec![\n')
    for m in d['read_schedules']:
        responses=[-1 if x=='Interrupted' else -2 if x=='OriginalIo' else x for x in m['responses']]
        outcome=0 if m['id'].startswith('all-last-') or m['id']=='32-positive-partials' else 1 if m['id'].startswith('no33rd-') else 2 if 'io' in m['id'] else 3 if m['id']=='short-after-prefix' else 4 if m['id']=='overreported' else 5
        chunks.append(f'({json.dumps(m["id"])},{m["extent"]},{m["expected_calls"]},{m["expected_bytes"]},vec!{responses},{outcome}),\n')
    chunks.append('] }\n')
    (HERE/'vectors.inc.rs').write_text(''.join(chunks))
    fragment=(HERE/'vectors.inc.rs').read_text()+(HERE/'independent.inc.rs').read_text()
    target=source/'vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs'
    original=target.read_text(); anchor='    }\n\n    // OWNER_PROBE_INSERTION'
    assert original.count(anchor)==1
    updated=original.replace(anchor,fragment+'\n'+anchor);target.write_text(updated)
    (HERE/'independent-only.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),updated.splitlines(True),fromfile='frozen/retained_profile_loader_v1.rs',tofile='tested/retained_profile_loader_v1.rs')))
    write(HERE/'provenance-vector-mapping.json',dict(schema=1,source='frozen-oracles.json',count=230,mapping=mapping,
        baseline_limit='frozen baseline is parser-only; actual baseline derives from admitted production generic core and uses validator-created proof. XOR preserves every original changed bit, not original absolute digest/identity value.',
        original_vectors_preserved=True))
    write(HERE/'tested-source-manifest.json',dict(schema=1,members=rows(source/'vm'),tree_sha256=digest(rows(source/'vm')),
        frozen_source146_tree=manifest['tree_sha256'],only_changed='src/experimental_swift_reactor/retained_profile_loader_v1.rs',
        change='Additive private cfg(test) independent methods and exact frozen vector data only; all frozen producer methods and production bytes preserved.'))
    write(HERE/'custody.json',dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=sys.argv,python=sys.version,
        inputs=custody,frozen_vectors=row(frozen,HERE),compiler_or_runtime_executed=False,source146_tree=manifest['tree_sha256'],
        tested_source146_tree=digest(rows(source/'vm')),frozen_binary=51,frozen_provenance=230,frozen_reads=12,one_owned_test_tree=True))
    print(json.dumps({'custody':'verified','source_members':len(rows(source/'vm')),'binary':51,'provenance':230,'reads':12,'compiler_runtime':0}))
if __name__=='__main__': main()
