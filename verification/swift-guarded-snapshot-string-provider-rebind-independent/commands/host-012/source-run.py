"""Record bounded owned Python-only review commands and full input custody."""
from support import *
import datetime, signal, subprocess, time
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    require(len(sys.argv)>1 and Path(sys.argv[1]).name==sys.argv[1] and sys.argv[1]=='review.py','owned review script only')
    base=D/'commands';base.mkdir(exist_ok=True);i=1
    while (base/f'host-{i:03d}').exists():i+=1
    dest=base/f'host-{i:03d}';dest.mkdir()
    before=custody();save(str(dest.relative_to(D)/'inputs-before.json'),before)
    scripts=[]
    for p in sorted(D.glob('*.py')):
        b=p.read_bytes();(dest/('source-'+p.name)).write_bytes(b);scripts.append(row(p.name,b))
    argv=[sys.executable,'-B',str(D/sys.argv[1]),*sys.argv[2:]]
    env={'PATH':os.environ.get('PATH',''),'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','LANG':'C.UTF-8','LC_ALL':'C.UTF-8'}
    r={'schema':1,'argv':argv,'cwd':str(R),'environment':env,'python_version':sys.version,'python_executable':row(sys.executable,Path(sys.executable).read_bytes()),'scripts':scripts,'source_trees':TREES,'source_revision':read(V/'swift-guarded-snapshot-owned-provider-work-storage/commands/capture-layout/receipt.json')['source_revision'],'started_at':now(),'timeout_seconds':55,'compiler_product_native_UI_capture_global_inventory_invocations':0}
    t=time.monotonic();p=None;timed=False;signals=[];exception=None
    try:
        with (dest/'stdout').open('wb') as so,(dest/'stderr').open('wb') as se:
            p=subprocess.Popen(argv,cwd=R,env=env,stdout=so,stderr=se,start_new_session=True);r['owned_pid']=r['owned_pgid']=p.pid
            try:p.wait(timeout=55)
            except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGKILL);signals.append('SIGKILL');p.wait()
    except BaseException as e:exception=repr(e)
    absent=False
    if p:
        try:os.killpg(p.pid,0)
        except ProcessLookupError:absent=True
        if not absent:
            os.killpg(p.pid,signal.SIGKILL);signals.append('SIGKILL-owned-descendant');p.wait()
            try:os.killpg(p.pid,0)
            except ProcessLookupError:absent=True
    after=custody();save(str(dest.relative_to(D)/'inputs-after.json'),after)
    r.update(finished_at=now(),elapsed_seconds=time.monotonic()-t,timed_out=timed,exception=exception,cleanup_signals=signals,child_reaped=p is not None and p.returncode is not None,owned_group_absent=absent,exit_code=p.returncode if p else None,input_custody_unchanged=before==after,outputs=[row(n,(dest/n).read_bytes()) for n in ('stdout','stderr')])
    r['success']=r['exit_code']==0 and not timed and exception is None and absent and before==after
    save(str(dest.relative_to(D)/'receipt.json'),r);print(json.dumps({'receipt':str(dest.relative_to(R)/'receipt.json'),'success':r['success'],'seconds':r['elapsed_seconds'],'exit':r['exit_code']}));raise SystemExit(not r['success'])
if __name__=='__main__':main()
