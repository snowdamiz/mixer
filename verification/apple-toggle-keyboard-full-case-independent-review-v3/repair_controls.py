#!/usr/bin/env python3
"""Bounded independent V2 repair controls; all native boundaries are mocked."""
import importlib.util
import json
import pathlib
import shutil
import sys
import threading
import types
import unittest
from unittest import mock

import controls as support
c=support.c
HERE=support.HERE
SCRATCH=support.SCRATCH

class Origins(unittest.TestCase):
    def outside(self):
        module=types.ModuleType('durable_settings')
        module.__file__=str(c.ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/durable_settings.py')
        module.__spec__=importlib.util.spec_from_file_location(module.__name__,module.__file__)
        return module
    def test_postcomposition_preload_refuses_new_bridge_before_output(self):
        original=sys.modules['durable_settings'];root=pathlib.Path(support.tempfile.mkdtemp(prefix='origin-',dir=SCRATCH));docs=root/'Documents';docs.mkdir()
        before=(c.h.Commands,c.h.Bridge)
        try:
            sys.modules['durable_settings']=self.outside()
            with self.assertRaisesRegex(ValueError,'outside selected origin'):c.h.Bridge({'diagnostic':docs,'comparator':docs},root/'captures','review-synthetic',{'scope':'host-only'},allowed_cases=c.oracle.CASES)
            with self.assertRaisesRegex(ValueError,'outside selected origin'):c.compose()
            self.assertFalse((root/'captures').exists());self.assertEqual((c.h.Commands,c.h.Bridge),before)
        finally:sys.modules['durable_settings']=original
    def test_existing_http_bridge_latches_binding_failure(self):
        f=support.Flow();self.addCleanup(f.close);original=sys.modules['durable_settings']
        record=f.record('mark',stage='settings-launched',detail={})
        try:
            sys.modules['durable_settings']=self.outside()
            self.assertEqual(f.http('evaluate',dict(settingsDiagnostic=record))[0],400)
            first=f.bridge.binding_failure;self.assertIsNotNone(first)
        finally:sys.modules['durable_settings']=original
        self.assertEqual(f.http('evaluate',dict(settingsDiagnostic=record))[0],400)
        self.assertIs(f.bridge.binding_failure,first);self.assertEqual(f.bridge.settings.sequence,0)
    def test_selected_case_data_redirection_refused_without_file_mutation(self):
        target=c.oracle.original;before=target.BASE
        try:
            target.BASE=c.ROOT/'verification/apple-toggle-keyboard-focus'
            with self.assertRaisesRegex(ValueError,'case-data origin redirected'):c.bindings.check(c.RUNTIME_ROOTS)
        finally:target.BASE=before
        c.bindings.check(c.RUNTIME_ROOTS)

class NativeProcess(support.Process):
    def __init__(self,argv,owner,**kwargs):
        super().__init__(argv,owner,**kwargs)
        self.interrupted=False
        if argv[1:2]==['test-without-building']:owner.after_test=True
        if argv[1:2]!=['simctl']:return
        args=argv[2:]
        owner.native_calls.append(args)
        if args[:2]==['list','runtimes']:self.stdout=json.dumps(dict(runtimes=[dict(identifier=c.h.RUNTIME,isAvailable=True,buildversion=c.h.RUNTIME_BUILD)]))
        elif args[:2]==['list','devices']:
            rows=[dict(udid=owner.baseline,name='Other Project Preserved',state='Shutdown',deviceTypeIdentifier=c.h.DEVICE_TYPE)]
            if owner.device is not None:rows.append(dict(udid=owner.identifier,name=owner.device['name'],state=owner.device['state'],deviceTypeIdentifier=c.h.DEVICE_TYPE))
            self.stdout=json.dumps(dict(devices={c.h.RUNTIME:rows}))
        elif args[0]=='create':owner.device=dict(name=args[1],state='Shutdown');self.stdout=owner.identifier
        elif args[0]=='boot':owner.device['state']='Booted'
        elif args[0]=='shutdown':owner.device['state']='Shutdown'
        elif args[0]=='delete':owner.device=None
        elif args[0]=='get_app_container':self.stdout=str(owner.docs)
    def communicate(self,timeout=None):
        if self.argv[1:2]==['test-without-building'] and self.owner.primary is not None and not self.interrupted:
            self.interrupted=True;self.returncode=65;raise self.owner.primary
        return self.stdout,self.stderr

class Cleanup(support.Commands):
    # Select only the new repair controls, not inherited test methods already
    # run in controls.py. setUp/restore/official are reused synthetic plumbing.
    def setUp(self):
        super().setUp();self.patcher.stop()
        self.patcher=mock.patch.object(c.h.subprocess,'Popen',side_effect=lambda argv,**kw:NativeProcess(argv,self,**kw));self.patcher.start();self.addCleanup(self.patcher.stop)
        self.identifier='11111111-2222-3333-4444-555555555555';self.baseline='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        self.device=None;self.native_calls=[];self.after_test=False;self.primary=None
        self.docs=self.root/'native-synthetic-container';self.docs.mkdir()
        self.test_exit=65
    def exercise(self,fault,resource_fault=None):
        products=self.root/'build/Build/Products';products.mkdir(parents=True)
        (products/'synthetic.xctestrun').write_bytes(c.h.plistlib.dumps(dict(MixerToggleUITests=dict(EnvironmentVariables={},TestingEnvironmentVariables={}))))
        primary=KeyboardInterrupt('independent original native-command interruption');self.primary=primary
        attempts=[];servers=[];threads=[]
        native_factory=c.h.tempfile.mkdtemp;server_factory=c.h.server_for;thread_factory=c.h.threading.Thread
        real_remove=c.h.remove_ephemeral;real_cleanup=c.h.cleanup;record=c.CANONICAL_COMMANDS.record;write=c.h.write
        def guarded(label,action):
            def invoke(*a,**kw):
                attempts.append(label);result=action(*a,**kw)
                if resource_fault==label:raise OSError('independent cleanup fault after '+label)
                return result
            return invoke
        def server(bridge):
            s=server_factory(bridge);servers.append((s,s.shutdown,s.server_close))
            s.shutdown=guarded('shutdown',s.shutdown);s.server_close=guarded('close',s.server_close);return s
        def thread(*a,**kw):
            t=thread_factory(*a,**kw);threads.append((t,t.join));t.join=guarded('join',t.join);return t
        def failed_record(owner,name,value):
            if self.after_test and fault in ['report-storage','all-final-storage']:raise OSError('independent unavailable command receipt sink')
            return record(owner,name,value)
        def failed_write(path,value):
            if self.after_test and fault=='all-final-storage' and path.name in ['lifecycle.json','runtime-verdict.json','xctest-summary.json','xctest-tests.json']:
                raise OSError('independent unavailable final receipt sink')
            return write(path,value)
        patches=[mock.patch.object(c.h,'verify',return_value=dict(sealSHA256='review-synthetic')),mock.patch.object(c.h.packet,'restore'),mock.patch.object(c.h.packet,'verify_installed',return_value={}),mock.patch.object(c.h,'validate_container',return_value=self.docs),mock.patch.object(c.h.tempfile,'mkdtemp',side_effect=lambda *a,**kw:native_factory(prefix='mixer-toggle-xctest-',dir=self.root)),mock.patch.object(c.h.tempfile,'gettempdir',return_value=str(self.root)),mock.patch.object(c.h,'server_for',side_effect=server),mock.patch.object(c.h.threading,'Thread',side_effect=thread),mock.patch.object(c.h.Commands,'record',failed_record),mock.patch.object(c.h,'write',side_effect=failed_write),mock.patch.object(c.h,'remove_ephemeral',side_effect=guarded('workspace',real_remove)),mock.patch.object(c.h,'cleanup',side_effect=guarded('simulator',real_cleanup))]
        try:
            import contextlib
            with contextlib.ExitStack() as stack:
                for patch in patches:stack.enter_context(patch)
                shutil.rmtree(self.runtime)
                with self.assertRaises(KeyboardInterrupt) as caught:c.h.run('review-synthetic','interaction')
                self.assertIs(caught.exception,primary)
            self.assertEqual(attempts,['shutdown','close','join','workspace','simulator'])
            life=c.h.last_lifecycle;self.assertEqual(len(life['cleanupResults']),5)
            self.assertTrue(all(not t.is_alive() for t,_ in threads));self.assertTrue(all(s.fileno()==-1 for s,_,_ in servers))
            self.assertFalse(pathlib.Path(life['ephemeralWorkspace']['path']).exists());self.assertIsNone(self.device)
            self.assertTrue(life['ownedDeviceAbsent']);self.assertTrue(life['baselineStatesPreserved'])
            self.assertIn(['shutdown',self.identifier],self.native_calls);self.assertIn(['delete',self.identifier],self.native_calls)
            self.assertFalse(any(args[0] in ['shutdown','delete'] and self.baseline in args for args in self.native_calls))
            self.assertIs(c.h.last_outcome.first,primary)
            if c.h.last_runtime_summary is not None:self.assertFalse(c.h.last_runtime_summary['runPassed'])
            support.write('repair-cleanup-'+fault+(('-'+resource_fault) if resource_fault else '')+'.json',dict(firstExceptionObjectRetained=True,allFiveCleanupAttempted=True,
                cleanupAttempts=attempts,cleanupResults=life['cleanupResults'],ownedSyntheticDeviceAbsent=self.device is None,baselinePreserved=True,
                threadsJoined=True,serversClosed=True,workspaceAbsent=True,nativeExecuted=False))
        finally:
            for s,shutdown,close in servers:
                if any(t.is_alive() for t,_ in threads):shutdown()
                close()
            for t,join in threads:join(timeout=3);self.assertFalse(t.is_alive())
    def test_report_storage_failure_preserves_primary_and_actual_cleanup(self):self.exercise('report-storage')
    def test_all_final_storage_failure_preserves_primary_and_actual_cleanup(self):self.exercise('all-final-storage')

for label in ['shutdown','close','join','workspace','simulator']:
    def test(self,label=label):self.exercise('none',label)
    setattr(Cleanup,'test_resource_failure_'+label,test)

if __name__=='__main__':
    suite=unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Origins))
    suite.addTests(Cleanup(name) for name in dir(Cleanup) if name.startswith('test_') and ('resource_failure_' in name or name in ['test_report_storage_failure_preserves_primary_and_actual_cleanup','test_all_final_storage_failure_preserves_primary_and_actual_cleanup']))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
