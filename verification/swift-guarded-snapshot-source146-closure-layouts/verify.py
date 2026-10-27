"""Read-only verification of six exact original anonymous layout observations."""
import gzip
import hashlib
import json
from pathlib import Path
import re

D=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def read(n):return json.loads((D/n).read_text())
def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':')).encode()

def main():
    receipt=read('compiler-receipt.json');binding=read('binding.json');manifest=read('compiled-manifest.json');cleanup=read('cleanup.json')
    assert receipt['exit_code']==0 and not receipt['timed_out'] and receipt['direct_child_waited'] and receipt['owned_group_absent']
    assert cleanup['completed'] and cleanup['owned_scratch_removed'] and cleanup['command_children_waited_and_groups_absent'] and not (D/'owned-work').exists()
    assert manifest['original_source146_bodies_unchanged'] and manifest['original_closure_source_spans_unchanged']
    old={r['path']:r for r in manifest['source_manifest']['members']};new={r['path']:r for r in manifest['compiled_source_members']}
    assert len(old)==len(new)==146 and sha(canonical(manifest['source_manifest']['members']))==binding['source_tree_sha256']
    assert set(k for k in old if old[k]!=new[k])==set(manifest['additions'])
    source_refs=read('original-source-reference-map.json')['members']
    for row in source_refs:
        original=(D.parents[1]/row['source']).read_bytes()
        assert len(original)==row['bytes'] and sha(original)==row['sha256']
        extra=manifest['additions'].get(row['path'])
        compiled=original
        if extra:
            fragment=(D/(Path(row['path']).stem+'-append.inc.rs')).read_bytes()
            assert len(fragment)==extra['bytes'] and sha(fragment)==extra['sha256']
            compiled+=fragment
        assert len(compiled)==new[row['path']]['bytes'] and sha(compiled)==new[row['path']]['sha256']
    for key,name in [('MIXER_LOADER_MANIFEST_SHA256','compiled-manifest.json'),('MIXER_LOADER_COMMAND_SHA256','argv.bin'),('MIXER_LOADER_COMPILE_ENV_SHA256','environment.bin'),('MIXER_LOADER_COMPILER_VERSION_SHA256','compiler-version.stdout')]:
        assert sha((D/name).read_bytes())==binding['compile_identity_keys'][key]==receipt['environment'][key]
    assert binding['compile_identity_keys']['MIXER_LOADER_COMPILER_SHA256']==manifest['compiler_sha256']==receipt['environment']['MIXER_LOADER_COMPILER_SHA256']
    archive=read('layout-archive.json');packed=(D/'compiler.stdout.gz').read_bytes();raw=gzip.decompress(packed)
    assert len(packed)==archive['archive_bytes'] and sha(packed)==archive['archive_sha256']
    assert len(raw)==archive['raw_bytes']==receipt['outputs']['stdout']['bytes'] and sha(raw)==archive['raw_sha256']==receipt['outputs']['stdout']['sha256']
    err=(D/'compiler.stderr').read_bytes();assert len(err)==receipt['outputs']['stderr']['bytes'] and sha(err)==receipt['outputs']['stderr']['sha256']
    assert not any(json.loads(line).get('level')=='error' for line in err.splitlines())
    llvm=read('llvm-archive.json');packed=(D/'source146.ll.gz').read_bytes();ir=gzip.decompress(packed)
    assert len(packed)==llvm['archive_bytes'] and sha(packed)==llvm['archive_sha256'] and len(ir)==llvm['raw_bytes'] and sha(ir)==llvm['raw_sha256']
    assert b'SnapshotAdoptionV1' in ir and b'SOURCE146_CLOSURE_LAYOUT_CORE_V1' in ir and b'SOURCE146_CLOSURE_LAYOUT_BYTES4096_V1' in ir and b'SOURCE146_CLOSURE_LAYOUT_BYTES16384_V1' in ir
    observations=read('results.json')['closures']
    assert len(observations)==6
    for row in observations:
        prefix='print-type-size type: `{closure@'+str(D/'owned-work/vm')+'/'+row['source_span']+'}`: '
        matches=[line for line in raw.decode().splitlines() if line.startswith(prefix)]
        assert len(matches)==1
        tail=matches[0][len(prefix):];s,a=tail.split(' bytes, alignment: ');a=a.removesuffix(' bytes')
        assert (int(s),int(a))==(row['bytes'],row['alignment'])
        assert row['alignment']>0 and row['bytes']%row['alignment']==0
    assert [(r['bytes'],r['alignment']) for r in observations]==[(64,8),(16,8),(0,1),(16,8),(16,8),(8,8)]
    if (D/'seal.json').exists():
        for row in read('seal.json')['members']:
            data=(D/row['path']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
    print(json.dumps(dict(status='passed',original_source_members=146,additive_query_members=2,exact_original_closure_layouts=6,observed_zero_sized_closures=1,LLVM_bytes=len(ir),runtime=False)))

if __name__=='__main__':main()
