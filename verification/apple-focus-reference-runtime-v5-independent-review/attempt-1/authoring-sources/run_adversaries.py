"""Finite independent V5 controls using actual frozen importer and adapter bytes."""
import ast
import copy
import datetime
from decimal import Context,localcontext
from fractions import Fraction
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock

import prepare
import importer as i
import frozen_inputs
import test_importer as producer

BASE=Path(__file__).resolve().parent
OUT=BASE/'adversary-output';OUT.mkdir()
COUNTS={}
ADAPTERS=[]
FINDINGS=[]
stable=lambda v:(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
sha=lambda b:hashlib.sha256(b).hexdigest()
def count(label,n=1):COUNTS[label]=COUNTS.get(label,0)+n

class IndependentControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        producer.RuntimeControls.setUpClass()
        cls.ref=producer.RuntimeControls('test_001_one_complete_strict_original_pass_is_diagnostic_only')
    @classmethod
    def tearDownClass(cls):producer.RuntimeControls.tearDownClass()

    def adapter(self,label,root=None,start=None,finish=None,token=None,mutate=None,accepted=True):
        f=self.ref.fixture()
        if root is not None:f['root']['selectedAtUTC']=root
        with tempfile.TemporaryDirectory(prefix='independent-v5-adversary-',dir=prepare.BASE) as tmp:
            sandbox=Path(tmp);captured=False;called=False;calls=[];n=None
            try:
                n,invoke,calls,h=self.ref.adapter_namespace(f,sandbox)
                summary=i.stable(f['summary'])
                for field,value in [('startTime',start),('finishTime',finish)]:
                    if value is not None:
                        old=('"'+field+'": '+str(f['summary'][field])).encode();self.assertEqual(summary.count(old),1)
                        summary=summary.replace(old,('"'+field+'": '+value).encode())
                if token is not None:
                    manifest=sandbox/'runtime/attachments/manifest.json';raw=manifest.read_bytes();self.assertEqual(raw.count(b'1792893615.0'),1)
                    raw=raw.replace(b'1792893615.0',token.encode());manifest.write_bytes(raw)
                    path=sandbox/'runtime/attachment-export.json';export=i.parse(path.read_bytes())
                    export['files']['manifest.json']={'bytes':len(raw),'sha256':sha(raw)};path.write_bytes(i.stable(export))
                def returns(commands,argv,**kwargs):
                    actual=invoke(commands,argv,**kwargs)
                    return (actual[0],summary.decode(),actual[2]) if argv[4]=='summary' else actual
                n['capture_official'](object(),returns,h,sandbox);captured=True
                observer=f['session']/'command-observer'
                for name,data in f['streams'].items():(observer/(name+'.log')).write_bytes(data)
                bridge=types.SimpleNamespace(failures=[],settings=types.SimpleNamespace(summary=lambda:{'syntheticOnly':True}))
                inputs=dict(base=sandbox,h=h,oracle=self.ref.oracle,setup_ready=lambda _:True,scope=None,bridge=bridge,
                            xctest_exit=0,failure=None,cleanup_results=f['cleanup'])
                if mutate:mutate(n,inputs)
                called=True;result=n['runtime_summary'](**inputs)
            except (ValueError,KeyError,TypeError,OverflowError,RecursionError) as error:
                result={'diagnosticOutcome':'rejected-before-summary','error':type(error).__name__+': '+str(error)}
            record={'label':label,'root':f['root']['selectedAtUTC'],'start':start,'finish':finish,'token':token,
                    'captured':captured,'summaryCalled':called,'toolReturnCalls':len(calls),'expectedAccepted':accepted,'result':result}
            ADAPTERS.append(record)
            self.assertEqual(result['diagnosticOutcome']=='one-strict-original-verdict-passed',accepted,record)
            if called:self.assertEqual(result['schema'],'mixer.apple-focus-reference-runtime.5')
            if accepted:self.assertEqual(result['keyInjectionCount'],1)
            else:self.assertIsNone(result.get('keyInjectionCount'))
            return record

    def test_01_canonical_root_equivalences_are_exact(self):
        baseline='2026-10-25T02:00:00.999999+00:00';expected=1792893600999999000
        tokens=[baseline,'2026-10-24T22:00:00.999999-04:00','2026-10-25T07:45:00.999999+05:45',
                '2026-10-24T22:30:00.999999-03:30','2026-10-26T01:59:00.999999+23:59',
                '2026-10-24T02:01:00.999999-23:59']
        for token in tokens:
            with self.subTest(token=token):self.assertEqual(i.datetime_ns(token),expected);count('exactCanonicalOffsetForms')
        for token,value in [('1970-01-01T00:00:00+00:00',0),('1970-01-01T00:00:00.000001+00:00',1000),
                            ('1969-12-31T23:59:59.999999+00:00',-1000),('2000-02-29T00:00:00+00:00',951782400000000000)]:
            self.assertEqual(i.datetime_ns(token),value);count('exactCanonicalCalendarForms')

    def test_02_invalid_precision_offsets_unicode_and_calendar_reject(self):
        roots=['2026-10-25T02:00:00.000000001+00:00','2026-10-25T02:00:00.0000000000000001+00:00',
               '2026-10-25T02:00:00.0000000+00:00','2026-10-25T02:00:00.123+00:00',
               '2026-10-25T02:00:00+00:00:00.000000001','2026-10-25T02:00:00-04:00:01',
               '2026-10-25T02:00:00+24:00','2026-10-25T02:00:00+00:60','2026-10-25T02:00:00-00:00',
               '2026-10-25T02:00:00Z','2026-10-25T02:00:00+0000','2026-10-25T02:00:00+00',
               '2026-10-25 02:00:00+00:00','2026-10-25T02:00:00,123456+00:00',
               '2026-10-25T02:00:00.１２３４５６+00:00','٢٠٢٦-10-25T02:00:00+00:00',
               '2026-10-25T02:00:00+00:00\n','2026-10-25T02:00:00+00:00\x00',
               '2026-02-29T02:00:00+00:00','2100-02-29T00:00:00+00:00','2026-04-31T00:00:00+00:00',
               '2026-10-25T23:60:00+00:00','2026-10-25T23:59:60+00:00','2026-10-25T24:00:00+00:00']
        for token in roots:
            with self.subTest(token=token),self.assertRaises(ValueError):i.datetime_ns(token)
            count('invalidRootForms')

    def test_03_lexical_rejection_is_before_datetime_parsing(self):
        calls=[];real=datetime.datetime
        class Spy(real):
            @classmethod
            def fromisoformat(cls,value):calls.append(value);return real.fromisoformat(value)
        with mock.patch.object(i.datetime,'datetime',Spy):
            for token in ['2026-10-25T02:00:00.000000001+00:00','2026-10-25T02:00:00+00:00:00.1']:
                with self.assertRaises(ValueError):i.datetime_ns(token)
        self.assertEqual(calls,[]);count('preParserRejections',2)

    def test_04_freshness_microsecond_endpoints_and_offset_equivalence(self):
        real=datetime.datetime
        class Clock(real):
            @classmethod
            def now(cls,tz=None):return real(2026,10,25,2,0,0,999999,tzinfo=datetime.timezone.utc)
        cases=[('2026-10-25T02:00:00.999999+00:00',True),('2026-10-24T22:00:00.999999-04:00',True),
               ('2026-10-25T01:55:00.999999+00:00',True),('2026-10-24T21:55:00.999999-04:00',True),
               ('2026-10-25T02:00:01.000000+00:00',False),('2026-10-25T01:55:00.999998+00:00',False)]
        with mock.patch.object(i.datetime,'datetime',Clock):
            for token,accepted in cases:
                root=self.ref.fixture()['root'];root['selectedAtUTC']=token
                if accepted:self.assertEqual(i.validate_root(root,fresh=True),root)
                else:
                    with self.assertRaises(ValueError):i.validate_root(root,fresh=True)
                count('freshnessEndpoints')

    def test_05_finite_exact_rational_scalar_matrix(self):
        for scale in range(0,19):
            for seed in range(1,15):
                value=seed*731+19;token=str(value)+'e-'+str(scale)
                exact=Fraction(token)*1_000_000_000
                d=i.decimal_document(token.encode())
                if exact.denominator==1:self.assertEqual(i.decimal_timestamp_ns(d),exact.numerator);count('exactRationalScalars')
                else:
                    with self.assertRaises(ValueError):i.decimal_timestamp_ns(d)
                    count('trueSubNanosecondScalars')
        for token in ['1792893615.000000000000000000','179289361500000000000e-11','0e-1000000','-0.000000000000']:
            self.assertEqual(i.decimal_timestamp_ns(i.decimal_document(token.encode())),int(Fraction(token)*1_000_000_000));count('zeroTrailingExponentForms')

    def test_06_actual_adapter_root_and_summary_lower_endpoint(self):
        root='2026-10-25T02:00:01.000001+00:00'
        self.adapter('root-equal',root=root,start='1792893601.000001000')
        self.adapter('root-older-one-ns',root=root,start='1792893601.000000999',accepted=False)
        self.adapter('root-forward-one-ns',root=root,start='1792893601.000001001')

    def test_07_actual_adapter_window_upper_endpoint(self):
        root='2026-10-24T22:00:00.999999-04:00'
        self.adapter('finish-equal',root=root,finish='1792894260.999999000')
        self.adapter('finish-after-one-ns',root=root,finish='1792894260.999999001',accepted=False)

    def test_08_actual_adapter_attachment_exact_budget(self):
        self.adapter('premise-nine-exact',token='1792893619.0000000000000')
        self.adapter('premise-nine-over-one-ns',token='1792893619.000000001',accepted=False)
        self.adapter('premise-nine-over-sub-ns',token='1792893619.0000000000000000001',accepted=False)

    def test_09_actual_configure_root_never_accepts_unsupported_time(self):
        for index,root in enumerate(['2026-10-25T02:00:00.000000001+00:00','2026-10-25T02:00:00+00:00:00.000001',
                                     '2026-10-25T02:00:00.00000+00:00']):
            record=self.adapter('early-invalid-root-'+str(index),root=root,accepted=False)
            self.assertFalse(record['captured']);self.assertFalse(record['summaryCalled']);self.assertEqual(record['toolReturnCalls'],0)

    def test_10_decimal_flags_traps_and_full_profile_unchanged(self):
        prototype=Context();signals=list(prototype.flags)
        for trap in [False,True]:
            for active_flag in [None,'all']+signals:
                context=Context(prec=1,Emin=0,Emax=0,clamp=1,capitals=0)
                for s in signals:context.traps[s]=trap;context.flags[s]=(active_flag=='all' or active_flag is s)
                with localcontext(context) as current:
                    before=repr(current)
                    for token in [b'0',b'-0.0e-1000',b'1792893615.000000000000',b'123e-9']:
                        i.decimal_timestamp_ns(i.decimal_document(token));self.assertEqual(repr(current),before);count('ambientDecimalSuccessfulDocuments')
                    for token in [b'0e9999999999999999999',b'0e-1999999999999999998',b'1e-1000000',b'1e309',b'NaN',b'{"x":1,"x":2}']:
                        with self.assertRaises(ValueError):i.decimal_timestamp_ns(i.decimal_document(token))
                        self.assertEqual(repr(current),before);count('ambientDecimalRejectedDocuments')

    def test_11_actual_adapter_preserves_hostile_decimal_profile(self):
        for traps in [False,True]:
            c=Context(prec=1,Emin=0,Emax=0)
            for s in c.flags:c.flags[s]=True;c.traps[s]=traps
            with localcontext(c) as current:
                before=repr(current)
                self.adapter('decimal-'+str(traps)+'-success',token='1792893615.0000000000000')
                self.assertEqual(repr(current),before)
                self.adapter('decimal-'+str(traps)+'-reject',token='0e9999999999999999999',accepted=False)
                self.assertEqual(repr(current),before)

    def test_12_actual_summary_early_returns_are_schema5(self):
        mutations=[('no-cleanup',lambda n,p:p.update(cleanup_results=None)),('no-capture',lambda n,p:n.update(_OFFICIAL=None)),
                   ('command-failure',lambda n,p:p.update(failure='independent failure')),('bridge-none',lambda n,p:p.update(bridge=None)),
                   ('settings-incomplete',lambda n,p:p.update(setup_ready=lambda _:False)),('bridge-failure',lambda n,p:p['bridge'].failures.append('independent failure')),
                   ('capture-run-mismatch',lambda n,p:n['_OFFICIAL'].update(runID='mismatch'))]
        for name,change in mutations:self.adapter('schema-'+name,mutate=change,accepted=False)
        f=self.ref.fixture()
        with tempfile.TemporaryDirectory(prefix='independent-v5-schema-',dir=prepare.BASE) as tmp:
            n,_,_,h=self.ref.adapter_namespace(f,Path(tmp))
            result=n['runtime_summary'](Path(tmp),h,None,None,None,None,None,None,None)
            self.assertEqual(result['schema'],'mixer.apple-focus-reference-runtime.5');self.assertIsNone(result['actualNativeInputActions'])
        count('schema5EarlyReturns',8)

    def test_13_schema_and_simulator_name_reject_before_fixture_writes(self):
        for version in [3,4]:
            for field in ['schema','name']:
                f=self.ref.fixture()
                if field=='schema':f['root']['schema']='mixer.apple-focus-reference-root-selection.'+str(version)
                else:f['root']['ownedSimulatorIdentity']['name']='MixerFocusReferenceV'+str(version)+'-synthetic'
                with tempfile.TemporaryDirectory(prefix='independent-v5-schema-',dir=prepare.BASE) as tmp:
                    with self.assertRaises(ValueError):self.ref.adapter_namespace(f,Path(tmp))
                    self.assertEqual(list(Path(tmp).iterdir()),[])
                count('oldSchemaNameEarlyRejections')

    def test_14_live_workspace_reads_and_scans_are_denied(self):
        live=Path(os.environ['MIXER_V5_LIVE_ROOT'])
        for path in [live/'AGENTS.md',live/'verification/apple-focus-diagnostic-runtime-v1/runtime/captures/0000-settings-0000.json']:
            with self.assertRaises(PermissionError):path.read_bytes()
        with self.assertRaises(PermissionError):list((live/'verification/apple-focus-diagnostic-runtime-v1/runtime/captures').iterdir())
        count('liveWorkspaceReadScanDenials',3)

    def test_15_exact_selected_source_changes_and_276_supplement(self):
        p=prepare.ROOT/'verification/apple-focus-reference-runtime-v4'
        manifest=json.loads((p/'runtime-source-manifest.json').read_bytes())
        self.assertEqual(sha((p/'runtime-sources.tar.gz').read_bytes()),manifest['archive']['sha256'])
        with tarfile.open(p/'runtime-sources.tar.gz','r:gz') as tar:
            previous={m.name.removeprefix('selected/'):tar.extractfile(m).read() for m in tar.getmembers()}
        self.assertEqual(set(previous),set(self.ref.derived))
        changed=sorted(n for n in previous if previous[n]!=self.ref.derived[n])
        self.assertEqual(changed,['importer.py','join_support.py']);count('unchangedSelectedFiles',len(previous)-len(changed))
        meta=json.loads((prepare.BASE/'input-bindings.json').read_bytes());supp=meta['supplementalSettings']
        self.assertEqual(len(supp['members']),276);self.assertEqual(sum(v['bytes'] for v in supp['members'].values()),1190150)
        self.assertEqual(sha(stable(supp['members'])),'c5c19c9aa0520f92f904f698823a90994e89166f3693df07ced052e9e38aeb68')
        for name,want in supp['members'].items():self.assertEqual(frozen_inputs.row(prepare.ROOT/meta['storage'][name]),want)
        count('exactSupplementalJournalFiles',276)

    def test_16_missing_changed_and_unlisted_fixtures_fail_closed(self):
        folder=prepare.ROOT/'verification/apple-focus-diagnostic-runtime-v1/runtime/captures'
        path=folder/'0000-settings-0275.json';raw=path.read_bytes();mode=path.stat().st_mode&0o777
        try:
            path.unlink()
            with self.assertRaises((AssertionError,FileNotFoundError)):frozen_inputs.verify()
            path.write_bytes(raw+b'\n');path.chmod(mode)
            with self.assertRaises(AssertionError):frozen_inputs.verify()
        finally:path.write_bytes(raw);path.chmod(mode)
        extra=folder/'0000-settings-independent-unlisted.json'
        try:
            extra.write_bytes(b'{}\n')
            with self.assertRaises(AssertionError):frozen_inputs.verify()
        finally:extra.unlink()
        self.assertEqual(len(frozen_inputs.verify()),2393);count('closedFixtureMutationRejections',3)

    def test_17_replay_helper_only_defers_actual_canonical_time_error(self):
        import replay_v4_review
        source=inspect.getsource(replay_v4_review.run)
        self.assertIn("if str(error)!='Canonical exactly representable root ISO timestamp required':raise",source)
        helper=inspect.getsource(producer.RuntimeControls.adapter_namespace)
        old="    namespace['configure_root'](f['root'])\n"
        self.assertEqual(helper.count(old),1)
        # Independent actual configure probes: canonical-time error, schema/name
        # errors and calendar errors are distinct; only the documented two
        # unsupported lexical roots match the replay's exact routing predicate.
        for kind in ['time','schema','name','calendar']:
            f=self.ref.fixture()
            if kind=='time':f['root']['selectedAtUTC']='2026-10-25T02:00:00.000000001+00:00'
            elif kind=='schema':f['root']['schema']='mixer.apple-focus-reference-root-selection.4'
            elif kind=='name':f['root']['ownedSimulatorIdentity']['name']='MixerFocusReferenceV4-rejected'
            else:f['root']['selectedAtUTC']='2026-02-29T02:00:00+00:00'
            with tempfile.TemporaryDirectory(prefix='independent-v5-helper-',dir=prepare.BASE) as tmp:
                try:self.ref.adapter_namespace(f,Path(tmp))
                except ValueError as e:self.assertEqual(str(e)=='Canonical exactly representable root ISO timestamp required',kind=='time')
                else:self.fail('Invalid root accepted')
            count('actualConfigureRoutingPredicates')

    def test_18_v5_namespace_dispatch_finding_proved_by_actual_select(self):
        outcomes=[]
        for version in [5,4]:
            f=self.ref.fixture();output=prepare.BASE/('native-run-v'+str(version)+'-'+f['root']['runID'])
            self.assertFalse(output.exists())
            try:
                n,_,_,h=self.ref.adapter_namespace(f,output);(f['session']/'session.xcresult').rmdir()
                called=[]
                def original(h,argv,session):called.append(True);n['_selected']={'session':session}
                n['_ORIGINAL_SELECT']=original
                try:n['select_command'](h,i.command_argv(f['root'],f['session']),f['session']);error=None
                except ValueError as e:error=str(e)
                outcomes.append({'outputPrefix':'native-run-v'+str(version)+'-','actualConfigureRootAccepted':True,'actualSelectAccepted':error is None,'originalSelectorCalls':len(called),'error':error})
            finally:shutil.rmtree(output)
        self.assertFalse(outcomes[0]['actualSelectAccepted']);self.assertTrue(outcomes[1]['actualSelectAccepted'])
        tree=ast.parse((prepare.BASE/'prepare.py').read_bytes())
        dispatch=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='dispatch')
        assignment=next(n for n in ast.walk(dispatch) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='output' for t in n.targets))
        expression=ast.unparse(assignment.value)
        self.assertIn('native-run-v4-',expression)
        finding={'id':'V5-001','severity':'blocking-fresh-native-selection','summary':'Frozen V5 dispatch creates native-run-v4 and selected actual adapter rejects native-run-v5',
                 'dispatchOutputExpression':expression,'actualConfigureAndSelectProbes':outcomes,'nativeExecuted':False,'syntheticOnly':True}
        FINDINGS.append(finding);(OUT/'namespace-finding.json').write_bytes(stable(finding))

    def test_19_no_native_or_ga_credit_from_actual_success(self):
        row=self.adapter('qualification-remains-false')
        for field in ['runPassed','completeCaseSet','cursorCompletionCredit','fullSixCaseQualification','nativeKeyboardQualification','carrierAccepted','gaAccepted']:
            self.assertIs(row['result'][field],False)

