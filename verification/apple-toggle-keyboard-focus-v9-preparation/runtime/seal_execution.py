#!/usr/bin/env python3
"""Seal/check additive diagnostic evidence only. Never execute native or host tests."""
import datetime
import hashlib
import importlib.util
import json
import pathlib
import stat
import sys

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
SEAL = BASE / 'execution-seal.json'
DOC = ROOT / 'docs/apple-toggle-keyboard-focus-v9-runtime.md'
EXCLUDED = {'execution-seal.json', 'execution-seal-check.json'}
PINS = {
    'verification/apple-toggle-keyboard-focus-v9-root-review/native-diagnostic-selection.json': '6c846e79181247d00d22dd30e39c80519dd05bc0b35899c2815cfa7838b11f9c',
    'verification/apple-toggle-keyboard-focus-v9-preparation/packet-seal.json': 'a9f7f3843bd8cfbd2f751f70d2a0b02e503166129ab98637d3602bba2eb4c0f5',
    'verification/apple-toggle-keyboard-focus-v9-independent-review/review-seal.json': 'eb39d33f3a35dcdd0fb9c462cb49a6e1076688c203483377e9f8bb57565fcd50',
}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())


def files():
    paths = [DOC]
    for p in sorted(HERE.rglob('*')):
        assert not p.is_symlink(), str(p)
        assert p.is_file() or p.is_dir(), str(p)
        if p.is_file():
            paths.append(p)
    for p in sorted(BASE.glob('execution-*')):
        assert p.is_file() and not p.is_symlink()
        if p.name not in EXCLUDED:
            paths.append(p)
    assert len(paths) == len(set(paths))
    return {str(p.relative_to(ROOT)): dict(sha256=sha(p), bytes=p.stat().st_size,
                                           mode=stat.S_IMODE(p.stat().st_mode)) for p in paths}


def inspect():
    spec = importlib.util.spec_from_file_location('v9_completed_evidence_inspection', HERE / 'inspect_execution.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inspect()


def check():
    value = read(SEAL)
    assert value['files'] == files(), 'Additive evidence inventory/bytes changed'
    assert value['fileCount'] == len(value['files'])
    assert value['fileBytes'] == sum(x['bytes'] for x in value['files'].values())
    assert all(sha(ROOT/p) == expected for p, expected in PINS.items())
    assert value['selectedInputSealHashes'] == PINS
    assert hashlib.sha256(json.dumps(value['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest() == value['evidenceTreeSHA256']
    source = read(BASE / 'execution-command.json')
    assert sha(HERE/'execution.stdout') == source['stdoutSHA256']
    assert sha(HERE/'execution.stderr') == source['stderrSHA256']
    result = inspect()
    return dict(schema='mixer.apple-toggle.keyboard-v9-native-execution-seal-check.1',
                sealSHA256=sha(SEAL), filesVerified=value['fileCount'], bytesVerified=value['fileBytes'],
                evidenceTreeSHA256=value['evidenceTreeSHA256'], diagnosticCompleted=result['diagnosticCompleted'],
                officialXCTestPassed=1, selectedCommandExitCode=1, xcodebuildExitCode=0,
                cleanupVerified=True, originalAttachmentReceiptPassed=False, nativeKeyboardQualification=False,
                applicationCasesExecuted=0, carrierAccepted=False, gaAccepted=False,
                scope='Additive evidence files and offline assertions only; no native/compiler/host test execution.')


def seal():
    assert not SEAL.exists(), 'Never overwrite an additive execution seal'
    result = inspect()
    assert all(sha(ROOT/p) == expected for p, expected in PINS.items())
    bindings = files()
    result = dict(schema='mixer.apple-toggle.keyboard-v9-native-execution-seal.1',
                  observedUTC=datetime.datetime.now(datetime.UTC).isoformat(),
                  sealCommand=['python3', '-B', str((HERE/'seal_execution.py').relative_to(ROOT)), 'seal'],
                  pythonVersion=sys.version, pythonExecutableSHA256=sha(pathlib.Path(sys.executable)),
                  status='completed-setup-only-diagnostic-root-acceptance-pending',
                  selectedInputSealHashes=PINS, fileCount=len(bindings),
                  fileBytes=sum(x['bytes'] for x in bindings.values()), files=bindings,
                  evidenceTreeSHA256=hashlib.sha256(json.dumps(bindings, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                  commandExitCode=1, xcodebuildExitCode=0, officialXCTestPassed=1,
                  diagnosticCompleted=True, setupEvidenceComplete=True, cleanupVerified=True,
                  officialExportCommandSucceeded=True, originalAttachmentReceiptPassed=False,
                  attachmentReceiptDiscrepancyRetained=True, nativeKeyboardQualification=False,
                  applicationCasesExecuted=0, carrierAccepted=False, gaAccepted=False,
                  physicalPhones='disconnected-deferred', unchangedRetry=False,
                  unsealedOperationalFiles=sorted(EXCLUDED-{'execution-seal.json'}),
                  accountableReviewer='Root review pending; producer sealing supplies no acceptance.')
    with SEAL.open('x') as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return check()


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'check'
    assert action in ['seal', 'check']
    print(json.dumps(seal() if action == 'seal' else check(), sort_keys=True))
