"""Pure Python runner controls. Fake children never qualify Java/Swift or DEX."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

RUNNER = Path(__file__).resolve().parents[1] / 'check-android-generated-java.py'
SPEC = importlib.util.spec_from_file_location('android_generated_java_runner', RUNNER)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def data_identity(value):
    return {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}


class RunnerControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='generated-java-python-controls-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def consumer(self):
        root = self.root / 'consumer'
        sdk = {'Package.swift': b'owned package', 'Sources/MixerCore/Lifecycle.swift': b'owned core',
               'Sources/MixerUI/UI.swift': b'owned UI'}
        adapter = {f'app/src/dev/mixer/android/Product{i:02}.java': b'owned input' for i in range(18)}
        adapter.update({'Sources/MixerAndroidRuntime/Entry.swift': b'owned runtime',
                        'bridge/jni.c': b'owned JNI', 'contracts/ui.json': b'owned contract'})
        profile = {'schema': 1, 'id': 'mixer.android-source-pair.7',
                   'default_descriptor': data_identity(b'owned descriptor'),
                   'sdk_files': {p: data_identity(v) for p, v in sdk.items()},
                   'adapter_files': {p: data_identity(v) for p, v in adapter.items()}}
        for kind in ('sdk', 'adapter'):
            profile[kind + '_compatibility_sha256'] = M.source_digest(profile[kind + '_files'])
        for directory, values in (('MixerSDK', sdk), ('MixerAndroid', adapter)):
            for path, value in values.items():
                target = root / 'Generated' / directory / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(value)
        descriptor = root / 'Generated/MixerAndroid' / M.DESCRIPTOR
        descriptor.parent.mkdir(parents=True)
        descriptor.write_bytes(b'owned descriptor')
        template = "SOURCE_PROFILE_HEX = '" + M.MARKER + "'\n"
        driver = root / 'Generated/MixerAndroid/android-build.py'
        driver.write_text(template.replace(M.MARKER, json.dumps(profile).encode().hex()))
        toolchain = {'swift_version': 'pure-control-not-a-compiler', 'tools': {}}
        lock = {'schema': 1, 'swiftVersion': toolchain['swift_version'],
                'sdkDigest': M.source_digest(M.inventory(root / 'Generated/MixerSDK')),
                'android': {'adapterDigest': M.source_digest(M.inventory(root / 'Generated/MixerAndroid')),
                            'toolchain': toolchain,
                            'profile': {k: profile[k] for k in ('id', 'sdk_compatibility_sha256',
                                       'adapter_compatibility_sha256', 'default_descriptor')}}}
        M.save(root / 'mixer.lock', lock)
        return root, profile, toolchain, template

    def validate(self, consumer):
        return M.validate_consumer(*consumer)

    def recompute(self, root):
        lock = json.loads((root / 'mixer.lock').read_text())
        lock['sdkDigest'] = M.source_digest(M.inventory(root / 'Generated/MixerSDK'))
        lock['android']['adapterDigest'] = M.source_digest(M.inventory(root / 'Generated/MixerAndroid'))
        M.save(root / 'mixer.lock', lock)

    def test_canonical_live_policy_selects_all_18_not_instrumentation(self):
        profile = M.load_profile()
        roster = M.java_roster(profile)
        self.assertEqual(len(roster), 18)
        self.assertNotIn('app/src/dev/mixer/android/AdapterInstrumentation.java', roster)
        for kind, prefix in (('sdk', 'sdk/'), ('adapter', 'native/android/')):
            for path, expected in profile[kind + '_files'].items():
                actual = M.ROOT / (prefix + ('engine/' if kind == 'adapter' and path.startswith('Sources/') else '') + path)
                self.assertEqual(M.identity(actual), expected, str(actual))

    def test_valid_snapshot_preserves_full_inventory(self):
        consumer = self.consumer()
        result = self.validate(consumer)
        self.assertIn('mixer.lock', result)
        self.assertEqual(len([p for p in result if p.endswith('.java')]), 18)

    def test_same_size_sdk_or_adapter_drift_refused_with_recomputed_tree_locks(self):
        consumer = self.consumer()
        root = consumer[0]
        for path in ('Generated/MixerSDK/Sources/MixerCore/Lifecycle.swift',
                     'Generated/MixerAndroid/app/src/dev/mixer/android/Product00.java'):
            target = root / path
            original = target.read_bytes()
            target.write_bytes(b'X' * len(original))
            self.recompute(root)
            with self.assertRaisesRegex(RuntimeError, 'pinned source differs'):
                self.validate(consumer)
            target.write_bytes(original)
            self.recompute(root)

    def test_descriptor_drift_refused_with_recomputed_lock(self):
        consumer = self.consumer()
        target = consumer[0] / 'Generated/MixerAndroid' / M.DESCRIPTOR
        target.write_bytes(b'X' * target.stat().st_size)
        self.recompute(consumer[0])
        with self.assertRaisesRegex(RuntimeError, 'descriptor differs'):
            self.validate(consumer)

    def test_extra_java_and_empty_closed_directory_refused(self):
        consumer = self.consumer()
        for directory in (False, True):
            target = consumer[0] / 'Generated/MixerAndroid/app/src/extra'
            target.mkdir() if directory else target.write_text('extra')
            self.recompute(consumer[0])
            with self.assertRaisesRegex(RuntimeError, 'closed (inventory|directory topology) differs'):
                self.validate(consumer)
            target.rmdir() if directory else target.unlink()

    def test_missing_java_cannot_reduce_the_roster(self):
        consumer = self.consumer()
        (consumer[0] / 'Generated/MixerAndroid' / M.java_roster(consumer[1])[0]).unlink()
        self.recompute(consumer[0])
        with self.assertRaisesRegex(RuntimeError, 'pinned source differs'):
            self.validate(consumer)
        short = copy.deepcopy(consumer[1])
        short['adapter_files'].pop(M.java_roster(short)[0])
        with self.assertRaisesRegex(RuntimeError, 'all 18'):
            M.java_roster(short)

    def test_rendered_profile_cannot_hide_other_driver_edits(self):
        consumer = self.consumer()
        target = consumer[0] / 'Generated/MixerAndroid/android-build.py'
        target.write_text(target.read_text() + '# unselected change\n')
        self.recompute(consumer[0])
        with self.assertRaisesRegex(RuntimeError, 'canonical template'):
            self.validate(consumer)

    def test_rendered_driver_identity_does_not_normalize_newlines(self):
        consumer = self.consumer()
        target = consumer[0] / 'Generated/MixerAndroid/android-build.py'
        target.write_bytes(target.read_bytes().replace(b'\n', b'\r\n'))
        self.recompute(consumer[0])
        with self.assertRaisesRegex(RuntimeError, 'canonical template'):
            self.validate(consumer)

    def test_toolchain_and_pair_lock_changes_refused(self):
        consumer = self.consumer()
        path = consumer[0] / 'mixer.lock'
        original = json.loads(path.read_text())
        for key in ('toolchain', 'profile'):
            value = copy.deepcopy(original)
            value['android'][key] = {}
            M.save(path, value)
            with self.assertRaisesRegex(RuntimeError, 'lock differs'):
                self.validate(consumer)

    def test_symlink_inventory_is_not_followed(self):
        consumer = self.consumer()
        target = consumer[0] / 'Generated/MixerAndroid/app/src/escape'
        target.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'symlinks'):
            self.validate(consumer)

    def test_duplicate_json_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'Duplicate JSON'):
            M.unique_json('{"id":1,"id":2}')

    def compile_fake(self, omit_class=False, omit_descriptor=False, fail_d8=False,
                     omit_member_class=False, omit_members=False):
        root, profile, _, _ = self.consumer()
        calls = []
        def run(label, argv, **options):
            calls.append((label, argv))
            self.assertEqual(options, {'stdout_bytes': M.JAVAP_STDOUT_BYTES}
                             if label.endswith('-javap-members') else {})
            if label.endswith('-javac'):
                self.assertEqual(argv[1:9], ['--release', '17', '-Xlint:all', '-Werror',
                                           '-proc:none', '-sourcepath', '', '-classpath'])
                self.assertEqual(argv[9], self.root / 'sdk/platforms/android-37.0/android.jar')
                self.assertEqual(argv[12:], [root / 'Generated/MixerAndroid' / p for p in M.java_roster(profile)])
                for path in M.java_roster(profile)[1 if omit_class else 0:]:
                    target = Path(argv[11]) / (path.removeprefix('app/src/').removesuffix('.java') + '.class')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b'fake-child-output-not-a-class')
            elif label.endswith('-d8'):
                self.assertEqual(argv[1:5], ['--min-api', '28', '--lib', self.root / 'sdk/platforms/android-37.0/android.jar'])
                self.assertEqual(len(argv[7:]), 18)
                if fail_d8:
                    raise RuntimeError('fake D8 failure')
                (Path(argv[6]) / 'classes.dex').write_bytes(b'dex\n035\0fake-control')
            elif label.endswith('-javap-members'):
                self.assertEqual(argv[:5], [self.root / 'jdk/bin/javap', '-v', '-p', '-c', '-s'])
                self.assertEqual(len(argv[5:]), 18)
                return '\n'.join('Classfile ' + str(path) + '\n' + ('' if omit_members else
                    '  #1 = Methodref          #2.#3 // java/lang/Object."<init>":()V\n'
                    '  #4 = Fieldref           #5.#6 // android/os/Build.VERSION:I\n'
                    '  #7 = InterfaceMethodref #8.#9 // java/util/List.size:()I')
                    for path in argv[6 if omit_member_class else 5:])
            else:
                self.assertTrue(label.endswith('-dexdump'))
                return '\n'.join("Class descriptor  : 'L" + p.removeprefix('app/src/').removesuffix('.java') + ";'"
                                 for p in M.java_roster(profile)[1 if omit_descriptor else 0:])
            return ''
        result = M.compile_consumer(root, self.root / 'compile', profile,
                                    self.root / 'jdk', self.root / 'sdk', run, 'selection-control')
        return calls, result

    def test_compiler_selection_includes_all_sources_and_min_api28(self):
        calls, result = self.compile_fake()
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(result['sources']), 18)
        self.assertEqual(len(result['classes']), 18)
        self.assertEqual(result['member_references']['count'], 54)
        self.assertIn('No API28 floor/linkage approval', result['member_references']['scope'])
        raw = self.root / 'compile/member-references.javap.txt'
        self.assertEqual(M.identity(raw), {k: result['member_references']['raw_output'][k] for k in ('bytes', 'sha256')})
        members = json.loads((self.root / 'compile/member-references.json').read_text())
        self.assertEqual({r['kind'] for r in members['references']}, {'Methodref', 'Fieldref', 'InterfaceMethodref'})
        self.assertEqual(len({r['class_file'] for r in members['references']}), 18)

    def test_missing_class_member_scope_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'Missing emitted class in javap member inventory'):
            self.compile_fake(omit_member_class=True)
        self.assertFalse((self.root / 'compile/receipt.json').exists())

    def test_empty_actual_member_inventory_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'Missing actual class member references'):
            self.compile_fake(omit_members=True)

    def test_unscoped_duplicate_and_unresolved_member_references_refused(self):
        path = self.root / 'Product.class'
        entry = ' #1 = Methodref #2.#3 // java/lang/Object."<init>":()V\n'
        for dump, message in ((entry, 'Unscoped'),
                              ('Classfile ' + str(path) + '\nClassfile ' + str(path), 'duplicate'),
                              ('Classfile ' + str(path) + '\n #1 = Methodref #2.#3', 'unresolved')):
            with self.assertRaisesRegex(RuntimeError, message):
                M.member_references(dump, [path])

    def test_missing_emitted_class_fails_before_d8(self):
        with self.assertRaisesRegex(RuntimeError, 'Missing emitted product classes'):
            self.compile_fake(omit_class=True)

    def test_missing_dex_class_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'Missing product class descriptors'):
            self.compile_fake(omit_descriptor=True)

    def test_d8_failure_cannot_write_a_pass_receipt(self):
        with self.assertRaisesRegex(RuntimeError, 'fake D8 failure'):
            self.compile_fake(fail_d8=True)
        self.assertFalse((self.root / 'compile/receipt.json').exists())

    def test_tamper_suite_demands_named_refusal_and_no_staging(self):
        root, profile, _, _ = self.consumer()
        scratch = self.root / 'tamper'
        scratch.mkdir()
        codes = {name: code for name, _, code in M.tamper_cases(profile)}
        def run(label, argv, **options):
            self.assertTrue(options['expected_failure'])
            if '-driver-tamper-' in label:
                name = label.split('-driver-tamper-')[1]
                expected = ('android.sdk-profile-mismatch' if name == 'profile' else
                            'mixer.lock' if name == 'missing-lock' else 'Android SDK source compatibility rejected')
                self.assertTrue(options['diagnostics'])
                return 'Android local build error: ' + expected
            name = label.removeprefix('control-tamper-')
            changed = Path(argv[-1])
            if name in ('sdk', 'adapter', 'descriptor', 'extra-java'):
                lock = json.loads((changed / 'mixer.lock').read_text())
                self.assertEqual(lock['android']['adapterDigest'],
                                 M.source_digest(M.inventory(changed / 'Generated/MixerAndroid')))
            return json.dumps({'status': 'error', 'code': codes[name]})
        outcomes = M.tamper_consumers(root, scratch, self.root / 'not-a-cli', profile, run, 'control')
        self.assertEqual(len(outcomes), 6)
        self.assertEqual(list(scratch.iterdir()), [])

    def test_wrong_tamper_failure_does_not_count_as_refusal(self):
        root, profile, _, _ = self.consumer()
        scratch = self.root / 'tamper'
        scratch.mkdir()
        with self.assertRaisesRegex(RuntimeError, 'Unexpected tamper refusal'):
            M.tamper_consumers(root, scratch, self.root / 'not-a-cli', profile,
                               lambda *a, **kw: '{"status":"error","code":"compiler.failed"}', 'control')

    def commands(self, **kwargs):
        return M.Commands(self.root, os.environ.copy(), seconds=5, command_seconds=2, cleanup_seconds=0.2, **kwargs)

    def terminal_record(self, record):
        self.assertIsInstance(record['pid'], int)
        self.assertEqual(record['pid'], record['owned_pgid'])
        for key in ('direct_child_reaped', 'stdout_eof', 'stderr_eof', 'owned_group_absent', 'terminal_custody'):
            self.assertIs(record[key], True, key)
        self.assertEqual(record['group_observation']['outcome'], 'absent')
        self.assertGreaterEqual(record['group_observation']['attempts'], 1)
        self.assertIn(record['signal']['outcome'], ('sent', 'already-absent'))
        self.assertEqual(record['cleanup_errors'], [])
        self.assertEqual(json.loads((self.root / 'commands.json').read_text())[-1], record)

    def test_fake_child_success_and_failure_retain_diagnostics(self):
        commands = self.commands()
        self.assertEqual(commands.run('python-ok', [sys.executable, '-B', '-c', 'print("ok")']), 'ok\n')
        self.assertEqual(commands.run('python-no', [sys.executable, '-B', '-c',
            'import sys; print("refused"); print("detail",file=sys.stderr); sys.exit(3)'], expected_failure=True), 'refused\n')
        self.assertEqual(commands.records[-1]['exit_code'], 3)
        self.assertEqual((self.root / '001-python-no.stderr').read_text(), 'detail\n')
        self.terminal_record(commands.records[-1])
        self.assertTrue(commands.custody_terminal())

    def test_zero_or_signal_is_not_an_expected_refusal(self):
        commands = self.commands()
        for index, code in enumerate(('pass', 'import os,signal; os.kill(os.getpid(),signal.SIGTERM)')):
            with self.assertRaisesRegex(RuntimeError, 'unexpected exit'):
                commands.run('not-refusal-' + str(index), [sys.executable, '-B', '-c', code], expected_failure=True)

    def test_timeout_and_output_overflow_fail_and_close_owned_child(self):
        for label, script, expected in (
            ('timeout', 'import time; time.sleep(10)', 'timeout'),
            ('overflow', 'import os; os.write(1,b"x"*10000)', 'output-limit')):
            commands = M.Commands(self.root, os.environ.copy(), seconds=3, command_seconds=0.2, output_bytes=128)
            with self.assertRaisesRegex(RuntimeError, expected):
                commands.run(label, [sys.executable, '-B', '-c', script])
            self.assertEqual(commands.records[-1]['stop'], expected)
            self.assertIsNotNone(commands.records[-1]['exit_code'])
            self.assertTrue(commands.records[-1]['terminal_custody'])
            self.assertLessEqual((self.root / ('000-' + label + '.stdout')).stat().st_size, 128)

    def test_total_output_budget_spans_commands(self):
        commands = self.commands(output_bytes=128, total_output_bytes=6)
        commands.run('first', [sys.executable, '-B', '-c', 'print("abc")'])
        with self.assertRaisesRegex(RuntimeError, 'output-limit'):
            commands.run('second', [sys.executable, '-B', '-c', 'print("abc")'])
        self.assertEqual(commands.used_output, 6)

    def test_explicit_stdout_budget_captures_complete_large_output_without_changing_defaults(self):
        commands = M.Commands(self.root, os.environ.copy(), seconds=15, command_seconds=2)
        self.assertEqual(commands.output_bytes, 4_194_304)
        self.assertEqual(commands.total_output_bytes, 67_108_864)
        size = 4_194_305
        output = commands.run('large-inventory', [sys.executable, '-B', '-c',
            'import sys; sys.stdout.buffer.write(b"x"*' + str(size) + ')'],
            stdout_bytes=M.JAVAP_STDOUT_BYTES)
        self.assertEqual(output, 'x' * size)
        self.terminal_record(commands.records[-1])
        self.assertEqual(commands.records[-1]['stream_output_limits'],
                         {'stdout': 8_388_608, 'stderr': 4_194_304})
        with self.assertRaisesRegex(RuntimeError, 'output-limit'):
            commands.run('default-still-bounded', [sys.executable, '-B', '-c',
                'import sys; sys.stdout.buffer.write(b"x"*' + str(size) + ')'])
        self.assertEqual(commands.records[-1]['logs']['stdout']['bytes'], 4_194_304)
        self.terminal_record(commands.records[-1])

    def test_javap_stdout_ceiling_refuses_one_extra_byte_without_silent_success(self):
        commands = M.Commands(self.root, os.environ.copy(), seconds=15, command_seconds=2)
        with self.assertRaisesRegex(RuntimeError, 'output-limit'):
            commands.run('javap-budget-overflow', [sys.executable, '-B', '-c',
                'import sys; sys.stdout.buffer.write(b"x"*' + str(M.JAVAP_STDOUT_BYTES + 1) + ')'],
                stdout_bytes=M.JAVAP_STDOUT_BYTES)
        record = commands.records[-1]
        self.assertEqual(record['logs']['stdout']['bytes'], M.JAVAP_STDOUT_BYTES)
        self.assertEqual(record['stop'], 'output-limit')
        self.terminal_record(record)

    def test_stdout_override_is_exact_and_does_not_expand_stderr_or_aggregate(self):
        commands = M.Commands(self.root, os.environ.copy(), seconds=15, command_seconds=2,
                              output_bytes=16, total_output_bytes=100)
        self.assertEqual(commands.run('exact', [sys.executable, '-B', '-c',
            'import os; os.write(1,b"x"*32)'], stdout_bytes=32), 'x' * 32)
        with self.assertRaisesRegex(RuntimeError, 'output-limit'):
            commands.run('one-over', [sys.executable, '-B', '-c',
                'import os; os.write(1,b"x"*33)'], stdout_bytes=32)
        self.assertEqual(commands.records[-1]['logs']['stdout']['bytes'], 32)
        self.terminal_record(commands.records[-1])
        with self.assertRaisesRegex(RuntimeError, 'output-limit'):
            commands.run('stderr-default', [sys.executable, '-B', '-c',
                'import os; os.write(2,b"e"*17)'], stdout_bytes=32)
        self.assertEqual(commands.records[-1]['logs']['stderr']['bytes'], 16)
        self.terminal_record(commands.records[-1])
        with self.assertRaisesRegex(RuntimeError, 'output-limit'):
            commands.run('aggregate', [sys.executable, '-B', '-c',
                'import os; os.write(1,b"x"*32)'], stdout_bytes=32)
        self.assertEqual(commands.used_output, 100)
        self.assertEqual(commands.records[-1]['logs']['stdout']['bytes'], 20)
        self.terminal_record(commands.records[-1])

    def test_invalid_stdout_budgets_fail_before_spawning(self):
        commands = self.commands()
        with mock.patch.object(M.subprocess, 'Popen', side_effect=AssertionError('unexpected child')):
            for value in (0, -1, True, 1.5, '8000000', M.JAVAP_STDOUT_BYTES + 1):
                with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, 'Invalid explicit stdout budget'):
                    commands.run('invalid', ['unused'], stdout_bytes=value)
        self.assertEqual(commands.records, [])

    def test_exited_fake_parent_with_inherited_pipes_cannot_hang_runner(self):
        commands = M.Commands(self.root, os.environ.copy(), seconds=3, command_seconds=0.3, cleanup_seconds=0.2)
        script = ('import subprocess,sys; subprocess.Popen([sys.executable,"-B","-c",'
                  '"import time; time.sleep(10)"])')
        with self.assertRaisesRegex(RuntimeError, 'timeout|terminal custody'):
            commands.run('python-owned-descendant', [sys.executable, '-B', '-c', script])
        record = commands.records[0]
        self.assertEqual(record['signal']['outcome'], 'sent')
        self.assertTrue(record['stdout_eof'])
        self.assertTrue(record['stderr_eof'])

    def test_denied_signal_retains_receipt_even_after_child_exits(self):
        commands = self.commands()
        real_killpg = os.killpg
        def killpg(pgid, sig):
            self.assertEqual(pgid, commands.records[-1]['owned_pgid'])
            if sig == signal.SIGKILL:
                raise PermissionError('fake denied owned signal')
            return real_killpg(pgid, sig)
        with mock.patch.object(M.os, 'killpg', side_effect=killpg):
            with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                commands.run('denied-signal', [sys.executable, '-B', '-c', 'print("retained")'])
        record = json.loads((self.root / 'commands.json').read_text())[0]
        self.assertTrue(record['direct_child_reaped'])
        self.assertTrue(record['owned_group_absent'])
        self.assertFalse(record['terminal_custody'])
        self.assertEqual(record['signal']['outcome'], 'denied')
        self.assertEqual((self.root / '000-denied-signal.stdout').read_text(), 'retained\n')
        with self.assertRaisesRegex(RuntimeError, 'Prior command custody'):
            commands.run('no-followup', [sys.executable, '-B', '-c', 'pass'])

    def test_denied_or_unknown_group_observation_cannot_pass(self):
        real_killpg = os.killpg
        for denied in (True, False):
            commands = self.commands()
            def killpg(pgid, sig):
                self.assertEqual(pgid, commands.records[-1]['owned_pgid'])
                if sig == 0:
                    if denied:
                        raise PermissionError('fake denied observation')
                    return None  # Inject a group that never becomes observably absent.
                return real_killpg(pgid, sig)
            with mock.patch.object(M.os, 'killpg', side_effect=killpg):
                with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                    commands.run('unknown-group', [sys.executable, '-B', '-c', 'pass'])
            record = json.loads((self.root / 'commands.json').read_text())[0]
            self.assertEqual(record['group_observation']['outcome'], 'denied' if denied else 'present-at-deadline')
            self.assertFalse(record['owned_group_absent'])
            self.assertFalse(record['terminal_custody'])
            self.assertTrue(record['direct_child_reaped'])
            self.assertTrue(record['stdout_eof'] and record['stderr_eof'])

    def test_live_child_denied_cleanup_still_persists_unknown_terminal_facts(self):
        commands = M.Commands(self.root, os.environ.copy(), seconds=2,
                              command_seconds=0.03, cleanup_seconds=0.03)
        children = []
        real_popen, real_killpg = M.subprocess.Popen, os.killpg
        def popen(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child
        try:
            with mock.patch.object(M.subprocess, 'Popen', side_effect=popen), \
                 mock.patch.object(M.os, 'killpg', side_effect=PermissionError('fake live-child denial')):
                with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                    commands.run('denied-live', [sys.executable, '-B', '-c',
                        'import time; print("owned",flush=True); time.sleep(3)'])
            record = json.loads((self.root / 'commands.json').read_text())[0]
            self.assertEqual(record['pid'], children[0].pid)
            self.assertFalse(record['direct_child_reaped'])
            self.assertFalse(record['stdout_eof'])
            self.assertFalse(record['stderr_eof'])
            self.assertFalse(record['owned_group_absent'])
            self.assertFalse(record['terminal_custody'])
            self.assertEqual(record['signal']['outcome'], 'denied')
            self.assertEqual({e['operation'] for e in record['cleanup_errors']},
                             {'signal-owned-group', 'reap-direct-child', 'observe-owned-group'})
            self.assertEqual(set(record['logs']), {'stdout', 'stderr'})
        finally:
            for child in children:
                try:
                    real_killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(timeout=1)
                child.stdout.close()
                child.stderr.close()
                with self.assertRaises(ProcessLookupError):
                    real_killpg(child.pid, 0)

    def test_one_stream_read_error_cannot_be_reported_as_eof(self):
        commands = self.commands()
        children = []
        real_popen, real_read = M.subprocess.Popen, os.read
        def popen(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child
        def read(fd, size):
            if children and fd == children[0].stderr.fileno():
                raise OSError('fake stderr read failure')
            return real_read(fd, size)
        with mock.patch.object(M.subprocess, 'Popen', side_effect=popen), \
             mock.patch.object(M.os, 'read', side_effect=read):
            with self.assertRaisesRegex(RuntimeError, 'stderr read failure'):
                commands.run('stream-error', [sys.executable, '-B', '-c', 'print("owned")'])
        record = json.loads((self.root / 'commands.json').read_text())[0]
        self.assertTrue(record['stdout_eof'])
        self.assertFalse(record['stderr_eof'])
        self.assertTrue(record['direct_child_reaped'])
        self.assertFalse(record['terminal_custody'])
        self.assertIn('drain-stderr', {e['operation'] for e in record['cleanup_errors']})

    def test_nested_reap_and_selector_cleanup_errors_still_persist(self):
        commands = self.commands()
        children, selectors = [], []
        real_popen, real_selector = M.subprocess.Popen, M.selectors.DefaultSelector
        patches = []
        def popen(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            patch = mock.patch.object(child, 'wait', side_effect=subprocess.TimeoutExpired('fake', 0.2))
            patch.start()
            patches.append(patch)
            patch = mock.patch.object(child.stdout, 'close', side_effect=OSError('fake stdout close failure'))
            patch.start()
            patches.append(patch)
            return child
        def selector():
            selected = real_selector()
            selectors.append(selected)
            patch = mock.patch.object(selected, 'close', side_effect=OSError('fake selector close failure'))
            patch.start()
            patches.append(patch)
            return selected
        try:
            with mock.patch.object(M.subprocess, 'Popen', side_effect=popen), \
                 mock.patch.object(M.selectors, 'DefaultSelector', side_effect=selector):
                with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                    commands.run('nested-errors', [sys.executable, '-B', '-c', 'print("diagnostic")'])
            record = json.loads((self.root / 'commands.json').read_text())[0]
            self.assertEqual({e['operation'] for e in record['cleanup_errors']},
                             {'reap-direct-child', 'close-stdout', 'close-selector'})
            self.assertFalse(record['direct_child_reaped'])
            self.assertFalse(record['terminal_custody'])
            self.assertTrue(record['stdout_eof'] and record['stderr_eof'])
            self.assertEqual((self.root / '000-nested-errors.stdout').read_text(), 'diagnostic\n')
        finally:
            for patch in reversed(patches):
                patch.stop()
            for child in children:
                child.wait(timeout=1)
                child.stdout.close()
                child.stderr.close()
            for selected in selectors:
                selected.close()

    def test_command_receipt_write_failure_retains_in_memory_facts(self):
        commands = self.commands()
        with mock.patch.object(M, 'save', side_effect=PermissionError('fake receipt write denial')):
            with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                commands.run('receipt-denied', [sys.executable, '-B', '-c', 'print("owned")'])
        record = commands.records[0]
        self.assertTrue(record['direct_child_reaped'] and record['stdout_eof'] and record['stderr_eof'])
        self.assertTrue(record['owned_group_absent'])
        self.assertFalse(record['terminal_custody'])
        self.assertEqual(record['cleanup_errors'][-1]['operation'], 'persist-command-receipt')
        self.assertEqual((self.root / '000-receipt-denied.stdout').read_text(), 'owned\n')

    def execute_to_producer(self, cleanup_outcome=None):
        paths = {k: self.root / k for k in ('swift', 'swift_sdks', 'android_artifact', 'jdk', 'android_sdk')}
        inspection = {'schema': 1, 'sdk_id': 'aarch64-unknown-linux-android28', 'min_api': 28,
                      'target_api': 37, 'javac_version': 'javac 25.fake-control',
                      'tools': {'swift': {'path': str(paths['swift'])},
                                'javac': {'path': str(paths['jdk'] / 'bin/javac')}},
                      'distributions': {'android_platform': {'path': str(paths['android_sdk'] / 'platforms/android-37.0')}}}
        jar = paths['android_sdk'] / 'platforms/android-37.0/android.jar'
        jar.parent.mkdir(parents=True)
        jar.write_bytes(b'fake-control-never-used-as-compiler-input')
        javap = paths['jdk'] / 'bin/javap'
        javap.parent.mkdir(parents=True)
        javap.write_bytes(b'fake-control-never-executed')
        sentinel = self.root / 'unowned-sentinel'
        sentinel.write_text('preserve')
        calls = []
        real_run, real_killpg, real_save = M.Commands.run, os.killpg, M.save
        def run(commands, label, argv, **kwargs):
            calls.append((label, list(map(str, argv))))
            if label == 'official-inspect':
                output = json.dumps(inspection)
            elif label == 'javap-version':
                output = '25.fake-control'
            else:
                output = 'fake-git-identity'
            script = 'print(' + repr(output) + ')'
            if label.endswith('-producer-build'):
                scratch = Path(argv[argv.index('--scratch-path') + 1]).parent
                (scratch / 'custody-sentinel').write_text('retain on uncertain cleanup')
                script = 'import sys; print("fake compiler failure"); sys.exit(3)'
                def killpg(pgid, sig):
                    self.assertEqual(pgid, commands.records[-1]['owned_pgid'])
                    if sig == signal.SIGKILL and cleanup_outcome == 'denied-signal':
                        raise PermissionError('fake denied signal')
                    if sig == 0 and cleanup_outcome == 'denied-observation':
                        raise PermissionError('fake denied observation')
                    if sig == 0 and cleanup_outcome == 'unknown':
                        return None
                    return real_killpg(pgid, sig)
                def save(path, value):
                    if path.name == 'commands.json' and cleanup_outcome == 'receipt-denied':
                        raise PermissionError('fake command receipt write denied')
                    return real_save(path, value)
                with mock.patch.object(M.os, 'killpg', side_effect=killpg), \
                     mock.patch.object(M, 'save', side_effect=save):
                    return real_run(commands, label, [sys.executable, '-B', '-c', script], **kwargs)
            return real_run(commands, label, [sys.executable, '-B', '-c', script], **kwargs)
        real_commands = M.Commands
        def commands(*args, **kwargs):
            return real_commands(*args, **kwargs, cleanup_seconds=0.1)
        with mock.patch.object(M, 'tool_environment', return_value=(paths, {})), \
             mock.patch.object(M, 'apple_producer_provenance', return_value={'fake_boundary': True}), \
             mock.patch.object(M.sys, 'platform', 'darwin'), \
             mock.patch.object(M.Commands, 'run', run), \
             mock.patch.object(M, 'Commands', side_effect=commands):
            receipt = M.execute(SimpleNamespace(output=self.root / 'evidence', execute_toolchains=True))
        self.assertEqual(sentinel.read_text(), 'preserve')
        return receipt, calls

    def test_producer_failure_preserves_receipt_and_removes_only_owned_scratch(self):
        receipt, calls = self.execute_to_producer()
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['error'], 'debug-producer-build: unexpected exit 3')
        self.assertTrue(receipt['cleanup']['owned_scratch_removed'])
        self.assertTrue(receipt['cleanup']['command_custody_terminal'])
        self.assertEqual(list((self.root / 'evidence').glob('generated-java-owned-*')), [])
        self.assertTrue(all(r['terminal_custody'] for r in receipt['command_records']))
        argv = next(a for label, a in calls if label == 'debug-producer-build')
        self.assertEqual(argv[argv.index('-j') + 1], '2')
        self.assertEqual(receipt['producer_jobs'], 2)

    def test_execute_retains_scratch_on_denied_signal(self):
        self.retained_scratch('denied-signal')

    def test_execute_retains_scratch_on_denied_observation(self):
        self.retained_scratch('denied-observation')

    def test_execute_retains_scratch_on_unknown_cleanup(self):
        self.retained_scratch('unknown')

    def test_execute_persists_fallback_facts_on_command_receipt_write_denial(self):
        self.retained_scratch('receipt-denied')

    def test_scratch_removal_denial_retains_path_and_failure_receipt(self):
        real_rmtree = M.shutil.rmtree
        def rmtree(path, *args, **kwargs):
            if Path(path).name.startswith('generated-java-owned-'):
                raise PermissionError('fake scratch deletion denied')
            return real_rmtree(path, *args, **kwargs)
        with mock.patch.object(M.shutil, 'rmtree', side_effect=rmtree):
            receipt, _ = self.execute_to_producer()
        self.assertEqual(receipt['status'], 'failed')
        self.assertTrue(receipt['cleanup']['command_custody_terminal'])
        self.assertFalse(receipt['cleanup']['owned_scratch_removed'])
        self.assertIn('scratch deletion denied', receipt['cleanup']['error'])
        self.assertTrue(Path(receipt['cleanup']['owned_scratch_path']).exists())

    def retained_scratch(self, outcome):
        receipt, _ = self.execute_to_producer(outcome)
        self.assertEqual(receipt['status'], 'failed')
        self.assertFalse(receipt['cleanup']['command_custody_terminal'])
        self.assertFalse(receipt['cleanup']['owned_scratch_removed'])
        scratch = Path(receipt['cleanup']['owned_scratch_path'])
        self.assertEqual((scratch / 'custody-sentinel').read_text(), 'retain on uncertain cleanup')
        self.assertIn('retention_reason', receipt['cleanup'])
        self.assertEqual(json.loads((self.root / 'evidence/receipt.json').read_text()), receipt)

    def test_absent_tool_execution_selection_fails_before_any_child(self):
        with mock.patch.object(M.subprocess, 'Popen', side_effect=AssertionError('unexpected child')):
            receipt = M.execute(SimpleNamespace(output=self.root / 'evidence', execute_toolchains=False))
        self.assertEqual(receipt['status'], 'failed')
        self.assertIn('--execute-toolchains', receipt['error'])
        self.assertFalse(receipt['cleanup']['owned_scratch_started'])

    def test_explicit_swift_launcher_name_survives_symlink_resolution(self):
        paths = {k: self.root / k for k in ('swift_sdks', 'android_artifact', 'jdk', 'android_sdk')}
        for path in paths.values():
            path.mkdir()
        real = self.root / 'bin/swift-driver'
        real.parent.mkdir()
        real.write_bytes(b'fake-tool-never-executed')
        real.chmod(0o700)
        launcher = self.root / 'bin/swift'
        launcher.symlink_to(real)
        for path in (paths['android_artifact'] / 'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android28-clang',
                     paths['android_artifact'] / 'swift-sdk.json', paths['jdk'] / 'bin/javac',
                     paths['jdk'] / 'bin/javap',
                     paths['android_sdk'] / 'platforms/android-37.0/android.jar',
                     paths['android_sdk'] / 'build-tools/37.0.0/d8',
                     paths['android_sdk'] / 'build-tools/37.0.0/dexdump'):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fake-tool-never-executed')
        with mock.patch.object(M.subprocess, 'Popen', side_effect=AssertionError('unexpected child')):
            selected, env = M.tool_environment(SimpleNamespace(swift=launcher, **paths))
        self.assertEqual(selected['swift'], launcher)
        self.assertEqual(env['MIXER_SWIFT'], str(launcher))
        self.assertEqual(env['PATH'].split(os.pathsep)[0], str(launcher.parent))

    def test_apple_producer_selection_is_explicit_scoped_and_records_metadata(self):
        developer = self.root / 'Xcode.app/Contents/Developer'
        sdk = developer / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'
        sdk.mkdir(parents=True)
        version = developer.parent / 'version.plist'
        version.write_bytes(plistlib.dumps({'CFBundleShortVersionString': '26.6', 'ProductBuildVersion': 'test-only'}))
        settings = sdk / 'SDKSettings.json'
        M.save(settings, {'CanonicalName': 'macosx26.5', 'Version': '26.5'})
        env = {'DEVELOPER_DIR': str(developer), 'SDKROOT': str(sdk)}
        original = os.environ.copy()
        with mock.patch.object(M.subprocess, 'Popen', side_effect=AssertionError('unexpected child')):
            result = M.apple_producer_provenance(env)
            self.assertEqual(result['selection'], env)
            self.assertEqual(result['xcode_version'], '26.6')
            self.assertEqual(result['sdk_version'], '26.5')
            self.assertEqual(result['sdk_settings'], M.identity(settings))
            self.assertEqual(result['xcode_version_plist'], M.identity(version))
            for invalid in ({}, {'SDKROOT': str(sdk)}, {'DEVELOPER_DIR': str(developer)},
                            {'DEVELOPER_DIR': 'relative', 'SDKROOT': str(sdk)}):
                with self.assertRaisesRegex(RuntimeError, 'Explicit per-command'):
                    M.apple_producer_provenance(invalid)
            with self.assertRaisesRegex(RuntimeError, 'must belong'):
                M.apple_producer_provenance({**env, 'SDKROOT': str(self.root)})
            M.save(settings, {'CanonicalName': 'macosx26.5', 'Version': 'changed'})
            self.assertNotEqual(M.apple_producer_provenance(env), result)
        self.assertEqual(os.environ, original)

    def test_relative_or_incomplete_tool_paths_fail_closed(self):
        with mock.patch.object(M.subprocess, 'Popen', side_effect=AssertionError('unexpected child')):
            with self.assertRaisesRegex(RuntimeError, 'must be absolute'):
                M.tool_environment(SimpleNamespace(swift=Path('relative')))
            with mock.patch.object(M.sys, 'platform', 'darwin'):
                args = SimpleNamespace(output=self.root / 'evidence', execute_toolchains=True,
                    **{k: self.root / 'missing' for k in ('swift', 'swift_sdks', 'android_artifact', 'jdk', 'android_sdk')})
                receipt = M.execute(args)
        self.assertEqual(receipt['status'], 'failed')
        self.assertFalse(receipt['cleanup']['owned_scratch_started'])


if __name__ == '__main__':
    unittest.main()
