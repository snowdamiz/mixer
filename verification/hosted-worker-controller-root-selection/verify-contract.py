#!/usr/bin/env python3
"""Data-only root selection; no controller or provider acceptance."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
CONTRACT = ROOT / 'verification/hosted-worker-controller-contract'
IDENTITY = '41a64e88db50c6c320b447b0a18fd6624c05af28e3f7bf00be07d7d3a0b03ae3'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    target = BASE / 'contract-selection.json'
    assert not target.exists(), 'Preserve prior selection'
    raw = (CONTRACT / 'receipt.json').read_bytes()
    assert sha(raw) == IDENTITY
    receipt = json.loads(raw)
    for row in receipt['input_files'] + receipt['artifact_files']:
        path = ROOT / row['path']
        assert path.resolve() == path and path.is_file() and path.stat().st_nlink == 1, row['path']
        data = path.read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    assert sha(json.dumps(receipt['input_files'], sort_keys=True, separators=(',', ':')).encode()) == receipt['source_tree_sha256']
    for command in receipt['commands']:
        assert command['exit_code'] == command['expected_exit_code']
    assert receipt['effects']['product_modules_loaded'] == 0
    result = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'command': [sys.executable, str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
              'verifierSHA256': sha(Path(__file__).read_bytes()), 'contractReceiptSHA256': IDENTITY,
              'status': 'selected-for-isolated-controller-source-and-local-workerd-implementation',
              'inputFilesVerified': len(receipt['input_files']), 'contractArtifactsVerified': len(receipt['artifact_files']),
              'recordedCommandsVerified': len(receipt['commands']), 'sourceTreeSHA256': receipt['source_tree_sha256'],
              'selection': 'hosted-worker-controller/ source, codec, principal and SQLite DO ledger/recovery; test-only finite clock/provider in separate bundle.',
              'dependencySelectionSHA256': sha((BASE / 'dependencies.json').read_bytes()),
              'rootImportedOrExecutedContractCode': False, 'controllerImplementedByThisReceipt': False,
              'cloudDeploymentAuthorized': False, 'nativeOrProviderAccepted': False, 'gaAccepted': False,
              'remaining': receipt['not_verified']}
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'inputFilesVerified', 'contractArtifactsVerified', 'recordedCommandsVerified']}))


if __name__ == '__main__':
    main()
