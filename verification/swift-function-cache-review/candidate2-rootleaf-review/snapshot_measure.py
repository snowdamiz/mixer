#!/usr/bin/env python3
"""Capture evolving candidate2 explicitly; this is not an implementation freeze."""
from pathlib import Path
import hashlib,io,json,os,subprocess,tarfile,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];TREE=HERE/'tree'
def sha(b):return hashlib.sha256(b).hexdigest()
assert not TREE.exists();TREE.mkdir()
baseline='39199ae5475de5d03926807ce60add5dcb0741c2'
archive=subprocess.check_output(['git','archive',baseline,'vm'],cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(TREE,filter='data')
sources={}
paths=[p for p in (ROOT/'vm').rglob('*') if p.is_file() and ('target' not in p.relative_to(ROOT/'vm').parts)]
# Limit the evolving overlay to Rust and crate manifests; baseline fixtures are
# complete and separately recorded. No device or full guest target is accessed.
for p in paths:
    rel=p.relative_to(ROOT)
    if p.suffix=='.rs' or rel.name in ['Cargo.toml','Cargo.lock']:
        data=p.read_bytes();target=TREE/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);sources[str(rel)]=sha(data)
assert all(sha((ROOT/p).read_bytes())==digest for p,digest in sources.items()),'sources moved during capture'
test_source=TREE/'vm/src/experimental_swift_reactor/cache_tests.rs'
test_source.write_bytes(test_source.read_bytes()+b'\n#[test]\nfn review_only_rootleaf_measurement(){let bytes=fixture(0,&[0,0x0b],100);let(mut c,a)=adopt(&bytes,SwiftRunBudget::default());super::cache::review_rootleaf_measure(&mut c);c.drop_proof(a).unwrap();let _=c.finish_owned_cleanup(None);}\n')
cache=TREE/'vm/src/experimental_swift_reactor/cache.rs';cache.write_bytes(cache.read_bytes()+('\n#[cfg(test)]\ninclude!('+json.dumps(str(HERE/'measure.rs'))+');\n').encode())
env=os.environ|{'PATH':'/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],'CARGO_TARGET_DIR':str(HERE/'build'),'TMPDIR':str(HERE.parent/'tmp')}
commands=[]
for mode in ['debug','release']:
    argv=['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--all-features','--lib']
    if mode=='release':argv+=['--release']
    argv+=['experimental_swift_reactor::cache_tests::review_only_rootleaf_measurement','--','--exact','--nocapture']
    start=time.monotonic();p=subprocess.run(argv,cwd=TREE,env=env,capture_output=True,text=True);out=p.stdout+p.stderr
    log=f'measured-{mode}.log';(HERE/log).write_text(out)
    commands.append({'argv':argv,'cwd':str(TREE),'exit_code':p.returncode,'seconds':time.monotonic()-start,'output':log,'output_sha256':sha(out.encode())})
    (HERE/'measurement-receipt.json').write_text(json.dumps({'scope':'provisional candidate2 preflight type/closure layout audit only','source_before_test_overlay':sources,'source_digest':sha(json.dumps(sources,sort_keys=True).encode()),'derived_sources':{str(cache.relative_to(TREE)):sha(cache.read_bytes()),str(test_source.relative_to(TREE)):sha(test_source.read_bytes())},'full_vm_input_manifest':{str(p.relative_to(TREE)):sha(p.read_bytes()) for p in (TREE/'vm').rglob('*') if p.is_file()},'probe_sha256':sha((HERE/'measure.rs').read_bytes()),'commands':commands},indent=2)+'\n')
    print(out[-5000:],flush=True)
    if p.returncode!=0:raise SystemExit(1)
