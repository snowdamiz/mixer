#!/usr/bin/env python3
"""Bounded host command recorder. No network or production mutations."""
import datetime,gzip,hashlib,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CANDIDATE=HERE/'candidate'
TARGET=HERE/'owned-target'
ENV={key:os.environ[key] for key in ['HOME','TMPDIR','USER','LOGNAME'] if key in os.environ}
ENV.update(PATH='/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',RUSTUP_TOOLCHAIN='stable-aarch64-apple-darwin',CARGO_TARGET_DIR=str(TARGET),CARGO_INCREMENTAL='0',CARGO_NET_OFFLINE='true')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
def manifest(tree=CANDIDATE):return {str(p.relative_to(tree)):sha(p) for p in sorted(tree.rglob('*')) if p.is_file()}
def tools():
 out={}
 for name,args in [('rustc',['-vV']),('cargo',['-V']),('rustfmt',['--version'])]:
  proxy=shutil.which(name,path=ENV['PATH']); actual=subprocess.check_output(['rustup','which',name],env=ENV,text=True).strip()
  out[name]={'proxy':proxy,'proxySHA256':sha(proxy),'actual':actual,'actualSHA256':sha(actual),'version':subprocess.check_output([proxy,*args],env=ENV,text=True).strip()}
 return out
if __name__=='__main__':
 label=sys.argv[1]; argv=sys.argv[2:]; assert argv
 logs=HERE/'commands';logs.mkdir(exist_ok=True)
 assert not (logs/(label+'.json')).exists(),'label already used; preserve history'
 spent=sum(json.loads(p.read_text())['durationSeconds'] for p in logs.glob('*.json'))
 assert spent<1800,'aggregate command budget exhausted'
 bound=min(180,1800-spent)
 before=manifest();baseline=json.loads((HERE/'baseline-manifest.json').read_text())
 assert set(before)==set(baseline)
 assert set(n for n in before if before[n]!=baseline[n]) <= {'src/experimental_swift_reactor/lifecycle_tests.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/memory_growth_operations_tests.rs'}
 record={'argv':argv,'cwd':str(CANDIDATE),'environment':ENV,'timeoutSeconds':bound,'priorCommandSeconds':spent,'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tools':tools(),'candidateManifest':before}
 negative_copy=HERE/'compiler-negative-candidate'
 if negative_copy.exists(): record['compilerNegativeManifest']=manifest(negative_copy)
 start=time.monotonic();child=subprocess.Popen(argv,cwd=CANDIDATE,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 record['pid']=child.pid;record['processGroup']=child.pid
 try:out,err=child.communicate(timeout=bound);record['timedOut']=False
 except subprocess.TimeoutExpired:
  os.killpg(child.pid,signal.SIGTERM)
  try:out,err=child.communicate(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
  record['timedOut']=True
 record.update(exitCode=child.returncode,durationSeconds=time.monotonic()-start,finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),stdoutSHA256=hashlib.sha256(out).hexdigest(),stderrSHA256=hashlib.sha256(err).hexdigest(),sourceUnchanged=before==manifest(),postTools=tools())
 for suffix,data in [('stdout',out),('stderr',err)]: (logs/(label+'.'+suffix)).write_bytes(data)
 ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,command='],text=True)
 record['remainingProcessGroup']=[line for line in ps.splitlines() if len(line.split(None,2))>=2 and line.split(None,2)[1]==str(child.pid)]
 if negative_copy.exists(): record['compilerNegativeSourceUnchanged']=record['compilerNegativeManifest']==manifest(negative_copy)
 save(logs/(label+'.json'),record)
 print(json.dumps({k:record[k] for k in ['exitCode','durationSeconds','timedOut','sourceUnchanged','remainingProcessGroup']}));print(out.decode(errors='replace')[-12000:]);print(err.decode(errors='replace')[-7000:])
 sys.exit(0 if child.returncode==0 and not record['timedOut'] and record['sourceUnchanged'] and not record['remainingProcessGroup'] else 1)
