import base64
import copy
import json
import math
import pathlib
import struct
import tempfile
import unittest
import zlib
from unittest import mock
import settings_telemetry as t


def png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00\xff')) + chunk(b'IEND', b'')


class Flow:
    def __init__(self):
        self.clock = 100.0
        self.runner = 10.0
        self.records = []
        self.files = {}
        self.s = t.Session(lambda name, value: self.records.append((name, copy.deepcopy(value))), lambda slot, form, data: self.files.__setitem__(slot, data), 500, now=lambda: self.clock, token='fixed-host-session')
        self.s.request({'kind': 'start', 'case': t.CASE, 'uptime': self.runner})

    def record(self, kind, **extra):
        self.runner += .001
        return {'kind': kind, 'case': t.CASE, 'generation': self.s.token, 'sequence': self.s.sequence + 1, 'uptime': self.runner, **extra}

    def send(self, record):
        return self.s.request(record)

    def mark(self, stage, detail=None):
        return self.send(self.record('mark', stage=stage, detail={} if detail is None else detail))

    def observation(self, stage, value='0', route=3, attempt=0, upload=True):
        started = self.runner + .0001
        observed = started + .0001
        finished = observed + .0001
        snap = {'bundle': 'com.apple.Preferences', 'foreground': True, 'appState': 4, 'observedUptime': observed, 'identifier': 'FKAEnabledSwitch', 'label': 'Full Keyboard Access', 'elementType': 40, 'exists': True, 'hittable': True, 'enabled': True, 'valueKind': 'string', 'value': value, 'frame': {'x': 1.0, 'y': 2.0, 'width': 3.0, 'height': 4.0}}
        payloads = {} if stage == 'poll' else {'ax': b'Application com.apple.Preferences\nSwitch FKAEnabledSwitch'}
        if stage in ['before-switch', 'after-switch', 'terminal']:
            payloads['png'] = png()
        files = {k: {'bytes': len(v), 'sha256': t.sha(v)} for k, v in payloads.items()}
        record = self.record('observe', stage=stage, routeIndex=route, attempt=attempt, captureStartedUptime=started, captureFinishedUptime=finished, snapshot=snap, files=files)
        if upload:
            self.send(record)
            self.upload(payloads)
        return record, payloads

    def upload(self, payloads):
        for slot in list(self.s.pending):
            form = slot.rsplit('-', 1)[1]
            data = payloads[form]
            descriptor = self.s.uploads[slot]
            for index in range(descriptor['count']):
                self.send(self.record('chunk', slot=slot, index=index, count=descriptor['count'], bytes=len(data), sha256=t.sha(data), data=base64.b64encode(data[index * t.CHUNK:(index + 1) * t.CHUNK]).decode()))

    def route(self):
        self.mark('settings-launched')
        for index in range(3):
            self.observation('route-search', route=index)
            self.mark('route-tap', {'routeIndex': index})
            self.observation('route-opened', route=index)

    def before(self, initial='0'):
        self.route()
        self.observation('before-switch', initial)

    def action(self, initial='0'):
        anchor = self.runner + .0001 if initial == '0' else self.s.before['snapshot']['observedUptime']
        self.mark('switch-action', {'action': 'tap' if initial == '0' else 'no-tap', 'anchorUptime': anchor, 'deadlineUptime': anchor + 3.0})

    def finish(self, enabled='1', initial='0'):
        self.before(initial)
        self.action(initial)
        self.observation('after-switch', enabled)
        self.observation('terminal', enabled)
        for stage in ['terminate-before', 'terminate-after', 'test-case-finished', 'suite-finished', 'bundle-finished']:
            self.mark(stage)


