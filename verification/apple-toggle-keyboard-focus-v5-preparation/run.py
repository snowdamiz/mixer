#!/usr/bin/env python3
"""Root-selected setup diagnostic; verify/build never address native instances."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import signal
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PREVIOUS = BASE.parent / 'apple-toggle-keyboard-focus'
V2 = BASE.parent / 'apple-toggle-keyboard-focus-v2'
V3 = BASE.parent / 'apple-toggle-keyboard-focus-v3-preparation'
V4 = BASE.parent / 'apple-toggle-keyboard-focus-v4'
sys.path.append(str(PREVIOUS))
import keyboard_oracle
import settings_telemetry
spec = importlib.util.spec_from_file_location('immutable_keyboard_diagnostic_runtime', PREVIOUS / 'run.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
h = runtime.inherited
sha, read, require = runtime.sha, runtime.read, runtime.require
runtime.BASE = BASE
h.BASE = BASE
h.PRODUCTS = BASE / 'build/Build/Products'
h.PRODUCT_ARCHIVE = BASE / 'test-runner-products.tar.gz'
h.SOURCE_REVISION_CONTEXT = '9a9c0e000234b07a92c4484979d3587f7f24df48'
h.Bridge = settings_telemetry.diagnostic_bridge(h.Bridge)
h.SCOPES = {'interaction': {'cases': keyboard_oracle.CASES, 'methods': ['test000PublicSettingsFullKeyboardAccess']}}


def verify():
    seal = read(BASE / 'packet-seal.json')
    require(seal['schema'] == 'mixer.apple-toggle.keyboard-v5-diagnostic.1', 'Wrong diagnostic seal')
    for name, expected in seal['files'].items():
        p = ROOT / runtime.artifact.relative_name(name)
        require(p.is_file() and not p.is_symlink() and sha(p) == expected, 'Sealed diagnostic file changed: ' + name)
    old = subprocess.run([sys.executable, '-B', str(V4 / 'run.py'), 'verify'], cwd=ROOT, capture_output=True, text=True, timeout=60)
    require(old.returncode == 0, 'Immutable v4 preflight failed: ' + old.stderr)
    require(json.loads(old.stdout)['sealSHA256'] == 'b2b5630c09f3fbe0e0567ff118e88e75ccb5277ea1e1637915c6b3066e9616e3', 'V4 seal changed')
    reuse = read(BASE / 'immutable-reuse.json')
    require(all(sha(ROOT / name) == digest for group in ['copiedFiles', 'previousBindings'] for name, digest in reuse[group].items()), 'Immutable app/oracle/selection changed')
    review_seal = read(BASE.parent / 'apple-toggle-keyboard-focus-v3-independent-review/review-seal.json')
    require(all(sha(ROOT / name) == digest for name, digest in review_seal['files'].items()), 'Sealed independent V3 review changed')
    lock = read(BASE / 'source-lock.json')
    actual = {str(p.relative_to(BASE / 'source')): sha(p) for p in sorted((BASE / 'source').rglob('*')) if p.is_file()}
    closure = hashlib.sha256(h.json_bytes(actual)).hexdigest()
    require(actual == lock['sha256'] and closure == seal['candidateSourceClosureSHA256'] == 'f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46', 'App closure changed')
    app = read(BASE / 'built-app-manifest.json')
    require(app['archiveSHA256'] == seal['candidateArchiveSHA256'] == 'b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393', 'App archive identity')
    runtime.artifact.archive_payload(BASE / 'built-app.tar.gz', app, runtime.artifact.CONFIGS['diagnostic'])
    runner = read(BASE / 'build-products-manifest.json')
    require(h.tree(h.PRODUCTS) == runner['products'] and hashlib.sha256(h.json_bytes(runner['products'])).hexdigest() == runner['productTreeSHA256'] == seal['testRunnerProductTreeSHA256'], 'Runner tree changed')
    h.product_archive_payload(runner)
    require(all(sha(ROOT / name) == digest for name, digest in runner['sourceFiles'].items()), 'New runner sources changed')
    require(all(sha(pathlib.Path(name)) == digest for name, digest in runner['toolFiles'].items()), 'Official tools changed')
    for header in read(BASE / 'official/manifest.json')['installedOfficialHeaders']:
        require(sha(pathlib.Path(header['source'])) == header['sha256'] == sha(BASE / 'official' / header['snapshot']), 'Official declaration changed')
    controls = read(BASE / 'host-controls.json')
    require(controls['exitCode'] == 0 and controls['testsRun'] == controls['expectedTestsRun'] and controls['stderr'].rstrip().endswith('OK'), 'Diagnostic controls failed')
    require(all(sha(ROOT / name) == digest for name, digest in controls['sourceFiles'].items()), 'Diagnostic control sources changed')
    require(controls['allRequiredGroupsPassed'] is True, 'Required V5 replay groups incomplete')
    return {'schema': 'mixer.apple-toggle.keyboard-v5-diagnostic-preflight.1', 'sealSHA256': sha(BASE / 'packet-seal.json'), 'candidateSourceClosureSHA256': closure, 'candidateArchiveSHA256': app['archiveSHA256'], 'testRunnerProductTreeSHA256': runner['productTreeSHA256'], 'testRunnerArchiveSHA256': runner['productArchiveSHA256'], 'sourceRevisionContext': h.SOURCE_REVISION_CONTEXT, 'expectedXCTestMethods': 1, 'applicationCasesUnrun': sorted(keyboard_oracle.CASES), 'panPrerequisite': runtime.prerequisite(), 'status': 'DIAGNOSTIC_ONLY', 'nativeExecution': False, 'gaAccepted': False}


def summary(scope, bridge, xctest_exit, failure, cleanup_results):
    settings = None if bridge is None else bridge.settings.summary()
    export = read(BASE / 'runtime/attachment-export.json') if (BASE / 'runtime/attachment-export.json').is_file() else None
    boundary = failure is not None and failure['type'] == 'ValueError' and failure['message'] == 'Strict XCTest result failed; preserved evidence is authoritative' and xctest_exit == 0
    return {'schema': 'mixer.apple-toggle.keyboard-v5-diagnostic-runtime.1', 'status': 'DIAGNOSTIC_ONLY', 'scope': scope,
            'xcodebuildExitCode': xctest_exit, 'xcodebuildTerminalResultAvailable': xctest_exit is not None,
            'diagnosticCompleted': xctest_exit is not None and settings is not None and settings['settingsEvidenceComplete'] is True and settings['terminationMarkers'] == ['terminate-before', 'terminate-after'] and settings['completionMarkers'] == ['test-case-finished', 'suite-finished', 'bundle-finished'],
            'setupEvidenceComplete': settings is not None and settings['settingsEvidenceComplete'] is True,
            'settingsDiagnostic': settings, 'expectedDiagnosticQualificationBoundary': boundary,
            'sessionFailure': failure, 'sessionFailureClassification': 'expected-diagnostic-only-inherited-qualification-boundary' if boundary else None if failure is None else 'observed-command-or-session-failure',
            'strictNativeVerdictsPassed': False, 'bridgeFailures': None if bridge is None else list(bridge.failures),
            'expectedXCTestMethods': 1, 'actualNativeInputActions': 0, 'nativeUserInteractionVerdicts': [], 'applicationCasesExecuted': 0,
            'dependentCasesUnrun': sorted(keyboard_oracle.CASES), 'nativeKeyboardQualification': False,
            'attachmentExport': export, 'officialSummaryAvailable': (BASE / 'runtime/xctest-summary.json').is_file(), 'officialTestsAvailable': (BASE / 'runtime/xctest-tests.json').is_file(),
            'cleanupResults': cleanup_results, 'runPassed': False, 'carrierAccepted': False, 'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}


h.verify = verify
h.runtime_summary = summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['verify', 'run', 'cleanup'])
    p.add_argument('--scope', choices=['interaction'], default='interaction')
    p.add_argument('--reviewed-seal')
    a = p.parse_args()
    if a.action == 'verify':
        print(json.dumps(verify(), sort_keys=True))
    elif a.action == 'run':
        runtime.prerequisite()
        h.run(a.reviewed_seal, a.scope)
    else:
        h.RUN_DIR = h.select_runtime_directory(a.scope)
        life = read(h.RUN_DIR / 'lifecycle.json')
        require(life['verifiedHandoff']['sealSHA256'] == verify()['sealSHA256'], 'Diagnostic cleanup handoff changed')
        commands = runtime.ExportingCommands(h.RUN_DIR / 'recovery-commands.json')
        values = h.cleanup_independently([('owned-simulator-and-baseline-reconciliation', lambda: h.cleanup(life, commands)), ('ephemeral-capability-workspace-removal', lambda: h.remove_ephemeral(life))])
        life.update(cleanedUp=all(x['passed'] for x in values), recoveryCleanupResults=values)
        h.write(h.RUN_DIR / 'lifecycle.json', life)
        require(life['cleanedUp'], 'Diagnostic recovery cleanup incomplete')


if __name__ == '__main__':
    def stop(signum, frame):
        raise KeyboardInterrupt('Root diagnostic interrupted')
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    main()
