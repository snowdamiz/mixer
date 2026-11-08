#!/usr/bin/env python3
"""Two allowed invocations: normal and -O; all process/group operations fake."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(HERE))
import cleanup_control as c
import run_api28 as r


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


fake = module('existing_fake', BASE / 'native-custody-premise/optimized_fake_controls.py')
existing = module('existing_controls', BASE / 'native-custody-premise/host_controls.py')
MODE = 'optimized' if sys.flags.optimize else 'normal'
WORK = HERE / ('fake-' + MODE)
OUT_TEXT = '\n'.join('INSTRUMENTATION_RESULT: ' + text for text in (
    'gate=PAIR8-LOWER-API-ART-LINKAGE', 'sdk=28', 'abi=arm64-v8a', 'checks=4')) + '\nINSTRUMENTATION_CODE: -1'
ASSERTIONS = ('real JNI/Swift session is nonzero', 'real Observer exactly refuses below36',
    'motion factory exactly refuses below33 without linkage failure',
    'all exercised paths completed without ART linkage errors')
APP_LOG = '\n'.join('11-07 00:00:00.000 123 123 I MixerLowerApi: PASS ' + text for text in ASSERTIONS)


class FakeCommands:
    def __init__(self, failure=None, property_change=None):
        self.env = {}; self.records = []; self.owned = []; self.hold = None; self.limit = None
        self.deadline = time.monotonic() + 600; self.cleanup_seconds = 5
        self.failure = failure; self.property_change = property_change; self.avd = None
    def run(self, label, argv, cwd, timeout=120, allowed=(0,)):
        self.records.append({'label': label, 'argv': list(map(str, argv)), 'timeout': timeout, 'terminal_custody': True})
        if self.failure == label:
            if label == 'exact-api28-instrumentation':
                self.hold = 'synthetic UNKNOWN'
            raise RuntimeError('synthetic command failure')
        output = ''
        if label == 'owned-avd-create':
            self.avd = str(argv[argv.index('--name') + 1])
            path = Path(argv[argv.index('--path') + 1]); path.mkdir(parents=True)
            (path / 'config.ini').write_text('frozen-test-config\n')
        elif label.startswith('boot-'): output = '1'
        elif label == 'private-server-devices': output = 'List of devices attached\nemulator-5678\tdevice'
        elif label.startswith('identity-'):
            props = {'ro.kernel.qemu':'1', 'ro.boot.qemu.avd_name':self.avd,
                     'ro.build.version.sdk':'28', 'ro.product.cpu.abi':'arm64-v8a', 'ro.build.fingerprint':'fake'}
            if self.property_change: props.update(self.property_change)
            output = props[label[len('identity-'):]]
        elif label == 'install-accepted-apk': output = 'Success'
        elif label == 'installed-uid': output = 'package:' + r.PACKAGE + ' uid:12345'
        elif label == 'exact-api28-instrumentation': output = OUT_TEXT
        elif label == 'all-assertion-logs': output = APP_LOG
        data = b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\x00IEND\xaeB`\x82' if label.startswith('retrieve-') else output.encode()
        self.owned.append({'buffers':{'stdout':bytearray(data)}, 'record':{'label':label}})
        return output
    def start(self, label, argv, cwd, long_lived=False):
        r.require(not self.hold, 'launch forbidden after hold')
        self.records.append({'label':label,'argv':list(map(str,argv)),'long_lived':long_lived})
        item = {'record':{'label':label},'buffers':{'stdout':bytearray()}}
        self.owned.append(item); return item
    def pause(self, seconds): pass
    def reaped(self, item): return False
    def captured(self, label):
        if label == 'exact-api28-instrumentation': return OUT_TEXT if not self.hold else 'failureStage=runtime-identity'
        return APP_LOG if label == 'app-logcat-before-startup' else ''


def fake_start_server(commands, work, listener, binary, serial):
    commands.api28_listener = listener
    return commands.start('owned-adb-server', [sys.executable, '-B', r.HERE / 'server_fd_exec.py',
        'fake-channel', 'fake-token', binary, r.ADB_SHA, serial, listener.getsockname()[1]], work, long_lived=True)


class ControllerControls(unittest.TestCase):
    def test_actual_frozen_binding_and_postflight(self):
        frozen = r.load(HERE / 'controller-packet.json')
        packet = r.verify_bindings(frozen)
        self.assertEqual(packet['apk']['sha256'], r.APK_SHA)
        self.assertEqual(r.identity(HERE / 'cleanup_control.py')['sha256'], r.LIFECYCLE_SHA)
    def test_hash_tamper_refuses_before_any_launch(self):
        frozen = {'bindings':{str(HERE / 'run_api28.py'):{'bytes':0,'sha256':'bad'}}}
        with self.assertRaisesRegex(RuntimeError, 'input drift'):
            r.verify_bindings(frozen)
    def test_review_refusal(self):
        with self.assertRaisesRegex(RuntimeError, 'ACCEPT required'): r.admission({}, {}, 'bad')
        with self.assertRaisesRegex(RuntimeError, 'exact bytes mismatch'):
            r.admission({'verdict':'ACCEPT','scope':'ONE_API28_ARM64_RUNTIME_ATTEMPT'}, {}, 'bad')
    def test_each_identity_dimension_refuses(self):
        good = {'ro.kernel.qemu':'1','ro.boot.qemu.avd_name':'owned','ro.build.version.sdk':'28','ro.product.cpu.abi':'arm64-v8a'}
        r.runtime_identity(good, 'owned')
        for key in good:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                r.runtime_identity({**good, key:'wrong'}, 'owned')
    def test_result_retains_pair8_but_binds_pair9(self):
        result = r.instrumentation_result(OUT_TEXT, APP_LOG)
        self.assertEqual(result['historicalEmittedPair'], 8)
        self.assertEqual(result['actualAPKSourcePair'], 9)
        self.assertEqual(result['assertions'], list(ASSERTIONS))
    def test_failures_and_missing_assertions_refuse(self):
        for output, log in ((OUT_TEXT.replace('-1','0'),APP_LOG),
            (OUT_TEXT+'\nINSTRUMENTATION_RESULT: cleanupFailure=failed',APP_LOG),
            (OUT_TEXT+'\nINSTRUMENTATION_RESULT: failureStage=cold-start',APP_LOG),
            (OUT_TEXT,APP_LOG.rsplit('\n',1)[0]),(OUT_TEXT.replace('checks=4','checks=0'),APP_LOG)):
            with self.subTest(output=output), self.assertRaises(RuntimeError): r.instrumentation_result(output,log)
    def test_interrupted_cleanup_is_failure(self):
        class Broken:
            def cleanup(self, path): raise KeyboardInterrupt()
        self.assertEqual(r.cleanup(Broken(), WORK)['scratchRemoved'], False)
    def flow(self, failure=None, identity=None):
        work = Path(tempfile.mkdtemp(dir=WORK)); out = work / 'evidence'; out.mkdir()
        manager = FakeCommands(failure, identity); receipt = {}
        class Socket:
            def bind(self, address): self.port = address[1] or 64321
            def listen(self, count): pass
            def getsockname(self): return ('127.0.0.1', self.port)
            def close(self): pass
        try:
            with patch.object(r.socket, 'socket', Socket), patch.object(r, 'start_owned_server', fake_start_server):
                try:
                    r.execute(manager, work, out, {'apk':{'path':'accepted.apk'}},time.monotonic()+600,receipt,lambda:None)
                except RuntimeError:
                    if failure is None and identity is None: raise
            return manager, receipt, list(out.iterdir())
        finally:
            shutil.rmtree(work)
    def test_exact_success_command_selection(self):
        manager, receipt, files = self.flow()
        labels = [x['label'] for x in manager.records]
        self.assertEqual(receipt['status'],'passed-development-runtime')
        self.assertEqual(labels.count('exact-api28-instrumentation'),1)
        self.assertEqual(labels.count('owned-emulator'),1)
        self.assertLess(labels.index('app-logcat-before-startup'),labels.index('exact-api28-instrumentation'))
        self.assertEqual({p.name for p in files} & set(r.SCREENSHOTS),set(r.SCREENSHOTS))
        for command in manager.records:
            argv = command['argv']
            self.assertFalse(any(x in argv for x in ('javac','keytool','apksigner','settings','kill-server')))
            if Path(argv[0]).name == 'adb' and command['label'] != 'owned-adb-key':
                self.assertEqual(argv[1:7],['-H','127.0.0.1','-P','64321','-s','emulator-5678'])
    def test_identity_failure_never_installs(self):
        manager, _, _ = self.flow(identity={'ro.build.version.sdk':'37'})
        self.assertNotIn('install-accepted-apk',[x['label'] for x in manager.records])
    def test_instrumentation_unknown_has_no_followup_command(self):
        manager, receipt, _ = self.flow(failure='exact-api28-instrumentation')
        self.assertEqual(manager.records[-1]['label'],'exact-api28-instrumentation')
        self.assertIn('failureStage',receipt['instrumentationOutput'])
    def test_create_failure_never_starts_service(self):
        manager, _, _ = self.flow(failure='owned-avd-create')
        self.assertNotIn('owned-emulator',[x['label'] for x in manager.records])


class ReservedSocket:
    def __init__(self, *args, **kwargs): self.closed = False
    def bind(self, address): self.port = address[1] or 64321
    def listen(self, count): pass
    def getsockname(self): return ('127.0.0.1', self.port)
    def close(self): self.closed = True


class R2Controls(unittest.TestCase):
    def flow(self, manager):
        work = Path(tempfile.mkdtemp(dir=WORK)); out = work / 'evidence'; out.mkdir()
        receipt = {}; error = None
        try:
            with patch.object(r.socket, 'socket', ReservedSocket), patch.object(r, 'start_owned_server', fake_start_server):
                try:
                    r.execute(manager, work, out, {'apk': {'path': 'accepted.apk'}},
                              time.monotonic() + 600, receipt, lambda: None)
                except RuntimeError as caught: error = str(caught)
            files = {p.name: p.read_bytes() for p in out.iterdir()}
            return receipt, error, files
        finally: shutil.rmtree(work)

    def test_lost_server_before_client_refuses(self):
        class Manager(FakeCommands):
            dead = False
            def reaped(self, item): return self.dead and item['record']['label'] == 'owned-adb-server'
            def start(self, label, argv, cwd, long_lived=False):
                result = super().start(label, argv, cwd, long_lived)
                if label == 'owned-emulator': self.dead = True
                return result
        manager = Manager(); receipt, error, _ = self.flow(manager)
        self.assertIn('server lost', error)
        self.assertEqual(receipt['status'], 'failed')
        self.assertFalse(any(x['label'].startswith('boot-') for x in manager.records))
        self.assertFalse(manager.api28_listener.closed)

    def test_loss_between_check_and_connect_refuses_no_replacement(self):
        class Manager(FakeCommands):
            dead = False
            def reaped(self, item): return self.dead and item['record']['label'] == 'owned-adb-server'
            def run(self, label, argv, cwd, timeout=120, allowed=(0,)):
                result = super().run(label, argv, cwd, timeout, allowed)
                if label == 'boot-0':
                    self.dead = True
                    raise RuntimeError('remote client connection lost')
                return result
        manager = Manager(); receipt, error, _ = self.flow(manager)
        self.assertIn('server lost', error)
        self.assertEqual(manager.records[-1]['label'], 'boot-0')
        self.assertEqual(manager.records[-1]['argv'][1:7], ['-H', '127.0.0.1', '-P', '64321', '-s', 'emulator-5678'])
        self.assertTrue(manager.api28_server_lost)
        self.assertFalse(manager.api28_listener.closed)
        self.assertEqual(receipt['status'], 'failed')

    def test_unexpected_client_env_is_removed_and_exact_args_win(self):
        manager = FakeCommands()
        manager.env.update(ADB_SERVER_SOCKET='tcp:foreign:5037', ANDROID_ADB_SERVER_ADDRESS='foreign',
                           ANDROID_ADB_SERVER_PORT='5037', ADB_SERVER_PORT='5037', ANDROID_SERIAL='foreign')
        receipt, error, _ = self.flow(manager)
        self.assertIsNone(error)
        self.assertEqual(receipt['status'], 'passed-development-runtime')
        self.assertNotIn('ANDROID_SERIAL', manager.env)
        self.assertEqual(manager.env['ADB_SERVER_SOCKET'], 'tcp:127.0.0.1:64321')
        self.assertEqual(manager.env['ANDROID_ADB_SERVER_ADDRESS'], '127.0.0.1')
        self.assertEqual(manager.env['ANDROID_ADB_SERVER_PORT'], '64321')
        for command in manager.records:
            if Path(command['argv'][0]).name == 'adb' and command['label'] != 'owned-adb-key':
                self.assertEqual(command['argv'][1:7], ['-H','127.0.0.1','-P','64321','-s','emulator-5678'])

    def test_valid_same_bound_server_client_bytes(self):
        manager = FakeCommands(); receipt, error, _ = self.flow(manager)
        self.assertIsNone(error)
        server = next(x for x in manager.records if x['label'] == 'owned-adb-server')
        binary = receipt['serverTransport']['binary']
        self.assertIn(binary, server['argv']); self.assertIn(r.ADB_SHA, server['argv'])
        self.assertTrue(receipt['serverTransport']['retainedListener'])
        for command in manager.records:
            if Path(command['argv'][0]).name == 'adb': self.assertEqual(command['argv'][0], binary)

    def test_changed_client_version_refuses_before_client(self):
        class Manager(FakeCommands):
            def start(self, label, argv, cwd, long_lived=False):
                result = super().start(label, argv, cwd, long_lived)
                if label == 'owned-emulator':
                    target = Path(cwd) / 'adb'; target.chmod(0o600); target.write_bytes(b'foreign version')
                return result
        manager = Manager(); _, error, _ = self.flow(manager)
        self.assertIn('sealed ADB binary drift', error)
        self.assertFalse(any(x['label'].startswith('boot-') for x in manager.records))

    def failure_images(self, available):
        class Manager(FakeCommands):
            output = ''
            def run(self, label, argv, cwd, timeout=120, allowed=(0,)):
                value = super().run(label, argv, cwd, timeout, allowed)
                if label == 'exact-api28-instrumentation':
                    self.output = value.replace('INSTRUMENTATION_CODE: -1',
                        'INSTRUMENTATION_RESULT: failureStage=harness-lifecycle-cleanup\nINSTRUMENTATION_CODE: 0')
                    return self.output
                if label.startswith('retrieve-'):
                    if label[len('retrieve-'):] not in available: raise RuntimeError('PNG not authored')
                    self.owned[-1]['buffers']['stdout'] = bytearray(PNG_BYTES)
                return value
            def captured(self, label):
                return self.output if label == 'exact-api28-instrumentation' else super().captured(label)
        manager = Manager(); receipt, error, files = self.flow(manager)
        self.assertIn('did not finish', error)
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(set(files) & set(r.SCREENSHOTS), set(available))
        for name in available: self.assertEqual(files[name], PNG_BYTES)
        self.assertIn('failureStage=harness-lifecycle-cleanup', receipt['instrumentationOutput'])
        self.assertTrue(receipt['screenshotsNeedIndependentVisualReview'])
        self.assertEqual(sum(x['label'] == 'exact-api28-instrumentation' for x in manager.records), 1)
        self.assertEqual([x['label'] for x in manager.records if x['label'].startswith('retrieve-')],
                         ['retrieve-' + name for name in r.SCREENSHOTS])

    def test_late_failure_before_captures(self): self.failure_images(())
    def test_late_failure_after_first_capture_exact_bytes(self): self.failure_images(r.SCREENSHOTS[:1])
    def test_late_failure_after_both_captures_exact_bytes(self): self.failure_images(r.SCREENSHOTS)

    def test_known_terminal_nonzero_instrumentation_retains_images(self):
        class Manager(FakeCommands):
            def run(self, label, argv, cwd, timeout=120, allowed=(0,)):
                value = super().run(label, argv, cwd, timeout, allowed)
                if label == 'exact-api28-instrumentation': raise RuntimeError('terminal nonzero exit')
                return value
        manager = Manager(); receipt, error, files = self.flow(manager)
        self.assertEqual(error, 'terminal nonzero exit')
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(set(files) & set(r.SCREENSHOTS), set(r.SCREENSHOTS))

    def test_unknown_eperm_no_image_or_other_followup_command(self):
        manager = FakeCommands(failure='exact-api28-instrumentation')
        receipt, error, files = self.flow(manager)
        self.assertIsNotNone(error)
        self.assertEqual(manager.records[-1]['label'], 'exact-api28-instrumentation')
        self.assertFalse(set(files) & set(r.SCREENSHOTS))
        self.assertEqual(receipt['status'], 'failed')

    def test_nonterminal_instrumentation_no_retrieval(self):
        manager = FakeCommands(); manager.records = [{'label': 'exact-api28-instrumentation', 'terminal_custody': False}]
        receipt = {}
        r.retain_screenshots(manager, lambda *args: self.fail('nonterminal retrieval'), WORK, receipt)
        self.assertIn('not terminal', receipt['screenshotRetrievalSkipped'])

    def test_closed_budgets_and_hold_no_retrieval(self):
        for field, value in (('hold', 'EPERM'), ('limit', 'output-limit'), ('deadline', 0), ('api28_server_lost', True)):
            manager = FakeCommands(); setattr(manager, field, value)
            manager.records = [{'label': 'exact-api28-instrumentation', 'terminal_custody': True}]
            r.retain_screenshots(manager, lambda *args: self.fail('closed admission retrieval'), WORK, {})

    def test_listener_closed_only_after_terminal_cleanup(self):
        for terminal in (False, True):
            class Manager:
                api28_listener = ReservedSocket()
                def cleanup(self, work): return {'allTerminalCustody': terminal, 'scratchRemoved': terminal}
            manager = Manager(); result = r.cleanup(manager, WORK)
            self.assertEqual(manager.api28_listener.closed, terminal)
            self.assertEqual(result['allTerminalCustody'], terminal)

    def test_foreign_handoff_client_refused_without_fd(self):
        class Channel:
            sent = False
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def bind(self, path): pass
            def listen(self, count): pass
            def settimeout(self, timeout): pass
            def accept(self): return self, None
            def recv(self, count): return b'x' * count
            def sendmsg(self, *args): self.sent = True; return 1
        channel = Channel(); listener = ReservedSocket(); listener.bind(('127.0.0.1', 64321))
        with patch.object(r.socket, 'socket', return_value=channel):
            with self.assertRaisesRegex(RuntimeError, 'foreign descriptor'):
                r.start_owned_server(FakeCommands(), WORK, listener, r.ADB, 'emulator-5678')
        self.assertFalse(channel.sent)
        self.assertFalse(listener.closed)

    def test_handoff_sends_only_retained_listener_to_owned_server(self):
        class Channel:
            sent = None
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def bind(self, path): Path(path).touch()
            def listen(self, count): pass
            def settimeout(self, timeout): pass
            def accept(self): return self, None
            def recv(self, count): return b'1' * count
            def sendmsg(self, payload, ancillary): self.sent = (payload, ancillary); return 1
        channel = Channel(); listener = ReservedSocket(); listener.bind(('127.0.0.1', 64321))
        listener.fileno = lambda: 72
        manager = FakeCommands()
        with patch.object(r.socket, 'socket', return_value=channel), patch.object(r.os, 'urandom', return_value=b'\x11' * 32):
            server = r.start_owned_server(manager, WORK, listener, r.ADB, 'emulator-5678')
        self.assertEqual(server['record']['label'], 'owned-adb-server')
        self.assertIs(manager.api28_listener, listener)
        self.assertFalse(listener.closed)
        self.assertEqual(channel.sent[0], [b'F'])
        self.assertEqual(list(channel.sent[1][0][2]), [72])
        self.assertEqual(manager.records[0]['argv'][1:3], ['-I', '-B'])

    def test_descriptor_receive_rejects_missing_truncated_and_foreign(self):
        import array
        fd_exec = module('r2_fd_exec', HERE / 'server_fd_exec.py')
        class Channel:
            def sendall(self, value): pass
            def recvmsg(self, *args): return self.response
        channel = Channel()
        good = (r.socket.SOL_SOCKET, r.socket.SCM_RIGHTS, array.array('i', [72]).tobytes())
        for response in ((b'F', [], 0, None), (b'F', [good], r.socket.MSG_CTRUNC, None),
                         (b'X', [good], 0, None), (b'F', [(0, 0, b'')], 0, None)):
            channel.response = response
            with self.assertRaises(RuntimeError): fd_exec.receive(channel, 'token')
        channel.response = (b'F', [good], 0, None)
        self.assertEqual(fd_exec.receive(channel, 'token'), 72)


class R3Controls(unittest.TestCase):
    def descendant_environment(self, failure=None):
        class Manager(FakeCommands):
            inherited = None
            def start(self, label, argv, cwd, long_lived=False):
                value = super().start(label, argv, cwd, long_lived)
                if label == 'owned-emulator':
                    self.inherited = dict(self.env)
                return value
        manager = Manager(failure)
        manager.env.update(ADB_SERVER_SOCKET='tcp:localhost:5037',
                           ANDROID_ADB_SERVER_ADDRESS='foreign', ANDROID_SERIAL='foreign')
        receipt, error, files = R2Controls.flow(self, manager)
        self.assertIsNotNone(manager.inherited)
        self.assertEqual(manager.inherited['ADB_SERVER_SOCKET'], 'tcp:127.0.0.1:64321')
        self.assertEqual(manager.inherited['ANDROID_ADB_SERVER_ADDRESS'], '127.0.0.1')
        self.assertEqual(manager.inherited['ANDROID_ADB_SERVER_PORT'], '64321')
        self.assertNotIn('ANDROID_SERIAL', manager.inherited)
        return manager, receipt, error, files

    def test_emulator_descendant_inherits_numeric_socket_at_start(self):
        manager, receipt, error, _ = self.descendant_environment()
        self.assertIsNone(error)
        self.assertEqual(receipt['status'], 'passed-development-runtime')
        self.assertEqual(manager.inherited['ADB_SERVER_SOCKET'], manager.env['ADB_SERVER_SOCKET'])

    def test_queued_descendant_keeps_numeric_selection_after_unknown_exit(self):
        manager, receipt, error, _ = self.descendant_environment('exact-api28-instrumentation')
        self.assertIsNotNone(error)
        inherited = dict(manager.inherited)
        manager.env.clear()
        manager.api28_listener.close()
        # A previously launched child's environment survives parent teardown.
        self.assertEqual(inherited['ADB_SERVER_SOCKET'], 'tcp:127.0.0.1:64321')
        self.assertEqual(manager.records[-1]['label'], 'exact-api28-instrumentation')
        self.assertEqual(receipt['status'], 'failed')

    def test_key_and_private_server_share_sanitized_numeric_environment(self):
        class Manager(FakeCommands):
            key_environment = None
            def run(self, label, argv, cwd, timeout=120, allowed=(0,)):
                if label == 'owned-adb-key': self.key_environment = dict(self.env)
                return super().run(label, argv, cwd, timeout, allowed)
        manager = Manager()
        receipt, error, _ = R2Controls.flow(self, manager)
        self.assertIsNone(error)
        self.assertEqual(manager.key_environment['ADB_SERVER_SOCKET'], 'tcp:127.0.0.1:64321')
        self.assertEqual(manager.key_environment['ANDROID_ADB_SERVER_ADDRESS'], '127.0.0.1')


PNG_BYTES = b'\x89PNG\r\n\x1a\n' + bytes(range(256)) + b'\x00\x00\x00\x00IEND\xaeB`\x82'


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (110,115))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(RuntimeError('120s fake-host bound')))
    signal.alarm(120)
    WORK.mkdir(exist_ok=False)
    existing.OUT = WORK
    existing.START = started
    # These three old tests concern historical/controller sources; new tests above replace them.
    excluded = {'test_historical_false_absence_failure_preserved',
        'test_controller_import_is_inert_and_guards_survive_optimized',
        'test_packet_exact_source101_sdk22_adapter24'}
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(existing.Controls) if n not in excluded]
    suite = unittest.TestSuite([existing.Controls(name) for name in names])
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ControllerControls))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(R2Controls))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(R3Controls))
    original_pump = c.Commands.pump
    def pump(manager, seconds=.02):
        for child in fake.children.values(): child.tick()
        return original_pump(manager, seconds)
    with patch.object(c.subprocess,'Popen',side_effect=fake.Child), \
         patch.object(c.os,'killpg',side_effect=fake.group), \
         patch.object(c.Commands,'pump',pump), \
         patch.object(c.subprocess,'run',side_effect=RuntimeError('no helper launch')):
        result = unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    receipt = {'status':'passed' if result.wasSuccessful() else 'failed','mode':MODE,
        'tests':result.testsRun,'elapsedSeconds':time.monotonic()-started,'python':sys.version,
        'controllerSHA256':r.identity(HERE/'run_api28.py')['sha256'],
        'lifecycleSHA256':r.identity(HERE/'cleanup_control.py')['sha256'],
        'packetSHA256':r.identity(HERE/'controller-packet.json')['sha256'],
        'controlsSHA256':r.identity(__file__)['sha256'],'realNativeCommands':0,
        'realChildren':0,'realGroupOperations':0,
        'baselineControlsRetained':34,'r2ControlsRetained':16,'r3Controls':3,'r2Controls':unittest.defaultTestLoader.getTestCaseNames(R2Controls),
        'baselineControls':names + unittest.defaultTestLoader.getTestCaseNames(ControllerControls),
        'descriptorHelperSHA256':r.identity(HERE/'server_fd_exec.py')['sha256'],
        'command':[sys.executable,'-B',*(['-O'] if sys.flags.optimize else []),str(Path(__file__).resolve())],
        'failures':[(str(t),s) for t,s in result.failures], 'errors':[(str(t),s) for t,s in result.errors],
        'lifecycleRecords':existing.Controls.all_records,'lifecycleCleanup':existing.Controls.cleanups}
    # Fake files only; no OS process custody is inferred from their cleanup.
    shutil.rmtree(WORK)
    receipt['fakeScratchRemoved'] = not WORK.exists()
    r.save(HERE/('host-'+MODE+'.json'),receipt)
    signal.alarm(0)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__': sys.exit(main())
