"""One coordinated LLVM-only retention query over original source146; never replay."""
import datetime
import gzip
import importlib.util
import json
from pathlib import Path
import shutil
import sys

D=Path(__file__).resolve().parent
R=D.parents[1]
V=R/'verification'
HELPER=V/'swift-guarded-snapshot-source146-callee-storage-layouts/query-named.py'
spec=importlib.util.spec_from_file_location('frozen_bounded_command_helper',HELPER)
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);h.D=D

def main():
    assert not (D/'compiler-receipt.json').exists()
    prior=V/'swift-guarded-snapshot-source146-callee-storage-layouts'
    assert h.sha((prior/'seal.json').read_bytes())=='9e2cd764548188b30c93d045fdc72d59c771a4cd489858d6340f131bc67b1001'
    for row in json.loads((prior/'seal.json').read_text())['members']: h.checked_file(row,prior/row['path'])
    base=V/'swift-guarded-snapshot-loader-work-source146'
    manifest=json.loads((base/'source146-manifest.json').read_text())
    refs=json.loads((base/'source-reference-map.json').read_text())['members']
    assert len(refs)==146 and manifest['tree_sha256']==h.TREE and h.sha(h.canonical(manifest['members']))==h.TREE
    assert [(r['path'],r['bytes'],r['sha256']) for r in refs]==[(r['path'],r['bytes'],r['sha256']) for r in manifest['members']]
    sources={r['path']:h.checked_file(r,R/r['source']) for r in refs}
    host=json.loads((base/'host11-manifest.json').read_text())
    assert len(host['members'])==11 and h.sha(h.canonical(host['members']))==host['tree_sha256']
    for row in host['members']: h.checked_file(row,V/'swift-real-profile-loader-binding/host'/row['path'])
    additions={
      'src/experimental_swift_reactor/cache.rs': '''
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static RESOURCE_BINARY_DROP_SWIFT_SLOTS_V1: fn(Vec<SwiftSlot>) = std::mem::drop::<Vec<SwiftSlot>>;
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static RESOURCE_BINARY_DROP_SCAN_PLANS_V1: fn(Vec<Option<ScanPlan>>) = std::mem::drop::<Vec<Option<ScanPlan>>>;
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static RESOURCE_BINARY_DROP_FILE_V1: fn(std::fs::File) = std::mem::drop::<std::fs::File>;
''',
      'src/experimental/cache/decode.rs': '''
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static RESOURCE_BINARY_DROP_PATCHES_V1: fn(Vec<Patch>) = std::mem::drop::<Vec<Patch>>;
'''}
    assert set(additions)<=sources.keys()
    for name,fragment in additions.items():
        (D/(Path(name).stem+'-append.inc.rs')).write_text(fragment)
        sources[name]+=fragment.encode()
    compiled=[dict(path=n,bytes=len(b),sha256=h.sha(b)) for n,b in sorted(sources.items(),key=lambda p:Path(p[0]))]
    work=D/'compiler-owned-work';assert not work.exists();work.mkdir();complete=False
    try:
        vm=work/'vm'
        for n,b in sources.items():
            p=vm/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        env=dict(PATH='/usr/bin:/bin',TMPDIR=str(work),CARGO_MANIFEST_DIR=str(vm),RUSTC_BOOTSTRAP='1',SDKROOT='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
        version,_,vr=h.run('compiler-version',[str(h.COMPILER),'--version','--verbose'],env,10)
        assert vr['exit_code']==0 and h.sha(version)=='352d6857968e80a6357a926ac685b9b07f77c479aaafde33e73a53945e802909'
        compiler_sha=h.sha(h.COMPILER.read_bytes());assert compiler_sha=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
        output=work/'source146.ll'
        argv=[str(h.COMPILER),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind','-C','codegen-units=1','-Zmir-opt-level=0','-Zprint-type-sizes','--error-format=json']
        for feature in ('experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache'): argv+=['--cfg','feature="'+feature+'"']
        argv+=['--cfg','mixer_bootstrap_one_fixture_v1','--crate-type','rlib',str(vm/'src/lib.rs'),'--emit=llvm-ir='+str(output)]
        closure=dict(schema=1,source_manifest=manifest,source_reference_map=refs,compiled_source_members=compiled,compiled_tree_sha256=h.sha(h.canonical(compiled)),host_support=host,additions={p:dict(bytes=len(f.encode()),sha256=h.sha(f.encode())) for p,f in additions.items()},compiler_sha256=compiler_sha,compiler_version_sha256=h.sha(version),script_sha256=h.sha(Path(__file__).read_bytes()),frozen_helper_sha256=h.sha(HELPER.read_bytes()),original_source146_bodies_and_lines_unchanged=True,query_scope='Four used function pointers retain three exact owned Vec destructor instantiations and File teardown; LLVM only; no executable/run/grant')
        preimages=[h.canonical(closure),h.counted(argv),h.counted([k+'='+v for k,v in sorted(env.items())])]
        for n,b in zip(('compiled-manifest.json','argv.bin','environment.bin'),preimages): (D/n).write_bytes(b)
        keys=dict(zip(h.KEYS,[h.sha(x) for x in preimages]+[compiler_sha,h.sha(version)]))
        h.put('binding.json',dict(source_tree_sha256=h.TREE,host_tree_sha256=host['tree_sha256'],compile_identity_keys=keys,target='aarch64-apple-darwin',python_version=sys.version,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),product_runtime=False))
        stdout,stderr,rec=h.run('compiler',argv,env|keys,60)
        assert rec['exit_code']==0 and output.exists(), 'Do not retry without root coordination; preserve diagnostics.'
        for n,raw in [('source146.ll',output.read_bytes()),('compiler.stdout',stdout)]:
            packed=gzip.compress(raw,mtime=0);(D/(n+'.gz')).write_bytes(packed)
            h.put(n+'-archive.json',dict(raw_bytes=len(raw),raw_sha256=h.sha(raw),archive_bytes=len(packed),archive_sha256=h.sha(packed),full_output_retained=True))
        (D/'compiler.stdout').unlink()
        complete=True
    finally:
        files=[p for p in work.rglob('*') if p.is_file()]
        inventory=[dict(path=str(p.relative_to(work)),bytes=p.stat().st_size,sha256=h.sha(p.read_bytes())) for p in files]
        receipts=[json.loads((D/(label+'-receipt.json')).read_text()) for label in ('compiler-version','compiler') if (D/(label+'-receipt.json')).exists()]
        reaped=all(r['direct_child_waited'] and r['owned_group_absent'] for r in receipts)
        if reaped: shutil.rmtree(work)
        h.put('compiler-cleanup.json',dict(completed=complete,command_children_waited_and_groups_absent=reaped,owned_scratch_removed=not work.exists(),removed_files=len(inventory) if reaped else 0,removed_bytes=sum(x['bytes'] for x in inventory) if reaped else 0,scratch_inventory=inventory,compiler_only=True,native_or_product_runtime=False))
    print(json.dumps(dict(status='passed',seconds=rec['elapsed_seconds'],source_members=146,append_only_source_members=2,used_drop_pointers=4,LLVM_only=True,runtime=False)))

if __name__=='__main__': main()
