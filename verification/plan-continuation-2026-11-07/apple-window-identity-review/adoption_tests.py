"""Executable successor controls. Every process, AX, device and native boundary is fake."""
import copy
import dataclasses
import json
import runpy
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from review_tests import OUT, CANDIDATE, put
import adoption
import adopt_once
import controller
import commands
import independent_tests


@dataclasses.dataclass(eq=False)
class Ref:
    token: str
    title: str
    pid: int = adoption.PID
    role: str = 'AXWindow'
    stale: bool = False


class FakeAX:
    def __init__(self, recovery):
        self.windows = [Ref(str(i), w['title']) for i, w in enumerate(recovery['ax']['windows'])]
        self.held = []
        self.actions = []
        self.trust = True
        self.connected = True
        self.error = None
        self.reads = 0
        self.finished = False

    def trusted(self):
        self.reads += 1
        return self.trust

    def app(self, pid):
        if self.error:
            raise self.error
        return 'app'

    def children(self, ref, name='AXChildren', optional=True):
        if name == 'AXWindows':
            return [dataclasses.replace(w) for w in self.windows]
        return ['keyboard'] if ref == 'menu' else []

    def pid(self, ref):
        if ref == 'close':
            return adoption.PID
        if ref.stale:
            raise controller.Refused('Invalid/stale AX reference PID')
        return ref.pid

    def text(self, ref, name, optional=False):
        if ref == 'keyboard':
            return 'Connect Hardware Keyboard' if name == 'AXTitle' else ('✓' if self.connected else '')
        if ref == 'menu':
            return ''
        if ref.stale:
            raise controller.Refused('Invalid AX reference')
        return {'AXTitle': ref.title, 'AXRole': ref.role, 'AXIdentifier': ''}[name]

    def flag(self, ref, name):
        return True

    def attr(self, ref, name):
        if name == 'AXMenuBar':
            return 'menu'
        if name == 'AXCloseButton':
            if ref.title != adoption.TITLE:
                raise AssertionError('Outside close attempted')
            return 'close'
        raise AssertionError(name)

    def retain(self, ref):
        self.held.append(ref)
        return ref

    def equal(self, a, b):
        return a.token == b.token

    def release(self):
        pass

    def finish(self):
        self.finished = True

    def press(self, ref):
        if ref != 'close':
            raise AssertionError('Unexpected mutation')
        self.actions.append('owned-close')
        self.windows = [w for w in self.windows if w.title != adoption.TITLE]


class MemoryCommands:
    def __init__(self, baseline, recovery, ax):
        self.unresolved = False
        self.events = []
        self.calls = []
        self.rows = copy.deepcopy(baseline)
        self.rows[adoption.UID] = {**recovery['ownedDevice'], 'deviceType': adoption.DEVICE}
        self.identity = adoption.IDENTITY
        self.osas_trust = True
        self.ax = ax
        self.drift_at = None
        self.device_reads = 0

    def raw_devices(self):
        raw = {}
        for uid, row in self.rows.items():
            raw.setdefault(row['runtime'], []).append({**row, 'udid': uid})
        return json.dumps(dict(devices=raw))

    def run(self, label, argv, timeout=45, **kwargs):
        if self.unresolved:
            raise AssertionError('Command after UNKNOWN')
        self.calls.append((label, argv))
        if argv[0] == '/bin/ps':
            return self.identity
        if argv[0] == '/usr/bin/osascript':
            return json.dumps(dict(trusted=self.osas_trust))
        if argv[1:4] == ['simctl', 'list', 'runtimes']:
            return json.dumps(dict(runtimes=[dict(identifier=adoption.RUNTIME, isAvailable=True, buildversion='23F77')]))
        if argv[1:4] == ['simctl', 'list', 'devices']:
            self.device_reads += 1
            if self.drift_at == self.device_reads:
                row = next(value for uid, value in self.rows.items()
                           if uid != adoption.UID and value['state'] == 'Booted')
                if row['state'] != 'Booted':
                    raise AssertionError('Drift fixture must start Booted')
                row['state'] = 'Shutdown'
            return self.raw_devices()
        if argv[1:3] == ['simctl', 'shutdown'] and argv[-1] == adoption.UID:
            self.rows[adoption.UID]['state'] = 'Shutdown'
            return ''
        if argv[1:3] == ['simctl', 'delete'] and argv[-1] == adoption.UID:
            del self.rows[adoption.UID]
            return ''
        raise AssertionError('Forbidden fake boundary ' + repr(argv))


