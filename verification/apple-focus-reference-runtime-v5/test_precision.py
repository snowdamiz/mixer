"""V5 bounded exact-time controls, including real adapter capture with fake tools.

Every byte and application observation is synthetic host evidence. Decimal
contexts are hostile to arithmetic; expected endpoints are literal integer facts.
"""
import copy
from decimal import Decimal, Context, localcontext, ROUND_UP, ROUND_DOWN, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_EVEN
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
import prepare
import test_importer as legacy

i=legacy.i

class ExactTimestampControls(unittest.TestCase):
    records=[]
    @classmethod
    def setUpClass(cls):
        legacy.RuntimeControls.setUpClass()
        cls.ref=legacy.RuntimeControls('test_001_one_complete_strict_original_pass_is_diagnostic_only')
        cls.records=[]
    @classmethod
    def tearDownClass(cls):legacy.RuntimeControls.tearDownClass()

    def raw_case(self,token,signature_ns,role='before',accepted=False,context=None):
        f=self.ref.fixture();f['captures'][role]['signature'][1]=signature_ns
        if role=='before':f['captures']['after']['signature'][1]=signature_ns
        with tempfile.TemporaryDirectory(prefix='exact-time-adapter-',dir=prepare.BASE) as tmp:
            sandbox=Path(tmp);namespace,invoke,calls,h=self.ref.adapter_namespace(f,sandbox)
            manifest=sandbox/'runtime/attachments/manifest.json';raw=manifest.read_bytes()
            old=b'1792893615.0' if role=='before' else b'1792893620.0'
            self.assertEqual(raw.count(old),1);raw=raw.replace(old,token.encode());manifest.write_bytes(raw)
            export=sandbox/'runtime/attachment-export.json';value=i.parse(export.read_bytes())
            value['files']['manifest.json']={'bytes':len(raw),'sha256':i.digest(raw)};export.write_bytes(i.stable(value))
            namespace['capture_official'](object(),invoke,h,sandbox)
            official=namespace['_OFFICIAL']
            result=i.import_selected(f['root'],f['session'],f['observer'],f['streams'],official['official'],official['payloads'],official['captures'],f['cleanup'],self.ref.oracle,self.ref.classifier)
            self.records.append({'token':token,'role':role,'signatureNS':signature_ns,'context':context,'expectedAccepted':accepted,'actualAdapterCaptured':True,'toolCalls':[row[0] for row in calls],'manifestSHA256':i.digest(raw),'result':result,'syntheticOnly':True})
        expected='one-strict-original-verdict-passed' if accepted else 'invalid-or-incomplete-evidence'
        self.assertEqual(result['diagnosticOutcome'],expected,result)
        self.assertEqual(result['keyInjectionCount'],1 if accepted else None)
        for key in ['runPassed','nativeKeyboardQualification','carrierAccepted','gaAccepted']:
            self.assertIs(result[key],False)
        return result

    def test_literal_ns_boundaries_and_plus_one_through_adapter(self):
        for role,token,endpoint in [('before','1792893615.123456789',1792893615123456789),('after','1792893620.987654321',1792893620987654321)]:
            with self.subTest(role=role):
                self.raw_case(token,endpoint,role,True)
                self.raw_case(token,endpoint+1,role,False)

    def test_three_frozen_review_precision_failures_now_reject(self):
        for role,token,signature_ns in [('before','1792893615.123456789000000000000000001',1792893615123456789),('before','1792893615.999999999999999999999999999',1792893616000000000),('after','1792893620.123456789000000000000000001',1792893620123456789)]:
            with self.subTest(role=role,token=token):self.raw_case(token,signature_ns,role)

    def test_exact_ns_extra_zeroes_and_exponent_notation_accept(self):
        for token in ['1792893615.123456789000000000000000000','1.792893615123456789e9','1792893615123456789e-9','0.179289361512345678900000e10','1792893615.123456789'+'0'*900]:
            with self.subTest(token=token):self.raw_case(token,1792893615123456789,accepted=True)

    def test_deep_positive_and_negative_sub_ns_reject(self):
        for token in ['1792893615.123456789'+'0'*900+'1','-0.0000000000000000000000000001','-1792893615.999999999999999999999999999','1.7928936151234567890000000001e9','1792893615123456789000000001e-18']:
            with self.subTest(token=token):self.raw_case(token,1792893615123456789)

    def test_precision_rounding_exponent_limits_and_all_traps_do_not_change_results(self):
        for prec,rounding in [(1,ROUND_UP),(2,ROUND_DOWN),(9,ROUND_FLOOR),(18,ROUND_CEILING),(28,ROUND_HALF_EVEN),(120,ROUND_UP)]:
            ctx=Context(prec=prec,rounding=rounding,Emin=-2,Emax=2)
            for signal in ctx.traps:ctx.traps[signal]=True
            with localcontext(ctx) as active:
                label={'precision':prec,'rounding':rounding,'Emin':-2,'Emax':2,'allTraps':True}
                self.raw_case('1792893615.123456789000000',1792893615123456789,accepted=True,context=label)
                self.raw_case('1792893615.999999999999999999999999999',1792893616000000000,context=label)
                self.raw_case('1.792893620987654321e9',1792893620987654321,'after',True,label)
                self.assertFalse(any(active.flags.values()),active.flags)

    def test_untrapped_context_does_not_admit_unrepresentable_or_nonfinite(self):
        ctx=Context(prec=1,Emin=-2,Emax=2)
        for signal in ctx.traps:ctx.traps[signal]=False
        with localcontext(ctx):
            for token in ['NaN','sNaN','Infinity','-Infinity']:
                with self.subTest(token=token),self.assertRaises(ValueError):i.decimal_timestamp_ns(Decimal(token))
            for token in ['1e-9999999999999999999','0e9999999999999999999']:
                with self.subTest(token=token):
                    with self.assertRaises(ValueError):i.decimal_timestamp_ns(i.decimal_document(token.encode()))

    def test_converter_matches_independent_fraction_for_representable_values(self):
        tokens=['0','-0','0.000000000','1e-9','1.000000000000000000','1234567890123456789e-9','1792893615.1234567890000','1e308','1.7976931348623157e308','0e999999999999999999']
        for token in tokens:
            with self.subTest(token=token):
                # The extreme zero exponent is numerically zero without expansion.
                expected=0 if token.startswith('0e') else Fraction(token)*1_000_000_000
                if expected!=0:self.assertEqual(expected.denominator,1)
                self.assertEqual(i.decimal_timestamp_ns(Decimal(token)),int(expected))

    def test_extreme_exponents_fail_without_exponent_sized_work(self):
        for token in ['1e-999999999999999999','1e-1000000','1e1000000','-1e-999999999999999999','1e318']:
            with self.subTest(token=token),self.assertRaises(ValueError):i.decimal_timestamp_ns(Decimal(token))
        self.assertEqual(i.decimal_timestamp_ns(Decimal('0e-999999999999999999')),0)
        self.assertEqual(i.decimal_timestamp_ns(Decimal('0e999999999999999999')),0)

    def test_json_token_bound_and_coefficient_bound(self):
        exact='1792893615.'+'0'*(i.MAX_TIMESTAMP_TOKEN_BYTES-11)
        self.assertEqual(len(exact),i.MAX_TIMESTAMP_TOKEN_BYTES)
        self.assertEqual(i.decimal_timestamp_ns(i.decimal_document(exact.encode())),1792893615000000000)
        for token in [exact+'0','0.'+'0'*i.MAX_TIMESTAMP_TOKEN_BYTES,'1'*i.MAX_TIMESTAMP_TOKEN_BYTES+'.0']:
            with self.subTest(length=len(token)),self.assertRaises(ValueError):i.decimal_document(token.encode())
        with self.assertRaises(ValueError):i.decimal_timestamp_ns(Decimal('1.'+'0'*i.MAX_TIMESTAMP_TOKEN_BYTES))
        with self.assertRaises(ValueError):i.decimal_document(b'['+b' '*2_000_000+b']')

    def test_invalid_nondecimal_nonfinite_negative_and_overflow_inputs(self):
        for value in [False,True,1,1.0,'1',None,Decimal('NaN'),Decimal('sNaN'),Decimal('Infinity'),Decimal('-Infinity'),Decimal('-1e-999999999999999999')]:
            with self.subTest(value=repr(value)),self.assertRaises(ValueError):i.decimal_timestamp_ns(value)
        for raw in [b'NaN',b'Infinity',b'-Infinity',b'1e309',b'{"a":1,"a":2}',b'['*102+b'0'+b']'*102]:
            with self.subTest(raw=raw[:50]),self.assertRaises((ValueError,RecursionError)):i.decimal_document(raw)

    def official_range(self,start,finish):
        f=self.ref.fixture();exact={'startTime':Decimal(start),'finishTime':Decimal(finish)}
        summary=copy.deepcopy(f['summary']);summary.update(startTime=float(start),finishTime=float(finish))
        return i.official_methods(summary,f['tests'],f['root'],0,exact)

    def test_official_range_exact_order_survives_binaryfloat_collision(self):
        self.assertEqual(float('1792893610.000000001'),float('1792893610.000000002'))
        self.assertEqual(set(self.official_range('1792893610.000000001','1792893610.000000002')),set(i.METHODS))
        for start,finish in [('1792893610.000000002','1792893610.000000001'),('1792893610.000000001','1792893610.000000001')]:
            with self.subTest(start=start,finish=finish),self.assertRaises(ValueError):self.official_range(start,finish)

    def test_root_selected_range_exact_boundary_and_plus_one_ns(self):
        self.official_range('1792893600','1792894260')
        for start,finish in [('1792893599.999999999','1792893610'),('1792893600','1792894260.000000001'),('1792893600.0000000001','1792893610')]:
            with self.subTest(start=start,finish=finish),self.assertRaises(ValueError):self.official_range(start,finish)

    def test_original_before_generation_lower_bound_rejects_plus_one(self):
        f=self.ref.fixture();f['captures']['before']['signature'][1]=f['captures']['begin']['begunWallNS']-1;self.ref.reject(f)
        f=self.ref.fixture();f['captures']['before']['signature'][1]=f['captures']['begin']['begunWallNS'];f['captures']['after']['signature'][1]=f['captures']['begin']['begunWallNS'];self.assertEqual(self.ref.execute(f)['keyInjectionCount'],1)

    def test_generation_upper_finish_boundary_and_plus_one_reject(self):
        f=self.ref.fixture();f['captures']['begin']['begunWallNS']=1792893650000000001;self.ref.reject(f)
        f=self.ref.fixture();f['captures']['begin']['begunWallNS']=1792893600000000000-1;self.ref.reject(f)

    def test_after_mtime_lower_baseline_bound_rejects(self):
        f=self.ref.fixture();f['captures']['after']['signature'][1]=f['captures']['before']['signature'][1]-1;self.ref.reject(f)

    def test_unchanged_after_remains_accepted(self):
        f=self.ref.fixture();self.assertEqual(f['captures']['before']['signature'],f['captures']['after']['signature']);self.assertEqual(self.ref.execute(f)['keyInjectionCount'],1)

    def test_all_authoritative_attachment_order_edges_reject(self):
        for earlier,later in [(0,1),(1,2),(2,3)]:
            f=self.ref.fixture();rows=f['manifest'][1]['attachments'];rows[earlier]['timestamp']=rows[later]['timestamp']+1
            with self.subTest(edge=(earlier,later)):self.ref.reject(f)

    def test_attachment_run_range_endpoint_and_plus_one_ns(self):
        f=self.ref.fixture();raw={key:i.stable(f[key]) for key in ['summary','tests','manifest']}
        for token,accepted in [('1792893601.000000000',True),('1792893600.999999999',False),('1792893650.000000001',False)]:
            altered=dict(raw);altered['manifest']=raw['manifest'].replace(b'1792893610.0',token.encode())
            capsule=self.ref.host_capsule(f['root'],f['session'],0,altered,{role+'.json':i.stable(v) for role,v in f['values'].items()},{role:i.stable(v) for role,v in f['captures'].items()})
            with self.subTest(token=token):self.assertEqual(self.ref.execute(f,capsule)['diagnosticOutcome'],'one-strict-original-verdict-passed' if accepted else 'invalid-or-incomplete-evidence')

    def test_decimal_signal_flags_remain_clear_for_scalar_boundaries(self):
        ctx=Context(prec=1,Emin=-1,Emax=1)
        for signal in ctx.traps:ctx.traps[signal]=True
        with localcontext(ctx) as active:
            self.assertEqual(i.decimal_timestamp_ns(Decimal('1792893615123456789000000000e-18')),1792893615123456789)
            for token in ['1792893615.999999999999999999999999999','1e-999999999999999999','1e308']:
                try:i.decimal_timestamp_ns(Decimal(token))
                except ValueError:pass
            self.assertFalse(any(active.flags.values()),active.flags)
