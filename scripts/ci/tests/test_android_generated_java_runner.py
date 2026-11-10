"""Pure Python runner controls. Fake children never qualify Java/Swift or DEX."""
import copy
from contextlib import ExitStack, nullcontext
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
from types import FunctionType, SimpleNamespace
import unittest
from unittest import mock

RUNNER = Path(__file__).resolve().parents[1] / 'check-android-generated-java.py'
SPEC = importlib.util.spec_from_file_location('android_generated_java_runner', RUNNER)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def data_identity(value):
    return {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}



class FakeCommandBoundary:
    """Synthetic uncertainty only; no real process, descriptor or finalizer exists."""
    def __init__(self, root, *, stdout=b'', live=False, denied_signal=False,
                 observation='absent', read_error=False, reap_error=False,
                 pipe_close_error=False, selector_close_error=False):
        self.root = root
        self.stdout = stdout
        self.live = live
        self.signal_error = 'fake live-child denial' if live else 'fake denied owned signal'
        self.observation_error = 'fake live-child denial' if live else 'fake denied observation'
        self.denied_signal = denied_signal
        self.observation = observation
        self.read_error = read_error
        self.reap_error = reap_error
        self.pipe_close_error = pipe_close_error
        self.selector_close_error = selector_close_error
        self.exit_code = 0
        self.now = 1000.0
        self.events, self.children, self.selectors = [], [], []
        self.pipes = {}
        self.stack = ExitStack()

    def event(self, operation, *args):
        self.events.append([operation, *args])

    def monotonic(self):
        self.now += 0.001
        return self.now

    def sleep(self, seconds):
        if seconds < 0:
            raise AssertionError('negative fake sleep')
        self.event('sleep', seconds)
        self.now += seconds

    def popen(self, argv, **kwargs):
        if kwargs.get('start_new_session') is not True:
            raise AssertionError('fake launch must own its group')
        self.event('Popen', list(argv))
        boundary = self
        class Pipe:
            def __init__(self, name, fd, data):
                self.name, self.fd, self.data, self.closed = name, fd, data, False
            def fileno(self):
                boundary.event('fileno', self.name)
                return self.fd
            def close(self):
                boundary.event('close-pipe', self.name)
                if boundary.pipe_close_error and self.name == 'stdout':
                    raise OSError('fake stdout close failure')
                self.closed = True
        class Process:
            def __init__(self):
                self.pid = -100001 - len(boundary.children)
                self.live, self.returncode = boundary.live, None
                offset = 2 * len(boundary.children)
                self.stdout = Pipe('stdout', -200001-offset, boundary.stdout)
                self.stderr = Pipe('stderr', -200002-offset, b'')
                for pipe in (self.stdout, self.stderr):
                    boundary.pipes[pipe.fd] = (self, pipe)
            def poll(self):
                boundary.event('poll', self.pid)
                if not self.live:
                    self.returncode = boundary.exit_code
                return self.returncode
            def wait(self, timeout=None):
                boundary.event('wait', self.pid, timeout)
                if self.live or boundary.reap_error:
                    raise subprocess.TimeoutExpired('fake', 0.2 if boundary.reap_error else timeout)
                self.returncode = boundary.exit_code
                return self.returncode
        child = Process()
        self.children.append(child)
        M._PROCESS_OWNERS[id(child)] = child
        return child

    def selector(self):
        boundary = self
        boundary.event('selector-create')
        class Selector:
            def __init__(self):
                self.mapping, self.closed = {}, False
            def register(self, pipe, events, data):
                if boundary.pipes.get(pipe.fd, (None, None))[1] is not pipe:
                    raise AssertionError('foreign fake pipe')
                boundary.event('register', data)
                key = SimpleNamespace(fileobj=pipe, fd=pipe.fd, data=data)
                self.mapping[pipe.fd] = key
                return key
            def unregister(self, pipe):
                boundary.event('unregister', pipe.name)
                return self.mapping.pop(pipe.fd)
            def get_map(self):
                return self.mapping
            def select(self, timeout=None):
                boundary.event('select', timeout)
                boundary.now += timeout or 0
                return [(key, 1) for key in list(self.mapping.values())]
            def close(self):
                boundary.event('close-selector')
                if boundary.selector_close_error:
                    raise OSError('fake selector close failure')
                self.closed = True
        selected = Selector()
        self.selectors.append(selected)
        return selected

    def read(self, fd, size):
        if type(fd) is not int or fd not in self.pipes:
            raise AssertionError('foreign fake descriptor')
        child, pipe = self.pipes[fd]
        self.event('read', pipe.name, size)
        if self.read_error and pipe.name == 'stderr':
            raise OSError('fake stderr read failure')
        if pipe.data:
            data, pipe.data = pipe.data[:size], pipe.data[size:]
            return data
        if child.live:
            raise BlockingIOError('fake live pipe')
        return b''

    def set_blocking(self, fd, blocking):
        if type(fd) is not int or fd not in self.pipes or blocking is not False:
            raise AssertionError('foreign fake nonblocking request')
        self.event('set-blocking', fd, blocking)

    def killpg(self, pgid, sig):
        child = self.children[-1] if self.children else None
        if type(pgid) is not int or child is None or child.pid != pgid or sig not in (0, signal.SIGKILL):
            raise AssertionError('foreign fake group or signal')
        self.event('killpg', pgid, int(sig))
        if sig == signal.SIGKILL:
            if self.denied_signal:
                raise PermissionError(self.signal_error)
            if child.live:
                child.live = False
                return
        elif self.observation == 'denied':
            raise PermissionError(self.observation_error)
        elif self.observation == 'present' or child.live:
            return
        raise ProcessLookupError('fake owned group absent')

    def cleanup_markers(self):
        # These are plain Python markers, with no __del__ or OS ownership.
        self.event('test-finally-marker-cleanup')
        for child in self.children:
            child.stdout.closed = child.stderr.closed = True
        for selected in self.selectors:
            selected.closed = True

    def reject_descriptor(self, *args, **kwargs):
        raise AssertionError('public fake process OS never forwards receipt descriptors')

    def receipt_path(self, path):
        # Ordinary canonical paths only. No path subclass, symlink traversal,
        # descriptor argument, or target outside this explicitly owned root.
        if type(path) is not type(Path()) or not path.is_absolute():
            raise AssertionError('receipt requires an ordinary absolute Path')
        if path == self.root or not path.is_relative_to(self.root):
            raise AssertionError('receipt path outside owned root')
        if path.resolve() != path:
            raise AssertionError('receipt path is not canonical')
        parent = path.parent
        while True:
            if parent.is_symlink() or not parent.is_dir():
                raise AssertionError('receipt parent is not an ordinary directory')
            if parent == self.root:
                break
            parent = parent.parent
        for target in (path, path.with_name(path.name + '.next')):
            if target.is_symlink() or target.exists() and not target.is_file():
                raise AssertionError('receipt target is not an ordinary file')
        return path

    def __enter__(self):
        # Capture exact project writer code before replacing any module globals.
        if (type(self.root) is not type(Path()) or not self.root.is_absolute()
                or self.root.resolve(strict=True) != self.root or not self.root.is_dir()):
            raise AssertionError('explicit ordinary owned root required')
        names = ('os', 'subprocess', 'selectors', 'time', 'save', 'durable_save',
                 'COMMAND_PROCESS', '_PROCESS_OWNERS', '_COMMAND_OWNERS', '_CLI_OWNERS')
        self.missing = object()
        self.originals = {name: getattr(M, name, self.missing) for name in names}
        filesystem = SimpleNamespace(**{name: getattr(M.os, name) for name in
            ('open', 'fsync', 'close', 'replace', 'O_RDONLY', 'O_DIRECTORY')})
        self._receipt_writers = {}
        def writer(name):
            source = self.originals[name]
            bound = FunctionType(source.__code__,
                {'__builtins__': source.__globals__['__builtins__'],
                 'json': source.__globals__['json'], 'os': filesystem},
                source.__name__, source.__defaults__, source.__closure__)
            self._receipt_writers[name] = bound
            def persist(path, value):
                return bound(self.receipt_path(path), value)
            return persist
        fake_os = SimpleNamespace(environ=os.environ, pathsep=os.pathsep,
            read=self.read, set_blocking=self.set_blocking, killpg=self.killpg,
            **{name: self.reject_descriptor for name in
               ('open', 'fdopen', 'fstat', 'fsync', 'close', 'dup', 'dup2',
                'write', 'lseek', 'ftruncate', 'fchmod', 'replace')})
        fake_subprocess = SimpleNamespace(Popen=self.popen, PIPE=subprocess.PIPE,
            DEVNULL=subprocess.DEVNULL, TimeoutExpired=subprocess.TimeoutExpired)
        fake_selectors = SimpleNamespace(DefaultSelector=self.selector, EVENT_READ=1)
        fake_time = SimpleNamespace(monotonic=self.monotonic, sleep=self.sleep)
        try:
            for name, value in (('os', fake_os), ('subprocess', fake_subprocess),
                    ('selectors', fake_selectors), ('time', fake_time),
                    ('save', writer('save')), ('durable_save', writer('durable_save')),
                    ('COMMAND_PROCESS', self.popen), ('_PROCESS_OWNERS', {}),
                    ('_COMMAND_OWNERS', []), ('_CLI_OWNERS', [])):
                self.stack.enter_context(mock.patch.object(M, name, value, create=True))
        except BaseException:
            self.stack.close()
            raise
        return self

    def __exit__(self, *exc):
        self.stack.close()
        if any(getattr(M, name, self.missing) is not value for name, value in self.originals.items()):
            raise AssertionError('fake boundary patch restoration failed')


class RunnerControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='generated-java-python-controls-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve(strict=True)

    def consumer(self):
        root = self.root / 'consumer'
        sdk = {'Package.swift': b'owned package', 'Sources/MixerCore/Lifecycle.swift': b'owned core',
               'Sources/MixerUI/UI.swift': b'owned UI',
               'Sources/MixerAndroid/AndroidUIHost.swift': b'owned public host'}
        adapter = {f'app/src/dev/mixer/android/Product{i:02}.java': b'owned input' for i in range(21)}
        adapter.update({'Sources/MixerAndroidRuntime/Entry.swift': b'owned runtime',
                        'bridge/jni.c': b'owned JNI', 'contracts/ui.json': b'owned contract'})
        profile = {'schema': 1, 'id': 'mixer.android-source-pair.18',
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

    def test_canonical_live_policy_selects_all_21_not_instrumentation(self):
        profile = M.load_profile()
        roster = M.java_roster(profile)
        self.assertEqual(len(roster), 21)
        self.assertNotIn('app/src/dev/mixer/android/AdapterInstrumentation.java', roster)
        for kind, prefix in (('sdk', 'sdk/'), ('adapter', 'native/android/')):
            for path, expected in profile[kind + '_files'].items():
                actual = M.ROOT / (prefix + ('engine/' if kind == 'adapter' and path.startswith('Sources/') else '') + path)
                self.assertEqual(M.identity(actual), expected, str(actual))

    def test_valid_snapshot_preserves_full_inventory(self):
        consumer = self.consumer()
        result = self.validate(consumer)
        self.assertIn('mixer.lock', result)
        self.assertEqual(len([p for p in result if p.endswith('.java')]), 21)

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
        with self.assertRaisesRegex(RuntimeError, 'all 21'):
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
                self.assertEqual(len(argv[7:]), 21)
                if fail_d8:
                    raise RuntimeError('fake D8 failure')
                (Path(argv[6]) / 'classes.dex').write_bytes(b'dex\n035\0fake-control')
            elif label.endswith('-javap-members'):
                self.assertEqual(argv[:5], [self.root / 'jdk/bin/javap', '-v', '-p', '-c', '-s'])
                self.assertEqual(len(argv[5:]), 21)
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
        self.assertEqual(len(result['sources']), 21)
        self.assertEqual(len(result['classes']), 21)
        self.assertEqual(result['member_references']['count'], 63)
        self.assertIn('No API28 floor/linkage approval', result['member_references']['scope'])
        raw = self.root / 'compile/member-references.javap.txt'
        self.assertEqual(M.identity(raw), {k: result['member_references']['raw_output'][k] for k in ('bytes', 'sha256')})
        members = json.loads((self.root / 'compile/member-references.json').read_text())
        self.assertEqual({r['kind'] for r in members['references']}, {'Methodref', 'Fieldref', 'InterfaceMethodref'})
        self.assertEqual(len({r['class_file'] for r in members['references']}), 21)

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
        # The orphan edge is synthetic: parent already exited, inherited pipes
        # stay open until the owned-group signal, then all terminal facts release.
        class InheritedPipes(FakeCommandBoundary):
            def __init__(boundary, *args, **kwargs):
                super().__init__(*args, **kwargs)
                boundary.descendant_open = True

            def popen(boundary, *args, **kwargs):
                child = super().popen(*args, **kwargs)
                if child.poll() is None:
                    raise AssertionError('synthetic parent must already be reaped')
                boundary.event('parent-already-reaped', child.pid)
                return child

            def read(boundary, fd, size):
                if (fd in boundary.pipes and not boundary.pipes[fd][1].data
                        and boundary.descendant_open):
                    boundary.event('read-descendant-open', fd)
                    raise BlockingIOError('synthetic inherited pipe remains open')
                return super().read(fd, size)

            def killpg(boundary, pgid, sig):
                if (type(pgid) is int and boundary.children
                        and pgid == boundary.children[-1].pid
                        and sig == signal.SIGKILL and not boundary.denied_signal):
                    boundary.event('killpg', pgid, int(sig))
                    boundary.descendant_open = False
                    return
                return super().killpg(pgid, sig)

        with InheritedPipes(self.root, stdout=b'inherited-pipe diagnostic\n') as boundary:
            commands = M.Commands(self.root, os.environ.copy(), seconds=3,
                                  command_seconds=0.3, cleanup_seconds=0.2)
            with self.assertRaisesRegex(RuntimeError, 'timeout|terminal custody'):
                commands.run('python-owned-descendant', ['synthetic-exited-parent'])
            record = commands.records[0]
            self.assertEqual(record['stop'], 'timeout')
            self.assertEqual(record['signal']['outcome'], 'sent')
            self.terminal_record(record)
            self.assertTrue(record['descriptors_closed'])
            self.assertTrue(commands.custody_terminal())
            self.assertIsNone(commands.hold)
            self.assertLess(record['elapsed_seconds'], 1)
            self.assertEqual((self.root / '000-python-owned-descendant.stdout').read_text(),
                             'inherited-pipe diagnostic\n')
            signal_index = next(i for i, event in enumerate(boundary.events)
                                if event[0] == 'killpg' and event[2] == signal.SIGKILL)
            self.assertTrue(any(event[0] == 'poll' for event in boundary.events[:signal_index]))
            self.assertTrue(any(event[0] == 'read-descendant-open'
                                for event in boundary.events[:signal_index]))
            self.assertTrue(all(pipe.closed for child in boundary.children
                                for pipe in (child.stdout, child.stderr)))
            self.assertTrue(all(selected.closed for selected in boundary.selectors))
            self.assertEqual((M._PROCESS_OWNERS, M._COMMAND_OWNERS, M._CLI_OWNERS), ({}, [], []))

    def test_cooperative_parent_waits_for_descendant_and_releases_custody(self):
        commands = self.commands()
        child = ('import sys,time; time.sleep(0.02); print("child finished"); '
                 'print("child diagnostic",file=sys.stderr)')
        parent = ('import subprocess,sys; child=subprocess.Popen([sys.executable,"-B","-c",'
                  + repr(child) + ']); code=child.wait(); '
                  'sys.exit(code) if code else None; print("parent waited")')
        launched, factory = [], M.COMMAND_PROCESS
        def observe_launch(*args, **kwargs):
            process = factory(*args, **kwargs)
            launched.append(process)
            return process
        with mock.patch.object(M, 'COMMAND_PROCESS', observe_launch):
            self.assertEqual(commands.run('cooperative-descendant',
                [sys.executable, '-B', '-c', parent]), 'child finished\nparent waited\n')
        self.assertEqual(len(launched), 1)
        self.assertTrue(all(pipe.closed for pipe in (launched[0].stdout, launched[0].stderr)))
        record = commands.records[0]
        self.terminal_record(record)
        self.assertTrue(record['descriptors_closed'])
        self.assertTrue(commands.custody_terminal())
        self.assertIsNone(commands.hold)
        self.assertEqual((self.root / '000-cooperative-descendant.stderr').read_text(),
                         'child diagnostic\n')
        self.assertEqual((M._PROCESS_OWNERS, M._COMMAND_OWNERS, M._CLI_OWNERS), ({}, [], []))

    def test_denied_signal_retains_receipt_even_after_child_exits(self):
        with FakeCommandBoundary(root=self.root, stdout=b'retained\n', denied_signal=True):
            commands = self.commands()
            with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                commands.run('denied-signal', [sys.executable, '-B', '-c', 'print("retained")'])
            record = json.loads((self.root / 'commands.json').read_text())[0]
            self.assertTrue(record['direct_child_reaped'])
            self.assertTrue(record['owned_group_absent'])
            self.assertFalse(record['terminal_custody'])
            self.assertEqual(record['signal']['outcome'], 'denied')
            self.assertEqual((self.root / '000-denied-signal.stdout').read_text(), 'retained\n')
            with self.assertRaisesRegex(RuntimeError, 'Prior command custody|Sticky inner custody hold'):
                commands.run('no-followup', [sys.executable, '-B', '-c', 'pass'])

    def test_denied_or_unknown_group_observation_cannot_pass(self):
        for denied in (True, False):
            with FakeCommandBoundary(root=self.root, observation='denied' if denied else 'present'):
                commands = self.commands()
                with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                    commands.run('unknown-group', [sys.executable, '-B', '-c', 'pass'])
            record = json.loads((self.root / 'commands.json').read_text())[0]
            self.assertEqual(record['group_observation']['outcome'], 'denied' if denied else 'present-at-deadline')
            self.assertFalse(record['owned_group_absent'])
            self.assertFalse(record['terminal_custody'])
            self.assertTrue(record['direct_child_reaped'])
            self.assertTrue(record['stdout_eof'] and record['stderr_eof'])

    def test_live_child_denied_cleanup_still_persists_unknown_terminal_facts(self):
        with FakeCommandBoundary(root=self.root, stdout=b'owned\n', live=True, denied_signal=True,
                                 observation='denied') as boundary:
            commands = M.Commands(self.root, os.environ.copy(), seconds=2,
                                  command_seconds=0.03, cleanup_seconds=0.03)
            try:
                with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                    commands.run('denied-live', [sys.executable, '-B', '-c',
                        'import time; print("owned",flush=True); time.sleep(3)'])
                record = json.loads((self.root / 'commands.json').read_text())[0]
                self.assertEqual(record['pid'], boundary.children[0].pid)
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
                boundary.cleanup_markers()

    def test_one_stream_read_error_cannot_be_reported_as_eof(self):
        with FakeCommandBoundary(root=self.root, stdout=b'owned\n', read_error=True):
            commands = self.commands()
            with self.assertRaisesRegex(RuntimeError, 'stderr read failure'):
                commands.run('stream-error', [sys.executable, '-B', '-c', 'print("owned")'])
        record = json.loads((self.root / 'commands.json').read_text())[0]
        self.assertTrue(record['stdout_eof'])
        self.assertFalse(record['stderr_eof'])
        self.assertTrue(record['direct_child_reaped'])
        self.assertFalse(record['terminal_custody'])
        self.assertIn('drain-stderr', {e['operation'] for e in record['cleanup_errors']})

    def test_nested_reap_and_selector_cleanup_errors_still_persist(self):
        # Each error occurs at its permitted cleanup stage. UNKNOWN from reap
        # must not require a subsequent pipe or selector close on the successor.
        observed = set()
        for stage, options, operation in (
                ('reap', {'reap_error': True}, 'reap-direct-child'),
                ('pipe', {'pipe_close_error': True}, 'close-stdout'),
                ('selector', {'selector_close_error': True}, 'close-selector')):
            folder = self.root / stage
            folder.mkdir()
            with FakeCommandBoundary(root=self.root, stdout=b'diagnostic\n', **options) as boundary:
                commands = M.Commands(folder, {}, seconds=5, cleanup_seconds=0.2)
                try:
                    with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                        commands.run('nested-errors', ['synthetic-only'])
                    record = json.loads((folder / 'commands.json').read_text())[0]
                    operations = {e['operation'] for e in record['cleanup_errors']}
                    self.assertEqual(operations, {operation})
                    observed.update(operations)
                    self.assertEqual(record['direct_child_reaped'], stage != 'reap')
                    self.assertFalse(record['terminal_custody'])
                    self.assertTrue(record['stdout_eof'] and record['stderr_eof'])
                    self.assertEqual((folder / '000-nested-errors.stdout').read_text(), 'diagnostic\n')
                finally:
                    boundary.cleanup_markers()
        self.assertEqual(observed, {'reap-direct-child', 'close-stdout', 'close-selector'})

    def test_command_receipt_write_failure_retains_in_memory_facts(self):
        with FakeCommandBoundary(root=self.root, stdout=b'owned\n'), \
             mock.patch.object(M, 'save', side_effect=PermissionError('fake receipt write denial')), \
             mock.patch.object(M, 'durable_save', side_effect=PermissionError('fake receipt write denial')):
            commands = self.commands()
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
        real_run = M.Commands.run
        synthetic = cleanup_outcome in ('denied-signal', 'denied-observation', 'unknown', 'receipt-denied')
        boundary = FakeCommandBoundary(root=self.root) if synthetic else nullcontext()
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
                if synthetic:
                    boundary.stdout = b'fake compiler failure\n'
                    boundary.exit_code = 3
                    boundary.denied_signal = cleanup_outcome == 'denied-signal'
                    boundary.signal_error = 'fake denied signal'
                    boundary.observation = ('denied' if cleanup_outcome == 'denied-observation'
                                            else 'present' if cleanup_outcome == 'unknown' else 'absent')
                real_save, real_durable_save = M.save, M.durable_save
                def save(path, value):
                    if path.name == 'commands.json' and cleanup_outcome == 'receipt-denied':
                        raise PermissionError('fake command receipt write denied')
                    return real_save(path, value)
                def durable_save(path, value):
                    if path.name == 'commands.json' and cleanup_outcome == 'receipt-denied':
                        raise PermissionError('fake command receipt write denied')
                    return real_durable_save(path, value)
                with mock.patch.object(M, 'save', side_effect=save), \
                     mock.patch.object(M, 'durable_save', side_effect=durable_save):
                    return real_run(commands, label, [sys.executable, '-B', '-c', script], **kwargs)
            if synthetic:
                boundary.stdout = (output + '\n').encode()
                boundary.exit_code = 0
            return real_run(commands, label, [sys.executable, '-B', '-c', script], **kwargs)
        real_commands = M.Commands
        def commands(*args, **kwargs):
            return real_commands(*args, **kwargs, cleanup_seconds=0.1)
        with boundary, \
             mock.patch.object(M, 'tool_environment', return_value=(paths, {})), \
             mock.patch.object(M, 'apple_producer_provenance', return_value={'fake_boundary': True}), \
             mock.patch.object(M.sys, 'platform', 'darwin'), \
             mock.patch.object(M.Commands, 'run', run), \
             mock.patch.object(M, 'Commands', side_effect=commands):
            receipt = M.execute(SimpleNamespace(output=self.root / 'evidence', execute_toolchains=True))
        self.assertEqual(sentinel.read_text(), 'preserve')
        return receipt, calls

    def execute_fake_pipeline(self, *, producer_failure=False):
        """Exercise execute's retention/deletion branches without launching children."""
        paths = {k: self.root / k for k in ('swift', 'jdk', 'android_sdk')}
        inspection = {'schema': 1, 'sdk_id': 'aarch64-unknown-linux-android28',
                      'min_api': 28, 'target_api': 37, 'javac_version': 'javac 25.fake-control',
                      'tools': {'swift': {'path': str(paths['swift'])},
                                'javac': {'path': str(paths['jdk'] / 'bin/javac')}},
                      'distributions': {'android_platform': {
                          'path': str(paths['android_sdk'] / 'platforms/android-37.0')}}}
        for path in (paths['jdk'] / 'bin/javap',
                     paths['android_sdk'] / 'platforms/android-37.0/android.jar'):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'pure-fake-never-executed')
        sentinel = self.root / 'unowned-sentinel'
        sentinel.write_text('preserve')
        calls = []

        class FakeCommands:
            def __init__(self, out, env):
                self.records, self.hold = [], None

            def custody_terminal(self):
                return True

            def run(self, label, argv, **kwargs):
                argv = list(map(str, argv))
                calls.append((label, argv))
                record = {'label': label, 'exit_code': 0, 'terminal_custody': True,
                          'inner_receipts': [], 'direct_child_reaped': True,
                          'stdout_eof': True, 'stderr_eof': True,
                          'owned_group_absent': True, 'descriptors_closed': True}
                self.records.append(record)
                if label in ('revision', 'git-tree'):
                    return 'pure-fake-git-identity'
                if label in ('official-inspect', 'official-inspect-postflight'):
                    return json.dumps(inspection)
                if label == 'd8-version':
                    return 'pure-fake D8'
                if label in ('javap-version', 'javap-version-postflight'):
                    return '25.fake-control'
                if label.endswith('-producer-build'):
                    scratch = Path(argv[argv.index('--scratch-path') + 1]).parent
                    (scratch / 'custody-sentinel').write_text('retain integration evidence')
                    if producer_failure:
                        record['exit_code'] = 3
                        raise RuntimeError(label + ': unexpected exit 3')
                    return ''
                if label.endswith('-producer-bin'):
                    binary = Path(argv[argv.index('--scratch-path') + 1]) / 'bin'
                    binary.mkdir(parents=True)
                    (binary / 'mixer').write_bytes(b'pure-fake CLI never executed')
                    return str(binary)
                if label.endswith('-create'):
                    consumer = Path(argv[argv.index('--directory') + 1])
                    consumer.mkdir()
                    (consumer / 'mixer.lock').write_text('{}')
                    descriptor = consumer / 'Generated/MixerAndroid' / M.DESCRIPTOR
                    descriptor.parent.mkdir(parents=True)
                    descriptor.write_text('{}')
                    record['inner_required'] = ('version', 'inspect')
                    return ''
                if label.endswith('-export'):
                    M.shutil.copytree(Path(argv[-1]), Path(argv[2]))
                    return ''
                raise AssertionError('unexpected fake command: ' + label)

        class Loader:
            def create_module(self, spec):
                return None

            def exec_module(self, module):
                module.dependency_checkouts = lambda *args: {}

        def compile_consumer(consumer, artifact, *args):
            artifact.mkdir()
            return {'sources': list(range(21)), 'classes': ['Fake'], 'member_references': {}}

        spec = importlib.util.spec_from_loader('generated_java_dependencies', Loader())
        with mock.patch.object(M, 'tool_environment', return_value=(paths, {})), \
             mock.patch.object(M, 'apple_producer_provenance', return_value={'fake_boundary': True}), \
             mock.patch.object(M.sys, 'platform', 'darwin'), \
             mock.patch.object(M, 'Commands', FakeCommands), \
             mock.patch.object(M, 'load_profile', return_value={}), \
             mock.patch.object(M, 'source_inputs', return_value={'fake': data_identity(b'fixture')}), \
             mock.patch.object(M.importlib.util, 'spec_from_file_location', return_value=spec), \
             mock.patch.object(M, 'validate_consumer', return_value={}), \
             mock.patch.object(M, 'inventory', return_value={}), \
             mock.patch.object(M, 'compile_consumer', side_effect=compile_consumer), \
             mock.patch.object(M, 'tamper_consumers', return_value={}):
            receipt = M.execute(SimpleNamespace(output=self.root / 'evidence', execute_toolchains=True))
        self.assertEqual(sentinel.read_text(), 'preserve')
        return receipt, calls

    def test_producer_failure_preserves_receipt_and_retains_owned_scratch(self):
        with mock.patch.object(M.shutil, 'rmtree', side_effect=AssertionError('unsafe failure cleanup')) as remove:
            receipt, calls = self.execute_fake_pipeline(producer_failure=True)
        remove.assert_not_called()
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['error'], 'debug-producer-build: unexpected exit 3')
        self.assertFalse(receipt['cleanup']['owned_scratch_removed'])
        self.assertTrue(receipt['cleanup']['command_custody_terminal'])
        scratch = Path(receipt['cleanup']['owned_scratch_path'])
        self.assertEqual(list((self.root / 'evidence').glob('generated-java-owned-*')), [scratch])
        self.assertEqual((scratch / 'custody-sentinel').read_text(), 'retain integration evidence')
        self.assertIn('Failed integration', receipt['cleanup']['retention_reason'])
        self.assertNotIn('error', receipt['cleanup'])
        self.assertTrue(all(r['terminal_custody'] for r in receipt['command_records']))
        self.assertEqual(receipt['command_records'][-1]['exit_code'], 3)
        self.assertEqual(json.loads((self.root / 'evidence/receipt.json').read_text()), receipt)
        before = json.loads((self.root / 'evidence/receipt-before-cleanup.json').read_text())
        self.assertEqual(before['error'], receipt['error'])
        self.assertEqual(before['command_records'], receipt['command_records'])
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
        attempted = []
        def rmtree(path, *args, **kwargs):
            if Path(path).name.startswith('generated-java-owned-'):
                attempted.append(Path(path))
                raise PermissionError('fake scratch deletion denied')
            return real_rmtree(path, *args, **kwargs)
        with mock.patch.object(M.shutil, 'rmtree', side_effect=rmtree):
            receipt, calls = self.execute_fake_pipeline()
        self.assertEqual(receipt['status'], 'failed')
        self.assertTrue(receipt['cleanup']['command_custody_terminal'])
        self.assertFalse(receipt['cleanup']['owned_scratch_removed'])
        self.assertIn('scratch deletion denied', receipt['cleanup']['error'])
        scratch = Path(receipt['cleanup']['owned_scratch_path'])
        self.assertEqual(attempted, [scratch])
        self.assertEqual((scratch / 'custody-sentinel').read_text(), 'retain integration evidence')
        self.assertNotIn('error', receipt)
        self.assertNotIn('retention_reason', receipt['cleanup'])
        self.assertEqual(set(receipt['consumers']), {m + '-' + f for m in M.MODES for f in M.FORMS})
        self.assertTrue(all(r['terminal_custody'] and r['exit_code'] == 0 for r in receipt['command_records']))
        self.assertEqual(calls[-1][0], 'javap-version-postflight')
        before = json.loads((self.root / 'evidence/receipt-before-cleanup.json').read_text())
        self.assertEqual(before['status'], 'passed-java-crosscompile-only')
        self.assertEqual(before['consumers'], receipt['consumers'])
        self.assertNotIn('error', before['cleanup'])
        self.assertEqual(json.loads((self.root / 'evidence/receipt.json').read_text()), json.loads(json.dumps(receipt)))

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
