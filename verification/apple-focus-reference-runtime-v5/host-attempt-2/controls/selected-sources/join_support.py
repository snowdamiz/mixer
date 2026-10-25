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
METHODS = ['test000PublicSettingsFullKeyboardAccess', 'test010ReferenceFirstTab']
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


"""Appended to the frozen diagnostic adapter in the selected runtime only.

No import invokes native tools. Root supplies one fresh selection before dispatch.
"""
import importer
import reference_contract
import auxiliary_inventory
_ROOT = None
_OFFICIAL = None
_ORIGINAL_SELECT = select_command
_ORIGINAL_RUN_OBSERVED = run_observed


def configure_root(selection):
    global _ROOT
    require(_ROOT is None, 'Root selection already configured')
    _ROOT = importer.validate_root(selection)


def select_command(h, argv, session):
    require(_ROOT is not None and list(map(str,argv)) == importer.command_argv(_ROOT,session), 'Command must come from root-selected context')
    require(session.resolve() == session and session.is_dir() and not session.is_symlink() and session.name == 'session' and session.parent.name == 'runtime' and session.parent.parent.name == 'native-run-v4-'+_ROOT['runID'], 'Root-selected fresh result workspace required')
    require(not (session/'session.xcresult').exists() and not (session/'session.xcresult').is_symlink(), 'Result bundle exists before dispatch; replay refused')
    _ORIGINAL_SELECT(h,argv,session)
    _selected['sessionIdentity'] = path_identity(session,0o700)
    _selected['rootSHA256'] = sha(importer.stable(_ROOT))



def path_identity(path, mode=None):
    require(path.resolve() == path and path.is_dir() and not path.is_symlink(), 'Canonical owned directory required')
    info = path.lstat()
    require(mode is None or stat.S_IMODE(info.st_mode) == mode, 'Owned directory mode changed')
    return (info.st_dev,info.st_ino,info.st_uid)


def run_observed(commands, argv, timeout, check, retained_stdout_filter):
    result = _ORIGINAL_RUN_OBSERVED(commands,argv,timeout,check,retained_stdout_filter)
    require(path_identity(_selected['session'],0o700) == _selected['sessionIdentity'], 'Selected session identity changed during command')
    _selected['resultIdentity'] = path_identity(_selected['session']/'session.xcresult')
    return result


def observer_terminal(summary, code, argv=None):
    # The observer's own full stream binding is checked again at final import.
    cleanup = summary.get('cleanup',{})
    return (summary.get('schema') == 'mixer.apple-command-finalization-observer.2'
        and type(code) is int and summary.get('exitCode') == code
        and (argv is None or summary.get('argv') == argv)
        and summary.get('startNewSession') is True
        and summary.get('ownedProcessGroup',{}).get('state') == 'absent'
        and ((cleanup.get('attempted') is True and cleanup.get('complete') is True)
             or (cleanup.get('attempted') is False and cleanup.get('complete') is None and cleanup.get('signals') == []))
        and set(summary.get('streams',{})) == {'stdout','stderr'}
        and all(row.get('eof') is True and row.get('readerFailed') is False and row.get('readerErrors') == [] for row in summary['streams'].values())
        and summary.get('successInferredFromConsoleOrMarkers') is False)



def application_captures(output):
    captures, auxiliary = auxiliary_inventory.validate(output/'runtime/captures',_ROOT['ownedSimulatorIdentity'])
    return captures