class TelemetryTests(unittest.TestCase):
    def test_complete_enabled_diagnostic_never_qualifies(self):
        f = Flow(); f.finish()
        s = f.s.summary()
        self.assertTrue(s['setupObservationSatisfied'])
        self.assertFalse(s['runPassed']); self.assertFalse(s['nativeKeyboardQualification'])
        self.assertEqual(s['status'], 'DIAGNOSTIC_ONLY'); self.assertEqual(len(f.files), 12)

    def test_actual_failure_preserves_complete_images_and_false_setup(self):
        f = Flow(); f.finish('0')
        self.assertTrue(f.s.summary()['settingsEvidenceComplete'])
        self.assertFalse(f.s.summary()['settingsReportedEnabled'])
        self.assertEqual(sum(k.endswith('-png') for k in f.files), 3)

    def test_initial_enabled_no_tap_anchor_is_original_observation(self):
        f = Flow(); f.finish('1', '1')
        self.assertEqual(f.s.anchor, f.s.before['snapshot']['observedUptime'])
        self.assertEqual(f.s.action, 'no-tap')

    def test_extra_tap_or_changed_policy_rejected(self):
        for initial, wrong in [('0', 'no-tap'), ('1', 'tap')]:
            f = Flow(); f.before(initial)
            with self.assertRaises(ValueError):
                f.mark('switch-action', {'action': wrong, 'anchorUptime': f.runner, 'deadlineUptime': f.runner + 3})

    def test_missing_start_and_duplicate_start(self):
        f = Flow()
        with self.assertRaises(ValueError): f.s.request({'kind': 'start', 'case': t.CASE, 'uptime': 11})
        f.s.start_host = None
        with self.assertRaises(ValueError): f.mark('settings-launched')

    def test_wrong_generation_case_and_extra_authority(self):
        for key, value in [('generation', 'another'), ('case', 'keyboard-enabled-off'), ('path', '/tmp/arbitrary'), ('command', 'tap'), ('selector', 'anything')]:
            f = Flow(); r = f.record('mark', stage='settings-launched', detail={}); r[key] = value
            with self.assertRaises(ValueError): f.send(r)

    def test_missing_duplicate_reordered_sequences(self):
        for value in [0, 2, True, 1.0]:
            f = Flow(); r = f.record('mark', stage='settings-launched', detail={}); r['sequence'] = value
            with self.assertRaises(ValueError): f.send(r)
        f = Flow(); r = f.record('mark', stage='settings-launched', detail={}); f.send(r)
        with self.assertRaises(ValueError): f.send(r)

    def test_uptime_negative_bool_nonfinite_stale(self):
        for value in [-1, True, float('inf'), float('nan'), 9.0]:
            f = Flow(); r = f.record('mark', stage='settings-launched', detail={}); r['uptime'] = value
            with self.assertRaises(ValueError): f.send(r)

    def test_session_and_total_diagnostic_deadline(self):
        for clock in [129.01, 500]:
            f = Flow(); f.clock = clock
            with self.assertRaises(ValueError): f.mark('settings-launched')
        f = Flow(); f.runner = 39.01
        with self.assertRaises(ValueError): f.mark('settings-launched')

    def test_three_second_window_cannot_reset_or_extend(self):
        f = Flow(); f.before()
        for delta in [2.999, 3.001, True]:
            with self.assertRaises(ValueError): f.mark('switch-action', {'action': 'tap', 'anchorUptime': f.runner, 'deadlineUptime': f.runner + delta})
        f.action()
        with self.assertRaises(ValueError): f.action()

    def test_late_one_does_not_become_enabled_evidence(self):
        f = Flow(); f.before(); f.action(); f.runner = f.s.observation_deadline + .1
        f.observation('after-switch', '1'); f.observation('terminal', '1')
        self.assertFalse(f.s.summary()['settingsReportedEnabled'])
        self.assertFalse(f.s.summary()['setupObservationSatisfied'])

    def test_initial_enabled_anchor_cannot_move_to_after_upload(self):
        f = Flow(); f.before('1')
        with self.assertRaises(ValueError): f.mark('switch-action', {'action': 'no-tap', 'anchorUptime': f.runner, 'deadlineUptime': f.runner + 3})

    def test_route_order_attempts_and_duplicate_opened(self):
        f = Flow(); f.mark('settings-launched')
        with self.assertRaises(ValueError): f.observation('route-search', route=1)
        with self.assertRaises(ValueError): f.observation('route-search', route=0, attempt=1)
        f.observation('route-search', route=0); f.mark('route-tap', {'routeIndex': 0}); f.observation('route-opened', route=0)
        with self.assertRaises(ValueError): f.observation('route-opened', route=0)

    def test_missing_route_and_repeated_tap(self):
        f = Flow()
        with self.assertRaises(ValueError): f.observation('before-switch')
        f.mark('settings-launched'); f.observation('route-search', route=0); f.mark('route-tap', {'routeIndex': 0})
        with self.assertRaises(ValueError): f.mark('route-tap', {'routeIndex': 0})

    def test_snapshot_strict_types_and_order(self):
        for key, value in [('foreground', 1), ('appState', True), ('observedUptime', float('nan')), ('enabled', 0), ('elementType', True), ('value', 1), ('bundle', 'another')]:
            f = Flow(); f.route(); r, _ = f.observation('before-switch', upload=False); r['snapshot'][key] = value
            with self.assertRaises(ValueError): f.send(r)

    def test_stale_capture_and_nonpositive_geometry(self):
        for field, value in [('captureStartedUptime', 1), ('captureFinishedUptime', float('inf'))]:
            f = Flow(); f.route(); r, _ = f.observation('before-switch', upload=False); r[field] = value
            with self.assertRaises(ValueError): f.send(r)
        for value in [0, -1, True, float('nan')]:
            f = Flow(); f.route(); r, _ = f.observation('before-switch', upload=False); r['snapshot']['frame']['width'] = value
            with self.assertRaises(ValueError): f.send(r)

    def test_switch_id_label_and_foreground_mutations_never_satisfy(self):
        for key, value in [('identifier', 'other-switch'), ('identifier', 'Full Keyboard Access'), ('label', 'Changed'), ('foreground', False), ('enabled', False), ('hittable', False), ('appState', 3), ('elementType', 9)]:
            f = Flow(); f.finish(); f.s.after['snapshot'][key] = value
            self.assertFalse(f.s.summary()['setupObservationSatisfied'])

    def test_absent_or_unsupported_value_cannot_claim_enabled(self):
        for kind in ['absent', 'unsupported']:
            f = Flow(); f.finish(); f.s.terminal['snapshot'].update(valueKind=kind, value='')
            self.assertFalse(f.s.summary()['settingsReportedEnabled'])
        f = Flow(); f.route(); r, _ = f.observation('before-switch', upload=False); r['snapshot'].update(valueKind='unsupported', value='1')
        with self.assertRaises(ValueError): f.send(r)

    def test_required_ax_and_png_not_optional(self):
        for files in [{}, {'ax': {'bytes': 1, 'sha256': 'a' * 64}}]:
            f = Flow(); f.route(); r, _ = f.observation('before-switch', upload=False); r['files'] = files
            with self.assertRaises(ValueError): f.send(r)

    def test_partial_upload_cannot_complete_or_advance(self):
        f = Flow(); f.route(); r, _ = f.observation('before-switch', upload=False); f.send(r)
        self.assertFalse(f.s.summary()['settingsEvidenceComplete'])
        with self.assertRaises(ValueError): f.action()

    def test_chunk_wrong_slot_index_descriptor_and_bool_types(self):
        for key, value in [('slot', '../outside'), ('index', 1), ('index', True), ('count', True), ('bytes', True), ('sha256', 'b' * 64), ('data', '!!!!')]:
            f = Flow(); f.route(); r, payloads = f.observation('before-switch', upload=False); f.send(r)
            slot = f.s.pending[0]; d = f.s.uploads[slot]; payload = payloads['ax']
            c = f.record('chunk', slot=slot, index=0, count=d['count'], bytes=d['bytes'], sha256=d['sha256'], data=base64.b64encode(payload).decode()); c[key] = value
            with self.assertRaises(ValueError): f.send(c)

    def test_chunk_length_and_duplicate_rejected(self):
        f = Flow(); f.route(); r, payloads = f.observation('before-switch', upload=False); f.send(r)
        slot = f.s.pending[0]; d = f.s.uploads[slot]
        c = f.record('chunk', slot=slot, index=0, count=d['count'], bytes=d['bytes'], sha256=d['sha256'], data=base64.b64encode(payloads['ax'] + b'x').decode())
        with self.assertRaises(ValueError): f.send(c)
        c['data'] = base64.b64encode(payloads['ax']).decode(); f.send(c)
        with self.assertRaises(ValueError): f.send(c)

    def test_payload_digest_and_ax_encoding_rejected(self):
        for payload in [b'wrong bytes', b'\xff', b'\x00']:
            f = Flow(); f.route(); r, _ = f.observation('before-switch', upload=False)
            r['files']['ax'] = {'bytes': len(payload), 'sha256': t.sha(payload) if payload != b'wrong bytes' else 'a' * 64}; f.send(r)
            slot = f.s.pending[0]; d = f.s.uploads[slot]
            c = f.record('chunk', slot=slot, index=0, count=1, bytes=len(payload), sha256=d['sha256'], data=base64.b64encode(payload).decode())
            with self.assertRaises((ValueError, UnicodeError)): f.send(c)

    def test_png_signature_crc_truncation_dimensions(self):
        for data in [b'not png', png()[:-1], png() + b'extra', png()[:20] + b'X' + png()[21:]]:
            with self.assertRaises(ValueError): t.png(data)
        t.png(png())

    def test_ax_image_total_upload_and_request_bounds(self):
        for form, size in [('ax', 200001), ('png', 2000001), ('ax', True)]:
            f = Flow(); f.route(); r, _ = f.observation('before-switch', upload=False); r['files'][form]['bytes'] = size
            with self.assertRaises(ValueError): f.send(r)
        f = Flow(); f.route(); f.s.total = t.MAX_TOTAL
        with self.assertRaises(ValueError): f.observation('before-switch')
        f = Flow(); f.s.requests = t.MAX_REQUESTS
        with self.assertRaises(ValueError): f.mark('settings-launched')
        f = Flow(); f.route(); f.s.uploads.update({str(i): {} for i in range(t.MAX_UPLOADS)})
        with self.assertRaises(ValueError): f.observation('before-switch')

    def test_all_chunk_requests_fit_inherited_http_bound(self):
        f = Flow(); f.route(); r, _ = f.observation('before-switch', upload=False); f.send(r)
        slot = f.s.pending[0]
        c = f.record('chunk', slot=slot, index=651, count=652, bytes=2000000, sha256='a' * 64, data=base64.b64encode(b'x' * 3072).decode())
        self.assertLessEqual(len(json.dumps({'settingsDiagnostic': c}).encode()), 8192)
        self.assertEqual(t.MAX_REQUESTS, 2500)

    def test_terminal_blocks_future_actions(self):
        f = Flow(); f.finish('0')
        for stage in ['poll', 'route-search', 'after-switch', 'terminal']:
            with self.assertRaises(ValueError): f.observation(stage)
        with self.assertRaises(ValueError): f.mark('switch-action', {})

    def test_termination_and_completion_order(self):
        f = Flow()
        with self.assertRaises(ValueError): f.mark('terminate-after')
        with self.assertRaises(ValueError): f.mark('suite-finished')
        f.mark('terminate-before'); f.mark('terminate-after')
        with self.assertRaises(ValueError): f.mark('bundle-finished')
        f.mark('test-case-finished'); f.mark('suite-finished'); f.mark('bundle-finished')
        with self.assertRaises(ValueError): f.mark('bundle-finished')

    def test_persist_failure_cannot_ack_or_advance(self):
        f = Flow(); f.s.persist = mock.Mock(side_effect=OSError('disk full'))
        with self.assertRaises(OSError): f.mark('settings-launched')
        self.assertEqual(f.s.sequence, 0); self.assertEqual(f.s.events, [])

    def test_file_persist_failure_keeps_upload_incomplete(self):
        f = Flow(); f.route(); r, payloads = f.observation('before-switch', upload=False); f.send(r)
        f.s.persist_file = mock.Mock(side_effect=OSError('disk full'))
        with self.assertRaises(OSError): f.upload(payloads)
        self.assertTrue(f.s.pending); self.assertFalse(f.s.summary()['settingsEvidenceComplete'])

    def test_observation_before_action_and_missing_after(self):
        f = Flow(); f.before()
        with self.assertRaises(ValueError): f.observation('after-switch')
        f.action(); f.observation('terminal', '1')
        self.assertFalse(f.s.summary()['settingsEvidenceComplete'])

    def test_frozen_failed_v2_is_not_retroactive_pass(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        diagnosis = json.loads((pathlib.Path(__file__).parent / 'diagnosis.json').read_bytes())
        self.assertEqual(diagnosis['observed']['actualApplicationInputActions'], 0)
        old = json.loads((root / 'verification/apple-toggle-keyboard-focus-v2/runtime/runtime-verdict.json').read_bytes())
        self.assertFalse(old['runPassed']); self.assertEqual(len(old['dependentCasesUnrun']), 6)

    def test_replay_complete_and_mutated_native_png(self):
        import replay
        f = Flow(); f.finish('0')
        with tempfile.TemporaryDirectory() as folder:
            directory = pathlib.Path(folder)
            for name, value in f.records:
                (directory / ('0000-' + name + '.json')).write_text(json.dumps({**value, 'ownedSimulatorIdentity': {'udid': 'host-only'}}))
            for slot, data in f.files.items():
                (directory / (slot + ('.png' if slot.endswith('-png') else '.txt'))).write_bytes(data)
            self.assertEqual(replay.replay(directory), f.s.summary())
            path = next(directory.glob('*.png')); path.write_bytes(b'mutated')
            with self.assertRaises(ValueError): replay.replay(directory)

    def test_replay_missing_or_reordered_record_rejected(self):
        import replay
        f = Flow(); f.finish()
        with tempfile.TemporaryDirectory() as folder:
            directory = pathlib.Path(folder)
            for name, value in f.records:
                (directory / ('0000-' + name + '.json')).write_text(json.dumps({**value, 'ownedSimulatorIdentity': {'udid': 'host-only'}}))
            for slot, data in f.files.items():
                (directory / (slot + ('.png' if slot.endswith('-png') else '.txt'))).write_bytes(data)
            (directory / '0000-settings-0001.json').unlink()
            with self.assertRaises(ValueError): replay.replay(directory)

    def test_large_multichunk_payload_order_and_exact_bytes(self):
        f = Flow(); f.mark('settings-launched')
        r, _ = f.observation('route-search', route=0, upload=False)
        data = b'AX' * 4000
        r['files']['ax'] = {'bytes': len(data), 'sha256': t.sha(data)}; f.send(r)
        slot = f.s.pending[0]
        with self.assertRaises(ValueError): f.send(f.record('chunk', slot=slot, index=1, count=3, bytes=len(data), sha256=t.sha(data), data=base64.b64encode(data[3072:6144]).decode()))
        f.upload({'ax': data})
        self.assertEqual(f.files[slot], data)

    def test_start_clamps_remaining_session_budget(self):
        f = Flow()
        f.s.start_host = None; f.s.deadline = 100.025
        result = f.s.request({'kind': 'start', 'case': t.CASE, 'uptime': 10.0})
        self.assertAlmostEqual(result['remainingSessionSeconds'], .025)
        f.clock = 100.026
        with self.assertRaises(ValueError): f.mark('settings-launched')

    def test_missing_termination_or_completion_remains_incomplete_diagnostic(self):
        f = Flow(); f.before(); f.action(); f.observation('after-switch', '1'); f.observation('terminal', '1')
        self.assertTrue(f.s.summary()['setupObservationSatisfied'])
        self.assertEqual(f.s.summary()['completionMarkers'], [])
        self.assertFalse(f.s.summary()['runPassed'])


class RuntimeAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import run
        cls.r = run

    def test_only_fixed_method_selected_and_v2_oracle_bytes(self):
        r = self.r
        self.assertEqual(r.h.SCOPES['interaction']['methods'], ['test000PublicSettingsFullKeyboardAccess'])
        self.assertEqual(r.sha(r.BASE / 'keyboard_oracle.py'), r.sha(r.V2 / 'keyboard_oracle.py'))
        self.assertEqual(len(r.keyboard_oracle.CASES), 6)

    def test_empty_evaluation_unchanged_and_begin_disallowed(self):
        class Base:
            def __init__(self): self.current = None; self.generation = 0; self.deadline = 200; self.output = pathlib.Path('/unused')
            def save(self, *args): pass
            def _request(self, op, body): return (op, body)
        bridge = t.diagnostic_bridge(Base)()
        self.assertEqual(bridge._request('evaluate', {}), ('evaluate', {}))
        with self.assertRaises(ValueError): bridge._request('begin', {'candidate': 'diagnostic', 'case': 'keyboard-enabled-off'})
        bridge.current = {'case': 'another'}
        with self.assertRaises(ValueError): bridge._request('evaluate', {'settingsDiagnostic': {'kind': 'start'}})

    def test_expected_inherited_boundary_classified_separately(self):
        r = self.r
        s = r.summary('interaction', None, 0, {'type': 'ValueError', 'message': 'Strict XCTest result failed; preserved evidence is authoritative'}, [])
        self.assertTrue(s['expectedDiagnosticQualificationBoundary'])
        self.assertFalse(s['strictNativeVerdictsPassed']); self.assertFalse(s['runPassed'])
        self.assertEqual(s['dependentCasesUnrun'], sorted(r.keyboard_oracle.CASES))

    def test_xctest_failure_not_relabelled_as_expected_boundary(self):
        r = self.r
        for code, failure in [(65, {'type': 'ValueError', 'message': 'Strict XCTest result failed; preserved evidence is authoritative'}), (None, {'type': 'TimeoutExpired', 'message': 'timeout'})]:
            s = r.summary('interaction', None, code, failure, [])
            self.assertFalse(s['expectedDiagnosticQualificationBoundary'])

    def test_export_exception_does_not_replace_original_and_cleanup_independent(self):
        r = self.r
        with tempfile.TemporaryDirectory() as folder:
            commands = r.runtime.ExportingCommands(pathlib.Path(folder) / 'commands.json')
            with mock.patch.object(r.runtime.BaseCommands, 'run', side_effect=TimeoutError('original timeout')):
                with self.assertRaisesRegex(TimeoutError, 'original timeout'):
                    commands.run([str(r.h.DEVELOPER / 'usr/bin/xcodebuild'), 'test-without-building'])
            called = []
            def bad(): called.append('bad'); raise OSError('failure')
            result = r.h.cleanup_independently([('one', bad), ('two', lambda: called.append('two')), ('three', lambda: called.append('three'))])
            self.assertEqual(called, ['bad', 'two', 'three'])
            self.assertEqual([x['passed'] for x in result], [False, True, True])

    def test_fixed_artifact_directory_rejects_existing_file(self):
        class Base:
            def __init__(self, folder): self.current = None; self.generation = 0; self.deadline = 200; self.output = folder
            def save(self, *args): pass
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder)
            b = t.diagnostic_bridge(Base)(path)
            (path / 'settings-0001-ax.txt').write_bytes(b'original')
            with self.assertRaises(ValueError): b.settings.persist_file('settings-0001-ax', 'ax', b'replace')
            self.assertEqual((path / 'settings-0001-ax.txt').read_bytes(), b'original')

    def test_artifact_fd_closed_on_directory_fsync_failure(self):
        class Base:
            def __init__(self, folder): self.current = None; self.generation = 0; self.deadline = 200; self.output = folder
            def save(self, *args): pass
        with tempfile.TemporaryDirectory() as folder:
            bridge = t.diagnostic_bridge(Base)(pathlib.Path(folder))
            original_fsync = t.os.fsync
            calls = []
            def fsync(fd):
                calls.append(fd)
                if len(calls) == 2: raise OSError('directory fsync failed')
                return original_fsync(fd)
            with mock.patch.object(t.os, 'fsync', side_effect=fsync), mock.patch.object(t.os, 'close', wraps=t.os.close) as close:
                with self.assertRaises(OSError): bridge.settings.persist_file('settings-0001-ax', 'ax', b'AX')
                close.assert_called_once_with(calls[-1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
