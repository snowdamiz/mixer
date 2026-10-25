"""Independent host counterexamples and rational exact-time properties.

Only copied V4 sources run. Adapter tool returns and application observations are
explicit synthetic fixtures; the real derived capture and runtime_summary code
performs every import. This is not native, compiler, simulator or device credit.
"""
import copy
import argparse
import datetime
from decimal import (Decimal, Context, localcontext, ROUND_CEILING, ROUND_DOWN,
                     ROUND_FLOOR, ROUND_HALF_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP,
                     ROUND_UP, ROUND_05UP, InvalidOperation, Inexact)
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

OWNED=Path(__file__).resolve().parent
meta=json.loads((OWNED/'input-bindings.json').read_bytes())
repo=Path(meta['scratchRepo']);base=repo/'verification/apple-focus-reference-runtime-v4'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
stable=lambda value:(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def guard(event,args):
    if event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex','socket.getaddrinfo'):
        raise AssertionError('Independent exact-time review forbids '+event)
    if event=='open' and isinstance(args[0],(str,bytes)):
        path=os.fsdecode(args[0])
        assert not any(w in path.lower() for w in ('hosted','catalog','authority-driver','worker-transport')),path
        flags=args[2] if len(args)>2 else 0
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):assert Path(path).resolve().is_relative_to(OWNED),path
sys.addaudithook(guard);sys.dont_write_bytecode=True;sys.path.insert(0,str(base))
import prepare
import test_importer as frozen
i=frozen.i
parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,default=1);args=parser.parse_args()
assert args.attempt in (1,2)
OUT=OWNED/('independent-attempt-'+str(args.attempt));OUT.mkdir()
records=[];property_counts={};context_records=[]

class IndependentControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frozen.RuntimeControls.setUpClass()
        cls.ref=frozen.RuntimeControls('test_001_one_complete_strict_original_pass_is_diagnostic_only')
    @classmethod
    def tearDownClass(cls):frozen.RuntimeControls.tearDownClass()

    def adapter(self,label,f=None,manifest_tokens=None,summary_tokens=None,expected='one-strict-original-verdict-passed',retain=False):
        f=f or self.ref.fixture();manifest_tokens=manifest_tokens or {};summary_tokens=summary_tokens or {}
        with tempfile.TemporaryDirectory(prefix='independent-v4-adapter-',dir=base) as tmp:
            sandbox=Path(tmp);namespace,default_invoke,calls,h=self.ref.adapter_namespace(f,sandbox)
            manifest=sandbox/'runtime/attachments/manifest.json';raw=manifest.read_bytes()
            old={'settings':b'1792893610.0','premise':b'1792893615.0','before':b'1792893616.0','witness':b'1792893620.0','verdict':b'1792893622.0'}
            for role in manifest_tokens:
                self.assertEqual(raw.count(old[role]),1);raw=raw.replace(old[role],('__review_timestamp_'+role+'__').encode())
            for role,token in manifest_tokens.items():raw=raw.replace(('__review_timestamp_'+role+'__').encode(),token.encode())
            manifest.write_bytes(raw)
            export=sandbox/'runtime/attachment-export.json';value=i.parse(export.read_bytes())
            value['files']['manifest.json']={'bytes':len(raw),'sha256':sha(raw)};export.write_bytes(stable(value))
            summary=i.stable(f['summary'])
            for key,token in summary_tokens.items():
                target=json.dumps(key).encode()+b': '+json.dumps(f['summary'][key]).encode()
                self.assertEqual(summary.count(target),1)
                summary=summary.replace(target,json.dumps(key).encode()+b': '+token.encode())
            def invoke(commands,argv,**kwargs):
                result=default_invoke(commands,argv,**kwargs)
                return (result[0],summary.decode(),result[2]) if argv[4]=='summary' else result
            captured=False
            try:
                namespace['capture_official'](object(),invoke,h,sandbox);official=namespace['_OFFICIAL'];captured=True
                observer=f['session']/'command-observer'
                for name,payload in f['streams'].items():(observer/(name+'.log')).write_bytes(payload)
                bridge=types.SimpleNamespace(failures=[],settings=types.SimpleNamespace(summary=lambda:{'syntheticOnly':True}))
                # Invoke the actual derived summary path, including reread of the
                # application inventory, observer/streams and final import.
                result=namespace['runtime_summary'](sandbox,h,self.ref.oracle,lambda _:True,None,bridge,0,None,f['cleanup'])
            except (ValueError,KeyError,TypeError,OverflowError,RecursionError) as error:
                result={'diagnosticOutcome':'invalid-or-incomplete-evidence','keyInjectionCount':None,'provenanceAccepted':False,'failure':type(error).__name__+': '+str(error)}
            record={'label':label,'root':copy.deepcopy(f['root']),'manifestTokens':manifest_tokens,'summaryTokens':summary_tokens,
                    'rawSummarySHA256':sha(summary),'rawManifestSHA256':sha(raw),'expectedOutcome':expected,
                    'actualAdapterCaptured':captured,'actualDerivedRuntimeSummaryCalled':captured,'result':result,
                    'toolReturnsAreSynthetic':True,'nativeExecuted':False}
            records.append(record)
            if retain:
                dst=OUT/label;dst.mkdir();shutil.copytree(sandbox/'runtime',dst/'runtime')
                (dst/'root.json').write_bytes(stable(f['root']));(dst/'result.json').write_bytes(stable(result))
                (dst/'raw-summary.json').write_bytes(summary);(dst/'raw-manifest.json').write_bytes(raw)
            if expected is not None:self.assertEqual(result['diagnosticOutcome'],expected,record)
            if expected=='invalid-or-incomplete-evidence':self.assertIsNone(result['keyInjectionCount'],record)
            elif expected is not None:self.assertEqual(result['keyInjectionCount'],1,record)
            for key in ('runPassed','nativeKeyboardQualification','carrierAccepted','gaAccepted'):
                if key in result:self.assertIs(result[key],False)
            return result

    def test_01_independent_rational_exact_scalar_grid(self):
        rng=random.Random(0x4A17);count=0
        for _ in range(1800):
            integer=rng.randrange(0,10**rng.randrange(1,65));zeros=rng.randrange(0,40)
            token=str(integer)+'0'*zeros+'e'+str(-9-zeros)
            self.assertEqual(i.decimal_timestamp_ns(Decimal(token)),integer);count+=1
        property_counts['exactRationalScalarCases']=count

    def test_02_independent_rational_subns_grid(self):
        rng=random.Random(0x4A18);count=0
        for _ in range(800):
            token=str(rng.randrange(1,10**30)*10+1)+'e-'+str(rng.randrange(10,80))
            self.assertNotEqual((Fraction(token)*1_000_000_000).denominator,1)
            with self.assertRaises(ValueError):i.decimal_timestamp_ns(Decimal(token))
            count+=1
        property_counts['inexactRationalScalarCases']=count

    def test_03_all_rounding_modes_low_precision_actual_composed_boundary(self):
        modes=[ROUND_CEILING,ROUND_DOWN,ROUND_FLOOR,ROUND_HALF_DOWN,ROUND_HALF_EVEN,ROUND_HALF_UP,ROUND_UP,ROUND_05UP]
        for precision in (1,3,28,101):
            for rounding in modes:
                ctx=Context(prec=precision,rounding=rounding,Emin=0,Emax=0,clamp=1)
                for signal in ctx.traps:ctx.traps[signal]=True
                with localcontext(ctx) as active:
                    self.adapter('context-valid-'+str(precision)+'-'+rounding,manifest_tokens={'premise':'1792893615.000000000'+'0'*70})
                    self.adapter('context-inexact-'+str(precision)+'-'+rounding,manifest_tokens={'premise':'1792893615.000000000'+'0'*70+'1'},expected='invalid-or-incomplete-evidence')
                    self.assertFalse(any(active.flags.values()))
                    context_records.append({'precision':precision,'rounding':rounding,'allTraps':True,'Emin':0,'Emax':0,'flagsRemainClear':True})

    def test_04_existing_decimal_flags_survive_valid_scalar_and_adapter(self):
        ctx=Context(prec=1,Emin=0,Emax=0);ctx.flags[InvalidOperation]=True;ctx.flags[Inexact]=True
        with localcontext(ctx) as active:
            before=dict(active.flags)
            self.assertEqual(i.decimal_timestamp_ns(Decimal('1792893615.0000000000000')),1792893615000000000)
            self.adapter('preexisting-flags-preserved')
            self.assertEqual(dict(active.flags),before)

    def test_05_zero_extreme_exponents_signed_and_context_safe(self):
        ctx=Context(prec=1,Emin=0,Emax=0)
        for signal in ctx.traps:ctx.traps[signal]=True
        with localcontext(ctx) as active:
            for token in ['-0e999999999999999999','-0e-999999999999999999','0e999999999999999999','0e-999999999999999999']:
                self.assertEqual(i.decimal_timestamp_ns(i.decimal_document(token.encode())),0)
            self.assertFalse(any(active.flags.values()))

    def test_06_unrepresentable_raw_exponent_does_not_mutate_ambient_flags(self):
        ctx=Context(prec=1,Emin=0,Emax=0)
        for signal in ctx.traps:ctx.traps[signal]=True
        with localcontext(ctx) as active:
            self.adapter('invalid-exponent-context-flag',manifest_tokens={'premise':'0e9999999999999999999'},expected='invalid-or-incomplete-evidence',retain=True)
            state={str(k):v for k,v in active.flags.items()}
            (OUT/'invalid-exponent-context-flags.json').write_bytes(stable(state))
            self.assertFalse(any(active.flags.values()),state)

    def test_07_root_microsecond_endpoint_remains_exact(self):
        f=self.ref.fixture();f['root']['selectedAtUTC']='2026-10-25T02:00:01.000000+00:00'
        self.adapter('root-microsecond-equality',f)

    def test_08_root_microsecond_future_of_summary_rejects(self):
        f=self.ref.fixture();f['root']['selectedAtUTC']='2026-10-25T02:00:01.000001+00:00'
        self.adapter('root-microsecond-early-summary',f,expected='invalid-or-incomplete-evidence')

    def test_09_root_nanosecond_future_of_summary_must_reject(self):
        f=self.ref.fixture();f['root']['selectedAtUTC']='2026-10-25T02:00:01.000000001+00:00'
        self.adapter('root-nanosecond-early-summary',f,expected='invalid-or-incomplete-evidence',retain=True)

    def test_10_root_subnanosecond_tail_must_reject(self):
        f=self.ref.fixture();f['root']['selectedAtUTC']='2026-10-25T02:00:01.000000000000000000000000001+00:00'
        self.adapter('root-subnanosecond-early-summary',f,expected='invalid-or-incomplete-evidence',retain=True)

    def test_11_fresh_root_future_by_one_ns_must_reject(self):
        real=datetime.datetime
        class Clock(real):
            @classmethod
            def now(cls,tz=None):return real(2026,10,25,2,0,1,tzinfo=datetime.timezone.utc)
        f=self.ref.fixture();f['root']['selectedAtUTC']='2026-10-25T02:00:01.000000001+00:00'
        with mock.patch.object(i.datetime,'datetime',Clock),self.assertRaises(ValueError):i.validate_root(f['root'],fresh=True)

    def collision(self,label,start,finish,expected):
        tokens={role:'1792893615.123456789' for role in ('settings','premise','before','witness','verdict')}
        self.assertEqual(float(start),float(finish))
        self.adapter(label,manifest_tokens=tokens,summary_tokens={'startTime':start,'finishTime':finish},expected=expected)

    def test_12_actual_adapter_accepts_exact_summary_float_collision(self):
        self.collision('summary-collision-valid','1792893615.123456789','1792893615.123456790','one-strict-original-verdict-passed')

    def test_13_actual_adapter_rejects_reversed_summary_float_collision(self):
        self.collision('summary-collision-reversed','1792893615.123456790','1792893615.123456789','invalid-or-incomplete-evidence')

    def test_14_actual_adapter_rejects_equal_exact_summary(self):
        self.collision('summary-collision-equal','1792893615.123456789','1792893615.123456789','invalid-or-incomplete-evidence')

    def test_15_actual_adapter_rejects_subns_summary(self):
        self.adapter('summary-subnanosecond',summary_tokens={'startTime':'1792893601.00000000000000000000000001'},expected='invalid-or-incomplete-evidence')

    def test_16_before_one_ns_later_than_original_premise_rejects(self):
        f=self.ref.fixture();f['captures']['before']['signature'][1]=1792893615000000001;f['captures']['after']['signature'][1]=1792893615000000001
        self.adapter('before-original-premise-plus-one',f,manifest_tokens={'premise':'1792893615.000000000'},expected='invalid-or-incomplete-evidence')

    def test_17_after_one_ns_later_than_original_witness_rejects(self):
        f=self.ref.fixture();f['captures']['after']['signature'][1]=1792893620000000001
        self.adapter('after-original-witness-plus-one',f,manifest_tokens={'witness':'1792893620.000000000'},expected='invalid-or-incomplete-evidence')

    def test_18_after_at_witness_endpoint_can_follow_premise(self):
        f=self.ref.fixture();f['captures']['after']['signature'][1]=1792893620000000000
        b=copy.deepcopy(f['captures']['before']['observation']);b.update(keyboardWitness=f['values']['witness'],keyboardBinding=f['captures']['witness']['binding'])
        v=self.ref.oracle.verdict('diagnostic',i.CASE,'native-keyboard',b,f['captures']['after']['observation'],True)
        v.update(ownedSimulatorIdentity=f['root']['ownedSimulatorIdentity'],generation=1,actionIndex=1)
        f['values']['verdict']=v;f['captures']['after']['verdict']=copy.deepcopy(v)
        result=self.adapter('changed-after-at-later-witness',f,expected=None)
        self.assertTrue(result['provenanceAccepted'],result);self.assertEqual(result['keyInjectionCount'],1,result)
        self.assertIn(result['diagnosticOutcome'],('one-strict-original-verdict-passed','one-strict-original-verdict-failed'))

    def test_19_unchanged_after_is_still_valid(self):self.adapter('unchanged-after')

    def test_20_before_at_generation_start_is_valid(self):
        f=self.ref.fixture();f['captures']['before']['signature'][1]=f['captures']['begin']['begunWallNS'];f['captures']['after']['signature'][1]=f['captures']['begin']['begunWallNS']
        self.adapter('before-at-begin',f)

    def test_21_before_one_ns_before_generation_start_rejects(self):
        f=self.ref.fixture();f['captures']['before']['signature'][1]=f['captures']['begin']['begunWallNS']-1
        self.adapter('before-too-old',f,expected='invalid-or-incomplete-evidence')

    def test_22_after_one_ns_before_baseline_rejects(self):
        f=self.ref.fixture();f['captures']['after']['signature'][1]=f['captures']['before']['signature'][1]-1
        self.adapter('after-before-baseline',f,expected='invalid-or-incomplete-evidence')

    def test_23_official_window_upper_bound_exact(self):
        self.adapter('summary-at-660-seconds',summary_tokens={'finishTime':'1792894260.000000000'})

    def test_24_official_window_upper_bound_one_ns_rejects(self):
        self.adapter('summary-after-660-seconds',summary_tokens={'finishTime':'1792894260.000000001'},expected='invalid-or-incomplete-evidence')

    def test_25_authoritative_settings_before_summary_rejects(self):
        self.adapter('settings-before-summary',manifest_tokens={'settings':'1792893600.999999999'},expected='invalid-or-incomplete-evidence')

    def test_26_authoritative_verdict_after_summary_rejects(self):
        self.adapter('verdict-after-summary',manifest_tokens={'verdict':'1792893650.000000001'},expected='invalid-or-incomplete-evidence')

    def test_27_authoritative_before_witness_order_exact(self):
        self.adapter('before-key-after-witness',manifest_tokens={'before':'1792893620.000000001','witness':'1792893620.000000000'},expected='invalid-or-incomplete-evidence')

    def test_28_v3_root_schema_and_identity_rejected_before_tool_returns(self):
        for field,value in [('schema','mixer.apple-focus-reference-root-selection.3'),('ownedSimulatorIdentity',dict(self.ref.fixture()['root']['ownedSimulatorIdentity'],name='MixerFocusReferenceV3-host-synthetic'))]:
            f=self.ref.fixture();f['root'][field]=value
            with tempfile.TemporaryDirectory(prefix='independent-v4-schema-',dir=base) as tmp,self.assertRaises(ValueError):self.ref.adapter_namespace(f,Path(tmp))

    def test_29_no_capture_runtime_output_uses_v4_schema(self):
        f=self.ref.fixture()
        with tempfile.TemporaryDirectory(prefix='independent-v4-schema-',dir=base) as tmp:
            namespace,_,_,h=self.ref.adapter_namespace(f,Path(tmp))
            report=namespace['runtime_summary'](Path(tmp),h,None,None,None,None,None,None,None)
            (OUT/'no-capture-runtime-summary.json').write_bytes(stable(report))
            self.assertEqual(report['schema'],'mixer.apple-focus-reference-runtime.4',report)

    def test_30_token_length_1024_accepts_exact_boundary(self):
        token='1792893615.'+'0'*(1024-11);self.assertEqual(len(token),1024)
        self.adapter('token-1024',manifest_tokens={'premise':token})

    def test_31_token_length_1025_rejects_at_adapter(self):
        self.adapter('token-1025',manifest_tokens={'premise':'1792893615.'+'0'*(1025-11)},expected='invalid-or-incomplete-evidence')

    def test_32_max_coefficient_direct_converter_is_bounded(self):
        value=Decimal((0,(1,)+(0,)*1023,-1023))
        self.assertEqual(i.decimal_timestamp_ns(value),1_000_000_000)
        with self.assertRaises(ValueError):i.decimal_timestamp_ns(Decimal((0,(1,)+(0,)*1024,-1024)))

    def test_33_max_result_digits_and_one_digit_over(self):
        self.assertEqual(i.decimal_timestamp_ns(Decimal('1e308')),10**317)
        with self.assertRaises(ValueError):i.decimal_timestamp_ns(Decimal('1e309'))

    def test_34_extreme_exponents_reject_without_exponent_work(self):
        started=time.monotonic()
        for token in ('1e999999999999999999','1e-999999999999999999','-1e-999999999999999999'):
            with self.assertRaises(ValueError):i.decimal_timestamp_ns(Decimal(token))
        elapsed=time.monotonic()-started;property_counts['hugeExponentControlElapsedSeconds']=elapsed
        self.assertLess(elapsed,1.0)

    def test_35_root_timezone_microsecond_equivalence(self):
        f=self.ref.fixture();f['root']['selectedAtUTC']='2026-10-24T22:00:00.000000-04:00'
        self.adapter('root-timezone-equivalence',f)

    def test_36_frozen_closure_covers_referenced_settings_journals(self):
        supplement=json.loads((OWNED/'supplemental-inputs.json').read_bytes())
        missing=sorted(set(supplement['members'])-set(meta['bindings']))
        (OUT/'unbound-referenced-journals.json').write_bytes(stable({'count':len(missing),'members':missing}))
        self.assertEqual(missing,[],'Exact copied closure cannot replay frozen composition controls without these unbound historical inputs')