def capture_official(commands, base_run, h, output):
    """Called by the selected command wrapper; bytes originate in actual tool returns.

    Matching IDs in stored evidence cannot call this path or replace its outputs.
    """
    global _OFFICIAL
    require(_selected is not None and _selected['called'] and _OFFICIAL is None, 'Exactly one actual selected command capture required')
    session = _selected['session']
    require(_selected['rootSHA256'] == sha(importer.stable(_ROOT)) and session == output/'runtime/session' and h.RUN_DIR == output/'runtime', 'Official capture differs from root-selected run/path')
    require(path_identity(session,0o700) == _selected['sessionIdentity'] and path_identity(session/'session.xcresult') == _selected['resultIdentity'], 'Official result/session path identity substituted')
    official = {}; invocations = []
    for kind in ['summary','tests']:
        argv = ['/usr/bin/xcrun','xcresulttool','get','test-results',kind,'--path',str(session/'session.xcresult')]
        code, stdout, stderr = base_run(commands,argv,check=False)
        require(type(code) is int and code == 0, 'Official result traversal command failed')
        raw = stdout.encode('utf-8')
        importer.parse(raw)
        invocations.append({'argv':argv,'exitCode':code,'stdoutSHA256':sha(raw),'stderrSHA256':sha(stderr.encode('utf-8'))})
        official[kind] = raw
        path = output/'runtime'/('xctest-'+kind+'.json')
        with path.open('xb') as stream: stream.write(raw)
    # Read only the export generated by the exact selected command wrapper.
    retained = importer.read(output/'runtime/attachment-export.json')
    require(retained.get('ownedResultPath') == str(session/'session.xcresult') and retained.get('exitCode') == 0 and retained.get('passed') is True, 'Selected official attachment export failed')
    folder = output/'runtime/attachments'
    manifest = folder/'manifest.json'
    require(manifest.is_file() and not manifest.is_symlink(), 'Selected official manifest absent')
    official['manifest'] = manifest.read_bytes()
    # Traverse actual official execution identities before attachment bytes are joined.
    observer = importer.read(session/'command-observer/observer.json')
    importer.official_methods(importer.parse(official['summary']),importer.parse(official['tests']),_ROOT,observer['exitCode'],importer.decimal_document(official['summary']))
    payloads = {}
    for name, row in retained['files'].items():
        require(Path(name).name == name, 'Nested attachment refused')
        path = folder/name
        require(path.is_file() and not path.is_symlink() and path.resolve() == path, 'Attachment export entry redirected')
        raw = path.read_bytes()
        require(len(raw) == row['bytes'] and sha(raw) == row['sha256'], 'Attachment bytes changed before capture')
        if name != 'manifest.json': payloads[name] = raw
    require({path.name for path in folder.iterdir()} == set(retained['files']), 'Attachment export inventory changed')
    require(path_identity(session,0o700) == _selected['sessionIdentity'] and path_identity(session/'session.xcresult') == _selected['resultIdentity'], 'Official result/session substituted during traversal')
    captures = application_captures(output)
    captured = {'official':importer.CapturedOfficial(importer._CAPTURE_TOKEN,_ROOT,session,observer['exitCode'],official,payloads,captures),'payloads':payloads,'captures':captures,'runID':_ROOT['runID'],'argv':list(_selected['argv'])}
    receipt = {'schema':'mixer.apple-focus-reference-official-capture.1','runID':_ROOT['runID'],'rootSelectionSHA256':sha(importer.stable(_ROOT)), 'argv':_selected['argv'],'officialSHA256':{k:sha(v) for k,v in official.items()},'payloadSHA256':{k:sha(v) for k,v in payloads.items()},'applicationCaptureSHA256':{k:sha(v) for k,v in captures.items()},'officialToolInvocations':invocations,'sessionIdentity':list(_selected['sessionIdentity']),'resultIdentity':list(_selected['resultIdentity']),'nativeQualification':False}
    with (output/'runtime/official-capture.json').open('xb') as stream:
        stream.write(importer.stable(receipt));stream.flush();os.fsync(stream.fileno())
    _OFFICIAL = captured


def runtime_summary(base, h, oracle, setup_ready, scope, bridge, xctest_exit, failure, cleanup_results):
    report = {'schema':'mixer.apple-focus-reference-runtime.5','diagnosticOnly':True,'diagnosticOutcome':'unknown','runPassed':False,'strictNativeVerdictsPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred','cleanupResults':cleanup_results,'sessionFailure':failure,'xcodebuildExitCode':xctest_exit,'selectedMethods':list(importer.METHODS),'selectedApplicationCases':[importer.CASE],'actualNativeInputActions':None}
    if cleanup_results is None or _OFFICIAL is None: return report
    try:
        require(_OFFICIAL['runID'] == _ROOT['runID'] and _OFFICIAL['argv'] == _selected['argv'], 'Official capture belongs to another dispatch')
        require(failure is None and getattr(h,'reporting_state',{}).get('firstFailure') is None, 'Runtime command/reporting failure prevents diagnostic import')
        require(bridge is not None and list(bridge.failures) == [] and setup_ready(bridge.settings), 'Durable Settings completion required')
        session = _selected['session']; observer_dir = session/'command-observer'
        captures = application_captures(base)
        require(captures == _OFFICIAL['captures'], 'Application observations changed after selected official capture')
        imported = importer.import_selected(_ROOT,session,importer.read(observer_dir/'observer.json'),{name:(observer_dir/(name+'.log')).read_bytes() for name in ['stdout','stderr']},_OFFICIAL['official'],_OFFICIAL['payloads'],captures,cleanup_results,oracle,reference_contract)
        report.update(imported,actualNativeInputActions=imported['keyInjectionCount'],settingsDiagnostic=bridge.settings.summary(),bridgeFailures=list(bridge.failures))
    except (KeyError,ValueError,TypeError,OSError,OverflowError,RecursionError) as error:
        report.update(diagnosticOutcome='invalid-or-incomplete-evidence',failure=type(error).__name__+': '+str(error))
    return report
