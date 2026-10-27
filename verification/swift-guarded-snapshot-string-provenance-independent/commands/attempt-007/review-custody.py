#!/usr/bin/env python3
"""Independently rehash every candidate and declared immutable input byte."""
import gzip,hashlib,json,pathlib
D=pathlib.Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification';P=V/'swift-guarded-snapshot-string-provenance'
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(j): return json.dumps(j,sort_keys=True,separators=(',',':')).encode()
def main():
    checked={}
    def raw(path,expected=None):
        path=pathlib.Path(path);b=path.read_bytes();seen={'bytes':len(b),'sha256':sha(b)}
        if expected is not None: assert seen==expected, str(path)
        checked[str(path.relative_to(R))]=seen;return b
    seal=json.loads(raw(P/'seal.json'))
    assert checked[str((P/'seal.json').relative_to(R))]['sha256']=='b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f'
    names=[]
    for m in seal['members']:
        q=pathlib.PurePosixPath(m['path']);assert not q.is_absolute() and '..' not in q.parts
        names.append(m['path']);raw(P/q,{k:m[k] for k in ('bytes','sha256')})
    assert len(names)==len(set(names))==114
    assert sum(m['bytes'] for m in seal['members'])==6305257
    actual={str(f.relative_to(P)) for f in P.rglob('*') if f.is_file()}
    assert actual==set(names)|{'seal.json'}
    pins={'guarded-snapshot-string-provenance-frozen-release.json':'8e7ee6b230451da7343397db7b79e111be5e0ac8766bd7c2a34d79c874720c5d',
        'guarded-snapshot-remaining-work-contract-amendment.json':'766e27395fd3ba66d2e7968ef1aeb192e2691ab38614f00c1563bf5e5dcdb1ab'}
    for n,h in pins.items(): assert sha(raw(V/'swift-semantic-adapter-root-review'/n))==h
    bindings=json.loads((P/'input-bindings.json').read_text())['files']
    for path,expected in bindings.items():raw(R/path,expected)
    B=V/'swift-guarded-snapshot-loader-work-source146'
    manifest=json.loads((B/'source146-manifest.json').read_text());ref=json.loads((B/'source-reference-map.json').read_text())
    assert len(manifest['members'])==146 and sha(canonical(manifest['members']))==seal['source_tree_sha256']
    index={x['path']:x for x in manifest['members']};assert len(index)==146
    assert len(ref['members'])==146
    for m in ref['members']:
        expected={k:m[k] for k in ('path','bytes','sha256')};assert expected==index[m['path']]
        raw(R/m['source'],{k:m[k] for k in ('bytes','sha256')})
    host=json.loads((B/'host11-manifest.json').read_text())
    assert len(host['members'])==11 and sha(canonical(host['members']))==seal['host_tree_sha256']
    receipt=json.loads((B/'compiler-receipt.json').read_text());archive=(B/'whole-source146.mir.gz').read_bytes();mir=gzip.decompress(archive)
    assert {'bytes':len(archive),'sha256':sha(archive)}=={'bytes':receipt['MIR']['archive_bytes'],'sha256':receipt['MIR']['archive_sha256']}
    assert {'bytes':len(mir),'sha256':sha(mir)}=={'bytes':receipt['MIR']['raw_bytes'],'sha256':receipt['MIR']['raw_sha256']}
    assert receipt['source_tree_sha256']==seal['source_tree_sha256'] and receipt['exit_code']==0
    out={'schema':1,'candidate_members':114,'candidate_member_bytes':6305257,'declared_input_files':len(bindings),'all_checked_files':checked,
         'source_members':146,'host_members':11,'MIR_bytes':len(mir),'MIR_sha256':sha(mir),
         'all_pins_match':True,'compiler_reran':False,'product_runtime':False,'source_and_frozen_inputs_written':False}
    (D/'custody.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='all_checked_files'},sort_keys=True))
if __name__=='__main__':main()
