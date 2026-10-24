#!/usr/bin/env python3
"""Controlled host file/process tests. No native SDK executable or target is used."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cleanup_runner', HERE / 'run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
EVIDENCE = None
RESULTS = []


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


class ExtractionGuards(unittest.TestCase):
    def setUp(self):
        self.out = EVIDENCE / self._testMethodName
        self.out.mkdir()
        self.work = self.out / '.build'
        self.work.mkdir()
        identity = self.work.stat()
        self.ownership = (identity.st_dev, identity.st_ino)
        self.fixture = self.work / 'fixture.bin'
        self.fixture.write_bytes(b'controlled runtime cleanup host fixture')
        self.expected = {'fixture.bin': {}}

    def remove(self):
        result = runner.remove_owned_extraction(self.work, self.out, self.expected, self.ownership)
        self.assertEqual(result['status'], 'removed')
        self.assertFalse(self.work.exists())
        return result

    def refused(self, fragment):
        with self.assertRaises(runner.ExtractionCleanupRefused) as caught:
            runner.remove_owned_extraction(self.work, self.out, self.expected, self.ownership)
        self.assertIn(fragment, str(caught.exception))
        self.assertTrue(self.work.exists() or self.work.is_symlink())
        save(self.out / 'refusal.json', caught.exception.cleanup)
        return caught.exception

    def tearDown(self):
        # Tests explicitly restore the failed condition before this same owned cleanup.
        self.assertFalse(self.work.exists() or self.work.is_symlink(), 'owned host extraction leaked')
        RESULTS.append({'case': self._testMethodName, 'finalOwnedExtractionAbsent': True})

    def test_success_retains_evidence(self):
        evidence = self.out / 'retained.log'
        evidence.write_text('retained runtime evidence\n')
        save(self.out / 'cleanup.json', self.remove())
        self.assertEqual(evidence.read_text(), 'retained runtime evidence\n')

    def test_operation_failure_runs_finally(self):
        with self.assertRaisesRegex(RuntimeError, 'controlled operation failure'):
            try:
                raise RuntimeError('controlled operation failure')
            finally:
                save(self.out / 'cleanup.json', self.remove())

    def test_open_holder_refused_then_recovered(self):
        with self.fixture.open('rb'):
            error = self.refused('open holder')
            holder_log = self.out / error.cleanup['openHoldersCheck']['output']
            self.assertIn(str(self.fixture), holder_log.read_text())
            (self.out / 'extraction-open-holders.log').rename(self.out / 'refused-open-holders.log')
        save(self.out / 'cleanup.json', self.remove())

    def test_nested_symlink_refused_then_recovered(self):
        outside = self.out / 'retained-outside.bin'
        outside.write_bytes(b'preserved external bytes')
        link = self.work / 'substituted-link'
        link.symlink_to(outside)
        self.refused('symlink')
        self.assertEqual(outside.read_bytes(), b'preserved external bytes')
        link.unlink()
        save(self.out / 'cleanup.json', self.remove())

    def test_root_symlink_refused_then_recovered(self):
        parked = self.out / 'parked-owned-directory'
        self.work.rename(parked)
        self.work.symlink_to(parked, target_is_directory=True)
        self.refused('unexpected extraction path')
        self.assertTrue((parked / 'fixture.bin').is_file())
        self.work.unlink()
        parked.rename(self.work)
        save(self.out / 'cleanup.json', self.remove())

    def test_replaced_directory_refused_then_recovered(self):
        parked = self.out / 'parked-owned-directory'
        self.work.rename(parked)
        self.work.mkdir()
        self.refused('substituted extraction directory')
        self.work.rmdir()
        parked.rename(self.work)
        save(self.out / 'cleanup.json', self.remove())

    def test_wrong_path_refused_then_recovered(self):
        wrong = self.out / 'not-the-owned-extraction'
        self.work.rename(wrong)
        original = self.work
        self.work = wrong
        self.refused('unexpected extraction path')
        wrong.rename(original)
        self.work = original
        save(self.out / 'cleanup.json', self.remove())

    def test_parent_symlink_refused_then_recovered(self):
        alias = self.out / 'alias'
        alias.symlink_to(self.out, target_is_directory=True)
        with self.assertRaisesRegex(runner.ExtractionCleanupRefused, 'unexpected extraction path'):
            runner.remove_owned_extraction(alias / '.build', alias, self.expected, self.ownership)
        self.assertTrue(self.fixture.is_file())
        alias.unlink()
        save(self.out / 'cleanup.json', self.remove())

    def test_unexpected_file_refused_then_recovered(self):
        extra = self.work / 'unsealed.bin'
        extra.write_bytes(b'unsealed')
        self.refused('unexpected files')
        extra.unlink()
        save(self.out / 'cleanup.json', self.remove())

    def test_unexpected_empty_directory_refused_then_recovered(self):
        extra = self.work / 'unsealed-directory'
        extra.mkdir()
        self.refused('unexpected directory')
        extra.rmdir()
        save(self.out / 'cleanup.json', self.remove())

    def test_special_file_refused_then_recovered(self):
        fifo = self.work / 'fixture.fifo'
        os.mkfifo(fifo)
        self.refused('special file')
        fifo.unlink()
        save(self.out / 'cleanup.json', self.remove())

    def test_unknown_ownership_refused_then_recovered(self):
        ownership = self.ownership
        self.ownership = None
        self.refused('substituted extraction directory')
        self.ownership = ownership
        save(self.out / 'cleanup.json', self.remove())

    def test_unavailable_holder_check_refused_then_recovered(self):
        unavailable = SimpleNamespace(returncode=2, stdout=b'controlled lsof unavailable\n', groupCleanup={})
        with patch.object(runner, 'execute', return_value=unavailable):
            self.refused('unavailable open-holder check')
        (self.out / 'extraction-open-holders.log').rename(self.out / 'refused-unavailable-check.log')
        save(self.out / 'cleanup.json', self.remove())

    def test_partial_expected_extraction_is_removed(self):
        self.expected['not-yet-extracted/other.bin'] = {}
        (self.work / 'not-yet-extracted').mkdir()
        save(self.out / 'cleanup.json', self.remove())

    def test_already_absent_is_not_created(self):
        save(self.out / 'cleanup.json', self.remove())
        result = runner.remove_owned_extraction(self.work, self.out, self.expected, self.ownership)
        self.assertEqual(result['status'], 'not-created')
        save(self.out / 'repeat-cleanup.json', result)

    def test_post_holder_check_substitution_refused_then_recovered(self):
        real_execute = runner.execute
        extra = self.work / 'late-unsealed.bin'
        def substitute_after_check(*args, **kwargs):
            checked = real_execute(*args, **kwargs)
            extra.write_bytes(b'controlled substitution after holder check')
            return checked
        with patch.object(runner, 'execute', side_effect=substitute_after_check):
            self.refused('unexpected files')
        extra.unlink()
        save(self.out / 'cleanup.json', self.remove())


class MainGuards(unittest.TestCase):
    def test_source_binding_and_original_emulator_guards_preserved(self):
        metadata = runner.bind_candidate(runner.BUILDS / 'candidate-2')
        self.assertEqual(metadata['sourceClosureSHA256'], runner.SOURCE_CLOSURE_SHA256)
        original = (runner.BUILDS / 'run.py').read_text()
        corrected = (HERE / 'run.py').read_text()
        def function(source, name):
            return ast.dump(next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name))
        for name in ['owned_identity', 'validate_members', 'validate_target']:
            self.assertEqual(function(original, name), function(corrected, name))
        def emulator_cleanup(source):
            return source.split('    finally:\n        if process is not None:', 1)[1].split('        if cleanup_errors:', 1)[0]
        self.assertEqual(emulator_cleanup(original), emulator_cleanup(corrected).split('        extraction_failure = None', 1)[0])
        self.assertEqual(runner.sha(HERE / 'owned_process.py'), runner.PROCESS_HELPER_SHA256)
        save(EVIDENCE / 'preserved-contracts.json', {'status': 'passed', 'candidateInputs': 105,
             'originalRunnerSHA256': runner.sha(runner.BUILDS / 'run.py'),
             'unchangedFunctions': ['owned_identity', 'validate_members', 'validate_target'],
             'originalEmulatorCleanupBlockByteIdentical': True,
             'ownedProcessHelperByteIdentical': True})

    def test_cli_rejects_without_native_dispatch_or_unbound_candidate(self):
        for suffix in [[], ['--execute-native', '--build', 'candidate-3'],
                       ['--execute-native', '--attempt', '../outside']]:
            argv = [sys.executable, '-B', str(HERE / 'run.py'), '--build', 'candidate-2', '--attempt', 'runtime-987654'] + suffix
            completed = subprocess.run(argv, cwd=runner.ROOT, capture_output=True)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse((HERE / 'runtime-987654').exists())
            name = 'dispatch' if not suffix else ('build' if '--build' in suffix else 'path')
            (EVIDENCE / ('cli-refusal-' + name + '.log')).write_bytes(completed.stdout + completed.stderr)

    def run_main_failure(self, cleanup_unavailable):
        # Tiny synthetic archive is a controlled host fixture, never a candidate/APK qualification.
        out = EVIDENCE / ('main-failure-cleanup-unavailable' if cleanup_unavailable else 'main-failure-cleanup-success')
        out.mkdir()
        shutil.copy2(HERE / 'owned_process.py', out / 'owned_process.py')
        built = out / 'fixture-builds/candidate-2'
        built.mkdir(parents=True)
        payload = b'host synthetic extraction only; no executable APK'
        archive = built / 'built-artifacts.tar.gz'
        with tarfile.open(archive, 'w:gz') as target:
            member = tarfile.TarInfo('coordinator-join.apk')
            member.size = len(payload)
            target.addfile(member, io.BytesIO(payload))
        metadata = {'status': 'actual-private-apk-built-runtime-NOT-RUN', 'sourceUnchanged': True,
            'builtArchiveSHA256': runner.sha(archive), 'apkSHA256': hashlib.sha256(payload).hexdigest(),
            'descriptorSHA256': 'controlled-host-fixture', 'sourceRevision': 'controlled-host-fixture',
            'sourceClosureSHA256': 'controlled-host-fixture', 'debugCertificateSHA256': 'controlled-host-fixture'}
        save(built / 'receipt.json', metadata)
        save(built / 'source-lock.json', {'fixture': True})
        save(built / 'built-artifacts.json', {'coordinator-join.apk': {'sha256': metadata['apkSHA256']}})
        session = built / 'inputs/verification/android-native-appearance-v2/emulator-session.json'
        session.parent.mkdir(parents=True)
        save(session, {'argv': ['controlled-invalid-contract-before-any-native-command'], 'serial': 'host-fixture'})
        real_execute = runner.execute
        calls = []
        def host_only(argv, **kwargs):
            calls.append(list(map(str, argv)))
            self.assertEqual(str(argv[0]), '/usr/sbin/lsof', 'native/other command blocked by host test')
            self.assertEqual(argv[1:3], ['-nP', '+D'])
            if cleanup_unavailable:
                return SimpleNamespace(returncode=2, stdout=b'controlled lsof unavailable\n', groupCleanup={})
            return real_execute(argv, **kwargs)
        def forbidden_native_start(*args, **kwargs):
            self.fail('native process start blocked by host test')
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(runner, 'HERE', out))
            stack.enter_context(patch.object(runner, 'BUILDS', out / 'fixture-builds'))
            stack.enter_context(patch.object(runner, 'bind_candidate', return_value=metadata))
            stack.enter_context(patch.object(runner, 'execute', side_effect=host_only))
            stack.enter_context(patch.object(runner, 'subprocess', SimpleNamespace(Popen=forbidden_native_start, TimeoutExpired=subprocess.TimeoutExpired)))
            stack.enter_context(patch.object(sys, 'argv', ['host-main-fixture', '--build', 'candidate-2', '--attempt', 'runtime-1', '--execute-native']))
            expected_error = 'owned extraction cleanup failed' if cleanup_unavailable else 'bounded owned-instance contract changed'
            with self.assertRaisesRegex(RuntimeError if cleanup_unavailable else ValueError, expected_error):
                runner.main()
        attempt = out / 'runtime-1'
        receipt = json.loads((attempt / 'receipt.json').read_text())
        self.assertEqual(receipt['cleanup'], 'not-started')
        self.assertEqual(receipt['commands'], [])
        self.assertIn('bounded owned-instance contract changed', receipt['failure'])
        self.assertEqual(len(calls), 1)
        seal = json.loads((attempt / 'artifact-seal.json').read_text())
        self.assertIn('receipt.json', seal)
        self.assertTrue(all('.build' not in Path(name).parts for name in seal))
        for relative, expected in seal.items():
            self.assertEqual(runner.sha(attempt / relative), expected['sha256'])
        if cleanup_unavailable:
            self.assertEqual(receipt['status'], 'failed-owned-extraction-cleanup')
            self.assertTrue((attempt / '.build').is_dir())
            identity = (attempt / '.build').stat()
            result = runner.remove_owned_extraction(attempt / '.build', attempt,
                {'coordinator-join.apk': {}}, (identity.st_dev, identity.st_ino))
            save(out / 'recovery-cleanup.json', result)
        else:
            self.assertEqual(receipt['status'], 'failed-native-attempt-retained')
            self.assertEqual(receipt['extractionCleanup']['status'], 'removed')
        self.assertFalse((attempt / '.build').exists())
        save(out / 'host-scope.json', {'nativeRuntime': 'NOT RUN', 'nativeCommandsExecuted': 0,
             'nativeTargetsDiscovered': 0, 'controlledSyntheticBuildFixture': True,
             'actualMainFinallyExecuted': True, 'allOwnedExtractionsAbsentAfterSafetyRestored': True,
             'actualHostCommands': calls})

    def test_main_failure_after_extraction_cleans_and_retains_receipt(self):
        self.run_main_failure(False)

    def test_main_cleanup_failure_retains_then_recovers_extraction(self):
        self.run_main_failure(True)


if __name__ == '__main__':
    if len(sys.argv) != 2 or not sys.argv[1].startswith('host-tests-') or not sys.argv[1][11:].isdigit():
        raise SystemExit('usage: python3 -B test_cleanup.py host-tests-N (fresh directory)')
    EVIDENCE = HERE / sys.argv.pop()
    EVIDENCE.mkdir()
    program = unittest.main(verbosity=2, exit=False)
    # unittest's exit=False requires explicit status propagation for the collector.
    failed = any(path.name == '.build' for path in EVIDENCE.rglob('*'))
    save(EVIDENCE / 'unittest-result.json', {'status': 'passed' if program.result.wasSuccessful() and not failed else 'failed',
         'testsRun': program.result.testsRun, 'failures': len(program.result.failures),
         'errors': len(program.result.errors), 'nativeRuntime': 'NOT RUN',
         'nativeCommandsExecuted': 0, 'nativeInstancesStarted': 0, 'physicalTargetsQueried': False})
    save(EVIDENCE / 'fixture-cleanup-ledger.json', {'cases': RESULTS, 'remainingOwnedExtractions': failed,
         'scope': 'controlled host files/processes only; no native SDK command, discovery, UI or capture'})
    raise SystemExit(1 if failed or not program.result.wasSuccessful() else 0)