started=time.monotonic()
with (OUT/'stdout.log').open('w') as stdout,(OUT/'stderr.log').open('w') as stderr,mock.patch('sys.stdout',stdout):
    result=unittest.TextTestRunner(stream=stderr,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls))
(OUT/'adapter-results.json').write_bytes(stable(records))
(OUT/'context-results.json').write_bytes(stable(context_records))
receipt={'schema':'mixer.apple-focus-reference-runtime-v4-independent-controls.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'command':[sys.executable,'-B',str(Path(__file__).resolve()),'--attempt',str(args.attempt)],'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),
         'sourceSHA256':sha(Path(__file__).read_bytes()),'copiedClosureTreeSHA256':meta['bindingTreeSHA256'],'testsRun':result.testsRun,
         'passed':result.wasSuccessful(),'controlsPassed':result.testsRun-len(result.failures)-len(result.errors),
         'failures':[{'name':str(c),'traceback':tb} for c,tb in result.failures],'errors':[{'name':str(c),'traceback':tb} for c,tb in result.errors],
         'skipped':result.skipped,'actualDerivedAdapterAndSummaryCases':len(records),'hostileContextProfiles':len(context_records),
         'properties':property_counts,'elapsedSeconds':time.monotonic()-started,'nativeExecuted':False,'syntheticOnly':True}
(OUT/'receipt.json').write_bytes(stable(receipt))
print(json.dumps({k:v for k,v in receipt.items() if k not in ('failures','errors','python','command')},sort_keys=True))
if not result.wasSuccessful():raise SystemExit(1)
