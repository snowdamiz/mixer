#!/usr/bin/env python3
"""One additional filtered tie control; no repeated broad test contexts."""
from pathlib import Path,PurePosixPath
import datetime,hashlib,json,os,subprocess,tarfile,time
H=Path(__file__).resolve().parent;ROOT=H.parent.parent;P=ROOT/'verification/swift-cache-retention-candidate';D=H/'owned-source'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
assert not D.exists()
expected=json.loads((P/'candidate-manifest.json').read_text())
with tarfile.open(P/'candidate-source.tar.gz','r:gz')as archive:
    members=archive.getmembers();assert len(members)==len(expected)==len(set(m.name for m in members))==132
    assert sum(m.size for m in members)<32*1024*1024 and set(m.name for m in members)==set(expected)
    for m in members:
        n=PurePosixPath(m.name);assert m.isfile() and not n.is_absolute() and '..' not in n.parts and m.size<12*1024*1024
        b=archive.extractfile(m).read();assert hashlib.sha256(b).hexdigest()==expected[m.name]
        p=D.joinpath(*n.parts);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
target=D/'src/experimental_swift_reactor/cache_tests.rs';target.write_bytes(target.read_bytes()+b'\n'+(H/'independent-tie-probe.rs').read_bytes())
manifest={n:sha(D/n)for n in expected}
out=H/'commands/independent-ties';out.mkdir(parents=True,exist_ok=False);write(out/'source-manifest.json',manifest)
tool=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
env=os.environ.copy();env.update(PATH=str(tool)+':'+env.get('PATH','/usr/bin:/bin'),CARGO_BUILD_JOBS='2',CARGO_INCREMENTAL='0',CARGO_NET_OFFLINE='true',CARGO_TARGET_DIR=str(H/'owned-target'),RUST_TEST_THREADS='1',TMPDIR=str(H/'owned-tmp'));Path(env['TMPDIR']).mkdir(exist_ok=True)
argv=[str(tool/'cargo'),'test','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor','--release','experimental_swift_reactor::cache_tests::retention_review_equal_ages_and_all_pinned','--','--nocapture','--test-threads=1']
start=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat()
with(out/'stdout').open('wb')as stdout,(out/'stderr').open('wb')as stderr:r=subprocess.run(argv,cwd=D,env=env,stdout=stdout,stderr=stderr,timeout=240)
write(out/'receipt.json',{'schema':1,'argv':argv,'cwd':str(D),'beganUTC':began,'elapsedSeconds':time.monotonic()-start,'exitCode':r.returncode,'sourceManifestSHA256':sha(out/'source-manifest.json'),'stdoutSHA256':sha(out/'stdout'),'stderrSHA256':sha(out/'stderr'),'environment':{k:env[k]for k in ['PATH','CARGO_BUILD_JOBS','CARGO_INCREMENTAL','CARGO_NET_OFFLINE','CARGO_TARGET_DIR','RUST_TEST_THREADS','TMPDIR']},'scope':'One additional independent finite equal-age/all-pinned method only.'})
print(json.dumps({'exitCode':r.returncode,'elapsedSeconds':time.monotonic()-start}));print((out/'stdout').read_text());print((out/'stderr').read_text()[-3000:]);raise SystemExit(r.returncode)
