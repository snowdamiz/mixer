#!/usr/bin/env python3
"""Independent mocked dispatch/source guards and non-authoritative telemetry controls."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,MagicMock
import copy,hashlib,importlib.util,json,sys,unittest
H=Path(__file__).resolve().parent;P=H.parent/'swift-current-attribution-full-preparation';R=H.parent.parent
sys.path.insert(0,str(H/'input-snapshots'))
spec=importlib.util.spec_from_file_location('independent_prepared_driver',H/'input-snapshots/diagnostic.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
load=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
class DispatchReached(Exception):pass

class IndependentHostControls(unittest.TestCase):
    def guarded(self,changes=None,marker_exists=False,missing_selection=False):
        here=H/'unmaterialized-guard-fixture';binary=here/'bin/exact-tests';reactor=here/'bound-data-only.wasm'
        info=load(P/'binary.json');retained=copy.deepcopy(info['retained']);retained['path']=retained['resolvedPath']=str(binary)
        info['retained']=retained
        selection=load(P/'root-selection-template.json')
        selection['exactCommandSelected']=True
        selection['outerCommand']=['python3','-B',str((here/'diagnostic.py').relative_to(R)),'target']
        selection['argv']=[str(binary),driver.PREFIX+'exact_reactor_target_once','--exact','--nocapture','--test-threads=1']
        if changes:selection.update(copy.deepcopy(changes))
        digests=load(P/'prepared-seal.json')['files']
        def mock_sha(p):
            p=Path(p)
            if p==binary:return retained['sha256']
            if p==reactor or p.name=='fieldlog-reactor.wasm':return driver.REACTOR_HASH
            return digests[str(p.relative_to(here))]
        def mock_read(p):
            if Path(p).name=='binary.json':return copy.deepcopy(info)
            if Path(p).name=='root-selection.json':
                if missing_selection:raise FileNotFoundError('independent missing selection')
                return copy.deepcopy(selection)
            raise AssertionError('unexpected read '+str(p))
        def mock_identity(p):
            if Path(p)==binary:return copy.deepcopy(retained)
            return {'path':str(p),'sha256':mock_sha(p) if Path(p).name!='root-selection.json' else 'review-only-selection'}
        record=MagicMock(side_effect=DispatchReached('intercepted before subprocess'))
        opened=MagicMock();opened.__enter__.return_value=MagicMock()
        with patch.multiple(driver,HERE=here,ROOT=R,BINARY=binary,REACTOR=reactor,SCRATCH=here/'owned-scratch'),patch.object(driver,'read',side_effect=mock_read),patch.object(driver,'sha',side_effect=mock_sha),patch.object(driver,'identity',side_effect=mock_identity),patch.object(driver,'environment',return_value={}),patch.object(driver.shutil,'copyfile'),patch.object(driver.Path,'stat',return_value=SimpleNamespace(st_size=53_777_114)),patch.object(driver.Path,'exists',side_effect=lambda:marker_exists),patch.object(driver.Path,'open',return_value=opened),patch.object(driver,'record_command',record):
            try:driver.execute(True)
            except BaseException as error:return error,record,opened
        self.fail('guarded dispatch unexpectedly returned')

    def test_exact_selection_reaches_only_intercepted_dispatch(self):
        error,record,opened=self.guarded();self.assertIsInstance(error,DispatchReached);self.assertEqual(record.call_count,1)
        argv=record.call_args.args[1]
        self.assertEqual(argv[1],driver.PREFIX+'exact_reactor_target_once');self.assertEqual(argv[2:],['--exact','--nocapture','--test-threads=1'])
        self.assertEqual(record.call_args.args[2],170)
        self.assertEqual(opened.__enter__.return_value.write.call_count,1)

    def test_each_exact_selection_binding_rejects_drift(self):
        cases={'exactCommandSelected':False,'baselineClosure':'bad','harnessSHA256':'bad','driverSHA256':'bad','binarySHA256':'bad','targetBytes':1,'targetSHA256':'bad','inputBindingSHA256':'bad','maxTargetAttempts':2,'sourceManifestSHA256':'bad','telemetryClassifierSHA256':'bad','outputContractSHA256':'bad','outerCommand':[],'argv':[],'boundEvidence':{'adapter.rs':'bad'}}
        for key,value in cases.items():
            with self.subTest(binding=key):
                error,record,_=self.guarded({key:value});self.assertIsInstance(error,AssertionError);record.assert_not_called()
        print('REVIEW_GUARD independent_binding_drift_rejections='+str(len(cases)))

    def test_missing_selection_and_existing_marker_refuse_dispatch(self):
        error,record,_=self.guarded(missing_selection=True);self.assertIsInstance(error,FileNotFoundError);record.assert_not_called()
        error,record,_=self.guarded(marker_exists=True);self.assertIsInstance(error,AssertionError);record.assert_not_called()

    def test_exact_source_manifest_refuses_drift(self):
        manifest=load(P/'copied-build-manifest.json');baseline=load(P/'baseline-manifest.json')
        append='\n// Isolated diagnostic only; baseline production bytes are unchanged.\ninclude!('+json.dumps(str(P/'harness.rs'))+');\n'
        with patch.multiple(driver,HERE=P,CANDIDATE=H.parent/'swift-cache-current-attribution-observer',APPEND=append):
            reconstructed=driver.reconstructed_source()
        self.assertEqual({n:hashlib.sha256(b).hexdigest() for n,b in reconstructed.items()},manifest)
        def read(p):return baseline if Path(p).name=='baseline-manifest.json' else manifest
        with patch.object(driver,'read',side_effect=read),patch.object(driver,'reconstructed_source',return_value=reconstructed),patch.object(driver,'source_manifest',return_value=manifest):self.assertEqual(driver.assert_baseline(),manifest)
        changed=dict(manifest);changed['src/experimental_swift_reactor/cache.rs']='bad'
        with patch.object(driver,'read',side_effect=read),patch.object(driver,'reconstructed_source',return_value=reconstructed),patch.object(driver,'source_manifest',return_value=changed):self.assertRaises(AssertionError,driver.assert_baseline)

    def test_invalid_telemetry_cannot_change_original_command_result(self):
        binary=load(P/'binary.json');original=[{'event':'runtime_failure','payload':{'kind':'WorkExhausted','attempted':64000001,'limit':64000000}},{'event':'cleanup_empty','payload':True}]
        saved=[]
        for command_passed in (False,True):
            saved.clear()
            with patch.object(driver,'read',return_value=binary),patch.object(driver,'identity',return_value=binary['retained']),patch.object(driver,'sha',return_value=binary['harnessSHA256']),patch.object(driver,'environment',return_value={}),patch.object(driver,'record_command',return_value=({'passed':command_passed},H/'not-read.stdout',H/'not-read.stderr')),patch.object(driver,'events',return_value=copy.deepcopy(original)),patch.object(driver,'save',side_effect=lambda name,value:saved.append((name,copy.deepcopy(value)))),patch.object(driver.telemetry,'classify',return_value={'status':'invalid_or_missing','originalResultReplaced':False}):
                result=driver.execute(False)
            self.assertEqual(result,0 if command_passed else 1)
            self.assertTrue(saved[-2][0].endswith('-result.json'));self.assertTrue(saved[-1][0].endswith('-telemetry.json'))
            self.assertEqual(saved[-2][1]['commandPassed'],command_passed);self.assertEqual(saved[-2][1]['firstFailure'],original[0])
        print('REVIEW_AUTHORITY result_persisted_before_telemetry=true original_failure_preserved=true telemetry_does_not_authorize_command=true')

    def test_failure_prefix_and_zero_snapshot_validation_failure(self):
        original=load(H/'parser-original-events.json')
        telemetry=driver.telemetry
        with patch.object(driver.telemetry,'LABELS',telemetry.LABELS):
            empty=H/'owned-tmp/empty.stdout';empty.write_bytes(b'')
            result=telemetry.classify(empty,[{'event':'validation_failure','payload':{'kind':'bad_module'}}])
            self.assertEqual(result['status'],'not_started');self.assertFalse(result['originalResultReplaced'])
            result=telemetry.classify(empty,original);self.assertEqual(result['status'],'invalid_or_missing')
        empty.unlink()

if __name__=='__main__':unittest.main(verbosity=2)
