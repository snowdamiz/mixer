"""Retained-build binding/scope controls using only synthetic records and bytes."""
import copy
import unittest

import region_certificate as r
import tests_region_certificate as f


EXPECTED_BINDING={
    'source_tree':'91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
    'compiler_commit':'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4',
    'target':'aarch64-apple-darwin',
    'features':['experimental-swift-reactor','experimental-swift-wasi',
        'experimental-stream-validation','experimental-function-cache'],
    'fixture_cfg':'mixer_bootstrap_one_fixture_v1','opt_level':0,'mir_opt_level':0,
    'overflow_checks':True,'panic':'unwind','codegen_units':1,'debuginfo':2,
    'link_dead_code':True,'alternate_diagnostic_configuration_only':True,
    'capture_plan_sha256':'15413684daf6815fbc9773c7fecf669f035768116524e567a841bd571c3f31c8',
    'argv_sha256':'799f61fd0bff3d5eba3849b784e7bc7b699a5ee84a2a814f298f407befb28e75',
}
EXPECTED_SCOPE={'link_dead_code':True,'alternate_diagnostic_configuration_only':True,
    'original_capture_qualified':False,'runtime_admission_accepted':False}
ORIGINAL_CAPTURE='bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184'
ORIGINAL_ARGV='4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa'


def rejoin(blobs,approval):
    """Rehash mutated synthetic envelopes so stale hashes cannot mask scope checks."""
    seal=r.strict(blobs['independent_seal'])
    seal['members']=[{'path':'semantic-review.json','bytes':len(blobs['semantic_review']),
        'sha256':r.digest(blobs['semantic_review'])}]
    seal['tree_sha256']=r.digest(f.encoded(seal['members']))
    blobs['independent_seal']=f.encoded(seal)
    envelope=r.strict(approval)
    envelope['semantic_review_sha256']=r.digest(blobs['semantic_review'])
    envelope['independent_seal_sha256']=r.digest(blobs['independent_seal'])
    envelope['inputs']=r.pins(blobs)
    raw=f.encoded(envelope)
    return raw,r.Invocation(r.digest(raw),synthetic=True)


