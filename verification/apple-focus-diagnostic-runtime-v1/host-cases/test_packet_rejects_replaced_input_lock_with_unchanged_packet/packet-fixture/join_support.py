"""Owned diagnostic adapters; imports have no native or service side effects."""
import copy
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import time

_selected = None
METHODS = ['test000PublicSettingsFullKeyboardAccess', 'test010EnabledFromOff']
CASE = 'keyboard-enabled-off'


def require(value, message):
    if not value: raise ValueError(message)


def sha(data): return hashlib.sha256(data).hexdigest()


def verify_packet(base):
    selection = json.loads((base / 'runtime-selection.json').read_bytes())
    for name, digest in selection['files'].items():
        path = base / name
        require(path.resolve() == path and path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == digest,
                'Selected runtime bytes changed: ' + name)
    verify_products(selection)
    return {'sealSHA256': sha((base / 'runtime-selection.json').read_bytes()),
            'nativeAcceptanceGranted': False, 'methods': METHODS, 'cases': [CASE]}


def product_tree(path):
    info = path.lstat()
    require(path.resolve() == path and stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o755,
            'Unexpected product root directory')
    rows, directories = {}, set()
    for item in sorted(path.rglob('*')):
        mode = stat.S_IMODE(item.lstat().st_mode)
        if item.is_symlink(): rows[str(item.relative_to(path))] = {'kind': 'symlink', 'target': os.readlink(item), 'mode': mode}
        elif item.is_file():
            value = item.read_bytes()
            rows[str(item.relative_to(path))] = {'kind': 'file', 'bytes': len(value), 'mode': mode, 'sha256': sha(value)}
        else:
            require(item.is_dir() and mode == 0o755, 'Unexpected product directory')
            directories.add(str(item.relative_to(path)))
    implied = {str(parent) for name in rows for parent in Path(name).parents if str(parent) != '.'}
    require(directories == implied, 'Product directory set differs from exact implied directories')
    return rows


def verify_products(selection):
    expected = selection['productManifest']['products']
    require(product_tree(Path(selection['productsRoot'])) == expected, 'Compiled product changed')
    return True


def candidate_apps(artifact, base, selection):
    app_name = 'MixerToggleDiagnostics.app'
    files = {name.removeprefix(app_name + '/'): {'sha256': row['sha256'], 'bytes': row['bytes']}
             for name, row in selection['productManifest']['products'].items() if name.startswith(app_name + '/')}
    require(files and all(row['kind'] == 'file' for name, row in selection['productManifest']['products'].items() if name.startswith(app_name + '/')),
            'Diagnostic app requires manifest regular files')
    manifest = {'files': files, 'archiveSHA256': selection['productManifest']['archive']['sha256']}
    class CandidateApps:
        CONFIGS = {'diagnostic': dict(artifact.CONFIGS['diagnostic'])}
        @staticmethod
        def expected_manifest(key):
            require(key == 'diagnostic', 'Only diagnostic application selected')
            return manifest
        @staticmethod
        def restore(destination, key):
            require(key == 'diagnostic' and not destination.exists() and destination.resolve() == destination,
                    'Fresh diagnostic restore required')
            verify_products(selection)
            destination.mkdir(parents=True)
            shutil.copytree(Path(selection['productsRoot']) / app_name, destination / app_name)
            artifact.expected_manifest = CandidateApps.expected_manifest
            return artifact.verify_restored(destination / app_name, key)
        verify_installed = staticmethod(artifact.verify_installed)
    return CandidateApps


