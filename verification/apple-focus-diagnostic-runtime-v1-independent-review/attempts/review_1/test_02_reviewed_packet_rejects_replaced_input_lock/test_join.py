"""Host-only adversarial controls. Native command boundaries are mocked."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch
import uuid
import secrets

import prepare

SELECTED = prepare.SCRATCH / 'selected'
sys.path.insert(0, str(SELECTED))
import composition
import join_support as support
import command_observer as observer


class JoinControls(unittest.TestCase):
    def setUp(self):
        self.folder = prepare.BASE / 'host-cases' / self._testMethodName
        self.folder.mkdir(parents=True, exist_ok=False)
        support._selected = None

    def tearDown(self):
        support._selected = None

    def archive(self, members):
        path = self.folder / 'input.tar.gz'
        with tarfile.open(path, 'w:gz') as archive:
            for info, value in members:
                archive.addfile(info, None if value is None else io.BytesIO(value))
        return path

    def entry(self, name='a/file', value=b'fixed', mode=0o644, kind=None):
        info = tarfile.TarInfo(name)
        info.mode, info.size = mode, len(value)
        if kind is not None: info.type = kind
        return info, value if info.isfile() else None

    def synthetic_manifest(self):
        return {'a/file': {'kind': 'file', 'bytes': 5, 'mode': 0o644, 'sha256': prepare.sha(b'fixed')}}

    def test_archive_exact_bytes_modes_and_directories(self):
        directory = tarfile.TarInfo('a'); directory.type = tarfile.DIRTYPE; directory.mode = 0o755
        path = self.archive([(directory, None), self.entry()])
        self.assertEqual(prepare.archive_payload(path, self.synthetic_manifest(), prepare.sha(path.read_bytes())), {'a/file': b'fixed'})

    def test_archive_bad_payload_rejected_before_materialization(self):
        path = self.archive([self.entry(value=b'wrong')])
        with self.assertRaises(ValueError): prepare.archive_payload(path, self.synthetic_manifest(), prepare.sha(path.read_bytes()))
        self.assertFalse((self.folder / 'destination').exists())

    def test_archive_changed_mode_rejected(self):
        path = self.archive([self.entry(mode=0o755)])
        with self.assertRaisesRegex(ValueError, 'mode'): prepare.archive_payload(path, self.synthetic_manifest(), prepare.sha(path.read_bytes()))

    def test_archive_duplicate_rejected(self):
        path = self.archive([self.entry(), self.entry()])
        with self.assertRaisesRegex(ValueError, 'Duplicate'): prepare.archive_payload(path, self.synthetic_manifest(), prepare.sha(path.read_bytes()))

    def test_archive_parent_traversal_rejected(self):
        path = self.archive([self.entry(name='../outside')])
        with self.assertRaisesRegex(ValueError, 'Unsafe'): prepare.archive_payload(path, self.synthetic_manifest(), prepare.sha(path.read_bytes()))

    def test_archive_symlink_substitution_rejected(self):
        info, _ = self.entry(kind=tarfile.SYMTYPE)
        info.linkname = '/tmp/outside'
        path = self.archive([(info, None)])
        with self.assertRaises(ValueError): prepare.archive_payload(path, self.synthetic_manifest(), prepare.sha(path.read_bytes()))

    def test_archive_extra_or_missing_directory_rejected(self):
        directory = tarfile.TarInfo('unexpected'); directory.type = tarfile.DIRTYPE; directory.mode = 0o755
        path = self.archive([(directory, None), self.entry()])
        with self.assertRaisesRegex(ValueError, 'directory'): prepare.archive_payload(path, self.synthetic_manifest(), prepare.sha(path.read_bytes()))

    def test_archive_directory_mode_rejected(self):
        directory = tarfile.TarInfo('a'); directory.type = tarfile.DIRTYPE; directory.mode = 0o777
        path = self.archive([(directory, None), self.entry()])
        with self.assertRaisesRegex(ValueError, 'mode'): prepare.archive_payload(path, self.synthetic_manifest(), prepare.sha(path.read_bytes()))

    def test_packet_exact_products_and_six_accepted_sources(self):
        self.assertTrue(support.verify_products(composition.selection))
        prepared = json.loads((prepare.ROOT / 'verification/apple-toggle-keyboard-focus-diagnostic-v1/prepared.json').read_bytes())
        for name, row in prepared['preparedSources'].items():
            self.assertEqual(prepare.sha((prepare.SCRATCH / 'accepted' / name).read_bytes()), row['sha256'])
        self.assertEqual(prepared['preparedSourceTreeSHA256'], prepare.SIX_SHA)
        original = json.loads((prepare.V3 / 'runtime-selection.json').read_bytes())
        for name, digest in original['files'].items():
            if 'oracle.py' in name: self.assertEqual(prepare.sha((SELECTED / name).read_bytes()), digest)

    def test_bridge_accepts_only_exact_diagnostic_container_set(self):
        doc = self.folder / 'documents'; doc.mkdir()
        bridge = composition.transport.Bridge({'diagnostic': doc}, self.folder / 'captures', 'a' * 64,
            {'udid': 'host-only', 'name': 'host-only', 'runtime': 'mock', 'build': 'mock'}, allowed_cases={prepare.CASE})
        self.assertEqual(set(bridge.documents), {'diagnostic'})
        for containers in [{}, {'comparator': doc}, {'diagnostic': doc, 'comparator': doc}, {'diagnostic': doc, 'other': doc}]:
            with self.assertRaises(ValueError):
                composition.transport.Bridge(containers, self.folder / 'rejected', 'a' * 64, {}, allowed_cases={prepare.CASE})
        self.assertFalse((self.folder / 'rejected').exists())

    def test_selected_import_has_no_native_or_service_calls(self):
        script = """
