#!/usr/bin/env python3
"""Guarded targeted controls for the sibling evidence-only correction."""
import unittest.mock
import offline
offline.install()
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock
import admit as a
import bounded_commands as b

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / 'swift-pin-bitmap-lint-independent-admission'


def passed_text():
    names = list(a.ORACLES) + ['fixture_' + str(i) for i in range(690)]
    return ''.join('test ' + n + ' ... ok\n' for n in names) + 'test result: ok. 699 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1s\n'


class Controls(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix='pure-', dir=HERE))

    def tearDown(self):
        for p in sorted(self.work.rglob('*'), key=lambda x: len(x.parts), reverse=True):
            if p.is_symlink() or p.is_file(): p.unlink()
            else: p.rmdir()
        self.work.rmdir()

    def fixture(self):
        source = self.work / 'source'; source.mkdir()
        raw = {n: ('fn fixture() {} // ' + n + '\n').encode() for n in a.OVERLAYS}
        raw['Cargo.toml'] = b'[package]\n'
        for n, value in raw.items():
            p = source / n; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(value)
        before = {n: a.file_row(value) for n, value in raw.items()}
        out = self.work / 'out'; out.mkdir()
        return source, raw, before, out

    def record(self, out):
        return json.loads((out / 'format/candidate/receipt.json').read_text())

    def assert_originals(self, raw, out):
        for name in a.OVERLAYS:
            self.assertEqual((out / 'format/candidate/before' / name).read_bytes(), raw[name])

    def test_guard_before_import_and_no_live_calls(self):
        self.assertIs(b.subprocess.Popen, offline.denied)
        self.assertIs(b.os.waitpid, offline.denied)
        self.assertIs(b.os.setsid, offline.denied)
        self.assertIs(b.os.killpg, offline.denied)
        self.assertIs(a.signal.setitimer, offline.denied)
        self.assertIs(b.resource.getrusage, offline.denied)
        self.assertEqual(offline.ATTEMPTS, [])

    def test_only_two_functions_and_one_small_roster_helper_change(self):
        old = ast.parse((FROZEN / 'admit.py').read_text())
        rebound = (HERE / 'admit.py').read_text()
        bindings = json.loads((HERE / 'source-basis.json').read_text())['admitReplacements']
        for binding in bindings:
            self.assertEqual(rebound.count(binding['after']), binding['count'])
            rebound = rebound.replace(binding['after'], binding['before'], binding['count'])
        self.assertEqual(rebound, (HERE.parent / 'swift-pin-bitmap-lint-host-evidence-correction' / 'admit.py').read_text())
        new = ast.parse(rebound)
        def nodes(tree):
            return {n.name: ast.dump(n, include_attributes=False) for n in tree.body if isinstance(n, ast.FunctionDef)}
        before, after = nodes(old), nodes(new)
        self.assertEqual(set(after) - set(before), {'format_roster'})
        self.assertEqual(set(before) - set(after), set())
        self.assertEqual({n for n in before if before[n] != after[n]}, {'test_evidence', 'format_evidence'})
        self.assertEqual([ast.dump(n, include_attributes=False) for n in old.body if not isinstance(n, ast.FunctionDef)],
                         [ast.dump(n, include_attributes=False) for n in new.body if not isinstance(n, ast.FunctionDef)])
        for n in ('bounded_commands.py', 'offline.py'):
            self.assertEqual((HERE / n).read_bytes(), (FROZEN / n).read_bytes())

    def test_real_source_admission_and_exact_six_vectors_remain(self):
        manifest, data = a.inputs()
        self.assertEqual((len(data), len(a.OVERLAYS), a.CANDIDATE), (136, 15, 'e9282e05cea70d4aceaf6a145fb9f971acb023dd41a7d4651216753666305ba1'))
        self.assertEqual(a.closure(manifest['candidateFiles']), a.CANDIDATE)
        paths = {n: Path('$RUNNER_TEMP/pin-bitmap-lint-regression-v1-evidence/scratch') / n for n in ('source', 'target', 'cargo', 'home', 'nodebin')}
        toolbin = Path('$RUSTUP_HOME/toolchains') / a.TOOLCHAIN / 'bin'
        config = Path('$RUNNER_TEMP/pin-bitmap-lint-regression-v1-evidence/scratch/rustfmt.toml')
        actual = json.loads(json.dumps(a.command_plan(paths, toolbin, config, {'path': '$NODE_REALPATH'})))
        expected = json.loads((FROZEN / 'command-plan.json').read_text())
        self.assertEqual(actual, expected['commands'])
        self.assertEqual((a.ACTIVE_SECONDS, a.CLEANUP_SECONDS, b.MAX_COMMANDS, b.OUTPUT_CAP, b.AGGREGATE_OUTPUT_CAP),
                         (1800, 60, 6, 8388608, 33554432))

    def test_accepts_complete_test_output_and_zero_test_summaries(self):
        text = passed_text() + 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
        self.assertEqual(a.test_evidence(text)['passed'], 699)

    def test_rejects_every_contradictory_and_malformed_summary(self):
        for suffix in (
            'test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1s\n',
            'test result: FAILED. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1s\n',
            'test result: ok. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1s\n',
            'test result: ok. 0 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out; finished in 1s\n',
            'test result: unknown. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;\n',
            'test result: FAILED\n',
            '  test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1s\n',
            'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; forged suffix\n',
        ):
            with self.subTest(suffix=suffix):
                with self.assertRaises(RuntimeError): a.test_evidence(passed_text() + suffix)

    def test_existing_missing_duplicate_ignored_oracles_still_refuse(self):
        for text in (
            passed_text().replace(a.ORACLES[0], a.ORACLES[1]),
            passed_text().replace(' ... ok', ' ... ignored', 1),
            passed_text().replace('699 passed', '698 passed'),
            passed_text().replace('0 filtered out', '1 filtered out'),
        ):
            with self.assertRaises(RuntimeError): a.test_evidence(text)

    def test_stable_roster_retains_all_exact_before_and_after_and_manifest(self):
        source, raw, before, out = self.fixture()
        name = a.OVERLAYS[0]; (source / name).write_text('changed formatter output\n')
        after, record = a.format_evidence(out, 'candidate', source, before, raw)
        self.assertTrue(record['verified']); self.assertEqual(record['changedPaths'], [name])
        self.assertEqual(record['afterTreeSHA256'], a.closure(after))
        self.assert_originals(raw, out)
        for n in a.OVERLAYS:
            self.assertEqual((out / 'format/candidate/after' / n).read_bytes(), (source / n).read_bytes())

    def test_unexpected_file_is_recorded_without_reading_and_retains_fifteen(self):
        source, raw, before, out = self.fixture(); extra = source / 'unexpected.rs'; extra.write_text('do not read\n')
        original = Path.open
        def opened(path, *args, **kwargs):
            self.assertNotEqual(path, extra)
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'open', opened):
            with self.assertRaisesRegex(RuntimeError, 'roster changed'): a.format_evidence(out, 'candidate', source, before, raw)
        record = self.record(out); self.assertFalse(record['verified'])
        self.assertEqual(record['roster']['unexpectedPaths'], ['unexpected.rs'])
        self.assertIsNone(record['afterTreeSHA256']); self.assertEqual(record['availableExpectedMembers'], len(before))
        self.assert_originals(raw, out)
        self.assertTrue(all(record['files'][n]['afterAvailable'] for n in a.OVERLAYS))

    def test_unexpected_directory_is_never_descended_or_read(self):
        source, raw, before, out = self.fixture(); extra = source / 'unexpected'; extra.mkdir(); (extra / 'secret').write_text('do not read')
        original = os.scandir; visited = []
        def scanned(path):
            visited.append(Path(path)); self.assertNotEqual(Path(path), extra)
            return original(path)
        with mock.patch.object(os, 'scandir', scanned):
            with self.assertRaisesRegex(RuntimeError, 'roster changed'): a.format_evidence(out, 'candidate', source, before, raw)
        self.assertEqual(self.record(out)['roster']['unexpectedPaths'], ['unexpected'])
        self.assertNotIn(extra, visited); self.assert_originals(raw, out)

    def test_missing_overlay_retains_originals_and_fourteen_available_after_files(self):
        source, raw, before, out = self.fixture(); missing = a.OVERLAYS[0]; (source / missing).unlink()
        with self.assertRaisesRegex(RuntimeError, 'roster changed'): a.format_evidence(out, 'candidate', source, before, raw)
        record = self.record(out); self.assertEqual(record['roster']['missingPaths'], [missing]); self.assert_originals(raw, out)
        self.assertFalse(record['files'][missing]['afterAvailable'])
        self.assertEqual(sum(row['afterAvailable'] for row in record['files'].values()), 14)
        self.assertTrue((out / 'format/candidate/format.diff').exists())

    def test_expected_file_symlink_is_not_followed_or_read(self):
        source, raw, before, out = self.fixture(); n = a.OVERLAYS[0]; target = self.work / 'external'; target.write_text('do not read')
        (source / n).unlink(); (source / n).symlink_to(target)
        original = Path.open
        def opened(path, *args, **kwargs):
            self.assertNotEqual(path, target); self.assertNotEqual(path, source / n)
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'open', opened):
            with self.assertRaisesRegex(RuntimeError, 'roster changed'): a.format_evidence(out, 'candidate', source, before, raw)
        record = self.record(out); self.assertEqual(record['roster']['unsafePaths'], [n]); self.assert_originals(raw, out)

    def test_expected_directory_symlink_is_not_followed(self):
        source, raw, before, out = self.fixture(); directory = source / 'src/experimental'; moved = self.work / 'moved'; directory.rename(moved); directory.symlink_to(moved)
        original = os.scandir
        def scanned(path):
            self.assertNotEqual(Path(path), directory); self.assertNotEqual(Path(path), moved)
            return original(path)
        with mock.patch.object(os, 'scandir', scanned):
            with self.assertRaisesRegex(RuntimeError, 'roster changed'): a.format_evidence(out, 'candidate', source, before, raw)
        record = self.record(out); self.assertEqual(record['roster']['unsafePaths'], ['src/experimental']); self.assert_originals(raw, out)

    def test_unreadable_expected_after_retains_original_and_other_safe_after_files(self):
        source, raw, before, out = self.fixture(); n = a.OVERLAYS[0]; original = Path.read_bytes
        def read(path):
            if path == source / n: raise PermissionError('independent unreadable expected file')
            return original(path)
        with mock.patch.object(Path, 'read_bytes', read):
            with self.assertRaisesRegex(RuntimeError, 'expected source unavailable'): a.format_evidence(out, 'candidate', source, before, raw)
        record = self.record(out); self.assertEqual(record['expectedReadErrors'][0]['path'], n); self.assert_originals(raw, out)
        self.assertEqual(sum(row['afterAvailable'] for row in record['files'].values()), 14)

    def test_missing_source_root_retains_originals_and_explicit_roster_error(self):
        source, raw, before, out = self.fixture(); source.rename(self.work / 'moved-source')
        with self.assertRaisesRegex(RuntimeError, 'roster changed'): a.format_evidence(out, 'candidate', source, before, raw)
        record = self.record(out); self.assertTrue(record['roster']['errors']); self.assertEqual(len(record['roster']['missingPaths']), len(before)); self.assert_originals(raw, out)

    def test_invalid_utf8_retains_exact_after_bytes_and_diff(self):
        source, raw, before, out = self.fixture(); n = a.OVERLAYS[0]; (source / n).write_bytes(b'\xff\x00\n')
        with self.assertRaisesRegex(RuntimeError, 'not UTF-8'): a.format_evidence(out, 'candidate', source, before, raw)
        record = self.record(out)
        self.assertEqual((out / 'format/candidate/after' / n).read_bytes(), b'\xff\x00\n')
        self.assertEqual(record['files'][n]['after'], a.file_row(b'\xff\x00\n')); self.assertTrue((out / 'format/candidate/format.diff').read_text())
        self.assertFalse(record['verified']); self.assertEqual(record['diffDecodingErrors'][0]['path'], n)

    def test_outside_overlay_change_still_refuses_and_retains_fifteen(self):
        source, raw, before, out = self.fixture(); (source / 'Cargo.toml').write_text('unexpected change')
        with self.assertRaisesRegex(RuntimeError, 'outside the fifteen'): a.format_evidence(out, 'candidate', source, before, raw)
        record = self.record(out); self.assertEqual(record['outsideOverlayChanges'], ['Cargo.toml']); self.assertFalse(record['verified']); self.assert_originals(raw, out)


if __name__ == '__main__':
    stream = io.StringIO(); result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    (HERE / 'test-output.txt').write_text(stream.getvalue()); sys.stderr.write(stream.getvalue())
    record = {'schema': 1, 'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped),
              'pythonVersion': sys.version, 'guardBeforeSubjectImports': True, 'liveApiAttempts': offline.ATTEMPTS,
              'realNestedProcessSessionGroupSignalTimerWaitSocketCalls': 0, 'RustNodeSwiftElixirCompilerProductRuntimeRuns': 0,
              'producerPacketsWritten': False, 'scratchRemaining': [p.name for p in HERE.glob('pure-*')]}
    (HERE / 'controls-result.json').write_text(json.dumps(record, sort_keys=True, indent=2) + '\n')
    if not result.wasSuccessful(): raise SystemExit(1)
