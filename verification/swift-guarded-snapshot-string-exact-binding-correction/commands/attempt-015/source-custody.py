#!/usr/bin/env python3
"""Read-only rehash of original packets, exact source/host/MIR and copy history."""
import gzip,hashlib,json,sys
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(ok,reason):
    if not ok:raise ValueError(reason)
def main(check=False):
    seen={}
    def read(path,expected=None):
        require(not path.is_symlink(),'symlink input')
        raw=path.read_bytes();actual={'bytes':len(raw),'sha256':sha(raw)}
        if expected is not None:require(actual==expected,'custody:'+str(path))
        seen[str(path.relative_to(R))]=actual;return raw
    packets=[('swift-guarded-snapshot-string-provenance','b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f',114,6305257),
        ('swift-guarded-snapshot-string-provenance-independent','741e104537fc3ddc57fc499a764cca9fedaa2b42d2fe109eeb590504b01241d9',108,6581268),
        ('swift-guarded-snapshot-string-provenance-correction','4d2dcab90e7c9cfd7074a67fe8eac0d6807b6ed3704b74afe430ebc624b07994',358,56817849),
        ('swift-guarded-snapshot-string-correction-independent','7c101623fa53d9207c467f196cca729085fff23a195f873a46da7a1369135f65',248,6817047)]
    for name,digest,count,size in packets:
        base=V/name;raw=read(base/'seal.json');require(sha(raw)==digest,'frozen seal')
        seal=json.loads(raw);names=[]
        for m in seal['members']:
            q=Path(m['path']);require(not q.is_absolute() and '..' not in q.parts,'member path')
            names.append(m['path']);read(base/q,{k:m[k] for k in ('bytes','sha256')})
        require(len(names)==len(set(names))==count and sum(m['bytes'] for m in seal['members'])==size,'frozen count/bytes')
        actual={str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()}
        require(actual==set(names)|{'seal.json'},'frozen membership')
    bindings=json.loads((D/'input-bindings.json').read_text())['files']
    for path,expected in bindings.items():read(R/path,expected)
    source=V/'swift-guarded-snapshot-loader-work-source146'
    manifest=json.loads(read(source/'source146-manifest.json'));host=json.loads(read(source/'host11-manifest.json'))
    canonical=lambda j:json.dumps(j,sort_keys=True,separators=(',',':')).encode()
    require(len(manifest['members'])==146 and sha(canonical(manifest['members']))=='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','source tree')
    require(len(host['members'])==11 and sha(canonical(host['members']))=='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2','host tree')
    reference=json.loads(read(source/'source-reference-map.json'));index={m['path']:m for m in manifest['members']}
    for m in reference['members']:
        require({k:m[k] for k in ('path','bytes','sha256')}==index[m['path']],'source map')
        read(R/m['source'],{k:m[k] for k in ('bytes','sha256')})
    for m in host['members']:read(V/'swift-real-profile-loader-binding/host'/m['path'],{k:m[k] for k in ('bytes','sha256')})
    receipt=json.loads(read(source/'compiler-receipt.json'));archive=read(source/'whole-source146.mir.gz');mir=gzip.decompress(archive)
    require(len(mir)==receipt['MIR']['raw_bytes'] and sha(mir)==receipt['MIR']['raw_sha256'],'raw MIR')
    history=[('producer-006',V/'swift-guarded-snapshot-string-provenance/commands/attempt-006'),
        ('producer-007',V/'swift-guarded-snapshot-string-provenance/commands/attempt-007'),
        ('independent-adverse-006',V/'swift-guarded-snapshot-string-provenance-independent/commands/attempt-006')]
    for name,old in history:
        for p in old.rglob('*'):
            if p.is_file():
                raw=read(p);require(read(D/'history'/name/p.relative_to(old))==raw,'retained failure bytes')
        require(json.loads((D/'history'/name/'receipt.json').read_text())['exit_code']==1,'original failure not a pass')
    failure_roster=[]
    for label,base in [('first-correction',V/'swift-guarded-snapshot-string-provenance-correction'),('second-independent',V/'swift-guarded-snapshot-string-correction-independent')]:
        for attempt in sorted((base/'commands').glob('attempt-*')):
            receipt=json.loads((attempt/'receipt.json').read_text())
            if receipt['exit_code']==0:continue
            for path in attempt.rglob('*'):
                if path.is_file():require(read(D/'history'/label/attempt.name/path.relative_to(attempt))==read(path),'historical failure unchanged')
            failure_roster.append({'origin':str(attempt.relative_to(R)),'copy':str((D/'history'/label/attempt.name).relative_to(D)),'exit_code':receipt['exit_code']})
    read(V/'swift-semantic-adapter-root-review/guarded-snapshot-string-correction-second-return.json',{'bytes':(V/'swift-semantic-adapter-root-review/guarded-snapshot-string-correction-second-return.json').stat().st_size,'sha256':'9dba765988b0e464fe58245520586696945e9f4bbd87f1ca2b8bc4051cf68440'})
    out={'schema':1,'all_pins_match':True,'original_candidate_members':114,'original_candidate_member_bytes':6305257,
        'independent_review_members':108,'independent_review_member_bytes':6581268,'source_members':146,'host_members':11,
        'MIR_bytes':len(mir),'MIR_sha256':sha(mir),'checked_files':seen,
        'failure_receipts_preserved_as_failures':True,'first_correction_members':358,'first_correction_bytes':56817849,'second_independent_members':248,'second_independent_bytes':6817047,'additional_failure_roster':failure_roster,'compiler_or_runtime_reran':False,'native_or_UI_or_capture':False,
        'Git_or_global_inventory':False,'frozen_inputs_written':False,'only_owned_output':not check,'root_or_L_str_selected':False}
    # The receipt describes the original writable custody collection. Rechecks
    # compare those exact observed bytes while themselves remaining read-only.
    if check:out['only_owned_output']=True
    raw=(json.dumps(out,indent=2,sort_keys=True)+'\n').encode()
    if check:require((D/'custody.json').read_bytes()==raw,'custody exact recheck')
    else:
        require(not (D/'seal.json').exists(),'already frozen')
        (D/'custody.json').write_bytes(raw)
    print(json.dumps({'all_pins_match':True,'files':len(seen),'read_only':check,'original_failures_retained':True,'root_or_L_str_selected':False},sort_keys=True))
if __name__=='__main__':main('--check' in sys.argv)
