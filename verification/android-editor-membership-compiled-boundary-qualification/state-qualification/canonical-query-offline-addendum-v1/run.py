"""Focused ordinary-host canonical gate; no interpreter/runtime admission."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,platform,signal,subprocess,sys,time
BASE=Path(__file__).resolve().parent
REPO=BASE.parents[3]
MANIFEST_SHA256='da5e35acf808154a71615db4c161c2a9bb4fa10e6e94e7dc9230a9476c5210c9'
def ident(p):
 d=p.read_bytes();return {'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def verify(expected):
 assert ident(BASE/'seal.json')['sha256']==expected,'external gate source seal'
 seal=json.loads((BASE/'seal.json').read_bytes());assert {str(p.relative_to(BASE))for p in BASE.rglob('*')if p.is_file()}=={'seal.json'}|{m['path']for m in seal['members']}
 for m in seal['members']:assert ident(BASE/m['path'])=={k:m[k]for k in('bytes','sha256')}
 assert ident(BASE/'input-manifest.json')['sha256']==MANIFEST_SHA256
 manifest=json.loads((BASE/'input-manifest.json').read_bytes())
 for root in manifest['closed_roots']:
  paths=list((REPO/root['root']).rglob('*'));assert not any(p.is_symlink()for p in paths);assert {str(p.relative_to(REPO))for p in paths if p.is_file()}==set(root['paths'])
 for m in manifest['files']:
  rel=Path(m['path']);assert not rel.is_absolute()and'..'not in rel.parts;assert ident(REPO/rel)=={k:m[k]for k in('bytes','sha256')}
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-seal-sha256',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve();assert not out.exists()and out.is_relative_to(BASE.parent)and not out.is_relative_to(BASE);out.mkdir();entry=exit=False;commands=[];status='failed';started=time.monotonic()
 try:
  signal.alarm(60);verify(a.source_seal_sha256);entry=True;signal.alarm(0);state=BASE.parent;v3=state/'offline-reconciler-v3'
  for label,argv in [('retained40',[sys.executable,'-B',str(v3/'code/test_observation_auditor_v2.py'),'--run',str(state/'full-candidate-v1/run-33'),'--recovery',str(state/'run33-single-state-recovery'),'--output',str(out/'retained40-controls.json')]),('canonical10',[sys.executable,'-B',str(BASE/'code/test_canonical_query.py'),str(out/'canonical10-controls.json')])]:
   env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC'};start=time.monotonic();timed=False
   with(out/(label+'.stdout')).open('wb')as stdout,(out/(label+'.stderr')).open('wb')as stderr:
    child=subprocess.Popen(argv,cwd=REPO,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
    try:child.wait(timeout=60)
    except subprocess.TimeoutExpired:timed=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
    except BaseException:os.killpg(child.pid,signal.SIGKILL);child.wait();raise
   commands.append({'label':label,'argv':argv,'exit':child.returncode,'timeout':timed,'maximum_seconds':60,'elapsed_seconds':time.monotonic()-start,'reaped':True,'stdout':ident(out/(label+'.stdout')),'stderr':ident(out/(label+'.stderr'))});assert child.returncode==0 and not timed,'fresh required controls '+label
  signal.alarm(60);verify(a.source_seal_sha256);sys.path.insert(0,str(BASE/'code'));from canonical_query import run_gate
  value=run_gate();save(out/'canonical84-query-join.json',value);signal.alarm(0);status='passed-focused84-query-canonical-and-v3-row-composition; not-qualified';print(json.dumps({'status':status,'actual_query_rows':value['actual_query_rows'],'selected_event_rows':value['selected_event_rows'],'zero_selected_event_rows':value['zero_selected_event_rows']}),flush=True)
 finally:
  signal.alarm(60)
  try:verify(a.source_seal_sha256);exit=True
  finally:
   signal.alarm(0);save(out/'receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'source_seal_sha256':a.source_seal_sha256,'manifest_sha256':MANIFEST_SHA256,'closure_entry_verified':entry,'closure_exit_verified':exit,'commands':commands,'all_owned_children_reaped':all(c['reaped']for c in commands),'python':sys.version,'python_executable':sys.executable,'platform':platform.platform(),'argv':sys.argv,'elapsed_seconds':time.monotonic()-started,'scope':'Focused84 immutable query rows only, plus retained40 and10 focused refusal controls. No Java execution or225-file re-audit. Ordinary trusted caller-selected Python/OS; complete interpreter/v5 closure unaccepted.','qualified':False})
if __name__=='__main__':main()
