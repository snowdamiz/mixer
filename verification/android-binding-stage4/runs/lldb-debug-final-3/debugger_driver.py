"""LLDB-only controls of actual production frames, never product outcomes."""
import json, pathlib, shlex, time, struct
import lldb
EVENTS=[]
FAILED=[]
def gate(frame, bp_loc, internal):
    EVENTS.append({'point':'gate-reserved','thread':frame.GetThread().GetThreadID(),'function':frame.GetFunctionName()})
    return False
def acquire(frame,bp_loc,internal):
    if not EVENTS or EVENTS[-1]['point']!='gate-reserved':FAILED.append('C acquire preceded actual gate reservation')
    EVENTS.append({'point':'C-acquire','thread':frame.GetThread().GetThreadID(),'function':frame.GetFunctionName()})
    return False
def require(condition,message):
    if not condition:raise RuntimeError(message)
def expression(frame, code, language=lldb.eLanguageTypeSwift):
    options=lldb.SBExpressionOptions();options.SetLanguage(language);options.SetIgnoreBreakpoints(True);options.SetTimeoutInMicroSeconds(5000000)
    value=frame.EvaluateExpression(code,options)
    require(value.GetError().Success(),code+': '+str(value.GetError()))
    stream=lldb.SBStream();value.GetDescription(stream)
    EVENTS.append({'point':'debugger-expression','code':code,'output':stream.GetData()})
    return value
