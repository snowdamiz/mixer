#!/usr/bin/env python3
"""Record isolated commands and exact source closures; never touch live VM."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,re,subprocess,sys,tarfile
HERE=Path(__file__).resolve().parent
SESSION=json.loads((HERE/'session.json').read_text());SCRATCH=Path(SESSION['scratch'])
enc=lambda obj:(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
sha=lambda data:hashlib.sha256(data).hexdigest()
def manifest(vm):
 paths=[vm/'Cargo.toml',vm/'Cargo.lock']
 for folder in ['src','tests','include']:paths+=sorted(p for p in(vm/folder).rglob('*')if p.is_file())
 return {str(p.relative_to(vm)):sha(p.read_bytes())for p in paths}
def digest(m):return sha(enc(m))
def target_dir(vm,argv,extra=None,name=''):
 features='all'if'--all-features'in argv else argv[argv.index('--features')+1]if'--features'in argv else'default'
 profile='release'if'--release'in argv else'debug'
 mode='unit'if len(argv)>1 and argv[1]=='test'and'--lib'in argv else'production'
 role='layout'if name.startswith('layout-')else'mir'if name.endswith('-mir')else'runtime'
 context=re.sub(r'[^A-Za-z0-9_-]','_',features+'-'+profile+'-'+mode+'-'+role)
 return SCRATCH/('target-source-'+digest(manifest(Path(vm))))/context
def run(name,argv,vm=None,extra=None):
 cwd=Path(vm or HERE.parents[1]);out=HERE/'commands'/name;out.mkdir(parents=True,exist_ok=False)
 env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']);env.pop('RUSTFLAGS',None);env.pop('RUSTC_BOOTSTRAP',None)
 if vm:env['CARGO_TARGET_DIR']=str(target_dir(cwd,argv,extra,name))
 if extra:env.update(extra)
 before=manifest(cwd)if vm else None
 if before:
  (out/'source-manifest.json').write_bytes(enc(before));(HERE/'sources').mkdir(exist_ok=True);archive=HERE/'sources'/(digest(before)+'.tar.gz')
  if not archive.exists():
   with tarfile.open(archive,'w:gz')as tar:
    for key in before:tar.add(cwd/key,arcname=key)
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=900)
 for stream in ['stdout','stderr']:(out/(stream+'.gz')).write_bytes(gzip.compress(getattr(p,stream),mtime=0))
 after=manifest(cwd)if vm else None
 receipt=dict(argv=argv,cwd=str(cwd),environment={k:env[k]for k in['PATH','CARGO_TARGET_DIR','RUSTFLAGS','RUSTC_BOOTSTRAP']if k in env},startedUTC=started,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,sourceTreeSHA256=digest(before)if before else None,sourceUnchanged=before==after,stdoutSHA256=sha(p.stdout),stderrSHA256=sha(p.stderr))
 receipt['executables']=[]
 for name in re.findall(r'Running[^\n]*\((/[^)]+)\)',p.stderr.decode(errors='replace'))+re.findall(r'Running `(/[^`]+)`',p.stderr.decode(errors='replace')):
  binary=Path(name)
  if binary.is_file()and os.access(binary,os.X_OK):receipt['executables'].append(dict(path=name,sha256=sha(binary.read_bytes()),bytes=binary.stat().st_size))
 (out/'receipt.json').write_bytes(enc(receipt));assert before==after;print(out.name,p.returncode,flush=True)
 if p.returncode:print(p.stderr.decode(errors='replace')[-12000:],flush=True)
 return p
if __name__=='__main__':
 label,source,*argv=sys.argv[1:];sys.exit(run(label,argv,SCRATCH/source/'vm'if source!='-'else None).returncode)
