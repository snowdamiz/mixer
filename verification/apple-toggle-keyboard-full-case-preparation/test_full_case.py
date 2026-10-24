"""Host controls execute the composition and real loopback endpoint; no native calls."""
import copy
import importlib.util
import json
import pathlib
import plistlib
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest import mock
import composition as c
import attachment_export
from fixtures import Flow, SCRATCH
from runtime_summary import runtime_summary, official_methods

class HTTPHandoff(unittest.TestCase):
    def setUp(self):
        self.flow=Flow();self.addCleanup(self.flow.close)
    def rejected_begin(self):
        status,result=self.flow.http('begin',{'candidate':'diagnostic','case':'keyboard-enabled-off'})
        self.assertEqual(status,400,result);self.assertEqual(self.flow.bridge.generation,0)
    def test_every_missing_handoff_checkpoint_rejects_begin(self):
        f=self.flow
        self.rejected_begin()
        f.before();self.rejected_begin()
        f.action();self.rejected_begin()
        f.observe('after-switch',value='1');self.rejected_begin()
        f.observe('terminal',value='1');self.rejected_begin()
        f.mark('terminate-before');self.rejected_begin()
        f.mark('terminate-after');self.rejected_begin()
        f.mark('test-case-finished')
        self.assertTrue(c.setup_ready(f.bridge.settings))
        status,result=f.http('begin',{'candidate':'diagnostic','case':'keyboard-enabled-off'})
        self.assertEqual(status,200,result);self.assertTrue(f.bridge.setup_handed_off)
        self.assertEqual(f.bridge.generation,1)
        for name in ['keyboard-enabled-off','keyboard-enabled-on']:
            self.assertEqual(f.http('begin',{'candidate':'diagnostic','case':name})[0],400)
            self.assertEqual(f.bridge.generation,1)
        self.assertEqual(f.bridge.settings.summary()['completionMarkers'],['test-case-finished'])
        self.assertNotEqual(f.bridge.settings.summary()['completionMarkers'],['test-case-finished','suite-finished','bundle-finished'])
    def test_pending_uploads_and_missing_terminal_refuse_begin(self):
        f=self.flow;f.before();f.action();f.observe('after-switch',value='1');f.observe('terminal',value='1',upload=False)
        self.rejected_begin()
        self.assertFalse(c.setup_ready(f.bridge.settings))
    def test_wrong_generation_duplicate_and_stale_setup_leave_cursor(self):
        f=self.flow
        valid=f.record('mark',stage='settings-launched',detail={})
        for replacement in [dict(generation='wrong-generation'),dict(sequence=0),dict(uptime=0)]:
            bad={**valid,**replacement};status,_=f.http('evaluate',{'settingsDiagnostic':bad})
            self.assertEqual(status,400);self.assertEqual(f.bridge.settings.sequence,0)
        self.assertEqual(f.http('evaluate',{'settingsDiagnostic':valid})[0],200)
        self.assertEqual(f.http('evaluate',{'settingsDiagnostic':valid})[0],400)
        self.assertEqual(f.bridge.settings.sequence,1)
    def test_all_late_setup_writes_refuse_after_handoff(self):
        f=self.flow;f.finish();self.assertEqual(f.http('begin',{'candidate':'diagnostic','case':'keyboard-enabled-off'})[0],200)
        sequence=f.bridge.settings.sequence
        for stage in ['test-case-finished','suite-finished','bundle-finished']:
            self.assertEqual(f.http('evaluate',{'settingsDiagnostic':f.record('mark',stage=stage,detail={})})[0],400)
            self.assertEqual(f.bridge.settings.sequence,sequence)
    def test_retirement_uncertainty_blocks_handoff(self):
        f=self.flow;f.finish();f.bridge.persistence.retirement_pending=True
        self.rejected_begin();f.bridge.persistence.retirement_pending=False;f.bridge.persistence.uncertain=True
        self.rejected_begin()
    def test_out_of_order_termination_and_completion_refuse(self):
        f=self.flow;f.before();f.action();f.observe('after-switch',value='1');f.observe('terminal',value='1')
        for stage in ['terminate-after','test-case-finished','suite-finished']:
            status,_=f.http('evaluate',{'settingsDiagnostic':f.record('mark',stage=stage,detail={})})
            self.assertEqual(status,400)
        self.rejected_begin()
    def test_unrecognized_case_cannot_open_handoff(self):
        f=self.flow;f.finish()
        for body in [{'candidate':'diagnostic','case':'arbitrary'},{'candidate':'comparator','case':'keyboard-enabled-off'}]:
            status,_=f.http('begin',body);self.assertEqual(status,400);self.assertFalse(f.bridge.setup_handed_off)

