"""Capture every compiler/runtime attempt, source closure, executable and group."""
from pathlib import Path
import os,sys,hashlib,json,gzip,tarfile,subprocess,signal,datetime,tempfile,shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda x:hashlib.sha256(x).hexdigest()
def manifest(tree):return {str(p.relative_to(tree)):sha(p.read_bytes()) for p in sorted(tree.rglob('*')) if p.is_file() and not any(x in p.relative_to(tree).parts for x in ['target'])}
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(x if isinstance(x,bytes) else enc(x))
def run(argv,tree=None,env_extra=None,label='command',expected=0):
 tree=tree or HERE/'candidate';attempt=HERE/'attempts'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');attempt.mkdir(parents=True)
 before=manifest(tree);save(attempt/'source-manifest.json',before)
 for script in HERE.glob('*.py'):save(attempt/'collector-scripts'/script.name,script.read_bytes())
 with tarfile.open(attempt/'source.tar.gz','w:gz') as t:
  for rel in before:t.add(tree/rel,arcname=rel,recursive=False)
 scratch=Path(tempfile.mkdtemp(prefix='mixer-calls-dispatch-'))
 env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],CARGO_TARGET_DIR=str(scratch/'target'),CARGO_INCREMENTAL='0')
 for k in ['RUSTFLAGS','RUSTC_BOOTSTRAP','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_RUSTFLAGS']:env.pop(k,None)
 if env_extra:env.update(env_extra)
 row={'label':label,'argv':argv,'cwd':str(tree),'environment':{k:v for k,v in env.items() if k in ['PATH','CARGO_TARGET_DIR','CARGO_INCREMENTAL','RUSTC_BOOTSTRAP','RUSTFLAGS']},'sourceClosure':sha(enc(before)),'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 save(attempt/'command.json',row)
 p=subprocess.Popen(argv,cwd=tree,env=env,start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 row['group']=p.pid
 try:
  out,err=p.communicate(timeout=900)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate();row['timedOut']=True
 save(attempt/'stdout.log.gz',gzip.compress(out,mtime=0));save(attempt/'stderr.log.gz',gzip.compress(err,mtime=0))
 row.update(exitCode=p.returncode,stdoutSHA256=sha(out),stderrSHA256=sha(err),expectedExitCode=expected,sourceUnchanged=before==manifest(tree),finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
 groups=subprocess.check_output(['ps','-axo','pid=,pgid=,command='],text=True)
 left=[x for x in groups.splitlines() if len(x.split(None,2))>=2 and x.split(None,2)[1]==str(p.pid)]
 row['remainingGroup']=left
 if left:os.killpg(p.pid,signal.SIGKILL)
 # Always retain compiler outputs and binaries before removing owned scratch.
 artifacts=[]
 for artifact in sorted(scratch.rglob('*')):
  if not artifact.is_file():continue
  if artifact.suffix=='.mir' or (artifact.parent.name=='deps' and artifact.stat().st_mode&0o111 and artifact.suffix==''):
   raw=artifact.read_bytes();name='artifacts/'+str(artifact.relative_to(scratch))+'.gz';save(attempt/name,gzip.compress(raw,mtime=0));artifacts.append({'path':name,'sha256':sha(raw),'bytes':len(raw)})
 save(attempt/'artifacts.json',artifacts);save(attempt/'command.json',row)
 holders=subprocess.run(['lsof','-nP','+D',str(scratch)],capture_output=True)
 save(attempt/'holders.log',holders.stdout+holders.stderr)
 count=sum(x.is_file() for x in scratch.rglob('*'));size=sum(x.stat().st_size for x in scratch.rglob('*') if x.is_file())
 assert not holders.stdout,holders.stdout
 shutil.rmtree(scratch)
 save(attempt/'cleanup.json',{'scratch':str(scratch),'removed':not scratch.exists(),'filesRemoved':count,'logicalBytesRemoved':size,'nativeInstancesCreated':0,'holderCheckEmpty':True,'remainingGroup':left})
 print(str(attempt),flush=True);print(out.decode(errors='replace')[-1000:] if len(out)<100000 else '[large stdout archived]');print(err.decode(errors='replace')[-9000:])
 assert row['sourceUnchanged'] and not left
 return p.returncode,attempt,out,err
if __name__=='__main__':
 code,*_=run(sys.argv[1:]);sys.exit(code)
