"""Focused host corrections using the real inherited bridge and durable replay."""
import copy
import json
import pathlib
import tempfile
import unittest
from unittest import mock
import test_independent_adapted as independent
import settings_telemetry as t
import replay


class RepairTests(unittest.TestCase):
    def flow(self):
        f = independent.HostFlow()
        self.addCleanup(f.close)
        return f

    def invalid_poll(self, changes):
        f = self.flow(); f.before(); f.action(); f.observe('after-switch', '0')
        f.observe('poll', '1', changes=changes)
        f.runner = f.bridge.settings.observation_deadline + .1
        f.observe('terminal', '1'); f.complete_markers()
        value = f.bridge.settings.summary()
        self.assertFalse(value['setupObservationSatisfied'])
        self.assertEqual(value['enabledWithinWindowSequences'], [])
        self.assertEqual(len(value['invalidEnabledWithinWindowSequences']), 1)
        self.assertEqual(value, replay.replay(f.bridge.output))

    def test_each_poll_identity_label_type_and_state_field(self):
        for changes in [{'identifier': 'OtherSwitch'}, {'label': 'Other setting'}, {'elementType': 9}, {'exists': False}, {'hittable': False}, {'enabled': False}, {'foreground': False}, {'appState': 3}]:
            with self.subTest(changes=changes): self.invalid_poll(changes)

    def test_poll_allowed_alias_still_must_match_initial_identifier(self):
        self.invalid_poll({'identifier': 'Full Keyboard Access'})

    def test_initial_enabled_invalid_switch_supplies_no_sample(self):
        for changes in [{'identifier': 'OtherSwitch'}, {'label': 'Wrong'}, {'elementType': 9}, {'exists': False}, {'hittable': False}, {'enabled': False}, {'foreground': False}, {'appState': 3}]:
            with self.subTest(changes=changes):
                f = self.flow(); f.routes(); f.observe('before-switch', '1', changes=changes); f.action('1')
                f.observe('after-switch', '1'); f.observe('terminal', '1')
                value = f.bridge.settings.summary()
                self.assertEqual(value['enabledWithinWindowSequences'], [])
                self.assertFalse(value['setupObservationSatisfied'])

    def test_every_switch_stage_shares_expected_switch_predicate(self):
        for stage in ['after-switch', 'terminal']:
            for changes in [{'identifier': 'OtherSwitch'}, {'label': 'Wrong'}, {'elementType': 9}, {'exists': False}, {'hittable': False}, {'enabled': False}, {'foreground': False}, {'appState': 3}]:
                f = self.flow(); f.before(); f.action()
                f.observe('after-switch', '1' if stage == 'after-switch' else '0', changes=changes if stage == 'after-switch' else None)
                f.observe('terminal', '1', changes=changes if stage == 'terminal' else None)
                value = f.bridge.settings.summary()
                self.assertFalse(value['settingsMetadataExpected'])
                self.assertFalse(value['setupObservationSatisfied'])

    def test_correct_poll_one_can_supply_window_with_late_correct_terminal(self):
        f = self.flow(); f.before(); f.action(); f.observe('after-switch', '0'); f.observe('poll', '1')
        f.runner = f.bridge.settings.observation_deadline + .1
        f.observe('terminal', '1')
        self.assertTrue(f.bridge.settings.summary()['setupObservationSatisfied'])
        self.assertEqual(len(f.bridge.settings.enabled_samples), 1)

    def test_valid_initial_enabled_no_tap_and_fixed_alias(self):
        for identifier in ['FKAEnabledSwitch', 'Full Keyboard Access']:
            f = self.flow(); f.routes(); f.observe('before-switch', '1', changes={'identifier': identifier}); f.action('1')
            f.observe('after-switch', '1', changes={'identifier': identifier}); f.observe('terminal', '1', changes={'identifier': identifier})
            self.assertTrue(f.bridge.settings.summary()['setupObservationSatisfied'])
            self.assertEqual(f.bridge.settings.action, 'no-tap')

    def test_wrong_route_fields_never_become_selected_taps(self):
        for changes in [{'identifier': 'Unselected public row'}, {'label': 'Unselected public row'}, {'elementType': 40}, {'exists': False}, {'hittable': False}, {'enabled': False}, {'foreground': False}, {'appState': 3}]:
            with self.subTest(changes=changes):
                f = self.flow(); f.mark('settings-launched')
                for index in range(3):
                    f.observe('route-search', index=index, changes=changes if index == 1 else None)
                    f.mark('route-tap', {'routeIndex': index}); f.observe('route-opened', index=index)
                f.observe('before-switch'); f.action(); f.observe('after-switch', '1'); f.observe('terminal', '1')
                value = f.bridge.settings.summary()
                self.assertFalse(value['selectedRouteEvidenceExpected']); self.assertFalse(value['setupObservationSatisfied'])
                self.assertEqual(value['routeTaps'], [0, 2]); self.assertEqual(value['claimedRouteTapIndices'], [0, 1, 2])
                self.assertFalse(value['routeTapBindings'][1]['rowMatched'])

    def test_latest_search_must_match_tap_not_earlier_valid_search(self):
        f = self.flow(); f.mark('settings-launched')
        f.observe('route-search', index=0); f.observe('route-search', index=0, attempt=1, changes={'label': 'Wrong'})
        f.mark('route-tap', {'routeIndex': 0})
        self.assertFalse(f.bridge.settings.route_bindings[0]['rowMatched'])
        self.assertEqual(f.bridge.settings.route_bindings[0]['searchSequence'], f.bridge.settings.route_searches[0]['sequence'])

    def test_failed_search_then_correct_retry_can_bind_tap(self):
        f = self.flow(); f.mark('settings-launched')
        absent = dict(identifier='', label='', elementType=0, exists=False, hittable=False, enabled=False, valueKind='absent', value='', frame=dict(x=0, y=0, width=0, height=0))
        f.observe('route-search', index=0, changes=absent)
        f.observe('route-search', index=0, attempt=1); f.mark('route-tap', {'routeIndex': 0})
        self.assertTrue(f.bridge.settings.route_bindings[0]['rowMatched'])

    def test_expected_cell_and_static_text_identifiers(self):
        aliases = [('ACCESSIBILITY', 'Accessibility'), ('KEYBOARDS', 'Keyboards & Typing'), ('FULL_KEYBOARD_ACCESS', 'Full Keyboard Access')]
        for element in [48, 75]:
            f = self.flow(); f.mark('settings-launched')
            for index, (identifier, label) in enumerate(aliases):
                f.observe('route-search', index=index, changes={'identifier': identifier, 'label': label, 'elementType': element})
                f.mark('route-tap', {'routeIndex': index}); f.observe('route-opened', index=index)
            f.observe('before-switch'); f.action(); f.observe('after-switch', '1'); f.observe('terminal', '1')
            self.assertTrue(f.bridge.settings.summary()['setupObservationSatisfied'])

    def test_absent_opened_selector_is_explicit_exception(self):
        f = self.flow(); f.finish()
        value = f.bridge.settings.summary()
        self.assertTrue(value['selectedRouteEvidenceExpected'])
        self.assertTrue(all(row['oldSelectorAbsent'] for row in value['routeOpenedBindings']))

    def test_arbitrary_present_opened_row_is_not_absent_exception(self):
        f = self.flow(); f.mark('settings-launched')
        for index in range(3):
            f.observe('route-search', index=index); f.mark('route-tap', {'routeIndex': index})
            f.observe('route-opened', index=index, changes={'identifier': 'Other', 'label': 'Other', 'elementType': 75, 'exists': True, 'hittable': True, 'enabled': True, 'frame': dict(x=1, y=1, width=10, height=10)})
        f.observe('before-switch'); f.action(); f.observe('after-switch', '1'); f.observe('terminal', '1')
        self.assertFalse(f.bridge.settings.summary()['selectedRouteEvidenceExpected'])
        self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])

    def test_absent_opened_exception_rejects_metadata_inconsistency(self):
        for changes in [{'label': 'Other'}, {'identifier': 'Other'}, {'elementType': 75}, {'hittable': True}, {'enabled': True}, {'foreground': False}, {'appState': 3}, {'valueKind': 'unsupported'}, {'frame': dict(x=0, y=0, width=10, height=0)}]:
            f = self.flow(); f.mark('settings-launched'); f.observe('route-search', index=0); f.mark('route-tap', {'routeIndex': 0}); f.observe('route-opened', index=0, changes=changes)
            self.assertFalse(f.bridge.settings.route_opened_bindings[0]['expectedOrAbsent'])

    def test_equal_host_receipts_allowed(self):
        f = self.flow(); record = f.record('mark', stage='settings-launched', detail={}); f.clock = f.bridge.settings.last_host
        result = f.send(record)
        self.assertTrue(result['accepted']); self.assertEqual(f.bridge.settings.last_host, 100)
        self.assertEqual(replay.replay(f.bridge.output), f.bridge.settings.summary())

    def test_first_and_later_host_regressions_rejected(self):
        f = self.flow(); initial = f.bridge.settings.last_host
        record = f.record('mark', stage='settings-launched', detail={}); f.clock = initial - .1
        with self.assertRaises(ValueError): f.send(record)
        self.assertEqual(f.bridge.settings.last_host, initial); self.assertEqual(f.bridge.settings.sequence, 0)
        f.clock = initial + .1; f.send(record); accepted = f.bridge.settings.last_host
        record = f.record('observe', stage='poll'); f.clock = accepted - .01
        with self.assertRaises(ValueError): f.send(record)
        self.assertEqual(f.bridge.settings.last_host, accepted); self.assertEqual(f.bridge.settings.sequence, 1)

    def test_start_persistence_failure_rolls_back_host_cursor(self):
        clock = [100.0]
        persist = mock.Mock(side_effect=OSError('failed start fsync'))
        session = t.Session(persist, lambda *args: None, 500, now=lambda: clock[0])
        with self.assertRaises(OSError): session.request({'kind': 'start', 'case': t.CASE, 'uptime': 10.0})
        self.assertIsNone(session.start_host); self.assertIsNone(session.last_host); self.assertEqual(session.sequence, 0)
        persist.side_effect = None; clock[0] = 101.0
        session.request({'kind': 'start', 'case': t.CASE, 'uptime': 10.0})
        self.assertEqual(session.last_host, 101.0)

    def test_event_persistence_failure_preserves_all_accepted_cursors(self):
        f = self.flow(); before = (f.bridge.settings.last_host, f.bridge.settings.sequence, f.bridge.settings.last_uptime)
        record = f.record('mark', stage='settings-launched', detail={})
        with mock.patch.object(f.bridge, 'save', side_effect=OSError('failed event fsync')):
            with self.assertRaises(OSError): f.send(record)
        self.assertEqual((f.bridge.settings.last_host, f.bridge.settings.sequence, f.bridge.settings.last_uptime), before)
        f.send(record)
        self.assertEqual(f.bridge.settings.last_host, f.clock); self.assertEqual(f.bridge.settings.sequence, 1)

    def test_chunk_persistence_failure_does_not_advance_time_or_upload(self):
        f = self.flow(); f.mark('settings-launched'); record, payloads = f.observe('route-search', index=0, upload=False); f.send(record)
        before = (f.bridge.settings.last_host, f.bridge.settings.sequence)
        with mock.patch.object(f.bridge.settings, 'persist_file', side_effect=OSError('failed artifact fsync')):
            with self.assertRaises(OSError): f.upload(payloads)
        self.assertEqual((f.bridge.settings.last_host, f.bridge.settings.sequence), before)
        self.assertTrue(f.bridge.settings.pending)
        self.assertTrue(all(v['complete'] is False for v in f.bridge.settings.uploads.values()))

    def test_replay_first_later_and_start_receipt_mutations(self):
        for index, value in [(1, 99.0), (4, 100.0), (0, 100.5)]:
            f = self.flow(); f.finish()
            path = f.bridge.output / f'0000-settings-{index:04d}.json'
            record = json.loads(path.read_bytes()); record['receivedUptime'] = value; path.write_text(json.dumps(record))
            with self.assertRaises(ValueError): replay.replay(f.bridge.output)

    def test_nonfinite_bool_negative_host_receipts_and_session_caps(self):
        for host in [-1, True, float('nan'), float('inf'), 500.0, 129.001]:
            f = self.flow(); record = f.record('mark', stage='settings-launched', detail={}); f.clock = host
            with self.assertRaises(ValueError): f.send(record)
            self.assertEqual(f.bridge.settings.last_host, 100.0)

    def test_reused_runner_app_and_oracle_are_exact_v3_bytes(self):
        b = pathlib.Path(__file__).resolve().parent; p = b.parent / 'apple-toggle-keyboard-focus-v3-preparation'
        for name in ['built-app.tar.gz', 'test-runner-products.tar.gz', 'keyboard_oracle.py', 'harness/UITests/ToggleUITests.swift']:
            self.assertEqual((b / name).read_bytes(), (p / name).read_bytes())

    def test_inherited_qualification_boundary_remains_false(self):
        f = self.flow(); f.finish()
        summary = independent.producer.summary('interaction', f.bridge, 0, {'type': 'ValueError', 'message': 'Strict XCTest result failed; preserved evidence is authoritative'}, [{'passed': True}])
        self.assertTrue(summary['diagnosticCompleted']); self.assertTrue(summary['expectedDiagnosticQualificationBoundary'])
        self.assertFalse(summary['runPassed']); self.assertFalse(summary['nativeKeyboardQualification']); self.assertEqual(len(summary['dependentCasesUnrun']), 6)


if __name__ == '__main__': unittest.main(verbosity=2)
