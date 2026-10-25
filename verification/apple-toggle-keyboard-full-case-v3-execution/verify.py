#!/usr/bin/env python3
"""Read-only execution evidence verification; never imports/reruns native code."""
import hashlib
import json
import os
import pathlib
import stat
import sys

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
RUNTIME = ROOT / 'verification/apple-toggle-keyboard-full-case-preparation-v3/runtime'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def record(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink(), 'Expected regular evidence file: ' + str(path))
    return dict(sha256=sha(path), bytes=info.st_size, mode=stat.S_IMODE(info.st_mode))


def verify(expected_seal):
    seal_path = BASE / 'packet-seal.json'
    require(sha(seal_path) == expected_seal, 'Exact execution seal changed')
    seal = read(seal_path)
    require(seal['schema'] == 'mixer.apple-toggle.keyboard-full-case-v3-execution.1', 'Wrong execution seal schema')
    for name, expected in seal['files'].items():
        require(record(ROOT / name) == expected, 'Sealed execution evidence changed: ' + name)
    before, after = read(BASE / 'inputs-before.json'), read(BASE / 'inputs-after.json')
    require(before == after, 'Bound selected input changed during execution')
    for name, expected in after.items():
        path = pathlib.Path(name) if name.startswith('/') else ROOT / name
        info = path.lstat()
        if expected['kind'] == 'file':
            actual = dict(kind='file', **record(path))
        elif expected['kind'] == 'symlink':
            require(stat.S_ISLNK(info.st_mode), 'Bound symlink type changed')
            actual = dict(kind='symlink', target=os.readlink(path), mode=stat.S_IMODE(info.st_mode))
        else:
            require(stat.S_ISDIR(info.st_mode), 'Bound directory type changed')
            actual = dict(kind='directory', mode=stat.S_IMODE(info.st_mode))
        require(actual == expected, 'Bound selected input changed after execution: ' + name)
    invocation, command = read(BASE / 'invocation-receipt.json'), read(BASE / 'command.json')
    require(invocation['nativeInvocationCount'] in [0, 1], 'More than one native invocation')
    require(command['maximumAttempts'] == 1 and command['retryAttempted'] is False, 'Retry contract changed')
    exception_path = BASE / 'original-exception.json'
    if invocation['returnedNormally'] is False:
        require(exception_path.is_file() and command['exitCode'] != 0, 'Original failed outcome missing')
        require(read(exception_path)['originalOutcomeRetained'] is True, 'Original exception not retained')
    else:
        require(not exception_path.exists() and command['exitCode'] == 0, 'Successful invocation has inconsistent outcome')
    inspection = read(BASE / 'outcome-inspection.json')
    if not invocation['runtimePathPresent']:
        require(not os.path.lexists(RUNTIME), 'Unexpected output after early failure')
        require(invocation['returnedNormally'] is False, 'Absent runtime cannot qualify')
    else:
        runtime_files = {str(p.relative_to(ROOT)): record(p) for p in sorted(RUNTIME.rglob('*')) if p.is_file()}
        require(runtime_files == seal['runtimeFiles'], 'Runtime evidence membership/bytes changed')
        verdict = read(RUNTIME / 'runtime-verdict.json') if (RUNTIME / 'runtime-verdict.json').is_file() else None
        if verdict is not None and verdict.get('runPassed') is True:
            require(inspection['exactOfficialSevenMethodsPassed'] is True, 'Passed verdict lacks exact official seven methods')
            require(inspection['strictCompletedCursorCount'] == 6, 'Passed verdict lacks six complete strict cursors')
            require(inspection['allFiveCleanupPassed'] is True, 'Passed verdict lacks five cleanups')
            require(command['exitCode'] == 0 and verdict['xcodebuildExitCode'] == 0, 'Passed verdict has failed process')
    require(inspection['physicalPhones'] == 'disconnected-deferred' and inspection['gaAccepted'] is False and inspection['nativeAcceptancePending'] is True, 'Execution evidence overclaims acceptance')
    return dict(schema=1, status='sealed-execution-evidence-verified', nativeInvocationCount=invocation['nativeInvocationCount'],
        processExitCode=command['exitCode'], nativeOutcome=inspection['nativeOutcome'],
        exactOfficialSevenMethodsPassed=inspection['exactOfficialSevenMethodsPassed'],
        strictCompletedCursorCount=inspection['strictCompletedCursorCount'], allFiveCleanupPassed=inspection['allFiveCleanupPassed'],
        sourceInputsUnchanged=True, readOnly=True, nativeRerun=False,
        physicalPhones='disconnected-deferred', nativeAcceptancePending=True, gaAccepted=False)


if __name__ == '__main__':
    require(len(sys.argv) == 2, 'Usage: verify.py EXACT_EXECUTION_SEAL_SHA256')
    print(json.dumps(verify(sys.argv[1]), sort_keys=True))
