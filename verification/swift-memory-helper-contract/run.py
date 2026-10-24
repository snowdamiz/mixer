#!/usr/bin/env python3
from pathlib import Path
import json,os,subprocess,datetime,hashlib,sys,importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('builder',HERE/'build_overlay.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
SESSION=json.loads((HERE/'session.json').read_text());SCRATCH=Path(SESSION['scratch'])
def run(name,args,vm=None,extra=None):
 out=HERE/'commands'/name;out.mkdir(parents=True,exist_ok=False)
 env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']);env.pop('RUSTFLAGS',None);env.pop('RUSTC_BOOTSTRAP',None)
 if vm:env['CARGO_TARGET_DIR']=str(SCRATCH/('target-'+name))
 if extra:env.update(extra)
 cwd=Path(vm or HERE.parents[1]);before=b.manifest(cwd) if vm else None
 if before:(out/'source-manifest.json').write_bytes(b.enc(before))
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(args,cwd=cwd,env=env,capture_output=True,timeout=900)
 for stream in ['stdout','stderr']:(out/stream).write_bytes(getattr(p,stream))
 after=b.manifest(cwd) if vm else None
 receipt=dict(argv=args,cwd=str(cwd),environment={k:env[k] for k in ['PATH','CARGO_TARGET_DIR','RUSTFLAGS','RUSTC_BOOTSTRAP'] if k in env},startedUTC=start,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,sourceTreeSHA256=b.digest(before) if before else None,sourceUnchanged=before==after,stdoutSHA256=b.sha(out/'stdout'),stderrSHA256=b.sha(out/'stderr'))
 (out/'receipt.json').write_bytes(b.enc(receipt));print(name,p.returncode,flush=True)
 if p.returncode:print(p.stderr.decode(errors='replace')[-8000:],flush=True)
 assert before==after
 return p
if __name__=='__main__':
 name,label,*args=sys.argv[1:];p=run(name,args,SCRATCH/label if label!='-' else None);sys.exit(p.returncode)
