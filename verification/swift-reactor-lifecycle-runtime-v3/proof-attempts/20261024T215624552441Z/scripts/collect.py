"""Capture every compiler/runtime attempt, source closure, executable and group."""
from pathlib import Path
import os,sys,hashlib,json,gzip,tarfile,subprocess,signal,datetime,tempfile,shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda x:hashlib.sha256(x).hexdigest()
def manifest(tree):return {str(p.relative_to(tree)):sha(p.read_bytes()) for p in sorted(tree.rglob('*')) if p.is_file() and not any(x in p.relative_to(tree).parts for x in ['target'])}
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(x if isinstance(x,bytes) else enc(x))
def read_json(p):return json.loads(p.read_bytes()if p.exists()else gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes()))
def run(argv,tree=None,env_extra=None,label='command',expected=0,post=None):
 tree=tree or HERE/'candidate';attempt=HERE/'attempts'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');attempt.mkdir(parents=True)
 before=manifest(tree);save(attempt/'source-manifest.json',before)
 authority={}
 for rel in ['verification/swift-reactor-lifecycle-runtime-v2-root-review/v3-ticket-test-repair-selection.json','verification/swift-reactor-lifecycle-runtime-v2/finite-representation-selection.json','docs/swift-reactor-lifecycle-contract.md']:
  data=(ROOT/rel).read_bytes();save(attempt/'authority'/rel,data);authority[rel]=sha(data)
 save(attempt/'authority-bindings.json',authority)
 tools={}
 for executable,args in [('rustc',['-vV']),('cargo',['-V']),('python3',['--version']),('rustfmt',['--version'])]:
  resolved=shutil.which(executable,path='/opt/homebrew/opt/rustup/bin:/Users/andreyyurlov/.local/share/fnm/node-versions/v22.23.3/installation/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin');probe=subprocess.run([resolved,*args],capture_output=True);tools[executable]={'executable':resolved,'executableSHA256':sha(Path(resolved).read_bytes()),'argv':[resolved,*args],'exitCode':probe.returncode,'stdout':probe.stdout.decode(),'stderr':probe.stderr.decode()}
 sysroot=subprocess.check_output(['/opt/homebrew/opt/rustup/bin/rustc','--print','sysroot'],text=True).strip();compiler=Path(sysroot)/'bin/rustc';tools['actualCompiler']={'sysroot':sysroot,'path':str(compiler),'sha256':sha(compiler.read_bytes())}
 compiler_files={str(p.relative_to(Path(sysroot))):sha(p.read_bytes())for group in ['bin','lib']for p in sorted((Path(sysroot)/group).rglob('*'))if p.is_file()}
 baseline=read_json(ROOT/'verification/swift-reactor-lifecycle-runtime-v2'/read_json(ROOT/'verification/swift-reactor-lifecycle-runtime-v2/exact-query-swift-debug-unit.json')['attempt']/'tools.json')['actualCompiler'];assert compiler_files==baseline['sysrootCompilerFiles'];assert tools['actualCompiler']['sha256']==baseline['sha256']
 tools['actualCompiler'].update(sysrootCompilerFiles=compiler_files,sysrootCompilerFilesSHA256=sha(enc(compiler_files)),sysrootBindingScope='Every actual file below compiler sysroot bin/ and lib/, including host/target compiler and standard-library metadata/object libraries; documentation excluded')
 assert tools['actualCompiler']['sha256']=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0';assert sha(enc(manifest(tree)))==json.loads((HERE/'source-delta.json').read_text())['candidateClosure'];save(attempt/'tools.json',tools)
 for script in HERE.glob('*.py'):save(attempt/'collector-scripts'/script.name,script.read_bytes())
 with tarfile.open(attempt/'source.tar.gz','w:gz') as t:
  for rel in before:t.add(tree/rel,arcname=rel,recursive=False)
 scratch=Path(tempfile.mkdtemp(prefix='mixer-lifecycle-v3-compiler-'))
 env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:/Users/andreyyurlov/.local/share/fnm/node-versions/v22.23.3/installation/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',CARGO_TARGET_DIR=str(scratch/'target'),CARGO_INCREMENTAL='0')
 for k in ['RUSTC','RUSTFLAGS','RUSTC_BOOTSTRAP','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_RUSTFLAGS']:env.pop(k,None)
 if env_extra:env.update(env_extra)
 row={'label':label,'argv':argv,'cwd':str(tree),'environment':{k:v for k,v in env.items() if k in ['PATH','CARGO_TARGET_DIR','CARGO_INCREMENTAL','RUSTC_BOOTSTRAP','RUSTFLAGS','RUSTC_WRAPPER','MIXER_LAYOUT_SYSROOT','MIXER_LAYOUT_OUTPUT','DYLD_LIBRARY_PATH']},'sourceClosure':sha(enc(before)),'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 save(attempt/'command.json',row)
 p=subprocess.Popen(argv,cwd=tree,env=env,start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 row['group']=p.pid
 try:
  out,err=p.communicate(timeout=900)
 except subprocess.TimeoutExpired:
  assert p.poll() is None and os.getpgid(p.pid)==p.pid;os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate();row['timedOut']=True
 save(attempt/'stdout.log.gz',gzip.compress(out,mtime=0));save(attempt/'stderr.log.gz',gzip.compress(err,mtime=0))
 row.update(exitCode=p.returncode,stdoutSHA256=sha(out),stderrSHA256=sha(err),expectedExitCode=expected,sourceUnchanged=before==manifest(tree),finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
 groups=subprocess.check_output(['ps','-axo','pid=,pgid=,command='],text=True)
 left=[x for x in groups.splitlines() if len(x.split(None,2))>=2 and x.split(None,2)[1]==str(p.pid)]
 row['remainingGroup']=left
 if left:row['cleanupFailure']='Completed numeric PGID ambiguous; no kill attempted'
 extra_artifacts=[]
 post_output=b''
 try:
  assert post is None, "No executable post-run route in accounting collector"
 except BaseException as error:
  import traceback
  row['postError']=repr(error);row['exitCode']=-1
  save(attempt/'post-failure.log',traceback.format_exc().encode())
 # Always retain compiler outputs and binaries before removing owned scratch.
 artifacts=[]
 for artifact in sorted(scratch.rglob('*')):
  if not artifact.is_file():continue
  if artifact in extra_artifacts or artifact.suffix in ['.mir','.ll'] or (artifact.parent.name=='deps' and artifact.stat().st_mode&0o111 and artifact.suffix==''):
   raw=artifact.read_bytes();name='artifacts/'+str(artifact.relative_to(scratch))+'.gz';save(attempt/name,gzip.compress(raw,mtime=0));artifacts.append({'path':name,'sha256':sha(raw),'bytes':len(raw)})
 save(attempt/'artifacts.json',artifacts);save(attempt/'command.json',row)
 holders=subprocess.run(['lsof','-nP','+D',str(scratch)],capture_output=True)
 save(attempt/'holders.log',holders.stdout+holders.stderr)
 count=sum(x.is_file() for x in scratch.rglob('*'));size=sum(x.stat().st_size for x in scratch.rglob('*') if x.is_file())
 assert holders.returncode==1 and not holders.stdout and not holders.stderr,(holders.returncode,holders.stdout,holders.stderr)
 shutil.rmtree(scratch)
 save(attempt/'cleanup.json',{'scratch':str(scratch),'removed':not scratch.exists(),'filesRemoved':count,'logicalBytesRemoved':size,'nativeInstancesCreated':0,'holderCheckEmpty':True,'remainingGroup':left})
 print(str(attempt),flush=True);
 if post_output:print(post_output.decode(errors='replace')[-16000:])
 print(out.decode(errors='replace')[-1000:] if len(out)<100000 else '[large stdout archived]');print(err.decode(errors='replace')[-9000:])
 assert row['sourceUnchanged'] and not left
 return row['exitCode'],attempt,out+post_output,err
if __name__=='__main__':
 code,*_=run(sys.argv[1:]);sys.exit(code)