class FakeProcess:
    def __init__(self,argv,owner,**kwargs):
        self.argv=argv;self.owner=owner;self.returncode=0;self.pid=424242
        owner.calls.append(argv)
        if len(argv)>1 and argv[1]=='test-without-building':self.returncode=owner.test_exit
        if argv[1:4]==['xcresulttool','export','attachments']:
            if owner.export_error:raise OSError('synthetic export failure')
            self.returncode=owner.export_exit
            output=pathlib.Path(argv[argv.index('--output-path')+1]);output.mkdir()
            (output/'manifest.json').write_text('{}')
            if owner.setup_attachment:(output/'actual-setup.json').write_text(json.dumps(owner.setup_attachment))
        self.stdout='';self.stderr=''
        if argv[1:4]==['xcresulttool','get','test-results']:
            self.stdout=json.dumps(owner.official(argv[4]))
    def communicate(self,timeout=None):
        if self.argv[1:2]==['test-without-building'] and self.owner.test_error:
            self.returncode=65;raise self.owner.test_error
        return self.stdout,self.stderr
    def poll(self):return self.returncode

class CommandsComposition(unittest.TestCase):
    def setUp(self):
        self.root=pathlib.Path(tempfile.mkdtemp(prefix='commands-',dir=SCRATCH)).resolve();# Retain packet-owned synthetic evidence until verified archive cleanup.
        self.runtime=self.root/'runtime';self.runtime.mkdir();self.workspace=self.root/'workspace';self.workspace.mkdir(mode=0o700)
        (self.workspace/'session.xcresult').mkdir();info=self.workspace.stat()
        (self.runtime/'lifecycle.json').write_text(json.dumps({'ephemeralWorkspace':dict(path=str(self.workspace),device=info.st_dev,inode=info.st_ino,uid=info.st_uid)}))
        self.calls=[];self.test_exit=0;self.export_exit=0;self.test_error=None;self.export_error=False
        self.setup_attachment=dict(schema='mixer.apple-toggle.keyboard-settings.1',step='setup-enabled',passed=True,bundle='com.apple.Preferences',route=c.telemetry.ROUTE,fullKeyboardAccessValue='1')
        self.old_base=c.BASE;self.old_run=c.h.RUN_DIR
        c.BASE=self.root;c.compose();self.addCleanup(self.restore)
        self.popen=mock.patch.object(c.h.subprocess,'Popen',side_effect=lambda argv,**kwargs:FakeProcess(argv,self,**kwargs));self.popen.start();self.addCleanup(self.popen.stop)
        self.command=c.h.Commands(self.runtime/'commands.json')
        self.argv=[str(c.h.DEVELOPER/'usr/bin/xcodebuild'),'test-without-building','-resultBundlePath',str(self.workspace/'session.xcresult')]
    def restore(self):c.BASE=self.old_base;c.compose();c.h.RUN_DIR=self.old_run
    def official(self,kind):
        if kind=='summary':return dict(result='Passed',totalTestCount=7,passedTests=7,failedTests=0,skippedTests=0,expectedFailures=0)
        return {'testNodes':[dict(nodeType='Test Case',nodeIdentifier='ToggleUITests/'+name+'()',result='Passed') for name in c.METHODS]}
    def exports(self):return [argv for argv in self.calls if argv[1:4]==['xcresulttool','export','attachments']]
    def receipt(self):return json.loads((self.runtime/'attachment-export.json').read_bytes())
    def test_one_composed_export_and_success_receipt(self):
        self.assertEqual(self.command.run(self.argv,check=False)[0],0)
        self.assertEqual(len(self.exports()),1);self.assertTrue(self.receipt()['passed']);self.assertTrue(self.receipt()['settingsSetupObservedPassed'])
        self.assertTrue(official_methods(self.root,c.METHODS));self.assertTrue(c.h.attachment_export_state['receiptDurablyCommitted'])
    def test_missing_setup_attachment_cannot_receive_settings_credit(self):
        self.setup_attachment=None;self.command.run(self.argv)
        self.assertTrue(self.receipt()['passed']);self.assertFalse(self.receipt()['settingsSetupObservedPassed'])
    def test_existing_directory_is_not_adopted(self):
        (self.runtime/'attachments').mkdir();self.command.run(self.argv)
        self.assertEqual(self.exports(),[]);self.assertFalse(self.receipt()['passed'])
        self.assertIn('Fresh fixed',self.receipt()['failure']['message'])
    def test_export_error_is_recorded_without_hiding_test_exit(self):
        self.export_error=True;self.test_exit=65
        self.assertEqual(self.command.run(self.argv,check=False)[0],65)
        self.assertFalse(self.receipt()['passed']);self.assertIn('synthetic export failure',self.receipt()['failure']['message'])
    def test_test_failure_and_interrupt_still_export_once(self):
        for error in [ValueError('synthetic command failure'),KeyboardInterrupt('synthetic interrupt')]:
            self.test_error=error
            with self.assertRaises(type(error)):self.command.run(self.argv)
            self.assertEqual(len(self.exports()),1)
        self.assertTrue(self.receipt()['passed'])
    def test_first_success_receipt_is_immutable(self):
        self.command.run(self.argv);first=(self.runtime/'attachment-export.json').read_bytes()
        self.command.export_owned_attachments(self.argv)
        self.assertEqual((self.runtime/'attachment-export.json').read_bytes(),first)
        self.assertEqual(len(self.exports()),1)
        self.assertIn('Immutable export attempt already retained',json.dumps(self.command.events))
    def test_duplicate_legacy_loading_is_repaired_at_actual_composition_boundary(self):
        # Execute the exact frozen legacy module twice: the historical source
        # does stack two exporting wrappers. Only snapshot modules are touched.
        for index in range(2):c.load('legacy_duplicate_'+str(index),c.KEYBOARD/'run.py')
        self.assertEqual(sum(cls.__name__=='ExportingCommands' for cls in c.h.Commands.__mro__),2)
        c.compose();self.command=c.h.Commands(self.runtime/'commands.json')
        self.assertEqual(sum(getattr(cls,'_full_case_export_owner',False) for cls in c.h.Commands.__mro__),1)
        self.assertFalse(any(cls.__name__=='ExportingCommands' for cls in c.h.Commands.__mro__))
        self.command.run(self.argv);self.assertEqual(len(self.exports()),1);self.assertTrue(self.receipt()['passed'])
    def test_receipt_write_failure_still_allows_independent_cleanup(self):
        (self.runtime/'attachment-export.json').mkdir()
        self.command.run(self.argv)
        self.assertIn('attachment-export-receipt-unavailable',json.dumps(self.command.events))
        attempts=[]
        def fail():attempts.append('server');raise OSError('synthetic cleanup failure')
        results=c.h.cleanup_independently([('server',fail),('thread',lambda:attempts.append('thread')),('workspace',lambda:attempts.append('workspace')),('simulator',lambda:attempts.append('simulator'))])
        self.assertEqual(attempts,['server','thread','workspace','simulator']);self.assertFalse(results[0]['passed']);self.assertTrue(all(row['passed'] for row in results[1:]))

    def test_receipt_fsync_failure_cannot_qualify_readable_success_bytes(self):
        original=attachment_export.publish_first_receipt
        def failed_sync(path,data):
            # Fault the actual persistence helper after its real file write.
            with mock.patch.object(attachment_export.os,'fsync',side_effect=OSError('synthetic receipt fsync failure')):
                return original(path,data)
        with mock.patch.object(attachment_export,'publish_first_receipt',side_effect=failed_sync):
            self.command.run(self.argv)
        self.assertTrue(self.receipt()['passed'])
        self.assertFalse(c.h.attachment_export_state['receiptDurablyCommitted'])
        self.assertIn('synthetic receipt fsync failure',c.h.attachment_export_state['failure']['message'])
    def test_actual_harness_run_failure_attempts_all_five_cleanup_operations(self):
        products=self.root/'build/Build/Products';products.mkdir(parents=True)
        (products/'synthetic.xctestrun').write_bytes(plistlib.dumps({'MixerToggleUITests':{'EnvironmentVariables':{},'TestingEnvironmentVariables':{}}}))
        self.test_exit=65
        attempts=[]
        original_factory=c.h.tempfile.mkdtemp
        def owned_temp(*args,**kwargs):
            return original_factory(prefix='mixer-toggle-xctest-',dir=self.root)
        def simctl(*args,**kwargs):
            if args[:2]==('list','runtimes'):
                return json.dumps({'runtimes':[{'identifier':c.h.RUNTIME,'isAvailable':True,'buildversion':c.h.RUNTIME_BUILD}]})
            if args[0]=='create':return '11111111-2222-3333-4444-555555555555'
            if args[0]=='get_app_container':return str(self.root/'native-synthetic-container')
            return ''
        docs=self.root/'native-synthetic-container';docs.mkdir()
        original_remove=c.h.remove_ephemeral
        def remove(life):attempts.append('workspace');return original_remove(life)
        original_server=c.h.server_for
        def server(bridge):
            value=original_server(bridge)
            shutdown=value.shutdown;close=value.server_close
            def shut():attempts.append('shutdown');return shutdown()
            def closed():attempts.append('close');return close()
            value.shutdown=shut;value.server_close=closed;return value
        # All process and native boundaries are synthetic. The actual harness
        # orchestration/finally and real loopback thread cleanup execute.
        with mock.patch.object(c.h,'verify',return_value={'sealSHA256':'synthetic-reviewed'}),mock.patch.object(c.h.Commands,'simctl',side_effect=simctl),mock.patch.object(c.h,'devices',return_value={}),mock.patch.object(c.h,'frontends',return_value=[]),mock.patch.object(c.h,'owned_device'),mock.patch.object(c.h.packet,'restore'),mock.patch.object(c.h.packet,'verify_installed',return_value={}),mock.patch.object(c.h,'validate_container',return_value=docs),mock.patch.object(c.h.tempfile,'mkdtemp',side_effect=owned_temp),mock.patch.object(c.h.tempfile,'gettempdir',return_value=str(self.root)),mock.patch.object(c.h,'remove_ephemeral',side_effect=remove),mock.patch.object(c.h,'cleanup',side_effect=lambda *args:attempts.append('simulator')),mock.patch.object(c.h,'server_for',side_effect=server):
            # h.run owns its runtime directory; replace our command fixture root.
            shutil.rmtree(self.runtime)
            with self.assertRaisesRegex(ValueError,'Strict XCTest result failed'):
                c.h.run('synthetic-reviewed','interaction')
        life=json.loads((self.runtime/'lifecycle.json').read_bytes())
        self.assertEqual(len(life['cleanupResults']),5)
        self.assertTrue(all(row['passed'] for row in life['cleanupResults']))
        self.assertEqual(attempts,['shutdown','close','workspace','simulator'])
        self.assertFalse(pathlib.Path(life['ephemeralWorkspace']['path']).exists())
        self.assertTrue(life['cleanedUp'])

