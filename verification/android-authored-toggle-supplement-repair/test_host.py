"""Host controls exercise failure plumbing and exact runner identities, never native dispatch."""
import hashlib,tempfile
from pathlib import Path
from types import SimpleNamespace
import support
import run
import diagnostics

def test():
    checks=0
    def need(value,message):
        nonlocal checks
        checks+=1
        if not value:raise AssertionError(message)
    contract=support.read(support.HERE/'runner-contract.json');module,source,_=run.load_runner();_,original,_=support.old_runner()
    marker='    except BaseException as failure:\n'
    need(source[source.index(marker):]==original[original.index(marker):],'emulator/extraction cleanup must remain byte-identical')
    need("PACKAGE = 'dev.mixer.android.authoredtogglerepair'" in source,'new private package')
    need(contract['sourceClosureSHA256']==support.frozen()['sourceClosureSHA256'],'new source closure')
    old=(support.PRODUCER/'supplement-3/source-used/AuthoredToggleSupplementInstrumentation.java').read_text();new=(support.candidate()/'source-used/AuthoredToggleSupplementInstrumentation.java').read_text()
    start='        try{\n            if(arguments==null';end='        }catch(Throwable caught){failure=caught;}'
    need(old[old.index(start):old.index(end)]==new[new.index(start):new.index(end)],'all original 45 case bodies untouched')
    old_prefix=old[:old.index(start)].replace('private void main(Runnable action){runOnMainSync(action);}','private void main(Runnable action){FixtureFailures.main(this::runOnMainSync,action);}')
    need(old_prefix==new[:new.index(start)],'all callback, event and helper logic untouched except forwarding')
    need((support.candidate()/'source-used/AuthoredToggleSupplementActivity.java').read_bytes()==(support.PRODUCER/'supplement-3/source-used/AuthoredToggleSupplementActivity.java').read_bytes(),'activity unchanged')
    need(len(support.inventory())==184,'complete184 payload')
    for invalid in ('../runtime-1','runtime-0','runtime-01','other-1'):
        try:support.runtime_directory(invalid)
        except ValueError:checks+=1
        else:raise AssertionError('unsafe runtime path admitted')
    class Process:
        pid=1234
        def poll(self):return None
    group={'group':1,'before':[],'after':[],'signals':[]}
    with tempfile.TemporaryDirectory(prefix='repair-host-control-',dir=support.HERE) as tmp:
        path=Path(tmp);calls=[]
        def execute(argv,**kwargs):
            calls.append(argv)
            if argv[0]=='ps':data=b'exact owned process'
            elif 'crash' in argv and 'main' not in argv:raise RuntimeError('simulated crash buffer unavailable')
            elif 'exec-out' in argv:data=b'original assertion\nSuppressed: cleanup failed\n'
            else:data=b'logcat tail'
            return SimpleNamespace(returncode=0,stdout=data,groupCleanup=group)
        receipt={};diagnostics.capture(execute,lambda text,pid:text=='exact owned process' and pid==1234,Process(),['bound-adb','-s','emulator-5586'],'dev.mixer.android.authoredtogglerepair',path,receipt,support.ROOT)
        need(len(calls)==4,'independent later diagnostics attempted after earlier failure')
        need(all(argv[:3]==['bound-adb','-s','emulator-5586'] for argv in calls[1:]),'no global/unowned adb')
        need(all('files/toggle-supplement-diagnostics.txt' in argv for argv in calls if 'exec-out' in argv),'literal private diagnostic export')
        expected=hashlib.sha256(b'original assertion\nSuppressed: cleanup failed\n').hexdigest()
        need(diagnostics.bind_fixture(receipt['diagnostics'],('INSTRUMENTATION_RESULT: diagnosticSHA256='+expected).encode()),'instrumentation diagnostic hash verified')
        need(not diagnostics.bind_fixture(receipt['diagnostics'],b'INSTRUMENTATION_RESULT: diagnosticSHA256='+b'0'*64),'wrong diagnostic hash rejected')
    with tempfile.TemporaryDirectory(prefix='repair-host-control-',dir=support.HERE) as tmp:
        calls=[]
        def noidentity(argv,**kwargs):calls.append(argv);return SimpleNamespace(returncode=0,stdout=b'wrong identity',groupCleanup=group)
        receipt={};diagnostics.capture(noidentity,lambda *args:False,Process(),['bound-adb','-s','emulator-5586'],'private',Path(tmp),receipt,support.ROOT)
        need(len(calls)==1 and 'refused' in receipt['diagnostics']['status'],'identity mismatch refuses native diagnostics')
    return {'status':'passed-host-only-fixture-and-runner-controls','checks':checks,'nativeCommandsExecuted':0,'productAcceptance':False}
if __name__=='__main__':print(test())