class RetainedBindingControls(unittest.TestCase):
    def scoped(self,result):
        for key,expected in EXPECTED_SCOPE.items():self.assertIs(result[key],expected)
        self.assertIs(result['local_geometry_only'],True)
        self.assertIs(result['complete_capacity_accepted'],False)
        return result

    def refused(self,result):
        self.scoped(result)
        self.assertEqual(result['status'],'incomplete_or_invalid')
        self.assertIsNone(result['closed_local_phase_bytes'])
        self.assertIsNone(result['local_peak_bytes'])
        self.assertIs(result['trusted_approval_matched'],False)

    def test_b01_exact_retained_actual_binding_and_synthetic_separation(self):
        self.assertEqual(r.CURRENT_BINDING,EXPECTED_BINDING)
        self.assertIsNone(r.validate_binding(copy.deepcopy(EXPECTED_BINDING),False))
        case=f.fixture()
        self.assertNotEqual(case['cert']['binding']['source_tree'],EXPECTED_BINDING['source_tree'])
        self.assertIsNone(r.validate_binding(case['cert']['binding'],True))
        with self.assertRaises(r.Refusal):r.validate_binding(case['cert']['binding'],False)
        result=self.scoped(f.evaluate(case))
        self.assertEqual(result['status'],'synthetic_local_geometry')
        self.assertIs(result['synthetic'],True)

    def test_b02_original_cross_build_and_unknown_build_refuse(self):
        changes=[{'capture_plan_sha256':ORIGINAL_CAPTURE},
            {'argv_sha256':ORIGINAL_ARGV},
            {'capture_plan_sha256':ORIGINAL_CAPTURE,'argv_sha256':ORIGINAL_ARGV},
            {'capture_plan_sha256':'0'*64},{'argv_sha256':'0'*64}]
        for change in changes:
            with self.subTest(change=change):
                binding=copy.deepcopy(EXPECTED_BINDING);binding.update(change)
                with self.assertRaises(r.Refusal):r.validate_binding(binding,False)
                case=f.fixture();case['cert']['binding'].update(change)
                self.refused(f.evaluate(case))

    def test_b03_source_compiler_target_and_every_flag_remain_exact(self):
        wrong={
            'source_tree':'0'*64,'compiler_commit':'another-compiler',
            'target':'aarch64-apple-ios','features':list(reversed(EXPECTED_BINDING['features'])),
            'fixture_cfg':'proxy_fixture','opt_level':2,'mir_opt_level':1,
            'overflow_checks':False,'panic':'abort','codegen_units':2,'debuginfo':0,
        }
        for key,value in wrong.items():
            with self.subTest(key=key):
                binding=copy.deepcopy(EXPECTED_BINDING);binding[key]=value
                with self.assertRaises(r.Refusal):r.validate_binding(binding,False)
                case=f.fixture();case['cert']['binding'][key]=value
                self.refused(f.evaluate(case))
        for key in EXPECTED_BINDING:
            with self.subTest(missing=key):
                binding=copy.deepcopy(EXPECTED_BINDING);del binding[key]
                with self.assertRaises(r.Refusal):r.validate_binding(binding,False)

    def test_b04_retention_and_alternate_flags_are_explicit_typed_and_bound(self):
        for key in ('link_dead_code','alternate_diagnostic_configuration_only'):
            for wrong in (False,None,0,1,'true'):
                with self.subTest(key=key,wrong=wrong):
                    case=f.fixture();case['cert']['binding'][key]=wrong
                    self.refused(f.evaluate(case))
            case=f.fixture();del case['cert']['binding'][key]
            self.refused(f.evaluate(case))
        # Qualification fields do not belong inside immutable capture binding.
        for key in ('original_capture_qualified','runtime_admission_accepted'):
            case=f.fixture();case['cert']['binding'][key]=False
            self.refused(f.evaluate(case))

    def test_b05_certificate_and_capture_scope_cannot_be_laundered(self):
        for key,expected in EXPECTED_SCOPE.items():
            for missing in (False,True):
                with self.subTest(envelope='certificate',key=key,missing=missing):
                    case=f.fixture()
                    if missing:del case['cert'][key]
                    else:case['cert'][key]=not expected
                    self.refused(f.evaluate(case))
        for blob,scope in (('capture_observation',r.OBSERVATION_SCOPE),
                ('capture_acceptance',EXPECTED_SCOPE)):
            for key,expected in scope.items():
                for missing in (False,True):
                    def mutate(case,key=key,expected=expected,missing=missing,blob=blob):
                        value=r.strict(case['blobs'][blob])
                        if missing:del value[key]
                        else:value[key]=not expected
                        case['blobs'][blob]=f.encoded(value)
                    with self.subTest(envelope=blob,key=key,missing=missing):
                        self.refused(f.evaluate(f.fixture(),mutate))
        for key,value in (('local_geometry_only',False),('complete_capacity_accepted',True)):
            case=f.fixture();case['cert']['semantic_map']['claims'][key]=value
            self.refused(f.evaluate(case))
        # No output authority can be smuggled in as an unknown map claim.
        case=f.fixture();case['cert']['semantic_map']['claims']['original_capture_qualified']=True
        self.refused(f.evaluate(case))

    def test_b06_freshly_rejoined_review_seal_and_root_scope_refuse(self):
        for blob in ('semantic_review','independent_seal'):
            for key,expected in EXPECTED_SCOPE.items():
                for missing in (False,True):
                    with self.subTest(envelope=blob,key=key,missing=missing):
                        case=f.fixture();f.refresh_capture(case)
                        certificate,blobs,approval,invocation=f.authorize(case)
                        value=r.strict(blobs[blob])
                        if missing:del value[key]
                        else:value[key]=not expected
                        blobs[blob]=f.encoded(value)
                        approval,invocation=rejoin(blobs,approval)
                        result=r.verify(certificate,blobs,approval,invocation)
                        self.refused(result)
                        self.assertEqual(result['missing'][0]['reason'],'alternate diagnostic scope'
                            if not missing else 'closed object fields')
        for key,expected in EXPECTED_SCOPE.items():
            for missing in (False,True):
                with self.subTest(envelope='root_approval',key=key,missing=missing):
                    case=f.fixture();f.refresh_capture(case)
                    certificate,blobs,approval,invocation=f.authorize(case)
                    value=r.strict(approval)
                    if missing:del value[key]
                    else:value[key]=not expected
                    approval=f.encoded(value)
                    self.refused(r.verify(certificate,blobs,approval,
                        r.Invocation(r.digest(approval),synthetic=True)))

    def test_b07_invalid_missing_approval_and_incomplete_outputs_keep_scope(self):
        self.refused(r.verify(b'{}',{}))
        case=f.fixture();f.refresh_capture(case)
        certificate,blobs,approval,invocation=f.authorize(case)
        result=self.scoped(r.verify(certificate,blobs,None,r.Invocation(None,synthetic=True)))
        self.assertIs(result['trusted_approval_matched'],False)
        case=f.fixture();f.arena(case,'A_R')['physical_alignment']=None
        result=self.scoped(f.evaluate(case))
        self.assertEqual(result['status'],'synthetic_local_geometry')
        self.assertIsNone(result['local_peak_bytes'])
        self.assertIsNone(result['closed_local_phase_bytes'])
        self.assertTrue(any(item['scope']=='local' for item in result['missing']))


if __name__=='__main__':unittest.main(verbosity=2)
