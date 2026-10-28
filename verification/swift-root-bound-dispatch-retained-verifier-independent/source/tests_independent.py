"""Independent adversarial controls. All verifier input bytes are synthetic."""
import copy
import json
from pathlib import Path
import unittest

import region_certificate as r
import tests_region_certificate as f


ROOT = Path(__file__).resolve().parents[3]
OBS_FIELDS = ('alternate_diagnostic_configuration_only',
              'original_capture_qualified', 'runtime_admission_accepted')
RESULTS_CHECKED = 0


def package():
    case = f.fixture()
    f.refresh_capture(case)
    return f.authorize(case)


def rejoin_root(certificate, blobs, approval):
    """Join mutated bytes to a fresh synthetic root; do not repair inner claims."""
    value = r.strict(approval)
    value.update(certificate_sha256=r.digest(certificate),
                 semantic_map_sha256=r.digest(f.encoded(r.strict(certificate)['semantic_map'])),
                 binding_sha256=r.digest(f.encoded(r.strict(certificate)['binding'])),
                 semantic_review_sha256=r.digest(blobs['semantic_review']),
                 independent_seal_sha256=r.digest(blobs['independent_seal']),
                 capture_acceptance_sha256=r.digest(blobs['capture_acceptance']),
                 inputs=r.pins(blobs))
    raw = f.encoded(value)
    return raw, r.Invocation(r.digest(raw), synthetic=True)


def rejoin_review(certificate, blobs, approval):
    seal = r.strict(blobs['independent_seal'])
    seal['members'] = [{'path': 'semantic-review.json',
                        'bytes': len(blobs['semantic_review']),
                        'sha256': r.digest(blobs['semantic_review'])}]
    seal['tree_sha256'] = r.digest(f.encoded(seal['members']))
    blobs['independent_seal'] = f.encoded(seal)
    return rejoin_root(certificate, blobs, approval)