def prepare_session(h, lifecycle):
    path = h.RUN_DIR / 'session'
    require(path.resolve() == path and not path.exists(), 'Fresh canonical session required')
    path.mkdir(mode=0o700)
    info = path.lstat()
    lifecycle['ephemeralWorkspace'] = {'path': str(path), 'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid}
    lifecycle['retainedSessionScope'] = 'Retain result/observer evidence; retire only secret session configuration after exports.'
    return path


def derive_configuration(original, products, port, capability):
    require(type(port) is int and 0 < port < 65536 and type(capability) is str and len(capability) == 64,
            'Exact loopback port/ephemeral capability required')
    require(set(original) == {'MixerToggleUITests', '__xctestrun_metadata__'}, 'Unexpected xctestrun targets')
    result = copy.deepcopy(original)
    target = result['MixerToggleUITests']
    for key in ['EnvironmentVariables', 'TestingEnvironmentVariables']:
        require(not {'MIXER_BRIDGE_URL', 'MIXER_BRIDGE_CAPABILITY'} & set(target[key]), 'Preexisting bridge environment')
        target[key].update(MIXER_BRIDGE_URL=f'http://127.0.0.1:{port}', MIXER_BRIDGE_CAPABILITY=capability)
    target.update(TestTimeoutsEnabled=True, DefaultTestExecutionTimeAllowance=30, MaximumTestExecutionTimeAllowance=45,
                  ParallelizationEnabled=False, UserAttachmentLifetime='keepAlways', SystemAttachmentLifetime='keepAlways')
    def relocate(value):
        if isinstance(value, str): return value.replace('__TESTROOT__', str(products))
        if isinstance(value, dict): return {key: relocate(item) for key, item in value.items()}
        if isinstance(value, list): return [relocate(item) for item in value]
        return value
    return relocate(result)


def session_configuration(h, session, port, capability):
    selection = json.loads((Path(__file__).parent / 'runtime-selection.json').read_bytes())
    verify_products(selection)
    originals = list(h.PRODUCTS.glob('*.xctestrun'))
    require(len(originals) == 1, 'One exact prepared xctestrun required')
    raw = originals[0].read_bytes()
    key = str(originals[0].relative_to(Path(selection['productsRoot'])))
    require(sha(raw) == selection['productManifest']['products'][key]['sha256'], 'Original xctestrun changed')
    config = derive_configuration(plistlib.loads(raw), h.PRODUCTS, port, capability)
    path = session / 'session.xctestrun'
    with path.open('xb') as stream: stream.write(plistlib.dumps(config))
    path.chmod(0o600)
    redacted = plistlib.dumps(config).replace(capability.encode(), b'[ephemeral-capability-redacted]')
    h.write(session / 'configuration-derivation.json', {'schema': 1, 'sourceSHA256': sha(raw),
        'redactedDerivedSHA256': sha(redacted), 'mode': 0o600, 'capabilityRetainedInReceipt': False,
        'relocation': {'token': '__TESTROOT__', 'destination': str(h.PRODUCTS)},
        'environmentKeysAddedPerMapping': ['MIXER_BRIDGE_URL', 'MIXER_BRIDGE_CAPABILITY'],
        'limits': {'TestTimeoutsEnabled': True, 'DefaultTestExecutionTimeAllowance': 30,
                  'MaximumTestExecutionTimeAllowance': 45, 'ParallelizationEnabled': False,
                  'UserAttachmentLifetime': 'keepAlways', 'SystemAttachmentLifetime': 'keepAlways'},
        'compiledProductsUnchanged': verify_products(selection), 'retired': False})
    return path


def select_command(h, argv, session):
    global _selected
    require(_selected is None, 'Only one command can be selected')
    values = [str(value) for value in argv]
    identifier = values[values.index('-destination') + 1].removeprefix('platform=iOS Simulator,id=')
    expected = [str(h.DEVELOPER / 'usr/bin/xcodebuild'), 'test-without-building', '-xctestrun',
                str(session / 'session.xctestrun'), '-destination', 'platform=iOS Simulator,id=' + identifier,
                '-parallel-testing-enabled', 'NO', '-maximum-concurrent-test-simulator-destinations', '1',
                '-resultBundlePath', str(session / 'session.xcresult')]
    expected += ['-only-testing:MixerToggleUITests/ToggleUITests/' + method for method in METHODS]
    import uuid
    uuid.UUID(identifier)
    require(values == expected, 'Selected command differs from exact diagnostic contract')
    _selected = {'argv': values, 'cwd': h.ROOT, 'developer': h.DEVELOPER, 'session': session, 'called': False}


def is_selected(argv):
    values = [str(value) for value in argv]
    if _selected is not None and values == _selected['argv']: return True
    # Any other test-without-building invocation fails closed, never delegates silently.
    require(not (len(values) > 1 and values[1] == 'test-without-building'), 'Unselected XCTest command refused')
    return False


def run_observed(commands, argv, timeout, check, retained_stdout_filter):
    import command_observer
    require(_selected is not None and list(map(str, argv)) == _selected['argv'] and not _selected['called'],
            'Exact once-only selected command required')
    require(timeout == 600 and check is False and retained_stdout_filter is None,
            'Selected command timeout/check/filter contract changed')
    _selected['called'] = True
    started = time.monotonic()
    env = {**os.environ, 'DEVELOPER_DIR': str(_selected['developer']), 'PYTHONDONTWRITEBYTECODE': '1'}
    output = _selected['session'] / 'command-observer'
    try:
        result = command_observer.observe_command(_selected['argv'], cwd=_selected['cwd'], env=env,
            output_dir=output, owned_result_root=_selected['session'], result_bundle=_selected['session'] / 'session.xcresult',
            timeout=600, check=False)
    except BaseException as failure:
        summary = json.loads((output / 'observer.json').read_bytes()) if (output / 'observer.json').is_file() else {}
        retained = lambda name: (output / name).read_bytes().decode(summary.get('encoding', 'utf-8'), errors='replace') if (output / name).is_file() else ''
        commands.record('command-interrupted', {'argv': list(map(str, argv)), 'exitCode': summary.get('exitCode'),
            'failureType': type(failure).__name__, 'stdout': commands.redact(retained('stdout.log')),
            'stderr': commands.redact(retained('stderr.log')), 'elapsedSeconds': time.monotonic() - started})
        raise
    summary = json.loads((output / 'observer.json').read_bytes()) if (output / 'observer.json').is_file() else {}
    retained = lambda name, fallback: (output / name).read_text(encoding=summary.get('encoding', 'utf-8')) if (output / name).is_file() else fallback
    commands.record('command', {'argv': list(map(str, argv)), 'DEVELOPER_DIR': str(_selected['developer']),
        'exitCode': result[0], 'stdout': commands.redact(retained('stdout.log', result[1])), 'stdoutScope': 'complete',
        'stderr': commands.redact(retained('stderr.log', result[2])), 'elapsedSeconds': time.monotonic() - started})
    require(observer_terminal(summary, result[0], list(map(str, argv))),
            'Selected command lacks terminal owned-group/EOF/exit evidence; preserve owned PID/PGID for root recovery')
    return result


def observer_terminal(summary, code, argv=None):
    return (summary.get('exitCode') == code and type(code) is int
            and (argv is None or summary.get('argv') == argv)
            and summary.get('ownedProcessGroup', {}).get('state') == 'absent'
            and summary.get('cleanup', {}).get('complete') is not False
            and set(summary.get('streams', {})) == {'stdout', 'stderr'}
            and all(value.get('eof') is True and value.get('readerFailed') is False for value in summary['streams'].values())
            and summary.get('successInferredFromConsoleOrMarkers') is False)


def retire_session(h, lifecycle):
    expected = lifecycle['ephemeralWorkspace']
    path = Path(expected['path'])
    require(path == h.RUN_DIR / 'session' and path.resolve() == path and not path.is_symlink(), 'Session path changed')
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
            and (info.st_dev, info.st_ino, info.st_uid) == (expected['device'], expected['inode'], expected['uid']),
            'Session identity changed; preserve evidence')
    config = path / 'session.xctestrun'
    if config.exists() or config.is_symlink():
        info = config.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600,
                'Secret configuration identity changed')
        config.unlink()
    receipt = path / 'configuration-derivation.json'
    if receipt.is_file() and not receipt.is_symlink():
        value = json.loads(receipt.read_bytes())
        value.update(retired=True, secretConfigurationAbsent=not config.exists())
        h.write(receipt, value)
    lifecycle.update(secretConfigurationAbsent=not config.exists(), sessionEvidenceRetained=True)
    require(not config.exists() and not config.is_symlink(), 'Secret configuration remains')


