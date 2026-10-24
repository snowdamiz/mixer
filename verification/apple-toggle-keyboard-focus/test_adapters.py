"""Host integration controls for closed witnesses and fixed result-artifact export."""
import copy
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock
import keyboard_oracle as o
import run
from test_keyboard import fixture

class WitnessBridgeControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name).resolve()
        self.docs=self.root/'Documents';self.docs.mkdir();self.case,self.before,self.after=fixture();self.path=self.docs/'observations.json'
        self.store({k:v for k,v in self.before.items() if k not in {'keyboardWitness','keyboardBinding'}})
        self.bridge=run.inherited.Bridge({'diagnostic':self.docs,'comparator':self.docs},self.root/'captures','host-capability',{'scope':'host-only'},allowed_cases={self.case})
        self.cursor=o.Cursor(self.case)
        for command in o.CASE_COMMAND_SEQUENCE[self.case]:self.cursor.command(command)
        self.cursor.acquired=True
        self.bridge.generation=1;self.bridge.current={'case':self.case,'candidate':'diagnostic','ready':True,'nativeIdentity':self.before['state']['identity'],'commandGeneration':len(self.cursor.done_commands),'actionIndex':0,'keyboardCursor':self.cursor}
        self.bridge.keyboard_cases[self.case]=self.cursor
    def store(self,value):
        temp=self.docs/'next.json';temp.write_text(json.dumps(value));temp.replace(self.path)
    def baseline(self):
        with mock.patch.object(run.keyboard_bridge.time,'monotonic',return_value=100.5):
            return self.bridge.request('baseline',{'action':'native-keyboard','geometry':{'app':dict(x=0,y=0,width=402,height=874),'target':dict(x=303,y=244,width=63,height=44)}})
    def test_witness_persists_before_evaluation_and_replays_against_exact_capture(self):
        acknowledged=self.baseline();self.assertEqual(acknowledged['actionIndex'],1);self.store(self.after)
        w=self.before['keyboardWitness']
        original=run.transport.verdict
        def checking(*args,**kwargs):
            self.assertTrue((self.root/'captures/0001-keyboard-witness-1.json').is_file());return original(*args,**kwargs)
        with mock.patch.object(run.transport,'verdict',side_effect=checking),mock.patch.object(run.keyboard_bridge.time,'monotonic',return_value=103),mock.patch.object(run.transport.time,'sleep',return_value=None):
            result=self.bridge.request('evaluate',{'keyboardWitness':w})
        self.assertTrue(result['passed'],result);self.assertEqual(result['keyboardWitness'],w)
        before=json.loads((self.root/'captures/0001-before-1.json').read_bytes());after=json.loads((self.root/'captures/0001-after-1.json').read_bytes());bound=json.loads((self.root/'captures/0001-keyboard-witness-1.json').read_bytes())
        self.assertNotIn('keyboardWitness',before['observation'])
        exact=before['observation'];exact.update(keyboardWitness=bound['witness'],keyboardBinding=bound['binding'])
        replay=o.verdict('diagnostic',self.case,'native-keyboard',exact,after['observation'])
        self.assertEqual(replay['predicates'],result['predicates']);self.assertEqual(self.cursor.phase_index,1)
        with self.assertRaises(ValueError):self.bridge.request('evaluate',{'keyboardWitness':w})
    def test_missing_witness_fails_without_qualifying_direct_callback(self):
        self.baseline();self.store(self.after)
        with mock.patch.object(run.transport.time,'sleep',return_value=None):result=self.bridge.request('evaluate',{})
        self.assertFalse(result['passed']);self.assertTrue(self.cursor.failed)
    def test_wrong_case_generation_action_and_phase_cannot_reach_oracle(self):
        self.baseline()
        for field,value in [('case','keyboard-enabled-on'),('generation',2),('actionIndex',2),('phase','space-reverse')]:
            w=copy.deepcopy(self.before['keyboardWitness']);w[field]=value
            with mock.patch.object(run.keyboard_bridge.time,'monotonic',return_value=103),mock.patch.object(run.transport,'verdict') as verdict,self.assertRaises(ValueError):self.bridge.request('evaluate',{'keyboardWitness':w})
            verdict.assert_not_called()
        self.assertFalse((self.root/'captures/0001-keyboard-witness-1.json').exists())
    def test_no_added_endpoint_or_arbitrary_fixture_command_authority(self):
        for operation,body in [('keyboard',{}),('command',{'command':'focus'}),('command',{'command':'self-tests'}),('command',{'command':'disable'}),('command',{'command':'/tmp/path'})]:
            with self.assertRaises(ValueError):self.bridge.request(operation,body)
        self.assertEqual(o.COMMANDS,{'resume','reset','set-on','stale','disable'})
        self.assertIs(run.inherited.Bridge.request,run.transport.Bridge.request)
        self.assertIs(run.inherited.Bridge.write_command,run.transport.Bridge.write_command)

class AttachmentExportControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name).resolve()
        self.base=self.root/'packet';self.runtime=self.base/'runtime';self.runtime.mkdir(parents=True)
        self.workspace=self.root/'owned';self.workspace.mkdir(mode=0o700);self.result=self.workspace/'session.xcresult';self.result.mkdir()
        info=self.workspace.stat();life={'ephemeralWorkspace':{'path':str(self.workspace),'device':info.st_dev,'inode':info.st_ino,'uid':info.st_uid}}
        (self.runtime/'lifecycle.json').write_text(json.dumps(life));self.command=run.ExportingCommands(self.runtime/'commands.json')
        self.argv=[str(run.inherited.DEVELOPER/'usr/bin/xcodebuild'),'test-without-building','-resultBundlePath',str(self.result)]
        self.patches=[mock.patch.object(run,'BASE',self.base),mock.patch.object(run.inherited,'RUN_DIR',self.runtime)]
        for patch in self.patches:patch.start();self.addCleanup(patch.stop)
    def exported(self):
        out=self.runtime/'attachments';out.mkdir()
        (out/'manifest.json').write_text('[]')
        (out/'setup.json').write_text(json.dumps({'schema':'mixer.apple-toggle.keyboard-settings.1','step':'setup-enabled','passed':True,'bundle':'com.apple.Preferences','route':['Accessibility','Keyboards & Typing','Full Keyboard Access'],'fullKeyboardAccessValue':'1'}))
    def test_fixed_bounded_export_and_artifact_inventory(self):
        def tool(argv,**kwargs):
            if argv[0]=='/usr/bin/xcrun':
                self.assertEqual(argv,['/usr/bin/xcrun','xcresulttool','export','attachments','--path',str(self.result),'--output-path',str(self.runtime/'attachments')]);self.assertEqual(kwargs,{'timeout':30,'check':False});self.exported()
            return 0,'',''
        with mock.patch.object(run.BaseCommands,'run',side_effect=tool):self.command.run(self.argv,timeout=600,check=False)
        receipt=json.loads((self.runtime/'attachment-export.json').read_bytes());self.assertTrue(receipt['passed']);self.assertTrue(receipt['settingsSetupObservedPassed']);self.assertEqual(len(receipt['files']),2)
    def test_export_attempt_runs_after_test_timeout_and_preserves_exception(self):
        def tool(argv,**kwargs):
            if argv[0]!=' /usr/bin/xcrun'.strip():raise TimeoutError('host-only-test-timeout')
            self.exported();return 0,'',''
        with mock.patch.object(run.BaseCommands,'run',side_effect=tool),self.assertRaisesRegex(TimeoutError,'host-only-test-timeout'):self.command.run(self.argv,timeout=600,check=False)
        self.assertTrue(json.loads((self.runtime/'attachment-export.json').read_bytes())['passed'])
    def test_export_failure_never_suppresses_original_result_or_cleanup(self):
        def tool(argv,**kwargs):
            if argv[0]=='/usr/bin/xcrun':raise RuntimeError('host-only-export-failure')
            return 65,'failed',''
        with mock.patch.object(run.BaseCommands,'run',side_effect=tool):self.assertEqual(self.command.run(self.argv,check=False)[0],65)
        self.assertFalse(json.loads((self.runtime/'attachment-export.json').read_bytes())['passed'])
        self.assertEqual(pathlib.Path(run.inherited.cleanup.__code__.co_filename),run.PARENT/'harness.py')
    def test_nonowned_result_or_workspace_identity_never_invokes_export(self):
        life=json.loads((self.runtime/'lifecycle.json').read_bytes());life['ephemeralWorkspace']['inode']+=1;(self.runtime/'lifecycle.json').write_text(json.dumps(life))
        with mock.patch.object(run.BaseCommands,'run',return_value=(0,'','')) as tool:self.command.run(self.argv,check=False)
        self.assertEqual(tool.call_count,1);self.assertFalse(json.loads((self.runtime/'attachment-export.json').read_bytes())['passed'])
    def test_missing_result_after_exception_is_recorded_as_unqualified(self):
        self.result.rmdir()
        with mock.patch.object(run.BaseCommands,'run',side_effect=TimeoutError('host-only')),self.assertRaises(TimeoutError):self.command.run(self.argv,check=False)
        self.assertFalse(json.loads((self.runtime/'attachment-export.json').read_bytes())['passed'])
    def test_setup_failure_or_missing_export_leaves_all_cases_unrun(self):
        class Bridge:
            verdicts=[];failures=[];keyboard_cases={}
        summary=run.summary('interaction',Bridge(),65,{'type':'setup-failed'},[{'passed':True}])
        self.assertFalse(summary['requiredEvidenceAvailable']);self.assertFalse(summary['runPassed']);self.assertEqual(set(summary['dependentCasesUnrun']),o.CASES)
    def test_redirected_export_inventory_is_rejected(self):
        def tool(argv,**kwargs):
            if argv[0]=='/usr/bin/xcrun':
                self.exported();(self.runtime/'attachments/redirect').symlink_to(self.runtime/'lifecycle.json')
            return 0,'',''
        with mock.patch.object(run.BaseCommands,'run',side_effect=tool):self.command.run(self.argv,check=False)
        self.assertFalse(json.loads((self.runtime/'attachment-export.json').read_bytes())['passed'])

if __name__=='__main__':unittest.main()
