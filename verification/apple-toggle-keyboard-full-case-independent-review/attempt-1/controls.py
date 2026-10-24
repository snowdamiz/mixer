#!/usr/bin/env python3
"""Fresh bounded host controls of actual sealed composition; stdlib only."""
import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import plistlib
import shutil
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PACKET=ROOT/'verification/apple-toggle-keyboard-full-case-preparation'
SCRATCH=HERE/'scratch'
SCRATCH.mkdir(exist_ok=True)
sys.path.insert(0,str(PACKET))
executed=set();reads=set()

def audit(event,args):
    if event in ['subprocess.Popen','os.system','os.posix_spawn']:
        raise RuntimeError('Child/native process forbidden in host controls')
    if event=='exec':
        p=pathlib.Path(args[0].co_filename)
        if p.is_absolute() and p.is_relative_to(ROOT):executed.add(p)
    if event=='open' and isinstance(args[0],(str,bytes)):
        p=pathlib.Path(os.fsdecode(args[0]))
        mode=args[1];flags=args[2]
        writing=(isinstance(mode,str) and any(v in mode for v in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
        if writing and not p.resolve().is_relative_to(HERE):
            raise RuntimeError('Write outside independent review forbidden: '+str(p))
        if not writing and p.is_absolute() and p.is_relative_to(ROOT):reads.add(p)
sys.addaudithook(audit)

def write(name,data):
    (HERE/name).write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')

if sys.argv[1]=='preloaded-durable':
    # Load the unchanged historical module read-only under its ordinary import
    # name. It is outside the sealed runtime snapshot and must be refused.
    path=ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/durable_settings.py'
    spec=importlib.util.spec_from_file_location('durable_settings',path)
    outside=importlib.util.module_from_spec(spec);spec.loader.exec_module(outside)
    sys.modules['durable_settings']=outside
    import composition as c
    root=pathlib.Path(tempfile.mkdtemp(prefix='preloaded-',dir=SCRATCH));docs=root/'Documents';docs.mkdir()
    b=c.h.Bridge({'diagnostic':docs,'comparator':docs},root/'captures','synthetic-review',{'scope':'synthetic-host-only'},allowed_cases=c.oracle.CASES)
    adopted=b.persistence.__class__ is outside.TransactionStore
    write('preloaded-durable.json',dict(reproduced=adopted,compositionAccepted=True,
        adoptedSource=str(path),adoptedSourceSHA256=hashlib.sha256(path.read_bytes()).hexdigest(),
        sourceInsideSealedSnapshot=path.is_relative_to(PACKET/'inputs/runtime'),nativeExecuted=False))
    assert adopted,'Probe no longer reproduces unchecked durable import'
    raise SystemExit(0)

import composition as c
if sys.argv[1]=='imports':
    for index in range(2):c.load('independent_duplicate_'+str(index),c.KEYBOARD/'run.py')
    c.compose()
    claimed=json.loads((PACKET/'runtime-import-bindings.json').read_bytes())
    sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(executed) if p.is_file() and p.is_relative_to(PACKET)}
    data={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(reads-executed) if p.is_file() and p.is_relative_to(PACKET) and p.suffix not in ['.py','.pyc']}
    assert sources==claimed['sourceFiles'],(set(sources)^set(claimed['sourceFiles']))
    assert data==claimed['dataFiles']
    write('imports.json',dict(sources=sources,data=data,sourceFiles=len(sources),dataFiles=len(data),
        normalAndDuplicateImportClosureMatched=True,nativeExecuted=False))
    raise SystemExit(0)

# Reuse only the producer's synthetic record builder, with one disclosed path
# adaptation so its retained HTTP/persistence receipts stay in review scratch.
source=(PACKET/'fixtures.py').read_text()
assert source.count("SCRATCH=HERE/'.scratch'")==1
adapted=source.replace("SCRATCH=HERE/'.scratch'","SCRATCH=pathlib.Path("+repr(str(SCRATCH))+')')
(HERE/'fixture-adapted.py').write_text(adapted)
helper=types.ModuleType('independent_fixture');helper.__file__=str(HERE/'fixture-adapted.py')
exec(compile(adapted,helper.__file__,'exec'),helper.__dict__)
Flow=helper.Flow
from runtime_summary import official_methods,runtime_summary
import attachment_export

class Handoff(unittest.TestCase):
    def setUp(self):
        self.f=Flow();self.addCleanup(self.f.close)
    def begin(self,name='keyboard-enabled-off'):
        return self.f.http('begin',dict(candidate='diagnostic',case=name))[0]
    def test_actual_http_every_handoff_checkpoint(self):
        f=self.f
        for step in [lambda:None,f.before,f.action,lambda:f.observe('after-switch',value='1'),lambda:f.observe('terminal',value='1'),lambda:f.mark('terminate-before'),lambda:f.mark('terminate-after')]:
            step();self.assertEqual(self.begin(),400);self.assertEqual(f.bridge.generation,0)
        f.mark('test-case-finished');self.assertTrue(c.setup_ready(f.bridge.settings));self.assertEqual(self.begin(),200)
        self.assertEqual(f.bridge.settings.completions,['test-case-finished'])
        self.assertEqual(self.begin('keyboard-enabled-on'),400)
        f.bridge.current['keyboardCursor'].complete=True
        self.assertEqual(self.begin(),400)
        self.assertEqual(self.begin('keyboard-enabled-on'),200)
    def test_actual_http_wrong_generation_case_stale_and_duplicate(self):
        f=self.f;valid=f.record('mark',stage='settings-launched',detail={})
        for change in [dict(generation='other'),dict(case='other'),dict(sequence=2),dict(uptime=0)]:
            self.assertEqual(f.http('evaluate',dict(settingsDiagnostic={**valid,**change}))[0],400)
            self.assertEqual(f.bridge.settings.sequence,0)
        self.assertEqual(f.http('evaluate',dict(settingsDiagnostic=valid))[0],200)
        self.assertEqual(f.http('evaluate',dict(settingsDiagnostic=valid))[0],400)
    def test_actual_http_pending_and_29_second_limit(self):
        f=self.f;f.before();f.action();f.observe('after-switch',value='1')
        r,payloads=f.observe('terminal',value='1',upload=False)
        self.assertEqual(f.http('evaluate',dict(settingsDiagnostic=r))[0],200)
        self.assertTrue(f.bridge.settings.pending);self.assertEqual(self.begin(),400)
        sequence=f.bridge.settings.sequence;f.clock=f.bridge.settings.start_host+29.1
        self.assertEqual(f.http('evaluate',dict(settingsDiagnostic=f.record('mark',stage='terminate-before',detail={})))[0],400)
        self.assertEqual(f.bridge.settings.sequence,sequence)
    def test_actual_http_handoff_closed_to_every_write_shape(self):
        f=self.f;f.finish();self.assertEqual(self.begin(),200);sequence=f.bridge.settings.sequence
        for r in [dict(kind='start',case=c.telemetry.CASE,uptime=f.runner)]+[f.record('mark',stage=stage,detail={}) for stage in ['test-case-finished','suite-finished','bundle-finished']]+[f.record('observe'),f.record('chunk')]:
            self.assertEqual(f.http('evaluate',dict(settingsDiagnostic=r))[0],400)
            self.assertEqual(f.bridge.settings.sequence,sequence)
    def test_actual_http_pending_retirement_and_uncertainty(self):
        self.f.finish();p=self.f.bridge.persistence
        p.retirement_pending=True;self.assertEqual(self.begin(),400);p.retirement_pending=False
        p.uncertain=True;self.assertEqual(self.begin(),400)

class Process:
    def __init__(self,argv,owner,**kwargs):
        self.argv=argv;self.pid=123456;self.returncode=0;self.stdout='';self.stderr='';self.owner=owner;owner.calls.append(argv)
        if argv[1:2]==['test-without-building']:self.returncode=owner.test_exit
        if argv[1:4]==['xcresulttool','export','attachments']:
            self.returncode=owner.export_exit
            if owner.export_error:raise OSError('review injected export failure')
            out=pathlib.Path(argv[argv.index('--output-path')+1]);out.mkdir()
            (out/'manifest.json').write_text('{}')
            if owner.with_setup:(out/'setup.json').write_text(json.dumps(dict(schema='mixer.apple-toggle.keyboard-settings.1',step='setup-enabled',passed=True,bundle='com.apple.Preferences',route=c.telemetry.ROUTE,fullKeyboardAccessValue='1')))
        if argv[1:4]==['xcresulttool','get','test-results']:self.stdout=json.dumps(owner.official(argv[4]))
    def communicate(self,timeout=None):return self.stdout,self.stderr
    def poll(self):return self.returncode

class Commands(unittest.TestCase):
    def setUp(self):
        self.root=pathlib.Path(tempfile.mkdtemp(prefix='commands-',dir=SCRATCH)).resolve();self.runtime=self.root/'runtime';self.runtime.mkdir()
        self.workspace=self.root/'workspace';self.workspace.mkdir(mode=0o700);(self.workspace/'session.xcresult').mkdir();i=self.workspace.stat()
        (self.runtime/'lifecycle.json').write_text(json.dumps(dict(ephemeralWorkspace=dict(path=str(self.workspace),device=i.st_dev,inode=i.st_ino,uid=i.st_uid))))
        self.old=c.BASE;c.BASE=self.root;c.compose();self.addCleanup(self.restore)
        self.calls=[];self.test_exit=0;self.export_exit=0;self.export_error=False;self.with_setup=True
        self.patcher=mock.patch.object(c.h.subprocess,'Popen',side_effect=lambda argv,**kw:Process(argv,self,**kw));self.patcher.start();self.addCleanup(self.patcher.stop)
        self.command=c.h.Commands(self.runtime/'commands.json');self.argv=[str(c.h.DEVELOPER/'usr/bin/xcodebuild'),'test-without-building','-resultBundlePath',str(self.workspace/'session.xcresult')]
    def restore(self):c.BASE=self.old;c.compose()
    def official(self,kind):
        if kind=='summary':return dict(result='Passed',totalTestCount=7,passedTests=7,failedTests=0,skippedTests=0,expectedFailures=0)
        return dict(testNodes=[dict(nodeType='Test Case',nodeIdentifier='ToggleUITests/'+n+'()',result='Passed') for n in c.METHODS])
    def exports(self):return [a for a in self.calls if a[1:4]==['xcresulttool','export','attachments']]
    def test_duplicate_inherited_exporters_repaired_and_receipt_immutable(self):
        for i in range(2):c.load('review_legacy_'+str(i),c.KEYBOARD/'run.py')
        self.assertEqual(sum(k.__name__=='ExportingCommands' for k in c.h.Commands.__mro__),2)
        c.compose();self.command=c.h.Commands(self.runtime/'commands.json');self.command.run(self.argv)
        path=self.runtime/'attachment-export.json';first=path.read_bytes()
        self.command.export_owned_attachments(self.argv);self.command.run(self.argv)
        self.assertEqual(len(self.exports()),1);self.assertEqual(path.read_bytes(),first);self.assertTrue(json.loads(first)['passed'])
    def test_export_failure_preserves_test_exit_and_first_failure(self):
        self.test_exit=65;self.export_error=True;self.assertEqual(self.command.run(self.argv,check=False)[0],65)
        path=self.runtime/'attachment-export.json';first=path.read_bytes();self.assertFalse(json.loads(first)['passed'])
        self.export_error=False;self.command.export_owned_attachments(self.argv);self.assertEqual(path.read_bytes(),first);self.assertEqual(len(self.exports()),1)
    def test_existing_directory_not_adopted(self):
        (self.runtime/'attachments').mkdir();self.command.run(self.argv);self.assertEqual(self.exports(),[])
        self.assertFalse(json.loads((self.runtime/'attachment-export.json').read_bytes())['passed'])
    def test_receipt_fsync_failure_blocks_readable_success(self):
        real=attachment_export.publish_first_receipt
        def fail(path,data):
            with mock.patch.object(attachment_export.os,'fsync',side_effect=OSError('review receipt fsync')):return real(path,data)
        with mock.patch.object(attachment_export,'publish_first_receipt',side_effect=fail):self.command.run(self.argv)
        self.assertTrue(json.loads((self.runtime/'attachment-export.json').read_bytes())['passed'])
        self.assertFalse(c.h.attachment_export_state['receiptDurablyCommitted'])
    def test_no_setup_attachment_gets_no_setup_credit(self):
        self.with_setup=False;self.command.run(self.argv)
        self.assertFalse(json.loads((self.runtime/'attachment-export.json').read_bytes())['settingsSetupObservedPassed'])
    def test_actual_finally_cleanup_reporting_failure_reproduction(self):
        products=self.root/'build/Build/Products';products.mkdir(parents=True)
        (products/'synthetic.xctestrun').write_bytes(plistlib.dumps(dict(MixerToggleUITests=dict(EnvironmentVariables={},TestingEnvironmentVariables={}))))
        docs=self.root/'native-synthetic-container';docs.mkdir();self.test_exit=65;attempts=[]
        original_factory=c.h.tempfile.mkdtemp;real_server=c.h.server_for;servers=[];threads=[]
        def simctl(*args,**kw):
            if args[:2]==('list','runtimes'):return json.dumps(dict(runtimes=[dict(identifier=c.h.RUNTIME,isAvailable=True,buildversion=c.h.RUNTIME_BUILD)]))
            if args[0]=='create':return '11111111-2222-3333-4444-555555555555'
            if args[0]=='get_app_container':return str(docs)
            return ''
        def server(bridge):
            s=real_server(bridge);servers.append(s);old=s.shutdown
            def shutdown():attempts.append('shutdown');return old()
            s.shutdown=shutdown;return s
        original_record=c.h.Commands.record;original_thread=c.h.threading.Thread
        def record(owner,name,value):
            if name=='official-result-export-unavailable' or name=='command' and value.get('argv',[None])[1:4]==['xcresulttool','get','test-results']:
                raise OSError('review command receipt unavailable')
            return original_record(owner,name,value)
        def thread(*args,**kw):
            t=original_thread(*args,**kw);threads.append(t);return t
        failure=None
        try:
            with mock.patch.object(c.h,'verify',return_value=dict(sealSHA256='review-synthetic')),mock.patch.object(c.h.Commands,'simctl',side_effect=simctl),mock.patch.object(c.h,'devices',return_value={}),mock.patch.object(c.h,'frontends',return_value=[]),mock.patch.object(c.h,'owned_device'),mock.patch.object(c.h.packet,'restore'),mock.patch.object(c.h.packet,'verify_installed',return_value={}),mock.patch.object(c.h,'validate_container',return_value=docs),mock.patch.object(c.h.tempfile,'mkdtemp',side_effect=lambda *a,**kw:original_factory(prefix='mixer-toggle-xctest-',dir=self.root)),mock.patch.object(c.h.tempfile,'gettempdir',return_value=str(self.root)),mock.patch.object(c.h,'cleanup',side_effect=lambda *a:attempts.append('simulator')),mock.patch.object(c.h,'server_for',side_effect=server),mock.patch.object(c.h.Commands,'record',record),mock.patch.object(c.h.threading,'Thread',side_effect=thread):
                shutil.rmtree(self.runtime)
                try:c.h.run('review-synthetic','interaction')
                except BaseException as error:failure=dict(type=type(error).__name__,message=str(error))
            life=json.loads((self.runtime/'lifecycle.json').read_bytes())
            reproduced=attempts==[] and any(t.is_alive() for t in threads) and pathlib.Path(life['ephemeralWorkspace']['path']).exists()
            write('cleanup-failure-reproduction.json',dict(reproduced=reproduced,exception=failure,
                inheritedCleanupAttempts=attempts[:],loopbackThreadStillAlive=any(t.is_alive() for t in threads),
                syntheticWorkspaceStillPresent=pathlib.Path(life['ephemeralWorkspace']['path']).exists(),
                nativeBoundaries='mocked',nativeExecuted=False))
            self.assertTrue(reproduced)
        finally:
            # Reviewer owns recovery of synthetic resources even when target
            # finally was bypassed. No simulator was created.
            for s in servers:s.shutdown();s.server_close()
            for t in threads:t.join(timeout=3);self.assertFalse(t.is_alive())
            write('cleanup-recovery.json',dict(serverShutdown=True,serverClosed=True,threadsJoined=all(not t.is_alive() for t in threads),nativeInstancesTouched=False))

class Predicates(unittest.TestCase):
    def setUp(self):
        self.root=pathlib.Path(tempfile.mkdtemp(prefix='predicates-',dir=SCRATCH));(self.root/'runtime').mkdir()
        self.nodes=[dict(nodeType='Test Case',nodeIdentifier='ToggleUITests/'+n+'()',result='Passed') for n in c.METHODS]
        self.summary=dict(result='Passed',totalTestCount=7,passedTests=7,failedTests=0,skippedTests=0,expectedFailures=0)
    def official(self,nodes=None,summary=None):
        (self.root/'runtime/xctest-tests.json').write_text(json.dumps(dict(testNodes=self.nodes if nodes is None else nodes)))
        (self.root/'runtime/xctest-summary.json').write_text(json.dumps(self.summary if summary is None else summary))
    def test_seven_exact_official_methods_require_unique_passes_and_summary(self):
        self.official();self.assertTrue(official_methods(self.root,c.METHODS))
        for nodes in [self.nodes[:-1],self.nodes+[self.nodes[0]],[{**n,'result':'Skipped'} if i==0 else n for i,n in enumerate(self.nodes)],[{**n,'nodeIdentifier':'Other/'+c.METHODS[0]} if i==0 else n for i,n in enumerate(self.nodes)]]:
            self.official(nodes);self.assertFalse(official_methods(self.root,c.METHODS))
        self.official(summary={**self.summary,'skippedTests':1});self.assertFalse(official_methods(self.root,c.METHODS))
    def test_six_case_cursors_native_oracles_export_and_cleanup_conjoined(self):
        f=Flow();self.addCleanup(f.close);f.finish();self.official();b=f.bridge
        b.failures=[];b.keyboard_cases={n:types.SimpleNamespace(complete=True,failed=False) for n in c.oracle.CASES}
        b.verdicts=[dict(case=n,action='native-keyboard',passed=True) for n in c.oracle.CASES]
        path=self.root/'runtime/attachment-export.json';path.write_text(json.dumps(dict(passed=True,settingsSetupObservedPassed=True)))
        c.h.attachment_export_state=dict(receiptDurablyCommitted=True,failure=None)
        good=[dict(passed=True)]
        check=lambda:runtime_summary(self.root,c.h,c.oracle,c.setup_ready,'interaction',b,0,None,good)
        self.assertTrue(check()['runPassed']);self.assertFalse(check()['setupV9CompletionMarkersComplete'])
        for name in sorted(c.oracle.CASES):
            b.keyboard_cases[name].failed=True;self.assertFalse(check()['runPassed']);b.keyboard_cases[name].failed=False
        for v in b.verdicts:
            v['passed']=False;self.assertFalse(check()['runPassed']);v['passed']=True
        c.h.attachment_export_state['receiptDurablyCommitted']=False;self.assertFalse(check()['runPassed']);c.h.attachment_export_state['receiptDurablyCommitted']=True
        good[0]['passed']=False;self.assertFalse(check()['runPassed']);good[0]['passed']=True
        b.failures.append(dict(reason='review failure'));self.assertFalse(check()['runPassed'])

if __name__=='__main__':
    unittest.main(argv=[sys.argv[0]],verbosity=2)
