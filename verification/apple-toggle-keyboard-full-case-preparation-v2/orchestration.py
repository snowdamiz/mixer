"""Same private native sequence with reporting-independent resource cleanup.

Source preparation only. This function is exercised with mocked native/process
boundaries in host controls; the verify-only CLI supplies no native authority.
"""
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
    cleanup_results=[]
    h.last_outcome=outcome;h.last_lifecycle=None;h.last_bridge=None;h.last_runtime_summary=None
    try:
        runtime_list=h.json.loads(commands.simctl('list','runtimes','--json'))
        runtime=next(value for value in runtime_list['runtimes'] if value['identifier']==h.RUNTIME)
        h.require(runtime['isAvailable'] and runtime['buildversion']==h.RUNTIME_BUILD,'Exact available iOS26.5(23F77) runtime required')
        before=h.devices(commands);name='MixerTogglePanOrigin-'+str(h.uuid.uuid4())
        lifecycle=dict(schema='mixer.apple-toggle.xctest-lifecycle.1',ownedName=name,ownedSimulator=None,creationIntentRecordedBeforeCommand=True,before=before,beforeFrontends=h.frontends(commands),verifiedHandoff=verified,runtime=runtime,apps={},cleanedUp=False,nativeExecutionAttempted=True,physicalDevices='disconnected-deferred')
        h.last_lifecycle=lifecycle
        h.write(h.RUN_DIR/'lifecycle.json',lifecycle)
        identifier=commands.simctl('create',name,h.DEVICE_TYPE,h.RUNTIME);h.uuid.UUID(identifier)
        lifecycle['ownedSimulator']=identifier;h.write(h.RUN_DIR/'lifecycle.json',lifecycle)
        h.owned_device(lifecycle,h.devices(commands));commands.simctl('boot',identifier)
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
        original=list(h.PRODUCTS.glob('*.xctestrun'));h.require(len(original)==1,'One exact prepared xctestrun required')
        configuration=h.plistlib.loads(original[0].read_bytes());target=configuration['MixerToggleUITests']
        for key in ['EnvironmentVariables','TestingEnvironmentVariables']:
            target[key].update(MIXER_BRIDGE_URL=f'http://127.0.0.1:{server.server_port}',MIXER_BRIDGE_CAPABILITY=capability)
        target.update(TestTimeoutsEnabled=True,DefaultTestExecutionTimeAllowance=30,MaximumTestExecutionTimeAllowance=45,ParallelizationEnabled=False,UserAttachmentLifetime='keepAlways',SystemAttachmentLifetime='keepAlways')
        def absolute(value):
            if isinstance(value,str):return value.replace('__TESTROOT__',str(h.PRODUCTS))
            if isinstance(value,dict):return {key:absolute(item) for key,item in value.items()}
            if isinstance(value,list):return [absolute(item) for item in value]
            return value
        ephemeral=h.pathlib.Path(h.tempfile.mkdtemp(prefix='mixer-toggle-xctest-')).resolve();ephemeral.chmod(0o700);info=ephemeral.stat()
        lifecycle['ephemeralWorkspace']=dict(path=str(ephemeral),device=info.st_dev,inode=info.st_ino,uid=info.st_uid);h.write(h.RUN_DIR/'lifecycle.json',lifecycle)
        config_path=ephemeral/'session.xctestrun';config_path.write_bytes(h.plistlib.dumps(absolute(configuration)));config_path.chmod(0o600)
        result_path=ephemeral/'session.xcresult'
        argv=[str(h.DEVELOPER/'usr/bin/xcodebuild'),'test-without-building','-xctestrun',str(config_path),'-destination','platform=iOS Simulator,id='+identifier,'-parallel-testing-enabled','NO','-maximum-concurrent-test-simulator-destinations','1','-resultBundlePath',str(result_path)]
        argv+=['-only-testing:MixerToggleUITests/ToggleUITests/'+method for method in h.SCOPES[scope]['methods']]
        xctest_exit=commands.run(argv,timeout=600,check=False)[0]
        if xctest_exit==0 and commands.reporting_error is not None:raise commands.reporting_error
        summary=h.runtime_summary(scope,bridge,xctest_exit,None,None);h.write(h.RUN_DIR/'runtime-verdict.json',summary)
        h.require(xctest_exit==0 and summary['strictNativeVerdictsPassed'] is True and summary['bridgeFailures']==[],'Strict XCTest result failed; preserved evidence is authoritative')
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
        if ephemeral is not None:operations.append(('ephemeral-capability-workspace-removal',lambda:h.remove_ephemeral(lifecycle)))
        if lifecycle is not None:operations.append(('owned-simulator-and-baseline-reconciliation',lambda:h.cleanup(lifecycle,commands)))
        try:
            commands.cleanup_mode=True
            if result_path is not None and result_path.exists():
                for kind in ['summary','tests']:
                    def export(kind=kind):
                        try:
                            code,output,_=commands.run(['/usr/bin/xcrun','xcresulttool','get','test-results',kind,'--path',str(result_path)],check=False)
                            if code==0:(h.RUN_DIR/('xctest-'+kind+'.json')).write_text(commands.redact(output)+'\n')
                        except BaseException as error:
                            outcome.fail('official-'+kind+'-export',error)
                            outcome.attempt('official-'+kind+'-failure-report',lambda:commands.record('official-result-export-unavailable',dict(kind=kind,type=type(error).__name__,message=commands.redact(str(error)))))
                    outcome.attempt('official-'+kind+'-export-wrapper',export)
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