class QualificationPredicates(unittest.TestCase):
    def setUp(self):
        self.root=pathlib.Path(tempfile.mkdtemp(prefix='verdict-',dir=SCRATCH));# Retain packet-owned synthetic evidence until verified archive cleanup.
        (self.root/'runtime').mkdir()
    def install_official(self):
        (self.root/'runtime/xctest-summary.json').write_text(json.dumps(dict(result='Passed',totalTestCount=7,passedTests=7,failedTests=0,skippedTests=0,expectedFailures=0)))
        nodes=[dict(nodeType='Test Case',nodeIdentifier='ToggleUITests/'+name+'()',result='Passed') for name in c.METHODS]
        (self.root/'runtime/xctest-tests.json').write_text(json.dumps(dict(testNodes=nodes)))
        return nodes
    def test_requires_all_seven_official_methods_no_skips_duplicates_or_extra(self):
        self.assertFalse(official_methods(self.root,c.METHODS));nodes=self.install_official();self.assertTrue(official_methods(self.root,c.METHODS))
        for altered in [nodes[:-1],nodes+[nodes[0]],[{**n,'result':'Skipped'} if i==1 else n for i,n in enumerate(nodes)]]:
            (self.root/'runtime/xctest-tests.json').write_text(json.dumps(dict(testNodes=altered)));self.assertFalse(official_methods(self.root,c.METHODS))
    def test_seven_official_passes_do_not_replace_six_case_oracles(self):
        self.install_official();summary=runtime_summary(self.root,c.h,c.oracle,c.setup_ready,'interaction',None,0,None,[dict(passed=True)])
        self.assertTrue(summary['officialSevenMethodsPassed']);self.assertFalse(summary['strictNativeVerdictsPassed']);self.assertFalse(summary['runPassed']);self.assertEqual(len(summary['dependentCasesUnrun']),6)
    def test_full_predicate_requires_setup_export_each_case_and_cleanup(self):
        flow=Flow();self.addCleanup(flow.close);flow.finish();self.install_official()
        bridge=flow.bridge
        bridge.keyboard_cases={name:types.SimpleNamespace(complete=True,failed=False) for name in c.oracle.CASES}
        bridge.verdicts=[dict(case=name,action='native-keyboard',passed=True) for name in c.oracle.CASES]
        (self.root/'runtime/attachment-export.json').write_text(json.dumps(dict(passed=True,settingsSetupObservedPassed=True)))
        def summary():return runtime_summary(self.root,c.h,c.oracle,c.setup_ready,'interaction',bridge,0,None,[dict(passed=True)])
        c.h.attachment_export_state=dict(receiptDurablyCommitted=True,failure=None)
        self.assertTrue(summary()['runPassed'])
        c.h.attachment_export_state['receiptDurablyCommitted']=False;self.assertFalse(summary()['runPassed'])
        c.h.attachment_export_state['receiptDurablyCommitted']=True
        saved=bridge.verdicts[:]
        bridge.verdicts=bridge.verdicts[:-1];self.assertFalse(summary()['strictNativeVerdictsPassed'])
        bridge.verdicts=saved;bridge.verdicts[0]['passed']=False;self.assertFalse(summary()['strictNativeVerdictsPassed'])
        bridge.verdicts[0]['passed']=True
        (self.root/'runtime/attachment-export.json').write_text(json.dumps(dict(passed=True,settingsSetupObservedPassed=False)))
        self.assertFalse(summary()['strictNativeVerdictsPassed'])
        (self.root/'runtime/attachment-export.json').write_text(json.dumps(dict(passed=True,settingsSetupObservedPassed=True)))
        bridge.settings.completions=[];self.assertFalse(summary()['strictNativeVerdictsPassed'])
        bridge.settings.completions=['test-case-finished']
        self.assertFalse(runtime_summary(self.root,c.h,c.oracle,c.setup_ready,'interaction',bridge,0,None,[dict(passed=False)])['runPassed'])
    def test_original_application_helpers_and_methods_exact(self):
        original=(c.ROOT/'verification/apple-toggle-keyboard-focus/harness/UITests/ToggleUITests.swift').read_text()
        new=c.BASE/'harness/UITests/ToggleUITests.swift'
        prepared=new.read_text()
        block=original[original.index('    private func launchCase('):original.rfind('\n}')]
        self.assertIn(block,prepared)
        bridge=original[original.index('    private func bridge('):original.index('    private func settingsObservation(')]
        self.assertIn(bridge,prepared)
        self.assertEqual(prepared.count('    func test0'),7)
    def test_preloaded_legacy_module_is_refused_before_any_mutation(self):
        code="""import sys,types
from pathlib import Path
base=Path(sys.argv[1]);sys.path.insert(0,str(base))
legacy=types.ModuleType('harness');legacy.__file__=str(base.parents[1]/'verification/apple-toggle-pan-origin-correction/harness.py')
sys.modules['harness']=legacy
before=dict(legacy.__dict__)
try:import composition
except ValueError as error:
 assert 'outside isolated packet' in str(error)
else:raise AssertionError('Preloaded old harness was accepted')
assert legacy.__dict__==before
"""
        result=subprocess.run([__import__('sys').executable,'-B','-c',code,str(c.BASE)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_readonly_verify_never_imports_composition_or_launches_process(self):
        source=(c.BASE/'run.py').read_text()
        self.assertNotIn('import composition',source)
        # Execute the real read-only entrypoint with every process creation and
        # legacy/snapshot import denied by an audit hook in the host child.
        code="""import runpy,sys
from pathlib import Path
base=Path(sys.argv[1])
def audit(event,args):
 if event in ['subprocess.Popen','os.system']:raise RuntimeError('Native/process operation forbidden')
 if event=='open' and any(token in str(args[0]) for token in ['/composition.py','/inputs/runtime/']):raise RuntimeError('Runtime import forbidden')
sys.addaudithook(audit)
sys.argv=[str(base/'run.py'),'verify','--unsealed-host-check']
runpy.run_path(str(base/'run.py'),run_name='__main__')
"""
        result=subprocess.run([__import__('sys').executable,'-B','-c',code,str(c.BASE)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertFalse(json.loads(result.stdout)['nativeInstancesQueried'])

if __name__=='__main__':unittest.main(verbosity=2)
