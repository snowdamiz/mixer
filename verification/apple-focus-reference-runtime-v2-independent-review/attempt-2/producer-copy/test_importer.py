"""Host-only adversarial tests; fake tools and synthetic data grant no native credit."""
import copy
import datetime
import importlib.util
from pathlib import Path
import tempfile
import sys
import subprocess
import types
import os
import stat
import unittest
from unittest import mock

import prepare
import importer as i


class RuntimeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.accepted, cls.products, cls.bindings = prepare.inputs()
        cls.derived, cls.template = prepare.derive(cls.runtime)
        cls.temp = tempfile.TemporaryDirectory(prefix='pure-oracle-',dir=prepare.BASE)
        cls.pure = Path(cls.temp.name)
        for relative in prepare.ORACLES:
            name = 'inputs/runtime/verification/'+relative
            path = cls.pure/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(cls.runtime[name])
        path=cls.pure/'inputs/runtime/verification'/prepare.ORACLES[0]
        spec=importlib.util.spec_from_file_location('_runtime_v2_pure_original_oracle',path)
        cls.oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.oracle)
        spec=importlib.util.spec_from_file_location('_runtime_v2_frozen_classifier',prepare.V2/'reference_contract.py')
        cls.classifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.classifier)
        cls.old_before=i.read(prepare.OLD/'runtime/captures/0001-before-1.json')
        cls.old_after=i.read(prepare.OLD/'runtime/captures/0001-after-1.json')
        cls.old_witness=i.read(prepare.OLD/'runtime/captures/0001-keyboard-witness-1.json')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def fixture(self, destination='next-focus', premise=True, missing=False):
        root={'schema':'mixer.apple-focus-reference-root-selection.1','runID':'11111111-1111-4111-8111-111111111111','packetSHA256':'a'*64,'selectedAtUTC':'2026-10-25T02:00:00+00:00','ownedSimulatorIdentity':{'udid':'22222222-2222-4222-8222-222222222222','name':'MixerFocusReferenceV2-host-synthetic','runtime':'com.apple.CoreSimulator.SimRuntime.iOS-26-5','build':'23F77'},'sourceTreeSHA256':i.SOURCE,'productArchiveSHA256':i.PRODUCT,'developerDirectory':'/Applications/Xcode_26.6.app/Contents/Developer','baselineDevices':{'devices':{}},'baselineFrontends':[]}
        start=datetime.datetime.fromisoformat(root['selectedAtUTC']).timestamp()
        device={'architecture':'arm64','deviceId':root['ownedSimulatorIdentity']['udid'],'deviceName':root['ownedSimulatorIdentity']['name'],'osBuildNumber':'23F77','osVersion':'26.5','platform':'iOS Simulator','modelName':'iPhone 17 Pro'}
        summary={'devicesAndConfigurations':[{'device':device,'passedTests':2,'failedTests':0,'skippedTests':0,'expectedFailures':0,'testPlanConfiguration':{'configurationId':'1','configurationName':'Test Scheme Action'}}],'totalTestCount':2,'passedTests':2,'failedTests':0,'skippedTests':0,'expectedFailures':0,'result':'Passed','startTime':start+1,'finishTime':start+50}
        tests={'devices':[device],'testNodes':[{'nodeType':'Test Case','nodeIdentifier':'ToggleUITests/'+method+'()','nodeIdentifierURL':i.PREFIX+method,'name':method+'()','result':'Passed'} for method in i.METHODS]}
        session=prepare.BASE/'host-fixture/session'
        observer={'schema':'mixer.apple-command-finalization-observer.2','argv':i.command_argv(root,session),'resultBundle':str(session/'session.xcresult'),'PID':4242,'processGroup':4242,'ownedProcessGroup':{'state':'absent','targetProcessGroup':4242},'startNewSession':True,'successInferredFromConsoleOrMarkers':False,'exitCode':0,'cleanup':{'attempted':False,'complete':None,'signals':[]},'streams':{name:{'eof':True,'readerFailed':False,'readerErrors':[],'observedBytes':0,'retainedBytes':0,'retainedSHA256':i.digest(b'')} for name in ['stdout','stderr']}}
        before=copy.deepcopy(self.old_before);before['observation']['state']['focused']=False;before['signature'][1]=int((start+12)*1e9)
        after=copy.deepcopy(before['observation'])
        witness=copy.deepcopy(self.old_witness['witness'])
        for snapshot, focus in [(witness['before'],self.classifier.REFERENCE if premise else None),(witness['after'],destination)]:
            for identifier,element in snapshot['elements'].items():element['hasFocus']=identifier==focus
        binding=copy.deepcopy(self.old_witness['binding'])
        baseline=copy.deepcopy(before['observation']);baseline.update(keyboardWitness=witness,keyboardBinding=binding)
        verdict=self.oracle.verdict('diagnostic',i.CASE,'native-keyboard',baseline,after,False)
        verdict.update(ownedSimulatorIdentity=copy.deepcopy(root['ownedSimulatorIdentity']),generation=1,actionIndex=1)
        p={'schema':self.classifier.SCHEMA,'case':i.CASE,'phase':'acquire','generation':1,'actionIndex':1,'requiredFocus':self.classifier.REFERENCE,'observedFocus':self.classifier.REFERENCE if premise else None,'passed':premise,'actionInjectionCount':0,'before':copy.deepcopy(witness['before'])}
        before_key={key:witness[key] for key in ['case','phase','key','generation','actionIndex','before']}
        settings={'schema':'mixer.apple-toggle.keyboard-settings.1','step':'setup-enabled','passed':True,'bundle':'com.apple.Preferences','fullKeyboardAccessValue':'1','route':['Accessibility','Keyboards & Typing','Full Keyboard Access']}
        values={'settings':settings,'premise':p}
        if premise and not missing:values.update(before=before_key,witness=witness,verdict=verdict)
        manifest=[{'testIdentifier':'ToggleUITests/'+method+'()','testIdentifierURL':i.PREFIX+method,'attachments':[]} for method in i.METHODS]
        human={'settings':'Public Settings setup-enabled_0_fixture.json','premise':'Reference first-Tab precondition_0_fixture.json','before':'Before public key acquire_0_fixture.json','witness':'Public keyboard acquire_0_fixture.json','verdict':'Strict keyboard verdict acquire_0_fixture.json'}
        timestamps={'settings':start+10,'premise':start+15,'before':start+16,'witness':start+20,'verdict':start+22}
        for role in values:
            manifest[0 if role=='settings' else 1]['attachments'].append({'exportedFileName':role+'.json','suggestedHumanReadableName':human[role],'timestamp':timestamps[role],'deviceId':device['deviceId'],'deviceName':device['deviceName'],'configurationName':'Test Scheme Action','isAssociatedWithFailure':False})
        captures={'begin':{'ownedSimulatorIdentity':copy.deepcopy(root['ownedSimulatorIdentity']),'candidate':'diagnostic','case':i.CASE,'generation':1,'actionIndex':0,'begunWallNS':int((start+11)*1e9)},'before':before}
        if premise and not missing:captures.update(after={'observation':after,'signature':copy.deepcopy(before['signature']),'verdict':copy.deepcopy(verdict)},witness={'binding':binding,'witness':copy.deepcopy(witness)})
        if not premise or missing or verdict['passed'] is False:
            summary.update(result='Failed',passedTests=1,failedTests=1);summary['devicesAndConfigurations'][0].update(passedTests=1,failedTests=1);tests['testNodes'][1]['result']='Failed';observer['exitCode']=65
        cleanup=[{'resource':name,'passed':True} for name in ['loopback-server-shutdown','loopback-server-close','loopback-thread-join','ephemeral-capability-workspace-removal','owned-simulator-and-baseline-reconciliation']]
        return dict(root=root,session=session,observer=observer,streams={'stdout':b'','stderr':b''},summary=summary,tests=tests,manifest=manifest,values=values,captures=captures,cleanup=cleanup)

    def host_capsule(self,root,session,code,raw,payloads,captures):
        # Explicit private synthetic test fixture. Only adapter.capture_official
        # may construct this in runtime after actual selected official commands.
        i.official_methods(i.parse(raw['summary']),i.parse(raw['tests']),root,code)
        return i.CapturedOfficial(i._CAPTURE_TOKEN,root,session,code,raw,payloads,captures)

    def execute(self,f, capsule=None):
        raw={'summary':i.stable(f['summary']),'tests':i.stable(f['tests']),'manifest':i.stable(f['manifest'])}
        try:
            payloads={role+'.json':i.stable(value) if type(value) is not bytes else value for role,value in f['values'].items()}
            captures={role:i.stable(value) for role,value in f['captures'].items()}
            captured=capsule if capsule is not None else self.host_capsule(f['root'],f['session'],f['observer']['exitCode'],raw,payloads,captures)
            return i.import_selected(f['root'],f['session'],f['observer'],f['streams'],captured,payloads,captures,f['cleanup'],self.oracle,self.classifier)
        except (KeyError,ValueError,TypeError,OverflowError,RecursionError) as error:
            return {'diagnosticOutcome':'invalid-or-incomplete-evidence','keyInjectionCount':None,'failure':str(error)}

    def reject(self,f):
        result=self.execute(f);self.assertEqual(result['diagnosticOutcome'],'invalid-or-incomplete-evidence',result);self.assertIsNone(result['keyInjectionCount'])

    def test_001_one_complete_strict_original_pass_is_diagnostic_only(self):
        result=self.execute(self.fixture());self.assertEqual(result['diagnosticOutcome'],'one-strict-original-verdict-passed',result);self.assertEqual(result['keyInjectionCount'],1)
        for key in ['runPassed','completeCaseSet','cursorCompletionCredit','fullSixCaseQualification','nativeKeyboardQualification','carrierAccepted','gaAccepted']:self.assertIs(result[key],False)

    def test_002_one_complete_strict_original_failure_retained(self):
        result=self.execute(self.fixture(destination=None));self.assertEqual(result['diagnosticOutcome'],'one-strict-original-verdict-failed',result);self.assertEqual(result['keyInjectionCount'],1);self.assertIs(result['singleTabDiagnosticEvidencePassed'],False)

    def test_003_unique_bound_false_premise_proves_zero(self):
        result=self.execute(self.fixture(premise=False));self.assertEqual(result['diagnosticOutcome'],'failed-reference-precondition-zero-injection',result);self.assertEqual(result['keyInjectionCount'],0)

    def test_004_passed_premise_missing_return_stays_unknown(self):
        result=self.execute(self.fixture(missing=True));self.assertEqual(result['diagnosticOutcome'],'unknown',result);self.assertIsNone(result['keyInjectionCount'])

    def test_005_missing_premise_never_infers_zero(self):
        f=self.fixture(premise=False);f['values'].pop('premise');f['manifest'][1]['attachments']=[]
        result=self.execute(f);self.assertEqual(result['diagnosticOutcome'],'unknown');self.assertIsNone(result['keyInjectionCount'])

    def test_006_original_authored_first_failure_is_exact_and_immutable(self):
        before=copy.deepcopy(self.old_before['observation']);before.update(keyboardWitness=self.old_witness['witness'],keyboardBinding=self.old_witness['binding'])
        verdict=self.oracle.verdict('diagnostic',i.CASE,'native-keyboard',before,self.old_after['observation'],self.old_before['signature']!=self.old_after['signature'])
        expected=copy.deepcopy(self.old_after['verdict'])
        for field in ['generation','actionIndex','ownedSimulatorIdentity']:expected.pop(field)
        self.assertTrue(self.classifier.strict_json_equal(verdict,expected));self.assertEqual([key for key,value in verdict['predicates'].items() if value is not True],['actualNativeFocusTraversal'])

    def test_007_pure_classifier_cannot_supply_provenance(self):
        f=self.fixture();raw={key:i.stable(f[key]) for key in ['summary','tests','manifest']}
        result=i.import_selected(f['root'],f['session'],f['observer'],f['streams'],raw,{}, {},f['cleanup'],self.oracle,self.classifier)
        self.assertFalse(result['provenanceAccepted']);self.assertIsNone(result['keyInjectionCount'])

    def test_008_cross_run_capsule_rejected(self):
        f=self.fixture();c=self.host_capsule(f['root'],f['session'],0,{key:i.stable(f[key]) for key in ['summary','tests','manifest']},{role+'.json':i.stable(value) for role,value in f['values'].items()},{role:i.stable(value) for role,value in f['captures'].items()});f['root']['runID']='33333333-3333-4333-8333-333333333333'
        result=self.execute(f,c);self.assertEqual(result['diagnosticOutcome'],'invalid-or-incomplete-evidence')

    def test_009_capsule_wrong_session_rejected(self):
        f=self.fixture();c=self.host_capsule(f['root'],f['session']/'other',0,{key:i.stable(f[key]) for key in ['summary','tests','manifest']},{role+'.json':i.stable(value) for role,value in f['values'].items()},{role:i.stable(value) for role,value in f['captures'].items()});result=self.execute(f,c);self.assertEqual(result['diagnosticOutcome'],'invalid-or-incomplete-evidence')

    def test_010_selected_source_derivation_is_bounded(self):
        changed={name for name,raw in self.derived.items() if self.runtime.get(name)!=raw}
        self.assertEqual(changed,{'composition.py','orchestration.py','attachment_export.py','join_support.py','importer.py','reference_contract.py'})
        self.assertEqual(self.derived['command_observer.py'],self.runtime['command_observer.py'])
        for name in prepare.ORACLES:
            key='inputs/runtime/verification/'+name;self.assertEqual(self.derived[key],self.runtime[key])
        self.assertEqual(self.template['methods'],list(i.METHODS))

    def test_011_derived_modules_compile_without_tools(self):
        for name,raw in self.derived.items():
            if name.endswith('.py'):compile(raw,name,'exec')

    def test_012_duplicate_json_members_reject(self):
        for raw in [b'{"a":1,"a":1}',b'{"before":{"a":true,"a":true}}',b'{"x":NaN}',b'{"x":Infinity}',b'{"x":-Infinity}',b'{"x":1e9999}',b'{"x":01}']:
            with self.subTest(raw=raw),self.assertRaises((ValueError,UnicodeError)):i.parse(raw)

    def test_013_huge_numeric_and_nesting_reject_structured(self):
        f=self.fixture();f['values']['premise']['before']['uptime']=10**1000;self.reject(f)
        with self.assertRaises(ValueError):i.parse(b'['*110+b'0'+b']'*110)

    def test_014_json_invalid_utf8_and_trailing_content_reject(self):
        for raw in [b'\xff',b'{} {}',b'"unterminated',b'['*1000]:
            with self.subTest(raw=raw[:20]),self.assertRaises((ValueError,UnicodeError,RecursionError)):i.parse(raw)

    def test_015_fresh_root_selection_requires_now_and_packet(self):
        f=self.fixture()
        with self.assertRaises(ValueError):i.validate_root(f['root'],'b'*64)
        f['root']['selectedAtUTC']='2000-01-01T00:00:00+00:00'
        with self.assertRaises(ValueError):i.validate_root(f['root'],fresh=True)
        f['root']['selectedAtUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();self.assertEqual(i.validate_root(f['root'],fresh=True),f['root'])

    def test_016_false_premise_foreign_execution_cannot_prove_zero(self):
        f=self.fixture(premise=False);f['manifest'][1]['testIdentifier']='ToggleUITests/test010EnabledFromOff()';self.reject(f)

    def test_017_failed_premise_with_returned_witness_contradiction(self):
        f=self.fixture();f['values']['premise'].update(passed=False,observedFocus=None);f['values']['premise']['before']['elements'][self.classifier.REFERENCE]['hasFocus']=False;self.reject(f)

    def test_018_reordered_before_attachment_rejects(self):
        f=self.fixture();f['manifest'][1]['attachments'][0]['timestamp']=f['summary']['finishTime'];self.reject(f)

    def test_019_typed_original_regressions_reject(self):
        for field in ['nativeAppFocusedBefore','nativeAppFocusedAfter','originalOraclePassed','pairedFocusDisagreement','missingAppFocusUpdateSignal']:
            f=self.fixture();v=f['values']['verdict'];v[field]=int(v[field]) if type(v[field]) is bool else bool(v[field]);f['captures']['after']['verdict']=copy.deepcopy(v)
            with self.subTest(field=field):self.reject(f)

    def test_020_unchanged_cursor_cannot_complete(self):
        f=self.fixture();cursor=self.oracle.Cursor(i.CASE)
        for command in ['resume','reset']:cursor.command(command)
        cursor.advance(f['values']['witness']);self.assertFalse(cursor.complete);self.assertEqual(cursor.acquisitions,1)

    def test_021_archive_round_trip_and_corruption_rejected(self):
        h=prepare.helpers();rows=prepare.manifest(self.derived)
        with tempfile.TemporaryDirectory(prefix='archive-control-',dir=prepare.BASE) as temp:
            base=Path(temp);h.materialize(base/'selected',rows,self.derived);arc=h.archive_sources(base/'sources.tar.gz',base/'selected',rows);self.assertEqual(h.archive_payload(base/'sources.tar.gz',rows,arc['archive']['sha256'],'selected/'),self.derived)
            with (base/'sources.tar.gz').open('ab') as stream:stream.write(b'corrupt')
            with self.assertRaises(ValueError):h.archive_payload(base/'sources.tar.gz',rows,arc['archive']['sha256'],'selected/')

    def test_022_source_preference_and_one_tab_fixture_unchanged(self):
        swift=self.accepted['harness/UITests/ToggleUITests.swift'].decode();method=swift.split('    func test010ReferenceFirstTab() throws {\n',1)[1].split('    }\n',1)[0]
        self.assertEqual(method,'        _ = try launchCase("keyboard-enabled-off", initial: false)\n        try key("acquire", "tab", requiredFocusBefore: "plain-uibutton-reference")\n')
        self.assertIn(b'preferredFocusEnvironments: [UIFocusEnvironment] { [referenceButton] }',self.accepted['source/Prototype/main.swift'])

    def test_023_adapter_actual_tool_capture_and_one_shot_binding(self):
        f=self.fixture();namespace={'select_command':lambda *args:None,'run_observed':lambda *args:None,'require':prepare.require,'Path':Path,'sha':prepare.sha,'_selected':{'called':True,'session':f['session'],'argv':f['observer']['argv']}}
        with mock.patch.dict(sys.modules,{'reference_contract':self.classifier}):
            exec(compile((prepare.BASE/'adapter.py').read_bytes(),'adapter.py','exec'),namespace)
        namespace['configure_root'](f['root'])
        with self.assertRaises(ValueError):namespace['configure_root'](f['root'])
        # Reading stale receipt fields cannot mint a selected execution capability.
        namespace['_selected']['called']=False
        with self.assertRaises(ValueError):namespace['capture_official'](None,None,None,None)

    def test_024_dispatch_refuses_unreviewed_packet_before_native_import(self):
        with mock.patch.object(prepare,'verify',return_value={'packetSHA256':'a'*64}):
            with self.assertRaises(ValueError):prepare.dispatch('b'*64,'absent','c'*64)


    def test_025_full_selected_composition_import_and_byte_verification_has_no_native_side_effect(self):
        f=self.fixture();h=prepare.helpers();rows=prepare.manifest(self.derived)
        with tempfile.TemporaryDirectory(prefix='composition-control-',dir=prepare.BASE) as temporary:
            base=Path(temporary);h.materialize(base/'selected',rows,self.derived)
            payload=h.archive_payload(prepare.V1/'compile-attempt-1/products.tar.gz',self.products['products'],prepare.PRODUCT)
            h.materialize(base/'products',self.products['products'],payload)
            selection=copy.deepcopy(self.template);selection.update(repositoryRoot=str(prepare.ROOT),outputBase=str(base),productsRoot=str(base/'products'),productArchive=str(prepare.V1/'compile-attempt-1/products.tar.gz'),productManifest=self.products,trustedRootSelection=f['root'],files={name:row['sha256'] for name,row in rows.items()})
            (base/'selected/runtime-selection.json').write_bytes(i.stable(selection))
            program="""import sys,subprocess,socket
from pathlib import Path
def forbidden(*args,**kwargs):raise AssertionError('Native command/service attempted by host-only composition import')
subprocess.Popen=forbidden
socket.socket.bind=forbidden
socket.socket.connect=forbidden
sys.path.insert(0,sys.argv[1])
import composition
assert composition.h.SCOPES['interaction']['methods']==['test000PublicSettingsFullKeyboardAccess','test010ReferenceFirstTab']
assert composition.h.SCOPES['interaction']['cases']=={'keyboard-enabled-off'}
assert set(composition.h.packet.CONFIGS)=={'diagnostic'}
assert composition.h.verify()['nativeAcceptanceGranted'] is False
assert composition.join_support._ROOT['runID']=='11111111-1111-4111-8111-111111111111'
print('PASS: complete frozen source composition and compiled products; native command and socket boundaries forbidden')
"""
            command=[sys.executable,'-B','-c',program,str(base/'selected')]
            completed=subprocess.run(command,capture_output=True,text=True,timeout=30)
            print('Host composition probe argv:',command)
            print(completed.stdout)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertFalse((base/'runtime').exists())

    def adapter_namespace(self,f,output):
        namespace={'__file__':str(output/'selected/join_support.py')}
        with mock.patch.dict(sys.modules,{'reference_contract':self.classifier}):
            exec(compile(self.derived['join_support.py'],namespace['__file__'],'exec'),namespace)
        namespace['configure_root'](f['root'])
        session=output/'runtime/session';session.mkdir(parents=True,mode=0o700);session.chmod(0o700)
        result=session/'session.xcresult';result.mkdir()
        f['session']=session;f['observer']['argv']=i.command_argv(f['root'],session);f['observer']['resultBundle']=str(result)
        observer=session/'command-observer';observer.mkdir();(observer/'observer.json').write_bytes(i.stable(f['observer']))
        namespace['_selected']={'called':True,'session':session,'argv':f['observer']['argv'],'sessionIdentity':namespace['path_identity'](session,0o700),'resultIdentity':namespace['path_identity'](result),'rootSHA256':i.digest(i.stable(f['root']))}
        folder=output/'runtime/attachments';folder.mkdir()
        for role,value in f['values'].items():(folder/(role+'.json')).write_bytes(i.stable(value))
        (folder/'manifest.json').write_bytes(i.stable(f['manifest']))
        retained={'ownedResultPath':str(result),'exitCode':0,'passed':True,'files':{p.name:{'bytes':p.stat().st_size,'sha256':i.digest(p.read_bytes())} for p in folder.iterdir()}}
        (output/'runtime/attachment-export.json').write_bytes(i.stable(retained))
        capture_folder=output/'runtime/captures';capture_folder.mkdir()
        for role,name in [('begin','0001-begin.json'),('before','0001-before-1.json'),('after','0001-after-1.json'),('witness','0001-keyboard-witness-1.json')]:
            if role in f['captures']:(capture_folder/name).write_bytes(i.stable(f['captures'][role]))
        calls=[]
        def invoke(command_object,argv,**kwargs):
            calls.append((argv,kwargs))
            self.assertEqual(argv[:4],['/usr/bin/xcrun','xcresulttool','get','test-results'])
            self.assertEqual(argv[-2:],['--path',str(result)])
            return 0,i.stable(f[argv[4]]).decode(),'actual fake tool stderr'
        return namespace,invoke,calls,types.SimpleNamespace(RUN_DIR=output/'runtime')

    def test_026_actual_adapter_traversal_mints_once_from_exact_selected_result(self):
        f=self.fixture()
        with tempfile.TemporaryDirectory(prefix='adapter-control-',dir=prepare.BASE) as temporary:
            output=Path(temporary);namespace,invoke,calls,h=self.adapter_namespace(f,output)
            namespace['capture_official'](object(),invoke,h,output)
            self.assertEqual([row[0][4] for row in calls],['summary','tests'])
            self.assertEqual(namespace['_OFFICIAL']['official'].rootSHA256,i.digest(i.stable(f['root'])))
            record=i.read(output/'runtime/official-capture.json');self.assertEqual(len(record['officialToolInvocations']),2)
            with self.assertRaises(ValueError):namespace['capture_official'](object(),invoke,h,output)
            with self.assertRaises(TypeError):namespace['_OFFICIAL']['official'].rootSHA256='changed'

    def test_027_result_directory_inode_substitution_rejected_before_official_commands(self):
        f=self.fixture()
        with tempfile.TemporaryDirectory(prefix='adapter-control-',dir=prepare.BASE) as temporary:
            output=Path(temporary);namespace,invoke,calls,h=self.adapter_namespace(f,output)
            result=f['session']/'session.xcresult';result.rename(f['session']/'retained-original.xcresult');result.mkdir()
            with self.assertRaises(ValueError):namespace['capture_official'](object(),invoke,h,output)
            self.assertEqual(calls,[]);self.assertIsNone(namespace['_OFFICIAL'])

    def test_028_session_directory_substitution_rejected_before_official_commands(self):
        f=self.fixture()
        with tempfile.TemporaryDirectory(prefix='adapter-control-',dir=prepare.BASE) as temporary:
            output=Path(temporary);namespace,invoke,calls,h=self.adapter_namespace(f,output)
            session=f['session'];session.rename(session.parent/'retained-original');session.mkdir(mode=0o700);session.chmod(0o700);(session/'session.xcresult').mkdir()
            with self.assertRaises(ValueError):namespace['capture_official'](object(),invoke,h,output)
            self.assertEqual(calls,[])

    def test_029_actual_official_tool_failure_does_not_mint(self):
        f=self.fixture()
        with tempfile.TemporaryDirectory(prefix='adapter-control-',dir=prepare.BASE) as temporary:
            output=Path(temporary);namespace,invoke,calls,h=self.adapter_namespace(f,output)
            with self.assertRaises(ValueError):namespace['capture_official'](object(),lambda *args,**kwargs:(1,'{}','failed'),h,output)
            self.assertIsNone(namespace['_OFFICIAL'])

    def test_030_manifest_file_substitution_is_rejected(self):
        f=self.fixture()
        with tempfile.TemporaryDirectory(prefix='adapter-control-',dir=prepare.BASE) as temporary:
            output=Path(temporary);namespace,invoke,calls,h=self.adapter_namespace(f,output)
            (output/'runtime/attachments/premise.json').write_bytes(b'{}')
            with self.assertRaises(ValueError):namespace['capture_official'](object(),invoke,h,output)
            self.assertIsNone(namespace['_OFFICIAL'])


    def test_031_attachment_bytes_cannot_change_after_actual_capture(self):
        f=self.fixture();raw={key:i.stable(f[key]) for key in ['summary','tests','manifest']}
        c=self.host_capsule(f['root'],f['session'],0,raw,{role+'.json':i.stable(value) for role,value in f['values'].items()},{role:i.stable(value) for role,value in f['captures'].items()})
        f['values']['premise']['extra']='tampered'
        result=self.execute(f,c);self.assertEqual(result['diagnosticOutcome'],'invalid-or-incomplete-evidence');self.assertIn('Attachment bytes differ',result['failure'])

    def test_032_app_observations_cannot_change_after_actual_capture(self):
        f=self.fixture();raw={key:i.stable(f[key]) for key in ['summary','tests','manifest']}
        c=self.host_capsule(f['root'],f['session'],0,raw,{role+'.json':i.stable(value) for role,value in f['values'].items()},{role:i.stable(value) for role,value in f['captures'].items()})
        f['captures']['before']['signature'][0]+=1
        result=self.execute(f,c);self.assertEqual(result['diagnosticOutcome'],'invalid-or-incomplete-evidence');self.assertIn('Application observation bytes differ',result['failure'])

    def test_033_duplicate_subexecution_inside_selected_test_rejects(self):
        f=self.fixture();f['tests']['testNodes'][1]['children']=[{'nodeType':'Repetition','name':'Run 2'}];self.reject(f)

    def test_034_unexpected_app_action_capture_rejects(self):
        f=self.fixture()
        with tempfile.TemporaryDirectory(prefix='adapter-control-',dir=prepare.BASE) as temporary:
            output=Path(temporary);namespace,invoke,calls,h=self.adapter_namespace(f,output)
            (output/'runtime/captures/0001-before-2.json').write_bytes(b'{}')
            with self.assertRaises(ValueError):namespace['capture_official'](object(),invoke,h,output)
            self.assertIsNone(namespace['_OFFICIAL'])

    def mocked_orchestration(self,timeout=False,cleanup_failure=False):
        f=self.fixture();trace=[]
        with tempfile.TemporaryDirectory(prefix='orchestration-control-',dir=prepare.BASE) as temporary:
            out=Path(temporary)
            class Commands:
                def __init__(self,*args):self.reporting_error=None;self.cleanup_mode=False
                def redact(self,value):return value
                def record(self,*args):trace.append(('record',args))
                def simctl(self,*args):
                    trace.append(('simctl',args))
                    if args==('list','runtimes','--json'):return i.stable({'runtimes':[{'identifier':f['root']['ownedSimulatorIdentity']['runtime'],'isAvailable':True,'buildversion':'23F77'}]}).decode()
                    if args[0]=='get_app_container':
                        path=out/('container-'+args[-1]);path.mkdir(exist_ok=True);return str(path)
                    return ''
                def run(self,argv,**kwargs):
                    trace.append(('run',list(map(str,argv))))
                    if len(argv)>1 and argv[1]=='test-without-building' and timeout:raise TimeoutError('Synthetic selected command timeout')
                    return (65 if len(argv)>1 and argv[1]=='test-without-building' else 0),'',''
            class Server:
                server_port=12345
                def serve_forever(self):raise AssertionError('Fake thread must not serve')
                def shutdown(self):
                    trace.append(('cleanup','loopback-server-shutdown'))
                    if cleanup_failure:raise OSError('Synthetic cleanup failure')
                def server_close(self):trace.append(('cleanup','loopback-server-close'))
            class Thread:
                def __init__(self,*args,**kwargs):pass
                def start(self):trace.append(('thread-start',None))
                def join(self,**kwargs):trace.append(('cleanup','loopback-thread-join'))
                def is_alive(self):return False
            def write(path,value):path.write_bytes(i.stable(value))
            def session(h,lifecycle):
                path=h.RUN_DIR/'session';path.mkdir();return path
            support=types.ModuleType('join_support');support._ROOT=f['root'];support.prepare_session=session
            support.session_configuration=lambda h,path,port,capability:path/'session.xctestrun'
            support.select_command=lambda h,argv,path:trace.append(('selection',list(argv)))
            support.retire_session=lambda *args:trace.append(('cleanup','ephemeral-capability-workspace-removal'))
            workspace=types.ModuleType('workspace_ownership')
            namespace={'__file__':str(out/'orchestration.py')}
            with mock.patch.dict(sys.modules,{'join_support':support,'workspace_ownership':workspace}):exec(compile(self.derived['orchestration.py'],namespace['__file__'],'exec'),namespace)
            h=types.SimpleNamespace(RUN_DIR=out/'runtime',SCOPES={'interaction':{'cases':{i.CASE},'methods':list(i.METHODS)}},select_runtime_directory=lambda scope:out/'runtime',verify=lambda:{'sealSHA256':'host-seal'},secrets=types.SimpleNamespace(token_hex=lambda count:'a'*64),Commands=Commands,json=i.json,RUNTIME=f['root']['ownedSimulatorIdentity']['runtime'],RUNTIME_BUILD='23F77',DEVICE_TYPE='fake',DEVELOPER=Path(f['root']['developerDirectory']),ROOT=prepare.ROOT,PRODUCTS=out/'products',devices=lambda commands:{'devices':{}},owned_device=lambda *args:{'state':'Shutdown'},write=write,require=i.require,packet=types.SimpleNamespace(CONFIGS={'diagnostic':{'app':'diagnostic.app','bundle':'dev.synthetic'}},restore=lambda *args:None,verify_installed=lambda *args:{}),validate_container=lambda path,*args,**kwargs:Path(path),Bridge=lambda *args,**kwargs:object(),server_for=lambda bridge:Server(),threading=types.SimpleNamespace(Thread=Thread),runtime_summary=lambda scope,bridge,code,failure,cleanup:{'runPassed':False,'diagnosticOutcome':'unknown','cleanupResults':cleanup},cleanup=lambda *args:trace.append(('cleanup','owned-simulator-and-baseline-reconciliation')))
            bindings=types.SimpleNamespace(check=lambda *args:None)
            if timeout or cleanup_failure:
                with self.assertRaises((TimeoutError,OSError)):namespace['run'](h,bindings,[],'host-seal')
            else:
                result=namespace['run'](h,bindings,[],'host-seal');self.assertIs(result['runPassed'],False)
            self.assertEqual([row[1] for row in trace if row[0]=='cleanup'],['loopback-server-shutdown','loopback-server-close','loopback-thread-join','ephemeral-capability-workspace-removal','owned-simulator-and-baseline-reconciliation'])
            self.assertFalse(any(row[0]=='simctl' and row[1][0]=='create' for row in trace))
            selected=[row[1] for row in trace if row[0]=='selection'];self.assertEqual(len(selected),1)
            self.assertEqual(selected[0][-2:],['-only-testing:MixerToggleUITests/ToggleUITests/'+m for m in i.METHODS])

    def test_035_root_owned_orchestration_selects_once_and_cleans_all(self):self.mocked_orchestration()
    def test_036_selected_timeout_still_attempts_five_cleanups(self):self.mocked_orchestration(timeout=True)
    def test_037_cleanup_failure_never_suppresses_later_cleanups(self):self.mocked_orchestration(cleanup_failure=True)


# Each mutation is a separately reported executable host control.
MUTATIONS = {
 'official_extra_execution':lambda f:f['tests']['testNodes'].append(copy.deepcopy(f['tests']['testNodes'][1])),
 'official_foreign_method':lambda f:f['tests']['testNodes'][1].update(nodeIdentifier='ToggleUITests/test010EnabledFromOff()'),
 'official_method_url':lambda f:f['tests']['testNodes'][1].update(nodeIdentifierURL=i.PREFIX+'test010EnabledFromOff'),
 'official_method_name':lambda f:f['tests']['testNodes'][1].update(name='test010EnabledFromOff()'),
 'official_duplicate_settings':lambda f:f['tests']['testNodes'].__setitem__(1,copy.deepcopy(f['tests']['testNodes'][0])),
 'official_missing_execution':lambda f:f['tests']['testNodes'].pop(),
 'official_skipped':lambda f:f['tests']['testNodes'][1].update(result='Skipped'),
 'official_count_bool':lambda f:f['summary'].update(totalTestCount=True),
 'official_count_mismatch':lambda f:f['summary'].update(totalTestCount=3),
 'official_device':lambda f:f['tests']['devices'][0].update(deviceId='foreign'),
 'official_extra_device':lambda f:f['tests']['devices'].append(copy.deepcopy(f['tests']['devices'][0])),
 'official_os_build':lambda f:f['tests']['devices'][0].update(osBuildNumber='foreign'),
 'official_configuration':lambda f:f['summary']['devicesAndConfigurations'][0]['testPlanConfiguration'].update(configurationId='2'),
 'official_stale_run':lambda f:f['summary'].update(startTime=1),
 'official_exit_contradiction':lambda f:f['observer'].update(exitCode=65),
 'root_source':lambda f:f['root'].update(sourceTreeSHA256='b'*64),
 'root_product':lambda f:f['root'].update(productArchiveSHA256='b'*64),
 'root_other_tool':lambda f:f['root'].update(developerDirectory='/Applications/Xcode.app/Contents/Developer'),
 'attachment_foreign_device':lambda f:f['manifest'][1]['attachments'][0].update(deviceId='foreign'),
 'attachment_duplicate_group':lambda f:f['manifest'].append(copy.deepcopy(f['manifest'][1])),
 'attachment_duplicate_role':lambda f:f['manifest'][1]['attachments'].append(copy.deepcopy(f['manifest'][1]['attachments'][0])),
 'attachment_wrong_method_owner':lambda f:f['manifest'][1].update(testIdentifier='ToggleUITests/test010EnabledFromOff()'),
 'attachment_stale_timestamp':lambda f:f['manifest'][1]['attachments'][0].update(timestamp=1),
 'attachment_missing_file':lambda f:f['values'].pop('witness'),
 'attachment_unmanifested_file':lambda f:f['values'].update(foreign={'unrelated':True}),
 'attachment_unrelated_json':lambda f:f['manifest'][1]['attachments'][0].update(suggestedHumanReadableName='Unrelated.json'),
 'attachment_unsafe_name':lambda f:f['manifest'][1]['attachments'][0].update(exportedFileName='../premise.json'),
 'attachment_settings_from_wrong_execution':lambda f:f['manifest'][1]['attachments'].append(f['manifest'][0]['attachments'].pop()),
 'attachment_missing_settings':lambda f:f['manifest'][0]['attachments'].clear(),
 'settings_wrong_route':lambda f:f['values']['settings'].update(route=['Other']),
 'settings_failed':lambda f:f['values']['settings'].update(passed=False),
 'missing_before_app':lambda f:f['captures'].pop('before'),
 'missing_begin':lambda f:f['captures'].pop('begin'),
 'begin_foreign_device':lambda f:f['captures']['begin']['ownedSimulatorIdentity'].update(udid='foreign'),
 'begin_cross_generation':lambda f:f['captures']['begin'].update(generation=2),
 'begin_stale_wall':lambda f:f['captures']['begin'].update(begunWallNS=1),
 'before_stale_wall':lambda f:f['captures']['before']['signature'].__setitem__(1,1),
 'after_stale_wall':lambda f:f['captures']['after']['signature'].__setitem__(1,1),
 'before_focus_contradicts':lambda f:f['captures']['before']['observation']['state'].update(focused=True),
 'before_action':lambda f:f['captures']['before'].update(action='native-touch'),
 'before_generation':lambda f:f['captures']['before'].update(generation=2),
 'before_signature_missing':lambda f:f['captures']['before'].pop('signature'),
 'premise_action':lambda f:f['values']['premise'].update(actionIndex=2),
 'premise_type':lambda f:f['values']['premise'].update(actionInjectionCount=False),
 'premise_claim':lambda f:f['values']['premise'].update(observedFocus='authored-toggle'),
 'premise_before_contradiction':lambda f:f['values']['premise']['before']['elements']['next-focus'].update(hasFocus=True),
 'before_ax_sample_contradiction':lambda f:f['values']['before']['before'].update(uptime=0),
 'verdict_foreign_device':lambda f:f['values']['verdict']['ownedSimulatorIdentity'].update(udid='foreign'),
 'verdict_generation_float':lambda f:f['values']['verdict'].update(generation=1.0),
 'verdict_integer_predicate':lambda f:f['values']['verdict']['predicates'].update(pairedNativeFocusBefore=1),
 'verdict_missing_predicate':lambda f:f['values']['verdict']['predicates'].pop('pairedNativeFocusBefore'),
 'verdict_extra_field':lambda f:f['values']['verdict'].update(extra='changed'),
 'retained_witness_contradiction':lambda f:f['captures']['witness']['witness'].update(key='space'),
 'retained_verdict_contradiction':lambda f:f['captures']['after']['verdict'].update(originalOraclePassed=False),
 'unrelated_capture':lambda f:f['captures'].update(foreign={}),
 'observer_eof_unobserved':lambda f:f['observer']['streams']['stdout'].update(eof=False),
 'observer_eof_missing':lambda f:f['observer']['streams']['stderr'].pop('eof'),
 'observer_reader_failed':lambda f:f['observer']['streams']['stderr'].update(readerFailed=True),
 'observer_reader_error':lambda f:f['observer']['streams']['stderr'].update(readerErrors=['failure']),
 'observer_stream_hash':lambda f:f['observer']['streams']['stdout'].update(retainedSHA256='b'*64),
 'observer_stream_bytes':lambda f:f['streams'].update(stdout=b'foreign'),
 'observer_cleanup_unknown':lambda f:f['observer']['cleanup'].pop('attempted'),
 'observer_cleanup_failed':lambda f:f['observer']['cleanup'].update(attempted=True,complete=False),
 'observer_group_present':lambda f:f['observer']['ownedProcessGroup'].update(state='present'),
 'observer_group_foreign':lambda f:f['observer']['ownedProcessGroup'].update(targetProcessGroup=4141),
 'observer_pid_bool':lambda f:f['observer'].update(PID=True),
 'observer_retained_bytes_bool':lambda f:f['observer']['streams']['stdout'].update(retainedBytes=False),
 'observer_bool_exit':lambda f:f['observer'].update(exitCode=False),
 'observer_marker_inference':lambda f:f['observer'].update(successInferredFromConsoleOrMarkers=True),
 'observer_wrong_command_method':lambda f:f['observer']['argv'].__setitem__(-1,'-only-testing:Other'),
 'cleanup_missing':lambda f:f['cleanup'].pop(),
 'cleanup_duplicate':lambda f:f['cleanup'].append(copy.deepcopy(f['cleanup'][0])),
 'cleanup_failed':lambda f:f['cleanup'][0].update(passed=False),
 'cleanup_unobserved':lambda f:f['cleanup'][0].pop('passed'),
}
for index,(name,mutation) in enumerate(MUTATIONS.items(),100):
    def control(self, mutation=mutation):
        f=self.fixture();mutation(f);self.reject(f)
    control.__name__='test_'+str(index)+'_'+name
    setattr(RuntimeControls,control.__name__,control)

if __name__=='__main__':unittest.main(verbosity=2)
