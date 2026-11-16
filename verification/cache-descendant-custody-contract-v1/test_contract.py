"""Pure intercepted custody boundaries; never target a kernel PID."""
import ast,errno,gc,hashlib,json,os,re,resource,selectors,signal,subprocess,sys,time,types
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
FAKE=987654
RESULT=[]
def check(value,message):
    if not value:raise RuntimeError(message)
class Frozen(BaseException):pass
class Clock:
    def __init__(self):self.t=0
    def monotonic(self):return self.t
    def sleep(self,n):self.t+=n
class FakePath:
    def __init__(self,name='fake',events=None):self.name=name;self.events=events if events is not None else []
    def __truediv__(self,name):return FakePath(self.name+'/'+str(name),self.events)
    def __str__(self):return self.name
    @property
    def suffix(self):return '.'+self.name.rsplit('.',1)[-1]
    @property
    def parent(self):return FakePath(self.name.rsplit('/',1)[0],self.events)
    def mkdir(self,*a,**k):pass
    def open(self,*a,**k):return Stream(self.events,'output')
    def exists(self):return True
    def read_text(self):return ''
    def write_bytes(self,b):pass
class Stream:
    def __init__(self,events,label):self.events=events;self.label=label
    def close(self):self.events.append('close-'+self.label)
    def fileno(self):return FAKE
    def write(self,b):return len(b)
def load(root,source=None):
    ns=dict(globals())
    runner=root/'verification/cache-fixture-shared-input-candidate-v2/check_cache_state.py'
    names={'need','now','exception_details','sha','save','identity','no_symlinks','environment','context_phase_progress','child_usage','child_accounting'}
    nodes=[n for n in ast.parse(runner.read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name in names]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(runner),'exec'),ns)
    exec(compile((HERE/'process_adapter.py').read_bytes(),str(HERE/'process_adapter.py'),'exec'),ns)
    exec(compile((HERE/'commands.py').read_bytes()if source is None else source,str(HERE/'commands.py'),'exec'),ns)
    ns.update(CHILD_SECONDS=.7,CLEANUP_SECONDS=60,OUTPUT_CAP=8388608)
    return ns
def test_stop(root,name,sequence,expected,*,signal_denied=False,unowned=False,errnum=1,source=None):
    ns=load(root,source);clock=Clock();events=[];pos=[0]
    proc=types.SimpleNamespace(pid=FAKE,returncode=0)
    proc.poll=lambda:events.append('poll')or 0
    proc.wait=lambda **kw:events.append('wait')or 0
    def killpg(pid,sig):
        check(pid==FAKE,'fake kernel target escaped')
        events.append('observe'if sig==0 else'signal')
        if sig:
            if signal_denied:raise PermissionError(1,'fake signal denial')
            return
        step=sequence[min(pos[0],len(sequence)-1)];pos[0]+=1
        if isinstance(step,tuple):step,clock.t=step
        events.append('observation-return-at-'+str(clock.t))
        if step=='eperm':raise PermissionError(errnum,'fake observation denial')
        if step=='esrch':raise ProcessLookupError(3,'fake absence')
        if step=='eio':raise OSError(5,'fake observation error')
    ns['os']=types.SimpleNamespace(killpg=killpg);ns['time']=clock
    c=object.__new__(ns['Commands']);c.unknown_custody=False;c.active=proc
    row={'pid':FAKE,'pgid':FAKE,'new_session':not unowned,'cleanup_deadline':1.0,'owned_group_gone':False}
    c.receipt={'commands':[row]};error=None
    try:c.stop(proc,row)
    except BaseException as e:error=type(e).__name__
    unknown=c.unknown_custody
    n=len(events)
    if unknown:
        for op in [lambda:c.gone(FAKE),lambda:c.observe(proc.poll),lambda:c.stop(proc,row)]:
            try:op()
            except BaseException:pass
        check(len(events)==n,name+' operations after UNKNOWN')
    check(unknown==expected,name+' UNKNOWN mismatch')
    if unknown:check(not row.get('stop_complete')and not row['owned_group_gone'],name+' late positive closure')
    RESULT.append({'name':name,'unknown':unknown,'error':error,'row':row,'events':events,'intercepted':True})
