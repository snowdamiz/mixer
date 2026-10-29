#!/usr/bin/env python3
"""Freeze a lean correction packet after retained guarded controls pass."""
import offline
offline.install()
import json
from pathlib import Path
import sys
import verify

HERE = Path(__file__).resolve().parent
assert not (HERE / 'seal.json').exists(), 'Refuse replacing a sealed packet'
attempts = sorted((HERE / 'local').glob('replay-attempt-*.json'))
assert attempts
latest = json.loads(attempts[-1].read_text())
assert latest['checks'] == latest['passed'] == 81 and latest['failures'] == 0
assert not latest['liveApiAttempts'] and not latest['scratchRemaining'] and latest['subjectRuntimeRuns'] == 0
assert latest['proposedHarnessSHA256'] == verify.row(HERE / 'admit.py')['sha256']
scope = json.loads((HERE / 'source-scope.json').read_text())
source_check = verify.check(sealed=False)
records = {r['name']: r for r in latest['controls']}
accepted = records['actual-corrected-parser-accepts-all-699']['result']
rejection = records['actual-original-parser-refusal-retained']['result']
assert accepted['groups'] == 37 and accepted['passed'] == accepted['terminals'] == 699
assert all(v == 1 for v in accepted['oracleCounts'].values()) and rejection['refused']
history = []
for path in attempts:
    value = json.loads(path.read_text())
    history.append({'path': str(path.relative_to(HERE)), **verify.row(path), 'checks': value['checks'],
                    'passed': value['passed'], 'failures': value['failures'], 'liveApiAttempts': value['liveApiAttempts'],
                    'failedControls': [r for r in value['controls'] if not r['passed']],
                    'proposedHarnessSHA256': value['proposedHarnessSHA256']})
receipt = {
    'schema': 1, 'status': 'source-only-parser-correction-proposal', 'actualRun': 40824584975,
    'actualHead': latest['sourceRevision'], 'actualTree': latest['sourceTree'],
    'actualArtifact': {'id': 12876267544, 'bytes': 487958, 'sha256': 'fdd1b83987eb3ecde7912814f27d9cd18d1f35d68d757eadc01b5d75f925810c'},
    'originalHarnessSHA256': scope['originalHarnessSHA256'], 'proposedHarness': verify.row(HERE / 'admit.py'),
    'parserFunctionFile': verify.row(HERE / 'parser_function.py'), 'oldFunction': scope['oldFunction'], 'newFunction': scope['newFunction'],
    'changedTopLevelDefinitions': ['test_evidence'], 'outsideFunctionASTByteIdentical': True,
    'boundedCommandsByteIdentical': True, 'sourceCheck': source_check,
    'actualDebug': {'stdout': latest['actualStdout'], 'exit': latest['actualCommandExit'], 'elapsedSeconds': latest['actualCommandElapsedSeconds'],
                    'oldSingleTokenTerminals': 682, 'spacedDoctests': 11, 'serializedSplitTerminals': 6,
                    'correctedReplay': accepted, 'originalParserRefusal': rejection},
    'controls': {'checks': 81, 'passed': 81, 'failed': 0, 'actualCorruptionRefusals': 53,
                 'focusedGrammarPositives': 10, 'focusedGrammarRefusals': 13,
                 'nonzeroExit101MockRefusedBeforeParser': records['nonzero-command-exit-refused-before-parser']['result'],
                 'latestLocalReplay': {'path': str(attempts[-1].relative_to(HERE)), **verify.row(attempts[-1])}},
    'draftReplayHistoryRetained': history,
    'setupFailuresRetained': [{'path': str(p.relative_to(HERE)), **verify.row(p)} for p in sorted((HERE / 'local').glob('setup-failure-*.json'))],
    'setupCleanupRetained': {'path': 'local/setup-cleanup.json', **verify.row(HERE / 'local/setup-cleanup.json')},
    'commands': ['python3 -B verification/swift-pin-bitmap-terminal-parser-correction/prepare.py',
                 'python3 -B verification/swift-pin-bitmap-terminal-parser-correction/replay.py',
                 'python3 -B verification/swift-pin-bitmap-terminal-parser-correction/freeze.py',
                 'python3 -B verification/swift-pin-bitmap-terminal-parser-correction/verify.py'],
    'pythonVersion': sys.version, 'guardBeforeSubjectImports': True, 'realNestedProcessSessionGroupSignalTimerWaitSocketCalls': 0,
    'latestLiveApiAttempts': [], 'subjectRuntimeRuns': 0, 'newDebugOrReleaseRuns': 0,
    'originalHostStatusUnchanged': 'failed', 'actualReleaseStarted': False,
    'rawAndReplayOutputsIgnored': True, 'scratchRemaining': [], 'otherProcessesProbedOrSignalled': False,
    'scope': 'Evidence parser only. Actual Debug replay is not a new hosted admission and does not run Release; native/UI/device/customer/GA gates remain pending.'}
(HERE / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
files = {name: verify.row(HERE / name) for name in sorted(verify.MEMBERS)}
seal = {'schema': 1, 'files': files, 'treeSHA256': verify.tree(files)}
(HERE / 'seal.json').write_text(json.dumps(seal, sort_keys=True, indent=2) + '\n')
assert verify.check()['sealed'] and not offline.ATTEMPTS
print(json.dumps({'members': len(files), 'seal': verify.row(HERE / 'seal.json'), 'treeSHA256': seal['treeSHA256'],
                  'parserFunctionFile': receipt['parserFunctionFile'], 'newFunction': receipt['newFunction'],
                  'proposedHarness': receipt['proposedHarness'], 'controls': 81, 'runtimeRuns': 0}, sort_keys=True))
