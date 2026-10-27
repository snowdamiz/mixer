"""Force exact original closure monomorphizations; compile only, never run."""
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

D = Path(__file__).resolve().parent
R = D.parents[1]
V = R / 'verification'
HELPER = V / 'swift-guarded-snapshot-source146-callee-storage-layouts/query-named.py'
spec = importlib.util.spec_from_file_location('frozen_layout_command_helpers', HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
h.D = D


def main():
    assert not (D/'compiler-receipt.json').exists()
    # The helpers were frozen with the successful21 named query packet.
    prior = V/'swift-guarded-snapshot-source146-callee-storage-layouts'
    assert h.sha((prior/'seal.json').read_bytes()) == '9e2cd764548188b30c93d045fdc72d59c771a4cd489858d6340f131bc67b1001'
    for row in json.loads((prior/'seal.json').read_text())['members']:
        h.checked_file(row, prior/row['path'])
    base = V/'swift-guarded-snapshot-loader-work-source146'
    manifest = json.loads((base/'source146-manifest.json').read_text())
    refs = json.loads((base/'source-reference-map.json').read_text())['members']
    assert len(refs) == 146 and manifest['tree_sha256'] == h.TREE
    assert h.sha(h.canonical(manifest['members'])) == h.TREE
    assert [(r['path'],r['bytes'],r['sha256']) for r in refs] == [(r['path'],r['bytes'],r['sha256']) for r in manifest['members']]
    sources = {r['path']:h.checked_file(r,R/r['source']) for r in refs}
    host = json.loads((base/'host11-manifest.json').read_text())
    assert len(host['members']) == 11 and h.sha(h.canonical(host['members'])) == host['tree_sha256']
    for row in host['members']:
        h.checked_file(row,V/'swift-real-profile-loader-binding/host'/row['path'])
    additions = {
        'src/experimental_swift_reactor/control.rs': '''
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static SOURCE146_CLOSURE_LAYOUT_CORE_V1: fn(AdoptionBodyV1, SwiftRunBudget, Instant, Cancellation) -> Result<(RuntimeControl, AdoptedProof), SnapshotPreScopeFailureV1> = RuntimeControl::adopt_body_core_v1::<SnapshotAdoptionV1>;
''',
        'src/experimental_swift_reactor/retained_profile_loader_v1.rs': '''
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static SOURCE146_CLOSURE_LAYOUT_BYTES4096_V1: fn(&mut Bytes<4096>, &[u8]) -> Result<(), LoaderFailureV1> = Bytes::<4096>::put;
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static SOURCE146_CLOSURE_LAYOUT_BYTES16384_V1: fn(&mut Bytes<16384>, &[u8]) -> Result<(), LoaderFailureV1> = Bytes::<16384>::put;
''',
    }
    for path, fragment in additions.items():
        (D/(Path(path).stem+'-append.inc.rs')).write_text(fragment)
        sources[path] += fragment.encode()
    compiled = [dict(path=n,bytes=len(b),sha256=h.sha(b)) for n,b in sorted(sources.items(),key=lambda p:Path(p[0]))]
    original = {r['path']:r for r in manifest['members']}
    assert {r['path'] for r in compiled if r != original[r['path']]} == set(additions)
    work = D/'owned-work'
    assert not work.exists()
    work.mkdir()
    completed = False
    try:
        vm = work/'vm'
        for name, data in sources.items():
            p=vm/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        env = dict(PATH='/usr/bin:/bin',TMPDIR=str(work),CARGO_MANIFEST_DIR=str(vm),RUSTC_BOOTSTRAP='1',SDKROOT='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
        version,_,vr = h.run('compiler-version',[str(h.COMPILER),'--version','--verbose'],env,10)
        assert vr['exit_code']==0 and h.sha(version)=='352d6857968e80a6357a926ac685b9b07f77c479aaafde33e73a53945e802909'
        compiler_sha=h.sha(h.COMPILER.read_bytes())
        assert compiler_sha=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
        output=work/'source146.ll'
        argv=[str(h.COMPILER),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind','-C','codegen-units=1','-Zmir-opt-level=0','-Zprint-type-sizes','--error-format=json']
        for feature in ('experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache'):
            argv+=['--cfg','feature="'+feature+'"']
        argv+=['--cfg','mixer_bootstrap_one_fixture_v1','--crate-type','rlib',str(vm/'src/lib.rs'),'--emit=llvm-ir='+str(output)]
        closure=dict(schema=1,source_manifest=manifest,compiled_source_members=compiled,compiled_tree_sha256=h.sha(h.canonical(compiled)),host_support=host,additions={p:dict(bytes=len(f.encode()),sha256=h.sha(f.encode())) for p,f in additions.items()},compiler_sha256=compiler_sha,compiler_version_sha256=h.sha(version),script_sha256=h.sha(Path(__file__).read_bytes()),frozen_helper_sha256=h.sha(HELPER.read_bytes()),original_source146_bodies_unchanged=True,original_closure_source_spans_unchanged=True,query_scope='Exact original monomorphized anonymous closure size/alignment; no executable/run/grant')
        preimages=[h.canonical(closure),h.counted(argv),h.counted([k+'='+v for k,v in sorted(env.items())])]
        for name,data in zip(('compiled-manifest.json','argv.bin','environment.bin'),preimages):(D/name).write_bytes(data)
        keys=dict(zip(h.KEYS,[h.sha(x) for x in preimages]+[compiler_sha,h.sha(version)]))
        h.put('binding.json',dict(source_tree_sha256=h.TREE,host_tree_sha256=host['tree_sha256'],compile_identity_keys=keys,python_version=sys.version,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),product_runtime=False))
        stdout,stderr,rec=h.run('compiler',argv,env|keys,60)
        assert rec['exit_code']==0 and output.exists(), 'Compiler evidence failed; preserve raw diagnostics.'
        raw=output.read_bytes();archive=gzip.compress(raw,mtime=0)
        (D/'source146.ll.gz').write_bytes(archive)
        h.put('llvm-archive.json',dict(raw_bytes=len(raw),raw_sha256=h.sha(raw),archive_bytes=len(archive),archive_sha256=h.sha(archive),full_output_retained=True))
        completed=True
    finally:
        items=[p for p in work.rglob('*') if p.is_file()]
        inventory=[dict(path=str(p.relative_to(work)),bytes=p.stat().st_size,sha256=h.sha(p.read_bytes())) for p in items]
        receipts=[json.loads(p.read_text()) for p in D.glob('*-receipt.json')]
        reaped=all(r.get('direct_child_waited') and r.get('owned_group_absent') for r in receipts)
        if reaped:shutil.rmtree(work)
        h.put('cleanup.json',dict(completed=completed,command_children_waited_and_groups_absent=reaped,owned_scratch_removed=not work.exists(),removed_files=len(inventory) if reaped else 0,removed_bytes=sum(r['bytes'] for r in inventory) if reaped else 0,scratch_inventory=inventory,product_or_native_runtime=False))
    print(json.dumps(dict(status='compiler-output-retained',seconds=rec['elapsed_seconds'],LLVM_bytes=len(raw),stdout_bytes=len(stdout),product_runtime=False)))


if __name__=='__main__':main()
