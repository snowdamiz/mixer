"""Focused V5 repair controls; all tool returns and observations are synthetic."""
import copy
import datetime
from decimal import Context,localcontext
from pathlib import Path
import shutil
import tempfile
import types
import unittest
from unittest import mock
import frozen_inputs
import prepare
import test_importer as frozen

i=frozen.i
OUT=None

class V5Controls(unittest.TestCase):
    records=[]
    @classmethod
    def setUpClass(cls):
        frozen.RuntimeControls.setUpClass()
        cls.ref=frozen.RuntimeControls('test_001_one_complete_strict_original_pass_is_diagnostic_only')
        cls.records=[]
    @classmethod
    def tearDownClass(cls):frozen.RuntimeControls.tearDownClass()

    def adapter(self,label,root=None,token=None,start=None,finish=None,expected=True,mutate=None):
        f=self.ref.fixture()
        if root is not None:f['root']['selectedAtUTC']=root
        with tempfile.TemporaryDirectory(prefix='v5-adapter-',dir=prepare.BASE) as tmp:
            sandbox=Path(tmp);captured=False;called=False;namespace=None
            try:
                namespace,invoke,_,h=self.ref.adapter_namespace(f,sandbox)
                manifest=sandbox/'runtime/attachments/manifest.json';raw=manifest.read_bytes()
                if token is not None:
                    self.assertEqual(raw.count(b'1792893615.0'),1)
                    raw=raw.replace(b'1792893615.0',token.encode());manifest.write_bytes(raw)
                    p=sandbox/'runtime/attachment-export.json';export=i.parse(p.read_bytes())
                    export['files']['manifest.json']={'bytes':len(raw),'sha256':i.digest(raw)};p.write_bytes(i.stable(export))
                summary=i.stable(f['summary'])
                for name,value in [('startTime',start),('finishTime',finish)]:
                    if value is not None:
                        old=('"'+name+'": '+str(f['summary'][name])).encode()
                        self.assertEqual(summary.count(old),1);summary=summary.replace(old,('"'+name+'": '+value).encode())
                def returns(command,argv,**kwargs):
                    r=invoke(command,argv,**kwargs)
                    return (r[0],summary.decode(),r[2]) if argv[4]=='summary' else r
                namespace['capture_official'](object(),returns,h,sandbox);captured=True
                observer=f['session']/'command-observer'
                for name,payload in f['streams'].items():(observer/(name+'.log')).write_bytes(payload)
                bridge=types.SimpleNamespace(failures=[],settings=types.SimpleNamespace(summary=lambda:{'syntheticOnly':True}))
                inputs=dict(base=sandbox,h=h,oracle=self.ref.oracle,setup_ready=lambda _:True,scope=None,bridge=bridge,
                            xctest_exit=0,failure=None,cleanup_results=f['cleanup'])
                if mutate:mutate(namespace,inputs)
                called=True;result=namespace['runtime_summary'](**inputs)
            except (KeyError,ValueError,TypeError,OverflowError,RecursionError) as error:
                result={'schema':'host-v5-rejected-before-summary','diagnosticOutcome':'invalid-or-incomplete-evidence',
                        'keyInjectionCount':None,'failure':type(error).__name__+': '+str(error)}
            record={'label':label,'root':copy.deepcopy(f['root']),'rawToken':token,'rawSummaryStart':start,'rawSummaryFinish':finish,
                    'expectedAccepted':expected,'actualAdapterCaptured':captured,'actualRuntimeSummaryCalled':called,'result':result,
                    'syntheticOnly':True,'nativeExecuted':False}
            self.records.append(record)
            destination=OUT/label;destination.mkdir()
            (destination/'control.json').write_bytes(i.stable(record))
            if (sandbox/'runtime').exists():shutil.copytree(sandbox/'runtime',destination/'runtime')
            if called:self.assertTrue(result['schema'].endswith('.5'),result)
            self.assertEqual(result['diagnosticOutcome']=='one-strict-original-verdict-passed',expected,record)
            if expected:self.assertEqual(result['keyInjectionCount'],1,record)
            else:self.assertIsNone(result.get('keyInjectionCount'),record)
            return result

    def test_01_exact_canonical_root_forms_use_actual_adapter_summary(self):
        for index,root in enumerate(['2026-10-25T02:00:00+00:00','2026-10-25T02:00:00.000000+00:00',
                '2026-10-25T02:00:00.123456+00:00','2026-10-24T22:00:00.123456-04:00',
                '2026-10-25T07:30:00.123456+05:30']):
            with self.subTest(root=root):self.adapter('canonical-'+str(index),root=root)

    def test_02_unsupported_root_precision_offsets_and_forms_reject(self):
        invalid=['2026-10-25T02:00:00.1+00:00','2026-10-25T02:00:00.0000000+00:00',
                 '2026-10-25T02:00:01.000000001+00:00','2026-10-25T02:00:01.000000000000000000000000001+00:00',
                 '2026-10-25T02:00:00+00:00:00.000000001','2026-10-25T02:00:00+00:00:01',
                 '2026-10-24T22:00:00-04:00:00.000001','2026-10-25T02:00:00Z',
                 '2026-10-25 02:00:00+00:00','2026-10-25t02:00:00+00:00','2026-10-25T02:00+00:00',
                 '2026-10-25T02:00:00-00:00','2026-10-25T02:00:00+24:00','2026-10-25T02:00:00+01:99',
                 '2026-02-29T02:00:00+00:00','0000-10-25T02:00:00+00:00','2026-10-25T24:00:00+00:00',
                 '2026-10-25T02:00:60+00:00','2026-10-25T02:00:00,123456+00:00','2026-10-25T02:00:00']
        for index,root in enumerate(invalid):
            with self.subTest(root=root):self.adapter('invalid-root-'+str(index),root=root,expected=False)

    def test_03_lexical_rejections_precede_datetime_parse(self):
        real=datetime.datetime;calls=[]
        class ParseObserver(real):
            @classmethod
            def fromisoformat(cls,value):calls.append(value);return real.fromisoformat(value)
        for root in ['2026-10-25T02:00:00.000000001+00:00','2026-10-25T02:00:00+00:00:00.1']:
            f=self.ref.fixture();f['root']['selectedAtUTC']=root
            with mock.patch.object(i.datetime,'datetime',ParseObserver):
                with self.assertRaises(ValueError):i.datetime_ns(root)
                with self.assertRaises(ValueError):i.validate_root(f['root'],fresh=True)
        self.assertEqual(calls,[])

    def test_04_calendar_and_canonical_roundtrip_reject(self):
        for value in ['2026-02-29T00:00:00+00:00','2026-01-01T00:00:00-00:00','2026-01-01T00:00:00+00:99']:
            with self.subTest(value=value),self.assertRaises(ValueError):i.root_datetime(value)
        self.assertEqual(i.datetime_ns('2026-10-24T22:00:00.123456-04:00'),1792893600123456000)

    def test_05_freshness_exact_microsecond_boundaries(self):
        real=datetime.datetime
        class Clock(real):
            @classmethod
            def now(cls,tz=None):return real(2026,10,25,2,0,0,123456,tzinfo=datetime.timezone.utc)
        for token,accepted in [('2026-10-25T02:00:00.123456+00:00',True),
                               ('2026-10-25T01:55:00.123456+00:00',True),
                               ('2026-10-24T21:55:00.123456-04:00',True),
                               ('2026-10-25T02:00:00.123457+00:00',False),
                               ('2026-10-25T01:55:00.123455+00:00',False),
                               ('2026-10-25T02:00:00.123456001+00:00',False),
                               ('2026-10-25T02:00:00.123456+00:00:00.000001',False)]:
            f=self.ref.fixture();f['root']['selectedAtUTC']=token
            with self.subTest(token=token),mock.patch.object(i.datetime,'datetime',Clock):
                if accepted:i.validate_root(f['root'],fresh=True)
                else:
                    with self.assertRaises(ValueError):i.validate_root(f['root'],fresh=True)

    def test_06_root_summary_lower_boundary_remains_exact(self):
        root='2026-10-25T02:00:01.000001+00:00'
        self.adapter('root-summary-equality',root=root,start='1792893601.000001000')
        self.adapter('root-summary-before-one-ns',root=root,start='1792893601.000000999',expected=False)

    def test_07_root_window_upper_boundary_remains_exact(self):
        root='2026-10-25T02:00:00.123456+00:00'
        self.adapter('root-window-equality',root=root,finish='1792894260.123456000')
        self.adapter('root-window-after-one-ns',root=root,finish='1792894260.123456001',expected=False)

    def test_08_ambient_flags_and_traps_preserved_on_success_and_failure(self):
        prototype=Context();signals=list(prototype.flags)
        for traps in [False,True]:
            for index,flag in enumerate([None,'all']+signals):
                ctx=Context(prec=1,Emin=0,Emax=0)
                for signal in signals:ctx.traps[signal]=traps;ctx.flags[signal]=(flag=='all' or flag is signal)
                with localcontext(ctx) as active:
                    flags=dict(active.flags);trap_state=dict(active.traps)
                    self.adapter('context-'+str(traps)+'-'+str(index)+'-valid',token='1792893615.000000000000')
                    self.adapter('context-'+str(traps)+'-'+str(index)+'-invalid',token='0e9999999999999999999',expected=False)
                    for raw in [b'0e9999999999999999999',b'0e-1999999999999999998',b'1e-1000000']:
                        with self.assertRaises(ValueError):i.decimal_timestamp_ns(i.decimal_document(raw))
                    self.assertEqual(dict(active.flags),flags);self.assertEqual(dict(active.traps),trap_state)
                    self.assertEqual((active.prec,active.Emin,active.Emax),(1,0,0))

    def test_09_extreme_representable_zero_and_exponent_bounds(self):
        for token in ['-0e999999999999999999','0e-1999999999999999997','0.0e-1999999999999999996']:
            self.assertEqual(i.decimal_timestamp_ns(i.decimal_document(token.encode())),0)
        for token in ['0e9999999999999999999','0e-1999999999999999998','0.0e-1999999999999999997']:
            with self.assertRaises(ValueError):i.decimal_document(token.encode())

    def test_10_all_runtime_summary_early_returns_use_schema_five(self):
        mutations=[('cleanup-none',lambda n,p:p.update(cleanup_results=None)),
                   ('capture-none',lambda n,p:n.update(_OFFICIAL=None)),
                   ('session-failure',lambda n,p:p.update(failure='synthetic failure')),
                   ('reporting-failure',lambda n,p:setattr(p['h'],'reporting_state',{'firstFailure':'synthetic'})),
                   ('bridge-none',lambda n,p:p.update(bridge=None)),
                   ('bridge-failure',lambda n,p:p['bridge'].failures.append('synthetic')),
                   ('settings-incomplete',lambda n,p:p.update(setup_ready=lambda _:False)),
                   ('capture-run-mismatch',lambda n,p:n['_OFFICIAL'].update(runID='different'))]
        for label,mutation in mutations:self.adapter('schema-'+label,expected=False,mutate=mutation)
        self.adapter('schema-success')

    def test_11_schema_five_without_any_capture_or_cleanup(self):
        f=self.ref.fixture()
        with tempfile.TemporaryDirectory(prefix='v5-schema-',dir=prepare.BASE) as tmp:
            n,_,_,h=self.ref.adapter_namespace(f,Path(tmp))
            r=n['runtime_summary'](Path(tmp),h,None,None,None,None,None,None,None)
            self.assertEqual(r['schema'],'mixer.apple-focus-reference-runtime.5');self.assertIsNone(r['actualNativeInputActions'])

    def test_12_v3_v4_root_schemas_and_names_rejected(self):
        for version in [3,4]:
            for field in ['schema','name']:
                f=self.ref.fixture()
                if field=='schema':f['root']['schema']='mixer.apple-focus-reference-root-selection.'+str(version)
                else:f['root']['ownedSimulatorIdentity']['name']='MixerFocusReferenceV'+str(version)+'-old'
                with self.assertRaises(ValueError):i.validate_root(f['root'])

    def test_13_v3_v4_output_workspaces_rejected(self):
        for version in [3,4]:
            f=self.ref.fixture()
            with tempfile.TemporaryDirectory(prefix='v5-namespace-',dir=prepare.BASE) as tmp:
                n,_,_,h=self.ref.adapter_namespace(f,Path(tmp))
                path=Path(tmp)/('native-run-v'+str(version)+'-'+f['root']['runID'])/'runtime/session';path.mkdir(parents=True)
                with self.assertRaises(ValueError):n['select_command'](h,i.command_argv(f['root'],path),path)

    def fixture_target(self):
        meta=i.parse((prepare.BASE/'input-bindings.json').read_bytes())
        return prepare.ROOT/next(iter(meta['supplementalSettings']['members']))

    def test_14_missing_fixture_fails_closed_then_restores(self):
        path=self.fixture_target();raw=path.read_bytes();mode=path.stat().st_mode&0o777
        try:
            path.unlink()
            with self.assertRaises((AssertionError,FileNotFoundError)):frozen_inputs.verify()
        finally:path.write_bytes(raw);path.chmod(mode)
        frozen_inputs.verify()

    def test_15_changed_fixture_fails_closed_then_restores(self):
        path=self.fixture_target();raw=path.read_bytes()
        try:
            path.write_bytes(raw+b'\n')
            with self.assertRaises(AssertionError):frozen_inputs.verify()
        finally:path.write_bytes(raw)
        frozen_inputs.verify()

    def test_16_unlisted_fixture_fails_closed_then_cleans(self):
        path=self.fixture_target().parent/'0000-settings-unlisted-v5.json'
        self.assertFalse(path.exists())
        try:
            path.write_bytes(b'{}\n')
            with self.assertRaises(AssertionError):frozen_inputs.verify()
        finally:path.unlink()
        frozen_inputs.verify()
