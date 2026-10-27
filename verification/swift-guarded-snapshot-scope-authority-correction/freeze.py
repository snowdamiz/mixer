"""Validate completed exact compiler controls, then seal this owned packet once."""
from pathlib import Path
import hashlib,json,re,sys
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def member(path):return {'path':path.relative_to(HERE).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}
def main():
    if '--check' in sys.argv:
        seal=json.loads((HERE/'seal.json').read_text())
        for m in seal['members']:assert member(HERE/m['path'])==m,m['path']
        assert sha(canonical(seal['members']))==seal['tree_sha256']
        print(json.dumps({'verified_members':len(seal['members']),'seal_sha256':sha((HERE/'seal.json').read_bytes())}));return
    assert not (HERE/'seal.json').exists()
    subset=json.loads((HERE/'source-seal.json').read_text())
    for m in subset['members']:assert member(HERE/m['path'])==m
    assert len(subset['members'])==149
    paths=sorted((HERE/'commands').glob('*/receipt.json'));assert len(paths)==14
    commands=[]
    for p in paths:
        v=json.loads(p.read_text());assert v['expectation_met'] and v['child_reaped'] and v['owned_group_absent'] and not v['timed_out'],p
        pre=json.loads((p.parent/'build-preimage.json').read_text())
        assert sha(canonical(pre['source_members']))==v['source_tree_sha256']
        assert sha(canonical(pre))==v['environment']['MIXER_LOADER_MANIFEST_SHA256']
        assert sha((p.parent/'stdout').read_bytes())==v['stdout_sha256']
        assert sha((p.parent/'stderr').read_bytes())==v['stderr_sha256']
        commands.append({'case':v['case'],'mode':v['mode'],'receipt':member(p),'source_tree_sha256':v['source_tree_sha256'],'expectation_met':True})
    layouts={}
    for mode in ['debug','optimized']:
        line=(HERE/'commands'/('layout-'+mode)/'exact-layout.llvm').read_text()
        raw=re.search(r'c"(.*?)"',line).group(1);data=bytearray();i=0
        while i<len(raw):
            if raw[i]=='\\':data.append(int(raw[i+1:i+3],16));i+=3
            else:data.append(ord(raw[i]));i+=1
        values=[int.from_bytes(data[i:i+8],'little') for i in range(0,len(data),8)]
        assert values==[1240,8,1240,8],values;layouts[mode]=values
    work=HERE/'owned-work';assert not any(work.iterdir());work.rmdir()
    summary={'schema':1,'source_tree_sha256':json.loads((HERE/'source-manifest.json').read_text())['source_tree_sha256'],'compiler_commands_passed':14,'commands':commands,'layout_values_capability_size_align_tuple_size_align':layouts,'actual_bypasses_closed_by_compiler':2,'all_compiler_children_reaped':True,'all_owned_compiler_groups_absent':True,'owned_scratch_removed':True,'runtime_or_writer_executed':False,'complete_storage_or_work_accepted':False,'independent_authority_review':'separate active lane','canonical_product_changed':False,'GA_gates_verified':0}
    (HERE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    members=[member(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    seal={'schema':1,'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'members':members,'tree_sha256':sha(canonical(members)),'scope':'isolated source authority correction and compiler-only checks; not operational admission'}
    (HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    print(json.dumps({'members':len(members),'bytes':seal['member_bytes'],'seal_sha256':sha((HERE/'seal.json').read_bytes()),'tree_sha256':seal['tree_sha256']}))
if __name__=='__main__':main()