def main():
    before=frozen_inputs.verify()
    with (OUT/'unittest.log').open('w') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls))
    after=frozen_inputs.verify()
    receipt={'schema':'mixer.apple-focus-reference-runtime-v5-independent-adversaries.1','testsRun':result.testsRun,
             'testsPassed':result.testsRun-len(result.failures)-len(result.errors),'failures':[{'name':str(t),'traceback':tb} for t,tb in result.failures],
             'errors':[{'name':str(t),'traceback':tb} for t,tb in result.errors],'skipped':result.skipped,'controlsPassed':result.wasSuccessful(),
             'finiteCaseCounts':COUNTS,'adapterAttempts':len(ADAPTERS),'actualSummaryCalls':sum(r['summaryCalled'] for r in ADAPTERS),
             'liveWorkspaceDeniedEvents':INDEPENDENT_DENIED,'frozenInputsUnchanged':before==after,'findings':FINDINGS,'nativeExecuted':False,'physicalPhones':'disconnected-deferred'}
    (OUT/'adapter-results.json').write_bytes(stable(ADAPTERS));(OUT/'receipt.json').write_bytes(stable(receipt))
    print(json.dumps({k:receipt[k] for k in ['testsRun','testsPassed','controlsPassed','adapterAttempts','actualSummaryCalls','finiteCaseCounts','findings']},indent=2))
    if not result.wasSuccessful():raise SystemExit(1)

if __name__=='__main__':main()
