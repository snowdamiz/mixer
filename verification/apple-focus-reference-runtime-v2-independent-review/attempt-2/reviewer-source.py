#!/usr/bin/env python3
"""Independent frozen host review. Never dispatch or invoke native tools."""
import argparse
import ast
from contextlib import redirect_stderr, redirect_stdout
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / 'verification/apple-focus-reference-runtime-v2'
EXPECTED_HANDOFF = '78ada9ff4aa3392e07f4fdf71a0eb563c67c8fde920388609372b09a771f3668'
EXPECTED_PACKET = '8a6be8d06285c3fd25bdb9bc2c589ea87a7677d8a6b9b6e0545b23076cd6a7b6'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
stable = lambda value: (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
SPAWNS = []


def audit(event, args):
    if event == 'subprocess.Popen':
        executable, argv = args[:2]
        # Only the two inspected, explicitly native-disabled composition probes.
        permitted = (str(Path(executable).resolve()) == str(Path(sys.executable).resolve())
                     and len(argv) == 5 and argv[1:3] == ['-B', '-c']
                     and 'subprocess.Popen=forbidden' in argv[3]
                     and 'socket.socket.bind=forbidden' in argv[3]
                     and 'socket.socket.connect=forbidden' in argv[3]
                     and Path(argv[4]).resolve().is_relative_to(BASE))
        if not permitted:
            raise AssertionError('Independent host boundary rejected subprocess: '+repr(argv))
        SPAWNS.append({'argv': argv, 'programSHA256': sha(argv[3].encode()), 'scope': 'Host-only guarded Python composition import'})
    if event in ('os.system', 'os.exec', 'os.posix_spawn', 'socket.bind', 'socket.connect', 'socket.connect_ex'):
        raise AssertionError('Independent host boundary rejected '+event)


INVENTORY_PROGRAM = '''import sys,subprocess,socket,json,time,zlib,struct
from pathlib import Path
def forbidden(*args,**kwargs):raise AssertionError('Native command/service forbidden in independent host probe')
subprocess.Popen=forbidden
socket.socket.bind=forbidden
socket.socket.connect=forbidden
sys.path.insert(0,sys.argv[1])
import composition
base=Path(composition.selection['outputBase'])
runtime=base/'runtime';runtime.mkdir()
documents=base/'synthetic-documents';documents.mkdir()
bridge=composition.h.Bridge({'diagnostic':documents},runtime/'captures','a'*64,composition.selection['trustedRootSelection']['ownedSimulatorIdentity'],allowed_cases={'keyboard-enabled-off'})
rows=[]
def observe(stage):
    inventory=[{'name':p.name,'kind':'directory' if p.is_dir() else 'file'} for p in sorted((runtime/'captures').iterdir())]
    try:result=composition.join_support.application_captures(base);accepted=True;failure=None
    except Exception as error:result=None;accepted=False;failure=type(error).__name__+': '+str(error)
    rows.append({'stage':stage,'inventory':inventory,'accepted':accepted,'failure':failure,'capturedRoles':None if result is None else sorted(result)})
observe('actual-composed-bridge-construction')
bridge.settings.request({'kind':'start','case':composition.telemetry.CASE,'uptime':time.monotonic()})
observe('actual-session-start-transaction-commit')
def chunk(name,payload):return struct.pack('>I',len(payload))+name+payload+struct.pack('>I',zlib.crc32(name+payload)&0xffffffff)
png=b'\\x89PNG\\r\\n\\x1a\\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\\x00\\x00\\x00\\x00'))+chunk(b'IEND',b'')
composition.telemetry.png(png)
bridge.persistence.commit(('settings-0001',{'record':'host-only-independent-synthetic-payload-publication'}),[('settings-0001-ax','ax',b'Host-only synthetic AX text'),('settings-0001-png','png',png)])
observe('actual-transactionstore-ax-and-png-publication')
print(json.dumps({'syntheticOnly':True,'nativeExecuted':False,'rows':rows,'guardAbsent':not bridge.persistence.guard.exists(),'retirementPending':bridge.persistence.retirement_pending,'persistenceUncertain':bridge.persistence.uncertain},sort_keys=True))
'''


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main(attempt_number):
    attempt = BASE / ('attempt-'+str(attempt_number))
    assert attempt.is_dir() and not (attempt/'receipt.json').exists(), 'Fresh review receipt required'
    started = time.monotonic()
    before = json.loads((attempt/'frozen-inputs-before.json').read_bytes())
    assert sha((PRODUCER/'handoff.json').read_bytes()) == EXPECTED_HANDOFF
    assert sha((PRODUCER/'packet.json').read_bytes()) == EXPECTED_PACKET
    for name, row in before.items():
        assert sha((ROOT/name).read_bytes()) == row['sha256'], name
    copies = attempt/'producer-copy'
    source_manifest = json.loads((attempt/'source-inspection-manifest.json').read_bytes())
    assert all(sha((attempt/'source-inspection'/name).read_bytes()) == digest for name,digest in source_manifest.items())
    # Reviewed module-level code: definitions, constants, bounded data reads and
    # frozen local imports. Record the top-level statements used in the audit.
    static = {}
    for name in source_manifest:
        if name.endswith('.py'):
            source = (attempt/'source-inspection'/name).read_text()
            module = ast.parse(source)
            static[name] = [{'line': node.lineno, 'kind': type(node).__name__, 'source': ast.get_source_segment(source,node) if not isinstance(node,(ast.FunctionDef,ast.ClassDef)) else node.name} for node in module.body]
    (attempt/'static-entrypoints.json').write_bytes(stable(static))
    sys.dont_write_bytecode = True
    sys.addaudithook(audit)
    sys.path.insert(0,str(copies))
    prepare = load('prepare',copies/'prepare.py')
    prepare.ROOT=ROOT;prepare.BASE=copies
    prepare.OLD=ROOT/'verification/apple-focus-diagnostic-runtime-v1'
    prepare.V1=ROOT/'verification/apple-focus-reference-diagnostic-v1'
    prepare.V2=ROOT/'verification/apple-focus-reference-diagnostic-v2'
    prepare.REVIEW=ROOT/'verification/apple-focus-reference-diagnostic-v2-independent-review'
    tests = load('test_importer',copies/'test_importer.py')
    i=tests.i
    detail=[]

    class IndependentControls(tests.RuntimeControls):
        def record_rejection(self,name,mutation):
            fixture=self.fixture();mutation(fixture)
            result=self.execute(fixture)
            detail.append({'control':name,'expected':'invalid-or-incomplete-evidence','result':result})
            self.assertEqual(result['diagnosticOutcome'],'invalid-or-incomplete-evidence',result)
            self.assertIsNone(result['keyInjectionCount'])

        def test_review_actual_composed_bridge_and_settings_inventory(self):
            helper=prepare.helpers();rows=prepare.manifest(self.derived)
            with tempfile.TemporaryDirectory(prefix='composition-control-',dir=prepare.BASE) as temporary:
                base=Path(temporary)
                helper.materialize(base/'selected',rows,self.derived)
                payload=helper.archive_payload(prepare.V1/'compile-attempt-1/products.tar.gz',self.products['products'],prepare.PRODUCT)
                helper.materialize(base/'products',self.products['products'],payload)
                selection=copy.deepcopy(self.template)
                selection.update(repositoryRoot=str(ROOT),outputBase=str(base),productsRoot=str(base/'products'),productArchive=str(prepare.V1/'compile-attempt-1/products.tar.gz'),productManifest=self.products,trustedRootSelection=self.fixture()['root'],files={name:row['sha256'] for name,row in rows.items()})
                (base/'selected/runtime-selection.json').write_bytes(i.stable(selection))
                completed=subprocess.run([sys.executable,'-B','-c',INVENTORY_PROGRAM,str(base/'selected')],capture_output=True,text=True,timeout=30)
                (attempt/'actual-bridge-inventory.stdout.log').write_text(completed.stdout)
                (attempt/'actual-bridge-inventory.stderr.log').write_text(completed.stderr)
                self.assertEqual(completed.returncode,0,completed.stderr)
                record=json.loads(completed.stdout);(attempt/'actual-bridge-inventory.json').write_bytes(stable(record))
                self.assertTrue(record['guardAbsent']);self.assertFalse(record['retirementPending']);self.assertFalse(record['persistenceUncertain'])
                self.assertTrue(all(row['accepted'] for row in record['rows']),record)

        def test_review_forged_public_caller_data_rejects(self):
            f=self.fixture()
            result=self.execute(f,copy.deepcopy(f['summary']))
            detail.append({'control':'forged-public-caller','result':result})
            self.assertEqual(result['diagnosticOutcome'],'invalid-or-incomplete-evidence')
            self.assertIsNone(result['keyInjectionCount'])

        def test_review_capture_constructor_requires_private_token(self):
            f=self.fixture()
            with self.assertRaises(ValueError):i.CapturedOfficial(object(),f['root'],f['session'],0,{}, {},{})

        def test_review_selection_age_future_and_boundary(self):
            for offset in [-301,1]:
                f=self.fixture();f['root']['selectedAtUTC']=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=offset)).isoformat()
                with self.subTest(offset=offset),self.assertRaises(ValueError):i.validate_root(f['root'],fresh=True)

        def test_review_app_symlink_rejected_before_mint(self):
            f=self.fixture()
            with tempfile.TemporaryDirectory(prefix='adapter-control-',dir=prepare.BASE) as temporary:
                output=Path(temporary);namespace,invoke,calls,h=self.adapter_namespace(f,output)
                path=output/'runtime/captures/0001-before-1.json';retained=output/'retained-before.json';path.rename(retained);path.symlink_to(retained)
                with self.assertRaises(ValueError):namespace['capture_official'](object(),invoke,h,output)
                self.assertIsNone(namespace['_OFFICIAL'])

        def test_review_result_swap_during_actual_tool_traversal_rejected(self):
            f=self.fixture()
            with tempfile.TemporaryDirectory(prefix='adapter-control-',dir=prepare.BASE) as temporary:
                output=Path(temporary);namespace,invoke,calls,h=self.adapter_namespace(f,output)
                def swapped(command,argv,**kwargs):
                    result=invoke(command,argv,**kwargs)
                    if argv[4]=='tests':
                        path=f['session']/'session.xcresult';path.rename(f['session']/'original.xcresult');path.mkdir()
                    return result
                with self.assertRaises(ValueError):namespace['capture_official'](object(),swapped,h,output)
                self.assertIsNone(namespace['_OFFICIAL'])

    mutations={
        'before_command_generation_float':lambda f:f['captures']['before'].update(commandGeneration=2.0),
        'before_signature_inode_boolean':lambda f:f['captures']['before']['signature'].__setitem__(0,False),
        'before_signature_bytes_negative':lambda f:f['captures']['before']['signature'].__setitem__(2,-1),
        'before_signature_digest_malformed':lambda f:f['captures']['before']['signature'].__setitem__(3,'not-a-sha256'),
        'after_signature_inode_boolean':lambda f:f['captures']['after']['signature'].__setitem__(0,False),
        'after_signature_bytes_float':lambda f:f['captures']['after']['signature'].__setitem__(2,1.5),
        'after_signature_digest_malformed':lambda f:f['captures']['after']['signature'].__setitem__(3,'not-a-sha256'),
        'both_signatures_wrongtypes':lambda f:[capture['signature'].__setitem__(0,False) for capture in [f['captures']['before'],f['captures']['after']]],
        'before_wall_after_premise':lambda f:[capture['signature'].__setitem__(1,int((f['summary']['startTime']+40)*1e9)) for capture in [f['captures']['before'],f['captures']['after']]],
        'false_premise_generation_boolean':lambda f:f['values']['premise'].update(generation=True),
        'duplicate_manifest_selected_owner':lambda f:f['manifest'].__setitem__(1,copy.deepcopy(f['manifest'][0])),
        'missing_app_witness_stays_unknown':lambda f:f['captures'].pop('witness'),
        'summary_nested_duplicate_execution':lambda f:f['tests']['testNodes'][1].update(extra={'nodeType':'Test Case',**copy.deepcopy(f['tests']['testNodes'][1])}),
        'official_foreign_configuration_device':lambda f:f['summary']['devicesAndConfigurations'][0]['device'].update(deviceName='foreign'),
        'official_settings_failure':lambda f:f['tests']['testNodes'][0].update(result='Failed'),
        'observer_exit_failure':lambda f:f['observer'].update(exitCode=1),
        'observer_empty_eof_metadata':lambda f:f['observer']['streams'].__setitem__('stdout',{}),
        'cleanup_nonboolean_success':lambda f:f['cleanup'][0].update(passed=1),
        'before_boolean_generation':lambda f:f['captures']['before'].update(generation=True),
        'root_baseline_contains_selected_udid':lambda f:f['root']['baselineDevices']['devices'].update(runtime=[{'udid':f['root']['ownedSimulatorIdentity']['udid']}]),
        'premise_duplicate_key_bytes':lambda f:f['values'].__setitem__('premise',b'{"passed":true,"passed":false}'),
        'retained_witness_foreign_binding':lambda f:f['captures']['witness']['binding'].update(generation=2),
        'attachment_settings_count_duplicate':lambda f:f['manifest'][0]['attachments'].append(copy.deepcopy(f['manifest'][0]['attachments'][0])),
        'after_before_order_reversed':lambda f:f['captures']['after']['signature'].__setitem__(1,f['captures']['before']['signature'][1]-1),
        'run_window_excess':lambda f:f['summary'].update(finishTime=f['summary']['finishTime']+1000),
        'source_identity_substitution':lambda f:f['root'].update(sourceTreeSHA256='c'*64),
        'product_identity_substitution':lambda f:f['root'].update(productArchiveSHA256='c'*64),
        'premise_unmanifested_json':lambda f:f['values'].update(extra={'passed':True}),
    }
    # A passing premise missing a returned witness is intentionally UNKNOWN,
    # so test that contract explicitly instead of classifying it as invalid.
    mutations.pop('missing_app_witness_stays_unknown')
    for name,mutation in mutations.items():
        def control(self,name=name,mutation=mutation):self.record_rejection(name,mutation)
        setattr(IndependentControls,'test_review_'+name,control)
    loader=unittest.TestLoader()
    original_suite=loader.loadTestsFromTestCase(tests.RuntimeControls)
    independent_suite=unittest.TestSuite(IndependentControls(name) for name in loader.getTestCaseNames(IndependentControls) if name.startswith('test_review_'))
    results={}
    for name,suite in [('producer',original_suite),('independent',independent_suite)]:
        with (attempt/(name+'.stdout.log')).open('x') as out,(attempt/(name+'.stderr.log')).open('x') as err,redirect_stdout(out),redirect_stderr(err):
            result=unittest.TextTestRunner(stream=err,verbosity=2).run(suite)
        results[name]={'testsRun':result.testsRun,'failures':[{'test':str(case),'traceback':failure} for case,failure in result.failures],'errors':[{'test':str(case),'traceback':error} for case,error in result.errors],'skipped':result.skipped,'passed':result.wasSuccessful()}
    (attempt/'control-results.json').write_bytes(stable(detail))
    (attempt/'suite-results.json').write_bytes(stable(results))
    historical=prepare.OLD/'runtime/captures'
    (attempt/'historical-capture-inventory.json').write_bytes(stable([{'name':p.name,'kind':'directory' if p.is_dir() else 'file'} for p in sorted(historical.iterdir())]))
    after={name:{'bytes':(ROOT/name).stat().st_size,'sha256':sha((ROOT/name).read_bytes())} for name in sorted(before)}
    (attempt/'frozen-inputs-after.json').write_bytes(stable(after))
    remaining=[str(path) for path in copies.iterdir() if path.is_dir()]
    outputs={str(p.relative_to(attempt)):{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(attempt.rglob('*')) if p.is_file()}
    receipt={'schema':'mixer.apple-focus-reference-runtime-independent-host-review.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(BASE/'run_review.py'),'--attempt',str(attempt_number)],'cwd':str(ROOT),'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),'hostUname':dict(zip(('sysname','nodename','release','version','machine'),os.uname())),'reviewerSourceSHA256':sha(Path(__file__).read_bytes()),'elapsedSeconds':time.monotonic()-started,'handoffSHA256':EXPECTED_HANDOFF,'packetSHA256':EXPECTED_PACKET,'sourceRevisionLabel':'ba9ad4372f94463ba4d363cdfd76dd565c96413f','sourceRevisionMeaning':'Inherited compile label; exact frozen SHA256 closure is authority; no Git query','sourceTreeSHA256':prepare.SOURCE,'productArchiveSHA256':prepare.PRODUCT,'frozenInputCount':len(before),'allFrozenInputsUnchanged':before==after,'results':results,'hostPythonSubprocesses':SPAWNS,'outputs':outputs,'cleanup':{'allOwnedTemporaryDirectoriesAbsent':not remaining,'remainingOwnedTemporaryDirectories':remaining,'nativeInstancesCreatedOrQueried':0,'nativeCommandsInvoked':0,'servicesStarted':0,'otherProjectsTouched':False,'sourceInspectionAndProducerCopiesRetainedForReview':True},'syntheticOnly':True,'nativeExecuted':False,'runtimeSelected':False,'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred'}
    (attempt/'receipt.json').write_bytes(stable(receipt))
    print(json.dumps({'producer':results['producer']['testsRun'],'producerPassed':results['producer']['passed'],'independent':results['independent']['testsRun'],'independentFailures':len(results['independent']['failures']),'independentErrors':len(results['independent']['errors']),'inputsUnchanged':before==after,'temporaryDirectoriesAbsent':not remaining,'nativeExecuted':False},sort_keys=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,required=True);main(parser.parse_args().attempt)
