"""Real filesystem controls for optional Android inspection progress."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
PRIVATE = (HERE / 'after').is_dir()
ROOT = HERE / 'after' if PRIVATE else HERE.parents[1]
OWNER = ROOT / 'cli/Sources/MixerBuild/Resources/android-build.py'
REFERENCE = (HERE / 'before/cli/Sources/MixerBuild/Resources/android-build.py' if PRIVATE else
             ROOT / 'scripts/ci/tests/android_inspection_digests/preimage-android-build.py')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReadMeter:
    def __init__(self, module, before_read=None):
        self.module, self.before_read = module, before_read
        self.bytes = 0
        self.reads = 0
        self.original = module.os.fdopen

    def open(self, *args, **kwargs):
        stream, meter = self.original(*args, **kwargs), self

        class Stream:
            def __enter__(self):
                stream.__enter__()
                return self

            def __exit__(self, *exc):
                return stream.__exit__(*exc)

            def read(self, size):
                meter.reads += 1
                if meter.before_read:
                    meter.before_read(meter.reads)
                data = stream.read(size)
                meter.bytes += len(data)
                return data

        return Stream()


class InspectionProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='r4868-pure-', dir=os.environ['TMPDIR'])
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dist = self.root / 'dist'
        self.trace = self.root / 'trace'
        self.dist.mkdir()
        self.trace.mkdir(mode=0o700)
        self.m = load('actual_progress_owner', OWNER)
        self.reference = load('unchanged_progress_reference', REFERENCE)
        self.m.ENV['MIXER_ANDROID_INSPECTION_PHASE_DIR'] = str(self.trace)
        self.m.SWIFT = self.root / 'toolchain/usr/bin/swift'
        self.m.ART = self.root / 'sdk/bundle'
        self.m.BT = self.root / 'tools'
        self.m.JDK = self.root / 'jdk'
        self.m.JAR = self.root / 'platform/android.jar'
        self.initial_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
        self.assertEqual(signal.getsignal(signal.SIGALRM), signal.SIG_DFL)

    def tearDown(self):
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
        self.assertEqual(signal.getsignal(signal.SIGALRM), signal.SIG_DFL)
        self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, set()), self.initial_mask)
        self.assertNotIn(signal.SIGALRM, signal.sigpending())

    def fixture(self):
        (self.dist / 'a').write_bytes(b'a' * (1024 * 1024 + 7))
        os.link(self.dist / 'a', self.dist / 'b')
        (self.dist / 'link').symlink_to('a')
        (self.dist / 'sub').mkdir()
        (self.dist / 'sub/c').write_bytes(b'xyz')

    def rows(self, progress=True):
        files = list(self.trace.glob('inspection-progress-*.jsonl')) if progress else [
            p for p in self.trace.glob('inspection-*.jsonl') if not p.name.startswith('inspection-progress-')]
        return [json.loads(line) for p in files for line in p.read_text().splitlines()]

    def run_tree(self, digest=None):
        digest = digest or self.m.InspectionDigests()
        phases = self.m.InspectionPhases()
        try:
            return phases.run('distribution.hash.swift_toolchain', self.m.tree, self.dist, digest)
        finally:
            phases.close()

    def test_digest_bytes_and_actual_counters(self):
        self.fixture()
        expected = self.reference.tree(self.dist, self.reference.InspectionDigests()) if hasattr(
            self.reference, 'InspectionDigests') else self.reference.tree(self.dist)
        meter = ReadMeter(self.m)
        with patch.object(self.m.os, 'fdopen', meter.open):
            actual = self.run_tree()
        self.assertEqual(actual, expected)
        self.assertEqual(meter.bytes, 1024 * 1024 + 10)
        row = self.rows()[-1]
        self.assertEqual(row['state'], 'end')
        c = row['hash_progress']
        self.assertEqual(c['read_bytes'], meter.bytes)
        self.assertEqual(c['read_calls'], meter.reads)
        self.assertEqual([c[k] for k in ('file_open_calls', 'files_completed', 'directories',
            'entries_completed', 'stat_calls', 'fstat_calls', 'cache_lookups', 'cache_hits')],
            [4, 4, 2, 4, 8, 8, 4, 2])
        self.assertGreater(c['process_cpu_ns'], 0)
        self.assertGreater(c['wall_ns'], 0)
        for k in ('utime', 'stime', 'minflt', 'majflt', 'inblock', 'oublock'):
            self.assertGreaterEqual(c[k], 0)
        text = ''.join(p.read_text() for p in self.trace.iterdir())
        self.assertNotIn(str(self.dist), text)
        self.assertNotIn('cache_miss', text)
        self.assertEqual([(r['phase'], r['state']) for r in self.rows(False)], [
            ('distribution.hash.swift_toolchain', 'begin'), ('distribution.hash.swift_toolchain', 'end')])
        self.assertEqual(set(self.rows(False)[0]), {'phase', 'state', 'monotonic_ns'})

    def test_real_same_inspection_cache_seed(self):
        self.fixture()
        digest = self.m.InspectionDigests()
        digest(self.dist / 'a')
        self.run_tree(digest)
        c = self.rows()[-1]['hash_progress']
        self.assertEqual(c['read_bytes'], 3)
        self.assertEqual(c['cache_hits'], 3)
        self.assertEqual(c['cache_lookups'], 4)

    def test_real_blocked_read_persists_predeadline_snapshot(self):
        (self.dist / 'a').write_bytes(b'abc')
        rd, wr = os.pipe()
        partial = []
        original_report = self.m.InspectionProgress.report

        def read_gate():
            return os.read(rd, 1)

        def report(progress, signum, frame):
            self.assertIs(frame.f_code, read_gate.__code__)
            original_report(progress, signum, frame)
            try:
                partial.extend(self.rows())
            finally:
                os.write(wr, b'G')

        def blocked(count):
            if count == 1:
                handler = signal.getsignal(signal.SIGALRM)
                self.assertIs(getattr(handler, '__func__', None), report)
                self.assertNotIn(signal.SIGALRM, signal.pthread_sigmask(signal.SIG_BLOCK, set()))
                # The one-shot alarm cannot reenter the snapshot while the pipe is blocked.
                signal.setitimer(signal.ITIMER_REAL, .05)
                self.assertEqual(read_gate(), b'G')

        meter = ReadMeter(self.m, blocked)
        try:
            with patch.object(self.m.InspectionProgress, 'INTERVAL_SECONDS', 60), \
                    patch.object(self.m.InspectionProgress, 'report', report), \
                    patch.object(self.m.os, 'fdopen', meter.open):
                self.run_tree()
        finally:
            os.close(rd)
            os.close(wr)
        self.assertEqual([r['state'] for r in partial], ['begin', 'progress'])
        rows = self.rows()
        self.assertEqual([r['state'] for r in rows], ['begin', 'progress', 'end'])
        self.assertEqual(rows[:2], partial)
        self.assertLess(rows[0]['monotonic_ns'], rows[1]['monotonic_ns'])
        self.assertLess(rows[1]['monotonic_ns'], rows[2]['monotonic_ns'])
        counters = ('operation', 'read_bytes', 'read_calls', 'file_open_calls', 'files_completed',
                    'directories', 'entries_completed', 'stat_calls', 'fstat_calls', 'cache_lookups',
                    'cache_hits')
        self.assertEqual([tuple(row['hash_progress'][key] for key in counters) for row in rows], [
            ('start', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            ('read', 0, 1, 1, 0, 1, 0, 1, 1, 1, 0),
            ('file_complete', 3, 2, 1, 1, 1, 1, 2, 2, 1, 0),
        ])
        self.assertGreaterEqual(partial[-1]['hash_progress']['wall_ns'], 45_000_000)
        self.assertEqual((meter.reads, meter.bytes), (2, 3))

    def test_error_partial_counters_and_original_exception(self):
        self.fixture()
        primary = TimeoutError('controlled inspection deadline')

        def fail(count):
            if count == 2:
                raise primary

        meter = ReadMeter(self.m, fail)
        with patch.object(self.m.os, 'fdopen', meter.open):
            with self.assertRaises(TimeoutError) as caught:
                self.run_tree()
        self.assertIs(caught.exception, primary)
        row = self.rows()[-1]
        self.assertEqual(row['state'], 'error')
        self.assertEqual(row['hash_progress']['read_bytes'], 1024 * 1024)
        self.assertEqual(row['hash_progress']['files_completed'], 0)
        self.assertEqual(self.rows(False)[-1]['state'], 'error')

    def test_diagnostic_publication_failure_preserves_real_error(self):
        (self.dist / 'broken').symlink_to('absent')
        primary = RuntimeError('real read guard')
        meter = ReadMeter(self.m, lambda count: None)
        (self.dist / 'broken').unlink()
        (self.dist / 'a').write_bytes(b'a')

        def fail(count):
            raise primary

        meter.before_read = fail
        original_write = self.m.os.write

        def failing_write(fd, data):
            if b'"hash_progress"' in data:
                raise OSError('diagnostic unavailable')
            return original_write(fd, data)

        with patch.object(self.m.os, 'write', failing_write), \
                patch.object(self.m.os, 'fdopen', meter.open):
            with self.assertRaises(RuntimeError) as caught:
                self.run_tree()
        self.assertIs(caught.exception, primary)

    def test_real_mutation_and_symlink_special_refusals(self):
        path = self.dist / 'a'
        path.write_bytes(b'old')
        digest = self.m.InspectionDigests()
        digest(path)
        path.write_bytes(b'new')
        with self.assertRaisesRegex(RuntimeError, 'changed during inspection'):
            self.run_tree(digest)
        path.unlink()
        outside = self.root / 'outside'
        outside.mkdir()
        path.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'escapes hashed root'):
            self.run_tree()
        path.unlink()
        path.symlink_to('absent')
        with self.assertRaises(FileNotFoundError):
            self.run_tree()
        path.unlink()
        os.mkfifo(path)
        with self.assertRaisesRegex(RuntimeError, 'Unsupported installed tool file'):
            self.run_tree()

    def test_disabled_contained_and_writable_directory_refusals(self):
        (self.dist / 'a').write_bytes(b'abc')
        self.m.ENV.pop('MIXER_ANDROID_INSPECTION_PHASE_DIR')
        self.run_tree()
        self.assertEqual(list(self.trace.iterdir()), [])
        self.m.ENV['MIXER_ANDROID_INSPECTION_PHASE_DIR'] = str(self.dist)
        self.m.BT = self.dist
        self.run_tree()
        self.assertEqual(list(self.dist.glob('inspection-*.jsonl')), [])
        self.m.ENV['MIXER_ANDROID_INSPECTION_PHASE_DIR'] = str(self.trace)
        self.trace.chmod(0o777)
        self.run_tree()
        self.assertEqual(list(self.trace.iterdir()), [])

    def test_preexisting_timer_and_handler_are_preserved(self):
        (self.dist / 'a').write_bytes(b'a')
        handler = lambda signum, frame: None
        signal.signal(signal.SIGALRM, handler)
        signal.setitimer(signal.ITIMER_REAL, 60, 60)
        try:
            before = signal.getitimer(signal.ITIMER_REAL)
            self.run_tree()
            after = signal.getitimer(signal.ITIMER_REAL)
            self.assertIs(signal.getsignal(signal.SIGALRM), handler)
            self.assertEqual(after[1], before[1])
            self.assertLessEqual(after[0], before[0])
            self.assertGreater(after[0], 59)
            self.assertEqual(self.rows(), [])
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, signal.SIG_DFL)

    def test_foreign_pending_alarm_and_mask_are_preserved(self):
        (self.dist / 'a').write_bytes(b'a')
        prior = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        signal.raise_signal(signal.SIGALRM)
        try:
            self.run_tree()
            self.assertIn(signal.SIGALRM, signal.sigpending())
            self.assertIn(signal.SIGALRM, signal.pthread_sigmask(signal.SIG_BLOCK, set()))
            self.assertEqual(self.rows(), [])
        finally:
            if signal.SIGALRM in signal.sigpending():
                signal.sigwait({signal.SIGALRM})
            signal.pthread_sigmask(signal.SIG_SETMASK, prior)

    def test_finish_drains_only_owned_pending_alarm_and_restores_mask(self):
        (self.dist / 'a').write_bytes(b'a')
        original = self.m.tree

        def pending(*args):
            result = original(*args)
            signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
            signal.raise_signal(signal.SIGALRM)
            return result

        self.m.tree = pending
        self.run_tree()
        self.assertEqual(self.rows()[-1]['state'], 'end')

    def test_nonmain_thread_disables_timer(self):
        sink = self.m.InspectionPhases('inspection-progress-')
        progress = self.m.InspectionProgress(sink, 'distribution.hash.jdk')
        results = []
        thread = threading.Thread(target=lambda: results.append(progress.start()))
        thread.start()
        thread.join(1)
        sink.close()
        self.assertFalse(thread.is_alive())
        self.assertEqual(results, [False])

    def test_periodic_and_total_caps_reserve_final_summaries(self):
        self.assertEqual(self.m.InspectionProgress.INTERVAL_SECONDS, 10)
        sink = self.m.InspectionPhases('inspection-progress-')
        try:
            for index in range(5):
                progress = self.m.InspectionProgress(sink, 'distribution.hash.swift_toolchain')
                self.assertTrue(progress.start())
                for _ in range(100):
                    progress.emit('progress')
                progress.finish('end')
        finally:
            sink.close()
        rows = self.rows()
        self.assertLessEqual(len(rows), 64)
        self.assertLessEqual(sum(p.stat().st_size for p in self.trace.iterdir()), 16384)
        self.assertLessEqual(sum(r['state'] == 'progress' for r in rows), 16)
        self.assertEqual(sum(r['state'] == 'end' for r in rows), 5)


if __name__ == '__main__':
    unittest.main()
