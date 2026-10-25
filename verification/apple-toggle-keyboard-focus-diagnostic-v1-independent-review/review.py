#!/usr/bin/env python3
"""Offline independent review. Writes only this review directory; no authority code."""
import ast
import copy
import datetime
import hashlib
import importlib.util
import io
import json
import pathlib
import re
import sys
import unittest

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / 'verification/apple-toggle-keyboard-focus-diagnostic-v1'
V3 = ROOT / 'verification/apple-toggle-keyboard-full-case-preparation-v3'
PURE = V3 / 'inputs/runtime/verification'
ORACLES = [
    PURE / 'apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py',
    PURE / 'apple-toggle-keyboard-focus/keyboard_oracle.py',
    PURE / 'apple-toggle-pan-commit-harness-v2/commit_oracle.py',
    PURE / 'apple-toggle-pan-origin-correction/oracle.py',
    PURE / 'apple-toggle-native-interruption/interruption_oracle.py',
    PURE / 'apple-toggle-semantic-activation/semantic_oracle.py',
]
CASES = [PURE / name / 'cases.json' for name in (
    'apple-toggle-keyboard-focus', 'apple-toggle-pan-commit-harness-v2',
    'apple-toggle-native-interruption')]
READ_SOURCE = [V3 / 'composition.py',
    PURE / 'apple-toggle-pan-origin-correction/harness.py',
    PURE / 'apple-toggle-pan-origin-correction/bridge.py',
    ROOT / 'AGENTS.md', ROOT / 'docs/apple-toggle-keyboard-focus-diagnostic-v1.md']
ALLOWED_EXEC = set(ORACLES + [PRODUCER / name for name in (
    'prepare.py', 'focus_diagnostic.py', 'test_diagnostic.py')])
EXECUTED_REPOSITORY_CODE = set()


def audit(event, args):
    if event == 'exec':
        filename = args[0].co_filename
        if filename.startswith(str(ROOT) + '/'):
            path = pathlib.Path(filename).resolve()
            if path not in ALLOWED_EXEC:
                raise RuntimeError('Unreviewed repository code execution refused: ' + str(path))
            EXECUTED_REPOSITORY_CODE.add(path)
    if event in ('subprocess.Popen', 'os.system', 'socket.connect', 'socket.bind'):
        raise RuntimeError('Out-of-scope operation refused: ' + event)
    if event == 'open' and len(args) >= 3:
        name, mode, flags = args
        if isinstance(name, (str, bytes)):
            writes = (isinstance(mode, str) and any(x in mode for x in 'wax+')) or (isinstance(flags, int) and flags & 0x603)
            if writes and not pathlib.Path(name).resolve().is_relative_to(BASE):
                raise RuntimeError('Write outside review refused: ' + str(name))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def descriptor(path):
    data = path.read_bytes()
    return {'sha256': sha(data), 'bytes': len(data)}


def apply_unified(original, patch):
    """Separate patch reader; all source and hunk positions checked in memory."""
    lines = iter(patch.decode().splitlines(keepends=True))
    pending = None
    result = {}
    while True:
        first = pending if pending is not None else next(lines, None)
        pending = None
        if first is None:
            break
        assert first.startswith('--- ')
        second = next(lines)
        assert second.startswith('+++ b/')
        name = second[6:].rstrip('\n')
        assert name not in result and '..' not in pathlib.PurePosixPath(name).parts
        source = original.get(name, '').splitlines(keepends=True)
        assert first == ('--- a/' + name + '\n' if name in original else '--- /dev/null\n')
        out = []
        at = 0
        line = next(lines, None)
        while line is not None and line.startswith('@@ '):
            match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n', line)
            assert match
            start = max(int(match[1]) - 1, 0)
            assert start >= at
            out.extend(source[at:start]); at = start
            assert len(out) == max(int(match[3]) - 1, 0)
            removed = added = 0
            line = next(lines, None)
            while line is not None and not line.startswith(('@@ ', '--- ')):
                assert line[:1] in (' ', '+', '-')
                if line[0] != '+':
                    assert source[at] == line[1:]
                    at += 1; removed += 1
                if line[0] != '-':
                    out.append(line[1:]); added += 1
                line = next(lines, None)
            assert removed == int(match[2] or 1) and added == int(match[4] or 1)
        out.extend(source[at:]); result[name] = ''.join(out)
        pending = line
    return result


