#!/usr/bin/env python3
"""Independent host controls. All writes remain in this review namespace."""
import copy
import base64
import hashlib
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE.parent / 'apple-settings-fix'
spec = importlib.util.spec_from_file_location('submitted_tests', FIX / 'test_terminal_reuse.py')
submitted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submitted)
t = submitted.candidate
d = submitted.durable_settings


class IndependentControls(submitted.ReuseTests):
    def setUp(self):
        self.scratch = pathlib.Path(tempfile.mkdtemp(prefix='case-', dir=HERE)).resolve()
        self.clock = [submitted.ROWS[0]['receivedUptime']]
        self.store = d.TransactionStore(self.scratch, submitted.ROWS[0]['ownedSimulatorIdentity'])
        self.session = t.Session(None, None, submitted.ROWS[0]['sessionDeadlineUptime'],
                                 now=lambda: self.clock[0], token=submitted.ROWS[0]['generation'],
                                 transaction=self.store)

    def test_fresh_metadata_required_even_when_bytes_match(self):
        self.before_terminal()
        original = copy.deepcopy(self.session.summary())
        mutations = [
            ('stale capture', lambda r: r.update(captureStartedUptime=self.session.last_capture_finished - 1)),
            ('stale witness', lambda r: r['switchWitness']['leaf'].update(observedUptime=0)),
            ('different identity', lambda r: r['snapshot'].update(identifier='other')),
            ('wrong route', lambda r: r.update(routeIndex=2)),
            ('wrong case', lambda r: r.update(case='another-case')),
            ('duplicate sequence', lambda r: r.update(sequence=130)),
            ('oversized PNG', lambda r: r['files']['png'].update(bytes=2_000_001)),
            ('boolean size', lambda r: r['files']['png'].update(bytes=True)),
            ('unexpected descriptor key', lambda r: r['files']['png'].update(cached=True)),
            ('action before capture', lambda r: r.update(captureStartedUptime=self.session.anchor - 1)),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name):
                row = copy.deepcopy(submitted.TERMINAL)
                mutate(row['record'])
                with self.assertRaises(ValueError):
                    self.feed(row)
                self.assertEqual(self.session.summary(), original)
                self.assertFalse((self.scratch / 'settings-0131-png.png').exists())

    def test_journal_preserves_fresh_metadata_and_copies_bytes(self):
        self.before_terminal()
        cached = self.session.completed_png
        before_total = self.session.total
        self.feed(submitted.TERMINAL)
        saved = json.loads((self.scratch / '0000-settings-0131.json').read_bytes())
        self.assertEqual(saved, submitted.TERMINAL)
        self.assertEqual(self.session.terminal, submitted.TERMINAL['record'])
        self.assertEqual(self.session.completed_png, cached)
        self.assertEqual(self.session.total - before_total,
                         sum(f['bytes'] for f in submitted.TERMINAL['record']['files'].values()))
        source = self.scratch / (cached[0] + '.png')
        terminal = self.scratch / 'settings-0131-png.png'
        self.assertNotEqual(source.stat().st_ino, terminal.stat().st_ino)
        source.write_bytes(b'tampered prior disk file')
        self.assertEqual(terminal.read_bytes(), cached[1])
        old = submitted.replay.t
        try:
            submitted.replay.t = t
            with self.assertRaisesRegex(ValueError, 'differs from journal'):
                submitted.replay.replay(self.scratch)
        finally:
            submitted.replay.t = old

    def test_absent_cache_uses_original_upload(self):
        self.before_terminal()
        self.session.completed_png = None
        response = self.feed(submitted.TERMINAL)
        self.assertEqual(response['pending'], ['settings-0131-ax', 'settings-0131-png'])
        self.assertFalse((self.scratch / 'settings-0131-png.png').exists())

    def test_nonterminal_never_reuses_matching_cached_png(self):
        for row in submitted.ROWS:
            if row is submitted.AFTER:
                break
            self.feed(row)
        row = copy.deepcopy(submitted.AFTER)
        slot, payload = self.session.completed_png
        row['record']['files']['png'] = {'bytes': len(payload), 'sha256': t.sha(payload)}
        result = self.feed(row)
        self.assertIn('settings-0083-png', result['pending'])
        self.assertFalse((self.scratch / 'settings-0083-png.png').exists())

    def test_different_valid_png_completes_original_upload_and_replay(self):
        self.before_terminal()
        earlier = self.scratch / ('settings-%04d-png.png' % self.session.before['sequence'])
        payload = earlier.read_bytes()
        self.assertNotEqual(payload, self.session.completed_png[1])
        row = copy.deepcopy(submitted.TERMINAL)
        row['record']['files']['png'] = {'bytes': len(payload), 'sha256': t.sha(payload)}
        response = self.feed(row)
        self.assertEqual(response['pending'], ['settings-0131-ax', 'settings-0131-png'])
        for slot in response['pending']:
            data = payload if slot.endswith('-png') else (submitted.CAPTURES / (slot + '.txt')).read_bytes()
            count = (len(data) + t.CHUNK - 1) // t.CHUNK
            for index in range(count):
                record = dict(kind='chunk', case=t.CASE, generation=self.session.token,
                              sequence=self.session.sequence + 1, uptime=row['record']['uptime'],
                              slot=slot, index=index, count=count, bytes=len(data), sha256=t.sha(data),
                              data=base64.b64encode(data[index*t.CHUNK:(index+1)*t.CHUNK]).decode())
                self.session.request(record)
        self.assertEqual((self.scratch / 'settings-0131-png.png').read_bytes(), payload)
        self.assertTrue(self.session.summary()['settingsEvidenceComplete'])
        old = submitted.replay.t
        try:
            submitted.replay.t = t
            self.assertEqual(submitted.replay.replay(self.scratch), self.session.summary())
        finally:
            submitted.replay.t = old

    def test_matching_hash_cannot_bypass_png_validation(self):
        self.before_terminal()
        slot, _ = self.session.completed_png
        invalid = b'not a PNG'
        descriptor = {'bytes': len(invalid), 'sha256': t.sha(invalid)}
        self.session.completed_png = (slot, invalid)
        self.session.uploads[slot].update(descriptor)
        row = copy.deepcopy(submitted.TERMINAL)
        row['record']['files']['png'] = descriptor
        with self.assertRaisesRegex(ValueError, 'PNG signature'):
            self.feed(row)
        self.assertEqual(self.session.sequence, 130)

    def test_aggregate_bound_still_counts_copied_payload(self):
        self.before_terminal()
        self.session.total = t.MAX_TOTAL - submitted.TERMINAL['record']['files']['ax']['bytes']
        with self.assertRaisesRegex(ValueError, 'Aggregate upload bound'):
            self.feed(submitted.TERMINAL)
        self.assertEqual(self.session.sequence, 130)

    def test_payload_and_journal_publication_failures_are_atomic(self):
        self.before_terminal()
        before = copy.deepcopy(self.session.summary())
        for target in ['payload', 'journal']:
            with self.subTest(role=target):
                original = self.store.io.publish
                def fail(staged, final, role):
                    original(staged, final, role)
                    if role == target:
                        raise OSError('injected after ' + role + ' publication')
                self.store.io.publish = fail
                try:
                    with self.assertRaisesRegex(OSError, 'injected after'):
                        self.feed(submitted.TERMINAL)
                finally:
                    self.store.io.publish = original
                self.assertEqual(self.session.summary(), before)
                self.assertFalse((self.scratch / 'settings-0131-png.png').exists())
                self.assertFalse((self.scratch / '0000-settings-0131.json').exists())
                self.assertFalse(d.unresolved(self.scratch))
        self.assertEqual(self.feed(submitted.TERMINAL)['pending'], ['settings-0131-ax'])

    def test_publication_directory_failure_rolls_back(self):
        self.before_terminal()
        original = self.store.io.sync
        def fail(path, role):
            if role == 'publication-directory':
                raise OSError('injected publication directory sync')
            return original(path, role)
        self.store.io.sync = fail
        with self.assertRaisesRegex(OSError, 'injected publication'):
            self.feed(submitted.TERMINAL)
        self.assertEqual(self.session.sequence, 130)
        self.assertFalse((self.scratch / 'settings-0131-png.png').exists())
        self.assertFalse((self.scratch / '0000-settings-0131.json').exists())
        self.assertFalse(d.unresolved(self.scratch))

    def test_postcommit_retirement_cannot_reject_ack_but_blocks_replay(self):
        self.before_terminal()
        original = self.store.io.unlink
        def fail(path, role):
            if role == 'guard-clear':
                raise OSError('injected committed guard retirement')
            return original(path, role)
        self.store.io.unlink = fail
        response = self.feed(submitted.TERMINAL)
        self.assertTrue(response['accepted'])
        self.assertEqual(self.session.sequence, 131)
        self.assertTrue((self.scratch / 'settings-0131-png.png').is_file())
        self.assertTrue(self.session.summary()['persistenceUncertain'])
        self.assertFalse(self.session.summary()['setupObservationSatisfied'])
        next_row = next(r for r in submitted.ROWS if r['record'].get('sequence') == 132)
        with self.assertRaises(d.PersistenceUncertain):
            self.feed(next_row)
        with self.assertRaises(d.PersistenceUncertain):
            submitted.replay.replay(self.scratch)
        self.store.io.unlink = original
        self.assertTrue(self.store.resolve_retirement())
        self.assertTrue(self.feed(next_row)['accepted'])

    def test_existing_terminal_file_is_never_overwritten(self):
        self.before_terminal()
        path = self.scratch / 'settings-0131-png.png'
        path.write_bytes(b'preexisting evidence')
        with self.assertRaisesRegex(ValueError, 'Fixed fresh telemetry artifact'):
            self.feed(submitted.TERMINAL)
        self.assertEqual(path.read_bytes(), b'preexisting evidence')
        self.assertEqual(self.session.sequence, 130)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (HERE / 'host-controls-result.json').write_text(json.dumps({
        'scope': 'host Python only; retained V9 observations, no native claims',
        'testsRun': result.testsRun, 'submittedTestsReexecuted': 12,
        'independentTestsAdded': result.testsRun - 12,
        'failures': len(result.failures), 'errors': len(result.errors),
        'passed': result.wasSuccessful(), 'scratchRemoved': not list(HERE.glob('case-*')),
    }, indent=2) + '\n')
    sys.exit(not result.wasSuccessful())
