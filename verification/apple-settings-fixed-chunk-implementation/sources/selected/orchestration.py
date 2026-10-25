"""Same private native sequence with reporting-independent resource cleanup.

Source preparation only. This function is exercised with mocked native/process
boundaries in host controls; the verify-only CLI supplies no native authority.
"""
import workspace_ownership
import join_support

class Outcome:
    def __init__(self,commands):
        self.commands=commands;self.first=None;self.traceback=None;self.failures=[]
    def fail(self,operation,error):
        if self.first is None:self.first=error;self.traceback=error.__traceback__
        self.failures.append(dict(operation=operation,type=type(error).__name__,message=self.commands.redact(str(error))))
    def attempt(self,operation,action):
        try:return action()
        except BaseException as error:self.fail(operation,error);return None
    def reporting(self):
        error=getattr(self.commands,'reporting_error',None)
        if error is not None and not any(value['operation']=='command-reporting' for value in self.failures):self.fail('command-reporting',error)


def run(h,bindings,runtime_roots,reviewed_seal,scope='interaction'):
    bindings.check(runtime_roots)
    h.RUN_DIR=h.select_runtime_directory(scope)
    selected_cases=h.SCOPES[scope]['cases'];verified=h.verify()
    h.require(reviewed_seal==verified['sealSHA256'],'Root reviewed seal does not match')
    h.RUN_DIR.mkdir(exist_ok=False)
    capability=h.secrets.token_hex(32)
    commands=h.Commands(h.RUN_DIR/'commands.json',capability)
    outcome=Outcome(commands)
    lifecycle=server=thread=ephemeral=bridge=result_path=xctest_exit=None
    allocation_returned=False
    cleanup_results=[]
    h.last_outcome=outcome;h.last_lifecycle=None;h.last_bridge=None;h.last_runtime_summary=None
    try:
        runtime_list=h.json.loads(commands.simctl('list','runtimes','--json'))
        runtime=next(value for value in runtime_list['runtimes'] if value['identifier']==h.RUNTIME)
        h.require(runtime['isAvailable'] and runtime['buildversion']==h.RUNTIME_BUILD,'Exact available iOS26.5(23F77) runtime required')
        root=join_support._ROOT;identity=root['ownedSimulatorIdentity']
        name=identity['name'];identifier=identity['udid']
        lifecycle=dict(schema='mixer.apple-toggle.xctest-lifecycle.1',ownedName=name,ownedSimulator=identifier,creationIntentRecordedBeforeCommand=False,rootSelectedExistingOwnedSimulator=True,before=root['baselineDevices'],beforeFrontends=root['baselineFrontends'],verifiedHandoff=verified,runtime=runtime,apps={},cleanedUp=False,nativeExecutionAttempted=True,physicalDevices='disconnected-deferred')
        h.last_lifecycle=lifecycle
        h.write(h.RUN_DIR/'lifecycle.json',lifecycle)
        owned=h.owned_device(lifecycle,h.devices(commands))
        h.require(owned is not None and owned['state'] in ['Shutdown','Booted'],'Exact root-owned simulator unavailable')
        if owned['state']=='Shutdown':commands.simctl('boot',identifier)
        commands.run(['/usr/bin/xcrun','simctl','bootstatus',identifier,'-b'],timeout=120)
        documents={}
        for key,config in h.packet.CONFIGS.items():
            destination=h.RUN_DIR/'restored-app'/key;h.packet.restore(destination,key);app=destination/config['app']
            commands.simctl('install',identifier,str(app))
            installed=h.validate_container(commands.simctl('get_app_container',identifier,config['bundle'],'app'),identifier)
            installed_validation=h.packet.verify_installed(installed,key,commands.record)
            container=h.validate_container(commands.simctl('get_app_container',identifier,config['bundle'],'data'),identifier,data=True)
            docs=container/'Documents';docs.mkdir(exist_ok=True);h.require(docs.resolve()==docs,'Documents redirected');documents[key]=docs
            lifecycle['apps'][key]=dict(container=str(container),installed=installed_validation);h.write(h.RUN_DIR/'lifecycle.json',lifecycle)
        bridge=h.Bridge(documents,h.RUN_DIR/'captures',capability,dict(udid=identifier,name=name,runtime=h.RUNTIME,build=h.RUNTIME_BUILD),lifetime=600,allowed_cases=selected_cases)
        h.last_bridge=bridge
        server=h.server_for(bridge);thread=h.threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        ephemeral=join_support.prepare_session(h,lifecycle)
        allocation_returned=True
        h.write(h.RUN_DIR/'lifecycle.json',lifecycle)
        config_path=join_support.session_configuration(h,ephemeral,server.server_port,capability)
        result_path=ephemeral/'session.xcresult'
        argv=[str(h.DEVELOPER/'usr/bin/xcodebuild'),'test-without-building','-xctestrun',str(config_path),'-destination','platform=iOS Simulator,id='+identifier,'-parallel-testing-enabled','NO','-maximum-concurrent-test-simulator-destinations','1','-resultBundlePath',str(result_path)]
        argv+=['-only-testing:MixerToggleUITests/ToggleUITests/'+method for method in h.SCOPES[scope]['methods']]
        join_support.select_command(h,argv,ephemeral)
        xctest_exit=commands.run(argv,timeout=600,check=False)[0]
        if xctest_exit==0 and commands.reporting_error is not None:raise commands.reporting_error
        h.require(xctest_exit in [0,65],'Unsupported XCTest terminal code; preserve evidence')
    except BaseException as error:
        outcome.fail('session',error)
        outcome.attempt('session-failure-report',lambda:commands.record('session-failure',dict(type=type(error).__name__,message=commands.redact(str(error)))))
    finally:
        # Register every owned cleanup operation before optional export/reporting.
        operations=[]
        if server is not None:operations.append(('loopback-server-shutdown',server.shutdown))
        if server is not None:operations.append(('loopback-server-close',server.server_close))
        if thread is not None:
            def join_thread():
                thread.join(timeout=3);h.require(not thread.is_alive(),'Bridge thread did not exit')
            operations.append(('loopback-thread-join',join_thread))
        if allocation_returned:operations.append(('ephemeral-capability-workspace-removal',lambda:join_support.retire_session(h,lifecycle)))
        if lifecycle is not None:operations.append(('owned-simulator-and-baseline-reconciliation',lambda:h.cleanup(lifecycle,commands)))
        try:
            commands.cleanup_mode=True
            pass  # Official output already captured by the selected wrapper.
        except BaseException as error:
            outcome.fail('optional-result-export',error)
        finally:
            # No reporting operation can prevent even the first cleanup attempt.
            for label,operation in operations:
                try:operation();cleanup_results.append(dict(resource=label,passed=True))
                except BaseException as error:
                    outcome.fail(label,error);cleanup_results.append(dict(resource=label,passed=False,failureType=type(error).__name__,message=commands.redact(str(error))))
            capability=None
            outcome.reporting()
            outcome.attempt('cleanup-report',lambda:commands.record('all-independent-cleanup-attempts',dict(results=cleanup_results)))
            outcome.reporting()
            if lifecycle is not None:
                lifecycle.update(cleanedUp=all(row['passed'] for row in cleanup_results),cleanupResults=cleanup_results)
                outcome.attempt('lifecycle-final-report',lambda:h.write(h.RUN_DIR/'lifecycle.json',lifecycle))
            failure=None if outcome.first is None else dict(type=type(outcome.first).__name__,message=commands.redact(str(outcome.first)))
            def final_report():
                final=h.runtime_summary(scope,bridge,xctest_exit,failure,cleanup_results)
                final.update(reportingFailures=list(outcome.failures),runPassed=final['runPassed'] and outcome.first is None)
                h.last_runtime_summary=final;h.write(h.RUN_DIR/'runtime-verdict.json',final)
            outcome.attempt('runtime-final-report',final_report)
            outcome.reporting()
            if outcome.first is not None and h.last_runtime_summary is not None:
                h.last_runtime_summary.update(runPassed=False,sessionFailure=dict(type=type(outcome.first).__name__,message=commands.redact(str(outcome.first))),reportingFailures=list(outcome.failures))
    if outcome.first is not None:raise outcome.first.with_traceback(outcome.traceback)
    return h.last_runtime_summary