def official_methods(base):
    summary_path, tests_path = base / 'runtime/xctest-summary.json', base / 'runtime/xctest-tests.json'
    if not summary_path.is_file() or not tests_path.is_file(): return False
    summary = json.loads(summary_path.read_bytes())
    if not (summary.get('result') == 'Passed' and summary.get('totalTestCount') == 2 and summary.get('passedTests') == 2
            and all(summary.get(key) == 0 for key in ['failedTests', 'skippedTests', 'expectedFailures'])): return False
    found, nodes = {}, []
    def visit(value):
        if isinstance(value, dict):
            if value.get('nodeType') == 'Test Case':
                nodes.append(value)
                for method in METHODS:
                    if value.get('nodeIdentifier') in [f'ToggleUITests/{method}()', f'ToggleUITests/{method}', f'MixerToggleUITests/ToggleUITests/{method}()']:
                        found.setdefault(method, []).append(value.get('result'))
            for nested in value.values(): visit(nested)
        elif isinstance(value, list):
            for nested in value: visit(nested)
    visit(json.loads(tests_path.read_bytes()))
    return len(nodes) == 2 and set(found) == set(METHODS) and all(value == ['Passed'] for value in found.values())


def runtime_summary(base, h, oracle, setup_ready, scope, bridge, xctest_exit, failure, cleanup_results):
    settings = None if bridge is None else bridge.settings.summary()
    results = [] if bridge is None else list(bridge.verdicts)
    cursors = {} if bridge is None else bridge.keyboard_cases
    complete = set(cursors) == {CASE} and all(c.complete is True and c.failed is False for c in cursors.values())
    path = base / 'runtime/attachment-export.json'
    export = json.loads(path.read_bytes()) if path.is_file() else None
    attachment = export is not None and export.get('passed') is True and export.get('settingsSetupObservedPassed') is True
    official = official_methods(base)
    errors = None if bridge is None else list(bridge.failures)
    ready = bridge is not None and setup_ready(bridge.settings)
    cases = bool(results) and {v.get('case') for v in results} == {CASE} and all(v.get('passed') is True and v.get('action') == 'native-keyboard' for v in results)
    export_state, reporting = getattr(h, 'attachment_export_state', {}), getattr(h, 'reporting_state', {})
    strict = complete and cases and ready and attachment and official and export_state.get('receiptDurablyCommitted') is True and reporting.get('firstFailure') is None
    cleaned = cleanup_results is not None and all(v['passed'] is True for v in cleanup_results)
    observer_path = base / 'runtime/session/command-observer/observer.json'
    observer = json.loads(observer_path.read_bytes()) if observer_path.is_file() and not observer_path.is_symlink() else None
    terminal = observer is not None and observer_terminal(observer, xctest_exit)
    return {'schema': 'mixer.apple-focus-diagnostic-runtime.1', 'scope': scope, 'diagnosticOnly': True,
        'xcodebuildExitCode': xctest_exit, 'expectedXCTestMethods': 2, 'selectedMethods': METHODS,
        'selectedApplicationCases': [CASE], 'officialTwoMethodsPassed': official,
        'completeCaseSet': complete, 'strictNativeVerdictsPassed': strict, 'bridgeFailures': errors,
        'sessionFailure': failure, 'settingsDiagnostic': settings, 'setupReadyForCases': ready,
        'publicSettingsSetupObservedPassed': attachment, 'attachmentExport': export,
        'attachmentExportReporting': export_state, 'commandReporting': reporting,
        'nativeUserInteractionVerdicts': results, 'actualNativeInputActions': len(results),
        'dependentCasesUnrun': sorted(oracle.CASES - set(cursors)), 'cleanupResults': cleanup_results,
        'commandObserver': observer, 'commandObserverTerminalEvidence': terminal,
        'runPassed': xctest_exit == 0 and strict and errors == [] and failure is None and cleaned and terminal,
        'comparatorInstalled': False, 'comparatorCredit': False, 'fullSixCaseQualification': False,
        'nativeKeyboardQualification': False, 'carrierAccepted': False, 'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}
