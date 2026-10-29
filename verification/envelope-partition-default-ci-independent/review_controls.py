#!/usr/bin/env python3
"""Independent source-only review, with guards before every subject import."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / 'verification/envelope-partition-default-ci-adoption'
sys.path.insert(0, str(HERE))
import offline_guard
offline_guard.install(HERE)

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout, redirect_stderr
from copy import deepcopy
from types import ModuleType, SimpleNamespace

# Read the sealed controls without modifying their on-disk bytes. Their own
# install call is omitted because this independent guard already confines all
# mutations to HERE; the inherited scratch methods below use this owned root.
sys.path.insert(0, str(PACKET))
source = (PACKET / 'test_adoption.py').read_text()
assert source.count('offline_guard.install(HERE)') == 2  # call plus self-check literal
source = source.replace('offline_guard.install(HERE)\n', '# Independent guard already installed.\n', 1)
subject = ModuleType('sealed_adoption_controls')
subject.__file__ = str(PACKET / 'test_adoption.py')
exec(compile(source, subject.__file__, 'exec'), subject.__dict__)
a, c, BASE = subject.a, subject.c, subject.BASE


class IndependentControls(subject.Controls):
    def setUp(self):
        scratch = HERE / 'control-scratch'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='independent-', dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.assertEqual(offline_guard.DENIED, [])

    @classmethod
    def tearDownClass(cls):
        scratch = HERE / 'control-scratch'
        if scratch.exists():
            if list(scratch.iterdir()):
                raise RuntimeError('Independent scratch not empty')
            scratch.rmdir()
        if offline_guard.DENIED:
            raise RuntimeError('Denied operations attempted: ' + repr(offline_guard.DENIED))

    def test_independent_preflight_denial_blocks_both_subject_imports(self):
        calls = []
        def refuse(*args, **kwargs):
            raise RuntimeError('independent dependency mismatch')
        def load(*args, **kwargs):
            calls.append(args)
            self.fail('Subject import after failed binding')
        with subject.patched(a, 'verify', refuse), subject.patched(a, 'module_at', load):
            with self.assertRaisesRegex(RuntimeError, 'dependency mismatch'):
                a.load_runner()
        self.assertEqual(calls, [])

    def test_independent_bad_revision_blocks_output_and_runner_admission(self):
        for revision in ['', 'a' * 39, 'a' * 41, 'A' * 40, 'g' * 40, 'a' * 39 + '\n']:
            target = self.work / 'never-created'
            with self.subTest(revision=revision), \
                    subject.patched(a.os, 'environ', {'RUSTUP_AUTO_INSTALL': '0', 'GITHUB_SHA': revision}), \
                    subject.patched(a, 'load_runner', lambda: self.fail('No runner admission expected')):
                with self.assertRaisesRegex(RuntimeError, 'source revision required'):
                    a.run_fixture(target, '/inert/rustc')
            self.assertFalse(target.exists())

    def adapter_case(self, *, exception=None, tamper_snapshot=False, absent_receipt=False):
        out = self.work / 'fixture'
        calls, checks = [], []
        original_fresh = c.fresh_output
        real_verify = a.verify
        fake_replay = SimpleNamespace(replay=lambda *args: {'passed': True, 'mocked': True})
        def execute(target, rustc):
            calls.append(rustc)
            if tamper_snapshot:
                (target / 'executed-adapter.py').write_bytes(b'tampered executed snapshot')
            if not absent_receipt:
                c.write_json(target / 'receipt.json', {'rustc': {'identity': 'synthetic'}, 'status': 'synthetic'})
            if exception is not None:
                raise exception
            return 0
        def verify(installed=False):
            checks.append(installed)
            return real_verify(False)
        with ExitStack() as stack:
            for obj, name, value in [
                    (a, 'verify', verify), (a, 'load_runner', lambda: (c, BASE, subject.PROOF)),
                    (a, 'module_at', lambda *args: fake_replay), (c, 'execute', execute),
                    (c, 'fresh_output', lambda p: original_fresh(p, root=self.work)),
                    (a.os, 'environ', {'RUSTUP_AUTO_INSTALL': '0', 'GITHUB_SHA': subject.REVISION})]:
                stack.enter_context(subject.patched(obj, name, value))
            result = a.run_fixture(out, '/inert/rustc')
        self.assertEqual(calls, ['/inert/rustc'])
        self.assertEqual(checks, [True, True])
        return result, json.loads((out / 'adapter-result.json').read_bytes())

    def test_independent_tampered_executed_snapshot_overrides_success(self):
        result, finish = self.adapter_case(tamper_snapshot=True)
        self.assertEqual(result, 1)
        self.assertEqual(finish['fixture_return_status'], 0)
        self.assertEqual(finish['errors'][0]['phase'], 'source-postflight')
        self.assertIn('Executed source identity differs', finish['errors'][0]['message'])

    def test_independent_missing_receipt_cannot_be_success(self):
        result, finish = self.adapter_case(absent_receipt=True)
        self.assertEqual(result, 1)
        self.assertIsNone(finish['terminal_replay'])
        self.assertEqual(finish['errors'][0]['phase'], 'terminal-replay')

    def test_independent_interrupt_is_recorded_and_postflight_runs(self):
        result, finish = self.adapter_case(exception=KeyboardInterrupt('independent synthetic interrupt'))
        self.assertEqual(result, 1)
        self.assertEqual(finish['adapter_exception']['type'], 'KeyboardInterrupt')
        self.assertEqual(finish['errors'], [])
        self.assertIsNone(finish['terminal_replay'])

    def test_independent_terminal_replay_rejects_coherent_receipt_forgeries(self):
        self.complete_mock()
        out = self.work / 'run/fixture'
        original = json.loads((out / 'receipt.json').read_bytes())
        replay = a.module_at('independent_terminal_replay', PACKET / 'terminal_replay.py')
        admission = {'revision': subject.REVISION, 'compiler': original['rustc']['path'],
                     'compiler_sha256': original['rustc']['sha256']}
        cases = [
            ('capture-ledger-splice', lambda r: r['commands'][1].update(aggregate_bytes_before=999)),
            ('missing-eof', lambda r: r['commands'][0]['pipe_eof'].update(stderr=False)),
            ('unreported-descendant', lambda r: r['commands'][0].update(descendants_outlived_direct_child=True)),
            ('forged-negative-success', lambda r: next(x for x in r['commands'] if x['name'].startswith('api-negative-')).update(exit=0)),
            ('wrong-compiler-tuple', lambda r: r['rustc']['identity'].update(release='1.99.1')),
            ('qualification-authority', lambda r: r.update(storedPrefixValidated=True)),
            ('partition-open', lambda r: r['producer_partition'].update(complete_disjoint_coverage=False)),
            ('independent-order', lambda r: r['test_binaries']['independent']['executed'].reverse()),
            ('missing-postflight', lambda r: r['postflight'].pop('launcher')),
        ]
        for label, mutate in cases:
            changed = deepcopy(original)
            mutate(changed)
            c.write_json(out / 'receipt.json', changed)
            # Update sidecars too, so a self-consistent receipt cannot evade the
            # custody, ledger, compiler policy or qualification checks.
            for row in changed['commands']:
                c.write_json(out / 'commands' / (row['name'] + '.json'), row)
            with self.subTest(forgery=label), self.assertRaises(RuntimeError):
                replay.replay(out, admission, c)
        c.write_json(out / 'receipt.json', original)
        for row in original['commands']:
            c.write_json(out / 'commands' / (row['name'] + '.json'), row)
        self.assertEqual(replay.replay(out, admission, c)['commands'], 40)

    def test_independent_retained_payload_digest_mutation_is_rejected(self):
        preserve = c.preserve_and_cleanup
        def with_payload(out, scratch, *args):
            (scratch / 'independent-retained-payload.bin').write_bytes(b'Independent inert retained fixture payload')
            return preserve(out, scratch, *args)
        with subject.patched(c, 'preserve_and_cleanup', with_payload):
            self.complete_mock()
        out = self.work / 'run/fixture'
        receipt = json.loads((out / 'receipt.json').read_bytes())
        replay = a.module_at('independent_retention_replay', PACKET / 'terminal_replay.py')
        admission = {'revision': subject.REVISION, 'compiler': receipt['rustc']['path'],
                     'compiler_sha256': receipt['rustc']['sha256']}
        retained = json.loads((out / 'retention.json').read_bytes())['test_files']
        name, record = next(iter(retained.items()))
        target = out / record['path']
        before = target.read_bytes()
        self.assertTrue(before)
        target.write_bytes(bytes([before[0] ^ 1]) + before[1:])
        with self.assertRaisesRegex(RuntimeError, 'Retained bytes differ'):
            replay.replay(out, admission, c)
        target.write_bytes(before)
        self.assertTrue(replay.replay(out, admission, c)['passed'])


if __name__ == '__main__':
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        program = unittest.main(exit=False, verbosity=2)
    result = program.result
    summary = {
        'schema': 1, 'tests': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'skipped': len(result.skipped),
        'passed': result.wasSuccessful(), 'python': sys.version, 'interpreter': sys.executable,
        'denied_operation_attempts': offline_guard.DENIED,
        'guard_precedes_subject_imports': True,
        'inherited_frozen_controls': 22, 'new_independent_controls': 7,
        'coherent_terminal_forgeries': 9,
        'control_scratch_absent': not (HERE / 'control-scratch').exists(),
        'actual_subject_processes_compilers_producers_products_native_runs': 0,
        'scope': 'Source-only, real Python orchestration with fake children, signals, timers, streams and inert products.'}
    (HERE / 'raw/controls.stdout').write_text(stdout.getvalue())
    (HERE / 'raw/controls.stderr').write_text(stderr.getvalue())
    (HERE / 'controls-result.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, sort_keys=True))
    print(stderr.getvalue())
    sys.exit(0 if result.wasSuccessful() else 1)
