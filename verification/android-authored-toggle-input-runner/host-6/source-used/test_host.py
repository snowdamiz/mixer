#!/usr/bin/env python3
"""Finite negative/positive controls. All fabricated results remain host-only."""
import argparse
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import support

RUN=support.load('authored_host_test_wrapper',support.HERE/'run.py')
ORACLE=support.load('authored_host_test_component',support.HERE/'supplement_oracle.py')
WORK=None

class DerivationTests(unittest.TestCase):
    def test_baseline_new_identity_and_exact_corrected_oracle(self):
        runner,source,_=RUN.load_runner()
        prior,original=support.prior()
        self.assertNotEqual(source,original)
        self.assertEqual(runner._pointer_validate_native.__code__.co_filename,str(support.TIMING/'oracle.py'))
        self.assertEqual(runner._pointer_validate_native.__code__.co_code,prior._pointer_validate_native.__code__.co_code)
        self.assertIs(runner._pointer_runtime_directory,support.runtime_directory)
        self.assertFalse(runner._ADAPTATION['authoredToggle']['sourceUnchanged'])
        self.assertTrue(runner._ADAPTATION['authoredToggle']['concreteSourceChanged'])
        self.assertEqual(runner.SOURCE_CLOSURE_SHA256,support.CLOSURE)
        self.assertEqual(runner.PACKAGE,'dev.mixer.android.coordinatorjoin')

    def test_supplement_has_distinct_package_entry_and_scope(self):
        runner,source,_=RUN.load_runner('supplement')
        self.assertEqual(runner.PACKAGE,'dev.mixer.android.authoredtoggle')
        self.assertIn('AuthoredToggleSupplementInstrumentation',source)
        self.assertNotIn("code, instrument = run('actual-native-pointer'",source)
        self.assertIn('fixture acknowledgements are not engine commits',source)

    def test_all_unchanged_baseline_native_injection_and_cleanup_source(self):
        _,original=support.prior();_,derived,_=RUN.load_runner()
        for start,end in [("        code, instrument = run('actual-native-pointer'",'    except BaseException as failure:'),('    finally:\n        if process is not None:','\n\nif __name__')]:
            before=original[original.index(start):original.index(end,original.index(start))]
            after=derived[derived.index(start):derived.index(end,derived.index(start))]
            if 'actual-native-pointer' in start:before=before.replace('native = json.loads(content)','native = _authored_parse(content)')
            self.assertEqual(before,after)

    def test_finite_delta_rejects_changed_or_duplicate_sites(self):
        _,source=support.prior()
        for changed in [source.replace("BUILDS = ROOT / 'verification/android-pointer-oracle-repair'","BUILDS = ROOT / 'wrong'"),source+"\nBUILDS = ROOT / 'verification/android-pointer-oracle-repair'\n"]:
            with self.assertRaises(ValueError):RUN.derive(changed,'baseline')

    def test_old_cli_rejected_without_dispatch(self):
        with patch.object(sys,'argv',['run.py','--build','candidate-5','--attempt','runtime-90001']),patch('sys.stderr',new=io.StringIO()):
            with self.assertRaises(SystemExit):RUN.main()

    def test_no_dispatch_switch_never_enters_host_or_runtime(self):
        with patch.object(sys,'argv',['run.py','--build','candidate-3','--attempt','runtime-90002']),patch.object(support,'runtime_directory',side_effect=AssertionError('must not enter')),patch('sys.stderr',new=io.StringIO()):
            with self.assertRaises(SystemExit):RUN.main()

    def test_contract_corruption_stops_before_prior_load(self):
        with patch.object(RUN,'CONTRACT_SHA256','0'*64),patch.object(support,'prior',side_effect=AssertionError('must not load')):
            with self.assertRaises(ValueError):RUN.load_runner()

    def test_tool_corruption_stops_before_prior_load(self):
        contract=support.read(support.HERE/'runner-contract.json');target=next(iter(contract['toolBindings']));original=support.sha
        with patch.object(support,'sha',side_effect=lambda p:'0'*64 if str(p)==target else original(p)),patch.object(support,'prior',side_effect=AssertionError('must not load')):
            with self.assertRaises(ValueError):RUN.load_runner()

    def test_strict_json_rejects_duplicate_identity(self):
        with self.assertRaises(ValueError):support.read_bytes(b'{"apkSHA256":"a","apkSHA256":"b"}')

    def test_output_paths_reject_reuse_traversal_and_symlinks(self):
        here=WORK/'containment';here.mkdir();runtime=here/'runtime';runtime.mkdir();(runtime/'runtime-1').mkdir()
        with patch.object(support,'HERE',here):
            for name in ('../runtime-2','runtime-01','runtime-0','runtime-1','runtime/runtime-2','/tmp/runtime-2'):
                with self.assertRaises(ValueError):support.runtime_directory(name)
            self.assertEqual(support.runtime_directory('runtime-2'),runtime/'runtime-2')
            link=runtime/'link';link.symlink_to(here/'x')
            with self.assertRaises(ValueError):support.runtime_directory('runtime-2')
            link.unlink()

    def test_exact183_inventories(self):
        for variant in ('baseline','supplement'):
            objects=support.inventory(variant)
            self.assertEqual(len(objects),183);self.assertEqual(sum(n.startswith('production-classes/') for n in objects),159)
            self.assertEqual(sum(n.startswith('apk/lib/') for n in objects),18)

    def test_archive_path_substitution_duplicate_and_size_drift_reject(self):
        import tarfile
        for index,names in enumerate((['../x'],['x','x'],['x'])):
            path=WORK/('archive-'+str(index)+'.tar.gz')
            with tarfile.open(path,'w:gz') as z:
                for name in names:
                    info=tarfile.TarInfo(name);info.size=1;z.addfile(info,io.BytesIO(b'x'))
            expected={'x':support.data_bind(b'xx' if index==2 else b'x')}
            with self.assertRaises(ValueError):list(support.verified_archive(path,expected))

