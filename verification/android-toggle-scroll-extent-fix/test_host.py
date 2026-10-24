"""Meaningful host controls; no Android commands or runtime assertions."""
import hashlib,json,tempfile
from pathlib import Path
from types import SimpleNamespace
import diagnostics,run,support
def _inherited_test():
    checks=0
    def need(value,label):
        nonlocal checks
        checks+=1
        if not value:raise AssertionError(label)
    _,source,_=run.load_runner();_,oldrunner,_=support.repair_runner();marker='    except BaseException as failure:\n'
    need(source[source.index(marker):]==oldrunner[oldrunner.index(marker):],'exact unchanged emulator/extraction cleanup tail')
    old=(support.REPAIR/'fixture/AuthoredToggleSupplementInstrumentation.java').read_text();new=(support.HERE/'fixture/AuthoredToggleSupplementInstrumentation.java').read_text()
    begin='            for(boolean direction:new boolean[]{false,true})for(boolean initial:';end='        }catch(Throwable caught){failure=caught;}'
    need(old[old.index(begin):old.index(end)]==new[new.index(begin):new.index(end)],'all45 original case bodies and assertions untouched')
    loop='for(int i=0;i<=8;i++){int action=i==0?0:i==8?1:2;double dx=diagonal?i*10:0;MotionEvent e=event(action,x+dx,y-i*35,1,7,base+i*25);try{sendPointerSync(e);events++;}finally{e.recycle();}}'
    stripped=new.replace('window.observe("worker.injection.before",e,null);','').replace('window.observe("worker.injection.after",e,null);','')
    need(loop in old and loop in stripped,'exact nine actions coordinates timestamps and counters after removing observation calls')
    assertion='require(window.scroll.getScrollY()>0&&proposals==0&&!toggle.isPressed(),"actual native ScrollView interception and CANCEL")'
    need(old.count(assertion)==new.count(assertion)==1,'unchanged combined scroll assertion')
    native=support.PRODUCER/'candidate-3/inputs/native'
    inspected=[*sorted(native.rglob('*.java')),*sorted((support.REPAIR/'fixture').glob('*.java'))]
    need(len(inspected)>1 and all('setOnTouchListener' not in p.read_text() and 'OnTouchListener' not in p.read_text() for p in inspected),'exact frozen product and fixture install no prior touch listener')
    activity=(support.HERE/'fixture/AuthoredToggleSupplementActivity.java').read_text()
    need('view.setOnTouchListener((target,event)->{observe("toggle.OnTouchListener.before-return-false",event,false);return false;});' in activity,'public listener never consumes')
    for label in ('scrollPositive','zeroProposals','notPressed','positiveContentExtent'):
        need('"'+label+'"' in new,'separate failed conjunct/extent observation '+label)
    need('base+i*25' in new and 'paced_uptime' not in new and new.count('SystemClock.sleep(')==old.count('SystemClock.sleep('),'no added sleeps or semantic mode')
    for invalid in ('../runtime-1','runtime-0','runtime-01','other-1'):
        try:support.runtime_directory(invalid)
        except ValueError:checks+=1
        else:raise AssertionError('unsafe runtime path admitted')
    class Process:
        pid=1234
        def poll(self):return None
    group={'group':1,'before':[],'after':[],'signals':[]}
    value={'schema':1,'mode':'original-protocol','entries':[{'stage':'scroll.geometry.after','case':18,'state':{'scrollPositive':False,'zeroProposals':True,'notPressed':True,'positiveContentExtent':True}}],'dropped':0,'observerFailures':0,'listenerConsumes':False}
    with tempfile.TemporaryDirectory(prefix='scroll-host-control-',dir=support.HERE) as tmp:
        out=Path(tmp);calls=[];data=json.dumps(value).encode()
        def execute(argv,**kwargs):
            calls.append(argv);return SimpleNamespace(returncode=0,stdout=b'owned' if argv[0]=='ps' else data,groupCleanup=group)
        receipt={};diagnostics.capture(execute,lambda text,pid:text=='owned' and pid==1234,Process(),['bound-adb','-s','emulator-5586'],support.PACKAGE,out,receipt,support.ROOT)
        need(len(calls)==2 and calls[1][:3]==['bound-adb','-s','emulator-5586'] and calls[1][-1]=='files/toggle-scroll-trace.json','finite serial-specific private trace only')
        instrument=('INSTRUMENTATION_RESULT: scrollTraceSHA256='+hashlib.sha256(data).hexdigest()).encode()
        need(diagnostics.bind_trace(receipt['scrollDiagnostics'],instrument,out),'trace hash and finite schema verified')
        need(not diagnostics.bind_trace(receipt['scrollDiagnostics'],b'INSTRUMENTATION_RESULT: scrollTraceSHA256='+b'0'*64,out),'wrong instrumentation hash rejected')
        row=receipt['scrollDiagnostics']['captures'][1];row['truncated']=True
        need(not diagnostics.bind_trace(receipt['scrollDiagnostics'],instrument,out),'truncated trace rejected')
        row['truncated']=False;value['dropped']=1;data=json.dumps(value).encode();(out/row['output']).write_bytes(data);row['sha256']=hashlib.sha256(data).hexdigest()
        need(not diagnostics.bind_trace(receipt['scrollDiagnostics'],('INSTRUMENTATION_RESULT: scrollTraceSHA256='+row['sha256']).encode(),out),'saturated trace rejected')
    with tempfile.TemporaryDirectory(prefix='scroll-host-control-',dir=support.HERE) as tmp:
        calls=[]
        def refuse(argv,**kwargs):calls.append(argv);return SimpleNamespace(returncode=0,stdout=b'foreign',groupCleanup=group)
        receipt={};diagnostics.capture(refuse,lambda *args:False,Process(),['bound-adb','-s','emulator-5586'],support.PACKAGE,Path(tmp),receipt,support.ROOT)
        need(len(calls)==1 and receipt['scrollDiagnostics']['status'].startswith('refused'),'foreign process identity refuses trace export')
    return {'status':'passed-host-only-original-protocol-source-runner-controls','checks':checks,'nativeCommandsExecuted':0,'productAcceptance':False,'observerTimingPerturbation':True,'listenerInspectionFiles':{str(p.relative_to(support.ROOT)):support.bind(p) for p in inspected}}

