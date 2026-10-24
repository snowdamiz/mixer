#!/usr/bin/env python3
"""Independently bounded offline host command recorder. Owned source/target only."""
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'source'
TARGET=HERE/'owned-target'
ENV={key:os.environ[key] for key in ['HOME','TMPDIR','USER','LOGNAME'] if key in os.environ}
ENV.update(PATH='/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',RUSTUP_TOOLCHAIN='stable-aarch64-apple-darwin',CARGO_TARGET_DIR=str(TARGET),CARGO_INCREMENTAL='0',CARGO_NET_OFFLINE='true')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):p.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def manifest():return {str(p.relative_to(SOURCE)):sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file()}
def tool_info():
 result={}
 for tool,args in [('rustc',['-vV']),('cargo',['-V']),('rustfmt',['--version'])]:
  proxy=Path('/opt/homebrew/opt/rustup/bin')/tool
  actual=Path(subprocess.check_output(['rustup','which',tool],env=ENV,text=True).strip())
  result[tool]={'proxy':str(proxy),'proxySHA256':sha(proxy),'actual':str(actual),'actualSHA256':sha(actual),'version':subprocess.check_output([str(proxy),*args],env=ENV,text=True).strip()}
 return result
if __name__=='__main__':
 label=sys.argv[1];argv=sys.argv[2:];assert argv
 logs=HERE/'commands';logs.mkdir(exist_ok=True)
 assert not (logs/(label+'.json')).exists()
 spent=sum(json.loads(p.read_text())['durationSeconds'] for p in logs.glob('*.json'))
 assert spent<900
 timeout=min(180,900-spent)
 before=manifest()
 row={'argv':argv,'cwd':str(SOURCE),'environment':ENV,'tools':tool_info(),'sourceRevisionContext':json.loads((HERE/'initial-source-inspection.json').read_text())['sourceRevisionContext'],'sourceManifest':before,'sourceClosureSHA256':hashlib.sha256((json.dumps(before,sort_keys=True,indent=2)+'\n').encode()).hexdigest(),'timeoutSeconds':timeout,'priorCommandSeconds':spent,'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 start=time.monotonic();child=subprocess.Popen(argv,cwd=SOURCE,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 row.update(pid=child.pid,processGroup=child.pid)
 try:out,err=child.communicate(timeout=timeout);row['timedOut']=False
 except subprocess.TimeoutExpired:
  os.killpg(child.pid,signal.SIGTERM)
  try:out,err=child.communicate(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
  row['timedOut']=True
 row.update(exitCode=child.returncode,durationSeconds=time.monotonic()-start,finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceUnchanged=before==manifest(),postTools=tool_info())
 for suffix,raw in [('stdout',out),('stderr',err)]:
  (logs/(label+'.'+suffix)).write_bytes(raw);row[suffix+'SHA256']=hashlib.sha256(raw).hexdigest()
 ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,command='],text=True)
 row['remainingProcessGroup']=[line for line in ps.splitlines() if len(line.split(None,2))>=2 and line.split(None,2)[1]==str(child.pid)]
 save(logs/(label+'.json'),row)
 print(json.dumps({k:row[k] for k in ['exitCode','durationSeconds','timedOut','sourceUnchanged','remainingProcessGroup']}))
 print(out.decode(errors='replace')[-12000:]);print(err.decode(errors='replace')[-6000:])
 sys.exit(0 if row['exitCode']==0 and not row['timedOut'] and row['sourceUnchanged'] and not row['remainingProcessGroup'] else 1)
