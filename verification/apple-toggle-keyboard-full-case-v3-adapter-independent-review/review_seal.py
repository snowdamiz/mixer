#!/usr/bin/env python3
"""Seal once or independently verify this bounded source/host review packet."""
import datetime
import hashlib
import json
import pathlib
import stat
import sys

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DOC = ROOT / 'docs/apple-toggle-keyboard-full-case-v3-adapter-independent-review.md'
ADAPTER = ROOT / 'verification/apple-toggle-keyboard-full-case-v3-adapter'
EXPECTED = '137b6dc9b681eff1358712c34d9b71a3b356072ee6954b4a99e9a8c32b60f46b'
SEAL = BASE / 'review-seal.json'


def audit(event, args):
    if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.fork', 'os.forkpty',
                 'os.exec', 'socket.connect', 'socket.bind', 'socket.getaddrinfo'}:
        raise AssertionError('Native/process/network boundary forbidden')


sys.addaudithook(audit)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def record(path):
    info = path.lstat()
    assert stat.S_ISREG(info.st_mode) and path.resolve() == path, str(path)
    return dict(kind='file', mode=stat.S_IMODE(info.st_mode), bytes=info.st_size, sha256=sha(path))


def inputs():
    assert sha(ADAPTER / 'packet-seal.json') == EXPECTED
    for name, row in read(ADAPTER / 'packet-seal.json')['files'].items():
        assert record(ROOT / name) == row, name
    for name, row in read(ADAPTER / 'selected-inputs.json')['files'].items():
        assert record(ROOT / name) == row, name
    assert not (ROOT / 'verification/apple-toggle-keyboard-full-case-preparation-v3/runtime').exists()
    assert not any(BASE.glob('review-host-*'))
    assert not any(BASE.rglob('__pycache__'))


def validate_evidence():
    host = read(BASE / 'host-controls.json')
    isolated = read(BASE / 'isolated.json')
    cleanup = read(BASE / 'cleanup.json')
    review = read(BASE / 'source-review.json')
    assert host['status'] == 'pass' and host['methodsRun'] == 13 and host['exitCode'] == 0
    assert host['failureCount'] == host['errorCount'] == 0
    assert host['reviewSourceSHA256'] == sha(BASE / 'review.py')
    assert isolated['reviewSourceSHA256'] == sha(BASE / 'isolated_check.py')
    assert isolated['exitCode'] == 0 and isolated['adapterSealSHA256'] == EXPECTED
    for label, receipt in [('host-controls', host), ('isolated', isolated)]:
        for stream in ['stdout', 'stderr']:
            assert sha(BASE / (label + '.' + stream)) == receipt[stream + 'SHA256']
    assert cleanup['acceptedBeforeAfterEqual'] and cleanup['ownedScratchAbsent'] and cleanup['fixedRuntimeAbsent']
    assert cleanup['prohibitedBoundaryAttempts'] == []
    assert review['actionableDefects'] == [] and review['rootAcceptancePending'] is True
    assert review['nativeAccepted'] is False and review['gaAccepted'] is False
    assert host['nativeExecution'] is False and isolated['nativeExecution'] is False


def main():
    assert sys.argv[1:] and sys.argv[1] in {'seal', 'verify'}
    inputs()
    validate_evidence()
    if sys.argv[1] == 'seal':
        assert len(sys.argv) == 2 and not SEAL.exists()
        paths = sorted(path for path in BASE.rglob('*') if path.is_file()) + [DOC]
        files = {str(path.relative_to(ROOT)): record(path) for path in paths}
        host = read(BASE / 'host-controls.json')
        value = dict(schema='mixer.apple-toggle.keyboard-full-case-v3-adapter-independent-review.1',
                     observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     reviewer='/root/apple_keyboard_v3_adapter_review', status='bounded-source-host-review-pass',
                     adapterSealSHA256=EXPECTED, files=files,
                     sourceRevision=host['sourceRevision'], sourceRevisionObservation=host['revisionObservation'],
                     finalHostMethodsPassed=13, finalHostExitCode=0, isolatedExitCode=0,
                     independentHostAttempts=2, failedFirstHostAttemptPreserved=True,
                     nativeExecutionSelected=False, nativeInstancesQueried=False, compilerInvoked=False,
                     applicationCasesExecuted=0, nativeAccepted=False, carrierAccepted=False, gaAccepted=False,
                     physicalPhones='disconnected-deferred', rootAcceptancePending=True,
                     command=[sys.executable, '-B', str(pathlib.Path(__file__).resolve()), 'seal'],
                     cwd=str(ROOT), pythonVersion=sys.version,
                     pythonExecutable=str(pathlib.Path(sys.executable).resolve()),
                     pythonBinarySHA256=sha(pathlib.Path(sys.executable).resolve()),
                     acceptedInputsUnchanged=True, ownedHostScratchAbsent=True)
        with SEAL.open('x') as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write('\n')
        print(sha(SEAL))
    else:
        assert len(sys.argv) == 3 and sha(SEAL) == sys.argv[2], 'Exact review seal required'
        value = read(SEAL)
        assert value['adapterSealSHA256'] == EXPECTED
        for name, expected in value['files'].items():
            assert record(ROOT / name) == expected, name
        print(json.dumps(dict(status='verified-source-host-review', reviewSealSHA256=sha(SEAL),
                              adapterSealSHA256=EXPECTED, reviewFiles=len(value['files']),
                              nativeAccepted=False, gaAccepted=False)))


if __name__ == '__main__':
    main()
