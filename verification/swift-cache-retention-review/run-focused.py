#!/usr/bin/env python3
"""Rerun only review-owned finite tests; preserve every initial output."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,tarfile,time
H=Path(__file__).resolve().parent;ROOT=H.parent.parent;P=ROOT/'verification/swift-cache-retention-candidate';D=H/'owned-source'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
run_name=sys.argv[1] if len(sys.argv)>1 else 'final'
assert run_name.isidentifier()
prior_path=H/(sys.argv[2] if len(sys.argv)>2 else 'review-source-manifest.json')
assert prior_path.resolve().is_relative_to(H)
prior=json.loads(prior_path.read_text())
assert {n:sha(D/n) for n in prior}==prior
with tarfile.open(P/'candidate-source.tar.gz','r:gz') as archive:
    for name,probe in [('src/experimental_swift_reactor/cache_tests.rs','independent-probes.rs'),('src/experimental/cache/tests.rs','independent-generic-probes.rs')]:
        original=archive.extractfile(name).read()
        assert hashlib.sha256(original).hexdigest()==json.loads((P/'candidate-manifest.json').read_text())[name]
        (D/name).write_bytes(original+b'\n'+(H/probe).read_bytes())
manifest={n:sha(D/n) for n in prior}
tool=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
env=os.environ.copy();env.update(PATH=str(tool)+':'+env.get('PATH','/usr/bin:/bin'),CARGO_BUILD_JOBS='2',CARGO_INCREMENTAL='0',CARGO_NET_OFFLINE='true',CARGO_TARGET_DIR=str(H/'owned-target'),RUST_TEST_THREADS='1',TMPDIR=str(H/'owned-tmp'))
commands=[('independent-swift-'+run_name,['test','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor','--release','experimental_swift_reactor::cache_tests::retention_review_','--','--nocapture','--test-threads=1']),('independent-generic-'+run_name,['test','--lib','--locked','--offline','--no-default-features','--features','experimental-function-cache','--release','experimental::cache::tests::retention_review_generic_','--','--nocapture','--test-threads=1'])]
for name,args in commands:
    out=H/'commands'/name;out.mkdir(parents=True,exist_ok=False);write(out/'source-manifest.json',manifest)
    argv=[str(tool/'cargo'),*args];start=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (out/'stdout').open('wb')as stdout,(out/'stderr').open('wb')as stderr:r=subprocess.run(argv,cwd=D,env=env,stdout=stdout,stderr=stderr,timeout=240)
    write(out/'receipt.json',{'schema':1,'argv':argv,'cwd':str(D),'beganUTC':began,'elapsedSeconds':time.monotonic()-start,'exitCode':r.returncode,'sourceManifestSHA256':sha(out/'source-manifest.json'),'stdoutSHA256':sha(out/'stdout'),'stderrSHA256':sha(out/'stderr'),'environment':{k:env[k]for k in ['PATH','CARGO_BUILD_JOBS','CARGO_INCREMENTAL','CARGO_NET_OFFLINE','CARGO_TARGET_DIR','RUST_TEST_THREADS','TMPDIR']},'scope':'Independent targeted finite host cache probes only; no full diagnostic or broad regression contexts.'})
    print(json.dumps({'name':name,'exitCode':r.returncode,'elapsedSeconds':time.monotonic()-start}),flush=True);print((out/'stdout').read_text()[-10000:],flush=True);print((out/'stderr').read_text()[-3000:],flush=True)
    if r.returncode:sys.exit(r.returncode)
