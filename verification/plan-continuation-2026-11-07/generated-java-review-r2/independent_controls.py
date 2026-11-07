"""Independent Python/fake-boundary review. Never invokes Swift or Java tools."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location('r2_independent_runner', ROOT / 'scripts/ci/check-android-generated-java.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
FACTS = {'scope': 'Python children, fake tool responses, and copied Java source inputs only', 'cases': {}}


class IndependentControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='r2-independent-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def commands(self, **kwargs):
        return M.Commands(self.root, os.environ.copy(), seconds=4, command_seconds=0.3,
                          cleanup_seconds=0.15, **kwargs)

    def record(self, name, value):
        FACTS['cases'][name] = value

    def test_success_and_compile_failure_have_terminal_custody(self):
        commands = self.commands()
        children, probes = [], []
        real_popen, real_killpg = subprocess.Popen, os.killpg
        def popen(*args, **kwargs):
            self.assertTrue(kwargs['start_new_session'])
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child
        def killpg(pgid, sig):
            self.assertIn(pgid, [child.pid for child in children])
            probes.append([pgid, sig])
            return real_killpg(pgid, sig)
        with mock.patch.object(M.subprocess, 'Popen', side_effect=popen), \
             mock.patch.object(M.os, 'killpg', side_effect=killpg):
            self.assertEqual(commands.run('ok', [sys.executable, '-B', '-c', 'print("ok")']), 'ok\n')
            with self.assertRaisesRegex(RuntimeError, 'unexpected exit 7'):
                commands.run('compile-failure', [sys.executable, '-B', '-c',
                    'import sys; print("compiler diagnostic",file=sys.stderr); sys.exit(7)'])
        for r, child in zip(commands.records, children):
            for key in ['direct_child_reaped', 'stdout_eof', 'stderr_eof', 'owned_group_absent', 'terminal_custody']:
                self.assertIs(r[key], True, key)
            self.assertEqual(r['group_observation']['outcome'], 'absent')
            self.assertEqual(r['cleanup_errors'], [])
            self.assertTrue(child.stdout.closed and child.stderr.closed)
        self.assertEqual(json.loads((self.root / 'commands.json').read_text()), commands.records)
        self.record('success_and_compile_failure', {'records': commands.records, 'owned_group_calls': probes})

    def test_live_denial_records_unknown_and_closes_resources(self):
        commands = self.commands()
        commands.command_seconds = 0.04
        children, selected = [], []
        real_popen, real_selector, real_killpg = subprocess.Popen, M.selectors.DefaultSelector, os.killpg
        def popen(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child
        def selector():
            value = real_selector()
            selected.append(value)
            return value
        def denied(pgid, sig):
            self.assertEqual(pgid, children[0].pid)
            raise PermissionError('independent owned-group denial')
        try:
            start = time.monotonic()
            with mock.patch.object(M.subprocess, 'Popen', side_effect=popen), \
                 mock.patch.object(M.selectors, 'DefaultSelector', side_effect=selector), \
                 mock.patch.object(M.os, 'killpg', side_effect=denied):
                with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                    commands.run('live-denied', [sys.executable, '-B', '-c',
                        'import time; time.sleep(5)'])
            r = json.loads((self.root / 'commands.json').read_text())[0]
            self.assertLess(time.monotonic() - start, 1.5)
            self.assertFalse(r['terminal_custody'] or r['owned_group_absent'] or r['direct_child_reaped'])
            self.assertFalse(r['stdout_eof'] or r['stderr_eof'])
            self.assertTrue(children[0].stdout.closed and children[0].stderr.closed)
            self.assertIsNone(selected[0].get_map())
            self.assertEqual({e['operation'] for e in r['cleanup_errors']},
                             {'signal-owned-group', 'reap-direct-child', 'observe-owned-group'})
            self.record('live_denied', {'record': r})
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
            FACTS['cases'].setdefault('live_denied', {})['harness_cleanup'] = 'Killed/reaped only created child; both streams closed and its group observed absent'

    def test_nested_wait_and_close_failures_preserve_terminal_receipt(self):
        commands = self.commands()
        children, selected, patches = [], [], []
        real_popen, real_selector = subprocess.Popen, M.selectors.DefaultSelector
        def popen(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            real_close = child.stdout.close
            def close_then_error():
                real_close()
                raise OSError('independent stdout close error')
            for obj, name, effect in [(child, 'wait', subprocess.TimeoutExpired('independent', 0.15)),
                                      (child.stdout, 'close', close_then_error)]:
                p = mock.patch.object(obj, name, side_effect=effect)
                p.start()
                patches.append(p)
            return child
        def selector():
            value = real_selector()
            selected.append(value)
            real_close = value.close
            def close_then_error():
                real_close()
                raise OSError('independent selector close error')
            p = mock.patch.object(value, 'close', side_effect=close_then_error)
            p.start()
            patches.append(p)
            return value
        try:
            with mock.patch.object(M.subprocess, 'Popen', side_effect=popen), \
                 mock.patch.object(M.selectors, 'DefaultSelector', side_effect=selector):
                with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                    commands.run('nested', [sys.executable, '-B', '-c', 'print("keep diagnostic")'])
            r = json.loads((self.root / 'commands.json').read_text())[0]
            self.assertEqual({e['operation'] for e in r['cleanup_errors']},
                             {'reap-direct-child', 'close-stdout', 'close-selector'})
            self.assertTrue(r['stdout_eof'] and r['stderr_eof'])
            self.assertFalse(r['terminal_custody'])
            self.assertTrue(children[0].stdout.closed and children[0].stderr.closed)
            self.assertIsNone(selected[0].get_map())
            self.assertEqual((self.root / '000-nested.stdout').read_text(), 'keep diagnostic\n')
            self.record('nested_errors', r)
        finally:
            for p in reversed(patches):
                p.stop()
            for child in children:
                child.wait(timeout=1)
                child.stdout.close()
                child.stderr.close()
            for value in selected:
                value.close()

    def test_unknown_group_blocks_next_command_without_spawning(self):
        commands = self.commands()
        real_killpg = os.killpg
        def killpg(pgid, sig):
            self.assertEqual(pgid, commands.records[0]['owned_pgid'])
            if sig == 0:
                return None
            return real_killpg(pgid, sig)
        with mock.patch.object(M.os, 'killpg', side_effect=killpg):
            with self.assertRaisesRegex(RuntimeError, 'terminal custody'):
                commands.run('unknown', [sys.executable, '-B', '-c', 'pass'])
        r = commands.records[0]
        self.assertEqual(r['group_observation']['outcome'], 'present-at-deadline')
        self.assertTrue(r['direct_child_reaped'] and r['stdout_eof'] and r['stderr_eof'])
        self.assertFalse(r['terminal_custody'])
        with mock.patch.object(M.subprocess, 'Popen', side_effect=AssertionError('must not spawn')):
            with self.assertRaisesRegex(RuntimeError, 'Prior command custody'):
                commands.run('forbidden-followup', [sys.executable, '-B', '-c', 'pass'])
        with self.assertRaises(ProcessLookupError):
            real_killpg(r['owned_pgid'], 0)
        self.record('unknown_group', r)

    def test_all_emitted_class_inputs_and_member_output_are_retained(self):
        profile = M.load_profile()
        consumer, dest = self.root / 'copied-consumer-inputs', self.root / 'artifacts'
        for name in M.java_roster(profile):
            p = consumer / 'Generated/MixerAndroid' / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / 'native/android' / name, p)
        jdk, sdk = self.root / 'jdk-not-executed', self.root / 'sdk-not-executed'
        calls, raw_outputs = [], []
        def run(label, argv):
            calls.append({'label': label, 'argv': list(map(str, argv))})
            if label.endswith('-javac'):
                self.assertEqual(argv[1:12], ['--release', '17', '-Xlint:all', '-Werror', '-proc:none',
                    '-sourcepath', '', '-classpath', sdk / 'platforms/android-37.0/android.jar', '-d', dest / 'classes'])
                self.assertEqual(len(argv[12:]), 18)
                for source in argv[12:]:
                    p = dest / 'classes/dev/mixer/android' / (source.stem + '.class')
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(b'fake boundary output, not JVM bytecode')
                (dest / 'classes/dev/mixer/android/Nested$1.class').write_bytes(b'fake nested output')
                return ''
            if label.endswith('-javap-members'):
                self.assertEqual(argv[:5], [jdk / 'bin/javap', '-v', '-p', '-c', '-s'])
                self.assertEqual(len(argv[5:]), 19)
                raw = '\n'.join('Classfile ' + str(p) + '\nConstant pool:\n'
                    '   #1 = Methodref          #2.#3   // java/lang/Object."<init>":()V\n'
                    '   #4 = Fieldref           #5.#6   // android/os/Build.VERSION:I\n'
                    '   #7 = InterfaceMethodref #8.#9   // java/util/List.size:()I\n'
                    for p in argv[5:])
                raw_outputs.append(raw)
                return raw
            if label.endswith('-d8'):
                self.assertEqual(argv[1:5], ['--min-api', '28', '--lib', sdk / 'platforms/android-37.0/android.jar'])
                self.assertEqual(len(argv[7:]), 19)
                (dest / 'dex/classes.dex').write_bytes(b'dex\n035\0fake DEX boundary output')
                return ''
            self.assertTrue(label.endswith('-dexdump'))
            return '\n'.join("Class descriptor  : 'L" + str(p.relative_to(dest / 'classes')).removesuffix('.class') + ";'"
                             for p in sorted((dest / 'classes').rglob('*.class')))
        result = M.compile_consumer(consumer, dest, profile, jdk, sdk, run, 'independent')
        members = json.loads((dest / 'member-references.json').read_text())
        self.assertEqual(len(members['class_inputs']), 19)
        self.assertEqual(len(members['references']), 57)
        self.assertEqual((dest / 'member-references.javap.txt').read_text(), raw_outputs[0])
        self.assertEqual(M.identity(dest / 'member-references.javap.txt'),
                         {k: result['member_references']['raw_output'][k] for k in ['bytes', 'sha256']})
        self.assertEqual(M.identity(dest / 'member-references.json'), result['member_references']['inventory'])
        self.assertIn('post-D8 reference rewriting', members['scope'])
        self.record('compile_member_selection', {'calls': calls, 'result': result, 'member_inventory': members})

    def fake_execute(self, unknown=False):
        """Test actual execute sequencing using explicit fake boundaries, no real tools."""
        paths = {k: self.root / k for k in ['swift', 'swift_sdks', 'android_artifact', 'jdk', 'android_sdk']}
        jar, javap = paths['android_sdk'] / 'platforms/android-37.0/android.jar', paths['jdk'] / 'bin/javap'
        for p in [jar, javap]:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'fake tool prerequisite, never executed')
        inspection = {'schema': 1, 'sdk_id': 'aarch64-unknown-linux-android28', 'min_api': 28, 'target_api': 37,
            'javac_version': 'javac 25.fake-review',
            'tools': {'swift': {'path': str(paths['swift'])}, 'javac': {'path': str(paths['jdk'] / 'bin/javac')}},
            'distributions': {'android_platform': {'path': str(paths['android_sdk'] / 'platforms/android-37.0')}}}
        calls, compiled, dependencies = [], [], []
        marker = self.root / 'unowned-sentinel'
        marker.write_text('preserve')
        class FakeCommands:
            def __init__(inner, *args, **kwargs):
                inner.records = []
            def custody_terminal(inner):
                return bool(inner.records) and all(r['terminal_custody'] for r in inner.records)
            def run(inner, label, argv, **kwargs):
                calls.append({'label': label, 'argv': list(map(str, argv))})
                inner.records.append({'label': label, 'terminal_custody': True, 'fake_boundary': True})
                if label in ['official-inspect', 'official-inspect-postflight']:
                    return json.dumps(inspection)
                if label.startswith('javap-version'):
                    return '25.fake-review'
                if label.endswith('-producer-build'):
                    build = Path(argv[argv.index('--scratch-path') + 1])
                    build.mkdir()
                    (build.parent / 'custody-sentinel').write_text('retain unknown custody')
                    (build / 'mixer').write_bytes(b'fake CLI, never executed')
                    if unknown:
                        inner.records[-1]['terminal_custody'] = False
                        raise RuntimeError('injected terminal custody unknown')
                if label.endswith('-producer-bin'):
                    return str(argv[argv.index('--scratch-path') + 1])
                if label.endswith('-create'):
                    consumer = Path(argv[argv.index('--directory') + 1])
                    for p in ['mixer.lock', 'Generated/MixerAndroid/' + M.DESCRIPTOR]:
                        target = consumer / p
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text('fake fixture boundary')
                if label.endswith('-export'):
                    shutil.copytree(Path(argv[-1]), Path(argv[2]))
                return 'fake-output'
        def compile_fake(consumer, artifact, profile, jdk, sdk, run, label):
            compiled.append(label)
            self.assertTrue(consumer.is_dir())
            if consumer.name == 'relocated':
                self.assertFalse((consumer.parent / 'original').exists())
            artifact.mkdir()
            return {'sources': {str(i): {} for i in range(18)}, 'classes': {'fake': {}},
                    'member_references': {'fake_boundary': True}}
        def dependency_import(*args, **kwargs):
            def load(module):
                def check(source, build, run, prefix):
                    dependencies.append(prefix)
                    return {'fake_dependency_boundary': True}
                module.dependency_checkouts = check
            return importlib.util.spec_from_loader('fake_dependencies', SimpleNamespace(create_module=lambda _: None, exec_module=load))
        tamper = mock.Mock(return_value=[{'fake_boundary': True}])
        with mock.patch.object(M, 'Commands', FakeCommands), \
             mock.patch.object(M, 'tool_environment', return_value=(paths, {})), \
             mock.patch.object(M, 'source_inputs', return_value={'sentinel': M.identity(marker)}), \
             mock.patch.object(M, 'validate_consumer', side_effect=lambda consumer, *args: M.inventory(consumer)), \
             mock.patch.object(M, 'compile_consumer', side_effect=compile_fake), \
             mock.patch.object(M, 'tamper_consumers', tamper), \
             mock.patch.object(M.importlib.util, 'spec_from_file_location', side_effect=dependency_import):
            receipt = M.execute(SimpleNamespace(output=self.root / 'execution', execute_toolchains=True))
        self.assertEqual(marker.read_text(), 'preserve')
        return receipt, calls, compiled, dependencies, tamper

    def test_both_bounded_producers_reach_all_six_consumer_forms(self):
        receipt, calls, compiled, dependencies, tamper = self.fake_execute()
        self.assertEqual(receipt['status'], 'passed-java-crosscompile-only', receipt)
        expected = [mode + '-' + form for mode in ['debug', 'release'] for form in ['original', 'relocated', 'exported']]
        self.assertEqual(compiled, expected)
        builds = [c for c in calls if c['label'].endswith('-producer-build')]
        self.assertEqual(len(builds), 2)
        for call, mode in zip(builds, ['debug', 'release']):
            argv = call['argv']
            self.assertEqual(argv[argv.index('-j') + 1], '2')
            self.assertEqual(argv[argv.index('-c') + 1], mode)
        self.assertEqual(set(receipt['consumers']), set(expected))
        self.assertEqual(tamper.call_count, 2)
        self.assertTrue(all(c.args[0].name == 'exported' for c in tamper.call_args_list))
        self.assertEqual(dependencies, ['debug-dependency', 'debug-post-dependency', 'release-dependency', 'release-post-dependency'])
        self.assertTrue(receipt['cleanup']['owned_scratch_removed'])
        self.record('six_consumer_flow', {'calls': calls, 'compiled': compiled, 'receipt': receipt,
                                        'scope': 'Fake boundaries test execute sequencing, not actual generation or tamper qualification'})

    def test_execute_unknown_custody_retains_scratch_and_failed_receipt(self):
        receipt, _, compiled, _, _ = self.fake_execute(unknown=True)
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(compiled, [])
        self.assertFalse(receipt['cleanup']['command_custody_terminal'])
        self.assertFalse(receipt['cleanup']['owned_scratch_removed'])
        scratch = Path(receipt['cleanup']['owned_scratch_path'])
        self.assertEqual((scratch / 'custody-sentinel').read_text(), 'retain unknown custody')
        self.assertEqual(json.loads((self.root / 'execution/receipt.json').read_text()), receipt)
        self.record('execute_unknown_custody', receipt)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    FACTS['tests_run'] = result.testsRun
    FACTS['passed'] = result.wasSuccessful()
    FACTS['optimized'] = not __debug__
    M.save(HERE / ('independent-optimized-facts.json' if not __debug__ else 'independent-normal-facts.json'), FACTS)
    sys.exit(0 if result.wasSuccessful() else 1)