def command(debugger,text,result,internal):
    global EVENTS,FAILED
    EVENTS=[];FAILED=[]
    binary,scenario,output,source=shlex.split(text)
    output=pathlib.Path(output);source=pathlib.Path(source)
    target=debugger.CreateTarget(binary);require(target.IsValid(),'create target')
    debugger.SetAsync(False)
    launch=lldb.SBLaunchInfo([scenario]);launch.SetWorkingDirectory(str(output.parent))
    launch.AddOpenFileAction(1,str(output.with_suffix('.stdout')),False,True)
    launch.AddOpenFileAction(2,str(output.with_suffix('.stderr')),False,True)
    hold=False;held_thread=None
    try:
        if scenario=='gate-order':
            first=target.BreakpointCreateByRegex('CapabilityAndroidLifetimeControl.*reserveBindGate')
            first.SetScriptCallbackFunction('debugger_driver.gate')
            second=target.BreakpointCreateByName('mxuit_acquire_for_facade')
            second.SetScriptCallbackFunction('debugger_driver.acquire')
        else:
            if scenario=='post-store':
                first=target.BreakpointCreateByRegex('CapabilityAndroidLifetimeControl.*finishTask')
                hold=True
            elif scenario=='bind-return':
                path=source/'capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIAndroidBinding.swift'
                line=next(i for i,v in enumerate(path.read_text().splitlines(),1) if 'return installation' in v)
                first=target.BreakpointCreateByLocation(str(path),line);hold=True
            elif scenario=='cancel-accepted':
                first=target.BreakpointCreateByName('mxish_debug_release_point')
            elif scenario=='setup-alias':
                path=source/'capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIAndroidResources.swift'
                line=next(i for i,v in enumerate(path.read_text().splitlines(),1) if 'guard resources.exchange == nil' in v)
                first=target.BreakpointCreateByLocation(str(path),line);hold=True
            else:
                regex={'waiter-exhaustion':'CapabilityAndroidLifetimeControl.*reserveWaiter','progress-token-exhaustion':'CapabilityAndroidProgressCell.*register','progress-sequence-exhaustion':'CapabilityAndroidProgressCell.*merge','lifetime-exhaustion':'CapabilityPresentationCounter.*issue'}[scenario]
                first=target.BreakpointCreateByRegex(regex)
            first.SetOneShot(True)
        error=lldb.SBError();process=target.Launch(launch,error)
        require(error.Success(),'launch: '+str(error))
        if scenario=='gate-order':
            require(process.GetState()==lldb.eStateExited,'gate process exit')
            require(not FAILED and [e['point'] for e in EVENTS]==['gate-reserved','C-acquire'],'actual gate order '+repr(EVENTS))
        else:
            require(process.GetState()==lldb.eStateStopped,'production breakpoint resolved/stopped')
            thread=process.GetSelectedThread();frame=thread.GetFrameAtIndex(0)
            EVENTS.append({'point':'production-breakpoint','thread':thread.GetThreadID(),'pc':frame.GetPC(),'function':frame.GetFunctionName(),'description':str(frame)})
            if scenario=='post-store':
                expression(frame,'self.terminal')
                thread.StepOut()
                require(process.GetState()==lldb.eStateStopped,'synchronous helper returned')
                frame=thread.GetFrameAtIndex(0)
                require('CapabilityAndroidLifetimeControl.run' in (frame.GetFunctionName() or ''),'step-out reached actual run before its return: '+str(frame))
                EVENTS.append({'point':'after-terminal-helper-return-before-task-return','thread':thread.GetThreadID(),'pc':frame.GetPC(),'function':frame.GetFunctionName(),'description':str(frame)})
                expression(frame,'self.terminal')
            elif scenario=='cancel-accepted':
                frame=thread.GetFrameAtIndex(1)
                EVENTS.append({'point':'exact-accepted-task-owner-frame','function':frame.GetFunctionName(),'description':str(frame)})
                expression(frame,'binding.current!.lifetime.task!.cancel()')
                expression(frame,'binding.current!.lifetime.task!.isCancelled')
            elif scenario=='bind-return':
                expression(frame,'installation.key')
            elif scenario=='setup-alias':
                variable=frame.FindVariable('resources')
                require(variable.IsValid() and variable.GetValueAsUnsigned()!=0,'actual promoted strong resource local present')
                EVENTS.append({'point':'actual-strong-resource-local','type':variable.GetTypeName(),'address':variable.GetValueAsUnsigned()})
            else:
                field={'waiter-exhaustion':'waiterSerial','progress-token-exhaustion':'issued','progress-sequence-exhaustion':'sequence','lifetime-exhaustion':'value'}[scenario]
                expression(frame,'self.'+field+' = UInt64.max')
                expression(frame,'self.'+field)
            marker=target.FindFirstGlobalVariable('debug_phase')
            require(marker.IsValid(),'fixed verification barrier symbol')
            address=marker.GetLoadAddress();write_error=lldb.SBError()
            require(process.WriteMemory(address,struct.pack('I',1),write_error)==4 and write_error.Success(),'signal fixed verification-only barrier')
            EVENTS.append({'point':'signal-test-barrier','address':address,'value':1})
            if hold:
                held_thread=thread
                require(held_thread.Suspend(),'suspend exact original production worker')
                release=target.BreakpointCreateByName('mxish_debug_release_point');release.SetOneShot(True)
                discarded=lldb.SBEvent()
                while debugger.GetListener().GetNextEvent(discarded):pass
                debugger.SetAsync(True);process.Continue()
                deadline=time.monotonic()+20
                released=False
                while time.monotonic()<deadline:
                    event=lldb.SBEvent();debugger.GetListener().WaitForEvent(1,event)
                    if not released and process.GetState()==lldb.eStateStopped:
                        current=None
                        for index in range(process.GetNumThreads()):
                            candidate=process.GetThreadAtIndex(index)
                            if 'mxish_debug_release_point' in (candidate.GetFrameAtIndex(0).GetFunctionName() or ''):
                                current=candidate;break
                        if current is not None:
                            current_frame=current.GetFrameAtIndex(0)
                            EVENTS.append({'point':'other-worker-verified-hold','thread':current.GetThreadID(),'function':current_frame.GetFunctionName(),'held_thread':held_thread.GetThreadID()})
                            require(held_thread.Resume(),'resume original production worker unchanged')
                            released=True;process.Continue()
                    if process.GetState()==lldb.eStateExited:break
                require(released and process.GetState()==lldb.eStateExited,'held worker resumed and process exited')
            else:
                process.Continue();require(process.GetState()==lldb.eStateExited,'failure-only counter scenario exited')
        require(process.GetExitStatus()==0,'harness exit '+str(process.GetExitStatus()))
        stdout=output.with_suffix('.stdout').read_text();require('DEBUG_HOLD_PASS '+scenario in stdout,'actual harness assertions passed: '+stdout)
        receipt={'scenario':scenario,'result':'passed','binary':binary,'events':EVENTS,'stdout':stdout,'exit':process.GetExitStatus(),'scope':'Actual unchanged production-byte frames under LLDB. Worker stop/resume or failure-only checked counter write; no success/cleanup/join receipt or C fence injection.'}
        output.write_text(json.dumps(receipt,indent=2)+'\n');result.AppendMessage('LLDB_PASS '+scenario)
    except BaseException as error:
        if held_thread and held_thread.IsSuspended():held_thread.Resume()
        p=target.GetProcess()
        if p.IsValid() and p.GetState()!=lldb.eStateExited:p.Kill()
        output.write_text(json.dumps({'scenario':scenario,'result':'failed','error':str(error),'events':EVENTS},indent=2)+'\n')
        result.SetError(str(error))
def __lldb_init_module(debugger,internal):
    debugger.HandleCommand('command script add -f debugger_driver.command stage4-debugger')
