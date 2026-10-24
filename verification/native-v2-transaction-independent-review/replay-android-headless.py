#!/usr/bin/env python3
"""Offline Android source/compile evidence replay. No native/runtime commands."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import traceback

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
ANDROID = ROOT / 'verification/android-native-appearance-v2'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'headless-section-[0-9]+', args.candidate)
    assert re.fullmatch(r'android-headless-review-[0-9]+', args.output)
    out = BASE / args.output
    out.mkdir()
    reads, checks, summary = {}, [], {}

    def path(base, name):
        result = (base / name).resolve()
        assert result.is_relative_to(base.resolve()), name
        return result

    def read(file):
        data = file.read_bytes()
        reads[str(file.relative_to(ROOT)) if file.is_relative_to(ROOT) else str(file)] = sha(data)
        return data

    def obj(file):
        return json.loads(read(file))

    def check(condition, name):
        assert condition, name
        checks.append(name)

    status, error = 'failed', None
    try:
        current = ANDROID / args.candidate
        receipt = obj(current / 'receipt.json')
        check(receipt['status'] == 'passed-headless-java-and-dex-only' and receipt['error'] is None,
              'headless-production-and-test-compile-pass')
        check(receipt['sourceUnchanged'] is True, 'producer-observed-stable-inputs')
        check(receipt['emulator'] == 'not-booted' and receipt['screenshots'] == 'not-run-user-paused',
              'no-native-execution-claimed')
        check(receipt['nativeSectionRegression'] == 'pending-user-resumption-of-computer-use-and-native-runtime',
              'native-regressions-explicitly-pending')
        manifest = receipt['sourceManifest']
        check(sha(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()) == receipt['sourceClosureSHA256'],
              'current-source-closure-digest')
        for name, expected in manifest.items():
            check(sha(read(path(current / 'inputs', name))) == expected, 'captured-source:' + name)
            check(sha(read(path(ROOT, name))) == expected, 'current-source:' + name)
        expected_commands = {'python-version', 'java-version', 'javac-version', 'd8-version',
                             'production-java-compile', 'native-renderer-bytecode', 'production-dex-min28',
                             'instrumentation-java-compile', 'instrumentation-dex-min36'}
        check({item['name'] for item in receipt['commands']} == expected_commands, 'complete-headless-command-set')
        for command in receipt['commands']:
            check(command['exitCode'] == 0, 'command-success:' + command['name'])
            check(sha(read(path(ROOT, command['output']))) == command['sha256'], 'command-log:' + command['name'])
            check(Path(command['argv'][0]).name in {'python3.14', 'python3', 'java', 'javac', 'javap', 'd8'},
                  'headless-command-entry:' + command['name'])
        for name, expected in receipt['toolSHA256'].items():
            check(sha(read(Path(name))) == expected, 'headless-tool:' + name)
        for name, expected in receipt['artifacts'].items():
            check(sha(read(path(ANDROID, name))) == expected, 'retained-build-artifact:' + name)
        seal = obj(current / 'artifact-seal.json')
        for name, expected in seal.items():
            check(sha(read(path(current, name))) == expected, 'sealed-current-evidence:' + name)
        summary['current'] = dict(candidate=args.candidate, sourceClosureSHA256=receipt['sourceClosureSHA256'],
                                  sourceInputs=len(manifest), retainedBuildArtifacts=len(receipt['artifacts']),
                                  sealedEvidenceFiles=len(seal), commands=len(receipt['commands']))
        # Verify old evidence without equating its closure to current repaired source.
        historical = ANDROID / 'candidate-15'
        old_receipt = obj(historical / 'receipt.json')
        old_seal = obj(historical / 'artifact-seal.json')
        for name, expected in old_seal.items():
            check(sha(read(path(historical, name))) == expected, 'historical-native-evidence-integrity:' + name)
        old_manifest = old_receipt['sourceManifest']
        drift = {name: {'historicalSHA256': value, 'currentSHA256': sha(read(path(ROOT, name)))}
                 for name, value in old_manifest.items() if sha(read(path(ROOT, name))) != value}
        check(bool(drift), 'historical-native-closure-is-distinct-from-current')
        summary['historicalNative'] = dict(candidate='candidate-15', status='integrity-only-not-current-native-acceptance',
                                          sealedEvidenceFiles=len(old_seal), sourceDifferences=drift)
        cleanup = obj(ANDROID / 'computer-use-pause-cleanup.json')
        check(cleanup['lastOwnedPID'] == 47382 and cleanup['lastOwnedSerial'] == 'emulator-5586', 'cleanup-owned-identity')
        check(cleanup['sectionRegressionBooted'] is False and cleanup['sectionNativeRunStarted'] is False, 'no-new-section-runtime')
        check({item['name'] for item in cleanup['commands']} == {'last-owned-process', 'last-owned-console-port'},
              'cleanup-exact-process-and-port')
        for item in cleanup['commands']:
            check(item['exitCode'] == 1 and not item['stdout'] and not item['stderr'], 'owned-resource-absent:' + item['name'])
        pause = obj(ROOT / 'verification/computer-use-pause-2026-10-24/receipt.json')
        check(pause['status'] == 'owned-native-processes-stopped', 'user-pause-recorded')
        for name, item in pause['processChecks'].items():
            check(item['absent'] and item['exitCode'] == 1, 'paused-process-absent:' + name)
            check(sha(read(path(ROOT / 'verification/computer-use-pause-2026-10-24', item['log']))) == item['sha256'],
                  'pause-process-output:' + name)
        for name, expected in manifest.items():
            check(sha(read(path(ROOT, name))) == expected, 'final-source-unchanged:' + name)
        status = 'passed-android-headless-source-and-evidence-review-native-pending'
    except Exception as failure:
        error = repr(failure)
        (out / 'failure.log').write_text(traceback.format_exc())
    result = {
        'status': status, 'error': error,
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        'pythonVersion': platform.python_version(),
        'reviewerScriptSHA256': sha(Path(__file__).read_bytes()),
        'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'sourceTree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(),
        'checks': checks, 'summary': summary, 'evidenceSHA256': reads,
        'scope': 'Independent read-only final Android Section/baseline source assessment and offline replay of retained strict Java/D8 compile evidence. Historical native candidate15 integrity is checked separately and cannot qualify changed source. No GUI, capture, simulator/emulator, device or product runtime commands; no redundant product suites.',
        'sourceReview': 'No remaining blocking finding in requested bounded transaction/environment/Section/baseline correction scope.',
        'nativeAcceptance': False,
        'pending': ['Current Section intrinsic/native header measurement and source-edge baseline fixtures on resumed native runtime.',
                    'Required-control-baseline rejection and ordinary-control alignment native assertions.',
                    'Current source generated-consumer export/ABI cross-build binding.',
                    'Apple opaque-cover paint/input/accessibility/held/cancel qualification.',
                    'Physical phones, real IME/AT breadth, native engine coordinator, signed/bootstrap V2, published packages, stores and GA.'],
    }
    (out / 'receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': status, 'checks': len(checks), 'evidenceFiles': len(reads),
                      'receipt': str(out / 'receipt.json'), 'error': error}))
    return 0 if status.startswith('passed-') else 1


if __name__ == '__main__':
    sys.exit(main())
