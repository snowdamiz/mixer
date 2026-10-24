#!/usr/bin/env python3
"""Independent host tests of the sealed producer's real bridge/replay adapters.

No XCTest, simulator, compiler, shell runner, or device operation is invoked.
The three contract tests named CONTRACT are deliberately ordinary assertions:
the selected V3 packet currently fails them, making findings reproducible.
"""
import base64
import copy
import hashlib
import http.client
import importlib.util
import json
import pathlib
import struct
import sys
import tempfile
import threading
import unittest
import zlib
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/apple-toggle-keyboard-focus-v3-preparation'
sys.path.insert(0, str(PRODUCER))
import run as producer
import settings_telemetry as telemetry
import replay

SCRATCH = HERE / '.scratch'
SCRATCH.mkdir(exist_ok=True)


def image():
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 1, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00' + b'\x00\x00\x00\xff' * 2)) + chunk(b'IEND', b'')


class HostFlow:
    """An independent emitter, using actual inherited Bridge.request and saves."""
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='actual-adapter-', dir=SCRATCH)
        self.root = pathlib.Path(self.temporary.name)
        docs = self.root / 'Documents'
        docs.mkdir()
        self.bridge = producer.h.Bridge({'diagnostic': docs, 'comparator': docs}, self.root / 'captures', 'host-only-capability', {'scope': 'synthetic-host-only'}, allowed_cases=producer.keyboard_oracle.CASES)
        self.clock = 100.0
        self.runner = 10.0
        self.bridge.settings.now = lambda: self.clock
        self.bridge.settings.deadline = 500.0
        self.send({'kind': 'start', 'case': telemetry.CASE, 'uptime': self.runner})

    def close(self):
        self.temporary.cleanup()

    def send(self, record):
        return self.bridge.request('evaluate', {'settingsDiagnostic': record})

    def record(self, kind, **fields):
        self.runner += .01
        self.clock += .001
        return {'kind': kind, 'case': telemetry.CASE, 'generation': self.bridge.settings.token, 'sequence': self.bridge.settings.sequence + 1, 'uptime': self.runner, **fields}

    def mark(self, stage, detail=None):
        return self.send(self.record('mark', stage=stage, detail={} if detail is None else detail))

    def observe(self, stage, value='0', index=3, attempt=0, changes=None, payloads=None, upload=True):
        self.runner += .01
        started = self.runner
        snap = {'bundle': 'com.apple.Preferences', 'foreground': True, 'appState': 4, 'observedUptime': started + .001, 'identifier': 'FKAEnabledSwitch', 'label': 'Full Keyboard Access', 'elementType': 40, 'exists': True, 'hittable': True, 'enabled': True, 'valueKind': 'string', 'value': value, 'frame': {'x': 2.0, 'y': 3.0, 'width': 10.0, 'height': 10.0}}
        if stage == 'route-search':
            snap.update(identifier=telemetry.ROUTE[index], label=telemetry.ROUTE[index], elementType=75)
        elif stage == 'route-opened':
            # The previous selector can legitimately disappear after navigation.
            snap.update(identifier='', label='', elementType=0, exists=False, hittable=False, enabled=False, valueKind='absent', value='', frame=dict(x=0, y=0, width=0, height=0))
        snap.update(changes or {})
        if payloads is None:
            payloads = {} if stage == 'poll' else {'ax': b'Independent synthetic public AX hierarchy\n'}
            if stage in ['before-switch', 'after-switch', 'terminal']:
                payloads['png'] = image()
        files = {form: {'bytes': len(data), 'sha256': telemetry.sha(data)} for form, data in payloads.items()}
        record = self.record('observe', stage=stage, routeIndex=index, attempt=attempt, captureStartedUptime=started, captureFinishedUptime=started + .002, snapshot=snap, files=files)
        if upload:
            self.send(record)
            self.upload(payloads)
        return record, payloads

    def upload(self, payloads):
        for slot in list(self.bridge.settings.pending):
            form = slot.rsplit('-', 1)[1]
            payload = payloads[form]
            item = self.bridge.settings.uploads[slot]
            for index in range(item['count']):
                self.send(self.record('chunk', slot=slot, index=index, count=item['count'], bytes=len(payload), sha256=telemetry.sha(payload), data=base64.b64encode(payload[index * telemetry.CHUNK:(index + 1) * telemetry.CHUNK]).decode()))

    def routes(self, wrong_route=False):
        self.mark('settings-launched')
        for index in range(3):
            self.observe('route-search', index=index, changes={'identifier': 'Unselected public row', 'label': 'Unselected public row'} if wrong_route else None)
            self.mark('route-tap', {'routeIndex': index})
            self.observe('route-opened', index=index)

    def before(self, initial='0', wrong_route=False):
        self.routes(wrong_route)
        self.observe('before-switch', initial)

    def action(self, initial='0'):
        anchor = self.runner + .001 if initial == '0' else self.bridge.settings.before['snapshot']['observedUptime']
        self.mark('switch-action', {'action': 'tap' if initial == '0' else 'no-tap', 'anchorUptime': anchor, 'deadlineUptime': anchor + 3.0})

    def complete_markers(self):
        for stage in ['terminate-before', 'terminate-after', 'test-case-finished', 'suite-finished', 'bundle-finished']:
            self.mark(stage)

    def finish(self, value='1', initial='0', wrong_route=False):
        self.before(initial, wrong_route)
        self.action(initial)
        self.observe('after-switch', value)
        self.observe('terminal', value)
        self.complete_markers()


