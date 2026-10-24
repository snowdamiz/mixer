"""Host-only guard tests. All emulator/ADB/process operations are injected fakes."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('boot_probe', Path(__file__).with_name('boot_probe.py'))
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class Clock:
    def __init__(self):
        self.value = 0

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class Child:
    pid = 210000

    def __init__(self, harness):
        self.harness = harness
        self.code = 1 if harness.mode == 'early-exit' else None
        self.actions = []

    def poll(self):
        return self.code

    def wait(self, timeout):
        if self.code is None:
            raise subprocess.TimeoutExpired('fake-owned-child', timeout)
        return self.code

    def terminate(self):
        self.actions.append('terminate')
        if self.harness.mode != 'kill-fallback':
            self.code = -15

    def kill(self):
        self.actions.append('kill')
        self.code = -9


class Harness:
    def __init__(self, mode='success'):
        self.mode = mode
        self.commands = []
        self.spawns = []
        self.group_stops = []
        self.clock = Clock()
        self.child = None

    def popen(self, argv, **kwargs):
        self.spawns.append((argv, kwargs))
        self.child = Child(self)
        return self.child

    def stop_group(self, group):
        self.group_stops.append(group)
        if self.mode == 'cleanup-unavailable':
            raise RuntimeError('fake group lookup unavailable')
        return {'group': group, 'before': [], 'after': [], 'signals': []}

    def execute(self, argv, **kwargs):
        self.commands.append((argv, kwargs))
        code, output = 0, b''
        if argv[0] == 'lsof':
            code = 1
            if self.mode == 'occupied-port' and self.child is None:
                code, output = 0, b'unrelated-listener\n'
        elif argv[:2] == ['git', 'rev-parse']:
            output = b'fixture-source-revision\n'
        elif argv[:2] == ['ps', '-axo']:
            output = b'999 1 /unrelated/emulator -avd other-project -port 5554\n'
            if self.mode == 'reserved-process':
                output = b'999 1 /unrelated/emulator -avd other-project -port 5586\n'
        elif argv[:2] == ['ps', '-p']:
            exe = '/wrong/qemu-system-aarch64-headless' if self.mode == 'identity-drift' else PROBE.HEADLESS
            line = f'{self.child.pid} {self.child.pid} ' + ' '.join([exe] + PROBE.expected_argv()[1:])
            output = (line + '\n').encode()
        elif argv[0].endswith('/adb'):
            if argv[1:] == ['version']:
                output = b'fixture-adb-version\n'
            else:
                if argv[1:3] != ['-s', PROBE.SERIAL]:
                    raise AssertionError('non-targeted ADB command')
                if argv[3:5] == ['emu', 'kill']:
                    if self.mode not in ('terminate-fallback', 'kill-fallback'):
                        self.child.code = 0
                elif argv[3:5] == ['shell', 'getprop']:
                    if self.mode == 'boot-timeout':
                        code, output = 1, b'adb: device offline\n'
                    else:
                        value = PROBE.PROPS[argv[5]]
                        if self.mode == 'wrong-target' and argv[5] == 'ro.build.version.sdk':
                            value = '36'
                        output = (value + '\n').encode()
                else:
                    raise AssertionError('unexpected ADB operation')
        else:
            output = b'fixture-tool-documentation\n'
        return SimpleNamespace(returncode=code, stdout=output,
                               groupCleanup={'group': 220000, 'before': [], 'after': [], 'signals': []})


class GuardTests(unittest.TestCase):
    def identity(self, argv=None, exe=None, pid=210000, group=210000):
        argv = list(argv or PROBE.expected_argv())
        if exe:
            argv[0] = exe
        return PROBE.owned_identity(f'{pid} {group} ' + ' '.join(argv), 210000, 210000)

    def test_exact_launcher_and_headless_paths(self):
        self.assertTrue(self.identity())
        self.assertTrue(self.identity(exe=PROBE.HEADLESS))

    def test_identity_rejects_wrong_paths_pid_group(self):
        for change in ({'exe': '/other/qemu-system-aarch64-headless'}, {'pid': 210001}, {'group': 210001}):
            with self.subTest(change=change):
                self.assertFalse(self.identity(**change))

    def test_identity_rejects_wrong_pairs_missing_and_duplicate_flags(self):
        for flag, value in (('-port', '5584'), ('-avd', 'other'), ('-gpu', 'host'), ('-feature', 'WiFiPacketStream')):
            args = PROBE.expected_argv()
            args[args.index(flag) + 1] = value
            self.assertFalse(self.identity(args), flag)
        for flag in ('-port', '-avd', '-feature', '-read-only'):
            self.assertFalse(self.identity(PROBE.expected_argv() + [flag, 'anything']), flag)
        args = PROBE.expected_argv()
        args.remove('-read-only')
        self.assertFalse(self.identity(args))

    def test_contract_exact_single_runtime_delta_and_bound_inputs(self):
        contract = PROBE.load_contract()
        self.assertEqual(contract['argv'], contract['baseArgv'] + ['-feature', '-WiFiPacketStream'])
        self.assertEqual(contract['bootDeadlineSeconds'], 180)
        self.assertTrue(any(e['path'] == PROBE.HEADLESS for e in contract['bindings']))

    def test_contract_rejects_drift(self):
        with tempfile.TemporaryDirectory(prefix='mixer-boot-contract-host-') as folder:
            path = Path(folder) / 'changed.json'
            path.write_text('{}')
            with patch.object(PROBE, 'CONTRACT', path):
                with self.assertRaisesRegex(ValueError, 'contract changed'):
                    PROBE.load_contract()

    def test_missing_dispatch_stops_before_any_runtime_or_binding(self):
        with patch('sys.argv', ['boot_probe.py', '--attempt', 'boot-probe-1']), patch.object(PROBE, 'load_contract') as bound:
            with self.assertRaises(SystemExit) as error:
                PROBE.main()
            self.assertEqual(error.exception.code, 2)
            bound.assert_not_called()

    def test_reserved_port_process_parser(self):
        self.assertTrue(PROBE.reserved_process('999 1 /path/emulator -avd other -port 5586'))
        self.assertTrue(PROBE.reserved_process('999 1 /path/qemu-system-aarch64-headless -ports 5586,5587'))
        self.assertFalse(PROBE.reserved_process('999 1 /path/emulator -avd other -port 5554'))
        self.assertFalse(PROBE.reserved_process('999 1 /path/editor /path/emulator -port 5586'))


class LifecycleTests(unittest.TestCase):
    def exercise(self, mode):
        harness = Harness(mode)
        with tempfile.TemporaryDirectory(prefix='mixer-boot-probe-host-') as folder:
            out = Path(folder)
            result = PROBE.probe(out, PROBE.load_contract(), harness,
                                 popen=harness.popen, clock=harness.clock.now, sleep=harness.clock.sleep)
            self.assertEqual(json.loads((out / 'receipt.json').read_text()), result)
        for argv, _ in harness.commands:
            self.assertNotIn('install', argv)
            self.assertNotIn('devices', argv)
            self.assertNotIn('settings', argv)
            self.assertNotIn('wm', argv)
        self.assertLessEqual(len(harness.spawns), 1)
        self.assertFalse(result['appAssertionsRun'])
        return harness, result

    def test_success_records_identity_and_stops_owned_child(self):
        h, r = self.exercise('success')
        self.assertEqual(r['status'], 'boot-only-diagnostic-passed')
        self.assertEqual(r['target'], PROBE.PROPS)
        self.assertEqual(r['cleanup'], 'stopped')
        self.assertEqual(h.group_stops, [h.child.pid])
        self.assertTrue(h.spawns[0][1]['start_new_session'])
        self.assertEqual(h.spawns[0][0], PROBE.expected_argv())

    def test_port_and_process_guards_never_spawn_or_stop(self):
        for mode in ('occupied-port', 'reserved-process'):
            h, r = self.exercise(mode)
            self.assertEqual(h.spawns, [])
            self.assertEqual(h.group_stops, [])
            self.assertEqual(r['cleanup'], 'not-started')

    def test_early_exit_records_failure_and_group_absence(self):
        h, r = self.exercise('early-exit')
        self.assertEqual(r['status'], 'failed-boot-only-diagnostic')
        self.assertIn('exited before boot', r['failure'])
        self.assertEqual(r['cleanup'], 'stopped')
        self.assertEqual(h.group_stops, [h.child.pid])

    def test_boot_deadline_is_bounded_and_cleanup_runs(self):
        h, r = self.exercise('boot-timeout')
        self.assertEqual(h.clock.value, 180)
        self.assertIn('deadline exceeded', r['failure'])
        self.assertEqual(r['cleanup'], 'stopped')
        self.assertEqual(h.group_stops, [h.child.pid])

    def test_wrong_target_fails_and_cleans_up(self):
        _, r = self.exercise('wrong-target')
        self.assertIn('target identity', r['failure'])
        self.assertEqual(r['cleanup'], 'stopped')

    def test_identity_drift_refuses_every_stop(self):
        h, r = self.exercise('identity-drift')
        self.assertEqual(r['status'], 'failed-owned-cleanup')
        self.assertEqual(r['cleanup'], 'failed')
        self.assertEqual(h.child.actions, [])
        self.assertEqual(h.group_stops, [])
        self.assertFalse(any(argv[-2:] == ['emu', 'kill'] for argv, _ in h.commands))

    def test_exact_owned_pid_termination_and_kill_fallbacks(self):
        for mode, actions in (('terminate-fallback', ['terminate']), ('kill-fallback', ['terminate', 'kill'])):
            h, r = self.exercise(mode)
            self.assertEqual(h.child.actions, actions)
            self.assertEqual(h.group_stops, [h.child.pid])
            self.assertEqual(r['cleanup'], 'stopped')

    def test_cleanup_unavailable_is_not_a_pass(self):
        _, r = self.exercise('cleanup-unavailable')
        self.assertEqual(r['status'], 'failed-owned-cleanup')
        self.assertEqual(r['cleanup'], 'failed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
