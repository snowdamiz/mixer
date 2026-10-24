"""Negative controls for selected transitive origins and actual cleanup orchestration."""
import contextlib
import copy
import hashlib
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock
import composition as c
import test_full_case as previous
from fixtures import Flow,SCRATCH

class ImportOrigins(unittest.TestCase):
    def child(self,alias,path,spoof=False):
        code='''import importlib.util,json,pathlib,sys
base=pathlib.Path(sys.argv[1]);alias=sys.argv[2];path=pathlib.Path(sys.argv[3]);spoof=sys.argv[4]=='1'
def audit(event,args):
 if event in ['subprocess.Popen','os.system','os.posix_spawn']:raise RuntimeError('Native/process boundary forbidden')
sys.addaudithook(audit)
spec=importlib.util.spec_from_file_location(alias,path);outside=importlib.util.module_from_spec(spec)
# Exact real V9 lazy module executes; other aliases need only a cache object
# with the real outside origin to prove refusal before selected imports.
if alias=='durable_settings':spec.loader.exec_module(outside)
sys.modules[alias]=outside
if spoof:
 selected=base/'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/durable_settings.py'
 outside.__file__=str(selected);outside.__spec__.origin=str(selected)
sys.path.insert(0,str(base))
spec=importlib.util.spec_from_file_location('_candidate_v2',base/'composition.py');candidate=importlib.util.module_from_spec(spec)
try:spec.loader.exec_module(candidate)
except ValueError as error:
 print(json.dumps(dict(rejected=True,alias=alias,reason=str(error),nativeExecuted=False)))
else:raise AssertionError('Outside preload accepted: '+alias)
'''
        result=subprocess.run([sys.executable,'-B','-c',code,str(c.BASE),alias,str(path),'1' if spoof else '0'],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)
    def test_exact_historical_durable_preload_rejected_before_bridge_creation(self):
        result=self.child('durable_settings',c.ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/durable_settings.py')
        self.assertTrue(result['rejected']);self.assertIn('outside selected origin',result['reason'])
    def test_every_owned_import_alias_outside_preload_rejected(self):
        selection=json.loads((c.BASE/'runtime-selection.json').read_bytes());results=[]
        for alias in selection['moduleAliases']:
            with self.subTest(alias=alias):
                results.append(self.child(alias,c.ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/durable_settings.py'))
        (c.BASE/'import-substitution-controls.json').write_text(json.dumps(results,sort_keys=True,indent=2)+'\n')
    def test_spoofed_file_and_spec_cannot_adopt_outside_transaction_store(self):
        result=self.child('durable_settings',c.ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/durable_settings.py',True)
        self.assertIn('code outside selected origin',result['reason'])
    def test_postcomposition_lazy_substitution_rejects_bridge_without_output(self):
        original=sys.modules['durable_settings'];outside=types.ModuleType('durable_settings')
        outside.__file__=str(c.ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/durable_settings.py')
        outside.__spec__=importlib.util.spec_from_file_location('durable_settings',outside.__file__)
        root=pathlib.Path(tempfile.mkdtemp(prefix='preload-',dir=SCRATCH));docs=root/'Documents';docs.mkdir()
        try:
            sys.modules['durable_settings']=outside
            with self.assertRaisesRegex(ValueError,'outside selected origin'):c.h.Bridge({'diagnostic':docs,'comparator':docs},root/'captures','synthetic',{'scope':'host-only'},allowed_cases=c.oracle.CASES)
            self.assertFalse((root/'captures').exists())
            with self.assertRaisesRegex(ValueError,'outside selected origin'):c.compose()
        finally:sys.modules['durable_settings']=original
    def test_existing_http_bridge_latches_lazy_substitution_and_refuses_new_work(self):
        flow=Flow();self.addCleanup(flow.close);original=sys.modules['durable_settings']
        outside=types.ModuleType('durable_settings');outside.__file__=str(c.ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/durable_settings.py');outside.__spec__=importlib.util.spec_from_file_location('durable_settings',outside.__file__)
        record=flow.record('mark',stage='settings-launched',detail={})
        try:
            sys.modules['durable_settings']=outside
            status,_=flow.http('evaluate',{'settingsDiagnostic':record});self.assertEqual(status,400)
            self.assertEqual(flow.bridge.settings.sequence,0);first=flow.bridge.binding_failure
        finally:sys.modules['durable_settings']=original
        self.assertEqual(flow.http('evaluate',{'settingsDiagnostic':record})[0],400)
        self.assertIs(flow.bridge.binding_failure,first);self.assertEqual(flow.bridge.settings.sequence,0)
    def test_each_selected_data_mutation_rejects_without_adopting_new_bytes(self):
        selection=json.loads((c.BASE/'runtime-selection.json').read_bytes())
        for name in [name for name in selection['files'] if name.endswith('.json')]:
            path=c.BASE/name;original=path.read_bytes()
            try:
                path.write_bytes(original+b' ')
                with self.assertRaisesRegex(ValueError,'Selected runtime source/data changed'):c.bindings.check(c.RUNTIME_ROOTS)
            finally:path.write_bytes(original)
        c.bindings.check(c.RUNTIME_ROOTS)
    def test_selected_case_data_cannot_redirect_to_same_historical_directory(self):
        module=c.oracle.original;prior=module.BASE
        try:
            module.BASE=c.ROOT/'verification/apple-toggle-keyboard-focus'
            with self.assertRaisesRegex(ValueError,'case-data origin redirected'):c.bindings.check(c.RUNTIME_ROOTS)
        finally:module.BASE=prior
        saved=copy.deepcopy(module.SPECS)
        try:
            module.SPECS['keyboard-enabled-off']['initial']=True
            with self.assertRaisesRegex(ValueError,'case-data differs'):c.bindings.check(c.RUNTIME_ROOTS)
        finally:module.SPECS.clear();module.SPECS.update(saved)

class NativeFake(previous.FakeProcess):
    def __init__(self,argv,owner,**kwargs):
        super().__init__(argv,owner,**kwargs)
        if argv[1:2]==['test-without-building']:
            pathlib.Path(argv[argv.index('-resultBundlePath')+1]).mkdir()
            owner.after_test=True
        if argv[1:2]==['simctl']:
            args=argv[2:]
            if args[:2]==['list','runtimes']:self.stdout=json.dumps({'runtimes':[dict(identifier=c.h.RUNTIME,isAvailable=True,buildversion=c.h.RUNTIME_BUILD)]})
            elif args[:2]==['list','devices']:
                owned=[] if owner.device is None else [dict(udid=owner.identifier,name=owner.device['name'],state=owner.device['state'],deviceTypeIdentifier=c.h.DEVICE_TYPE)]
                self.stdout=json.dumps({'devices':{c.h.RUNTIME:owned}})
            elif args[0]=='create':owner.device=dict(name=args[1],state='Shutdown');self.stdout=owner.identifier
            elif args[0]=='boot':owner.device['state']='Booted'
            elif args[0]=='shutdown':owner.device['state']='Shutdown'
            elif args[0]=='delete':owner.device=None
            elif args[0]=='get_app_container':self.stdout=str(owner.docs)

class ReportingCleanup(unittest.TestCase):
    restore=previous.CommandsComposition.restore
    official=previous.CommandsComposition.official
    def setUp(self):
        previous.CommandsComposition.setUp(self)
        self.popen.stop();self.popen=mock.patch.object(c.h.subprocess,'Popen',side_effect=lambda argv,**kwargs:NativeFake(argv,self,**kwargs));self.popen.start();self.addCleanup(self.popen.stop)
        self.identifier='11111111-2222-3333-4444-555555555555';self.device=None;self.after_test=False
        self.docs=self.root/'native-synthetic-container';self.docs.mkdir()
        self.servers=[];self.threads=[];self.attempts=[];self.matrix=[];self.primary=None
        self.test_exit=65
    def run_case(self,fault,cleanup_fault=None,primary=None):
        self.primary=primary;self.test_error=primary
        products=self.root/'build/Build/Products';products.mkdir(parents=True,exist_ok=True)
        (products/'synthetic.xctestrun').write_bytes(c.h.plistlib.dumps(dict(MixerToggleUITests=dict(EnvironmentVariables={},TestingEnvironmentVariables={}))))
        original_factory=c.h.tempfile.mkdtemp;real_server=c.h.server_for;original_record=c.CANONICAL_COMMANDS.record;original_write=c.h.write
        real_remove=c.h.remove_ephemeral;real_cleanup=c.h.cleanup;real_thread=c.h.threading.Thread
        def record(owner,name,value):
            argv=value.get('argv',[])
            hit=fault=='review-exact' and (name=='official-result-export-unavailable' or name=='command' and argv[1:4]==['xcresulttool','get','test-results'])
            hit=hit or fault=='all-command-receipts-after-test' and self.after_test
            hit=hit or fault=='cleanup-command-receipts' and owner.cleanup_mode
            hit=hit or fault=='cleanup-report' and name=='all-independent-cleanup-attempts'
            hit=hit or fault=='session-failure-report' and name=='session-failure'
            if hit:raise OSError('synthetic record unavailable: '+fault)
            return original_record(owner,name,value)
        def write(path,value):
            if self.after_test and (fault=='official-result-report' and path.name.startswith('xctest-') or fault=='lifecycle-final-report' and path.name=='lifecycle.json' or fault=='runtime-final-report' and path.name=='runtime-verdict.json'):
                raise OSError('synthetic file report unavailable: '+fault)
            return original_write(path,value)
        def resource(label,operation):
            def invoke(*args,**kwargs):
                self.attempts.append(label);result=operation(*args,**kwargs)
                if cleanup_fault==label:raise OSError('synthetic cleanup failure after actual '+label)
                return result
            return invoke
        def server(bridge):
            value=real_server(bridge);self.servers.append(value)
            value.shutdown=resource('shutdown',value.shutdown);value.server_close=resource('close',value.server_close)
            return value
        def thread(*args,**kwargs):
            value=real_thread(*args,**kwargs);self.threads.append(value);value.join=resource('join',value.join);return value
        def receipt(path,data):
            raise OSError('synthetic attachment receipt unavailable')
        import attachment_export
        patches=[mock.patch.object(c.h,'verify',return_value=dict(sealSHA256='synthetic-reviewed')),mock.patch.object(c.h,'frontends',return_value=[]),mock.patch.object(c.h.packet,'restore'),mock.patch.object(c.h.packet,'verify_installed',return_value={}),mock.patch.object(c.h,'validate_container',return_value=self.docs),mock.patch.object(c.h.tempfile,'mkdtemp',side_effect=lambda *a,**kw:original_factory(prefix='mixer-toggle-xctest-',dir=self.root)),mock.patch.object(c.h.tempfile,'gettempdir',return_value=str(self.root)),mock.patch.object(c.h,'server_for',side_effect=server),mock.patch.object(c.h.threading,'Thread',side_effect=thread),mock.patch.object(c.h.Commands,'record',record),mock.patch.object(c.h,'write',side_effect=write),mock.patch.object(c.h,'remove_ephemeral',side_effect=resource('workspace',real_remove)),mock.patch.object(c.h,'cleanup',side_effect=resource('simulator',real_cleanup))]
        if fault=='attachment-receipt':patches.append(mock.patch.object(attachment_export,'publish_first_receipt',side_effect=receipt))
        if fault=='attachment-export':self.export_error=True
        if fault=='result-path-stat':
            original_exists=c.h.pathlib.Path.exists
            def exists(path,*args,**kwargs):
                if self.after_test and path.name=='session.xcresult':raise OSError('synthetic optional result path stat unavailable')
                return original_exists(path,*args,**kwargs)
            patches.append(mock.patch.object(c.h.pathlib.Path,'exists',exists))
        if fault=='runtime-summary':patches.append(mock.patch.object(c.h,'runtime_summary',side_effect=OSError('synthetic summary evaluation failure')))
        error=None
        with contextlib.ExitStack() as stack:
            for patch in patches:stack.enter_context(patch)
            shutil.rmtree(self.runtime)
            try:c.h.run('synthetic-reviewed','interaction')
            except BaseException as failure:error=failure
        self.assertIsNotNone(error)
        if primary is not None:self.assertIs(error,primary)
        elif fault not in ['all-command-receipts-after-test','runtime-final-report','runtime-summary']:
            self.assertIsInstance(error,ValueError);self.assertIn('Strict XCTest result failed',str(error))
        self.assertEqual(self.attempts,['shutdown','close','join','workspace','simulator'])
        self.assertFalse(any(thread.is_alive() for thread in self.threads));self.assertTrue(all(server.fileno()==-1 for server in self.servers))
        life=c.h.last_lifecycle;self.assertFalse(pathlib.Path(life['ephemeralWorkspace']['path']).exists());self.assertIsNone(self.device)
        self.assertEqual(len(life['cleanupResults']),5)
        self.assertEqual(sum(not value['passed'] for value in life['cleanupResults']),0 if cleanup_fault is None and fault!='lifecycle-final-report' else 1)
        if c.h.last_runtime_summary is not None:self.assertFalse(c.h.last_runtime_summary['runPassed'])
        self.assertIs(c.h.last_outcome.first,error)
        result=dict(fault=fault,cleanupFault=cleanup_fault,firstFailure=dict(type=type(error).__name__,message=str(error)),cleanupAttempts=self.attempts,cleanupResults=life['cleanupResults'],threadJoined=True,serverClosed=True,workspaceAbsent=True,ownedSyntheticDeviceAbsent=True,nativeExecuted=False)
        (self.root/'negative-control.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    def test_exact_review_export_reporting_reproduction_now_cleans_all_five(self):self.run_case('review-exact')
    def test_command_receipt_failure_after_test_cleans_and_preserves_error(self):self.run_case('all-command-receipts-after-test')
    def test_attachment_export_failure_cleans_all_five(self):self.run_case('attachment-export')
    def test_attachment_receipt_failure_cleans_all_five(self):self.run_case('attachment-receipt')
    def test_official_result_report_failure_cleans_all_five(self):self.run_case('official-result-report')
    def test_cleanup_command_receipt_failure_does_not_skip_shutdown_delete_reconciliation(self):self.run_case('cleanup-command-receipts')
    def test_cleanup_report_failure_cannot_change_first_failure(self):self.run_case('cleanup-report')
    def test_session_failure_report_unavailable_preserves_primary_exception(self):self.run_case('session-failure-report',primary=KeyboardInterrupt('synthetic first native interruption'))
    def test_final_lifecycle_receipt_failure_does_not_leak(self):self.run_case('lifecycle-final-report')
    def test_final_runtime_receipt_failure_does_not_leak_or_pass(self):self.run_case('runtime-final-report')
    def test_summary_evaluation_failure_still_cleans(self):self.run_case('runtime-summary')
    def test_optional_result_path_stat_error_cannot_replace_first_failure_or_skip_cleanup(self):self.run_case('result-path-stat')
    def test_receipt_failure_preserves_exit_and_blocks_new_normal_command(self):
        process=types.SimpleNamespace(returncode=65,pid=424242,communicate=lambda **kwargs:('',''),poll=lambda:65)
        original_write=c.h.write
        error=OSError('synthetic command receipt unavailable')
        def write(path,value):
            if path==self.runtime/'commands.json':raise error
            return original_write(path,value)
        with mock.patch.object(c.h.subprocess,'Popen',return_value=process) as popen,mock.patch.object(c.h,'write',side_effect=write):
            self.assertEqual(self.command.run(['/synthetic/command'],check=False)[0],65)
            self.assertIs(self.command.reporting_error,error);self.assertEqual(popen.call_count,1)
            with self.assertRaises(OSError) as caught:self.command.run(['/synthetic/next'],check=False)
            self.assertIs(caught.exception,error);self.assertEqual(popen.call_count,1)
            self.command.cleanup_mode=True
            self.assertEqual(self.command.run(['/synthetic/cleanup'],check=False)[0],65);self.assertEqual(popen.call_count,2)
            with self.assertRaisesRegex(ValueError,'Command failed'):self.command.run(['/synthetic/cleanup-check'],check=True)
        self.assertIsNotNone(c.h.reporting_state['firstFailure'])
    def test_each_cleanup_failure_cannot_skip_later_operations(self):
        # Each case owns a new command/scratch/server/thread lifetime.
        for label in ['shutdown','close','join','workspace','simulator']:
            with self.subTest(resource=label):
                if self.attempts:
                    self.restore();self.setUp()
                self.run_case('none',cleanup_fault=label,primary=KeyboardInterrupt('synthetic sticky first failure'))

if __name__=='__main__':unittest.main(verbosity=2)
