"""Behavioral controls for the bounded standalone framing evidence runner."""
import importlib.util
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

RUNNER = Path(__file__).resolve().parents[1] / 'check-analyzer-framing.py'
SPEC = importlib.util.spec_from_file_location('analyzer_framing_runner', RUNNER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FramingRunnerTests(unittest.TestCase):
    def setUp(self):
        # macOS /var and /tmp may themselves be links; the runner rejects lexical links.
        self.temporary = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def cli(self, *args, optimized=False, env=None):
        return subprocess.run([sys.executable, *(['-O'] if optimized else []), '-B', str(RUNNER),
                               *map(str, args)], capture_output=True, text=True, timeout=30, env=env)

    def compiler(self, name, exit_code, version=None):
        toolchain = self.root / name
        (toolchain / 'bin').mkdir(parents=True)
        compiler = toolchain / 'bin/rustc'
        version = version or 'rustc 1.99.0 (synthetic test fixture)\nbinary: rustc\nhost: synthetic-test-host\nrelease: 1.99.0'
        compiler.write_text('#!' + sys.executable + '\n'
                            'import sys\n'
                            'if sys.argv[1:] == ["--print", "sysroot"]:\n'
                            ' print(' + repr(str(toolchain)) + ')\n'
                            ' sys.exit(0)\n'
                            'if "--version" in sys.argv:\n'
                            ' print(' + repr(version) + ')\n'
                            ' sys.exit(0)\n'
                            'print("deliberate compiler failure", file=sys.stderr)\n'
                            'sys.exit(' + repr(exit_code) + ')\n')
        compiler.chmod(0o755)
        return compiler

    def test_existing_output_is_not_overwritten(self):
        output = self.root / 'already-owned'
        output.mkdir()
        sentinel = output / 'user-file'
        sentinel.write_text('preserve')
        result = self.cli('--output', output)
        self.assertEqual(result.returncode, 2)
        self.assertIn('must be fresh', result.stderr)
        self.assertEqual(sentinel.read_text(), 'preserve')
        self.assertEqual(list(output.iterdir()), [sentinel])

    def test_symlink_ancestor_and_leaf_cannot_redirect_output(self):
        target = self.root / 'target'
        target.mkdir()
        link = self.root / 'redirect'
        link.symlink_to(target, target_is_directory=True)
        for output in [link, link / 'escape']:
            with self.subTest(output=output):
                result = self.cli('--output', output, optimized=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn('Symlink path is forbidden', result.stderr)
        self.assertEqual(list(target.iterdir()), [])

    def test_git_parent_traversal_and_frozen_packet_outputs_are_rejected(self):
        for output in [self.root / '.git' / 'escape', self.root / '..' / 'escape',
                       MODULE.ROOT / MODULE.PRODUCER / 'new-ci-output']:
            with self.subTest(output=output):
                result = self.cli('--output', output, optimized=True)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(output.exists())

    def test_cli_requires_explicit_fresh_output_and_has_no_source_override(self):
        for arguments in [[], ['--source', 'replacement.rs'],
                          ['--output', str(self.root / 'must-not-exist'), '--private-tests', 'replacement.rs']]:
            with self.subTest(arguments=arguments):
                result = self.cli(*arguments)
                self.assertEqual(result.returncode, 2)
        self.assertFalse((self.root / 'must-not-exist').exists())

    def test_missing_output_parent_is_not_created(self):
        output = self.root / 'missing' / 'output'
        result = self.cli('--output', output)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.parent.exists())

    def test_optimization_cannot_disable_required_inventory(self):
        result = subprocess.run([sys.executable, '-O', '-B', '-c',
                                 'import runpy,sys; runpy.run_path(sys.argv[1])["verify_methods"]("wrong: test")',
                                 str(RUNNER)], capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Frozen 44-method inventory differs', result.stderr)

    def test_method_inventory_rejects_duplicate_missing_and_substituted_tests(self):
        expected = list(MODULE.EXPECTED_METHODS)
        for names in [expected[:-1], expected + [expected[0]], expected[:-1] + ['unreviewed_method']]:
            with self.subTest(names=names[-1]):
                with self.assertRaisesRegex(RuntimeError, '44-method inventory differs'):
                    MODULE.verify_methods('\n'.join(name + ': test' for name in names))

    def test_compiler_failure_retains_exact_selected_closure_and_receipt_then_cleans(self):
        compiler = self.compiler('failing-toolchain', 23)
        sentinel = self.root / 'unrelated-owned-file'
        sentinel.write_text('preserve')
        output = self.root / 'failed-run'
        result = self.cli('--rustc', compiler, '--output', output, optimized=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        receipt = json.loads((output / 'receipt.json').read_text())
        self.assertEqual(receipt['result'], 'failed')
        self.assertFalse(receipt['storedPrefixValidated'])
        self.assertFalse(receipt['fullReplayAccepted'])
        self.assertTrue(receipt['frozen_packets_unchanged'])
        self.assertEqual(receipt['rustc']['path'], str(compiler))
        self.assertEqual(receipt['rustc']['sha256'], MODULE.sha(compiler))
        self.assertEqual(len(receipt['selected_closure']), 38)
        self.assertEqual(len(receipt['historical_sidecars']), 17)
        self.assertEqual(len(list((output / 'inputs/historical').iterdir())), 34)
        for original, row in receipt['selected_closure'].items():
            self.assertEqual(MODULE.sha(output / row['snapshot']), MODULE.sha(MODULE.ROOT / original))
        self.assertEqual((output / 'source/inputs/framing.rs').read_bytes(),
                         (output / 'source/original/analyzer.rs').read_bytes() + b'\n'
                         + (output / 'source/original/private_io_tests.rs').read_bytes())
        command = next(row for row in receipt['commands'] if row['name'] == 'library-compile')
        self.assertEqual(command['exit'], 23)
        self.assertTrue(command['child_returned'])
        self.assertEqual(MODULE.sha(output / command['stderr']['path']), command['stderr']['sha256'])
        self.assertIn('deliberate compiler failure', (output / command['stderr']['path']).read_text())
        self.assertTrue(receipt['cleanup']['removed'])
        self.assertTrue(receipt['cleanup']['children_returned_before_cleanup'])
        self.assertFalse((output / 'scratch').exists())
        self.assertEqual(sentinel.read_text(), 'preserve')
        self.assertFalse((output / 'source' / 'run_review.py').exists())

    def test_timeout_returns_owned_child_and_preserves_partial_logs(self):
        output = self.root / 'timeout'
        output.mkdir()
        receipt = {'commands': []}
        commands = MODULE.Commands(output, receipt)
        marker = self.root / 'descendant-was-not-killed'
        ready = self.root / 'parent-ready'
        descendant_ready = self.root / 'descendant-ready'
        release = self.root / 'release-descendant'
        descendant = '''import sys,time
from pathlib import Path
Path(sys.argv[1]).touch()
until = time.monotonic() + 5
while not Path(sys.argv[2]).exists() and time.monotonic() < until:
    time.sleep(.01)
if Path(sys.argv[2]).exists():
    Path(sys.argv[3]).touch()
'''
        # Deliberately exceed the short command timeout during startup. The test
        # starts that timed wait only after both real children and partial output
        # exist; the production timeout and process-group cleanup stay unchanged.
        parent = '''import subprocess,sys,time
from pathlib import Path
time.sleep(.3)
subprocess.Popen([sys.executable, "-c", %r, *sys.argv[2:]])
until = time.monotonic() + 5
while not Path(sys.argv[2]).exists():
    if time.monotonic() >= until:
        raise RuntimeError("descendant did not become ready")
    time.sleep(.01)
print("started", flush=True)
Path(sys.argv[1]).touch()
time.sleep(10)
''' % descendant
        popen = subprocess.Popen
        timed_waits = []

        def spawn(*args, **kwargs):
            process = popen(*args, **kwargs)
            wait = process.wait
            first_wait = True

            def wait_ready(timeout=None):
                nonlocal first_wait
                if first_wait:
                    first_wait = False
                    until = time.monotonic() + 10
                    while not ready.is_file():
                        if process.poll() is not None or time.monotonic() >= until:
                            self.fail('Owned timeout-control children did not become ready')
                        time.sleep(.01)
                start = time.monotonic()
                try:
                    return wait(timeout=timeout)
                finally:
                    if timeout is not None:
                        timed_waits.append((timeout, time.monotonic() - start))

            process.wait = wait_ready
            return process

        with mock.patch.object(MODULE.subprocess, 'Popen', spawn):
            with self.assertRaisesRegex(RuntimeError, 'Command failed: timeout'):
                commands.run('timeout', [sys.executable, '-c', parent, str(ready),
                             str(descendant_ready), str(release), str(marker)],
                             cwd=output, timeout=0.15)
        row = receipt['commands'][0]
        self.assertTrue(row['timed_out'])
        self.assertTrue(row['child_returned'])
        self.assertIsNone(commands.active)
        self.assertTrue(ready.is_file())
        self.assertTrue(descendant_ready.is_file())
        self.assertEqual(len(timed_waits), 1)
        self.assertEqual(timed_waits[0][0], .15)
        self.assertLess(timed_waits[0][1], 3)
        self.assertLess(row['elapsed_seconds'], 13)
        self.assertIn('started', (output / row['stdout']['path']).read_text())
        release.touch()
        time.sleep(0.7)
        self.assertFalse(marker.exists())

    def test_rustup_shim_resolves_actual_compiler_and_records_both_identities(self):
        compiler = self.compiler('selected-toolchain', 29)
        rustup = self.root / 'rustup'
        rustup.write_text('#!' + sys.executable + '\n'
                          'import os,sys\n'
                          'if os.path.basename(sys.argv[0]) != "rustc": sys.exit(31)\n'
                          'if sys.argv[1:] != ["--print", "sysroot"]: sys.exit(32)\n'
                          'if os.environ.get("RUSTUP_AUTO_INSTALL") != "0": sys.exit(33)\n'
                          'print(' + repr(str(compiler.parent.parent)) + ')\n')
        rustup.chmod(0o755)
        shim = self.root / 'rustc'
        shim.symlink_to(rustup)
        output = self.root / 'shim-run'
        result = self.cli('--rustc', shim, '--output', output)
        self.assertEqual(result.returncode, 1, result.stderr)
        receipt = json.loads((output / 'receipt.json').read_text())
        self.assertEqual(receipt['rustc_launcher']['path'], str(shim))
        self.assertEqual(receipt['rustc_launcher']['resolved_path'], str(rustup))
        self.assertEqual(receipt['rustc']['path'], str(compiler))
        self.assertEqual(receipt['rustc']['sha256'], MODULE.sha(compiler))
        self.assertEqual(next(row['exit'] for row in receipt['commands']
                              if row['name'] == 'library-compile'), 29)
        self.assertTrue(receipt['cleanup']['removed'])

    def test_homebrew_rustup_init_chain_preserves_default_path_dispatch(self):
        compiler = self.compiler('homebrew-selected-toolchain', 37)
        cellar = self.root / 'opt/homebrew/Cellar/rustup/1.29.0/bin'
        cellar.mkdir(parents=True)
        installer = cellar / 'rustup-init'
        installer.write_text('#!' + sys.executable + '\n'
                             'import os,sys\n'
                             'if os.path.basename(sys.argv[0]) == "rustup-init":\n'
                             ' print("rustup-init 1.29.0 (synthetic test fixture)")\n'
                             ' sys.exit(0)\n'
                             'if os.path.basename(sys.argv[0]) != "rustc": sys.exit(41)\n'
                             'if sys.argv[1:] != ["--print", "sysroot"]: sys.exit(42)\n'
                             'if os.environ.get("RUSTUP_AUTO_INSTALL") != "0": sys.exit(43)\n'
                             'print(' + repr(str(compiler.parent.parent)) + ')\n')
        installer.chmod(0o755)
        brew_bin = self.root / 'opt/homebrew/bin'
        brew_bin.mkdir()
        (brew_bin / 'rustc').symlink_to(installer)
        cargo_bin = self.root / 'cargo/bin'
        cargo_bin.mkdir(parents=True)
        shim = cargo_bin / 'rustc'
        shim.symlink_to(brew_bin / 'rustc')
        output = self.root / 'homebrew-default-run'
        result = self.cli('--output', output, optimized=True,
                          env=dict(os.environ, PATH=str(cargo_bin) + os.pathsep + os.environ.get('PATH', '')))
        self.assertEqual(result.returncode, 1, result.stderr)
        receipt = json.loads((output / 'receipt.json').read_text())
        self.assertEqual(receipt['rustc_launcher']['path'], str(shim))
        self.assertEqual(receipt['rustc_launcher']['resolved_path'], str(installer))
        query = next(row for row in receipt['commands'] if row['name'] == 'rustc-sysroot')
        self.assertEqual(query['argv'], [str(shim), '--print', 'sysroot'])
        self.assertEqual(query['environment_overrides']['RUSTUP_AUTO_INSTALL'], '0')
        self.assertEqual(receipt['rustc']['path'], str(compiler))
        self.assertEqual(receipt['rustc']['identity']['host'], 'synthetic-test-host')
        compile_row = next(row for row in receipt['commands'] if row['name'] == 'library-compile')
        self.assertEqual(compile_row['argv'][0], str(compiler))
        self.assertEqual(compile_row['exit'], 37)
        self.assertTrue(receipt['cleanup']['removed'])

    def test_successful_non_rustc_version_cannot_reach_compilation(self):
        compiler = self.compiler('installer-impostor', 0, 'rustup-init 1.29.0 (synthetic fixture)')
        output = self.root / 'not-rustc'
        result = self.cli('--rustc', compiler, '--output', output, optimized=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        receipt = json.loads((output / 'receipt.json').read_text())
        self.assertIn('Compiler version is not a rustc identity', receipt['errors'])
        self.assertNotIn('library-compile', [row['name'] for row in receipt['commands']])
        self.assertFalse(receipt['cleanup']['created'])
        self.assertFalse(receipt['storedPrefixValidated'])
        self.assertFalse(receipt['fullReplayAccepted'])

    def test_verbose_identity_requires_matching_release_binary_and_host(self):
        valid = 'rustc 1.99.0 (fixture)\nbinary: rustc\nhost: synthetic-test-host\nrelease: 1.99.0'
        for invalid in [valid.replace('binary: rustc', 'binary: rustup'),
                        valid.replace('release: 1.99.0', 'release: 1.98.0'),
                        valid.replace('host: synthetic-test-host', 'host: '),
                        valid.replace('1.99.0', '1.future.0')]:
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(RuntimeError, 'identity is incomplete or inconsistent'):
                    MODULE.rustc_identity(invalid)

    def test_cleanup_preserves_failure_inputs_and_removes_only_owned_scratch(self):
        output = self.root / 'retention'
        output.mkdir()
        scratch = output / 'scratch'
        scratch.mkdir()
        marker = {'owner': 'test', 'nonce': 'unique'}
        MODULE.write_json(scratch / 'ownership.json', marker)
        (scratch / 'failed-output').write_bytes(b'partial failed output')
        stamp = scratch.stat()
        sentinel = self.root / 'other-project'
        sentinel.write_bytes(b'preserve')
        receipt = MODULE.preserve_and_cleanup(output, scratch, (stamp.st_dev, stamp.st_ino), marker)
        self.assertTrue(receipt['removed'])
        self.assertFalse(scratch.exists())
        self.assertEqual((output / 'retained/failed-output').read_bytes(), b'partial failed output')
        self.assertEqual(sentinel.read_bytes(), b'preserve')

    def test_cleanup_refuses_changed_ownership_and_links(self):
        output = self.root / 'ownership'
        output.mkdir()
        scratch = output / 'scratch'
        scratch.mkdir()
        marker = {'owner': 'expected'}
        MODULE.write_json(scratch / 'ownership.json', {'owner': 'different'})
        stamp = scratch.stat()
        identity = stamp.st_dev, stamp.st_ino
        with self.assertRaisesRegex(RuntimeError, 'marker changed'):
            MODULE.preserve_and_cleanup(output, scratch, identity, marker)
        self.assertTrue(scratch.exists())
        MODULE.write_json(scratch / 'ownership.json', marker)
        (scratch / 'redirect').symlink_to(self.root / 'other-project')
        with self.assertRaisesRegex(RuntimeError, 'Symlink in scratch'):
            MODULE.preserve_and_cleanup(output, scratch, identity, marker)
        self.assertTrue(scratch.exists())

    def test_failed_sparse_fixture_is_retained_exactly_without_large_raw_artifact(self):
        output = self.root / 'sparse-failure'
        output.mkdir()
        scratch = output / 'scratch'
        scratch.mkdir()
        marker = {'owner': 'sparse-test'}
        MODULE.write_json(scratch / 'ownership.json', marker)
        source = scratch / 'oversized-stream'
        with source.open('wb') as stream:
            stream.write(b'fixture-prefix')
            stream.truncate(17 * 1024 * 1024)
        original = MODULE.sha(source)
        stamp = scratch.stat()
        receipt = MODULE.preserve_and_cleanup(output, scratch, (stamp.st_dev, stamp.st_ino), marker)
        self.assertFalse(scratch.exists())
        row = receipt['retained_test_files']['oversized-stream']
        self.assertEqual(row['encoding'], 'gzip')
        self.assertLess(row['bytes'], 65536)
        digest = hashlib.sha256()
        with gzip.open(output / row['path'], 'rb') as stream:
            for block in iter(lambda: stream.read(65536), b''):
                digest.update(block)
        self.assertEqual(digest.hexdigest(), original)
        self.assertEqual(row['uncompressed_sha256'], original)


if __name__ == '__main__':
    unittest.main()
