import copy
import importlib.util
import json
import pathlib
import unittest
import fixtures
import test_independent_adapted as independent
import settings_telemetry as t
import replay


class V5Tests(unittest.TestCase):
    def flow(self):
        f = independent.HostFlow(); self.addCleanup(f.close); return f
    def search(self, f, mutate=lambda r: None):
        r, payloads = f.observe('route-search', index=0, upload=False)
        r = fixtures.adapt(r, f.bridge.settings); mutate(r)
        f.bridge.request('evaluate', {'settingsDiagnostic': r}); f.upload(payloads)
        return r
    def tap(self, f, mutate=lambda r: None):
        r = fixtures.adapt(f.record('mark', stage='route-tap', detail={'routeIndex': 0}), f.bridge.settings)
        mutate(r); return f.bridge.request('evaluate', {'settingsDiagnostic': r})

    def test_anonymous_container_retained_with_named_scoped_actual_target(self):
        f = self.flow(); f.mark('settings-launched')
        self.search(f, lambda r: r['snapshot'].update(identifier='', label=''))
        self.tap(f)
        self.assertTrue(f.bridge.settings.route_bindings[0]['rowMatched'])
        self.assertEqual(f.bridge.settings.route_searches[0]['snapshot']['identifier'], '')
        self.assertEqual(f.bridge.settings.route_searches[0]['routeWitness']['target']['label'], 'Accessibility')

    def test_anonymous_container_without_descendant_never_authorizes(self):
        f = self.flow(); f.mark('settings-launched'); r, _ = f.observe('route-search', index=0, upload=False)
        with self.assertRaises(ValueError): f.bridge.request('evaluate', {'settingsDiagnostic': r})

    def test_wrong_child_label_type_identity_state(self):
        for change in [{'label': 'Other'}, {'identifier': 'Other'}, {'elementType': 75}, {'hittable': False}, {'enabled': False}, {'foreground': False}, {'appState': 3}]:
            f = self.flow(); f.mark('settings-launched')
            self.search(f, lambda r: r['routeWitness']['target'].update(change)); self.tap(f)
            self.assertFalse(f.bridge.settings.route_bindings[0]['rowMatched'])

    def test_unrelated_outside_child_cannot_bind_container(self):
        for key, value in [('x', -1), ('y', -1), ('width', 100), ('height', 100)]:
            f = self.flow(); f.mark('settings-launched')
            self.search(f, lambda r: r['routeWitness']['target']['frame'].update({key: value})); self.tap(f)
            self.assertFalse(f.bridge.settings.route_bindings[0]['rowMatched'])

    def test_self_relation_requires_same_named_native_metadata(self):
        f = self.flow(); f.mark('settings-launched')
        self.search(f, lambda r: r['routeWitness'].update(relation='self')); self.tap(f)
        self.assertFalse(f.bridge.settings.route_bindings[0]['rowMatched'])
        f = self.flow(); f.mark('settings-launched')
        def valid(r): r['snapshot'] = copy.deepcopy(r['routeWitness']['target']); r['routeWitness']['relation'] = 'self'
        self.search(f, valid); self.tap(f)
        self.assertTrue(f.bridge.settings.route_bindings[0]['rowMatched'])

    def test_fresh_actual_tap_frame_identity_type_label_mismatch(self):
        for key, value in [('identifier', 'Other'), ('label', 'Other'), ('elementType', 9), ('frame', dict(x=3, y=3, width=10, height=10))]:
            f = self.flow(); f.mark('settings-launched'); self.search(f)
            self.tap(f, lambda r: r['detail']['target'].update({key: value}))
            self.assertFalse(f.bridge.settings.route_bindings[0]['rowMatched'])
            self.assertFalse(f.bridge.settings.route_bindings[0]['samePublicTargetMetadata'])

    def test_stale_search_sequence_and_tap_times_rejected(self):
        for change in [lambda r: r['detail'].update(searchSequence=True), lambda r: r['detail'].update(searchSequence=999), lambda r: r['detail'].update(startedUptime=0), lambda r: r['detail']['target'].update(observedUptime=0)]:
            f = self.flow(); f.mark('settings-launched'); self.search(f)
            with self.assertRaises(ValueError): self.tap(f, change)

    def test_nonactionable_zero_frame_search_is_diagnostic_not_tap_authority(self):
        f = self.flow(); f.mark('settings-launched')
        def zero(r):
            for value in [r['snapshot'], r['routeWitness']['target']]: value.update(hittable=False, frame=dict(x=0, y=0, width=0, height=0))
        self.search(f, zero)
        self.assertEqual(f.bridge.settings.route_searches[0]['snapshot']['frame']['width'], 0)
        with self.assertRaises(ValueError): self.tap(f)
        self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])

    def test_zero_frame_hittable_and_partial_zero_frames_rejected(self):
        for frame in [dict(x=0, y=0, width=0, height=0), dict(x=0, y=0, width=0, height=10)]:
            f = self.flow(); f.mark('settings-launched')
            with self.assertRaises(ValueError): self.search(f, lambda r: r['snapshot'].update(frame=frame))

    def test_search_exception_does_not_relax_actual_switch_or_tap(self):
        f = self.flow(); f.before(); snap = copy.deepcopy(f.bridge.settings.before['snapshot'])
        snap.update(hittable=False, frame=dict(x=0, y=0, width=0, height=0))
        with self.assertRaises(ValueError): t.snapshot(snap)
        self.assertIs(t.snapshot(snap, diagnostic_search=True), snap)
        self.assertFalse(t.expected_switch(snap))

    def test_negative_x_old_selector_cannot_prove_destination(self):
        f = self.flow(); f.mark('settings-launched'); self.search(f); self.tap(f)
        f.observe('route-opened', index=0, changes=dict(identifier='', label='', elementType=75, exists=True, hittable=False, frame=dict(x=-105, y=3, width=10, height=10)))
        value = f.bridge.settings.route_opened_bindings[0]
        self.assertFalse(value['oldSelectorAbsent']); self.assertTrue(value['destinationMatched'])

    def test_destination_required_wrong_page_old_selector_and_type_rejected(self):
        for change in [{'identifier': 'Other'}, {'label': 'Other'}, {'elementType': 75}, {'foreground': False}, {'appState': 3}, {'exists': False}, {'frame': dict(x=-105, y=3, width=10, height=10)}]:
            f = self.flow(); f.mark('settings-launched'); self.search(f); self.tap(f)
            r, payloads = f.observe('route-opened', index=0, upload=False); r = fixtures.adapt(r, f.bridge.settings); r['routeWitness']['destination'].update(change)
            f.bridge.request('evaluate', {'settingsDiagnostic': r}); f.upload(payloads)
            self.assertFalse(f.bridge.settings.route_opened_bindings[0]['destinationMatched'])

    def test_missing_destination_or_extra_route_fields_rejected(self):
        f = self.flow(); f.mark('settings-launched'); self.search(f); self.tap(f)
        r, _ = f.observe('route-opened', index=0, upload=False)
        with self.assertRaises(ValueError): f.bridge.request('evaluate', {'settingsDiagnostic': r})
        r = fixtures.adapt(r, f.bridge.settings); r['routeWitness']['path'] = '/unselected'
        with self.assertRaises(ValueError): f.bridge.request('evaluate', {'settingsDiagnostic': r})

    def test_nested_times_strict_and_transactional(self):
        for value in [True, float('nan'), -1, 999999]:
            f = self.flow(); f.mark('settings-launched'); before = f.bridge.settings.sequence
            with self.assertRaises(ValueError): self.search(f, lambda r: r['routeWitness']['target'].update(observedUptime=value))
            self.assertEqual(f.bridge.settings.sequence, before)

    def test_full_setup_and_replay_still_diagnostic_only(self):
        f = self.flow(); f.finish()
        value = replay.replay(f.bridge.output)
        self.assertTrue(value['setupObservationSatisfied']); self.assertFalse(value['runPassed'])
        self.assertFalse(value['nativeKeyboardQualification']); self.assertEqual(value, f.bridge.settings.summary())

    def test_limits_and_strict_app_oracle_unchanged(self):
        b = pathlib.Path(__file__).resolve().parent; prior = b.parent / 'apple-toggle-keyboard-focus-v4'
        spec = importlib.util.spec_from_file_location('prior_v4_limits', prior / 'settings_telemetry.py'); old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
        for name in ['CHUNK', 'MAX_TOTAL', 'MAX_REQUESTS', 'MAX_EVENTS', 'MAX_UPLOADS', 'MAX_DURATION']: self.assertEqual(getattr(t, name), getattr(old, name))
        for name in ['built-app.tar.gz', 'keyboard_oracle.py', 'source-lock.json']: self.assertEqual((b/name).read_bytes(), (prior/name).read_bytes())

    def test_observation_wire_fits_existing_request_cap(self):
        f = self.flow(); f.mark('settings-launched'); r, _ = f.observe('route-search', index=0, upload=False)
        self.assertLessEqual(len(json.dumps({'settingsDiagnostic': fixtures.adapt(r, f.bridge.settings)}).encode()), 8192)

    def test_bounded_switch_window_still_anchored_and_invalid_poll_silent(self):
        f = self.flow(); f.before(); f.action(); anchor = f.bridge.settings.anchor; f.observe('after-switch', '0')
        f.observe('poll', '1', changes={'identifier': 'Other'}); f.runner = f.bridge.settings.observation_deadline + .1; f.observe('terminal', '1')
        self.assertEqual(f.bridge.settings.observation_deadline, anchor+3)
        self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])


if __name__ == '__main__': unittest.main(verbosity=2)
