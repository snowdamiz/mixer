#!/usr/bin/env python3
"""Read-only replay of contract snapshot integrity; no Android runtime operations."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'snapshot-[1-9][0-9]*', args.snapshot):
        parser.error('snapshot-N required')
    if not re.fullmatch(r'review-[1-9][0-9]*', args.attempt):
        parser.error('fresh review-N required')
    out = HERE / args.attempt
    out.mkdir()
    receipt = {
        'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT)),
                    '--snapshot', args.snapshot, '--attempt', args.attempt],
        'toolVersion': sys.version, 'toolSHA256': sha(Path(sys.executable)),
        'reviewerSHA256': sha(Path(__file__)), 'snapshot': args.snapshot,
        'scope': 'Replay saved file bindings and contract metadata; no runtime or release authorization',
        'nativeTargetsQueried': False, 'nativeInstancesStarted': 0,
    }
    try:
        saved = HERE / args.snapshot
        sealed = json.loads((saved / 'artifact-seal.json').read_text())['files']
        for name, expected in sealed.items():
            path = saved / name
            assert path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'], name
        lock = json.loads((saved / 'source-lock.json').read_text())
        digest = hashlib.sha256(json.dumps(lock['files'], sort_keys=True,
                                            separators=(',', ':')).encode()).hexdigest()
        assert digest == lock['sourceSnapshotSHA256']
        for name, expected in lock['files'].items():
            assert sha(ROOT / name) == expected, 'current source drift: ' + name
        captured = json.loads((saved / 'receipt.json').read_text())
        assert captured['status'] == 'contract-snapshot-and-public-api-linkage-passed-no-native-execution'
        assert captured['compileWitness']['executed'] is False
        assert captured['compileWitness']['packaged'] is False
        assert captured['predecessorRootAcceptance']['bindingsRechecked'] == 60
        assert captured['predecessorComparison']['nativeAndSDKInputsAllMatch'] is True
        assert captured['predecessorComparison']['nativeAndSDKInputs'] == 88
        contract = json.loads((HERE / 'contract.json').read_text())
        bounds = contract['firstSlice']['bounds']
        actions = len(contract['firstSlice']['cycle']) * contract['firstSlice']['cycleRepetitions']
        actions += len(contract['firstSlice']['singleActions'])
        assert actions == bounds['gestureActions'] == 20
        assert actions * bounds['eventsPerAction'] == bounds['injectedMotionEvents'] == 320
        assert contract['fixtureImplemented'] is False
        assert contract['firstSlice']['directNativeCallbackCount'] is None
        assert contract['firstSlice']['generationReplacementCoverage'] is False
        assert captured['nativeAssertionsExecutedByThisLane'] == 0
        prior = HERE / 'snapshot-1'
        for name, expected in json.loads((prior / 'artifact-seal.json').read_text())['files'].items():
            assert sha(prior / name) == expected['sha256']
        note = json.loads((HERE / 'failure-notes/snapshot-1.json').read_text())
        assert sha(HERE / 'failure-notes/snapshot-1-collector.original.py') == note['originalCollectorSHA256']
        assert sha(prior / 'receipt.json') == note['failedReceiptSHA256']
        receipt.update({
            'status': 'passed-contract-integrity-only',
            'snapshotReceiptSHA256': sha(saved / 'receipt.json'),
            'snapshotSealSHA256': sha(saved / 'artifact-seal.json'),
            'sourceRevision': captured['sourceRevision'], 'sourceTree': captured['sourceTree'],
            'sourceSnapshotSHA256': digest, 'sealedFilesRechecked': len(sealed),
            'currentSourcesRechecked': len(lock['files']),
            'retainedFailedAttemptIntegrity': 'passed; snapshot-1 unchanged',
            'contractBudgetConsistency': 'passed; 20 actions, maximum 320 injected events',
            'directNativeCallbackCount': None, 'nativeAcceptance': False, 'gaAcceptance': False,
        })
    except BaseException as failure:
        receipt.update({'status': 'failed-integrity-review-retained', 'failure': repr(failure)})
        raise
    finally:
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
