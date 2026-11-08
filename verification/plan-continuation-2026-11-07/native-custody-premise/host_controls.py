#!/usr/bin/env python3
"""Exactly one bounded host-only control pass; invoke normally and with -O."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
PREP=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-0f4ec327/verification/plan-continuation-2026-11-07/android-motion-r2-native-runtime')
MODE='optimized' if sys.flags.optimize else 'normal'
START=time.monotonic()
import cleanup_control as c


def identity(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return {'bytes':Path(path).stat().st_size,'sha256':h.hexdigest()}


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class Controls(unittest.TestCase):
    all_records=[]
    cleanups=[]

    def setUp(self):
        self.root=Path(tempfile.mkdtemp(prefix='host-'+MODE+'-',dir=OUT))
        self.scratch=self.root/'scratch';self.scratch.mkdir()
        self.manager=c.Commands(self.root,dict(os.environ),deadline=time.monotonic()+8,cleanup_seconds=.5,output_bytes=4*c.MIB,total_output_bytes=32*c.MIB)

    def tearDown(self):
        # Only controls that started real children reach this cleanup. Fake holds are reset
        # by their test, never by a process probe or a denied OS operation.
        receipt=self.manager.cleanup(self.scratch)
        self.all_records.extend(self.manager.records)
        self.cleanups.append({'case':self.id(),'root':str(self.root),**receipt})
        self.assertTrue(receipt['allTerminalCustody'])
        self.assertTrue(receipt['scratchRemoved'])
        self.assertLess(time.monotonic()-START,45)

    def child(self,source):
        return [sys.executable,'-B','-c',source]

    def fake(self):
        class Fake:
            pid=99999991
            def poll(self):return None
        r={'label':'fake','state':'RUNNING','owned_pgid':Fake.pid,'direct_child_reaped':False,
           'stdout_eof':False,'stderr_eof':False,'owned_group_absent':False,
           'terminal_custody':False,'cleanup_errors':[],'signals':[],'group_probes':0}
        return {'record':r,'process':Fake(),'buffers':{'stdout':bytearray(),'stderr':bytearray()}}

    def test_signal_eperm_is_cached_unknown_and_no_launch(self):
        item=self.fake()
        with patch.object(c.os,'killpg',side_effect=PermissionError('synthetic EPERM')) as group, patch.object(c.subprocess,'Popen') as spawn:
            first=self.manager.stop(item)
            self.assertEqual(first['state'],'UNKNOWN')
            self.assertIs(self.manager.stop(item),first)
            with self.assertRaises(RuntimeError):self.manager.start('forbidden',[],self.root)
            restore=c.restoration(self.manager,'1',lambda:self.fail('restore command after hold'))
            self.assertEqual(restore['raw']['status'],'unavailable')
            self.assertEqual(restore['effective']['status'],'unavailable')
            self.assertEqual(group.call_count,1)
            spawn.assert_not_called()
        self.assertTrue(self.scratch.exists())
        self.manager.hold=None

    def test_observation_eperm_no_second_probe(self):
        item=self.fake()
        item['process'].poll=lambda:0
        with patch.object(c.os,'killpg',side_effect=[None,PermissionError('synthetic EPERM')]) as group:
            r=self.manager.stop(item)
            self.manager.stop(item)
            self.assertEqual(r['state'],'UNKNOWN')
            self.assertTrue(r['direct_child_reaped'])
            self.assertEqual(group.call_count,2)
        self.manager.hold=None

    def test_unknown_stops_other_cleanup_and_retains(self):
        item=self.fake();other=self.fake()
        self.manager.owned=[other,item];self.manager.records=[other['record'],item['record']]
        with patch.object(c.os,'killpg',side_effect=PermissionError('synthetic EPERM')) as group:
            result=self.manager.cleanup(self.scratch)
            self.assertFalse(result['scratchRemoved'])
            self.assertTrue(self.scratch.exists())
            self.assertEqual(group.call_count,1)
            self.assertEqual(other['record']['state'],'RUNNING')
        self.manager.hold=None;self.manager.owned=[];self.manager.records=[]

    def test_cached_terminal_cannot_be_contaminated(self):
        self.assertEqual(self.manager.run('success',self.child("print('ok')"),self.root,2),'ok')
        item=self.manager.owned[-1];before=json.dumps(item['record'],sort_keys=True)
        with patch.object(c.os,'killpg',side_effect=AssertionError('terminal group reprobe')), patch.object(item['process'],'poll',side_effect=AssertionError('terminal child repoll')):
            self.manager.stop(item);self.manager.stop(item)
        self.assertEqual(json.dumps(item['record'],sort_keys=True),before)

    def test_separate_stdout_eof_does_not_imply_stderr_or_reap(self):
        item=self.manager.start('separate-eof',self.child("import os,time;os.close(1);time.sleep(.2);os.write(2,b'err')"),self.root,long_lived=True)
        until=time.monotonic()+1
        while not item['record']['stdout_eof'] and time.monotonic()<until:self.manager.pump(.01)
        self.assertTrue(item['record']['stdout_eof'])
        self.assertFalse(item['record']['stderr_eof'])
        self.assertFalse(self.manager.reaped(item))
        self.manager.pause(.25)
        self.manager.stop(item)
        self.assertTrue(item['record']['terminal_custody'])
        self.assertEqual(item['buffers']['stderr'],b'err')

    def test_short_output_flood_combines_both_streams(self):
        self.manager.output_bytes=1024
        with self.assertRaises(RuntimeError):
            self.manager.run('flood',self.child("import os;os.write(1,b'x'*700);os.write(2,b'y'*700)"),self.root,2)
        r=self.manager.records[-1]
        self.assertEqual(r['output_bytes'],1024)
        self.assertEqual(r['stop'],'output-limit')
        self.assertTrue(r['terminal_custody'])

    def test_long_output_flood_is_bounded_while_short_runs(self):
        self.manager.output_bytes=1024
        long=self.manager.start('service-flood',self.child("import os,time;os.write(1,b'x'*2048);time.sleep(2)"),self.root,long_lived=True)
        with self.assertRaises(RuntimeError):self.manager.run('short',self.child('import time;time.sleep(.2)'),self.root,2)
        self.assertEqual(long['record']['output_bytes'],1024)
        self.assertIsNotNone(self.manager.limit)

    def test_aggregate_spans_short_and_long(self):
        self.manager.total_output_bytes=1000
        self.manager.run('one',self.child("import os;os.write(1,b'a'*400)"),self.root,2)
        self.manager.start('two',self.child("import os,time;os.write(2,b'b'*400);time.sleep(2)"),self.root,long_lived=True)
        with self.assertRaises(RuntimeError):self.manager.run('three',self.child("import os;os.write(1,b'c'*400)"),self.root,2)
        self.assertEqual(self.manager.used_output,1000)
        self.assertEqual(sum(r['output_bytes'] for r in self.manager.records),1000)
        with self.assertRaises(RuntimeError):self.manager.start('four',[],self.root)

    def test_command_deadline_and_terminal_cleanup(self):
        with self.assertRaises(RuntimeError):self.manager.run('deadline',self.child('import time;time.sleep(2)'),self.root,.05)
        self.assertEqual(self.manager.records[-1]['stop'],'timeout')
        self.assertTrue(self.manager.records[-1]['terminal_custody'])

    def test_whole_deadline_refuses_launch(self):
        self.manager.deadline=time.monotonic()+.1
        with patch.object(c.subprocess,'Popen') as spawn:
            with self.assertRaises(RuntimeError):self.manager.start('late',[],self.root)
            spawn.assert_not_called()

    def test_nonzero_retains_output_and_restoration_runs_once(self):
        code="import sys;print('INSTRUMENTATION_RESULT: motionEffectiveRestored=true');print('failure=synthetic');sys.exit(7)"
        with self.assertRaises(RuntimeError):self.manager.run('canonical-instrumentation',self.child(code),self.root,2)
        calls=[]
        report=c.restoration(self.manager,'null',lambda:calls.append('raw') or 'null')
        self.assertEqual(calls,['raw'])
        self.assertEqual(report['raw']['status'],'verified')
        self.assertEqual(report['effective']['status'],'verified')
        self.assertIn('failure=synthetic',report['failureDiagnostics']['output'])
        self.assertEqual(self.manager.records[-1]['exit_code'],7)
        self.assertEqual(len(self.manager.records),1)

    def test_restoration_reader_exception_records_unavailable(self):
        def fail():raise RuntimeError('synthetic read failure')
        r=c.restoration(self.manager,'1',fail)
        self.assertEqual(r['raw']['status'],'unavailable')
        self.assertEqual(r['effective']['status'],'unavailable')
        self.assertIn('synthetic read failure',r['raw']['reason'])

    def test_restoration_missing_before_never_commands(self):
        r=c.restoration(self.manager,None,lambda:self.fail('unexpected read'))
        self.assertEqual(r['raw']['status'],'unavailable')
        self.assertEqual(r['effective']['status'],'unavailable')

    def test_restoration_output_limit_never_commands(self):
        self.manager.limit='output-limit'
        r=c.restoration(self.manager,'1',lambda:self.fail('unexpected read'))
        self.assertEqual(r['raw']['status'],'unavailable')

    def test_timeout_preserves_diagnostics_without_instrumentation_retry(self):
        with self.assertRaises(RuntimeError):
            self.manager.run('canonical-instrumentation',self.child("import time;print('failure-before-timeout',flush=True);time.sleep(2)"),self.root,.1)
        report=c.restoration(self.manager,'1',lambda:'1')
        self.assertIn('failure-before-timeout',report['failureDiagnostics']['output'])
        self.assertEqual(report['raw']['status'],'verified')
        self.assertEqual(report['effective']['status'],'unavailable')
        self.assertEqual(len(self.manager.records),1)

    def test_finish_writes_diagnostics_before_cleanup_exception(self):
        events=[]
        def broken_cleanup(scratch):
            events.append('cleanup')
            raise OSError('synthetic cleanup failure')
        with patch.object(self.manager,'cleanup',side_effect=broken_cleanup):
            report,cleanup=c.finish(self.manager,self.scratch,'1',lambda:'1',lambda r:events.append('restoration'))
        self.assertEqual(events,['restoration','cleanup'])
        self.assertEqual(report['raw']['status'],'verified')
        self.assertFalse(cleanup['scratchRemoved'])
        self.assertTrue(self.scratch.exists())

    def test_absence_and_reap_without_eof_cannot_remove_scratch(self):
        item=self.fake();item['process'].poll=lambda:0
        self.manager.cleanup_seconds=.001
        with patch.object(c.os,'killpg',side_effect=ProcessLookupError) as group:
            r=self.manager.stop(item)
            self.manager.stop(item)
            self.assertEqual(group.call_count,1)
        self.assertTrue(r['owned_group_absent'])
        self.assertTrue(r['direct_child_reaped'])
        self.assertFalse(r['stdout_eof']);self.assertFalse(r['terminal_custody'])
        self.assertEqual(r['state'],'UNKNOWN')
        self.manager.hold=None

    def test_cleanup_exception_retains_scratch(self):
        with patch.object(c.shutil,'rmtree',side_effect=OSError('synthetic removal failure')):
            receipt=self.manager.cleanup(self.scratch)
        self.assertFalse(receipt['scratchRemoved'])
        self.assertTrue(self.scratch.exists())
        self.assertIn('cleanupError',receipt)

    def test_cleanup_reap_exception_is_terminal_unknown(self):
        item=self.fake()
        def fail():raise OSError('synthetic reap error')
        item['process'].poll=fail
        with patch.object(c.os,'killpg',return_value=None) as group:
            r=self.manager.stop(item)
            self.assertEqual(r['state'],'UNKNOWN')
            self.assertEqual(group.call_count,0)
        self.manager.hold=None

    def test_cleanup_pipe_close_exception_is_unknown(self):
        item=self.fake();item['process'].poll=lambda:0
        class Pipe:
            def close(self):raise OSError('synthetic close failure')
        item['process'].stdout=Pipe();item['process'].stderr=Pipe()
        item['record']['stdout_eof']=item['record']['stderr_eof']=True
        with patch.object(c.os,'killpg',side_effect=ProcessLookupError):
            r=self.manager.stop(item)
        self.assertEqual(r['state'],'UNKNOWN');self.assertFalse(r['terminal_custody'])
        self.manager.hold=None

    def test_historical_false_absence_failure_preserved(self):
        # Read-only replay with every OS group operation and pgrep mocked.
        source=(PREP/'cleanup_control.py.candidate').read_text()
        namespace={};exec(compile(source,'historical-cleanup','exec'),namespace)
        class Done:
            pid=99999992
            returncode=0
            def poll(self):return 0
        with patch.object(os,'killpg',side_effect=PermissionError('synthetic EPERM')), patch.object(subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','')) as probe:
            r=namespace['stop'](Done())
        self.assertTrue(r['groupAbsent'])
        self.assertGreater(probe.call_count,0)

    def test_controller_import_is_inert_and_guards_survive_optimized(self):
        with patch.object(subprocess,'Popen',side_effect=AssertionError('import launch')), patch.object(tempfile,'mkdtemp',side_effect=AssertionError('import scratch')):
            module=load('native_candidate',OUT/'run_native_probe.py')
        with self.assertRaises(RuntimeError):module.require(False,'guard')
        self.assertFalse(any(isinstance(n,ast.Assert) for n in ast.walk(ast.parse((OUT/'run_native_probe.py').read_text()))))

    def test_packet_exact_source101_sdk22_adapter24(self):
        binding=json.loads((OUT/'prepared-source-binding.json').read_text())
        checker=load('canonical',ROOT/'scripts/ci/check-android-generated-java.py')
        profile=checker.load_profile(ROOT);inputs=checker.source_inputs(profile)
        self.assertEqual(len(inputs),101)
        self.assertEqual(inputs,binding['canonicalInputs'])
        self.assertEqual(checker.source_digest(inputs),'a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca')
        for kind,count in [('sdk',22),('adapter',24)]:
            self.assertEqual(len(profile[kind+'_files']),count)
            self.assertEqual(profile[kind+'_files'],binding['projections'][kind]['files'])
        for rel,expected in binding['implementationFiles'].items():self.assertEqual(identity(ROOT/rel),expected)

    def test_reap_before_signal_avoids_zombie_only_group(self):
        item=self.fake();events=[]
        def poll():events.append('reap');return 0
        item['process'].poll=poll
        class Pipe:
            def close(self):pass
        item['process'].stdout=Pipe();item['process'].stderr=Pipe()
        item['record']['stdout_eof']=item['record']['stderr_eof']=True
        item['record']['output_bytes']=0
        self.manager.records=[item['record']];self.manager.owned=[item]
        def group(pid,sig):
            events.append('signal')
            if events[0]!='reap':raise PermissionError('synthetic zombie-only EPERM')
            raise ProcessLookupError('synthetic absence after reap')
        with patch.object(c.os,'killpg',side_effect=group):self.manager.stop(item)
        self.assertTrue(item['record']['terminal_custody'])
        self.assertEqual(events,['reap','signal'])

    def test_no_group_probe_between_signal_and_reap(self):
        item=self.fake();events=[];polls=[None,None,0]
        class Pipe:
            def close(self):pass
        item['process'].stdout=Pipe();item['process'].stderr=Pipe()
        item['record']['stdout_eof']=item['record']['stderr_eof']=True
        item['record']['output_bytes']=0
        self.manager.records=[item['record']];self.manager.owned=[item]
        def poll():
            value=polls.pop(0);events.append(('poll',value));return value
        item['process'].poll=poll
        def group(pid,sig):
            events.append(('group',sig))
            if sig==0:
                if polls:raise PermissionError('synthetic exit-in-progress EPERM')
                raise ProcessLookupError('synthetic positive absence')
        with patch.object(c.os,'killpg',side_effect=group):self.manager.stop(item)
        self.assertTrue(item['record']['terminal_custody'])
        self.assertEqual(events,[('poll',None),('group',signal.SIGKILL),('poll',None),('poll',0),('group',0)])

    def test_fake_campaign_cannot_launch_helpers(self):
        with self.assertRaises(RuntimeError):subprocess.run(['forbidden-helper'])


if __name__=='__main__':
    target=OUT/('host-controls-'+MODE+'.json')
    if target.exists():raise RuntimeError('one control pass per mode; retain existing result')
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    receipt={'status':'passed' if result.wasSuccessful() else 'failed', 'tests':result.testsRun,
             'failures':[(str(t),s) for t,s in result.failures], 'errors':[(str(t),s) for t,s in result.errors],
             'mode':MODE,'python':sys.version,'pythonExecutable':sys.executable,'hostUname':list(os.uname()),
             'entryCommand':[sys.executable,'-B',*(['-O'] if sys.flags.optimize else []),str(Path(__file__).resolve())],
             'elapsedSeconds':time.monotonic()-START,'sourceRevision':'96f03ab65966a6374e958e780fa09a3eed814c0b',
             'sourceTree':'6dacea5d2f5cd55d6934142cce556a4bd0fcd1c0',
             'controllerSHA256':identity(OUT/'run_native_probe.py')['sha256'],
             'lifecycleSHA256':identity(OUT/'cleanup_control.py')['sha256'],
             'controlsSHA256':identity(__file__)['sha256'],
             'commands':Controls.all_records,'cleanup':Controls.cleanups,
             'fakeDriverSHA256':identity(OUT/'optimized_fake_controls.py')['sha256'],
             'realProcessLaunches':0,'realGroupCalls':0,'processMode':'FAKE_ONLY_WITH_REAL_PIPES',
             'nativeAttempts':0,'physicalOrDefaultADBContact':False,'historicalGroupProbes':0,
             'scope':'FAKE ONLY: simulated lifetimes and errors, real separate pipes; no OS child, group or native calls'}
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
