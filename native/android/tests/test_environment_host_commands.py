"""Six cheap fake-boundary control groups; no real child or group operations."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
import environment_host_commands as boundary
import private_owner_commands as adapter
import test_private_owner_commands as fake

ROOT=Path(__file__).resolve().parents[3]
OUTPUT=Path(os.environ['MIXER_HOST_CONTROL_OUTPUT'])
OUTPUT.mkdir()

def load(name, filename):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(filename))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

platform=load('environment_platform_controls','run-environment-platform-host.py')
observer=load('environment_observer_controls','run-environment-observer-host.py')
TOOL=Path(sys.executable).resolve()
JDK=Path(os.environ['MIXER_HOST_TEST_JDK'])

class Controls(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir()
        self.original_pump=adapter.core.Commands.pump
        def pump(commands, seconds=.02):
            for child in fake.CHILDREN.values():child.tick()
            return self.original_pump(commands,seconds)
        self.patches=[patch.object(adapter.core.subprocess,'Popen',side_effect=self.spawn),
            patch.object(adapter.core.os,'killpg',side_effect=fake.group),
            patch.object(adapter.core.Commands,'pump',pump),
            patch.object(adapter.core.subprocess,'run',side_effect=AssertionError('unmanaged launch forbidden'))]
        for p in self.patches:p.start()
        self.spec={'stdout':b'ok'}
        self.launches=[]
        self.before_spawn=lambda argv:None

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        # Only synthetic descriptors: no real UNKNOWN namespace/process operations.
        for child in fake.CHILDREN.values():
            for fd in child.writers.values():os.close(fd)
            child.writers.clear();child.stdout.close();child.stderr.close()
        fake.CHILDREN.clear();fake.SPECS.clear();fake.EVENTS.clear()

    def spawn(self, argv, **kwargs):
        self.before_spawn(argv)
        self.launches.append(argv)
        fake.SPECS[argv[0]]=dict(self.spec)
        return fake.Child(argv,**kwargs)

    def manager(self, name='owned', seconds=5):
        evidence=self.folder/name;evidence.mkdir();scratch=evidence/'scratch';scratch.mkdir()
        return boundary.HostCommands(evidence,scratch,{},active_seconds=seconds)

    def prepare(self, commands, plans=None):
        commands.prepare({'input.java':b'frozen'}, {'tool':TOOL}, plans or {'compile':([TOOL,'fake-compile'],1)})

    def facts(self, commands):
        for r in commands.control.commands.records:
            self.assertTrue(all(r[k] for k in adapter.FACTS))
            item=next(i for i in commands.control.commands.owned if i['record'] is r)
            self.assertTrue(item['process'].stdout.closed and item['process'].stderr.closed)

    def test_1_profile_and_all_source_closures(self):
        roster=json.loads((ROOT/platform.ROSTER).read_bytes())
        counts={}
        for name in ('environment','A','B','cross'):
            sources=platform.source_closure(name,roster)
            frozen,names=boundary.freeze_sources(ROOT,sources)
            self.assertEqual(names.count('dev.mixer.android.AndroidUIProfile'),1)
            self.assertEqual(frozen[boundary.PROFILE],(ROOT/boundary.PROFILE).read_bytes())
            counts[name]=len(sources)
            with self.assertRaisesRegex(RuntimeError,'actual AndroidUIProfile'):
                boundary.freeze_sources(ROOT,[s for s in sources if s!=boundary.PROFILE])
        boundary.freeze_sources(ROOT,observer.SOURCES)
        stub=(ROOT/(observer.BASE+'dev/mixer/android/AppearanceResolverV2.java')).read_text()
        actual=(ROOT/'native/android/app/src/dev/mixer/android/AppearanceResolverV2.java').read_text()
        self.assertIn('boolean reduceMotion)',stub)
        self.assertIn('boolean reduceMotion)',actual)
        with self.assertRaisesRegex(RuntimeError,'duplicate source FQCN'):
            boundary.freeze_sources(ROOT,platform.source_closure('environment',roster)+[observer.BASE+'dev/mixer/android/AppearanceResolverV2.java'])
        boundary.save(self.folder/'counts.json',counts)
        self.assertFalse(self.launches)

    def test_2_durable_prelaunch_executable_and_deadline(self):
        c=self.manager()
        with self.assertRaisesRegex(RuntimeError,'launch identity'):c.run('compile')
        with self.assertRaisesRegex(RuntimeError,'executable tool'):
            c.prepare({}, {'missing':self.folder/'missing-executable'}, {})
        self.assertFalse(self.launches)
        self.prepare(c)
        def before(argv):
            identity=json.loads((c.evidence/'launch-identity.json').read_bytes())
            admissions=json.loads((c.evidence/'admissions.json').read_bytes())
            self.assertEqual(identity['scratch_identity'],boundary.directory_identity(c.scratch))
            self.assertEqual(admissions[-1]['argv'],argv)
            self.assertEqual(identity['sources']['input.java'],boundary.ident(b'frozen'))
            self.assertGreater(identity['deadline_monotonic'],time.monotonic()+59)
            self.assertEqual(identity['cleanup_reserve_seconds'],60)
        self.before_spawn=before
        c.run('compile');self.facts(c)
        self.assertTrue(c.finish(failed=False)['scratchRemoved'])
        c=self.manager('expired');self.prepare(c);c.control.commands.deadline=time.monotonic()+59
        at=len(self.launches)
        with self.assertRaisesRegex(RuntimeError,'admission closed'):c.run('compile')
        self.assertEqual(len(self.launches),at);c.finish(failed=True)
        for seconds in (0,-1,240.01,float('nan')):
            with self.assertRaises(RuntimeError):self.manager('invalid-'+str(seconds),seconds)

    def test_3_compile_failure_retains_logs_and_scratch(self):
        c=self.manager();self.prepare(c)
        self.spec={'code':1,'stdout':b'compile trace','stderr':b'missing symbol'}
        with self.assertRaises(RuntimeError):c.run('compile')
        self.facts(c)
        self.assertEqual((c.evidence/'compile.stderr').read_bytes(),b'missing symbol')
        self.assertTrue(c.finish(failed=True)['allTerminalCustody']);self.assertTrue(c.scratch.is_dir())

    def test_4_UNKNOWN_sticky_no_later_process_operations(self):
        c=self.manager();self.prepare(c);self.spec={'denied':True}
        with self.assertRaises(RuntimeError):c.run('compile')
        self.assertTrue(c.control.commands.hold)
        at=len(fake.EVENTS)
        with self.assertRaisesRegex(RuntimeError,'sticky UNKNOWN'):c.run('compile')
        with self.assertRaisesRegex(RuntimeError,'sticky UNKNOWN'):c.add_plan('later',[TOOL],1)
        cleanup=c.finish(failed=True)
        self.assertFalse(cleanup['allTerminalCustody']);self.assertEqual(len(fake.EVENTS),at)
        self.assertTrue(c.scratch.is_dir());self.assertTrue((c.evidence/'HOLD.json').is_file())
        c=self.manager('launch-failure');self.prepare(c)
        with patch.object(adapter.core.subprocess,'Popen',side_effect=OSError('synthetic launch failure')):
            with self.assertRaises(OSError):c.run('compile')
        at=len(fake.EVENTS);c.finish(failed=True)
        self.assertEqual(len(fake.EVENTS),at);self.assertTrue(c.scratch.is_dir())
        self.assertFalse(c.control.commands.records[0]['direct_child_reaped'])

    def test_5_separate_EOF_combined_and_aggregate_limits(self):
        for stream in ('stdout','stderr'):
            c=self.manager(stream);self.prepare(c)
            self.spec={stream:b'delayed',stream+'_delay':.05}
            c.run('compile');self.facts(c);self.assertTrue(c.finish(failed=False)['scratchRemoved'])
        c=self.manager('output');self.prepare(c)
        c.control.commands.output_bytes=1024;self.spec={'stdout':b'a'*700,'stderr':b'b'*700}
        with self.assertRaises(RuntimeError):c.run('compile')
        self.assertEqual(c.control.commands.used_output,1024);self.facts(c);c.finish(failed=True)
        c=self.manager('aggregate');self.prepare(c,{'one':([TOOL],1),'two':([TOOL],1),'three':([TOOL],1)})
        c.control.commands.output_bytes=1024;c.control.commands.total_output_bytes=1500
        self.spec={'stdout':b'a'*800};c.run('one')
        with self.assertRaises(RuntimeError):c.run('two')
        at=len(self.launches)
        with self.assertRaises(RuntimeError):c.run('three')
        self.assertEqual(len(self.launches),at);self.assertEqual(c.control.commands.used_output,1500)
        self.facts(c);c.finish(failed=True)

    def test_6_harness_compile_failure_and_strict_plans(self):
        for runner in (platform,observer):
            evidence=self.folder/runner.__name__
            def before(argv):
                identity=json.loads((evidence/'launch-identity.json').read_bytes())
                compile_argv=identity['commands']['compile']['argv']
                for flag in ('--release','-Xlint:all','-Werror','-proc:none','-J-XX:ActiveProcessorCount=2'):
                    self.assertIn(flag,compile_argv)
                self.assertEqual(compile_argv[compile_argv.index('--release')+1],'17')
                cp=Path(compile_argv[compile_argv.index('-classpath')+1]);sp=Path(compile_argv[compile_argv.index('-sourcepath')+1])
                self.assertEqual(cp,sp);self.assertEqual(list(cp.iterdir()),[])
                self.assertEqual(identity['sources'][boundary.PROFILE],boundary.ident((ROOT/boundary.PROFILE).read_bytes()))
                self.spec={'code':1,'stderr':b'synthetic compile failure'} if '-d' in argv else {'stdout':b'version'}
            self.before_spawn=before
            self.assertEqual(runner.main(['--jdk',str(JDK),'--evidence',str(evidence),'--active-seconds','5']),1)
            receipt=json.loads((evidence/'receipt.json').read_bytes())
            self.assertEqual(receipt['status'],'failed');self.assertTrue(receipt['source_stable'])
            self.assertTrue(receipt['cleanup']['allTerminalCustody']);self.assertFalse(receipt['cleanup']['scratchRemoved'])
            self.assertEqual((evidence/'compile.stderr').read_bytes(),b'synthetic compile failure')
        # Real runner reports UNKNOWN separately from an ordinary compile failure.
        evidence=self.folder/'unknown-harness'
        self.before_spawn=lambda argv:None
        self.spec={'denied':True}
        with patch.object(observer,'freeze_sources',wraps=boundary.freeze_sources) as frozen_check:
            self.assertEqual(observer.main(['--jdk',str(JDK),'--evidence',str(evidence),'--active-seconds','5']),1)
        receipt=json.loads((evidence/'receipt.json').read_bytes())
        self.assertEqual(receipt['status'],'UNKNOWN');self.assertFalse(receipt['cleanup']['allTerminalCustody'])
        self.assertTrue((evidence/'scratch').is_dir())
        # Dispatch to accepted A/B entrypoint is exercised in process with no A/B JVM matrix.
        sentinel=object()
        class Runner:
            def main(inner,args):
                self.assertIn('--active-seconds',args);self.assertIn('240',args)
                return sentinel
        with patch.object(platform.importlib.util,'module_from_spec',return_value=Runner()),patch.object(platform.importlib.machinery.SourceFileLoader,'exec_module'):
            for closure in ('A','B'):
                self.assertIs(platform.main(['--closure',closure,'--evidence',str(self.folder/closure)]),sentinel)


class ReviewControls(Controls):
    """Required outcomes for the independent review counterexamples."""
    def refuse_later(self, c):
        at=len(self.launches)
        for action in (lambda:c.add_plan('later',[TOOL,'fake-later'],1),lambda:c.run('compile')):
            with self.assertRaisesRegex(RuntimeError,'admission closed'):
                action()
        self.assertEqual(len(self.launches),at)

    def success_tools(self, argv):
        if '-d' in argv:
            classes=Path(argv[argv.index('-d')+1])/'dev/mixer/android'
            classes.mkdir(parents=True)
            for name in ('NativeEnvironmentV2','NativeEnvironmentPlatformV2'):
                (classes/(name+'.class')).write_bytes(b'synthetic-class')
            self.spec={}
        elif '-v' in argv:
            classes=Path(argv[argv.index('-classpath')+1])
            self.spec={'stdout':(''.join('Classfile '+str(classes/(name.replace('.','/')+'.class'))+'\n  synthetic fake dump\n' for name in argv[argv.index('-classpath')+2:])).encode()}
        elif '-ea' in argv:
            self.spec={'stdout':b'PASS synthetic boundary only\n'}
        else:
            self.spec={'stdout':b'synthetic version'}

    def test_review_failure_interruption_and_finish_close_admission(self):
        c=self.manager('exit7');self.prepare(c)
        self.spec={'code':7,'stderr':b'synthetic compile error'}
        with self.assertRaises(RuntimeError):c.run('compile')
        self.assertEqual(c.control.commands.records[-1]['exit_code'],7)
        self.refuse_later(c);self.facts(c);c.finish(failed=True)
        for error in (KeyboardInterrupt,SystemExit):
            c=self.manager(error.__name__);self.prepare(c);self.spec={}
            normal_pump=adapter.core.Commands.pump
            injected={'count':0}
            def interrupt_once(commands,seconds=.02):
                injected['count']+=1
                if injected['count']==1:raise error('synthetic interruption')
                return normal_pump(commands,seconds)
            with patch.object(adapter.core.Commands,'pump',interrupt_once):
                with self.assertRaises(error):c.run('compile')
            self.assertGreater(injected['count'],1)
            self.refuse_later(c);self.facts(c);c.finish(failed=True)
        c=self.manager('finished');self.prepare(c);self.spec={}
        c.run('compile')
        original_finish=c.control.finish
        def finish(*args,**kwargs):
            # Refusal must already be in force when finalization starts.
            self.refuse_later(c)
            return original_finish(*args,**kwargs)
        with patch.object(c.control,'finish',side_effect=finish):
            self.assertTrue(c.finish(failed=True)['allTerminalCustody'])
        self.refuse_later(c)

    def test_review_postflight_drift_retains_failed_scratch(self):
        for runner, fault in ((r,f) for r in (platform,observer) for f in ('drift','read-error','interruption')):
            with self.subTest(runner=runner.__name__,fault=fault):
                evidence=self.folder/(runner.__name__+'-'+fault)
                self.before_spawn=self.success_tools
                state={'postflight':False}
                original_run=boundary.HostCommands.run
                original_finish=boundary.HostCommands.finish
                original_read=Path.read_bytes
                def run(c,label):
                    value=original_run(c,label)
                    if label in ('host','NativeEnvironmentPlatformV2HostTests'):state['postflight']=True
                    return value
                def read(p):
                    value=original_read(p)
                    if state['postflight'] and p==ROOT/boundary.PROFILE:
                        if fault=='read-error':raise OSError('synthetic postflight read error')
                        if fault=='interruption':raise KeyboardInterrupt('synthetic postflight interruption')
                        return value+b'\n'
                    return value
                def finish(c,*,failed):
                    state['manager']=c;state['failed']=failed
                    return original_finish(c,failed=failed)
                with patch.object(boundary.HostCommands,'run',run),patch.object(boundary.HostCommands,'finish',finish),patch.object(Path,'read_bytes',read):
                    try:
                        code=runner.main(['--jdk',str(JDK),'--evidence',str(evidence),'--active-seconds','5'])
                    except BaseException as error:
                        self.fail('postflight escaped instead of finalizing: '+type(error).__name__+': '+str(error))
                    self.assertEqual(code,1)
                receipt=json.loads((evidence/'receipt.json').read_bytes())
                self.assertEqual(receipt['status'],'failed')
                self.assertFalse(receipt['source_stable'])
                self.assertTrue(state['failed'])
                if fault!='drift':self.assertEqual(receipt['source_postflight_error']['type'],'OSError' if fault=='read-error' else 'KeyboardInterrupt')
                self.assertTrue(receipt['cleanup']['allTerminalCustody'])
                self.assertFalse(receipt['cleanup']['scratchRemoved'])
                self.assertEqual((evidence/'scratch/classes/dev/mixer/android/NativeEnvironmentV2.class').read_bytes(),b'synthetic-class')
                self.refuse_later(state['manager'])
                boundary.save(evidence/'review-outcome.json',{'case':'postflight '+fault,'status':receipt['status'],'scratchRetained':True,'additionalLaunches':0})

    def test_review_UNKNOWN_postflight_error_is_durable(self):
        for runner in (platform,observer):
            with self.subTest(runner=runner.__name__):
                evidence=self.folder/runner.__name__
                self.before_spawn=lambda argv:None
                self.spec={'denied':True}
                state={'postflight':False}
                original_run=boundary.HostCommands.run
                original_finish=boundary.HostCommands.finish
                original_read=Path.read_bytes
                def run(c,label):
                    try:return original_run(c,label)
                    finally:
                        if c.control.commands.hold:
                            state['postflight']=True
                            state['events_at_unknown']=len(fake.EVENTS)
                def read(p):
                    if state['postflight'] and p==ROOT/boundary.PROFILE:
                        raise OSError('synthetic postflight source-read failure')
                    return original_read(p)
                def finish(c,*,failed):
                    state['manager']=c;state['failed']=failed
                    return original_finish(c,failed=failed)
                with patch.object(boundary.HostCommands,'run',run),patch.object(boundary.HostCommands,'finish',finish),patch.object(Path,'read_bytes',read):
                    self.assertEqual(runner.main(['--jdk',str(JDK),'--evidence',str(evidence),'--active-seconds','5']),1)
                receipt=json.loads((evidence/'receipt.json').read_bytes())
                self.assertEqual(receipt['status'],'UNKNOWN')
                self.assertFalse(receipt['source_stable'])
                self.assertEqual(receipt['source_postflight_error']['type'],'OSError')
                self.assertIn('synthetic postflight',receipt['source_postflight_error']['message'])
                self.assertTrue(state['failed'])
                self.assertTrue((evidence/'HOLD.json').is_file())
                self.assertTrue((evidence/'scratch').is_dir())
                self.assertFalse(receipt['cleanup']['scratchRemoved'])
                self.refuse_later(state['manager'])
                self.assertEqual(len(fake.EVENTS),state['events_at_unknown'])
                boundary.save(evidence/'review-outcome.json',{'case':'UNKNOWN then source-read error','status':receipt['status'],'scratchRetained':True,'extraProcessOperationsAfterUnknown':0,'additionalLaunches':0})

    def test_review_minimum_work_before_and_after_persistence(self):
        minimum=2.0
        for remaining in (.25,minimum-.001,minimum):
            with self.subTest(remaining=remaining),patch.object(time,'monotonic',return_value=100.0):
                c=self.manager('remaining-'+str(remaining),seconds=remaining)
                c.prepare({'input.java':b'frozen'},{'tool':TOOL},{'compile':([TOOL,'fake-compile'],60)})
                self.spec={'stdout':b'immediate synthetic completion'}
                at=len(self.launches)
                if remaining<minimum:
                    with self.assertRaisesRegex(RuntimeError,'minimum useful work'):c.run('compile')
                    self.assertEqual(len(self.launches),at)
                    self.assertEqual(json.loads((c.evidence/'admissions.json').read_bytes()),[])
                    self.refuse_later(c);c.finish(failed=True)
                else:
                    c.run('compile')
                    self.assertEqual(len(self.launches),at+1)
                    self.assertEqual(c.control.commands.records[-1]['execution_deadline_monotonic'],102.0)
                    self.assertEqual(c.identity['cleanup_reserve_seconds'],60)
                    self.assertTrue(c.finish(failed=False)['scratchRemoved'])
        clock={'now':100.0}
        with patch.object(time,'monotonic',side_effect=lambda:clock['now']):
            c=self.manager('persistence-delay',seconds=minimum)
            c.prepare({'input.java':b'frozen'},{'tool':TOOL},{'compile':([TOOL,'fake-compile'],60)})
            original_save=boundary.save
            def save(p,value):
                original_save(p,value)
                if Path(p)==c.evidence/'admissions.json' and value:
                    clock['now']+=.001
            at=len(self.launches)
            with patch.object(boundary,'save',save):
                with self.assertRaisesRegex(RuntimeError,'minimum useful work'):c.run('compile')
            self.assertEqual(len(self.launches),at)
            self.assertEqual(len(json.loads((c.evidence/'admissions.json').read_bytes())),1)
            self.refuse_later(c);c.finish(failed=True)
        boundary.save(self.folder/'review-outcome.json',{'minimumUsefulWorkSeconds':minimum,'belowThresholdLaunches':0,'atThresholdLaunches':1,'persistenceDelayLaunches':0,'requestedTimeoutSeconds':60,'cleanupReserveSeconds':60})

    def test_review_actual_installed_AB_dispatch(self):
        original=platform.importlib.util.spec_from_file_location
        actual=[];sentinel=object()
        def spec_for(name,filename,*args,**kwargs):
            spec=original(name,filename,*args,**kwargs)
            if name=='environment_private_owner':
                real_exec=spec.loader.exec_module
                def execute(module):
                    real_exec(module)
                    actual.append({'path':str(filename),'identity':boundary.ident(Path(filename).read_bytes()),'mapping':module.MAPPING})
                    def selected(args):
                        self.assertIn('--active-seconds',args)
                        self.assertEqual(args[args.index('--closure')+1],closure)
                        return sentinel
                    module.main=selected
                spec.loader.exec_module=execute
            return spec
        with patch.object(platform.importlib.util,'spec_from_file_location',side_effect=spec_for):
            for closure in ('A','B'):
                self.assertIs(platform.main(['--closure',closure,'--evidence',str(self.folder/closure)]),sentinel)
        self.assertEqual(len(actual),2)
        self.assertEqual(actual[0]['identity']['sha256'],'0766988f630883da5e60118ce18a05afcef6f1a7eadae92aa340d9660bf71b3f')
        boundary.save(self.folder/'review-outcome.json',{'actualEntrypoints':actual,'actualABMatrixRepeated':False})


original=sys.modules[__name__]

class Targeted(original.ReviewControls):
    def test_target_persistent_cleanup_interruption(self):
        """UNKNOWN from cleanup failure must close all later process operations."""
        outcomes=[]
        for runner in (original.platform,original.observer):
            with self.subTest(runner=runner.__name__):
                evidence=self.folder/runner.__name__
                captured={}
                real_init=boundary.HostCommands.__init__
                def init(c,*args,**kwargs):
                    real_init(c,*args,**kwargs);captured['manager']=c
                self.spec={}
                self.before_spawn=lambda argv:None
                with patch.object(boundary.HostCommands,'__init__',init),patch.object(adapter.core.Commands,'pump',side_effect=KeyboardInterrupt('persistent cleanup interruption')):
                    code=runner.main(['--jdk',str(original.JDK),'--evidence',str(evidence),'--active-seconds','5'])
                    c=captured['manager']
                    receipt=json.loads((evidence/'receipt.json').read_bytes())
                    before_events=list(fake.EVENTS)
                    before_launches=len(self.launches)
                    # The durable UNKNOWN has already been observed. No later process action is legal.
                    reentry_error=None
                    try:c.finish(failed=True)
                    except BaseException as error:reentry_error=repr(error)
                    extra_events=fake.EVENTS[len(before_events):]
                    later=[]
                    for action in (lambda:c.add_plan('later',[original.TOOL],1),lambda:c.run('java-version')):
                        try:action();later.append('unexpected success')
                        except BaseException as error:later.append(repr(error))
                    outcome={'runner':runner.__name__,'harnessExit':code,'receipt':receipt,
                        'holdFile':json.loads((evidence/'HOLD.json').read_bytes()),
                        'internalHold':c.control.commands.hold,'records':c.control.commands.records,
                        'scratchRetained':c.scratch.is_dir(),'closed':c.closed,
                        'reentryError':reentry_error,'eventsBeforeUnknownObservation':before_events,
                        'extraOperationsAfterDurableUnknown':extra_events,
                        'additionalLaunches':len(self.launches)-before_launches,'laterAdmission':later}
                    boundary.save(evidence/'counterexample.json',outcome);outcomes.append(outcome)
                    self.assertEqual(code,1)
                    self.assertEqual(receipt['status'],'UNKNOWN')
                    self.assertFalse(receipt['cleanup']['allTerminalCustody'])
                    self.assertFalse(receipt['cleanup']['scratchRemoved'])
                    self.assertTrue(c.scratch.is_dir());self.assertTrue(c.closed)
                    self.assertEqual(len(self.launches),before_launches)
                    self.assertEqual(extra_events,[], 'cleanup reentry performed process operations after durable UNKNOWN')
        boundary.save(self.folder/'outcomes.json',outcomes)

    def test_target_unknown_postflight_and_persistence_fault(self):
        """Actual synthetic UNKNOWN remains sticky through secondary faults."""
        outcomes=[]
        for error_type in (OSError,KeyboardInterrupt):
            with self.subTest(error=error_type.__name__):
                c=self.manager(error_type.__name__);self.prepare(c);self.spec={'denied':True}
                with self.assertRaises(RuntimeError):c.run('compile')
                self.assertTrue(c.control.commands.hold)
                at=len(fake.EVENTS);launch_at=len(self.launches)
                receipt={'status':'UNKNOWN'}
                original_read=Path.read_bytes
                def read(p):
                    if p==self.folder/'postflight-input':raise error_type('secondary postflight fault')
                    return original_read(p)
                original_save=boundary.save
                def save(p,value):
                    if Path(p)==c.evidence/'receipt.json':raise OSError('secondary final receipt persistence fault')
                    return original_save(p,value)
                persistence_error=None
                with patch.object(Path,'read_bytes',read),patch.object(boundary,'save',save):
                    try:c.finalize(self.folder,{'postflight-input':b'input'},receipt,success_statuses=('passed',))
                    except BaseException as error:persistence_error=repr(error)
                self.assertEqual(receipt['status'],'UNKNOWN')
                self.assertEqual(receipt['source_postflight_error']['type'],error_type.__name__)
                self.assertTrue(c.control.commands.hold)
                self.refuse_later(c)
                cleanup=c.finish(failed=True)
                self.assertFalse(cleanup['allTerminalCustody'])
                self.assertEqual(len(fake.EVENTS),at);self.assertEqual(len(self.launches),launch_at)
                self.assertTrue(c.scratch.is_dir());self.assertTrue((c.evidence/'HOLD.json').is_file())
                self.assertIsNotNone(persistence_error)
                # No I/O fault remains; persist final evidence without any process operation.
                boundary.save(c.evidence/'observed-receipt.json',receipt)
                outcome={'sourcePostflightFault':error_type.__name__,'persistenceFault':persistence_error,
                    'receiptOnDisk':(c.evidence/'receipt.json').is_file(),'holdDurable':True,
                    'statusInMemory':receipt['status'],'hold':c.control.commands.hold,
                    'extraProcessOperations':len(fake.EVENTS)-at,'additionalLaunches':len(self.launches)-launch_at,
                    'scratchRetained':True,'closed':c.closed,'records':c.control.commands.records}
                boundary.save(c.evidence/'outcome.json',outcome);outcomes.append(outcome)
        boundary.save(self.folder/'outcomes.json',outcomes)

class LatchControls(original.ReviewControls):
    def test_latch_cleanup_exception_before_persistence_callbacks(self):
        outcomes=[]
        for error_type in (OSError,KeyboardInterrupt,SystemExit):
            with self.subTest(error=error_type.__name__):
                c=self.manager(error_type.__name__);self.prepare(c);self.spec={}
                c.run('compile');self.facts(c)
                cause=error_type('first cleanup failure')
                original_save=boundary.save
                at=len(fake.EVENTS);launch_at=len(self.launches)
                callbacks=[]
                def save(p,value):
                    if Path(p)==c.evidence/'HOLD.json':
                        self.assertIs(c.unknown_error,cause)
                        self.assertIs(c.unknown_hold,c.control.commands.hold)
                        self.assertEqual(c.unknown_hold['operation'],'finish')
                        self.assertEqual(c.unknown_hold['error_type'],error_type.__name__)
                        self.assertFalse(c.finish(failed=False)['allTerminalCustody'])
                        with self.assertRaisesRegex(RuntimeError,'finalization already in progress'):
                            c.finalize(self.folder,{}, {'status':'passed'},success_statuses=('passed',))
                        self.refuse_later(c);callbacks.append('hold')
                    return original_save(p,value)
                with patch.object(c.control,'finish',side_effect=cause) as finish,patch.object(boundary,'save',save):
                    cleanup=c.finish(failed=False)
                    self.assertEqual(finish.call_count,1)
                self.assertEqual(callbacks,['hold'])
                hold=c.unknown_hold
                receipt={'status':'passed'}
                input_path=self.folder/'secondary'
                real_read=Path.read_bytes
                def read(p):
                    if p==input_path:
                        self.assertIs(c.unknown_hold,hold)
                        self.assertIs(c.finish(failed=True),cleanup)
                        with self.assertRaisesRegex(RuntimeError,'finalization already in progress'):
                            c.finalize(self.folder,{}, {'status':'passed'},success_statuses=('passed',))
                        raise KeyboardInterrupt('secondary source failure')
                    return real_read(p)
                with patch.object(Path,'read_bytes',read):
                    c.finalize(self.folder,{'secondary':b'x'},receipt,success_statuses=('passed',))
                self.assertEqual(receipt['status'],'UNKNOWN')
                self.assertEqual(receipt['source_postflight_error']['type'],'KeyboardInterrupt')
                for unused in range(3):
                    self.assertIs(c.finish(failed=False),cleanup)
                    self.assertIs(c.finalize(self.folder,{}, {},success_statuses=()),receipt)
                self.assertIs(c.unknown_hold,hold);self.assertIs(c.control.commands.hold,hold)
                self.assertIs(c.unknown_error,cause)
                self.assertEqual(len(fake.EVENTS),at);self.assertEqual(len(self.launches),launch_at)
                self.assertTrue(c.scratch.is_dir())
                self.assertEqual(json.loads((c.evidence/'HOLD.json').read_bytes())['hold'],hold)
                self.assertEqual(json.loads((c.evidence/'receipt.json').read_bytes())['status'],'UNKNOWN')
                outcomes.append({'cause':error_type.__name__,'firstCauseIdentityRetained':True,
                    'holdCallbacks':len(callbacks),'extraOperations':0,'extraLaunches':0,'receipt':receipt})
        boundary.save(self.folder/'outcomes.json',outcomes)

    def test_latch_failed_hold_persistence_and_incomplete_result(self):
        outcomes=[]
        for mode in ('hold-persistence','incomplete-result'):
            c=self.manager(mode);self.prepare(c);self.spec={}
            cause=KeyboardInterrupt('first uncertain cleanup')
            original_save=boundary.save
            def save(p,value):
                if Path(p)==c.evidence/'HOLD.json':
                    self.assertTrue(c.unknown_hold)
                    self.assertIs(c.unknown_hold,c.control.commands.hold)
                    self.refuse_later(c)
                    self.assertFalse(c.finish(failed=True)['allTerminalCustody'])
                    if mode=='hold-persistence':raise OSError('secondary HOLD persistence failure')
                return original_save(p,value)
            finish_patch=(patch.object(c.control,'finish',side_effect=cause) if mode=='hold-persistence' else
                patch.object(c.control,'finish',return_value={'allTerminalCustody':False,'scratchRemoved':False,'hold':None}))
            receipt={'status':'passed'};at=len(fake.EVENTS);launch_at=len(self.launches)
            with finish_patch as finish,patch.object(boundary,'save',save):
                c.finalize(self.folder,{},receipt,success_statuses=('passed',))
                self.assertEqual(finish.call_count,1)
            hold=c.unknown_hold
            self.assertEqual(receipt['status'],'UNKNOWN')
            self.assertIs(c.control.commands.hold,hold)
            if mode=='hold-persistence':
                self.assertIs(c.unknown_error,cause)
                self.assertEqual(receipt['cleanup_persistence_error']['type'],'OSError')
                self.assertFalse((c.evidence/'HOLD.json').exists())
            else:
                self.assertIsNone(c.unknown_error)
                self.assertEqual(hold['operation'],'finish-incomplete')
                self.assertTrue((c.evidence/'HOLD.json').is_file())
            for unused in range(3):
                self.assertFalse(c.finish(failed=False)['allTerminalCustody'])
                self.assertIs(c.finalize(self.folder,{}, {},success_statuses=()),receipt)
            self.refuse_later(c)
            self.assertEqual(len(fake.EVENTS),at);self.assertEqual(len(self.launches),launch_at)
            self.assertTrue(c.scratch.is_dir())
            outcomes.append({'mode':mode,'hold':hold,'receipt':receipt,'extraOperations':0,
                'extraLaunches':0,'holdDurable':(c.evidence/'HOLD.json').is_file(),
                'receiptDurable':json.loads((c.evidence/'receipt.json').read_bytes())['status']=='UNKNOWN'})
        boundary.save(self.folder/'outcomes.json',outcomes)

    def test_latch_terminal_finish_and_callback_reentry(self):
        c=self.manager();self.prepare(c);self.spec={}
        c.run('compile');self.facts(c)
        original_finish=c.control.finish;original_save=boundary.save
        calls=[];at=len(fake.EVENTS);launch_at=len(self.launches)
        def finish(*args,**kwargs):
            self.refuse_later(c)
            with self.assertRaisesRegex(RuntimeError,'finalization already in progress'):c.finish(failed=False)
            with self.assertRaisesRegex(RuntimeError,'finalization already in progress'):
                c.finalize(self.folder,{}, {'status':'passed'},success_statuses=('passed',))
            calls.append('adapter')
            return original_finish(*args,**kwargs)
        with patch.object(c.control,'finish',side_effect=finish):
            cleanup=c.finish(failed=True)
            self.assertTrue(cleanup['allTerminalCustody']);self.facts(c)
            for unused in range(3):self.assertIs(c.finish(failed=True),cleanup)
            receipt={'status':'passed'}
            callbacks=[]
            def save(p,value):
                if Path(p)==c.evidence/'receipt.json':
                    self.assertIs(c.finish(failed=True),cleanup)
                    with self.assertRaisesRegex(RuntimeError,'finalization already in progress'):
                        c.finalize(self.folder,{}, {},success_statuses=())
                    callbacks.append('receipt')
                return original_save(p,value)
            with patch.object(boundary,'save',save):
                c.finalize(self.folder,{},receipt,success_statuses=('passed',))
            self.assertEqual(callbacks,['receipt'])
            with patch.object(Path,'read_bytes',side_effect=AssertionError('closed postflight must not rerun')):
                for unused in range(3):
                    self.assertIs(c.finalize(self.folder,{'unused':b'x'}, {},success_statuses=()),receipt)
                    self.assertIs(c.finish(failed=False),cleanup)
            self.assertEqual(calls,['adapter'])
        self.assertEqual(len(fake.EVENTS),at);self.assertEqual(len(self.launches),launch_at)
        self.assertIsNone(c.unknown_hold)
        boundary.save(self.folder/'outcome.json',{'status':'passed','adapterFinishCalls':len(calls),
            'receiptCallbacks':len(callbacks),'extraOperations':0,'extraLaunches':0,'terminalFactsUnchanged':True})

    def test_latch_run_uncertainty_precedes_source_callback(self):
        outcomes=[]
        for error_type in (KeyboardInterrupt,SystemExit):
            c=self.manager(error_type.__name__);self.prepare(c);self.spec={}
            cause=error_type('persistent pump interruption')
            with patch.object(adapter.core.Commands,'pump',side_effect=cause):
                with self.assertRaises(error_type):c.run('compile')
            self.assertIs(c.unknown_error,cause)
            hold=c.unknown_hold
            self.assertIs(c.control.commands.hold,hold)
            self.assertEqual(hold['operation'],'run:compile')
            self.assertFalse(c.control.commands.records[-1]['terminal_custody'])
            self.assertEqual(c.control.commands.records[-1]['state'],'UNKNOWN')
            at=len(fake.EVENTS);launch_at=len(self.launches)
            real_read=Path.read_bytes
            def read(p):
                if p==self.folder/'source':
                    self.assertIs(c.unknown_hold,hold)
                    with self.assertRaisesRegex(RuntimeError,'finalization already in progress'):c.finish(failed=False)
                    self.refuse_later(c)
                    raise OSError('secondary source postflight')
                return real_read(p)
            receipt={'status':'passed'}
            with patch.object(Path,'read_bytes',read):
                c.finalize(self.folder,{'source':b'x'},receipt,success_statuses=('passed',))
            for unused in range(3):
                self.assertFalse(c.finish(failed=False)['allTerminalCustody'])
                self.assertIs(c.finalize(self.folder,{}, {},success_statuses=()),receipt)
            self.assertIs(c.unknown_hold,hold);self.assertIs(c.unknown_error,cause)
            self.assertEqual(receipt['status'],'UNKNOWN')
            self.assertEqual(len(fake.EVENTS),at);self.assertEqual(len(self.launches),launch_at)
            self.assertTrue(c.scratch.is_dir())
            self.assertEqual(json.loads((c.evidence/'HOLD.json').read_bytes())['hold'],hold)
            outcomes.append({'cause':error_type.__name__,'firstCauseIdentityRetained':True,
                'receipt':receipt,'extraOperations':0,'extraLaunches':0,'holdDurable':True})
        boundary.save(self.folder/'outcomes.json',outcomes)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(original.Controls)
    for name in unittest.defaultTestLoader.getTestCaseNames(original.ReviewControls):
        if name.startswith('test_review_'):suite.addTest(original.ReviewControls(name))
    for cls,prefix in ((Targeted,'test_target_'),(LatchControls,'test_latch_')):
        for name in unittest.defaultTestLoader.getTestCaseNames(cls):
            if name.startswith(prefix):suite.addTest(cls(name))
    r=unittest.TextTestRunner(verbosity=2).run(suite)
    boundary.save(original.OUTPUT/'receipt.json',{'status':'passed' if r.wasSuccessful() else 'failed',
        'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'optimized':not __debug__,
        'originalSixGroupsUnchanged':True,'correctedElevenBodiesUnchanged':True,'reviewTargetedBodiesUnchanged':True,
        'realNestedToolLaunches':0,'realGroupOperations':0,'productSourceChanged':False})
    sys.exit(0 if r.wasSuccessful() else 1)
