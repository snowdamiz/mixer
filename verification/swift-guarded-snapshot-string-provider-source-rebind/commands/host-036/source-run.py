"""Owned55s Python-only command recorder. Never inventories global processes."""
import datetime, json, os, signal, subprocess, sys, time
from common import *
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 require(len(sys.argv)>1 and Path(sys.argv[1]).name==sys.argv[1] and sys.argv[1].endswith('.py'),'owned Python script required')
 require((D/sys.argv[1]).is_file() and sys.argv[1] not in ('run.py',),'allowed owned command')
 attempts=D/'commands';attempts.mkdir(exist_ok=True)
 ordinal=1
 while (attempts/f'host-{ordinal:03d}').exists():ordinal+=1
 out=attempts/f'host-{ordinal:03d}';out.mkdir()
 pre=custody();save(str(out.relative_to(D)/'inputs-before.json'),pre)
 scripts=[row(p.name,p.read_bytes()) for p in sorted(D.glob('*.py'))]
 for p in sorted(D.glob('*.py')):(out/('source-'+p.name)).write_bytes(p.read_bytes())
 env={'PATH':os.environ.get('PATH',''),'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','LANG':'C.UTF-8','LC_ALL':'C.UTF-8'}
 argv=[sys.executable,'-B',str(D/sys.argv[1]),*sys.argv[2:]]
 receipt={'schema':1,'argv':argv,'environment':env,'cwd':str(R),'python_version':sys.version,'python_executable':row(sys.executable,Path(sys.executable).read_bytes()),'source_revision':(V/'swift-guarded-snapshot-owned-provider-work-storage/commands/capture-layout/receipt.json').read_text(),'scripts':scripts,'source_trees':TREES,'started_at':now(),'timeout_seconds':55,'compiler_invocations':0,'runtime_native_UI_capture_global_inventory_invocations':0}
 receipt['source_revision']=json.loads(receipt['source_revision'])['source_revision']
 t=time.monotonic();p=None;exception=None;timed=False;signals=[]
 try:
  with (out/'stdout').open('wb') as so,(out/'stderr').open('wb') as se:
   p=subprocess.Popen(argv,cwd=R,env=env,stdout=so,stderr=se,start_new_session=True)
   receipt['owned_pid']=receipt['owned_pgid']=p.pid
   try:p.wait(timeout=55)
   except subprocess.TimeoutExpired:
    timed=True;os.killpg(p.pid,signal.SIGKILL);signals.append('SIGKILL');p.wait()
 except BaseException as e:exception=repr(e)
 absent=False
 if p:
  try:os.killpg(p.pid,0)
  except ProcessLookupError:absent=True
  if not absent:
   os.killpg(p.pid,signal.SIGKILL);signals.append('SIGKILL-descendant');p.wait()
   try:os.killpg(p.pid,0)
   except ProcessLookupError:absent=True
 post=custody();save(str(out.relative_to(D)/'inputs-after.json'),post)
 receipt.update(finished_at=now(),elapsed_seconds=time.monotonic()-t,exception=exception,timed_out=timed,cleanup_signals=signals,child_reaped=p is not None and p.returncode is not None,owned_group_absent=absent,exit_code=p.returncode if p else None,input_custody_unchanged=pre==post,outputs=[row(n,(out/n).read_bytes()) for n in ('stdout','stderr') if (out/n).exists()])
 receipt['success']=receipt['exit_code']==0 and not timed and exception is None and absent and pre==post
 save(str(out.relative_to(D)/'receipt.json'),receipt)
 print(json.dumps({'path':str(out.relative_to(R)),'success':receipt['success'],'seconds':receipt['elapsed_seconds'],'exit':receipt['exit_code']}))
 if not receipt['success']:sys.exit(1)
if __name__=='__main__':main()