class ComponentTests(unittest.TestCase):
    def fixture(self,events=180):
        cases=[{'id':i,'name':name,'status':'passed-component-native','proposals':p,'fixtureAcknowledgements':a,'authoritativeCommits':None,'rawCheckedListenerCallbacks':None}for i,(name,p,a)in enumerate(ORACLE.expected_cases(),1)]
        rows=[{'name':n[:-4],'checked':False,'boundChecked':False,'proposals':0,'route':'UiAutomation.takeScreenshot after native idle','geometry':{'offCenter':100,'onCenter':166,'trackX':50}}for n in ORACLE.SCREENSHOTS]
        rows = [{'case':1,'route':'actual View.onTouchEvent component','action':2,'pointerCount':1,'pointerId':7,'x':100,'y':66,'eventTime':i+1,'returned':True,'nativeChecked':False,'boundChecked':False,'proposals':0,'fixtureAcknowledgements':0,'pressed':True} for i in range(max(0,events-18))] + rows
        rows.append({'finally':True,'pressed':False,'parentAcquired':1,'parentReleased':1})
        return {'schema':1,'status':'passed-component-only','failure':None,'scope':ORACLE.SCOPE,'rawCheckedListenerCallbacks':None,'authoritativeCommits':None,'apkSHA256':support.SUPPLEMENT_APK,'sourceClosureSHA256':support.SUPPLEMENT_CLOSURE,'cases':cases,'observations':rows,'assertions':300,'events':events,'durationMilliseconds':5000,'physicalPhones':'deferred disconnected','TalkBackServiceWorkflow':'NOT RUN'}
    def validate(self,native):return ORACLE.validate(native,WORK,{'apkSHA256':support.SUPPLEMENT_APK,'sourceClosureSHA256':support.SUPPLEMENT_CLOSURE})
    def test_exact_component_only_positive(self):
        self.assertIsNone(self.validate(self.fixture())['authoritativeCommits'])
    def test_false_engine_or_raw_callback_authority_rejects(self):
        for field in ('authoritativeCommits','rawCheckedListenerCallbacks'):
            value=self.fixture();value[field]=0
            with self.assertRaises(ValueError):self.validate(value)
    def test_case_omission_duplicate_reorder_and_bad_proposal_rejects(self):
        for mode in range(4):
            value=self.fixture()
            if mode==0:value['cases'].pop()
            elif mode==1:value['cases'][1]=value['cases'][0]
            elif mode==2:value['cases'].reverse()
            else:value['cases'][0]['proposals']=0
            with self.assertRaises(ValueError):self.validate(value)
    def test_boolean_negative_nonfinite_overbudget_counters_reject(self):
        for field in ('assertions','events','durationMilliseconds'):
            for n in (True,-1,float('nan'),float('inf'),99999999):
                value=self.fixture();value[field]=n
                with self.assertRaises(ValueError):self.validate(value)
    def test_changed_apk_or_source_rejects(self):
        for key in ('apkSHA256','sourceClosureSHA256'):
            value=self.fixture();value[key]='0'*64
            with self.assertRaises(ValueError):self.validate(value)
    def test_uncommitted_preview_and_cleanup_cannot_be_claimed(self):
        for change in ('preview','cleanup','nonfinite'):
            value=self.fixture()
            snapshot=next(r for r in value['observations'] if 'name' in r)
            if change=='preview':snapshot['checked']=True
            elif change=='cleanup':value['observations'][-1]['parentReleased']=0
            else:snapshot['geometry']['offCenter']=float('nan')
            with self.assertRaises(ValueError):self.validate(value)
    def test_511_declared_plus_history_one_accepts_512_declared_rejects(self):
        self.assertEqual(self.validate(self.fixture(events=511))['boundedConstructedMotionEvents'],512)
        with self.assertRaisesRegex(ValueError,'history MotionEvent'):self.validate(self.fixture(events=512))
    def test_direct_observation_and_worker_counter_mismatch_rejects(self):
        value=self.fixture();value['events']+=1
        with self.assertRaisesRegex(ValueError,'eighteen worker'):self.validate(value)
    def test_boolean_or_nonfinite_direct_touch_fields_reject(self):
        for key,v in [('case',True),('x',float('nan')),('eventTime',True),('proposals',True),('pointerId',True)]:
            value=self.fixture();value['observations'][0][key]=v
            with self.assertRaises(ValueError):self.validate(value)
    def test_instrumentation_result_hash_must_bind_export(self):
        payload=json.dumps(self.fixture()).encode()
        def command(name,argv,**kw):return (0,payload)
        with self.assertRaisesRegex(ValueError,'export binding'):ORACLE.collect(command,[], 'private',WORK,{},0,b'INSTRUMENTATION_CODE: -1')

def main():
    global WORK
    parser=argparse.ArgumentParser();parser.add_argument('--work',required=True);parser.add_argument('--results',required=True);args=parser.parse_args();WORK=Path(args.work);WORK.mkdir()
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in (DerivationTests,ComponentTests)])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    support.save(args.results,{'schema':1,'status':'passed'if result.wasSuccessful()else'failed','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'syntheticOnly':True,'nativeCommands':0})
    raise SystemExit(0 if result.wasSuccessful()else 1)

if __name__=='__main__':main()
