"""Two bounded review invocations; native/process/group operations are fakes."""
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import sys
import time
import unittest
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
PACKET = OUT.parent / 'pair9-api28-controller-fix-r3'
sys.path.insert(0, str(PACKET))
spec = importlib.util.spec_from_file_location('reviewed_host_controls', PACKET / 'host_controls.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
r, c = h.r, h.c
MODE = 'optimized' if sys.flags.optimize else 'normal'
h.WORK = OUT / ('fake-' + MODE)


class Independent(unittest.TestCase):
    def test_exact_review_admission_and_receipt_mutation(self):
        review = {'verdict': 'ACCEPT', 'scope': 'ONE_API28_ARM64_RUNTIME_ATTEMPT',
                  'controllerSHA256': r.identity(PACKET/'run_api28.py')['sha256'],
                  'lifecycleSHA256': r.LIFECYCLE_SHA,
                  'packetSHA256': r.identity(PACKET/'controller-packet.json')['sha256'],
                  'hostReceipts': {mode:r.identity(PACKET/('host-'+mode+'.json')) for mode in ('normal','optimized')}}
        frozen = r.load(PACKET / 'controller-packet.json')
        r.admission(review, frozen, review['controllerSHA256'])
        review['hostReceipts']['normal']['sha256'] = 'wrong'
        with self.assertRaisesRegex(RuntimeError, 'bind both tested'):
            r.admission(review, frozen, review['controllerSHA256'])

    def test_mid_retrieval_closes_admission_before_second_command(self):
        for field, value in [('hold', 'EPERM'), ('limit', 'output'), ('deadline', 0), ('api28_server_lost', True)]:
            with self.subTest(field=field):
                m = h.FakeCommands()
                m.records = [{'label': 'exact-api28-instrumentation', 'terminal_custody': True}]
                calls = []
                def adb(label, argv):
                    calls.append((label, argv))
                    setattr(m, field, value)
                    raise RuntimeError('first retrieval closes admission')
                receipt = {}
                r.retain_screenshots(m, adb, h.WORK, receipt)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][1], ['exec-out', 'run-as', r.PACKAGE, 'cat', 'files/' + r.SCREENSHOTS[0]])
                self.assertEqual(receipt['screenshots'][r.SCREENSHOTS[1]]['status'], 'pending')

    def test_handoff_timeout_retains_listener_and_only_owned_helper(self):
        class Channel:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def bind(self, path): pass
            def listen(self, n): pass
            def settimeout(self, n): pass
            def accept(self): raise TimeoutError('pre-exec handoff timeout')
        m = h.FakeCommands()
        listener = h.ReservedSocket(); listener.bind(('127.0.0.1', 64321))
        with patch.object(r.socket, 'socket', return_value=Channel()):
            with self.assertRaisesRegex(TimeoutError, 'pre-exec'):
                r.start_owned_server(m, h.WORK, listener, r.ADB, 'emulator-5678')
        self.assertEqual([x['label'] for x in m.records], ['owned-adb-server'])
        self.assertIs(m.api28_listener, listener)
        self.assertFalse(listener.closed)

    def test_helper_hash_refusal_precedes_socket_and_exec(self):
        helper = h.module('review_fd_exec_hash', PACKET / 'server_fd_exec.py')
        with patch.object(sys, 'argv', ['helper', 'channel', 'token', str(PACKET / 'server_fd_exec.py'), 'wrong', 'emulator-5678', '64321']), \
             patch.object(helper.socket, 'socket') as sock, patch.object(helper.os, 'execv') as execute:
            with self.assertRaisesRegex(RuntimeError, 'executable drift'): helper.main()
            sock.assert_not_called(); execute.assert_not_called()

    def test_helper_exec_failure_remains_same_owned_process(self):
        helper = h.module('review_fd_exec_failure', PACKET / 'server_fd_exec.py')
        class Channel:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def settimeout(self, n): pass
            def connect(self, path): pass
            def getsockname(self): return ('127.0.0.1', 64321)
        binary = str(r.ADB)
        with patch.object(sys, 'argv', ['helper', 'channel', 'token', binary, r.ADB_SHA, 'emulator-5678', '64321']), \
             patch.object(helper.socket, 'socket', return_value=Channel()), \
             patch.object(helper, 'receive', return_value=72), \
             patch.object(helper.os, 'set_inheritable') as inherit, \
             patch.object(helper.os, 'execv', side_effect=OSError('synthetic exec refusal')) as execute:
            with self.assertRaisesRegex(OSError, 'exec refusal'): helper.main()
            inherit.assert_called_once_with(72, True)
            execute.assert_called_once_with(binary, [binary, '-L', 'acceptfd:72', '-s', 'emulator-5678', '--one-device', 'emulator-5678', 'server', 'nodaemon'])

    def test_unknown_cleanup_keeps_scratch_listener_and_forbids_operations(self):
        scratch = h.WORK / 'sticky-unknown'; scratch.mkdir()
        m = c.Commands(h.WORK, {}, deadline=time.monotonic()+5)
        m.hold = {'operation': 'synthetic EPERM'}
        listener = h.ReservedSocket(); m.api28_listener = listener
        with patch.object(c.os, 'killpg', side_effect=AssertionError('held process operation')), \
             patch.object(c.subprocess, 'Popen', side_effect=AssertionError('held child launch')):
            result = r.cleanup(m, scratch)
            with self.assertRaisesRegex(RuntimeError, 'admission closed'): m.start('forbidden', [], scratch)
        self.assertFalse(result['allTerminalCustody'])
        self.assertFalse(result['scratchRemoved'])
        self.assertTrue(scratch.exists()); self.assertFalse(listener.closed)
        m.selector.close()
        shutil.rmtree(scratch)  # fake-only fixture; never a real held process