import http.server,ssl,socket,subprocess,sys
def forbidden(*a,**k):raise AssertionError('Native/process/service boundary called on import')
subprocess.Popen=forbidden;socket.socket=forbidden
sys.path.insert(0,sys.argv[1])
import composition
assert composition.h.SCOPES['interaction']['methods']==['test000PublicSettingsFullKeyboardAccess','test010EnabledFromOff']
assert composition.h.SCOPES['interaction']['cases']=={'keyboard-enabled-off'}
assert set(composition.h.packet.CONFIGS)=={'diagnostic'}
print('PASS import only; zero native/process/service boundaries')
"""
        result = subprocess.run([sys.executable, '-B', '-c', script, str(SELECTED)], cwd=prepare.ROOT,
                                text=True, capture_output=True, timeout=10)
        (self.folder / 'stdout.log').write_text(result.stdout)
        (self.folder / 'stderr.log').write_text(result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_retained_failed_oracle_and_real_cursor_remain_closed(self):
        captures = prepare.V3 / 'runtime/captures'
        retained = json.loads((captures / '0001-keyboard-witness-1.json').read_bytes())
        before = json.loads((captures / '0001-before-1.json').read_bytes())['observation']
        after = json.loads((captures / '0001-after-1.json').read_bytes())
        before.update(keyboardWitness=retained['witness'], keyboardBinding=retained['binding'])
        result = composition.oracle.verdict('diagnostic', prepare.CASE, 'native-keyboard', before, after['observation'])
        self.assertEqual([k for k, v in result['predicates'].items() if v is not True], ['actualNativeFocusTraversal'])
        class Parent:
            def __init__(self):
                cursor = composition.oracle.Cursor(prepare.CASE)
                for command in cursor.setup: cursor.command(command)
                self.current = {'case': prepare.CASE, 'baseline': before, 'keyboardCursor': cursor,
                                'actionIndex': 1, 'keyboardBaselineUptime': retained['binding']['baselineUptime']}
                self.generation = retained['binding']['generation']; self.saved = []
            def _request(self, op, body):
                if op == 'evaluate': return result
                raise ValueError('Unselected request')
            def save(self, name, value): self.saved.append((name, value))
        Wrapped = composition.keyboard_bridge.keyboard_bridge(Parent, composition.transport)
        bridge = Wrapped()
        witness = retained['witness']
        extra = {'schema': 'mixer.apple-toggle.focus-diagnostic.1', 'authoritative': False,
                 **{key: retained['binding'][key] for key in ['case', 'generation', 'actionIndex']},
                 'followUp': {'captureStatus': 'complete', 'rows': [{'identifier': 'authored-toggle', 'hasFocus': True}]}}
        observed = bridge._request('evaluate', {'keyboardWitness': witness, 'focusDiagnostic': extra})
        self.assertIs(observed, result)
        cursor = bridge.current['keyboardCursor']
        self.assertTrue(cursor.failed); self.assertFalse(cursor.complete); self.assertFalse(cursor.acquired)
        with self.assertRaises(ValueError): cursor.baseline_allowed()
        self.assertEqual(cursor.acquisitions, 0)
        self.assertEqual(witness['phase'], 'acquire'); self.assertEqual(witness['key'], 'tab')
        self.assertEqual(set(witness['after']['elements']), set(composition.oracle.IDS))
        self.assertIsNone(composition.oracle.focused(witness['after']))

    def test_app_restore_reuses_strict_content_and_macho_contract(self):
        restored = composition.CandidateApps.restore(self.folder / 'app', 'diagnostic')
        self.assertTrue(restored['exactManifest'])
        app = self.folder / 'app/MixerToggleDiagnostics.app'
        self.assertTrue((app / 'MixerToggleDiagnostics.dSYM').is_dir())
        (app / 'unexpected').write_text('extra')
        with self.assertRaises(composition.artifact.ValidationError): composition.artifact.verify_restored(app, 'diagnostic')

    def test_session_configuration_exact_allowed_derivation(self):
        original = plistlib.loads(next(composition.h.PRODUCTS.glob('*.xctestrun')).read_bytes())
        derived = support.derive_configuration(original, composition.h.PRODUCTS, 12345, 'a' * 64)
        target = derived['MixerToggleUITests']
        self.assertEqual(target['DefaultTestExecutionTimeAllowance'], 30)
        self.assertEqual(target['MaximumTestExecutionTimeAllowance'], 45)
        self.assertFalse(target['ParallelizationEnabled'])
        for key in ['EnvironmentVariables', 'TestingEnvironmentVariables']:
            self.assertEqual(target[key]['MIXER_BRIDGE_CAPABILITY'], 'a' * 64)
        self.assertEqual(original['MixerToggleUITests']['DefaultTestExecutionTimeAllowance'], 600)
        self.assertNotIn('MIXER_BRIDGE_CAPABILITY', original['MixerToggleUITests']['EnvironmentVariables'])
        roundtrip = copy.deepcopy(derived)
        for key in ['EnvironmentVariables', 'TestingEnvironmentVariables']:
            del roundtrip['MixerToggleUITests'][key]['MIXER_BRIDGE_URL']; del roundtrip['MixerToggleUITests'][key]['MIXER_BRIDGE_CAPABILITY']
        for key in ['TestTimeoutsEnabled', 'DefaultTestExecutionTimeAllowance', 'UserAttachmentLifetime', 'SystemAttachmentLifetime']:
            roundtrip['MixerToggleUITests'][key] = original['MixerToggleUITests'][key]
        del roundtrip['MixerToggleUITests']['MaximumTestExecutionTimeAllowance']; del roundtrip['MixerToggleUITests']['ParallelizationEnabled']
        def undo(value):
            if isinstance(value, str): return value.replace(str(composition.h.PRODUCTS), '__TESTROOT__')
            if isinstance(value, list): return [undo(item) for item in value]
            if isinstance(value, dict): return {key: undo(item) for key, item in value.items()}
            return value
        self.assertEqual(undo(roundtrip), original)

    def command(self, session=None):
        session = session or self.folder
        return [str(composition.h.DEVELOPER / 'usr/bin/xcodebuild'), 'test-without-building', '-xctestrun',
                str(session / 'session.xctestrun'), '-destination', 'platform=iOS Simulator,id=11111111-1111-4111-8111-111111111111',
                '-parallel-testing-enabled', 'NO', '-maximum-concurrent-test-simulator-destinations', '1',
                '-resultBundlePath', str(session / 'session.xcresult')] + ['-only-testing:MixerToggleUITests/ToggleUITests/' + m for m in prepare.METHODS]

    def commands(self):
        class Commands:
            def __init__(self): self.events = []
            def redact(self, text): return text.replace('secret', '[redacted]')
            def record(self, name, value): self.events.append((name, value))
        return Commands()

    def observer_receipt(self, argv, kwargs, code=65, group='absent', cleanup=None):
        output = kwargs['output_dir']; output.mkdir()
        value = {'argv': argv, 'exitCode': code, 'ownedProcessGroup': {'state': group},
                 'cleanup': {'complete': cleanup}, 'streams': {name: {'eof': True, 'readerFailed': False} for name in ['stdout', 'stderr']},
                 'successInferredFromConsoleOrMarkers': False}
        prepare.save(output / 'observer.json', value)
        return value

    def test_exact_command_env_exit_and_forwarding(self):
        argv, commands = self.command(), self.commands()
        support.select_command(composition.h, argv, self.folder)
        seen = []
        def observe(actual, **kwargs):
            seen.append((actual, kwargs)); self.observer_receipt(actual, kwargs); return 65, 'suite failed', 'diagnostic'
        with patch.object(observer, 'observe_command', observe):
            self.assertEqual(support.run_observed(commands, argv, 600, False, None), (65, 'suite failed', 'diagnostic'))
        self.assertEqual(seen[0][0], argv)
        self.assertEqual(seen[0][1]['env'], {**os.environ, 'DEVELOPER_DIR': str(composition.h.DEVELOPER), 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(seen[0][1]['cwd'], prepare.ROOT)
        self.assertEqual(seen[0][1]['timeout'], 600); self.assertIs(seen[0][1]['check'], False)
        self.assertFalse(support.is_selected(['/usr/bin/xcrun', 'xcresulttool', 'get', 'test-results', 'summary']))
        self.assertFalse(support.is_selected(['/usr/bin/xcrun', 'simctl', 'list', 'runtimes', '--json']))
        with self.assertRaises(ValueError): support.run_observed(commands, argv, 600, False, None)

    def test_changed_selection_or_budgets_fail_before_observer(self):
        argv = self.command()
        with self.assertRaises(ValueError): support.select_command(composition.h, argv[:-1], self.folder)
        support.select_command(composition.h, argv, self.folder)
        changed = list(argv); changed[-1] += 'Changed'
        with self.assertRaises(ValueError): support.is_selected(changed)
        for timeout, check, filter_value in [(601, False, None), (599, False, None), (600, True, None), (600, False, lambda value: value)]:
            with self.assertRaises(ValueError): support.run_observed(self.commands(), argv, timeout, check, filter_value)
        self.assertFalse(support._selected['called'])

    def test_surviving_group_cannot_grant_terminal_diagnostic_evidence(self):
        argv, commands = self.command(), self.commands()
        support.select_command(composition.h, argv, self.folder)
        def observe(actual, **kwargs):
            self.observer_receipt(actual, kwargs, code=0, group='present-or-zombies')
            return 0, "Test Suite 'Selected tests' passed at fake.", ''
        with patch.object(observer, 'observe_command', observe):
            with self.assertRaisesRegex(ValueError, 'terminal owned-group'): support.run_observed(commands, argv, 600, False, None)
        self.assertEqual(commands.events[0][1]['exitCode'], 0)

    def test_explicit_failed_cleanup_is_not_erased_by_later_group_absence(self):
        summary = self.observer_receipt(self.command(), {'output_dir': self.folder / 'observer'}, code=65, cleanup=False)
        self.assertFalse(support.observer_terminal(summary, 65))

    def test_nonselected_canonical_command_body_unchanged(self):
        commands = composition.CANONICAL_COMMANDS(self.folder / 'commands.json')
        process = types.SimpleNamespace(returncode=0, communicate=lambda timeout: (' native-free \n', ' err \n'))
        with patch.object(composition.h.subprocess, 'Popen', return_value=process) as launch:
            result = commands.run(['/host-test-only'], timeout=7, check=True)
        self.assertEqual(result, (0, 'native-free', 'err'))
        self.assertEqual(launch.call_args.args[0], ['/host-test-only'])
        self.assertEqual(launch.call_args.kwargs['env'], {**os.environ, 'DEVELOPER_DIR': str(composition.h.DEVELOPER), 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(launch.call_args.kwargs['cwd'], prepare.ROOT)
        self.assertTrue(launch.call_args.kwargs['text'])

    def test_join_retains_observer_timeout_and_owned_group_cleanup(self):
        argv, commands = self.command(), self.commands()
        support.select_command(composition.h, argv, self.folder)
        actual = observer.observe_command
        boundary = []
        def host_observe(native_argv, **kwargs):
            boundary.append((native_argv, kwargs['timeout']))
            kwargs.update(timeout=0.25, poll_interval=0.01, post_suite_grace=0.03)
            return actual([sys.executable, '-B', '-c', "import time;print(\"Test Suite 'Selected tests' passed at host-only.\",flush=True);time.sleep(5)"], **kwargs)
        with patch.object(observer, 'observe_command', host_observe):
            with self.assertRaises(subprocess.TimeoutExpired): support.run_observed(commands, argv, 600, False, None)
        self.assertEqual(boundary, [(argv, 600)])
        receipt = json.loads((self.folder / 'command-observer/observer.json').read_bytes())
        self.assertIs(receipt['successInferredFromConsoleOrMarkers'], False)
        self.assertTrue(receipt['cleanup']['complete'])
        self.assertEqual(receipt['ownedProcessGroup']['state'], 'absent')
        self.assertIsNotNone(receipt['postSuiteCapture'])
        timeline = [json.loads(line) for line in (self.folder / 'command-observer/timeline.jsonl').read_text().splitlines()]
        self.assertEqual(sum(value['kind'] == 'post-suite-grace-capture' for value in timeline), 1)
        self.assertEqual(commands.events[0][0], 'command-interrupted')

    def test_config_retirement_preserves_result_and_redacted_derivation(self):
        h = types.SimpleNamespace(RUN_DIR=self.folder, PRODUCTS=composition.h.PRODUCTS, write=composition.h.write)
        life = {}; session = support.prepare_session(h, life)
        secret = 'a' * 64
        config = support.session_configuration(h, session, 12345, secret)
        self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o600)
        result = session / 'session.xcresult'; result.mkdir(); (result / 'Info.plist').write_bytes(b'retained')
        support.retire_session(h, life)
        self.assertFalse(config.exists()); self.assertEqual((result / 'Info.plist').read_bytes(), b'retained')
        receipt = (session / 'configuration-derivation.json').read_bytes()
        self.assertNotIn(secret.encode(), receipt)
        self.assertTrue(json.loads(receipt)['retired'])

    def test_cleanup_identity_failure_is_preserved(self):
        h = types.SimpleNamespace(RUN_DIR=self.folder, PRODUCTS=composition.h.PRODUCTS, write=composition.h.write)
        life = {}; session = support.prepare_session(h, life)
        support.session_configuration(h, session, 12345, 'a' * 64)
        session.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'identity'): support.retire_session(h, life)
        self.assertTrue((session / 'session.xctestrun').exists())
        # This host negative control owns the directory and restores it for explicit retirement.
        session.chmod(0o700); support.retire_session(h, life)

    def test_two_method_official_summary_rejects_console_or_six_case_credit(self):
        self.assertFalse(support.official_methods(self.folder))
        runtime = self.folder / 'runtime'; runtime.mkdir()
        summary = {'result': 'Passed', 'totalTestCount': 2, 'passedTests': 2, 'failedTests': 0, 'skippedTests': 0, 'expectedFailures': 0}
        tests = [{'nodeType': 'Test Case', 'nodeIdentifier': 'ToggleUITests/' + method, 'result': 'Passed'} for method in prepare.METHODS]
        prepare.save(runtime / 'xctest-summary.json', summary); prepare.save(runtime / 'xctest-tests.json', tests)
        self.assertTrue(support.official_methods(self.folder))
        summary.update(totalTestCount=7, passedTests=7); prepare.save(runtime / 'xctest-summary.json', summary)
        self.assertFalse(support.official_methods(self.folder))
        result = support.runtime_summary(self.folder, composition.h, composition.oracle, composition.setup_ready, 'interaction', None, 0, None, [{'passed': True}])
        self.assertFalse(result['runPassed']); self.assertFalse(result['fullSixCaseQualification']); self.assertFalse(result['gaAccepted'])

    def mocked_lifecycle(self, command_failure=False, cleanup_failure=False):
        trace = []
        outer = self
        class Commands:
            def __init__(self, output, capability): self.output=output; self.reporting_error=None; self.cleanup_mode=False; self.capability=capability
            def redact(self, text): return text.replace(self.capability, '[redacted]')
            def record(self, name, value): trace.append(('record', name))
            def simctl(self, *argv):
                trace.append(('mock-simctl', argv))
                if argv[:2] == ('list', 'runtimes'):
                    return json.dumps({'runtimes': [{'identifier': composition.h.RUNTIME, 'isAvailable': True, 'buildversion': composition.h.RUNTIME_BUILD}]})
                if argv[0] == 'create': return '11111111-1111-4111-8111-111111111111'
                if argv[0] == 'get_app_container':
                    path = outer.folder / 'mock-containers' / argv[-1]; path.mkdir(parents=True, exist_ok=True); return str(path)
                return ''
            def run(self, argv, **kwargs):
                trace.append(('mock-command', list(map(str, argv)), kwargs))
                if len(argv) > 1 and argv[1] == 'test-without-building':
                    if cleanup_failure: (outer.folder / 'runtime/session').chmod(0o755)
                    if command_failure: raise subprocess.TimeoutExpired(argv, 600)
                return 0, '{}', ''
        class Server:
            server_port=12345
            def serve_forever(self): raise AssertionError('Fake thread must not invoke service')
            def shutdown(self): trace.append(('cleanup', 'server-shutdown'))
            def server_close(self): trace.append(('cleanup', 'server-close'))
        class Thread:
            def __init__(self, **kwargs): pass
            def start(self): trace.append(('mock-thread', 'start'))
            def join(self, timeout): trace.append(('cleanup', 'thread-join'))
            def is_alive(self): return False
        class Bridge:
            def __init__(self, *args, **kwargs): trace.append(('mock-bridge', {**kwargs, 'allowed_cases': sorted(kwargs['allowed_cases'])}))
        packet = types.SimpleNamespace(CONFIGS=composition.CandidateApps.CONFIGS,
            restore=lambda destination, key: trace.append(('mock-app', 'restore', key)),
            verify_installed=lambda *args: {'mocked': True})
        def cleanup(life, commands): trace.append(('cleanup', 'owned-simulator'))
        h = types.SimpleNamespace(json=json, secrets=secrets, uuid=uuid, pathlib=prepare.Path,
            Commands=Commands, threading=types.SimpleNamespace(Thread=Thread), packet=packet,
            SCOPES={'interaction': {'cases': {prepare.CASE}, 'methods': prepare.METHODS}},
            select_runtime_directory=lambda scope: self.folder / 'runtime', verify=lambda: {'sealSHA256': 'host-only-seal'},
            RUNTIME=composition.h.RUNTIME, RUNTIME_BUILD=composition.h.RUNTIME_BUILD, DEVICE_TYPE=composition.h.DEVICE_TYPE,
            DEVELOPER=composition.h.DEVELOPER, ROOT=prepare.ROOT, PRODUCTS=composition.h.PRODUCTS,
            devices=lambda commands: {'devices': {}}, frontends=lambda commands: [],
            owned_device=lambda *args: None, write=composition.h.write, require=prepare.require,
            validate_container=lambda value,*args,**kwargs: prepare.Path(value), Bridge=Bridge,
            server_for=lambda bridge: Server(), cleanup=cleanup,
            runtime_summary=lambda *args: {'strictNativeVerdictsPassed': True, 'bridgeFailures': [], 'runPassed': True})
        bindings=types.SimpleNamespace(check=lambda roots: None)
        if command_failure or cleanup_failure:
            with self.assertRaises((subprocess.TimeoutExpired, ValueError)):
                composition.orchestration.run(h,bindings,[],'host-only-seal')
        else:
            result=composition.orchestration.run(h,bindings,[],'host-only-seal')
            self.assertTrue(result['runPassed'])
        life=json.loads((self.folder / 'runtime/lifecycle.json').read_bytes())
        selected_commands=[row for row in trace if row[0]=='mock-command' and row[1][1]=='test-without-building']
        self.assertEqual(len(selected_commands),1)
        self.assertEqual(selected_commands[0][2],{'timeout':600,'check':False})
        self.assertEqual(selected_commands[0][1][-2:],self.command(self.folder / 'runtime/session')[-2:])
        self.assertIn(('cleanup','owned-simulator'),trace)
        self.assertIn(('cleanup','server-shutdown'),trace)
        self.assertIn(('cleanup','server-close'),trace)
        self.assertIn(('cleanup','thread-join'),trace)
        self.assertEqual(sum(row[0]=='mock-simctl' and row[1][0]=='create' for row in trace),1)
        self.assertTrue(life['ownedName'].startswith('MixerFocusDiagnosticV1-'))
        if cleanup_failure:
            self.assertFalse(life['cleanedUp']); self.assertFalse(h.last_runtime_summary['runPassed'])
            session=self.folder / 'runtime/session'; session.chmod(0o700); support.retire_session(h,life)
        else:
            self.assertTrue(life['cleanedUp']); self.assertTrue(life['secretConfigurationAbsent'])
        prepare.save(self.folder / 'mock-boundary-trace.json', trace)

    def test_mocked_lifecycle_exact_selection_and_cleanup(self): self.mocked_lifecycle()

    def test_mocked_command_timeout_still_retires_all_resources(self): self.mocked_lifecycle(command_failure=True)

    def test_mocked_cleanup_failure_remains_failed_and_other_cleanup_runs(self): self.mocked_lifecycle(cleanup_failure=True)


if __name__ == '__main__': unittest.main(verbosity=2)