class IndependentAdversarialControls(unittest.TestCase):
    def scoped(self, result):
        global RESULTS_CHECKED
        RESULTS_CHECKED += 1
        for key, expected in r.SCOPE.items():
            self.assertIs(result[key], expected)
        self.assertIs(result['local_geometry_only'], True)
        self.assertIs(result['complete_capacity_accepted'], False)
        return result

    def refused(self, result):
        self.scoped(result)
        self.assertEqual(result['status'], 'incomplete_or_invalid')
        self.assertIsNone(result['local_peak_bytes'])
        self.assertIsNone(result['closed_local_phase_bytes'])
        self.assertIs(result['trusted_approval_matched'], False)

    def test_i01_saved_metadata_matches_exact_binding_and_observation_field_levels(self):
        # Inspect metadata only. None of these bytes enters verify()/geometry().
        folder = ROOT / 'verification/swift-root-bound-dispatch-retained-capture-v1'
        plan = json.loads((folder / 'plan.json').read_bytes())
        observation = json.loads((folder / 'runtime/capture-observation.json').read_bytes())
        self.assertEqual(r.canonical(r.CURRENT_BINDING), r.canonical(plan['verifier_binding']))
        self.assertEqual(r.canonical(r.CURRENT_BINDING), r.canonical(observation['binding']))
        self.assertEqual(r.digest((folder / 'base-capture-plan.json').read_bytes()),
                         r.CURRENT_BINDING['capture_plan_sha256'])
        self.assertEqual(r.digest(r.canonical(plan['argv'])), r.CURRENT_BINDING['argv_sha256'])
        self.assertEqual(set(observation), set(('schema status binding compiler_exit outputs '
                         'source_manifest_sha256 owned_groups_closed cleanup_complete '
                         'bounds_met truncated capture_complete').split()) | set(OBS_FIELDS))
        self.assertNotIn('link_dead_code', observation)
        for key in OBS_FIELDS:
            self.assertIs(observation[key], r.SCOPE[key])
        self.assertIs(observation['binding']['link_dead_code'], True)
        for key in ('original_capture_qualified', 'runtime_admission_accepted'):
            self.assertNotIn(key, observation['binding'])

    def test_i02_numeric_boolean_scope_cannot_pass_any_envelope(self):
        envelopes = ('certificate', 'capture_observation', 'capture_acceptance',
                     'semantic_review', 'independent_seal', 'root_approval')
        # Explicitly exercise 1 == True and 0 == False, including float equality.
        for envelope in envelopes:
            keys = OBS_FIELDS if envelope == 'capture_observation' else tuple(r.SCOPE)
            for key in keys:
                for wrong in (0, 1, 0.0, 1.0, None, 'true', 'false', [], {}):
                    with self.subTest(envelope=envelope, key=key, wrong=wrong):
                        certificate, blobs, approval, invocation = package()
                        if envelope == 'certificate':
                            value = r.strict(certificate)
                            value[key] = wrong
                            certificate = f.encoded(value)
                        elif envelope == 'root_approval':
                            value = r.strict(approval)
                            value[key] = wrong
                            approval = f.encoded(value)
                            invocation = r.Invocation(r.digest(approval), synthetic=True)
                        else:
                            value = r.strict(blobs[envelope])
                            value[key] = wrong
                            blobs[envelope] = f.encoded(value)
                        if envelope != 'root_approval':
                            if envelope == 'semantic_review':
                                approval, invocation = rejoin_review(certificate, blobs, approval)
                            else:
                                approval, invocation = rejoin_root(certificate, blobs, approval)
                        self.refused(r.verify(certificate, blobs, approval, invocation))

    def test_i03_numeric_binding_pins_fail_in_certificate_and_observation(self):
        for envelope in ('certificate', 'capture_observation'):
            for key in ('link_dead_code', 'alternate_diagnostic_configuration_only',
                        'overflow_checks', 'opt_level', 'mir_opt_level',
                        'codegen_units', 'debuginfo'):
                correct = r.CURRENT_BINDING[key]
                wrong = int(correct) if type(correct) is bool else bool(correct)
                with self.subTest(envelope=envelope, key=key):
                    if envelope == 'certificate':
                        case = f.fixture()
                        case['cert']['binding'][key] = wrong
                        self.refused(f.evaluate(case))
                    else:
                        certificate, blobs, approval, _ = package()
                        value = r.strict(blobs['capture_observation'])
                        value['binding'][key] = wrong
                        blobs['capture_observation'] = f.encoded(value)
                        approval, invocation = rejoin_root(certificate, blobs, approval)
                        self.refused(r.verify(certificate, blobs, approval, invocation))

    def test_i04_original_alternate_and_wrong_tool_target_mix_cannot_join(self):
        mutations = {
            'capture_plan_sha256': 'bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184',
            'argv_sha256': '4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa',
            'target': 'aarch64-apple-ios', 'compiler_commit': 'other-tool',
            'source_tree': '0' * 64, 'features': list(reversed(r.CURRENT_BINDING['features'])),
            'link_dead_code': False, 'alternate_diagnostic_configuration_only': False,
        }
        for key, wrong in mutations.items():
            for envelope in ('certificate', 'capture_observation'):
                with self.subTest(envelope=envelope, key=key):
                    if envelope == 'certificate':
                        case = f.fixture()
                        case['cert']['binding'][key] = wrong
                        self.refused(f.evaluate(case))
                    else:
                        certificate, blobs, approval, _ = package()
                        value = r.strict(blobs['capture_observation'])
                        value['binding'][key] = wrong
                        blobs['capture_observation'] = f.encoded(value)
                        approval, invocation = rejoin_root(certificate, blobs, approval)
                        self.refused(r.verify(certificate, blobs, approval, invocation))
        case = f.fixture()
        case['cert']['binding'].pop('link_dead_code')
        case['cert']['binding'].pop('alternate_diagnostic_configuration_only')
        case['cert']['binding'].update({k: mutations[k] for k in ('capture_plan_sha256', 'argv_sha256')})
        self.refused(f.evaluate(case))

    def test_i05_scope_cannot_move_between_binding_and_outer_envelopes(self):
        for key in ('original_capture_qualified', 'runtime_admission_accepted'):
            case = f.fixture()
            case['cert']['binding'][key] = False
            self.refused(f.evaluate(case))
            certificate, blobs, approval, _ = package()
            value = r.strict(blobs['capture_observation'])
            value['binding'][key] = value.pop(key)
            blobs['capture_observation'] = f.encoded(value)
            approval, invocation = rejoin_root(certificate, blobs, approval)
            self.refused(r.verify(certificate, blobs, approval, invocation))
        certificate, blobs, approval, _ = package()
        value = r.strict(blobs['capture_observation'])
        value['link_dead_code'] = value['binding'].pop('link_dead_code')
        blobs['capture_observation'] = f.encoded(value)
        approval, invocation = rejoin_root(certificate, blobs, approval)
        self.refused(r.verify(certificate, blobs, approval, invocation))

    def test_i06_freshly_rejoined_review_seal_and_approval_identity_mismatches(self):
        for key, wrong in (
            ('status', 'approved-looking-label'), ('semantic_map_sha256', '0' * 64),
            ('binding_sha256', '0' * 64), ('capture_acceptance_sha256', '0' * 64),
            ('targets', list(reversed(r.TARGETS))), ('whole_cfg_and_exits_checked', 1),
            ('outgoing_edges_exhaustive', 1), ('compiler_commit', 'another-tool'),
        ):
            with self.subTest(envelope='review', key=key):
                certificate, blobs, approval, _ = package()
                value = r.strict(blobs['semantic_review'])
                value[key] = wrong
                blobs['semantic_review'] = f.encoded(value)
                approval, invocation = rejoin_review(certificate, blobs, approval)
                self.refused(r.verify(certificate, blobs, approval, invocation))
        for mutation in ('status', 'tree', 'member_sha', 'member_bytes', 'duplicate'):
            with self.subTest(envelope='seal', mutation=mutation):
                certificate, blobs, approval, _ = package()
                value = r.strict(blobs['independent_seal'])
                if mutation == 'status': value['status'] = 'another-status'
                elif mutation == 'tree': value['tree_sha256'] = '0' * 64
                elif mutation == 'member_sha': value['members'][0]['sha256'] = '0' * 64
                elif mutation == 'member_bytes': value['members'][0]['bytes'] += 1
                else: value['members'].append(copy.deepcopy(value['members'][0]))
                if mutation not in ('status', 'tree'):
                    value['tree_sha256'] = r.digest(f.encoded(value['members']))
                blobs['independent_seal'] = f.encoded(value)
                approval, invocation = rejoin_root(certificate, blobs, approval)
                self.refused(r.verify(certificate, blobs, approval, invocation))
        for key in ('certificate_sha256', 'semantic_map_sha256', 'binding_sha256',
                    'capture_acceptance_sha256', 'semantic_review_sha256', 'independent_seal_sha256'):
            certificate, blobs, approval, _ = package()
            value = r.strict(approval)
            value[key] = '0' * 64
            approval = f.encoded(value)
            self.refused(r.verify(certificate, blobs, approval,
                         r.Invocation(r.digest(approval), synthetic=True)))

    def test_i07_unapproved_scope_is_mandatory_and_synthetic_label_has_no_actual_authority(self):
        for envelope in ('semantic_review', 'independent_seal'):
            for key in r.SCOPE:
                for wrong in (0, 1, None, 'true'):
                    certificate, blobs, _, _ = package()
                    value = r.strict(blobs[envelope])
                    value[key] = wrong
                    blobs[envelope] = f.encoded(value)
                    self.refused(r.verify(certificate, blobs, None,
                                 r.Invocation(None, synthetic=True)))
                certificate, blobs, _, _ = package()
                value = r.strict(blobs[envelope])
                value.pop(key)
                blobs[envelope] = f.encoded(value)
                self.refused(r.verify(certificate, blobs, None,
                             r.Invocation(None, synthetic=True)))
        certificate, blobs, approval, invocation = package()
        result = self.scoped(r.verify(certificate, blobs, None, r.Invocation(None, synthetic=True)))
        self.assertEqual(result['status'], 'synthetic_local_geometry')
        self.assertIs(result['trusted_approval_matched'], False)
        self.assertTrue(any(item['scope'] == 'approval' for item in result['missing']))
        # These bytes are still synthetic. The actual-mode switch refuses them.
        self.refused(r.verify(certificate, blobs, approval,
                     r.Invocation(invocation.expected_approval_sha256, synthetic=False)))
        self.refused(r.verify(certificate, blobs, approval, r.Invocation('0' * 64, synthetic=True)))
        self.refused(r.verify(certificate, blobs, approval, r.Invocation(None, synthetic=True)))
        for wrong in (0, 1, 'true', None):
            self.refused(r.verify(certificate, blobs, approval,
                         r.Invocation(invocation.expected_approval_sha256, synthetic=wrong)))

    def test_i08_unapproved_non_scope_review_content_is_synthetic_only_boundary(self):
        # Existing synthetic mode deliberately evaluates hypothetical maps without
        # approval. Record this behavior without calling it actual acceptance.
        certificate, blobs, _, _ = package()
        value = r.strict(blobs['semantic_review'])
        value.update(status='unapproved-label', semantic_map_sha256='0' * 64,
                     targets=['not-an-actual-target'])
        blobs['semantic_review'] = f.encoded(value)
        result = self.scoped(r.verify(certificate, blobs, None, r.Invocation(None, synthetic=True)))
        self.assertEqual(result['status'], 'synthetic_local_geometry')
        self.assertIs(result['trusted_approval_matched'], False)
        self.assertTrue(any(item['scope'] == 'approval' for item in result['missing']))
        self.refused(r.verify(certificate, blobs, None, r.Invocation(None, synthetic=False)))

    def test_i09_every_invalid_incomplete_and_success_result_keeps_output_scope(self):
        for raw in (b'{}', b'{"schema":1,"schema":1}', b'{"schema":NaN}'):
            self.refused(r.verify(raw, {}))
        case = f.fixture()
        f.arena(case, 'A_R')['physical_alignment'] = None
        result = self.scoped(f.evaluate(case))
        self.assertEqual(result['status'], 'synthetic_local_geometry')
        self.assertIsNone(result['local_peak_bytes'])
        self.assertIsNone(result['closed_local_phase_bytes'])
        self.assertTrue(any(item['scope'] == 'local' for item in result['missing']))
        result = self.scoped(f.evaluate(f.fixture()))
        self.assertEqual(result['status'], 'synthetic_local_geometry')
        self.assertIsNotNone(result['local_peak_bytes'])
        self.assertIs(result['trusted_approval_matched'], True)