# This narrow selection model is an executable discriminant, not a native proof.
# Reference: retained official-client-commandline.cpp:1646-1683;
# official-socket_spec.cpp:165-193; official-client-adb_client.cpp:254-282.
# The retained exact-binary no-H/no-P probe independently corroborates the branch.
DESCENDANT_EVIDENCE = []


def selected_socket(argv, environment):
    host = port = spec = None
    cursor = 1
    while cursor < len(argv):
        option = argv[cursor]
        if option in ('-s', '-H', '-P', '-L'):
            value = argv[cursor + 1]
            if option == '-H': host = value
            elif option == '-P': port = value
            elif option == '-L': spec = value
            cursor += 2
        elif option in ('-e', '-d'):
            cursor += 1
        else:
            break
    if (host or port) and spec:
        raise RuntimeError('incompatible explicit socket selection')
    if host is None and port is None and spec is None:
        spec = environment.get('ADB_SERVER_SOCKET')
    if spec is None:
        host = host if host is not None else environment.get('ANDROID_ADB_SERVER_ADDRESS')
        port = port if port is not None else environment.get('ANDROID_ADB_SERVER_PORT', '5037')
        spec = 'tcp:' + (host + ':' if host is not None else '') + str(port)
    return spec


def absent_server_branch(argv, environment):
    spec = selected_socket(argv, environment)
    parts = spec.split(':')
    if parts[0] != 'tcp' or len(parts) not in (2,3):
        raise RuntimeError('outside the reviewed TCP selection model')
    host = '' if len(parts) == 2 else parts[1]
    local = host in ('', 'localhost')
    return {'socket':spec, 'host':host, 'serverConnectResult':-2,
            'branch':'launch_server' if local else 'remote-refusal',
            'wouldLaunchServer':local}


class EnvironmentManager(h.FakeCommands):
    def __init__(self, failure=None):
        super().__init__(failure)
        self.environment_at_launch = {}
        self.env.update(ADB_SERVER_SOCKET='tcp:localhost:5037',
                        ANDROID_ADB_SERVER_ADDRESS='foreign', ANDROID_SERIAL='foreign',
                        ANDROID_ADB_SERVER_PORT='5037', ADB_SERVER_PORT='5037',
                        ANDROID_PREFS_ROOT='foreign', ANDROID_SDK_HOME='foreign')
    def run(self, label, argv, cwd, timeout=120, allowed=(0,)):
        self.environment_at_launch[label] = dict(self.env)
        return super().run(label, argv, cwd, timeout, allowed)
    def start(self, label, argv, cwd, long_lived=False):
        self.environment_at_launch[label] = dict(self.env)
        return super().start(label, argv, cwd, long_lived)


