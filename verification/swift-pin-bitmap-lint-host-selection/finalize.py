#!/usr/bin/env python3
"""Archive guarded results and freeze only owned static source/metadata."""
import unittest.mock
import offline
offline.install()
import datetime
import hashlib
import json
from pathlib import Path
import sys
import verify

HERE = Path(__file__).resolve().parent


def row(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


check = verify.check(verify_seal=False)
results = {}
for name, expected in (('host-controls-result.json', 27), ('controls-result.json', 16)):
    result = json.loads((HERE / name).read_text())
    assert result['tests'] == expected
    assert result['failures'] == result['errors'] == result['skips'] == 0
    assert result['guardBeforeSubjectImports'] and result['liveApiAttempts'] == []
    assert result['scratchRemaining'] == []
    results[name] = result
assert offline.ATTEMPTS == [] and not list(HERE.glob('pure-*'))
out = HERE / 'outputs'; out.mkdir(exist_ok=True)
for source, archived in (('host-controls-result.json', 'local-host-controls.json'),
                         ('controls-result.json', 'local-correction-controls.json'),
                         ('test-output.txt', 'local-correction-test-output.txt')):
    (out / archived).write_bytes((HERE / source).read_bytes())
save(out / 'local-source-check.json', check)
commands = [
    {'command': 'python3 -B verification/swift-pin-bitmap-lint-host-selection/prepare.py',
     'exit': 0, 'scope': 'Guarded source-only packet preparation; no subject runtime execution',
     'output': {'sourceOnly': True, 'originalHostTests': 27, 'unchangedBodies': 26,
                'exactCorrectionTests': 16, 'liveApiAttempts': []}},
    {'command': 'python3 -B verification/swift-pin-bitmap-lint-host-selection/host_controls.py',
     'exit': 0, 'scope': 'Guarded source and mocked child lifecycle controls',
     'output': 'outputs/local-host-controls.json', 'outputBinding': row(out / 'local-host-controls.json')},
    {'command': 'python3 -B verification/swift-pin-bitmap-lint-host-selection/controls.py',
     'exit': 0, 'scope': 'Guarded exact evidence correction controls',
     'output': 'outputs/local-correction-controls.json', 'outputBinding': row(out / 'local-correction-controls.json'),
     'testOutput': 'outputs/local-correction-test-output.txt', 'testOutputBinding': row(out / 'local-correction-test-output.txt')},
    {'command': 'python3 -B verification/swift-pin-bitmap-lint-host-selection/finalize.py',
     'exit': 0, 'scope': 'Guarded read-only source checks, result archive and static packet seal',
     'sourceCheck': 'outputs/local-source-check.json', 'sourceCheckBinding': row(out / 'local-source-check.json')},
]
save(HERE / 'receipt.json', {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'decision': 'Source-only integration frozen for independent root review; no workflow installed or host attempt selected',
    'parentSuppliedRevision': '6d57e05e58e6d614e58a0a4dc0fad661264fb46f',
    'parentSuppliedGitTree': '8d7444955c4e6f2519b6e0823d52f131d180a1af', 'GitVerified': False,
    'pythonVersion': sys.version, 'commands': commands,
    'controls': {'originalHost': 27, 'exactCorrection': 16, 'passed': 43, 'failed': 0, 'errors': 0, 'skipped': 0,
                 'suiteRuns': 2, 'failedSuiteRuns': 0, 'allGuardsBeforeSubjectImports': True,
                 'unchangedOriginalHostBodies': 26, 'correctionSourceByteIdentical': True,
                 'scope': 'Source and mock assertions only; no live compiler/Node/custody evidence'},
    'workflow': {'proposedSHA256': verify.WORKFLOW_SHA256, 'installed': False, 'selected': False,
                 'canonicalPath': '.github/workflows/swift-pin-bitmap-lint-regression-admission.yml',
                 'structuralSourceCheckOnly': True, 'YAMLParserAvailable': False,
                 'actionlintExecuted': False, 'parserOrDependencyInstallAttempted': False},
    'candidate': {'members': 136, 'overlays': 15, 'treeSHA256': check['candidateTreeSHA256'],
                  'sealSHA256': '89505e8f873e5c225d711f8ae923bd8149db30a74603c49dddb523639cb11052'},
    'guardedSourceCheck': check, 'liveApiAttempts': [],
    'realNestedProcessSessionGroupSignalTimerWaitSocketCalls': 0,
    'RustNodeSwiftElixirCompilerProductRuntimeRuns': 0, 'nativeUICaptureRuns': 0,
    'GitGhDispatchActions': 0, 'canonicalFilesEdited': False, 'frozenPacketsWritten': False,
    'cleanup': {'disposablePureScratchRemaining': 0, 'runtimeInstancesStarted': 0,
                'heldProcessesProbed': False, 'onlyOwnedFolderWritten': True, 'otherProjectsTouched': False},
    'localHoldsUnchanged': [20745, 20770, 20780, 20817, 20842, 20851, 20866],
    'FieldLog': {'run': 40802230894, 'pgid': 2424, 'pid': 2621, 'probedSignalledRetried': False},
    'limitations': ['No live runtime or custody evidence', 'Structural workflow validation only; no YAML/actionlint validation',
                    'Original provisioner, same-group descendants, Node pipes/reap, scratch upload, shared-library and evidence I/O limits preserved'],
    'pending': ['root independent final inspection/replay', 'root workflow install and one-attempt selection',
                'actual hosted compiler/Node/format/lint/Debug/Release evidence and artifact interpretation',
                'canonical integration', 'native/physical/published-package FieldLog/GA'],
    'GAQualified': False,
})
files = {p.relative_to(HERE).as_posix(): row(p) for p in sorted(HERE.rglob('*'))
         if p.is_file() and p.name not in verify.RUNTIME_NAMES and p.name != 'seal.json'}
assert not any(n.startswith('pure-') or '__pycache__' in n for n in files)
tree_sha = verify.tree(files)
save(HERE / 'seal.json', {'schema': 1, 'scope': 'Final source-only host integration packet; install/dispatch unselected',
                         'runtimeResultNamesExcluded': sorted(verify.RUNTIME_NAMES),
                         'files': files, 'treeSHA256': tree_sha})
print(json.dumps({'members': len(files), 'treeSHA256': tree_sha, 'sealSHA256': row(HERE / 'seal.json')['sha256'],
                  'controlsPassed': 43, 'workflowSHA256': verify.WORKFLOW_SHA256, 'liveApiAttempts': offline.ATTEMPTS}, sort_keys=True))
