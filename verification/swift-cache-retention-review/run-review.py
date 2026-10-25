#!/usr/bin/env python3
"""Restore sealed sources only inside this lane; append independent finite probes."""
from pathlib import Path, PurePosixPath
import datetime, hashlib, json, os, subprocess, sys, tarfile, time
H=Path(__file__).resolve().parent
ROOT=H.parent.parent
P=ROOT/'verification/swift-cache-retention-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
tool=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
assert sha(P/'seal.json')=='6507e85f869d0f1a052b9e8e5356ac07910c67813f87b309fa6a5b348e803c13'
verify=subprocess.run([sys.executable,str(P/'verify.py')],cwd=ROOT,capture_output=True,text=True,check=True)
(H/'producer-verification.stdout').write_text(verify.stdout)
expected=json.loads((P/'candidate-manifest.json').read_text())
destination=H/'owned-source'
assert not destination.exists()
with tarfile.open(P/'candidate-source.tar.gz','r:gz') as archive:
    members=archive.getmembers()
    assert len(members)==len(expected)==132
    assert sum(m.size for m in members)<32*1024*1024
    assert len(set(m.name for m in members))==len(members)
    assert set(m.name for m in members)==set(expected)
    for m in members:
        n=PurePosixPath(m.name)
        assert m.isfile() and not n.is_absolute() and '..' not in n.parts and m.size<12*1024*1024
        b=archive.extractfile(m).read()
        assert hashlib.sha256(b).hexdigest()==expected[m.name]
        output=destination.joinpath(*n.parts)
        output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(b)
assert {n:sha(destination/n) for n in expected}==expected
target=destination/'src/experimental_swift_reactor/cache_tests.rs'
target.write_bytes(target.read_bytes()+b'\n'+(H/'independent-probes.rs').read_bytes())
manifest={n:sha(destination/n) for n in expected}
write(H/'review-source-manifest.json',manifest)
write(H/'inputs.json',{'schema':1,'producerSealSHA256':sha(P/'seal.json'),'candidateManifestSHA256':sha(P/'candidate-manifest.json'),'baselineClosureSHA256':sha(P/'baseline-manifest.json'),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'archiveFiles':132,'archiveExtractedBytes':sum(m.size for m in members),'reviewSourceManifestSHA256':sha(H/'review-source-manifest.json'),'probeSHA256':sha(H/'independent-probes.rs'),'scope':'Independent finite correctness/accounting only; no full reactor, guest execution, live VM, network, native or GA attempt.'})
env=os.environ.copy()
env.update(PATH=str(tool)+':'+env.get('PATH','/usr/bin:/bin'),CARGO_BUILD_JOBS='2',CARGO_INCREMENTAL='0',CARGO_NET_OFFLINE='true',CARGO_TARGET_DIR=str(H/'owned-target'),RUST_TEST_THREADS='1',TMPDIR=str(H/'owned-tmp'))
Path(env['TMPDIR']).mkdir(exist_ok=True)
tools={}
for name,argv in [('rustc',[str(tool/'rustc'),'--version','--verbose']),('cargo',[str(tool/'cargo'),'--version']),('python',[sys.executable,'--version']),('host',['uname','-a'])]:
    r=subprocess.run(argv,capture_output=True,text=True,check=True);tools[name]={'argv':argv,'output':r.stdout.strip()}
write(H/'tools.json',tools)
argv=[str(tool/'cargo'),'test','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor','--release','experimental_swift_reactor::cache_tests::retention_review_','--','--nocapture','--test-threads=1']
start=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (H/'stdout').open('wb') as out,(H/'stderr').open('wb') as err:
    r=subprocess.run(argv,cwd=destination,env=env,stdout=out,stderr=err,timeout=240)
write(H/'receipt.json',{'schema':1,'argv':argv,'cwd':str(destination),'beganUTC':began,'elapsedSeconds':time.monotonic()-start,'exitCode':r.returncode,'sourceManifestSHA256':sha(H/'review-source-manifest.json'),'stdoutSHA256':sha(H/'stdout'),'stderrSHA256':sha(H/'stderr'),'environment':{k:env[k] for k in ['PATH','CARGO_BUILD_JOBS','CARGO_INCREMENTAL','CARGO_NET_OFFLINE','CARGO_TARGET_DIR','RUST_TEST_THREADS','TMPDIR']},'scope':'Five independent finite host cache methods only. No full diagnostic or live integration.'})
print(json.dumps({'exitCode':r.returncode,'elapsedSeconds':time.monotonic()-start}))
print((H/'stdout').read_text()[-12000:]);print((H/'stderr').read_text()[-4000:]);sys.exit(r.returncode)
