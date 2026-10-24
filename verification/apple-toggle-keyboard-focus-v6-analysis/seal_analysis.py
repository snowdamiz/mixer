#!/usr/bin/env python3
"""Seal only this new analysis lane after a read-only reproduction check."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import time

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DOC = ROOT / 'docs/apple-toggle-keyboard-focus-v6-analysis.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (BASE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


assert not (BASE / 'analysis-seal.json').exists(), 'Already sealed; do not overwrite'
argv = [sys.executable, '-B', 'verification/apple-toggle-keyboard-focus-v6-analysis/analyze.py', '--check']
started = time.monotonic()
result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=30)
receipt = {'schema': 'mixer.apple-toggle.keyboard-v6-analysis-check-command.1', 'argv': argv, 'cwd': str(ROOT), 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'tool': {'path': str(pathlib.Path(sys.executable).resolve()), 'version': sys.version, 'sha256': sha(pathlib.Path(sys.executable).resolve())}, 'sourceSHA256': sha(BASE / 'analyze.py'), 'exitCode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'elapsedSeconds': time.monotonic() - started, 'scope': 'Existing analyze.py --check performs read-only offline seal/input/replay/control comparisons only.'}
write('check-command.json', receipt)
assert result.returncode == 0, 'Read-only analysis reproduction failed'
analysis = json.loads((BASE / 'analysis.json').read_bytes())
inputs = json.loads((BASE / 'review-inputs.json').read_bytes())
for name, item in inputs.items():
    path = pathlib.Path(name) if name.startswith('/') else ROOT / name
    assert path.is_file() and not path.is_symlink() and sha(path) == item['sha256'], 'Input drift: ' + name
paths = [p for p in BASE.rglob('*') if p.is_file()]
paths.append(DOC)
files = {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}
seal = {'schema': 'mixer.apple-toggle.keyboard-v6-offline-analysis-seal.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'accountableAnalyst': '/root/apple_keyboard_v6_runtime_analysis', 'disposition': 'V6-failed-setup-preserved-minimal-V7-proposal-ready-for-root-selection', 'sourceRevisionContext': analysis['sourceRevisionContext'], 'rootRuntimeSelectionSHA256': analysis['rootRuntimeSelectionSHA256'], 'preparationSealSHA256': analysis['reviewedPreparationSHA256'], 'independentReviewSealSHA256': analysis['reviewedIndependentReviewSHA256'], 'inputCount': len(inputs), 'inputInventorySHA256': analysis['inputInventorySHA256'], 'files': files, 'fileCount': len(files), 'exactOfflineReplayMatches': True, 'hostReviewModelControls': 37, 'actualV6SetupObservationSatisfied': False, 'actualV6XCTestPassed': False, 'implementationSelected': False, 'nativeExecutionSelected': False, 'analysisNativeExecuted': False, 'analysisCompilerExecuted': False, 'applicationCasesExecuted': 0, 'applicationCasesUnrun': analysis['applicationCasesUnrun'], 'nativeKeyboardQualification': False, 'carrierAccepted': False, 'gaAccepted': False, 'physicalPhones': 'disconnected-deferred', 'scope': 'Offline replay, decoded immutable official event data, AX/PNG observation, native/host selector analysis and bounded V7 proposal only. Root retains runtime acceptance, tracking and Git.'}
write('analysis-seal.json', seal)
print(json.dumps({'sealed': True, 'files': len(files), 'inputs': len(inputs), 'sealSHA256': sha(BASE / 'analysis-seal.json'), 'nativeExecutionSelected': False, 'gaAccepted': False}, sort_keys=True))