class IndependentAdapterTests(unittest.TestCase):
    def flow(self):
        f = HostFlow()
        self.addCleanup(f.close)
        return f

    def test_complete_actual_adapter_diagnostic_never_qualifies(self):
        f = self.flow(); f.finish()
        summary = producer.summary('interaction', f.bridge, 0, None, [{'passed': True}])
        self.assertTrue(summary['diagnosticCompleted'])
        self.assertTrue(summary['settingsDiagnostic']['setupObservationSatisfied'])
        for key in ['runPassed', 'carrierAccepted', 'gaAccepted', 'nativeKeyboardQualification', 'strictNativeVerdictsPassed']:
            self.assertIs(summary[key], False)
        self.assertEqual(summary['applicationCasesExecuted'], 0)
        self.assertEqual(len(summary['dependentCasesUnrun']), 6)

    def test_failed_setup_retains_three_complete_png_ax_pairs(self):
        f = self.flow(); f.finish('0')
        result = replay.replay(f.bridge.output)
        self.assertTrue(result['settingsEvidenceComplete'])
        self.assertFalse(result['setupObservationSatisfied'])
        self.assertEqual(len(list(f.bridge.output.glob('*.png'))), 3)
        self.assertEqual(result, f.bridge.settings.summary())

    def test_initial_enabled_anchor_stays_original_despite_upload_latency(self):
        f = self.flow(); f.before('1')
        original = f.bridge.settings.before['snapshot']['observedUptime']
        f.runner += 3.5
        f.action('1'); f.observe('after-switch', '1'); f.observe('terminal', '1')
        self.assertEqual(f.bridge.settings.anchor, original)
        self.assertEqual(f.bridge.settings.action, 'no-tap')
        self.assertEqual(f.bridge.settings.observation_deadline, original + 3)

    def test_late_correct_switch_values_do_not_satisfy_window(self):
        f = self.flow(); f.before(); f.action()
        f.runner = f.bridge.settings.observation_deadline + .1
        f.observe('after-switch', '1'); f.observe('terminal', '1')
        self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'])

    def test_CONTRACT_wrong_target_poll_cannot_supply_enabled_window(self):
        for changes in [{'identifier': 'OtherSwitch', 'label': 'Other setting'}, {'elementType': 9}, {'foreground': False, 'appState': 3}]:
            with self.subTest(changes=changes):
                f = self.flow(); f.before(); f.action(); f.observe('after-switch', '0')
                f.observe('poll', '1', changes=changes)
                f.runner = f.bridge.settings.observation_deadline + .1
                f.observe('terminal', '1'); f.complete_markers()
                self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'], 'Wrong-target/nonforeground poll is accepted as in-window switch evidence')

    def test_CONTRACT_wrong_route_search_cannot_satisfy_selected_route(self):
        f = self.flow(); f.finish(wrong_route=True)
        self.assertFalse(f.bridge.settings.summary()['setupObservationSatisfied'], 'Arbitrary route-search labels/identifiers currently satisfy the selected route')

    def test_CONTRACT_replay_rejects_regressing_host_receipt_time(self):
        f = self.flow(); f.finish()
        path = f.bridge.output / '0000-settings-0001.json'
        value = json.loads(path.read_bytes()); value['receivedUptime'] = 99.0
        path.write_text(json.dumps(value))
        with self.assertRaises(ValueError, msg='Replay currently accepts host receipt earlier than setup start'):
            replay.replay(f.bridge.output)

    def test_partial_upload_replay_stays_incomplete(self):
        f = self.flow(); f.routes()
        record, _ = f.observe('before-switch', upload=False); f.send(record)
        result = replay.replay(f.bridge.output)
        self.assertFalse(result['settingsEvidenceComplete'])
        self.assertFalse(result['setupObservationSatisfied'])
        self.assertEqual(len(result['pendingSlots']), 2)

    def test_missing_or_reordered_chunk_journal_is_rejected(self):
        f = self.flow(); f.mark('settings-launched')
        payload = b'Independent AX text\n' * 400
        record, payloads = f.observe('route-search', index=0, payloads={'ax': payload}, upload=False)
        f.send(record); f.upload(payloads)
        first = f.bridge.output / '0000-settings-0003.json'
        self.assertEqual(json.loads(first.read_bytes())['record']['kind'], 'chunk')
        first.unlink()
        with self.assertRaises(ValueError): replay.replay(f.bridge.output)

    def test_file_digest_or_bytes_mutation_is_rejected_by_actual_replay(self):
        f = self.flow(); f.finish('0')
        path = next(f.bridge.output.glob('*.png')); path.write_bytes(path.read_bytes() + b'extra')
        with self.assertRaises(ValueError): replay.replay(f.bridge.output)

    def test_actual_adapter_rejects_begin_paths_targets_commands_and_stale_generation(self):
        f = self.flow()
        with self.assertRaises(ValueError): f.bridge.request('begin', {'candidate': 'diagnostic', 'case': 'keyboard-enabled-off'})
        for name in ['path', 'target', 'command', 'selector', 'callback']:
            record = f.record('mark', stage='settings-launched', detail={}); record[name] = '/tmp/unselected'
            with self.assertRaises(ValueError): f.send(record)
        record = f.record('mark', stage='settings-launched', detail={}); record['generation'] = 'stale-host-token'
        with self.assertRaises(ValueError): f.send(record)
        self.assertEqual(f.bridge.generation, 0)
        self.assertIsNone(f.bridge.current)
        self.assertFalse(list((f.root / 'Documents').iterdir()))

    def test_actual_journal_is_fsynced_before_ack_and_contains_no_capability(self):
        f = self.flow()
        actual = telemetry.os.fsync
        observed = []
        def fsync(fd):
            observed.append(fd)
            return actual(fd)
        with mock.patch.object(telemetry.os, 'fsync', side_effect=fsync):
            result = f.mark('settings-launched')
        self.assertTrue(result['accepted']); self.assertGreaterEqual(len(observed), 4)
        raw = b''.join(p.read_bytes() for p in f.bridge.output.iterdir() if p.is_file())
        self.assertNotIn(b'host-only-capability', raw)
        self.assertTrue((f.bridge.output / '0000-settings-0001.json').is_file())

    def test_persist_failure_is_not_acknowledged_and_cursor_stays_unchanged(self):
        f = self.flow()
        record = f.record('mark', stage='settings-launched', detail={})
        with mock.patch.object(f.bridge, 'save', side_effect=OSError('independent disk failure')):
            with self.assertRaises(OSError): f.send(record)
        self.assertEqual(f.bridge.settings.sequence, 0)
        self.assertEqual(f.bridge.settings.events, [])

    def test_http_actual_framing_rejects_oversize_duplicate_json_and_capability(self):
        f = self.flow()
        server = producer.h.server_for(f.bridge)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join(3)))
        for raw, cap in [(b' ' * 8193, 'host-only-capability'), (b'{"settingsDiagnostic":{},"settingsDiagnostic":{}}', 'host-only-capability'), (b'{}', 'wrong-capability')]:
            client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            try:
                client.request('POST', '/evaluate', body=raw, headers={'X-Mixer-Capability': cap, 'Content-Type': 'application/json'})
                response = client.getresponse(); response.read()
                self.assertEqual(response.status, 400)
            finally: client.close()
        self.assertEqual(f.bridge.settings.sequence, 0)

    def test_termination_completion_without_captures_never_completes_diagnostic(self):
        f = self.flow(); f.complete_markers()
        result = producer.summary('interaction', f.bridge, 0, None, [{'passed': True}])
        self.assertFalse(result['diagnosticCompleted'])
        self.assertFalse(result['setupEvidenceComplete'])
        self.assertFalse(result['runPassed'])

    def test_all_cleanup_operations_attempted_after_independent_failures(self):
        calls = []
        def operation(name, fail=False):
            calls.append(name)
            if fail: raise OSError('independent cleanup failure')
        result = producer.h.cleanup_independently([(str(i), lambda i=i: operation(i, i in [0, 3])) for i in range(5)])
        self.assertEqual(calls, list(range(5)))
        self.assertEqual([item['passed'] for item in result], [False, True, True, False, True])

    def test_unchanged_qualification_assertion_and_cleanup_are_inherited(self):
        expected = ROOT / 'verification/apple-toggle-pan-origin-correction/harness.py'
        self.assertEqual(pathlib.Path(producer.h.run.__code__.co_filename), expected)
        self.assertEqual(pathlib.Path(producer.h.cleanup.__code__.co_filename), expected)
        self.assertEqual(producer.h.SCOPES['interaction']['methods'], ['test000PublicSettingsFullKeyboardAccess'])
        self.assertEqual(len(producer.keyboard_oracle.CASES), 6)
        source = expected.read_text()
        self.assertIn('require(xctest_exit == 0 and summary["strictNativeVerdictsPassed"] is True and summary["bridgeFailures"] == [], "Strict XCTest result failed; preserved evidence is authoritative")', source)


