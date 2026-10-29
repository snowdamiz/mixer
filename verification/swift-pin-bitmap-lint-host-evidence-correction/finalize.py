#!/usr/bin/env python3
"""Freeze the sibling correction only; effect guard precedes subject import."""
import unittest.mock
import offline
offline.install()
import datetime
import hashlib
import json
from pathlib import Path
import sys
import admit

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / 'swift-pin-bitmap-lint-independent-admission'
REVIEW = HERE.parent / 'swift-pin-bitmap-lint-host-proposal-review'


def row(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


for packet, expected in (
    (FROZEN, '2012b4f0aabe97ebc2c10a501ea0f1dcc06791b0b4dcc5db5bb80c371fb28238'),
    (REVIEW, '16b9a002222f2df7e2977d9cd90b441f066d7f982f529133e0abb1483e8383f9'),
):
    assert row(packet / 'seal.json')['sha256'] == expected
    seal = json.loads((packet / 'seal.json').read_text())
    for name, expected_row in seal['files'].items():
        assert row(packet / name) == expected_row
controls = json.loads((HERE / 'controls-result.json').read_text())
assert controls['tests'] == 16
assert controls['failures'] == controls['errors'] == controls['skips'] == 0
assert controls['liveApiAttempts'] == [] and offline.ATTEMPTS == []
assert controls['scratchRemaining'] == [] and not list(HERE.glob('pure-*'))
save('source-basis.json', {
    'schema': 1,
    'frozenHostProposal': {'sealSHA256': row(FROZEN / 'seal.json')['sha256'], 'members': 18,
                           'treeSHA256': 'b3bb8c60d2a14213b48e7a203b97618cce8214fd78b09219f9d779fd3ef7359c'},
    'frozenIndependentReview': {'sealSHA256': row(REVIEW / 'seal.json')['sha256'], 'members': 7,
                                 'treeSHA256': 'a45be44c06a4c7e3c27df9a91db545bc94b5339d39f66dde5aabc41df6c71223'},
    'copiedInputs': {n: row(FROZEN / n) for n in ('admit.py', 'bounded_commands.py', 'offline.py', 'command-plan.json', 'workflow.yml')},
    'candidateTreeSHA256': admit.CANDIDATE, 'candidateMembers': 136, 'overlays': 15,
})
save('receipt.json', {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'decision': 'Narrow sibling evidence correction proposed; independent root inspection/replay and selection pending',
    'parentSuppliedRevision': '6d57e05e58e6d614e58a0a4dc0fad661264fb46f', 'GitVerified': False,
    'changedFunctions': ['test_evidence', 'format_evidence'], 'addedHelper': 'format_roster',
    'allOtherFunctionsAndGlobalsASTIdentical': True, 'boundedCommandsAndOfflineGuardByteIdentical': True,
    'exactSixVectorsAndBoundsUnchanged': True, 'compilerAndNodePolicyUnchanged': True,
    'candidateTreeSHA256': admit.CANDIDATE, 'candidateMembers': 136, 'overlays': 15,
    'controlsPassed': 16, 'controlsMockedOrSourceOnly': True, 'guardBeforeSubjectImports': True,
    'commands': [
        'python3 -B verification/swift-pin-bitmap-lint-host-evidence-correction/prepare.py',
        'python3 -B verification/swift-pin-bitmap-lint-host-evidence-correction/controls.py',
        'python3 -B verification/swift-pin-bitmap-lint-host-evidence-correction/finalize.py',
    ],
    'controlsRuns': 2, 'failedControlsRuns': 0,
    'iterationNote': 'The second passing run preserves UTF-8 refusal while retaining exact bytes and rejects indented failure-summary candidates',
    'pythonVersion': sys.version, 'liveApiAttempts': [], 'realNestedProcessSessionGroupSignalTimerWaitSocketCalls': 0,
    'RustNodeSwiftElixirCompilerProductRuntimeRuns': 0, 'nativeUICaptureRuns': 0, 'GitGhDispatchActions': 0,
    'frozenPacketsWritten': False, 'canonicalFilesEdited': False, 'workflowInstalled': False, 'selected': False,
    'cleanup': {'disposablePureScratchRemaining': 0, 'heldProcessesProbed': False, 'otherProjectsTouched': False},
    'localHoldsUnchanged': [20745, 20770, 20780, 20817, 20842, 20851, 20866],
    'FieldLog': {'run': 40802230894, 'pgid': 2424, 'pid': 2621, 'probedSignalledRetried': False},
    'limitations': ['No live runtime or custody proof', 'No YAML parser/actionlint execution',
                    'Original provisioner/descendant/Node-pipe/upload/shared-library limits preserved',
                    'Evidence destination I/O failure can prevent complete retention and fails admission'],
    'pending': ['root independent inspection/replay', 'root selection/workflow integration', 'host execution/artifact interpretation',
                'canonical integration', 'native/physical/published-package FieldLog/GA'],
    'GAQualified': False,
})
files = {p.name: row(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name != 'seal.json'}
tree = hashlib.sha256(''.join(n + '\0' + files[n]['sha256'] + '\n' for n in sorted(files)).encode()).hexdigest()
save('seal.json', {'schema': 1, 'scope': 'Narrow sibling host evidence correction proposal only', 'files': files, 'treeSHA256': tree})
print(json.dumps({'members': len(files), 'treeSHA256': tree, 'sealSHA256': row(HERE / 'seal.json')['sha256'], 'controlsPassed': 16, 'liveApiAttempts': offline.ATTEMPTS}, sort_keys=True))