class Successor(unittest.TestCase):
    def backend(self, suffix=''):
        baseline, recovery = adoption.evidence()
        folder = OUT/(self._testMethodName + suffix)
        folder.mkdir()
        ax = FakeAX(recovery)
        c = MemoryCommands(baseline, recovery, ax)
        with patch.object(adoption, 'ReferenceAX', return_value=ax), patch.object(adoption, 'Commands', return_value=c):
            b = adoption.AdoptionBackend(folder)
        # Accepted verifier runs separately unchanged in BindingControls.
        b.verify_bindings = lambda: None
        return b

    def adopted(self, suffix=''):
        b = self.backend(suffix)
        owned, baseline = b.adopt()
        return b, owned, baseline

    def stopped(self, b, action):
        with self.assertRaises((controller.Refused, RuntimeError)):
            action()
        self.assertTrue(b.unknown and b.c.unresolved)
        calls, reads, actions = len(b.c.calls), b.ax.reads, list(b.ax.actions)
        for further in [b.adopt, lambda: b.windows_for_device(adoption.UID),
                        lambda: b.close_window(getattr(b.owned, 'window', None)),
                        lambda: controller.cleanup(b, b.owned, getattr(b, 'external_baseline', {}))]:
            with self.assertRaises(controller.Refused):
                further()
        self.assertEqual((len(b.c.calls), b.ax.reads, b.ax.actions), (calls, reads, actions))

    def test_empty_identifier_retained_reference_valid(self):
        b, owned, baseline = self.adopted()
        self.assertEqual(b.windows_for_device(adoption.UID), [owned.window])
        self.assertTrue(b.keyboard_connected(owned.window))
        self.assertEqual(len(b.ax.held), 3)
        self.assertTrue(all(b.ax.text(ref, 'AXIdentifier') == '' for ref in b.ax.held))
        self.assertEqual(b.ax.actions, [])

    def test_duplicate_own_title_refused_at_adoption(self):
        b = self.backend()
        b.ax.windows.append(Ref('duplicate', adoption.TITLE))
        self.stopped(b, b.adopt)

    def test_colliding_title_after_binding_refused(self):
        b, _, _ = self.adopted()
        b.ax.windows.append(Ref('duplicate', adoption.TITLE))
        self.stopped(b, lambda: b.windows_for_device(adoption.UID))

    def test_duplicate_reference_refused(self):
        b, _, _ = self.adopted()
        b.ax.windows.append(dataclasses.replace(b.ax.windows[0]))
        self.stopped(b, lambda: b.windows_for_device(adoption.UID))

    def test_stale_retained_reference_refused(self):
        b, _, _ = self.adopted()
        b.ax.held[0].stale = True
        self.stopped(b, lambda: b.windows_for_device(adoption.UID))

    def test_reused_reference_changed_title_refused(self):
        b, _, _ = self.adopted()
        b.ax.windows[0].title = 'reused for another window'
        self.stopped(b, lambda: b.windows_for_device(adoption.UID))

    def test_same_title_replacement_reference_refused(self):
        b, _, _ = self.adopted()
        b.ax.windows[0].token = 'replacement'
        self.stopped(b, lambda: b.windows_for_device(adoption.UID))

    def test_outside_missing_refused(self):
        b, _, _ = self.adopted()
        b.ax.windows.pop()
        self.stopped(b, lambda: b.windows_for_device(adoption.UID))

    def test_outside_changed_refused(self):
        b, _, _ = self.adopted()
        b.ax.windows[-1].title += ' changed'
        self.stopped(b, lambda: b.windows_for_device(adoption.UID))

    def test_wrong_pid_refused(self):
        b, _, _ = self.adopted()
        b.ax.windows[0].pid = 99
        self.stopped(b, lambda: b.windows_for_device(adoption.UID))

    def test_missing_owned_before_close_refused(self):
        b, _, _ = self.adopted()
        b.ax.windows = [w for w in b.ax.windows if w.title != adoption.TITLE]
        self.stopped(b, lambda: b.windows_for_device(adoption.UID))

    def test_exact_frontend_drift_refused_before_ax(self):
        b = self.backend()
        b.c.identity += ' different-start'
        self.stopped(b, b.adopt)
        self.assertEqual(b.ax.held, [])

    def test_python_trust_refused(self):
        b = self.backend()
        b.ax.trust = False
        self.stopped(b, b.adopt)
        self.assertEqual(b.ax.held, [])

    def test_osascript_trust_refused(self):
        b = self.backend()
        b.c.osas_trust = False
        self.stopped(b, b.adopt)
        self.assertEqual(b.ax.held, [])

    def test_owned_record_drift_refused(self):
        b = self.backend()
        b.c.rows[adoption.UID]['dataPath'] = '/wrong'
        self.stopped(b, b.adopt)

    def test_external_drift_latched_before_window_probe(self):
        b, owned, baseline = self.adopted()
        b.c.drift_at = b.c.device_reads + 1
        before = b.ax.reads
        self.stopped(b, lambda: controller.check_snapshot(b, owned, baseline))
        self.assertEqual(before, b.ax.reads)
        self.assertTrue(b.preservation_failure['rootRecoveryRequired'])

    def test_unknown_ax_error_no_followups(self):
        b, _, _ = self.adopted()
        b.ax.error = RuntimeError('AXWindows -25204')
        self.stopped(b, lambda: b.windows_for_device(adoption.UID))

    def test_owned_only_close_shutdown_delete(self):
        b, owned, baseline = self.adopted()
        outside = [(w.token, w.title) for w in b.ax.windows if w.title != adoption.TITLE]
        result = controller.cleanup(b, owned, baseline)
        self.assertTrue(result['cleanupPassed'])
        self.assertEqual(b.ax.actions, ['owned-close'])
        self.assertEqual([(w.token, w.title) for w in b.ax.windows], outside)
        self.assertEqual(b.c.rows, baseline)
        mutations = [argv for _, argv in b.c.calls if argv[1:3] in (['simctl', 'shutdown'], ['simctl', 'delete'])]
        self.assertEqual([a[-1] for a in mutations], [adoption.UID, adoption.UID])
        self.assertFalse(result['frontendQuitRequested'])

    def test_outside_drift_before_close_prevents_press(self):
        b, owned, baseline = self.adopted()
        b.ax.windows.pop()
        self.stopped(b, lambda: controller.cleanup(b, owned, baseline))
        self.assertEqual(b.ax.actions, [])

    def test_keyboard_false_is_read_only(self):
        b, owned, _ = self.adopted()
        b.ax.connected = False
        self.assertFalse(b.keyboard_connected(owned.window))
        self.assertFalse(b.unknown)
        self.assertEqual(b.ax.actions, [])

    def test_no_create_boot_or_open_routes(self):
        b = self.backend()
        for call in [b.create_owned, lambda: b.boot(adoption.UID), lambda: b.open_owned_window(None)]:
            with self.assertRaises(RuntimeError):
                call()
        self.assertEqual(b.c.calls, [])

    def test_inner_baseline_drift_is_latched(self):
        b, _, _ = self.adopted()
        changed_uid = next(uid for uid, row in b.external_baseline.items() if row['state'] == 'Booted')
        self.assertEqual(b.c.rows[changed_uid]['state'], 'Booted')
        b.c.rows[changed_uid]['state'] = 'Shutdown'
        self.stopped(b, lambda: b.command('inner-baseline', ['/usr/bin/xcrun', 'simctl', 'list', 'devices', '--json']))

    def test_frozen_thirteen_receipts_and_failure(self):
        baseline, recovery = adoption.evidence()
        self.assertNotIn(adoption.UID, baseline)
        self.assertEqual(recovery['ax']['pid'], adoption.PID)
        self.assertTrue(all(w['identifier'] == '' for w in recovery['ax']['windows']))

    def test_terminal_shape_strict(self):
        valid = independent_tests.terminal()
        adopt_once.validate_terminal(valid)
        cases = [None, [], {}, {**valid, 'xcodebuildExitCode': False}, {**valid, 'xcodebuildExitCode': 0.0},
                 {**valid, 'sessionFailure': 'failed'}, {**valid, 'reportingFailures': ['bad']},
                 {**valid, 'cleanupResults': valid['cleanupResults'][:-1]},
                 {**valid, 'cleanupResults': [valid['cleanupResults'][0]]*5}]
        missing = dict(valid)
        del missing['sessionFailure']
        cases.append(missing)
        for case in cases:
            with self.subTest(case=case), self.assertRaises(controller.Refused):
                adopt_once.validate_terminal(case)

    def wrapper(self, *, mode='adopt-reviewed-once', terminal=None, keyboard=True, tamper_marker=False,
                suffix='', terminal_bytes=None, tamper_selection=False, event_change=None):
        root = OUT/('wrapper-' + self._testMethodName + suffix)
        root.mkdir()
        seal = json.loads((CANDIDATE/'candidate-seal.json').read_text())
        for name in [*seal['sourceFiles'], 'candidate-seal.json']:
            (root/name).write_bytes((CANDIDATE/name).read_bytes())
        folder = root/'attempt'
        b = self.backend('-wrapper-backend' + suffix)
        b.folder = folder
        b.ax.connected = keyboard
        called = []
        def plan(owned, baseline):
            selection = folder/'root-selection.json'
            selection.write_text('{}')
            return dict(argv=['fake-native'], packetSHA256='packet', selectionSHA256=commands.digest(selection.read_bytes()))
        b.dispatch_unchanged = plan
        def native(argv):
            called.append('native')
            p = json.loads((folder/'exact-dispatch-command.json').read_text())
            (folder/'native-invocation-once.json').write_text(json.dumps(dict(packetSHA256='bad' if tamper_marker else 'packet', selectionSHA256=p['selectionSHA256'])))
            (folder/'dispatch-result.json').write_text(json.dumps(terminal))
            if terminal_bytes is not None:
                (folder/'dispatch-result.json').write_bytes(terminal_bytes)
            if tamper_selection:
                (folder/'root-selection.json').write_text('{"changed":true}')
            b.c.events.append(dict(operation='native-dispatch', argv=argv, timeoutSeconds=950,
                                   unknownCustody=False, nestedCustodyUnknown=False, reaped=True,
                                   ownedGroupAbsent=True, exitCode=0, streams=dict(stdout=dict(eof=True), stderr=dict(eof=True))))
            if event_change:
                b.c.events[-1].update(event_change)
            # Accepted producer's terminal cleanup removed the owned device/window.
            b.c.rows.pop(adoption.UID)
            b.ax.windows = [w for w in b.ax.windows if w.title != adoption.TITLE]
        b.native_dispatch = native
        error = None
        argv = [str(CANDIDATE/'adopt_once.py'), mode, adoption.UID, str(adoption.PID),
                str(folder), commands.digest((root/'candidate-seal.json').read_bytes())]
        with patch.object(adoption, 'HERE', root), patch.object(adoption, 'AdoptionBackend', return_value=b), patch.object(sys, 'argv', argv):
            try:
                runpy.run_path(str(CANDIDATE/'adopt_once.py'), run_name='__main__')
            except BaseException as e:
                error = e
        return b, called, json.loads((folder/'result.json').read_text()), error

    def test_wrapper_valid_original_native_failure_allows_cleanup(self):
        b, called, result, error = self.wrapper(terminal=independent_tests.terminal())
        self.assertIsNone(error, result)
        self.assertEqual(called, ['native'])
        self.assertTrue(result['outerCleanup']['cleanupPassed'])
        self.assertFalse(result['native']['runPassed'])
        self.assertFalse(result['gaAccepted'])

    def test_wrapper_invalid_terminal_retains_no_cleanup(self):
        b, called, result, error = self.wrapper(terminal={})
        self.assertIsNotNone(error)
        self.assertEqual(called, ['native'])
        self.assertTrue(b.c.unresolved and b.unknown)
        self.assertNotIn('outerCleanup', result)
        self.assertEqual(b.ax.actions, [])

    def test_wrapper_unbound_native_data_refused(self):
        b, called, result, error = self.wrapper(terminal=independent_tests.terminal(), tamper_marker=True)
        self.assertIsNotNone(error)
        self.assertEqual(called, ['native'])
        self.assertTrue(b.c.unresolved)
        self.assertNotIn('outerCleanup', result)

    def test_wrapper_keyboard_false_exact_cleanup_no_native(self):
        b, called, result, error = self.wrapper(keyboard=False)
        self.assertIsNone(error, result)
        self.assertEqual(called, [])
        self.assertEqual(b.ax.actions, ['owned-close'])
        self.assertEqual(result['nativeAttempts'], 0)

    def test_wrapper_root_selected_cleanup_only(self):
        b, called, result, error = self.wrapper(mode='cleanup-reviewed-once')
        self.assertIsNone(error, result)
        self.assertEqual(called, [])
        self.assertEqual(b.ax.actions, ['owned-close'])
        self.assertEqual(result['nativeAttempts'], 0)

    def test_review_actual_main_malformed_bytes_and_terminal_fields(self):
        valid = independent_tests.terminal()
        missing = dict(valid)
        del missing['sessionFailure']
        invalid = [b'', b'{', b'{} trailing', b'\xff', b'[]', b'1',
                   json.dumps(missing).encode(),
                   json.dumps({**valid, 'xcodebuildExitCode': False}).encode(),
                   json.dumps({**valid, 'xcodebuildExitCode': 0.0}).encode(),
                   json.dumps({**valid, 'cleanupResults': [valid['cleanupResults'][0]] * 5}).encode()]
        for i, raw in enumerate(invalid):
            with self.subTest(case=i):
                b, called, result, error = self.wrapper(terminal=valid, terminal_bytes=raw, suffix='-'+str(i))
                self.assertIsNotNone(error)
                self.assertEqual(called, ['native'])
                self.assertTrue(b.c.unresolved and b.unknown)
                self.assertNotIn('outerCleanup', result)
                self.assertEqual(b.ax.actions, [])
                self.assertFalse(b.allow_owned_absent)
                self.assertTrue(b.ax.finished)
                put('review-malformed-'+str(i)+'.json', result)

    def test_review_actual_main_selection_and_command_binding(self):
        changes = [dict(operation='command'), dict(argv=['unbound']), dict(timeoutSeconds=120),
                   dict(unknownCustody=True), dict(nestedCustodyUnknown=True), dict(reaped=False),
                   dict(ownedGroupAbsent=False), dict(exitCode=False), dict(exitCode=65),
                   dict(streams=dict(stdout=dict(eof=True), stderr=dict(eof=False)))]
        for i, change in enumerate([None] + changes):
            with self.subTest(case=i):
                b, called, result, error = self.wrapper(terminal=independent_tests.terminal(),
                    tamper_selection=change is None, event_change=change, suffix='-'+str(i))
                self.assertIsNotNone(error)
                self.assertEqual(called, ['native'])
                self.assertTrue(b.c.unresolved and b.unknown)
                self.assertNotIn('outerCleanup', result)
                self.assertEqual(b.ax.actions, [])
                self.assertFalse(b.allow_owned_absent)
                put('review-native-binding-'+str(i)+'.json', result)
