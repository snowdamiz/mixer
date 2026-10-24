#!/usr/bin/env python3
"""Isolated contextual cleanup collector. Every build gets an empty target."""
from pathlib import Path
import datetime,difflib,gzip,hashlib,json,os,re,shutil,subprocess,sys,tarfile
from owned_process import stop_group
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda x:hashlib.sha256(x).hexdigest()
def save(name,x):
 p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(enc(x))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def manifest(vm):
 paths=[vm/'Cargo.toml',vm/'Cargo.lock']
 for n in ['src','tests','include']:paths+=sorted(p for p in(vm/n).rglob('*')if p.is_file())
 return {str(p.relative_to(vm)):sha(p.read_bytes())for p in paths}
def digest(x):return sha(enc(x))
def session():return json.loads((HERE/'session.json').read_text())
def scratch():return Path(session()['scratch'])
def source(label):return scratch()/label
def archive(label,vm=None):
 vm=vm or source(label);m=manifest(vm);save(label+'-source-manifest.json',m)
 with tarfile.open(HERE/(label+'-source.tar.gz'),'w:gz')as t:
  for n in m:t.add(vm/n,arcname=n)
 return digest(m)
def command(name,argv,vm=None,env_extra=None,expect=0):
 out=HERE/'commands'/name;out.mkdir(parents=True,exist_ok=False)
 before=manifest(vm)if vm else None
 env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
 for k in ['RUSTFLAGS','RUSTC_BOOTSTRAP','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_RUSTFLAGS']:env.pop(k,None)
 if env_extra:env.update(env_extra)
 started=now();process=subprocess.Popen(argv,cwd=vm or ROOT,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 group=process.pid;timed_out=False
 try:
  try:stdout,stderr=process.communicate(timeout=900)
  except subprocess.TimeoutExpired:
   timed_out=True;stop_group(group);stdout,stderr=process.communicate(timeout=10)
  group_cleanup=stop_group(group)
 finally:
  if process.poll()is None:stop_group(group);process.wait(timeout=10)
  process.stdout.close();process.stderr.close()
 from types import SimpleNamespace
 p=SimpleNamespace(stdout=stdout,stderr=stderr,returncode=(-1 if timed_out else -2 if group_cleanup['before'] else process.returncode))
 for stream in ['stdout','stderr']:
  with gzip.open(out/(stream+'.gz'),'wb')as z:z.write(getattr(p,stream))
 after=manifest(vm)if vm else None
 row=dict(argv=argv,cwd=str(vm or ROOT),startedUTC=started,completedUTC=now(),exitCode=p.returncode,expectedExitCode=expect,ownedProcessGroup=group,groupCleanup=group_cleanup,timedOut=timed_out,sourceTreeBeforeSHA256=digest(before)if before else None,sourceTreeAfterSHA256=digest(after)if after else None,sourceUnchanged=before==after,stdoutSHA256=sha(p.stdout),stderrSHA256=sha(p.stderr),environment={k:env[k]for k in ['PATH','CARGO_TARGET_DIR','RUSTC_BOOTSTRAP','RUSTFLAGS']if k in env})
 save('commands/'+name+'/receipt.json',row)
 if before:save('commands/'+name+'/source-manifest.json',before)
 print(name,p.returncode,flush=True)
 assert before==after,name
 if p.returncode!=expect:
  print(p.stderr.decode(errors='replace')[-8000:],flush=True);print(p.stdout.decode(errors='replace')[-3000:],flush=True);raise RuntimeError(name)
 return p,row
def target(vm,features,profile,context):
 tree=digest(manifest(vm));p=scratch()/('target-'+tree+'-'+features+'-'+profile+'-'+context)
 assert not p.exists(),p;p.mkdir();return p

def mir(label,prefix):
 vm=source(label)
 for unit in [False,True]:
  config='unit'if unit else'production';t=target(vm,'all','debug',prefix+'-'+config)
  env={'CARGO_TARGET_DIR':str(t),'RUSTC_BOOTSTRAP':'1'}
  if unit:
   env['RUSTFLAGS']='--emit=mir,link -Zmir-include-spans=yes'
   a=['cargo','test','--lib','--no-run','--all-features','--offline','--locked','--message-format=json-render-diagnostics']
  else:a=['cargo','rustc','--lib','--all-features','--offline','--locked','--message-format=json-render-diagnostics','--','--emit=mir','-Zmir-include-spans=yes']
  p,row=command(prefix+'-'+config,a,vm,env)
  files=[x for x in(t/'debug/deps').glob('*.mir')if '::remove_live_with_wasi('in x.read_text()];assert len(files)==1,files
  with gzip.open(HERE/(prefix+'-'+config+'.mir.gz'),'wb')as z:z.write(files[0].read_bytes())
  artifacts=[json.loads(l)for l in p.stdout.decode().splitlines()if l.startswith('{')]
  artifacts=[x for x in artifacts if x.get('reason')=='compiler-artifact'and x['target']['name']=='mixer_vm'and x['target']['src_path'].endswith('/src/lib.rs')and bool(x['profile']['test'])==unit]
  assert len(artifacts)==1 and artifacts[0]['fresh']is False
  save(prefix+'-'+config+'-artifact.json',artifacts[0])
  if unit:retain_and_run(prefix+'-'+config,artifacts[0],vm,env,list_only=True)

def retain_and_run(name,a,vm,env,list_only=False,args=None,probe_args=None):
 exe=Path(a['executable']);h=sha(exe.read_bytes());d=HERE/'artifacts'/name;d.mkdir(parents=True,exist_ok=False)
 save('artifacts/'+name+'/cargo-artifact.json',a)
 with gzip.open(d/'executable.gz','wb')as z:z.write(exe.read_bytes())
 tests=None
 if a['profile']['test']:
  p,_=command('list-'+name,[str(exe),'--list'],vm,env);tests=[l[:-6]for l in p.stdout.decode().splitlines()if l.endswith(': test')];assert len(tests)==len(set(tests));assert sha(exe.read_bytes())==h;save('artifacts/'+name+'/test-list.json',tests)
 output=None
 record=dict(exactExecutablePath=str(exe),executableSHA256=h,executableBytes=exe.stat().st_size,executableBeforeListSHA256=h if tests is not None else None,executableAfterListSHA256=sha(exe.read_bytes())if tests is not None else None,executableBeforeRunSHA256=h if not list_only else None,executableAfterRunSHA256=None,fullUnitTestCount=len(tests)if tests is not None else None,cargoTarget=env['CARGO_TARGET_DIR'],sourceTreeSHA256=digest(manifest(vm)),cargoArtifactFresh=a['fresh'],targetCreatedEmpty=True)
 save('artifacts/'+name+'/identity.json',record)
 if not list_only:
  try:
   if probe_args:
    probe_output,_=command('probe-'+name,[str(exe),*probe_args],vm,env);assert sha(exe.read_bytes())==h;record['probeExecutableSHA256']=h;record['probeCommand']='commands/probe-'+name+'/receipt.json'
   output,_=command('execute-'+name,[str(exe),*(args or[])],vm,env)
  finally:
   record['executableAfterRunSHA256']=sha(exe.read_bytes());assert record['executableAfterRunSHA256']==h;save('artifacts/'+name+'/identity.json',record)
 return output,record
if __name__=='__main__':
 if sys.argv[1]=='mir':mir(sys.argv[2],sys.argv[3])