def source_checks():
    """Strict source replay and negative mutations; no subprocess, scratch or native calls."""
    import stage_sources
    checks=0
    def need(value,label):
        nonlocal checks
        checks+=1
        if not value:raise AssertionError(label)
    adaptation=support.read(support.HERE/'source-adaptation.json')
    for name,row in adaptation['files'].items():
        expected,changes=stage_sources.transformed(name);actual=(support.HERE/name).read_text()
        need(support.sha(support.SCROLL/name)==row['upstreamSHA256'],'unchanged bound upstream '+name)
        need(actual==expected and support.sha(support.HERE/name)==row['candidateSHA256'] and changes==row['changes'],'exact finite source adaptation '+name)
    activity='fixture/AuthoredToggleSupplementActivity.java';instrument='fixture/AuthoredToggleSupplementInstrumentation.java'
    expectedActivity=stage_sources.transformed(activity)[0];expectedInstrument=stage_sources.transformed(instrument)[0]
    def validate(name,text):return text==stage_sources.transformed(name)[0]
    need(not validate(activity,expectedActivity.replace('content.setMinimumHeight(6000);','')),'missing extent correction rejected')
    need(not validate(instrument,expectedInstrument.replace(stage_sources.PRECONDITION,'')),'missing measured-extent precondition rejected')
    need(not validate(instrument,expectedInstrument.replace('&&window.scroll.canScrollVertically(1)','')),'missing canScrollDown precondition rejected')
    need(not validate(instrument,expectedInstrument.replace('base+i*25','base+i*26')),'changed timestamp schedule rejected')
    need(not validate(instrument,expectedInstrument.replace('y-i*35','y-i*34')),'changed coordinate rejected')
    need(not validate(instrument,expectedInstrument.replace('getScrollY()>0&&proposals==0','getScrollY()>=0&&proposals==0')),'weakened original scroll assertion rejected')
    old=(support.SCROLL/instrument).read_text();begin='            for(boolean direction:new boolean[]{false,true})for(boolean initial:';end='        }catch(Throwable caught){failure=caught;}'
    need(old[old.index(begin):old.index(end)]==expectedInstrument[expectedInstrument.index(begin):expectedInstrument.index(end)],'all45 original cases and assertions exact')
    start=expectedInstrument.index('    private void dispatchScroll(boolean diagonal)');inject=expectedInstrument.index('sendPointerSync(e)',start)
    need(start<expectedInstrument.index(stage_sources.PRECONDITION,start)<inject,'positive measured extent before injection')
    need('scroll.intercept.after' in expectedActivity and 'toggle.OnTouchListener.before-return-false' in expectedActivity,'native intercept and child CANCEL trace retained')
    _,source,_=run.load_runner();_,original,_=support.repair_runner();marker='    except BaseException as failure:\n'
    need(source[source.index(marker):]==original[original.index(marker):],'unchanged frozen failure and owned cleanup tail')
    for invalid in ('../runtime-1','runtime-0','runtime-01','other-1'):
        try:support.runtime_directory(invalid)
        except ValueError:checks+=1
        else:raise AssertionError('unsafe runtime path admitted')
    return {'status':'passed-read-only-finite-source-and-negative-controls','checks':checks,'nativeCommandsExecuted':0,'full45CaseSuiteAccepted':False}

def test():
    original=_inherited_test();fresh=source_checks()
    return {'status':'passed-fixture-only-extent-host-controls-native-NOT-RUN','checks':original['checks']+fresh['checks'],'inherited':original,'finiteSource':fresh,'nativeCommandsExecuted':0,'productAcceptance':False}

if __name__=='__main__':print(json.dumps(test(),sort_keys=True))