class IndependentR3(unittest.TestCase):
    def test_all_key_server_emulator_and_client_launches_use_private_environment(self):
        manager = EnvironmentManager()
        receipt, error, _ = h.R2Controls.flow(self, manager)
        self.assertIsNone(error)
        self.assertEqual(receipt['status'], 'passed-development-runtime')
        self.assertEqual(set(manager.environment_at_launch), {x['label'] for x in manager.records})
        for label, env in manager.environment_at_launch.items():
            with self.subTest(label=label):
                self.assertEqual(env['ADB_SERVER_SOCKET'], 'tcp:127.0.0.1:64321')
                self.assertEqual(env['ANDROID_ADB_SERVER_ADDRESS'], '127.0.0.1')
                self.assertEqual(env['ANDROID_ADB_SERVER_PORT'], '64321')
                self.assertEqual(env['ADB_SERVER_PORT'], '64321')
                for key in ('ANDROID_SERIAL','ANDROID_PREFS_ROOT','ANDROID_SDK_HOME'):
                    self.assertNotIn(key, env)
        for flag in (['-s','emulator-5678'], ['-e']):
            argv = [str(r.ADB), *flag, 'shell', 'logcat', '-G', '2M']
            selected = absent_server_branch(argv, manager.environment_at_launch['owned-emulator'])
            self.assertEqual(selected['socket'], 'tcp:127.0.0.1:64321')
            self.assertFalse(selected['wouldLaunchServer'])
            DESCENDANT_EVIDENCE.append({'schedule':'emulator inherited environment', 'argv':argv, **selected})

    def test_late_descendant_after_unknown_and_parent_listener_release_refuses(self):
        manager = EnvironmentManager('exact-api28-instrumentation')
        receipt, error, _ = h.R2Controls.flow(self, manager)
        self.assertIsNotNone(error)
        self.assertEqual(receipt['status'], 'failed')
        self.assertTrue(manager.hold)
        self.assertEqual(manager.records[-1]['label'], 'exact-api28-instrumentation')
        descendant_environment = dict(manager.environment_at_launch['owned-emulator'])
        scratch = h.WORK/'late-descendant-scratch'; scratch.mkdir()
        lifecycle = c.Commands(h.WORK, manager.env, deadline=time.monotonic()+5)
        lifecycle.hold = {'operation':'synthetic UNKNOWN after server exit'}
        lifecycle.api28_listener = manager.api28_listener
        with patch.object(c.os, 'killpg', side_effect=AssertionError('process operation after UNKNOWN')), \
             patch.object(c.subprocess, 'Popen', side_effect=AssertionError('child launch after UNKNOWN')):
            cleanup = r.cleanup(lifecycle, scratch)
            self.assertFalse(cleanup['allTerminalCustody'])
            self.assertFalse(cleanup['scratchRemoved'])
            self.assertFalse(manager.api28_listener.closed)
            with self.assertRaisesRegex(RuntimeError, 'admission closed'):
                lifecycle.start('forbidden', [], scratch)
        # Model OS descriptor/environment disposal on outer interpreter exit.
        # No actual process, socket or held scratch is involved.
        manager.api28_listener.close()
        manager.env.clear()
        self.assertTrue(manager.api28_listener.closed)
        argv = [str(r.ADB), '-s', 'emulator-5678', 'shell', 'settings', 'put', 'system', 'screen_off_timeout', '2147483647']
        self.assertNotIn('-H', argv); self.assertNotIn('-P', argv)
        selected = absent_server_branch(argv, descendant_environment)
        self.assertEqual(selected['branch'], 'remote-refusal')
        self.assertFalse(selected['wouldLaunchServer'])
        self.assertEqual(selected['socket'], 'tcp:127.0.0.1:64321')
        DESCENDANT_EVIDENCE.append({'schedule':'owned server absent; UNKNOWN; outer exit releases listener; queued child resumes',
                                   'argv':argv, 'rootFollowupCommands':0, **selected})
        lifecycle.selector.close()
        shutil.rmtree(scratch)

    def test_discriminant_reproduces_r2_selection_and_checks_address_fallback(self):
        manager = EnvironmentManager()
        _, error, _ = h.R2Controls.flow(self, manager)
        self.assertIsNone(error)
        env = dict(manager.environment_at_launch['owned-emulator'])
        argv = [str(r.ADB), '-s', 'emulator-5678', 'get-state']
        r2env = {k:v for k,v in env.items() if k not in ('ADB_SERVER_SOCKET','ANDROID_ADB_SERVER_ADDRESS')}
        counterfactual = absent_server_branch(argv, r2env)
        self.assertTrue(counterfactual['wouldLaunchServer'])
        self.assertEqual(counterfactual['socket'], 'tcp:64321')
        fallback = dict(env); fallback.pop('ADB_SERVER_SOCKET')
        for args in (argv, [str(r.ADB), '-P', '64321', '-s', 'emulator-5678', 'get-state']):
            selected = absent_server_branch(args, fallback)
            self.assertEqual(selected['socket'], 'tcp:127.0.0.1:64321')
            self.assertFalse(selected['wouldLaunchServer'])
        DESCENDANT_EVIDENCE.append({'schedule':'R2 counterfactual negative control; model only', **counterfactual})


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (110, 115))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(RuntimeError('120s review control bound')))
    signal.alarm(120)
    h.WORK.mkdir(exist_ok=False)
    h.existing.OUT = h.WORK; h.existing.START = started
    excluded = {'test_historical_false_absence_failure_preserved', 'test_controller_import_is_inert_and_guards_survive_optimized', 'test_packet_exact_source101_sdk22_adapter24'}
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(h.existing.Controls) if n not in excluded]
    suite = unittest.TestSuite([h.existing.Controls(name) for name in names])
    for cls in (h.ControllerControls, h.R2Controls, h.R3Controls, Independent, IndependentR3):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    r.require(suite.countTestCases() == 62, 'all 53 candidate + 6 reused + 3 new controls required')
    original_pump = c.Commands.pump
    def pump(manager, seconds=.02):
        for child in h.fake.children.values(): child.tick()
        return original_pump(manager, seconds)
    with patch.object(c.subprocess, 'Popen', side_effect=h.fake.Child), \
         patch.object(c.os, 'killpg', side_effect=h.fake.group), \
         patch.object(c.Commands, 'pump', pump), \
         patch.object(c.subprocess, 'run', side_effect=RuntimeError('no helper launch')):
        result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    receipt = {'status': 'passed' if result.wasSuccessful() else 'failed', 'mode': MODE,
        'tests': result.testsRun, 'baselineControls': 34, 'producerR2Controls': 16, 'producerR3Controls': 3, 'reusedIndependentControls': 6, 'newIndependentControls': 3,
        'elapsedSeconds': time.monotonic()-started, 'python': sys.version,
        'command': [sys.executable, '-B', *(['-O'] if sys.flags.optimize else []), str(Path(__file__).resolve())],
        'reviewScript': r.identity(__file__), 'controller': r.identity(PACKET/'run_api28.py'),
        'lifecycle': r.identity(PACKET/'cleanup_control.py'), 'packet': r.identity(PACKET/'controller-packet.json'),
        'producerControls': r.identity(PACKET/'host_controls.py'),
        'failures': [(str(t),s) for t,s in result.failures], 'errors': [(str(t),s) for t,s in result.errors],
        'realNativeCommands': 0, 'realChildrenInsideControl': 0, 'realGroupOperationsInsideControl': 0,
        'descendantSelectionEvidence': DESCENDANT_EVIDENCE, 'lifecycleRecords': h.existing.Controls.all_records, 'lifecycleCleanup': h.existing.Controls.cleanups}
    shutil.rmtree(h.WORK)
    receipt['fakeScratchRemoved'] = not h.WORK.exists()
    r.save(OUT/('independent-'+MODE+'.json'), receipt)
    signal.alarm(0)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__': sys.exit(main())