class IndependentControls(unittest.TestCase):
    def test_01_exact_all_input_and_producer_receipt_hashes(self):
        for path, expected in MANIFEST['immutableInputs'].items():
            self.assertEqual(descriptor(ROOT / path), expected)
            self.assertEqual(expected['sha256'], prepare.INPUTS[path])
        for path, expected in MANIFEST['preparationInputs'].items():
            self.assertEqual(descriptor(PRODUCER / path), expected)
        for path, expected in PRODUCER_RECEIPT['files'].items():
            self.assertEqual(descriptor(PRODUCER / path), expected)
        self.assertEqual(sha(canonical(MANIFEST['immutableInputs'])), MANIFEST['inputTreeSHA256'])
        self.assertEqual(sha(canonical(MANIFEST['preparationInputs'])), MANIFEST['preparationTreeSHA256'])
        self.assertEqual(sha(canonical(MANIFEST['preparedSources'])), MANIFEST['preparedSourceTreeSHA256'])
        self.assertEqual(sha(canonical(PRODUCER_RECEIPT['files'])), PRODUCER_RECEIPT['retainedFileTreeSHA256'])

    def test_02_deterministic_artifacts_and_independent_exact_patch(self):
        one = prepare.artifacts(); two = prepare.artifacts()
        self.assertEqual(one, two)
        self.assertEqual(one, ((PRODUCER / 'source.patch').read_bytes(), (PRODUCER / 'prepared.json').read_bytes()))
        self.assertEqual(apply_unified(ORIGINAL, one[0]), CHANGED)
        self.assertEqual(len(CHANGED), 6)
        self.assertEqual(sha(one[0]), MANIFEST['patchSHA256'])
        self.assertEqual(len(one[0]), MANIFEST['patchBytes'])
        for name, value in CHANGED.items():
            self.assertEqual({'sha256': sha(value.encode()), 'bytes': len(value.encode())},
                             {key: MANIFEST['preparedSources'][name][key] for key in ('sha256', 'bytes')})

    def test_03_oracle_full_retained_decision_directly_reexecutes(self):
        observed = oracle.verdict('diagnostic', WITNESS['case'], 'native-keyboard', BEFORE, AFTER, True)
        self.assertEqual(observed, DIRECT_VERDICT)
        self.assertEqual(observed, {key: RETAINED_VERDICT[key] for key in observed})
        self.assertEqual(set(RETAINED_VERDICT) - set(observed), {'actionIndex', 'generation', 'ownedSimulatorIdentity'})
        self.assertIs(observed['passed'], False)
        self.assertEqual([key for key, value in observed['predicates'].items() if value is not True], ['actualNativeFocusTraversal'])
        self.assertEqual((observed['observedFocusBefore'], observed['observedFocusAfter']), ('authored-toggle', None))

    def test_04_favorable_invalid_and_oversize_diagnostics_never_change_direct_oracle(self):
        good = {'schema': diagnostic.SCHEMA, **BINDING, 'authoritative': False,
                'followUp': {'captureStatus': 'complete', 'rows': [{'identifier': 'authored-toggle', 'hasFocus': True}]},
                'keyboardWitness': {'passed': True}, 'verdict': {'passed': True}}
        samples = [good, None, {**good, 'authoritative': True}, {**good, 'generation': True},
                   {**good, 'actionIndex': 999}, {**good, 'padding': 'x' * 4096},
                   {**good, 'value': float('nan')}, {**good, 'value': {1, 2}}]
        original_bytes = canonical(WITNESS)
        for sample in samples:
            saved = []
            body = diagnostic.strip_and_retain({'keyboardWitness': WITNESS, 'focusDiagnostic': sample}, BINDING,
                                                lambda name, value: saved.append((name, value)))
            self.assertEqual(set(body), {'keyboardWitness'})
            self.assertIs(body['keyboardWitness'], WITNESS)
            baseline = copy.deepcopy(BEFORE); baseline['keyboardWitness'] = body['keyboardWitness']
            self.assertEqual(oracle.verdict('diagnostic', WITNESS['case'], 'native-keyboard', baseline, AFTER, True), DIRECT_VERDICT)
            self.assertEqual(saved[0][0], 'focus-diagnostic-1')
            self.assertIs(saved[0][1]['authoritative'], False)
        self.assertEqual(canonical(WITNESS), original_bytes)

    def test_05_storage_failure_cannot_reach_decision_or_progress(self):
        calls = []
        def fail(*args):
            raise OSError('independent controlled storage failure')
        with self.assertRaisesRegex(OSError, 'controlled storage failure'):
            body = diagnostic.strip_and_retain({'keyboardWitness': WITNESS, 'focusDiagnostic': None}, BINDING, fail)
            calls.append(oracle.verdict('diagnostic', WITNESS['case'], 'native-keyboard', body, AFTER, True))
        self.assertEqual(calls, [])

    def test_06_actual_pure_cursor_refuses_after_latched_failure(self):
        cursor = oracle.Cursor(WITNESS['case'])
        for command in ('resume', 'reset'):
            cursor.command(command)
        cursor.check(WITNESS)
        initial = (cursor.acquired, cursor.acquisitions, cursor.phase_index, cursor.complete, cursor.last_after)
        self.assertEqual(initial, (False, 0, 0, False, None))
        # Exact unchanged bridge branch marks failed instead of calling advance.
        self.assertIn("if result['passed'] is True:cursor.advance(w)\n                else:cursor.failed=True", CHANGED[BRIDGE_NAME])
        self.assertIs(DIRECT_VERDICT['passed'], False)
        cursor.failed = True
        with self.assertRaisesRegex(ValueError, 'after completion/failure'):
            cursor.baseline_allowed()
        self.assertEqual((cursor.acquired, cursor.acquisitions, cursor.phase_index, cursor.complete, cursor.last_after), initial)
        composition = (V3 / 'composition.py').read_text()
        self.assertIn("self.current is None or self.current['keyboardCursor'].complete is True", composition)
        self.assertFalse(cursor.complete is True)
        # The composition module is read only, never imported/executed.

    def test_07_strict_oracles_first_tab_keys_semantics_and_completion_preserved(self):
        self.assertFalse(any(name.endswith('/keyboard_oracle.py') for name in CHANGED))
        old, new = ORIGINAL[HARNESS_NAME], CHANGED[HARNESS_NAME]
        self.assertEqual(new[new.index('    private func acquire()'):], old[old.index('    private func acquire()'):])
        self.assertIn('let after = try key("acquire", "tab")', new)
        self.assertEqual([line for line in new.splitlines() if '.typeKey(' in line], [line for line in old.splitlines() if '.typeKey(' in line])
        self.assertIn('guard result["passed"] as? Bool == true else', new)
        addition = ("            if op=='evaluate' and self.current is not None and 'baseline' in self.current:\n"
                    "                body=focus_diagnostic.strip_and_retain(body,{'case':self.current['case'],'generation':self.generation,'actionIndex':self.current['actionIndex']},self.save)\n")
        self.assertEqual(CHANGED[BRIDGE_NAME].replace('import focus_diagnostic as focus_diagnostic\n', '').replace(addition, ''), ORIGINAL[BRIDGE_NAME])

    def test_08_null_outside_anonymous_and_exact_context_truncation(self):
        null = diagnostic.endpoint(None)
        outside = diagnostic.endpoint({'identifier': 'outside', 'class': 'UIView', 'identity': 'outside1', 'frame': {}})
        anonymous = diagnostic.endpoint({'class': 'OtherFocusItem', 'identity': 'anonymous1', 'frame': {}})
        self.assertEqual([null['state'], outside['state'], anonymous['state']], ['null', 'item', 'item'])
        self.assertEqual([diagnostic.endpoint_scope(row) for row in (null, outside, anonymous)], ['explicit-null', 'outside-fixed-ids', 'outside-fixed-ids'])
        trace = diagnostic.ContextBuffer()
        for index in range(259):
            trace.append('controller', None, None, 16, index)
        self.assertEqual((len(trace.entries), trace.dropped, trace.revision), (128, 131, 259))
        self.assertEqual([row['sequence'] for row in trace.entries], list(range(1, 129)))
        swift = CHANGED['source/Prototype/DiagnosticTrace.swift']
        self.assertIn('focusContextEntries.count < 128 else { focusContextDropped += 1; return }', swift)
        self.assertEqual(swift[swift.index('    func append(_ kind:'):], ORIGINAL['source/Prototype/DiagnosticTrace.swift'][ORIGINAL['source/Prototype/DiagnosticTrace.swift'].index('    func append(_ kind:'):])

    def test_09_per_row_timing_and_fixed_authoritative_sample(self):
        harness = CHANGED[HARNESS_NAME]
        self.assertIn('rowTimes.append(["identifier": id, "startedUptime": rowStarted, "finishedUptime": now])', harness)
        self.assertIn('focusDiagnosticObservations.count < 4', harness)
        self.assertIn('else { focusDiagnosticObservationsDropped += 1 }', harness)
        self.assertLess(harness.index('let witness: [String: Any]'), harness.index('let followUp = focusOnlyDiagnostic'))
        self.assertIn('"before": before, "startedUptime": start, "finishedUptime": finished, "after": after]', harness)
        self.assertIn('return ["uptime": observedUptime, "appForeground": foreground, "elements": rows]', harness)
        rows = [{'startedUptime': 1, 'finishedUptime': 3}, {'startedUptime': 4, 'finishedUptime': 7}]
        self.assertEqual(diagnostic.observation_status(rows, 0, 8)['atomic'], False)
        with self.assertRaises(ValueError):
            diagnostic.observation_status(rows, 0, 6)

    def test_10_second_pass_expiry_overrun_and_original_budgets(self):
        reads = []; clock = [5.0]
        def read(identifier):
            reads.append(identifier); clock[0] += .3
            return True
        result = diagnostic.focus_only_once(read, lambda: clock[0], 17)
        self.assertEqual(reads, ['authored-toggle'])
        self.assertEqual(result['deadlineUptime'], 5.25)
        self.assertEqual(result['captureStatus'], 'incomplete-budget')
        self.assertGreater(result['finishedUptime'], result['deadlineUptime'])
        reads.clear()
        result = diagnostic.focus_only_once(reads.append, lambda: 18, 17)
        self.assertEqual(reads, [])
        self.assertEqual(result['captureStatus'], 'incomplete-budget')
        new, old = CHANGED[HARNESS_NAME], ORIGINAL[HARNESS_NAME]
        self.assertIn('focusOnlyDiagnostic((before["uptime"] as! Double) + 12.0)', new)
        self.assertIn('let deadline = min(actionDeadline, started + 0.250)', new)
        self.assertEqual(new[:new.index('    private func rectangle(')], old[:old.index('    private func rectangle(')])
        self.assertFalse(any(name.endswith('/harness.py') or name.endswith('.xctestplan') or name.endswith('.xcscheme') for name in CHANGED))
        self.assertIn('commands.run(argv, timeout=600, check=False)', READ_SOURCE[1].read_text())
        self.assertIn('MAX_BODY = 8192', READ_SOURCE[2].read_text())

    def test_11_no_focus_requests_and_persistence_revision_separate(self):
        for name in ('source/Prototype/main.swift', 'source/Prototype/AuthoredToggleCarrier.swift'):
            for operation in ('setNeedsFocusUpdate()', 'updateFocusIfNeeded()'):
                self.assertEqual(CHANGED[name].count(operation), ORIGINAL[name].count(operation))
            self.assertIn('super.didUpdateFocus(in: context, with: coordinator)\n        DiagnosticTrace.shared.focusContext(', CHANGED[name])
        main = CHANGED['source/Prototype/main.swift']
        for field in ('focusContexts', 'focusContextDropped', 'focusContextRevision'):
            self.assertIn('"' + field + '"', main)
        self.assertIn('lastFocusContextRevision != DiagnosticTrace.shared.focusContextRevision', main)

    def test_12_producer_and_bound_sources_unchanged(self):
        for path, expected in PRE_REVIEW_FILES.items():
            self.assertEqual(descriptor(ROOT / path), expected)
        self.assertEqual(set(EXECUTED_REPOSITORY_CODE), ALLOWED_EXEC)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    global prepare, diagnostic, MANIFEST, PRODUCER_RECEIPT, ORIGINAL, CHANGED
    global WITNESS, BINDING, BEFORE, AFTER, RETAINED_VERDICT, DIRECT_VERDICT, oracle
    global BRIDGE_NAME, HARNESS_NAME, PRE_REVIEW_FILES
    sys.dont_write_bytecode = True
    # Reviewed transitive graph: six oracle source files and three JSON case files.
    audit_rows = {}
    for path in ORACLES:
        tree = ast.parse(path.read_text(), filename=str(path))
        imports = sorted({node.module if isinstance(node, ast.ImportFrom) else alias.name
                          for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                          for alias in (node.names if isinstance(node, ast.Import) else [None])})
        assert all(name in {'importlib.util', 'json', 'math', 'pathlib', 'copy'} for name in imports)
        audit_rows[str(path.relative_to(ROOT))] = {**descriptor(path), 'imports': imports}
    (BASE / 'pure-oracle-source-audit.json').write_bytes(canonical(audit_rows))
    sys.addaudithook(audit)
    sys.path.insert(0, str(PRODUCER))
    import prepare as producer_prepare
    import focus_diagnostic as producer_diagnostic
    import test_diagnostic
    prepare = producer_prepare; diagnostic = producer_diagnostic
    MANIFEST = json.loads((PRODUCER / 'prepared.json').read_bytes())
    PRODUCER_RECEIPT = json.loads((PRODUCER / 'receipt.json').read_bytes())
    PRE_REVIEW_FILES = {str(path.relative_to(ROOT)): descriptor(path) for path in
                       list(PRODUCER.rglob('*')) + ORACLES + CASES + READ_SOURCE
                       + [ROOT / name for name in MANIFEST['immutableInputs']] if path.is_file()}
    producer_output = io.StringIO()
    producer_result = unittest.TextTestRunner(stream=producer_output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_diagnostic))
    (BASE / 'producer-controls.stdout.txt').write_text(producer_output.getvalue())
    assert producer_result.wasSuccessful() and producer_result.testsRun == 17 and not producer_result.skipped
    ORIGINAL, CHANGED = prepare.render()
    HARNESS_NAME = 'harness/UITests/ToggleUITests.swift'
    BRIDGE_NAME = 'runtime/verification/apple-toggle-keyboard-focus/keyboard_bridge.py'
    packet_path = V3 / 'runtime/captures/0001-keyboard-witness-1.json'
    before_path = V3 / 'runtime/captures/0001-before-1.json'
    after_path = V3 / 'runtime/captures/0001-after-1.json'
    for path in (packet_path, before_path, after_path):
        PRE_REVIEW_FILES[str(path.relative_to(ROOT))] = descriptor(path)
    packet = json.loads(packet_path.read_bytes()); WITNESS = packet['witness']
    BINDING = {key: packet['binding'][key] for key in ('case', 'generation', 'actionIndex')}
    BEFORE = json.loads(before_path.read_bytes())['observation']
    BEFORE.update(keyboardWitness=WITNESS, keyboardBinding=packet['binding'])
    after_packet = json.loads(after_path.read_bytes())
    AFTER = after_packet['observation']; RETAINED_VERDICT = after_packet['verdict']
    oracle = load('independent_retained_keyboard_v2', ORACLES[0])
    DIRECT_VERDICT = oracle.verdict('diagnostic', WITNESS['case'], 'native-keyboard', BEFORE, AFTER, True)
    (BASE / 'direct-oracle-verdict.json').write_bytes(canonical(DIRECT_VERDICT))
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls))
    (BASE / 'independent-controls.stdout.txt').write_text(output.getvalue())
    (BASE / 'independent-controls.stderr.txt').write_text('')
    result_files = {str(path.relative_to(BASE)): descriptor(path) for path in BASE.iterdir() if path.is_file() and path.name != 'receipt.json'}
    receipt = {
        'schema': 1, 'scope': 'independent-source-preparation-and-offline-pure-oracle-review',
        'status': 'pass-source-preparation-only' if result.wasSuccessful() else 'failed-independent-review',
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': '/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-toggle-keyboard-focus-diagnostic-v1-independent-review/review.py',
        'tool': {'executable': sys.executable, 'version': sys.version}, 'cwd': str(pathlib.Path.cwd()),
        'inheritedSourceRevisionLabel': MANIFEST['inheritedReviewRevisionLabel'], 'gitQueried': False,
        'inputTreeSHA256': MANIFEST['inputTreeSHA256'], 'preparedSourceTreeSHA256': MANIFEST['preparedSourceTreeSHA256'],
        'patchSHA256': MANIFEST['patchSHA256'], 'patchBytes': MANIFEST['patchBytes'],
        'producerControls': {'testsRun': producer_result.testsRun, 'failures': len(producer_result.failures), 'errors': len(producer_result.errors), 'skipped': len(producer_result.skipped)},
        'independentControls': {'testsRun': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped)},
        'retainedOracleDirectlyEvaluated': True, 'retainedOracleExactComparison': 'all oracle fields equal; only original bridge actionIndex/generation/ownedSimulatorIdentity are excluded',
        'directOracleFailedPredicates': [key for key, value in DIRECT_VERDICT['predicates'].items() if value is not True],
        'repositoryCodeExecuted': sorted(str(path.relative_to(ROOT)) for path in EXECUTED_REPOSITORY_CODE),
        'sourceBindings': PRE_REVIEW_FILES, 'reviewedSourceTreeSHA256': sha(canonical(PRE_REVIEW_FILES)),
        'outputFiles': result_files, 'outputTreeSHA256': sha(canonical(result_files)),
        'reviewDocument': descriptor(ROOT / 'docs/apple-toggle-keyboard-focus-diagnostic-v1-independent-review.md'),
        'producerOrOriginalFilesWritten': False, 'authorityDriverOrSelectedHarnessRuntimeImported': False,
        'nativeCompilerBuildSimulatorDeviceProcessInventoryNetworkServerUICaptureGitExecuted': False,
        'runtimeSelected': False, 'acceptanceGranted': False,
        'limitations': [
            'Only reviewed pure retained oracle modules are executed from retained inputs; bridge/composition/harness are source only.',
            'Actual pure cursor checks are exercised; failure latch follows the byte-identical bridge branch by explicit host assignment. Next-begin refusal is source-verified, not composition execution.',
            'Swift remains uncompiled; public UIKit/XCTest runtime behavior and timing interference are unverified.',
            'Synchronous XCUI reads may overrun admission deadline; late return is incomplete-budget and stops further rows. No hard wall-clock bound is proved.',
            'Full app AX hierarchy inventory is absent in this compact derivative; endpoint hooks and three fixed-ID follow-up are its observation scope.',
            'Original budgets and failed first-Tab verdict remain unchanged. Command finalization instrumentation is separately pending.',
            'No build/native/carrier/OTA/published-package dogfood/store/operational/physical-phone/GA acceptance.'
        ]}
    (BASE / 'receipt.json').write_bytes(canonical(receipt))
    print(output.getvalue(), end='')
    print('Producer controls: 17 passed; independent controls: ' + str(result.testsRun))
    print('Direct retained oracle: passed=' + str(DIRECT_VERDICT['passed']) + '; false=' + ','.join(receipt['directOracleFailedPredicates']))
    print('Receipt: ' + str(BASE / 'receipt.json'))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
