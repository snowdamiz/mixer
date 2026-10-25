#!/usr/bin/env python3
"""File-only V2 review: replay the frozen 74-control reviewer, then JSON edges."""
import copy
import datetime
import difflib
import importlib.util
import json
import math
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
V1 = ROOT / 'verification/apple-focus-reference-diagnostic-v1'
PRIOR = ROOT / 'verification/apple-focus-reference-diagnostic-v1-independent-review'
V2 = ROOT / 'verification/apple-focus-reference-diagnostic-v2'
EXPECTED_V2 = '07776c2af95bcc58e126b4ceb0f0dee39dec1138ea96bc9e33bc8a4a0393a3a0'
CONTROLS = []


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prior = load('frozen_v1_independent_reviewer', PRIOR / 'review.py')
stable, row, digest = prior.stable, prior.row, prior.digest


def check(name, condition, detail=None):
    item = {'name': name, 'passed': condition is True}
    if detail is not None:
        item['detail'] = detail
    CONTROLS.append(item)
    print(('PASS ' if item['passed'] else 'FAIL ') + name, flush=True)


def main():
    assert not (BASE / 'receipt.json').exists(), 'Retain previous V2 independent review'
    v2_handoff = json.loads((V2 / 'handoff.json').read_bytes())
    check('v2-frozen-identity', row(V2 / 'handoff.json')['sha256'] == EXPECTED_V2)
    check('v2-all-frozen-members-and-tree', all(row(ROOT / name) == value for name, value in v2_handoff['members'].items())
          and digest(stable(v2_handoff['members'])) == v2_handoff['memberTreeSHA256'])
    for name, expected in [('apple-focus-reference-diagnostic-v1', prior.EXPECTED_HANDOFF),
                           ('apple-focus-reference-diagnostic-v1-independent-review', 'd70da20d45323be52138a6efdbd2d53c74efbd521620584b228bf9f03e3eedbb')]:
        path = ROOT / 'verification' / name / 'handoff.json'
        handoff = json.loads(path.read_bytes())
        check(name + '-historical-members-unchanged', row(path)['sha256'] == expected
              and all(row(ROOT / member) == value for member, value in handoff['members'].items())
              and digest(stable(handoff['members'])) == handoff['memberTreeSHA256'])
    for filename, patch in [('reference_contract.py', 'classifier.patch'), ('test_reference.py', 'tests.patch')]:
        original, repaired = (V1 / filename).read_text(), (V2 / filename).read_text()
        expected = ''.join(difflib.unified_diff(original.splitlines(True), repaired.splitlines(True),
                       fromfile='a/verification/apple-focus-reference-diagnostic-v1/' + filename,
                       tofile='b/verification/apple-focus-reference-diagnostic-v2/' + filename))
        check('exact-' + patch, (V2 / patch).read_text() == expected)
    old_tests = (V1 / 'test_reference.py').read_text().split("\n\nif __name__ == '__main__': unittest.main()", 1)[0]
    new_tests = (V2 / 'test_reference.py').read_text().split('\n    def reject_frozen_counterexample', 1)[0]
    check('original-26-tests-preserved-only-two-read-path-adaptations',
          new_tests.rstrip() == old_tests.replace("prepare.BASE / 'accepted-sources.tar.gz'", "prepare.SOURCES_BASE / 'accepted-sources.tar.gz'").rstrip())
    producer_receipt = json.loads((V2 / 'host-attempt-1/receipt.json').read_bytes())
    check('producer-34-host-controls-source-output-bindings', producer_receipt['passed'] is True
          and (producer_receipt['testsRun'], producer_receipt['failures'], producer_receipt['errors'], producer_receipt['skipped']) == (34, 0, 0, 0)
          and all(row(V2 / name) == item for name, item in producer_receipt['ownedSources'].items())
          and all(row(V2 / 'host-attempt-1' / name) == item for name, item in producer_receipt['outputs'].items()))
    check('classifier-is-host-only-consistency-repair', v2_handoff['sourceOverlayChanged'] is False
          and v2_handoff['compileRerun'] is False and v2_handoff['selectedRunProvenanceImporterPresent'] is False
          and v2_handoff['nativeExecuted'] is False and v2_handoff['runnablePacketAssembled'] is False)
    freeze = subprocess.run([sys.executable, '-B', str(V2 / 'freeze.py'), 'verify', '--attempt', '1'], cwd=ROOT, capture_output=True, check=False)
    (BASE / 'v2-freeze-verify.stdout.log').write_bytes(freeze.stdout)
    (BASE / 'v2-freeze-verify.stderr.log').write_bytes(freeze.stderr)
    check('v2-file-only-freeze-verification', freeze.returncode == 0, freeze.stdout.decode().strip())

    # Run exactly the frozen earlier reviewer. Its only changed dependency is the
    # pure classifier path; reviewer-owned outputs are redirected to this lane.
    original_loader = prior.load
    redirects = []

    def classifier_loader(name, path):
        if name == 'reviewed_reference_contract':
            assert path == V1 / 'reference_contract.py'
            redirects.append({'original': str(path.relative_to(ROOT)), 'replacement': str((V2 / 'reference_contract.py').relative_to(ROOT)),
                              'originalBinding': row(path), 'replacementBinding': row(V2 / 'reference_contract.py')})
            return original_loader(name, V2 / 'reference_contract.py')
        return original_loader(name, path)

    prior.BASE = BASE
    prior.load = classifier_loader
    replay_exit = prior.main()
    replay = json.loads((BASE / 'receipt.json').read_bytes())
    replay['harnessInternalCommand'] = replay['command']
    replay['command'] = [sys.executable, '-B', str(Path(__file__).resolve())]
    replay['harnessReuse'] = {'source': str((PRIOR / 'review.py').relative_to(ROOT)), 'sourceBinding': row(PRIOR / 'review.py'),
                            'dependencyRedirects': redirects, 'controlSourceUnchanged': True,
                            'outputDirectoryRedirected': str(BASE.relative_to(ROOT))}
    replay['outputs'] = {name: row(BASE / name) for name in ['freeze-verify.stdout.log', 'freeze-verify.stderr.log',
                                                           'original-failure-replay.json', 'counterexamples.json']}
    (BASE / 'earlier-74-controls-receipt.json').write_bytes(stable(replay))
    (BASE / 'receipt.json').unlink()
    check('exact-earlier-74-controls-pass-with-v2-classifier', replay_exit == 0 and replay['controlsRun'] == replay['controlsPassed'] == 74
          and replay['failedControls'] == [] and len(redirects) == 1)
    check('original-seven-accepted-verdict-regressions-now-all-reject', all(c['passed'] is True for c in replay['controls']
          if c['name'].startswith(('exact-original-verdict-rejects-', 'runtime-reporting-'))))
    contract = load('independent_v2_contract_edges', V2 / 'reference_contract.py')
    equality_cases = [
        ('null', None, None, True), ('bool', True, True, True), ('int', 1, 1, True), ('float', 1.0, 1.0, True),
        ('string', 'focus', 'focus', True), ('empty-object', {}, {}, True), ('empty-array', [], [], True),
        ('object-order-insensitive', {'a': 1, 'b': [None, False]}, {'b': [None, False], 'a': 1}, True),
        ('nested-types-preserved', {'a': [1, True, 1.0, None]}, {'a': [1, True, 1.0, None]}, True),
        ('bool-vs-int', True, 1, False), ('false-vs-zero', False, 0, False), ('int-vs-float', 1, 1.0, False),
        ('negative-zero-int-type', -0.0, 0, False), ('different-integers', 1, 2, False), ('different-strings', '1', '01', False),
        ('list-order', [1, 2], [2, 1], False), ('list-length', [1], [1, 1], False),
        ('object-extra-member', {'a': 1}, {'a': 1, 'b': 2}, False), ('object-renamed-member', {'a': 1}, {'b': 1}, False),
        ('nested-int-float', {'a': [1]}, {'a': [1.0]}, False), ('integer-object-key', {1: 'a'}, {1: 'a'}, False),
        ('boolean-object-key', {True: 'a'}, {True: 'a'}, False), ('tuple-not-json', (1,), (1,), False),
        ('set-not-json', {1}, {1}, False), ('bytes-not-json', b'a', b'a', False),
        ('nan-not-json', float('nan'), float('nan'), False), ('positive-infinity-not-json', float('inf'), float('inf'), False),
        ('negative-infinity-not-json', float('-inf'), float('-inf'), False),
        ('nested-nan-not-json', {'a': [float('nan')]}, {'a': [float('nan')]}, False),
    ]
    for name, left, right, expected in equality_cases:
        check('strict-json-' + name, contract.strict_json_equal(left, right) is expected)
    selected_manifest = json.loads((prior.OLD / 'selected-runtime-source-manifest.json').read_bytes())
    selected = prior.archive(prior.OLD / 'selected-runtime-sources.tar.gz', selected_manifest['files'], 'selected/')
    prepared = json.loads((V1 / 'prepared.json').read_bytes())
    frozen = json.loads((PRIOR / 'counterexamples.json').read_bytes())
    exact_regressions = []
    with tempfile.TemporaryDirectory(prefix='v2-edge-oracle-', dir=BASE) as temporary:
        pure = Path(temporary)
        for name in prepared['pureOracleClosure']:
            path = pure / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(selected[name])
        oracle = load('v2_edge_pure_oracle', pure / 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py')
        check('edge-oracle-exact-nine-files-only', len([path for path in pure.rglob('*') if path.is_file()]) == 9)
        for example in frozen['examples']:
            outcome = contract.result(example['premises'], example['verdicts'], oracle, example['observations'])
            exact_regressions.append({'name': example['name'], 'syntheticOnly': True, 'outcome': outcome})
        check('seven-exact-frozen-counterexample-triples-rejected', len(exact_regressions) == 7
              and all(x['outcome']['status'] == 'invalid-or-incomplete-evidence'
                      and x['outcome']['singleTabDiagnosticEvidencePassed'] is False
                      and x['outcome']['keyInjectionCount'] is None for x in exact_regressions))
        # Repair the single mutated field in the first frozen synthetic triple to
        # reuse its independently assembled consistent positive fixture.
        prototype = copy.deepcopy(frozen['examples'][0])
        prototype['verdicts'][0]['originalOraclePassed'] = True

        def fixture():
            source = copy.deepcopy(prototype)
            return source['premises'][0], source['verdicts'][0], source['observations'][0]

        def outcome(p, v, pair):
            return contract.result([p], [v], oracle, [pair])

        p, v, pair = fixture()
        check('reconstructed-synthetic-fixture-consistent-only', outcome(p, v, pair)['singleTabDiagnosticEvidencePassed'] is True)
        edge_outcomes = []
        mutations = [
            ('nan-premise-time', lambda p, v, pair: p['before'].update(uptime=float('nan'))),
            ('infinite-premise-time', lambda p, v, pair: p['before'].update(uptime=float('inf'))),
            ('huge-premise-time', lambda p, v, pair: p['before'].update(uptime=10 ** 1000)),
            ('huge-premise-frame', lambda p, v, pair: p['before']['elements']['authored-toggle']['frame'].update(x=10 ** 1000)),
            ('outer-generation-bool', lambda p, v, pair: v.update(generation=True)),
            ('outer-action-index-bool', lambda p, v, pair: v.update(actionIndex=True)),
            ('outer-generation-string', lambda p, v, pair: v.update(generation='1')),
            ('outer-action-index-null', lambda p, v, pair: v.update(actionIndex=None)),
            ('predicates-integer-not-bool', lambda p, v, pair: v['predicates'].update(pairedNativeFocusBefore=1)),
            ('nonfinite-unexpected-verdict-member', lambda p, v, pair: v.update(unexpected=float('inf'))),
            ('negative-injection-count', lambda p, v, pair: p.update(actionInjectionCount=-1)),
            ('bool-generation-premise', lambda p, v, pair: p.update(generation=True)),
            ('float-action-index-premise', lambda p, v, pair: p.update(actionIndex=1.0)),
        ]
        for name, mutate in mutations:
            p, v, pair = fixture(); mutate(p, v, pair)
            result = outcome(p, v, pair)
            edge_outcomes.append({'name': name, 'syntheticOnly': True,
                                  'outcome': {key: result.get(key) for key in ['status', 'failure', 'singleTabDiagnosticEvidencePassed', 'keyInjectionCount', 'returnedPublicKeyWitnessCount']}})
            check('structured-rejection-' + name, result['status'] == 'invalid-or-incomplete-evidence'
                  and result['singleTabDiagnosticEvidencePassed'] is False and result['keyInjectionCount'] is None, result.get('failure'))
        p, v, pair = fixture()
        frame = p['before']['elements']['authored-toggle']['frame']
        dimension = next(name for name, value in frame.items() if type(value) is int)
        frame[dimension] = float(frame[dimension])
        result = outcome(p, v, pair)
        check('premise-before-int-float-representation-mismatch-rejected', result['status'] == 'invalid-or-incomplete-evidence')
        p, v, pair = fixture()
        deep = []; current = deep
        for _ in range(1500):
            child = []; current.append(child); current = child
        v['unexpectedNestedValue'] = deep
        result = outcome(p, v, pair)
        deep_result = {key: result.get(key) for key in ['status', 'failure', 'singleTabDiagnosticEvidencePassed', 'keyInjectionCount']}
        check('deep-complete-verdict-structured-recursion-rejection', result['status'] == 'invalid-or-incomplete-evidence'
              and result.get('failure', '').startswith('RecursionError:') and result['singleTabDiagnosticEvidencePassed'] is False)
        p, v, pair = fixture()
        # Exact JSON semantics permit object key reordering; this is not byte
        # serialization provenance, which belongs to the future importer.
        v = dict(reversed(list(v.items())))
        result = outcome(p, v, pair)
        check('valid-verdict-object-key-order-does-not-change-consistency', result['singleTabDiagnosticEvidencePassed'] is True)
        result2 = outcome(copy.deepcopy(p), copy.deepcopy(v), copy.deepcopy(pair))
        check('same-consistent-data-does-not-claim-native-provenance', result2['singleTabDiagnosticEvidencePassed'] is True
              and all(result2[k] is False for k in ['completeCaseSet', 'cursorCompletionCredit', 'runPassed', 'fullSixCaseQualification',
                                                   'nativeKeyboardQualification', 'carrierAccepted', 'gaAccepted']))
        (BASE / 'strict-json-edge-outcomes.json').write_bytes(stable({'syntheticOnly': True, 'rejections': edge_outcomes,
            'deepValueRejection': deep_result,
            'provenanceMeaning': 'Internal consistency only; all fixtures are synthetic.'}))
    (BASE / 'exact-frozen-regression-outcomes.json').write_bytes(stable({'syntheticOnly': True, 'frozenSource': row(PRIOR / 'counterexamples.json'),
                                                                      'outcomes': exact_regressions}))
    check('all-review-owned-scratch-retired', not any(path.is_dir() for path in BASE.iterdir()))
    check('v2-and-both-predecessors-unchanged-after-controls', row(V2 / 'handoff.json')['sha256'] == EXPECTED_V2
          and all(row(ROOT / name) == value for name, value in v2_handoff['members'].items())
          and row(V1 / 'handoff.json')['sha256'] == prior.EXPECTED_HANDOFF
          and row(PRIOR / 'handoff.json')['sha256'] == 'd70da20d45323be52138a6efdbd2d53c74efbd521620584b228bf9f03e3eedbb')
    failed = [control['name'] for control in CONTROLS if not control['passed']]
    receipt = {'schema': 'mixer.apple-focus-reference-v2-independent-review.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'command': [sys.executable, '-B', str(Path(__file__).resolve())], 'cwd': str(ROOT), 'python': sys.version,
               'pythonExecutable': str(Path(sys.executable).resolve()), 'platform': platform.platform(),
               'reviewedV2HandoffSHA256': EXPECTED_V2, 'predecessorReviewHandoffSHA256': 'd70da20d45323be52138a6efdbd2d53c74efbd521620584b228bf9f03e3eedbb',
               'sourceRevisionLabel': producer_receipt['sourceRevisionLabel'], 'sourceRevisionMeaning': 'Inherited historical label; exact hashes identify review.',
               'replayedEarlierControls': 74, 'replayedEarlierControlsPassed': replay['controlsPassed'],
               'additionalControlsRun': len(CONTROLS), 'additionalControlsPassed': len(CONTROLS) - len(failed), 'controls': CONTROLS,
               'totalControlsRun': 74 + len(CONTROLS), 'totalControlsPassed': replay['controlsPassed'] + len(CONTROLS) - len(failed),
               'failedControls': failed + replay['failedControls'], 'passed': not failed and not replay['failedControls'],
               'disposition': 'classifier-consistency-repair-verified-selected-run-provenance-separate',
               'selectedRunProvenanceImporterPresent': False, 'runtimeSelected': False, 'nativeExecuted': False,
               'compileRerun': False, 'gitCommands': 0, 'nativeInstancesQueried': 0, 'servicesStarted': 0, 'uiOrCapturePerformed': False,
               'hostedAuthorityOrCatalogImported': False, 'physicalPhones': 'disconnected-deferred',
               'completeCaseSet': False, 'runPassed': False, 'gaAccepted': False,
               'sourceAndProductReuse': producer_receipt['sourceAndProductReuse'],
               'reviewSources': {'review.py': row(Path(__file__).resolve()), 'prior74ControlHarness': row(PRIOR / 'review.py')},
               'cleanup': {'ownedPureOracleScratchAbsent': True},
               'outputs': {path.name: row(path) for path in sorted(BASE.iterdir()) if path.is_file() and path.name not in ['receipt.json', 'review.py', 'review.stdout.log', 'review.stderr.log']}}
    (BASE / 'receipt.json').write_bytes(stable(receipt))
    print(json.dumps({k: receipt[k] for k in ['passed', 'replayedEarlierControls', 'additionalControlsRun', 'totalControlsRun', 'totalControlsPassed', 'failedControls', 'nativeExecuted']}, sort_keys=True))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