def finding_witnesses():
    result = {'schema': 'mixer.apple-toggle.keyboard-v3-independent-synthetic-witnesses.1', 'syntheticHostOnly': True, 'nativeExecuted': False}
    f = HostFlow()
    try:
        f.before(); f.action(); f.observe('after-switch', '0')
        f.observe('poll', '1', changes={'identifier': 'OtherSwitch', 'label': 'Other setting'})
        f.runner = f.bridge.settings.observation_deadline + .1
        f.observe('terminal', '1'); f.complete_markers()
        result['wrongTargetPoll'] = {'summary': f.bridge.settings.summary(), 'observations': [{'stage': item['stage'], 'sequence': item['sequence'], 'snapshot': item['snapshot']} for item in f.bridge.settings.events if item['kind'] == 'observe' and item['stage'] in ['after-switch', 'poll', 'terminal']]}
    finally: f.close()
    f = HostFlow()
    try:
        f.finish(wrong_route=True)
        result['wrongRouteSearch'] = {'summary': f.bridge.settings.summary(), 'searches': [{'routeIndex': item['routeIndex'], 'snapshot': item['snapshot']} for item in f.bridge.settings.events if item['kind'] == 'observe' and item['stage'] == 'route-search']}
    finally: f.close()
    f = HostFlow()
    try:
        f.finish()
        first = json.loads((f.bridge.output / '0000-settings-0000.json').read_bytes())
        path = f.bridge.output / '0000-settings-0001.json'
        changed = json.loads(path.read_bytes()); previous = changed['receivedUptime']; changed['receivedUptime'] = 99.0
        path.write_text(json.dumps(changed))
        result['regressingHostReceipt'] = {'startReceivedUptime': first['receivedUptime'], 'originalSequenceOneReceivedUptime': previous, 'mutatedSequenceOneReceivedUptime': changed['receivedUptime'], 'replayReturnedWithoutRejection': True, 'summary': replay.replay(f.bridge.output)}
    finally: f.close()
    return result


if __name__ == '__main__':
    if sys.argv[1:] == ['--witnesses']:
        print(json.dumps(finding_witnesses(), sort_keys=True))
    else:
        unittest.main(verbosity=2)
