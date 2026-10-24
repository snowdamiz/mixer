#!/usr/bin/env python3
"""Verify saved planning bindings; never mark a proposed product row passed."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    receipt = json.loads((HERE / 'results/receipt.json').read_text())
    assert receipt['status'] == 'planning-evidence-only'
    assert receipt['rootFreeze'] == 'pending'
    for flag in ['productionChanged', 'compilationPerformed', 'productTestsPerformed',
                 'nativeRuntimePerformed', 'computerUsePerformed']:
        assert receipt[flag] is False, flag
    for name, digest in receipt['bindings'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    manifest = json.loads((HERE / 'results/vm-source-manifest.json').read_text())
    for name, digest in manifest.items():
        assert hashlib.sha256((ROOT / 'vm' / name).read_bytes()).hexdigest() == digest, name
    matrix = json.loads((HERE / 'matrix.json').read_text())
    assert matrix['status'] == 'planned-not-executed'
    assert len(matrix['newTests']) == 6
    assert len({test['name'] for test in matrix['newTests']}) == 6
    assert all(test['assertions'] for test in matrix['newTests'])
    assert all(command['status'].startswith('pending-') for command in matrix['futureCommands'])
    print(json.dumps({'status': 'planning-bindings-verified',
                      'boundArtifacts': len(receipt['bindings']),
                      'boundVMFiles': len(manifest), 'plannedNewTests': 6,
                      'semanticAcceptance': False, 'rootFreeze': 'pending'}, sort_keys=True))


if __name__ == '__main__':
    main()
