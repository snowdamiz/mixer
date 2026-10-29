#!/usr/bin/env python3
"""Guarded pure controls: fake children/streams/clocks only; no process access."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
import offline_guard
offline_guard.install(HERE)
import ast
from copy import deepcopy
from datetime import datetime, timezone
import difflib
import hashlib
import io
import json
from types import SimpleNamespace
import tempfile
import unittest
class patch:
    @staticmethod
    def object(target, name, *values, return_value=None, side_effect=None):
        class AttributePatch:
            def start(self):
                self.previous = getattr(target, name)
                def replacement(*args, **kwargs):
                    if isinstance(side_effect, BaseException): raise side_effect
                    if side_effect is not None: return side_effect(*args, **kwargs)
                    return return_value
                setattr(target, name, values[0] if values else replacement)
            def stop(self): setattr(target, name, self.previous)
        return AttributePatch()
import candidate_runner as c
ROOT = HERE.parents[1]
PACK = ROOT / c.PACK
NAMES = json.loads((PACK / 'inventories/expected-methods.json').read_bytes())['producer']['names']


def result(names, total=78):
    return ('running ' + str(len(names)) + ' tests\n' +
            ''.join('test ' + n + ' ... ok\n' for n in names) +
            '\ntest result: ok. ' + str(len(names)) + ' passed; 0 failed; 0 ignored; 0 measured; ' +
            str(total - len(names)) + ' filtered out; finished in 0.00s\n')


class FakeCommands:
    def __init__(self, fail=None, bad=None):
        self.receipt = {}; self.calls = []; self.fail = fail; self.bad = bad; self.saved = 0
    def save(self):
        self.saved += 1
    def run(self, name, argv, *, cwd, env, timeout):
        self.calls.append((name, argv, cwd, env, timeout))
        if len(self.calls) == self.fail:
            raise RuntimeError('first-command-failure')
        group = next(g for g in c.producer_groups(NAMES) if 'producer-' + g['name'] == name)
        text = result(group['methods'])
        if len(self.calls) == self.bad:
            text = text.replace(' passed;', ' missing;')
        return text, '', {'name': name, 'stdout': {'path': name + '.stdout'}}


class FakePipe:
    def __init__(self, fd): self.fd = fd; self.closed = False
    def fileno(self): return self.fd
    def close(self): self.closed = True


class FakeProc:
    def __init__(self, exit=0, running=False):
        self.pid = 424242; self.returncode = None if running else exit
        self.stdout = FakePipe(700001); self.stderr = FakePipe(700002)
        self.waits = []; self.running = running
    def poll(self): return self.returncode
    def wait(self, timeout):
        self.waits.append(timeout)
        if self.returncode is None: self.returncode = -9
        return self.returncode


class FakeSelector:
    def __init__(self): self.rows = {}; self.closed = False
    def register(self, pipe, events, data): self.rows[pipe.fd] = SimpleNamespace(fileobj=pipe, data=data)
    def unregister(self, pipe): del self.rows[pipe.fd]
    def get_map(self): return self.rows
    def select(self, timeout): return [(key, 1) for key in list(self.rows.values())]
    def close(self): self.closed = True


class PureControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pure-', dir=HERE)
        self.addCleanup(self.tmp.cleanup); self.work = Path(self.tmp.name)
        self.binary = self.work / 'fixture-test-binary'; self.binary.write_bytes(b'synthetic fixture bytes, never executable')
    def orchestrate(self, fake):
        scratch = self.work / 'scratch'; scratch.mkdir()
        return c.execute_test_groups(fake, 'producer', self.binary, self.work, scratch, {}, NAMES)
    def command(self, *, chunks=None, exit=0, running=False, tick=0, cap=None,
                total=None, initial_output=0, deadline=1000, stop_error=None, read_error=None, spawn_error=None, gone=True, negative=False):
        out = self.work / ('command-' + str(len(list(self.work.iterdir())))); out.mkdir()
        receipt = {'commands': []}; runner = c.Commands(out, receipt, deadline); runner.output_bytes = initial_output
        proc = FakeProc(exit, running); selector = FakeSelector(); clock = [0]
        streams = chunks or {700001: [b'hello', b''], 700002: [b'', b'']}
        def read(fd, count):
            if read_error: raise read_error
            return streams[fd].pop(0) if streams[fd] else b''
        def mono():
            value = clock[0]; clock[0] += tick; return value
        def kill(pid, sig):
            self.assertEqual(pid, proc.pid); self.assertEqual(sig, 0)
            if gone: raise ProcessLookupError()
        def stop(child, row):
            self.assertIs(child, proc)
            if stop_error: raise stop_error
            row.update(child_returned=True, owned_group_gone=True, owned_group_killed=True)
            proc.returncode = -9
        stack = [patch.object(c.subprocess, 'Popen', side_effect=spawn_error) if spawn_error else patch.object(c.subprocess, 'Popen', return_value=proc),
                 patch.object(c.selectors, 'DefaultSelector', return_value=selector),
                 patch.object(c.os, 'read', side_effect=read), patch.object(c.os, 'killpg', side_effect=kill),
                 patch.object(c.time, 'monotonic', side_effect=mono), patch.object(runner, 'stop_group', side_effect=stop),
                 patch.object(c, 'OUTPUT_CAP', 100 if cap is None else cap),
                 patch.object(c, 'TOTAL_OUTPUT_CAP', 1000 if total is None else total)]
        for p in stack: p.start()
        try:
            try:
                value = runner.run('synthetic', ['never-executed'], cwd=self.work, timeout=120, negative=negative)
                error = None
            except BaseException as e:
                value = None; error = e
        finally:
            for p in reversed(stack): p.stop()
        return SimpleNamespace(value=value, error=error, row=receipt['commands'][0], runner=runner,
                               proc=proc, selector=selector, out=out)
    def test_exact_overlay(self):
        overlay = json.loads((HERE / 'overlay.json').read_bytes())
        base = (ROOT / overlay['base_path']).read_text()
        self.assertEqual(hashlib.sha256(base.encode()).hexdigest(), overlay['base_sha256'])
        for change in overlay['changes']:
            self.assertEqual(base.count(change['before']), 1, change['label'])
            base = base.replace(change['before'], change['after'])
        self.assertEqual(base, (HERE / 'candidate_runner.py').read_text())
        self.assertEqual(hashlib.sha256(base.encode()).hexdigest(), overlay['candidate_sha256'])
        ast.parse(base)
    def test_frozen_pack_complete(self):
        self.assertEqual(c.verify_pack(PACK)['tree_sha256'], c.PACK_TREE_SHA256)
        self.assertEqual(hashlib.sha256((PACK / 'source/producer/independent_tests.rs').read_bytes()).hexdigest(),
                         'f5a56f984fb087edc86a50388a3b014902c965dae6a3787031fc1c56f269891d')
    def test_protected_sources_untouched(self):
        for name, wanted in {
            '.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57',
            'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), wanted)
    def test_partition_complete_unique_same_order(self):
        groups = c.producer_groups(NAMES)
        self.assertEqual(groups, json.loads((HERE / 'producer-partition.json').read_bytes())['groups'])
        self.assertEqual(len(groups), 18)
        self.assertEqual([len(g['methods']) for g in groups], [1] * 11 + [61] + [1] * 6)
        self.assertEqual([n for g in groups for n in g['methods']], NAMES)
        for g in groups:
            selected = [n for n in NAMES if n == g['args'][0]] if '--exact' in g['args'] else [n for n in NAMES if g['args'][0] in n]
            self.assertEqual(selected, g['methods'])
    def test_partition_missing_duplicate_reorder_unknown_refused(self):
        variants = [NAMES[:-1], NAMES + [NAMES[0]], list(reversed(NAMES)), sorted(NAMES[:-1] + ['unknown::method'])]
        for names in variants:
            with self.assertRaises(RuntimeError): c.producer_groups(names)
    def test_actual_orchestrator_complete(self):
        fake = FakeCommands(); output, observed = self.orchestrate(fake)
        self.assertEqual(observed, NAMES); self.assertEqual(len(fake.calls), 18)
        self.assertTrue(fake.receipt['producer_partition']['complete_disjoint_coverage'])
        self.assertEqual(output.count('test result: ok.'), 18)
        self.assertEqual([n for g in fake.receipt['producer_partition']['completed_groups'] for n in g['methods']], NAMES)
        self.assertTrue(all(row[-1] == 120 for row in fake.calls))
        self.assertEqual(len({row[3]['MIXER_REVIEW_SCRATCH'] for row in fake.calls}), 18)
        for _, argv, _, env, _ in fake.calls:
            self.assertEqual(argv[-2:], ['--test-threads=1', '--nocapture'])
            self.assertTrue(Path(env['MIXER_REVIEW_SCRATCH']).is_relative_to(self.work))
            self.assertEqual(env['TMPDIR'], env['TMP']); self.assertEqual(env['TMP'], env['TEMP'])
    def test_first_command_failure_stops_every_later_group(self):
        fake = FakeCommands(fail=3)
        with self.assertRaisesRegex(RuntimeError, '^first-command-failure$'): self.orchestrate(fake)
        self.assertEqual(len(fake.calls), 3)
        self.assertEqual(len(fake.receipt['producer_partition']['completed_groups']), 2)
        self.assertFalse(fake.receipt['producer_partition']['complete_disjoint_coverage'])
    def test_first_bad_summary_stops_every_later_group(self):
        fake = FakeCommands(bad=2)
        with self.assertRaisesRegex(RuntimeError, 'Partial/ignored/failed'): self.orchestrate(fake)
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(len(fake.receipt['producer_partition']['completed_groups']), 1)
        self.assertFalse(fake.receipt['producer_partition']['complete_disjoint_coverage'])
    def test_group_summary_counts_filtered_duplicate_missing_failed_refused(self):
        name = NAMES[0]; valid = result([name])
        self.assertEqual(c.verify_methods(valid, [name], True, 77), [name])
        for text in [valid.replace('77 filtered', '0 filtered'), valid.replace('1 passed', '0 passed'),
                     valid.replace('0 ignored', '1 ignored'), valid.replace('0 failed', '1 failed'),
                     valid.replace(' ... ok', ' ... FAILED'), valid + valid, valid.split('test result:')[0],
                     valid.replace(name, NAMES[1])]:
            with self.assertRaises(RuntimeError): c.verify_methods(text, [name], True, 77)
    def test_terminal_command_records_actual_eof_and_hashes(self):
        r = self.command(); self.assertIsNone(r.error); self.assertEqual(r.value[:2], ('hello', ''))
        self.assertEqual(r.row['pipe_eof'], {'stdout': True, 'stderr': True})
        self.assertEqual(r.row['stdout']['sha256'], hashlib.sha256(b'hello').hexdigest())
        self.assertEqual(r.row['aggregate_bytes_after'], 5)
        self.assertFalse(r.row['output_capped']); self.assertFalse(r.row['custody_hold'])
        self.assertTrue(r.proc.stdout.closed and r.proc.stderr.closed and r.selector.closed)
        self.assertEqual(json.loads((r.out / 'commands/synthetic.json').read_bytes()), r.row)
    def test_negative_exit_one_only(self):
        self.assertIsNone(self.command(exit=1, negative=True).error)
        self.assertIsInstance(self.command(exit=0, negative=True).error, RuntimeError)
        self.assertIsInstance(self.command(exit=2, negative=True).error, RuntimeError)
    def test_failure_exit_is_not_success(self):
        r = self.command(exit=1); self.assertIsInstance(r.error, RuntimeError)
        self.assertFalse(r.row['custody_hold']); self.assertEqual(r.row['exit'], 1)
    def test_timeout_stops_owned_child_and_does_not_invent_eof(self):
        r = self.command(running=True, tick=121)
        self.assertIsInstance(r.error, TimeoutError); self.assertTrue(r.row['timed_out'])
        self.assertTrue(r.row['owned_group_killed']); self.assertTrue(r.row['owned_group_gone'])
        self.assertFalse(any(r.row['pipe_eof'].values())); self.assertEqual(r.row['exit'], -9)
    def test_stream_output_cap_preserves_exact_bounded_prefix(self):
        r = self.command(cap=3)
        self.assertIsInstance(r.error, RuntimeError); self.assertIn('output cap', str(r.error))
        self.assertTrue(r.row['output_capped']); self.assertEqual(r.row['stdout']['bytes'], 3)
        self.assertEqual((r.out / 'commands/synthetic.stdout').read_bytes(), b'hel')
        self.assertEqual(r.row['aggregate_bytes_after'], 3); self.assertTrue(r.row['owned_group_gone'])
    def test_total_output_cap_shared_across_streams(self):
        r = self.command(total=6, chunks={700001: [b'four', b''], 700002: [b'four', b'']})
        self.assertIsInstance(r.error, RuntimeError); self.assertTrue(r.row['output_capped'])
        self.assertEqual(r.row['stdout']['bytes'] + r.row['stderr']['bytes'], 6)
        self.assertEqual(r.row['aggregate_bytes_after'], 6)
    def test_exact_cap_is_allowed_only_with_actual_eof(self):
        r = self.command(cap=5, total=5)
        self.assertIsNone(r.error); self.assertFalse(r.row['output_capped'])
        self.assertTrue(all(r.row['pipe_eof'].values()))
    def test_first_failure_preserved_when_cleanup_also_fails(self):
        primary = ValueError('original-read-failure')
        r = self.command(read_error=primary, stop_error=RuntimeError('cleanup-failed'))
        self.assertIs(r.error, primary); self.assertTrue(r.row['custody_hold'])
        self.assertIs(r.runner.active, r.proc); self.assertFalse(r.row['owned_group_gone'])
        self.assertEqual([e['phase'] for e in r.row['errors']], ['active', 'stop-owned-group'])
    def test_custody_hold_prevents_scratch_removal(self):
        r = self.command(read_error=ValueError('read'), stop_error=RuntimeError('stop'))
        scratch = self.work / 'must-remain'; scratch.mkdir(); (scratch / 'keep').write_text('held')
        with self.assertRaisesRegex(RuntimeError, 'Owned children/groups'):
            c.preserve_and_cleanup(self.work, scratch, None, None, set(), r.runner)
        self.assertEqual((scratch / 'keep').read_text(), 'held')
    def test_descendant_outliving_child_is_failed_even_after_cleanup(self):
        r = self.command(gone=False)
        self.assertIsInstance(r.error, RuntimeError); self.assertTrue(r.row['descendants_outlived_direct_child'])
        self.assertTrue(r.row['owned_group_gone']); self.assertFalse(r.row['custody_hold'])
    def test_spawn_error_retains_empty_hashes_without_custody_claim(self):
        error = OSError('synthetic-spawn-failure'); r = self.command(spawn_error=error)
        self.assertIs(r.error, error); self.assertIn('spawn_error', r.row)
        self.assertNotIn('pid', r.row); self.assertFalse(r.row['child_returned'])
        self.assertFalse(r.row['owned_group_gone']); self.assertFalse(r.row['custody_hold'])
        self.assertEqual(r.row['stdout']['bytes'] + r.row['stderr']['bytes'], 0)
    def test_source_original_budgets_and_tests_preserved(self):
        source = (HERE / 'candidate_runner.py').read_text()
        for required in ['started + 480', 'signal.setitimer(signal.ITIMER_REAL, 480)',
                         'signal.setitimer(signal.ITIMER_REAL, 60)', 'timeout=120',
                         'ENVELOPE_ORACLE_CASES=16170', 'CORRECTED_FINITE_BUDGET_CASES=5544']:
            self.assertIn(required, source)
        baseline = (ROOT / 'scripts/ci/check-analyzer-envelope.py').read_text()
        def defs(s):
            return {n.name: ast.get_source_segment(s, n) for n in ast.parse(s).body if isinstance(n, ast.FunctionDef)}
        old, new = defs(baseline), defs(source)
        for name in old.keys() - {'execute', 'verify_methods'}:
            self.assertEqual(old[name], new[name], name)
        self.assertEqual(c.FLAGS, {k: False for k in c.FLAGS})
    def test_total_output_cap_includes_prior_commands(self):
        r = self.command(total=6, initial_output=4)
        self.assertIsInstance(r.error, RuntimeError); self.assertTrue(r.row['output_capped'])
        self.assertEqual(r.row['aggregate_bytes_before'], 4)
        self.assertEqual(r.row['aggregate_bytes_after'], 6)
        self.assertEqual(r.row['stdout']['bytes'], 2)
    def test_command_deadline_clamped_to_remaining_aggregate(self):
        r = self.command(deadline=12, tick=13, running=True)
        self.assertIsInstance(r.error, TimeoutError)
        self.assertEqual(r.row['timeout_seconds'], 12)
        self.assertTrue(r.row['timed_out'])
    def test_custody_hold_refuses_next_command(self):
        r = self.command(read_error=ValueError('read'), stop_error=RuntimeError('stop'))
        with self.assertRaisesRegex(RuntimeError, 'Only one synchronous child group'):
            r.runner.run('must-not-launch', ['never'], cwd=self.work)
        self.assertEqual(len(r.runner.receipt['commands']), 1)
    def test_independent_lane_keeps_one_unfiltered_execution(self):
        names = ['a', 'b']
        class Independent:
            def run(inner, name, argv, *, cwd, env, timeout):
                self.assertEqual(name, 'independent-execute'); self.assertEqual(timeout, 120)
                self.assertEqual(argv, [self.binary, '--test-threads=1', '--nocapture'])
                return result(names, 2), '', {}
        text, observed = c.execute_test_groups(Independent(), 'independent', self.binary,
                                               self.work, self.work, {}, names)
        self.assertEqual(observed, names); self.assertEqual(text.count('test result:'), 1)
    def test_observed_method_order_reversal_refused(self):
        names = ['a', 'b']
        with self.assertRaisesRegex(RuntimeError, 'method order'):
            c.verify_methods(result(list(reversed(names)), 2), names, True)
    def test_partial_retained_baseline_still_refused(self):
        old = ROOT / 'verification/github-delivery-fixture-context-v4/ci-review/engine-envelope/extract/commands/producer-execute.stdout'
        if not old.exists():
            self.skipTest('Ignored local failure artifact not shipped; immutable original failure remains separately bound')
        text = old.read_text()
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),
                         '5d7e187eea92deb7073cf50e2bc5a7c421692527db2965b07b619ea3b1d1a1ca')
        with self.assertRaisesRegex(RuntimeError, 'Partial/ignored/failed'):
            c.verify_methods(text, NAMES, True)
    def test_guard_has_seen_no_attempted_real_process_calls(self):
        self.assertEqual(offline_guard.DENIED, [])


if __name__ == '__main__':
    logs = HERE / 'logs'; logs.mkdir(exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PureControls)
    stream = io.StringIO(); outcome = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    text = stream.getvalue(); print(text, end=''); (logs / 'pure-controls.stdout').write_text(text)
    source = (ROOT / 'scripts/ci/check-analyzer-envelope.py').read_text()
    candidate = (HERE / 'candidate_runner.py').read_text()
    diff = ''.join(difflib.unified_diff(source.splitlines(keepends=True), candidate.splitlines(keepends=True),
                                      fromfile='scripts/ci/check-analyzer-envelope.py',
                                      tofile='verification/envelope-producer-timeout-experiment/candidate_runner.py'))
    (HERE / 'runner.diff').write_text(diff)
    receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
               'command': 'python3 -B verification/envelope-producer-timeout-experiment/test_candidate.py',
               'python': sys.version, 'interpreter': sys.executable, 'source_head': '00e087210c24406aff49bcf3563bd4226e76660b',
               'source_tree': '8ffa6120f3173815ff12fdcb094554f000410ffc',
               'source_head_scope': 'caller supplied baseline, frozen input digests independently checked; no Git process launched',
               'candidate_sha256': hashlib.sha256(candidate.encode()).hexdigest(),
               'tests_run': outcome.testsRun, 'failures': len(outcome.failures), 'errors': len(outcome.errors), 'skipped': len(outcome.skipped),
               'success': outcome.wasSuccessful(), 'real_process_calls_denied_or_attempted': offline_guard.DENIED,
               'scope': 'actual candidate Python functions with fake children, streams and clock; no product runtime or actual custody test',
               'native_runtime_ui_capture_held_groups_probed': False, 'runtime_acceptance': False}
    (logs / 'pure-controls.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    raise SystemExit(not outcome.wasSuccessful())
