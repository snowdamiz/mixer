#!/usr/bin/env python3
"""Independent review runner. Writes only its own packet and unique scratch."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,re,subprocess,sys,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRODUCER=HERE.parent/'swift-memory-helper-behavior'
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(enc(x)).hexdigest()
def manifest(vm):
 paths=[vm/'Cargo.toml',vm/'Cargo.lock']
 for d in ['src','tests','include']:paths+=sorted(p for p in (vm/d).rglob('*') if p.is_file())
 return {str(p.relative_to(vm)):sha(p) for p in paths}
def run(name,args,vm=None,extra=None):
 directory=HERE/'commands'/name;directory.mkdir(parents=True,exist_ok=False)
 env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']);env.pop('RUSTFLAGS',None);env.pop('RUSTC_BOOTSTRAP',None)
 if vm:env['CARGO_TARGET_DIR']=str(SCRATCH/('target-'+name if 'mir' in name else 'target-'+vm.parent.name))
 if extra:env.update(extra)
 before=manifest(vm) if vm else None
 if before:(directory/'source-manifest.json').write_bytes(enc(before))
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 p=subprocess.run(args,cwd=vm or ROOT,env=env,capture_output=True,timeout=900)
 for stream in ['stdout','stderr']:(directory/(stream+'.gz')).write_bytes(gzip.compress(getattr(p,stream),mtime=0))
 after=manifest(vm) if vm else None
 executables=[]
 for value in re.findall(r'Running[^\n]*\((/[^)]+)\)',p.stderr.decode(errors='replace'))+re.findall(r'Running `(/[^`]+)`',p.stderr.decode(errors='replace')):
  path=Path(value)
  if path.is_file() and os.access(path,os.X_OK):executables.append(dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size))
 receipt=dict(argv=args,cwd=str(vm or ROOT),environment={k:env[k] for k in ['PATH','CARGO_TARGET_DIR','RUSTFLAGS','RUSTC_BOOTSTRAP'] if k in env},startedUTC=start,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,sourceClosure=digest(before) if before else None,sourceUnchanged=before==after,stdoutSHA256=hashlib.sha256(p.stdout).hexdigest(),stderrSHA256=hashlib.sha256(p.stderr).hexdigest(),executables=executables)
 (directory/'receipt.json').write_bytes(enc(receipt));print(name,p.returncode,flush=True)
 if p.returncode:print(p.stdout.decode(errors='replace')[-4000:]+p.stderr.decode(errors='replace')[-8000:],flush=True)
 assert before==after
 return p
if not (HERE/'session.json').exists():
 SCRATCH=Path('/tmp/mixer-memory-independent-review-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));SCRATCH.mkdir()
 (HERE/'session.json').write_bytes(enc(dict(scratch=str(SCRATCH),createdUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),gitHead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())))
else:SCRATCH=Path(json.loads((HERE/'session.json').read_text())['scratch'])
if __name__=='__main__':
 for name,args in [('producer-verify',['python3','-B',str(PRODUCER/'verify.py'),'--live-baseline']),('tool-rustc',['rustc','-vV']),('tool-cargo',['cargo','-V']),('tool-python',['python3','--version']),('tool-host',['uname','-a']),('tool-git',['git','rev-parse','HEAD'])]:assert run(name,args).returncode==0
 for label in ['baseline','candidate','metadata-baseline','metadata-candidate','parity-baseline','parity-candidate']:
  with tarfile.open(PRODUCER/(label+'-source.tar.gz')) as t:
   assert all(m.isfile() and m.name.startswith('vm/') and '..' not in Path(m.name).parts for m in t.getmembers());t.extractall(SCRATCH/label,filter='data')
  actual=manifest(SCRATCH/label/'vm');expected=json.loads((PRODUCER/(label+'-source-manifest.json')).read_text());assert actual==expected
 print('scratch',SCRATCH,flush=True)
