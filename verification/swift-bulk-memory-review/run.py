#!/usr/bin/env python3
from pathlib import Path
import datetime,gzip,hashlib,json,os,re,subprocess,sys,tarfile,tempfile
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]; PACKET=HERE.parent/'swift-bulk-memory'
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def manifest(vm):
 paths=[vm/'Cargo.toml',vm/'Cargo.lock']
 for d in ['src','tests','include']:paths+=sorted(p for p in (vm/d).rglob('*')if p.is_file())
 return {str(p.relative_to(vm)):sha(p)for p in paths}
def digest(m):return hashlib.sha256(enc(m)).hexdigest()
def run(name,args,vm=None,extra=None):
 out=HERE/'commands'/name;out.mkdir(parents=True,exist_ok=False)
 env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']);env.pop('RUSTFLAGS',None);env.pop('RUSTC_BOOTSTRAP',None)
 if vm:env['CARGO_TARGET_DIR']=str(SCRATCH/'target')
 if extra:env.update(extra)
 cwd=Path(vm or ROOT);before=manifest(cwd)if vm else None
 if before:(out/'source-manifest.json').write_bytes(enc(before))
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 p=subprocess.run(args,cwd=cwd,env=env,capture_output=True,timeout=900)
 for stream in ['stdout','stderr']:(out/stream).write_bytes(getattr(p,stream))
 after=manifest(cwd)if vm else None
 binaries=[]
 for s in re.findall(r'Running[^\n]*\((/[^)]+)\)',p.stderr.decode(errors='replace'))+re.findall(r'Running `(/[^`]+)`',p.stderr.decode(errors='replace')):
  q=Path(s)
  if q.is_file()and os.access(q,os.X_OK):binaries.append(dict(path=str(q),sha256=sha(q),bytes=q.stat().st_size))
 receipt=dict(argv=args,cwd=str(cwd),startedUTC=start,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,sourceTreeSHA256=digest(before)if before else None,sourceUnchanged=before==after,sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),environment={k:env[k]for k in ['PATH','CARGO_TARGET_DIR','RUSTFLAGS','RUSTC_BOOTSTRAP']if k in env},stdoutSHA256=sha(out/'stdout'),stderrSHA256=sha(out/'stderr'),executables=binaries)
 (out/'receipt.json').write_bytes(enc(receipt));print(name,p.returncode,flush=True)
 if p.returncode:print(p.stderr.decode(errors='replace')[-5000:],flush=True)
 assert before==after
 return p
if (HERE/'session.json').exists():SCRATCH=Path(json.loads((HERE/'session.json').read_text())['scratch'])
else:
 SCRATCH=Path(tempfile.mkdtemp(prefix='mixer-swift-bulk-review-'))
 (HERE/'session.json').write_bytes(enc(dict(scratch=str(SCRATCH),startedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())))
 for label in ['baseline','candidate']:
  dest=SCRATCH/label;dest.mkdir()
  with tarfile.open(PACKET/(label+'-source.tar.gz'),'r:gz')as t:
   assert all(m.isfile()and not Path(m.name).is_absolute()and'..'not in Path(m.name).parts for m in t.getmembers())
   t.extractall(dest,filter='data')
  assert manifest(dest)==json.loads((PACKET/(label+'-source-manifest.json')).read_text())
 (HERE/'source-diff.json').write_bytes(enc({n:dict(baseline=manifest(SCRATCH/'baseline').get(n),candidate=manifest(SCRATCH/'candidate').get(n))for n in sorted(set(manifest(SCRATCH/'baseline'))|set(manifest(SCRATCH/'candidate')))if manifest(SCRATCH/'baseline').get(n)!=manifest(SCRATCH/'candidate').get(n)}))
if __name__=='__main__':
 name,label,*args=sys.argv[1:];p=run(name,args,SCRATCH/label if label!='-'else None);sys.exit(p.returncode)
