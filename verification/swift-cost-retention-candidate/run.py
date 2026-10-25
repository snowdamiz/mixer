#!/usr/bin/env python3
"""Bounded host-only command recorder; never invokes a reactor workload."""
import datetime, hashlib, json, os, pathlib, subprocess, sys, time
OUT=pathlib.Path(__file__).resolve().parent
TOOL=pathlib.Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
def sha(data): return hashlib.sha256(data).hexdigest()
def write(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
if len(sys.argv)<4: raise SystemExit('run.py MODE LABEL CARGO_ARGS...')
mode,label,*args=sys.argv[1:]
assert mode in ['baseline','candidate']
assert '/' not in label and args[0]=='test' and '--offline' in args
assert not any('full_' in arg or 'actual' in arg for arg in args)
dest=OUT/'commands'/label
dest.mkdir(parents=True,exist_ok=False)
source=OUT/'.scratch'/mode
manifest={str(p.relative_to(source)):sha(p.read_bytes()) for p in sorted(source.rglob('*')) if p.is_file()}
write(dest/'source-manifest.json',manifest)
tmp=OUT/'.scratch'/f'tmp-{mode}'; tmp.mkdir(exist_ok=True)
env=os.environ.copy()
env.update(PATH=str(TOOL)+os.pathsep+env.get('PATH',''),RUSTC=str(TOOL/'rustc'),CARGO_NET_OFFLINE='true',CARGO_BUILD_JOBS='1',CARGO_TARGET_DIR=str(OUT/'.scratch'/f'build-{mode}'),TMPDIR=str(tmp))
argv=[str(TOOL/'cargo'),*args]
write(dest/'command.json',{'argv':argv,'cwd':str(source),'environmentOverrides':{k:env[k] for k in ['PATH','RUSTC','CARGO_NET_OFFLINE','CARGO_BUILD_JOBS','CARGO_TARGET_DIR','TMPDIR']},'timeoutSeconds':180,'sourceManifestSHA256':sha((dest/'source-manifest.json').read_bytes()),'beganUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()})
start=time.monotonic()
with (dest/'stdout').open('wb') as stdout,(dest/'stderr').open('wb') as stderr:
 p=subprocess.Popen(argv,cwd=source,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
 try: code=p.wait(timeout=180); timed_out=False
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,15)
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,9);p.wait()
  code=p.returncode; timed_out=True
write(dest/'result.json',{'exitCode':code,'timedOut':timed_out,'elapsedSeconds':time.monotonic()-start,'pid':p.pid,'stdoutSHA256':sha((dest/'stdout').read_bytes()),'stderrSHA256':sha((dest/'stderr').read_bytes())})
print(json.dumps({'label':label,'exitCode':code,'elapsedSeconds':time.monotonic()-start,'stdoutTail':(dest/'stdout').read_text()[-2200:],'stderrTail':(dest/'stderr').read_text()[-1800:]}))
raise SystemExit(0 if code==0 and not timed_out else 1)