def test_run(root,name,*,no_eof=False,constructor_failure=False,unexpected=False):
    ns=load(root);clock=Clock();events=[];keys={}
    base=ns['InertPopen']
    class FakeProc(base):
        def __init__(self,*a,**kw):
            if constructor_failure:raise RuntimeError('fake no-PID constructor unwind')
            self.pid=FAKE;self.returncode=0;self.stdout=Stream(events,'stdout');self.stderr=Stream(events,'stderr')
        def poll(self):
            events.append('poll')
            if unexpected:raise OSError(5,'fake poll failure')
            return 0
        def wait(self,**kw):events.append('wait');return 0
    def register(pipe,event,data):keys[pipe]=types.SimpleNamespace(fileobj=pipe,data=data)
    def select(n):
        clock.t+=.1
        return []if no_eof else[(k,1)for k in list(keys.values())]
    selector=types.SimpleNamespace(register=register,get_map=lambda:keys,select=select,unregister=lambda p:keys.pop(p),close=lambda:events.append('close-selector'))
    def killpg(pid,sig):
        check(pid==FAKE,'fake target escaped');events.append('observe'if sig==0 else'signal')
        raise ProcessLookupError(3,'fake absence')
    frozen=[]
    def freeze(authority,metadata,path):frozen.append((authority,metadata));raise Frozen()
    ns.update(admit_executable=lambda *args:None,InertPopen=FakeProc,time=clock,os=types.SimpleNamespace(killpg=killpg,read=lambda fd,n:b''),selectors=types.SimpleNamespace(DefaultSelector=lambda:selector,EVENT_READ=1),freeze_unknown=freeze,save=lambda *a:None,sha=lambda p:'fake-sha',child_usage=lambda:None,child_accounting=lambda *a:{},environment=lambda x:x)
    c=ns['Commands'](FakePath('fake/'+name,events),{'commands':[]},20);c.child_environment=lambda env:{}
    error=None
    try:c.run('fake',['/fake/intercepted'],c.out)
    except BaseException as e:error=type(e).__name__
    n=len(events)
    if c.unknown_custody:
        with c.active:pass
        c.active.__del__()
        for op in [lambda:c.run('again',[],c.out),lambda:c.observe(c.active.poll)]:
            try:op()
            except BaseException:pass
        gc.collect()
        check(len(events)==n,name+' process/descriptor side effect after UNKNOWN')
    expected=no_eof or constructor_failure or unexpected
    check(c.unknown_custody==expected,name+' UNKNOWN mismatch')
    if expected:check(frozen and c.active is not None and error=='Frozen',name+' retained authority missing')
    else:check(c.active is None and all(c.receipt['commands'][-1][k]for k in ['child_returned','owned_group_gone','stdout_eof','stderr_eof','stdout_closed','stderr_closed','selector_closed']),name+' positive closure incomplete')
    RESULT.append({'name':name,'unknown':c.unknown_custody,'events':events,'error':error,'fakeOnly':True,'authorityRetained':bool(frozen)})
def test_finalizers(root):
    ns=load(root);events=[]
    baseline=object.__new__(subprocess.Popen)
    baseline._child_created=True;baseline.returncode=None;baseline.pid=FAKE
    baseline._internal_poll=lambda **kw:events.append('baseline-finalizer-poll')
    subprocess.Popen.__del__(baseline)
    check(events==['baseline-finalizer-poll'],'ordinary baseline finalizer exposure missing')
    baseline._child_created=False
    if baseline in subprocess._active:subprocess._active.remove(baseline)
    for label in ['constructor','unwind','context','gc','exit-contract']:
        obj=object.__new__(ns['InertPopen']);obj._child_created=True;obj.returncode=None
        obj._internal_poll=lambda **kw:events.append('forbidden-poll')
        obj.wait=lambda **kw:events.append('forbidden-wait')
        obj.stdout=Stream(events,'stdout');obj.stderr=Stream(events,'stderr')
        with obj:pass
        obj.__del__();del obj;gc.collect()
    check(events==['baseline-finalizer-poll'],'inert finalizer performed an operation')
    RESULT.append({'name':'baseline-and-inert-finalizer','events':events,'kernelCalls':0,'pythonExitNeedsSeparateActualHelper':True})
def test_publication(root):
    for label,error in [('normal',None),('ENOSPC',OSError(errno.ENOSPC,'fake publication full')),('permission',PermissionError(errno.EACCES,'fake publication denied')),('BaseException',BaseException('fake base exception')),('SystemExit',SystemExit(91))]:
        ns=load(root);events=[];authority=object();metadata={'fakeOnly':True,'innerKernelPID':None,'originalDiagnostic':'preserved-input'}
        class Writer:
            def write_text(self,text):
                events.append('publish')
                check(json.loads(text)==metadata,'publication metadata changed')
                if error is not None:raise error
        def exit74(code):
            events.append(('exit',code))
            check(sys.exc_info()[1] is error,'pending publication diagnostic lost')
            raise Frozen()
        ns['os']=types.SimpleNamespace(_exit=exit74)
        terminal=False
        try:ns['freeze_unknown'](authority,metadata,Writer())
        except Frozen:terminal=True
        check(terminal and events==['publish',('exit',74)],label+' returned or unwound publication error')
        check(ns['UNKNOWN_AUTHORITIES']==[authority],label+' authority not retained')
        RESULT.append({'name':'publication-'+label,'fakeOnly':True,'exit':74,'pendingExceptionPreserved':True,'authorityRetained':True,'kernelCalls':0})
def main(root=None):
    root=Path(root)if root else HERE.parents[1]
    test_finalizers(root)
    test_publication(root)
    if (HERE.parents[2]/'baseline-controller.py').is_file():
        test_stop(root,'R3740-baseline-accepts-late-positive',['eperm',('eperm',.985),('esrch',1.005)],False,source=(HERE.parents[2]/'baseline-controller.py').read_bytes())
    test_stop(root,'normal',['esrch'],False)
    test_stop(root,'transient-eperm',['eperm','eperm','esrch'],False)
    test_stop(root,'permanent-eperm',['eperm'],True)
    test_stop(root,'late-esrch-return-1.005',['eperm',('eperm',.985),('esrch',1.005)],True)
    test_stop(root,'initial-late-esrch',[('esrch',1.005)],True)
    test_stop(root,'signal-denial',['present'],True,signal_denied=True)
    test_stop(root,'unowned-eperm',['eperm'],True,unowned=True)
    test_stop(root,'other-permission-errno',['eperm'],True,errnum=13)
    test_stop(root,'unexpected-observation-error',['eio'],True)
    test_run(root,'complete-positive-run')
    test_run(root,'no-eof',no_eof=True)
    test_run(root,'constructor-unwind-no-pid',constructor_failure=True)
    test_run(root,'ordinary-exception-unwind',unexpected=True)
    print(json.dumps({'status':'passed','optimize':sys.flags.optimize,'cases':RESULT,'engineOwners':0,'noLedgerClaim':True},sort_keys=True))
    return RESULT
if __name__=='__main__':main(sys.argv[1]if len(sys.argv)>1 else None)
