"""LLDB-only controls of actual production frames, never product outcomes."""
import json, pathlib, shlex, time, struct
import lldb
EVENTS=[]
FAILED=[]
def stale_gate(frame,bp_loc,internal):
    process=frame.GetThread().GetProcess();target=process.GetTarget();marker=target.FindFirstGlobalVariable('debug_phase')
    error=lldb.SBError();raw=process.ReadMemory(marker.GetLoadAddress(),4,error)
    return error.Success() and len(raw)==4 and struct.unpack('I',raw)[0]==10
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
def target_expression(target,code):
    options=lldb.SBExpressionOptions();options.SetLanguage(lldb.eLanguageTypeSwift);options.SetIgnoreBreakpoints(True);options.SetTimeoutInMicroSeconds(5000000)
    value=target.EvaluateExpression(code,options)
    require(value.GetError().Success(),code+': '+str(value.GetError()))
    stream=lldb.SBStream();value.GetDescription(stream)
    EVENTS.append({'point':'global-debugger-expression','code':code,'output':stream.GetData()})
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
            elif scenario=='stale-cleanup-replay':
                path=source/'capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIAndroidBinding.swift'
                line=next(i for i,v in enumerate(path.read_text().splitlines(),1) if 'guard let cleanup = last.facadeCleanup' in v)
                first=target.BreakpointCreateByLocation(str(path),line);first.SetScriptCallbackFunction('debugger_driver.stale_gate');hold=True
            elif scenario=='reservation-hold':
                first=target.BreakpointCreateByName('mxuit_facade_acquire');hold=True
            elif scenario in ('cleanup-wrong-entry','cleanup-wrong-generation'):
                first=target.BreakpointCreateByName('mxis_host_inspect');first.SetIgnoreCount(1)
            elif scenario=='progress-tail':
                first=target.BreakpointCreateByRegex('CapabilityAndroidProgressCell.*register');hold=True
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
                regex={'waiter-exhaustion':'CapabilityAndroidLifetimeControl.*reserveWaiter','progress-token-exhaustion':'CapabilityAndroidProgressCell.*register','progress-sequence-exhaustion':'CapabilityAndroidProgressCell.*register','lifetime-exhaustion':'CapabilityAndroidRegistry.*acquireEndpoint'}[scenario]
                first=target.BreakpointCreateByRegex(regex)
            if scenario!='stale-cleanup-replay':first.SetOneShot(True)
        error=lldb.SBError();process=target.Launch(launch,error)
        require(error.Success(),'launch: '+str(error))
        if scenario=='gate-order':
            require(process.GetState()==lldb.eStateExited,'gate process exit')
            require(not FAILED and [e['point'] for e in EVENTS]==['gate-reserved','C-acquire'],'actual gate order '+repr(EVENTS))
        else:
            require(process.GetState()==lldb.eStateStopped,'production breakpoint resolved/stopped')
            thread=process.GetSelectedThread();frame=thread.GetFrameAtIndex(0)
            if scenario=='progress-tail':
                EVENTS.append({'point':'actual-progress-registration-entry','function':frame.GetFunctionName(),'thread':thread.GetThreadID()})
                thread.StepOut();frame=thread.GetFrameAtIndex(0)
                require('wait' in (frame.GetFunctionName() or ''),'actual register helper returned with exact waiter published')
                EVENTS.append({'point':'actual-progress-registration-return','function':frame.GetFunctionName(),'thread':thread.GetThreadID()})
                name='$s25MixerCapabilityActivation25capabilityAndroidProgressyys6UInt64V_ADs5Int32VtF'
                symbols=target.FindSymbols(name,lldb.eSymbolTypeCode)
                require(symbols.GetSize()==1,'exact frozen Swift progress symbol')
                symbol=symbols.GetContextAtIndex(0).GetSymbol();instructions=symbol.GetInstructions(target)
                rows=[];resume=[]
                for instruction in instructions:
                    row={'pc':instruction.GetAddress().GetLoadAddress(target),'mnemonic':instruction.GetMnemonic(target),'operands':instruction.GetOperands(target),'comment':instruction.GetComment(target)}
                    rows.append(row)
                    if row['mnemonic'] in ('bl','callq','call') and 'resume' in row['comment']:resume.append(row)
                EVENTS.append({'point':'frozen-actual-progress-disassembly','instructions':rows})
                require(len(resume)==1,'exact one actual continuation.resume call in frozen function: '+repr(resume))
                after=resume[0]['pc']+4
                next_break=target.BreakpointCreateByAddress(after);next_break.SetOneShot(True);first.SetEnabled(False)
                marker=target.FindFirstGlobalVariable('debug_phase');error=lldb.SBError()
                require(process.WriteMemory(marker.GetLoadAddress(),struct.pack('I',1),error)==4 and error.Success(),'signal actual progress waiter registered')
                EVENTS.append({'point':'signal-registered-progress-wait','phase':1})
                process.Continue();require(process.GetState()==lldb.eStateStopped,'actual continuation resume returned before held tail')
                thread=process.GetSelectedThread()
                frame=next((thread.GetFrameAtIndex(i) for i in range(thread.GetNumFrames()) if thread.GetFrameAtIndex(i).GetPC()==after and 'capabilityAndroidProgress' in (thread.GetFrameAtIndex(i).GetFunctionName() or '')),thread.GetFrameAtIndex(0))
                EVENTS.append({'point':'post-resume-actual-native-stack','frames':[{'index':i,'function':thread.GetFrameAtIndex(i).GetFunctionName(),'pc':thread.GetFrameAtIndex(i).GetPC()} for i in range(thread.GetNumFrames())]})
                require(frame.GetPC()==after and 'capabilityAndroidProgress' in (frame.GetFunctionName() or ''),'exact post-resume native frame')
                EVENTS.append({'point':'actual-continuation-resume-returned','pc':after,'thread':thread.GetThreadID(),'function':frame.GetFunctionName()})
                outgoing=frame.FindVariable('outgoing')
                if outgoing.IsValid() and outgoing.GetError().Success():
                    stream=lldb.SBStream();outgoing.GetDescription(stream);count=outgoing.GetNumChildren()
                    EVENTS.append({'point':'actual-consumed-continuation-array','type':outgoing.GetTypeName(),'description':stream.GetData(),'element_count':count,'raw_bytes':outgoing.GetNonSyntheticValue().GetData().GetByteSize()})
                    require(count>0,'actual consumed continuation array remains alive')
                    variable=frame.FindVariable('continuation')
                    if not variable.IsValid() or not variable.GetError().Success() or variable.GetData().GetByteSize()==0:variable=outgoing.GetChildAtIndex(0)
                    require(variable.IsValid() and variable.GetError().Success() and variable.GetData().GetByteSize()>0 and 'CheckedContinuation' in (variable.GetTypeName() or ''),'actual consumed continuation local/array copy remains available')
                    stream=lldb.SBStream();variable.GetDescription(stream)
                    EVENTS.append({'point':'actual-consumed-continuation-local-or-array-copy','type':variable.GetTypeName(),'description':stream.GetData(),'raw_bytes':variable.GetData().GetByteSize()})
                else:
                    # Release eliminated debug-variable locations. Establish
                    # every read from these exact frozen ARM64 instructions.
                    ops=[(r['mnemonic'],r['operands'].replace(' ','')) for r in rows]
                    required=[('mov','x23,x8'),('ldr','x21,[x8,#0x10]'),('add','x9,x8,#0x20'),('bic','x8,x9,x8'),('add','x20,x23,x8'),('ldr','x22,[x22,#0x48]'),('add','x20,x20,x22'),('subs','x21,x21,#0x1')]
                    require(all(item in ops for item in required),'exact array/count/element/stride/remaining register bindings in frozen loop')
                    tail=[r for r in rows if r['pc']>after]
                    require(any(r['mnemonic']=='mov' and r['operands'].replace(' ','')=='x0,x23' for r in tail) and any('swift_bridgeObjectRelease' in r['comment'] for r in tail),'actual outgoing array ARC release remains after held PC')
                    array=frame.FindRegister('x23').GetValueAsUnsigned();element=frame.FindRegister('x20').GetValueAsUnsigned();remaining=frame.FindRegister('x21').GetValueAsUnsigned();stride=frame.FindRegister('x22').GetValueAsUnsigned()
                    require(array>0 and 0<stride<=64 and 32<=element-array<=128,'bounded actual array/element/stride values')
                    read_error=lldb.SBError();count_bytes=process.ReadMemory(array+0x10,8,read_error)
                    require(read_error.Success() and len(count_bytes)==8,'actual compiled count-load memory is readable')
                    count=struct.unpack('<Q',count_bytes)[0]
                    require(count==1 and remaining==1,'one actual resumed continuation copy still in retained outgoing storage')
                    copy=process.ReadMemory(element,stride,read_error)
                    require(read_error.Success() and len(copy)==stride and any(copy),'actual consumed continuation element storage remains readable')
                    EVENTS.append({'point':'actual-consumed-continuation-register-memory-proof','array_address':array,'compiled_count_address':array+0x10,'actual_count':count,'remaining':remaining,'stride':stride,'element_address':element,'element_offset':element-array,'element_bytes_hex':copy.hex(),'instruction_bindings':required,'later_arc_release':True,'scope':'Read-only exact optimized ARM64 loop/storage inspection; no guessed array layout or target ownership calls'})
            EVENTS.append({'point':'production-breakpoint','thread':thread.GetThreadID(),'pc':frame.GetPC(),'function':frame.GetFunctionName(),'description':str(frame)})
            if scenario=='post-store':
                expression(frame,'self.terminal')
                stack=[{'index':i,'function':thread.GetFrameAtIndex(i).GetFunctionName(),'pc':thread.GetFrameAtIndex(i).GetPC()} for i in range(thread.GetNumFrames())]
                EVENTS.append({'point':'actual-terminal-helper-call-stack','frames':stack})
                caller=next((thread.GetFrameAtIndex(i) for i in range(1,thread.GetNumFrames()) if 'CapabilityAndroidLifetimeControl.run' in (thread.GetFrameAtIndex(i).GetFunctionName() or '')),thread.GetFrameAtIndex(1))
                EVENTS.append({'point':'actual-presentation-caller-before-terminal-helper-return','function':caller.GetFunctionName(),'pc':caller.GetPC(),'description':str(caller)})
                require('CapabilityAndroidLifetimeControl.run' in (caller.GetFunctionName() or ''),'actual synchronous terminal helper called by presentation run')
                return_pc=caller.GetPC()
                before=target.ReadInstructions(target.ResolveLoadAddress(return_pc-4),2)
                decoded=[]
                for instruction in before:
                    decoded.append({'pc':instruction.GetAddress().GetLoadAddress(target),'mnemonic':instruction.GetMnemonic(target),'operands':instruction.GetOperands(target),'comment':instruction.GetComment(target)})
                EVENTS.append({'point':'actual-terminal-helper-return-pc-binding','instructions':decoded})
                require(decoded and 'finishTask' in decoded[0]['comment'],'exact caller return follows real terminal helper call')
                returned=target.BreakpointCreateByAddress(return_pc);returned.SetOneShot(True);first.SetEnabled(False)
                process.Continue()
                require(process.GetState()==lldb.eStateStopped,'terminal helper and actual lock unlock returned')
                thread=process.GetSelectedThread();frame=thread.GetFrameAtIndex(0)
                require(frame.GetPC()==return_pc and 'CapabilityAndroidLifetimeControl.run' in (frame.GetFunctionName() or ''),'actual run suspended before Task return: '+str(frame))
                EVENTS.append({'point':'after-terminal-helper-return-before-task-return','thread':thread.GetThreadID(),'pc':frame.GetPC(),'function':frame.GetFunctionName(),'description':str(frame)})
                expression(frame,'self.terminal')
            elif scenario=='stale-cleanup-replay':
                require('finishFinalClose' in (frame.GetFunctionName() or ''),'actual later final gate cleanup comparison')
                first.SetEnabled(False)
            elif scenario=='reservation-hold':
                callers=[thread.GetFrameAtIndex(i) for i in range(1,thread.GetNumFrames()) if 'CapabilityAndroidRegistry.acquireFacade' in (thread.GetFrameAtIndex(i).GetFunctionName() or '')]
                EVENTS.append({'point':'actual-reserved-facade-caller-stack','frames':[{'function':c.GetFunctionName(),'pc':c.GetPC(),'self':str(c.FindVariable('self')),'record':str(c.FindVariable('record'))} for c in callers]})
                caller=next((c for c in callers if c.FindVariable('self').IsValid() and c.FindVariable('self').GetValueAsUnsigned()!=0),callers[-1] if callers else None)
                require(caller is not None,'real reserved Swift facade caller above native acquire')
                reserved=expression(caller,'self.facades[0].reserved')
                require(reserved.GetValueAsUnsigned()==1,'actual first Swift facade record reserved before C acquisition')
                native=expression(caller,'self.facades[0].facade')
                require(native.GetValueAsUnsigned()==0,'actual Swift record has no published C facade yet')
            elif scenario in ('cleanup-wrong-entry','cleanup-wrong-generation'):
                actual=expression(frame,'host.slots[0].cleared',lldb.eLanguageTypeC)
                require(actual.GetValueAsUnsigned()==1,'actual native final clear already completed')
                original=expression(frame,'entry',lldb.eLanguageTypeC).GetValueAsUnsigned()
                cleared=expression(frame,'host.slots[0].final_entry',lldb.eLanguageTypeC).GetValueAsUnsigned()
                require(original>0 and original==cleared,'exact actual same-entry final native observation before failure control')
                if scenario=='cleanup-wrong-entry':
                    value=frame.FindVariable('entry');error=value.SetValueFromCString(str(original+1))
                    require(error,'failure-only native entry argument changed at its actual boundary')
                    wrong=expression(frame,'entry',lldb.eLanguageTypeC)
                    require(wrong.GetValueAsUnsigned()==original+1,'real native lease validator will receive wrong entry')
                else:
                    expression(frame,'({ ((int(*)(__typeof__(&host.lock)))pthread_mutex_lock)(&host.lock); host.slots[0].generation = 18446744073709551615ULL; ((int(*)(__typeof__(&host.lock)))pthread_mutex_unlock)(&host.lock); })',lldb.eLanguageTypeC)
                    wrong=expression(frame,'host.slots[0].generation',lldb.eLanguageTypeC)
                    require(wrong.GetValueAsUnsigned()==18446744073709551615,'actual fixed native slot generation poisoned under its real lock')
            elif scenario=='lifetime-exhaustion':
                expression(frame,'CapabilityPresentationLifetimeID.counter.value = UInt64.max')
                expression(frame,'CapabilityPresentationLifetimeID.counter.value')
            elif scenario=='progress-sequence-exhaustion':
                thread.StepOut();frame=thread.GetFrameAtIndex(0)
                EVENTS.append({'point':'actual-progress-register-return','function':frame.GetFunctionName(),'description':str(frame)})
                expression(frame,'cell.sequence = UInt64.max')
                expression(frame,'cell.sequence')
            elif scenario=='cancel-accepted':
                selected=None
                for frame_index in range(1,thread.GetNumFrames()):
                    candidate=thread.GetFrameAtIndex(frame_index);value=candidate.FindVariable('binding')
                    if 'acceptedTaskCancellationPoint' in (candidate.GetFunctionName() or '') and value.IsValid() and value.GetValueAsUnsigned()!=0:
                        selected=candidate;break
                require(selected is not None,'exact verification holder frame with caller-owned binding')
                frame=selected
                EVENTS.append({'point':'exact-accepted-task-owner-frame','function':frame.GetFunctionName(),'description':str(frame)})
                binding=frame.FindVariable('binding')
                require(binding.IsValid() and binding.GetValueAsUnsigned()!=0,'exact caller-owned scalar binding handle available')
                address=binding.GetValueAsUnsigned()
                EVENTS.append({'point':'exact-owned-binding-address','address':address,'type':binding.GetTypeName()})
                context=None
                for thread_index in range(process.GetNumThreads()):
                    candidate=process.GetThreadAtIndex(thread_index)
                    for frame_index in range(candidate.GetNumFrames()):
                        native_frame=candidate.GetFrameAtIndex(frame_index)
                        if 'CapabilityGuestUIAndroidResources' in (native_frame.GetFunctionName() or ''):
                            context=native_frame;break
                    if context is not None:break
                require(context is not None,'actual product Swift frame of held native RETIRE helper')
                EVENTS.append({'point':'actual-product-swift-evaluation-context','thread':context.GetThread().GetThreadID(),'function':context.GetFunctionName()})
                handle='Unmanaged<MixerCapabilityActivation.CapabilityGuestUIAndroidBinding>.fromOpaque(UnsafeRawPointer(bitPattern: '+str(address)+')!).takeUnretainedValue().current!.lifetime.task!'
                if ' [opt]' in str(context):
                    target_expression(target,'@testable import MixerCapabilityActivation\n'+handle+'.cancel()')
                    target_expression(target,'@testable import MixerCapabilityActivation\n'+handle+'.isCancelled')
                else:
                    expression(context,handle+'.cancel()')
                    expression(context,handle+'.isCancelled')
            elif scenario=='progress-tail':
                pass
            elif scenario=='bind-return':
                EVENTS.append({'point':'actual-bind-return-frame','description':str(frame),'same_original_worker':thread.GetThreadID()})
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
            require(process.WriteMemory(address,struct.pack('I',2 if scenario=='progress-tail' else 11 if scenario=='stale-cleanup-replay' else 1),write_error)==4 and write_error.Success(),'signal fixed verification-only barrier')
            EVENTS.append({'point':'signal-test-barrier','address':address,'value':2 if scenario=='progress-tail' else 11 if scenario=='stale-cleanup-replay' else 1})
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
