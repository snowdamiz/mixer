#!/usr/bin/env python3
"""Bounded host-only command recorder; does not select any full reactor run."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, sys, time

H = Path(__file__).resolve().parent
label, name, *args = sys.argv[1:]
assert label in ('baseline', 'candidate')
assert name and '/' not in name
out = H/'commands'/name
out.mkdir(parents=True, exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=json.loads((H/'baseline-manifest.json').read_text())
manifest={n:sha(H/label/n) for n in inputs}
(out/'source-manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
env=os.environ.copy()
env.update(CARGO_BUILD_JOBS='2',CARGO_INCREMENTAL='0',CARGO_NET_OFFLINE='true',CARGO_TARGET_DIR=str(H/'owned-target'/label),RUST_TEST_THREADS='1',TMPDIR=str(H/'owned-tmp'/label))
Path(env['TMPDIR']).mkdir(parents=True,exist_ok=True)
toolchain=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
env['PATH']=str(toolchain)+':'+env.get('PATH','/usr/bin:/bin')
argv=[str(toolchain/'cargo'),*args]
began=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic()
with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
    result=subprocess.run(argv,cwd=H/label,env=env,stdout=stdout,stderr=stderr,timeout=240)
receipt={'schema':1,'argv':argv,'cwd':str(H/label),'beganUTC':began,'elapsedSeconds':time.monotonic()-start,'exitCode':result.returncode,'sourceManifestSHA256':sha(out/'source-manifest.json'),'stdoutSHA256':sha(out/'stdout'),'stderrSHA256':sha(out/'stderr'),'environment':{k:env[k] for k in ['PATH','CARGO_BUILD_JOBS','CARGO_INCREMENTAL','CARGO_NET_OFFLINE','CARGO_TARGET_DIR','RUST_TEST_THREADS','TMPDIR']},'scope':'finite host cache tests; no full Swift reactor, native, device or guest instantiation selected'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'name':name,'exitCode':result.returncode,'elapsedSeconds':receipt['elapsedSeconds']}))
print((out/'stdout').read_text()[-10000:])
print((out/'stderr').read_text()[-5000:])
sys.exit(result.returncode)
