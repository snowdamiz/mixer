"""First of two fake-only commands. No process calls reach the OS."""
import errno, importlib.util, json, os, signal, sys, time
from pathlib import Path
from unittest.mock import patch
OUT=Path(__file__).resolve().parent
OLD=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-c7acc756/verification/plan-continuation-2026-11-07/android-motion-controller-repair')
spec=importlib.util.spec_from_file_location('old',OLD/'cleanup_control.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
original=os.killpg
results=[]
class Child:
    pid=90000001
    def __init__(self,zombie):self.zombie=zombie;self.reaped=False;self.polls=0
    def poll(self):
        self.polls+=1
        if self.zombie:self.reaped=True;return 0
        return None
for scenario in ['already-zombie','exit-during-signal']:
    folder=OUT/('premise-'+scenario);folder.mkdir(exist_ok=False)
    manager=old.Commands(folder,{},deadline=time.monotonic()+1,cleanup_seconds=.1)
    child=Child(scenario=='already-zombie');calls=[]
    record={'label':scenario,'state':'RUNNING','owned_pgid':child.pid,'direct_child_reaped':False,'stdout_eof':True,'stderr_eof':True,'owned_group_absent':False,'terminal_custody':False,'cleanup_errors':[],'signals':[],'group_probes':0}
    item={'record':record,'process':child,'buffers':{'stdout':bytearray(),'stderr':bytearray()}}
    manager.records=[record];manager.owned=[item]
    def group(pid,sig):
        calls.append([pid,sig,child.polls])
        if child.reaped:raise ProcessLookupError(errno.ESRCH,'fake absent')
        if child.zombie:raise PermissionError(errno.EPERM,'fake zombie-only group')
        # Model exit becoming visible between the first poll and the group probe.
        if sig==signal.SIGKILL:
            def delayed_poll():child.zombie=True;child.poll=Child.poll.__get__(child);return None
            child.poll=delayed_poll
    with patch.object(old.os,'killpg',side_effect=group),patch.object(old.subprocess,'Popen',side_effect=RuntimeError('no spawn permitted')):
        manager.stop(item)
        if record['state']!='UNKNOWN' or record['owned_group_absent']:raise RuntimeError('baseline did not discriminate')
        manager.stop(item)
    if os.killpg is not original:raise RuntimeError('mock leaked')
    results.append({'scenario':scenario,'expectedOldResult':'UNKNOWN','record':record,'calls':calls,'mockRestored':True})
    manager.selector.close()
receipt={'status':'passed','tests':2,'realChildren':0,'realGroupCalls':0,'results':results,'python':sys.version,'command':[sys.executable,'-B',str(Path(__file__).resolve())],'decision':'Old ordering reproduces both failure shapes with scoped mocks restored. Repair reaping order; persistent permission denial must remain UNKNOWN. Actual host policy not determined by fake.'}
(OUT/'premise-results.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'tests':2,'realChildren':0}))
