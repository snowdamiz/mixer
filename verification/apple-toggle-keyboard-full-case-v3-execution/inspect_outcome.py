#!/usr/bin/env python3
"""Inspect retained official results and replay strict cursors without native work."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PREP = ROOT / 'verification/apple-toggle-keyboard-full-case-preparation-v3'
RUNTIME = PREP / 'runtime'
METHODS = ['test000PublicSettingsFullKeyboardAccess', 'test010EnabledFromOff', 'test020EnabledFromOn',
           'test030StaleFromOff', 'test040StaleFromOn', 'test050DisabledFromOff', 'test060DisabledFromOn']
CLEANUPS = ['loopback-server-shutdown', 'loopback-server-close', 'loopback-thread-join',
            'ephemeral-capability-workspace-removal', 'owned-simulator-and-baseline-reconciliation']


def read(path):
    return json.loads(path.read_bytes())


def audit(event, args):
    if event.startswith(('subprocess.', 'os.exec', 'os.spawn', 'os.posix_spawn')) or event in ['os.system', 'os.fork', 'socket.connect', 'socket.bind']:
        raise RuntimeError('Native/process/network boundary forbidden during outcome inspection: ' + event)


def main():
    sys.addaudithook(audit)
    invocation = read(BASE / 'invocation-receipt.json')
    verdict_path = RUNTIME / 'runtime-verdict.json'
    verdict = read(verdict_path) if verdict_path.is_file() else None
    official = []
    def visit(value):
        if isinstance(value, dict):
            if value.get('nodeType') == 'Test Case':
                official.append(dict(identifier=value.get('nodeIdentifier'), result=value.get('result')))
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)
    tests_path = RUNTIME / 'xctest-tests.json'
    if tests_path.is_file():
        visit(read(tests_path))
    summary_path = RUNTIME / 'xctest-summary.json'
    summary = read(summary_path) if summary_path.is_file() else None
    found = {method: [row['result'] for row in official if row['identifier'] in [f'ToggleUITests/{method}()', f'ToggleUITests/{method}', f'MixerToggleUITests/ToggleUITests/{method}()']] for method in METHODS}
    exact_official = len(official) == 7 and all(rows == ['Passed'] for rows in found.values()) and summary is not None and summary.get('result') == 'Passed' and summary.get('totalTestCount') == summary.get('passedTests') == 7 and all(summary.get(k) == 0 for k in ['failedTests', 'skippedTests', 'expectedFailures'])
    cursors = []
    captures = RUNTIME / 'captures'
    begins = sorted(captures.glob('*-begin.json')) if captures.is_dir() else []
    if begins:
        # Only immutable, selected, pure evidence rules are loaded. No harness,
        # composition, orchestration or authority-driver module is imported.
        for name, expected in read(PREP / 'runtime-selection.json')['files'].items():
            if hashlib.sha256((PREP / name).read_bytes()).hexdigest() != expected:
                raise ValueError('Selected replay input changed: ' + name)
        path = PREP / 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py'
        spec = importlib.util.spec_from_file_location('_mixer_execution_cursor_replay', path)
        oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oracle)
        for begin_path in begins:
            begin = read(begin_path)
            generation = begin['generation']
            prefix = f'{generation:04d}-'
            cursor = oracle.Cursor(begin['case'])
            commands = {read(p)['commandGeneration']: read(p)['command'] for p in captures.glob(prefix + 'command-*.json')}
            witnesses = sorted(captures.glob(prefix + 'keyboard-witness-*.json'), key=lambda p: read(p)['binding']['actionIndex'])
            replay = []
            for witness_path in witnesses:
                value = read(witness_path)
                binding, witness = value['binding'], value['witness']
                index = binding['actionIndex']
                before = read(captures / (prefix + f'before-{index}.json'))
                while len(cursor.done_commands) < before['commandGeneration']:
                    cursor.command(commands[len(cursor.done_commands) + 1])
                oracle.witness(witness, binding)
                cursor.check(witness)
                after_path = captures / (prefix + f'after-{index}.json')
                if not after_path.is_file():
                    replay.append(dict(actionIndex=index, phase=witness['phase'], nativeVerdictAvailable=False, complete=False))
                    break
                after = read(after_path)
                baseline = copy.deepcopy(before['observation'])
                baseline.update(keyboardWitness=witness, keyboardBinding=binding)
                replayed = oracle.verdict(begin['candidate'], begin['case'], 'native-keyboard', baseline, after['observation'], before['signature'] != after['signature'])
                retained = after['verdict']
                if replayed['passed'] != retained['passed'] or replayed['predicates'] != retained['predicates']:
                    raise ValueError('Retained native verdict differs from exact selected oracle replay')
                if retained['passed'] is True:
                    cursor.advance(witness)
                else:
                    cursor.failed = True
                replay.append(dict(actionIndex=index, phase=witness['phase'], nativeVerdictAvailable=True,
                    passed=retained['passed'], failedPredicates=[k for k, v in retained['predicates'].items() if v is not True],
                    observedFocusBefore=retained.get('observedFocusBefore'), observedFocusAfter=retained.get('observedFocusAfter'),
                    exactSelectedOracleReplayMatched=True))
            cursors.append(dict(case=cursor.name, generation=generation, complete=cursor.complete, failed=cursor.failed,
                acquired=cursor.acquired, acquisitionSteps=cursor.acquisitions, phaseIndex=cursor.phase_index,
                commands=cursor.done_commands, replayedNativeActions=replay,
                scope='Reconstruction from actual immutable begin, command, baseline, witness and verdict files using exact selected Cursor/oracle definitions'))
    life_path = RUNTIME / 'lifecycle.json'
    lifecycle = read(life_path) if life_path.is_file() else None
    cleanup = [] if lifecycle is None else lifecycle.get('cleanupResults', [])
    all_cleanup = len(cleanup) == 5 and [row['resource'] for row in cleanup] == CLEANUPS and all(row['passed'] is True for row in cleanup)
    command_path = RUNTIME / 'commands.json'
    native_commands = []
    if command_path.is_file():
        for row in read(command_path):
            argv = row.get('argv', [])
            if len(argv) > 1 and argv[0] == '/Applications/Xcode_26.6.app/Contents/Developer/usr/bin/xcodebuild' and argv[1] == 'test-without-building':
                native_commands.append({k:row.get(k) for k in ['kind', 'argv', 'exitCode', 'failureType', 'elapsedSeconds']})
    actual_selection = [] if len(native_commands) != 1 else [arg.removeprefix('-only-testing:MixerToggleUITests/ToggleUITests/') for arg in native_commands[0]['argv'] if arg.startswith('-only-testing:')]
    exception_path = BASE / 'original-exception.json'
    exception = read(exception_path) if exception_path.is_file() else None
    value = dict(schema=1, sourceRevision='50f70a798fea43e1e77b1d95faa1bbda3fc029e0',
        nativeOutcome='passed' if invocation['returnedNormally'] and verdict is not None and verdict.get('runPassed') is True else 'failed',
        nativeInvocationCount=invocation['nativeInvocationCount'], xcodebuildExitCode=None if verdict is None else verdict['xcodebuildExitCode'],
        actualNativeTestCommands=native_commands, exactNativeMethodSelection=actual_selection == METHODS,
        originalException=exception, expectedMethods=METHODS, actualOfficialMethods=official,
        officialMethodResults=found, exactOfficialSevenMethodsPassed=exact_official,
        officialSummary=None if summary is None else {k:summary.get(k) for k in ['result', 'totalTestCount', 'passedTests', 'failedTests', 'skippedTests', 'expectedFailures']},
        actualCursors=cursors, actualCursorCount=len(cursors), strictCompletedCursorCount=sum(c['complete'] is True and c['failed'] is False for c in cursors),
        bridgeFailures=[] if verdict is None else verdict.get('bridgeFailures'),
        reportedCompleteCaseSet=False if verdict is None else verdict.get('completeCaseSet'),
        dependentCasesUnrun=None if verdict is None else verdict.get('dependentCasesUnrun'),
        publicSettingsSetupObservedPassed=False if verdict is None else verdict.get('publicSettingsSetupObservedPassed'),
        allFiveCleanupPassed=all_cleanup, cleanupResults=cleanup,
        lifecycleReconciliation=None if lifecycle is None else {k:lifecycle.get(k) for k in ['ownedSimulator', 'ownedDeviceAbsent', 'ephemeralWorkspaceAbsent', 'nativeDeviceCleanupPassed', 'baselineStatesPreserved', 'beforeFrontends', 'afterFrontends', 'cleanedUp']},
        nativeRerun=False, runtimeOutputRequiredAfterPreflightFailure=False,
        physicalPhones='disconnected-deferred', nativeAcceptancePending=True, carrierAccepted=False, gaAccepted=False)
    with (BASE / 'outcome-inspection.json').open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({k:value[k] for k in ['nativeOutcome', 'xcodebuildExitCode', 'actualCursorCount', 'strictCompletedCursorCount', 'exactOfficialSevenMethodsPassed', 'allFiveCleanupPassed']}, sort_keys=True))


if __name__ == '__main__':
    main()
