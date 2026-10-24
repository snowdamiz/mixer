"""Independent offline source, APK, retained signature, runtime and cleanup audit."""
import gzip
import hashlib
import io
import json
import re
import tarfile
import zipfile
import review_support as support


def audit():
    upstream = support.check_upstream()
    producer, runtime = support.PRODUCER, support.RUNTIME
    candidate = producer / 'supplement-3'
    build = support.read(candidate / 'receipt.json')
    receipt = support.read(runtime / 'receipt.json')
    lock = support.read(candidate / 'source-lock.json')
    inputs = {path.name: support.bind(path) for path in sorted((candidate / 'source-used').iterdir()) if path.is_file()}
    support.need(inputs == lock['supplementInputs'], 'exact compiled fixture input snapshot')
    closure = hashlib.sha256(json.dumps({'productionClosure': lock['productionClosureSHA256'], 'supplementInputs': inputs},
                                        sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    support.need(closure == lock['sourceClosureSHA256'] == build['sourceClosureSHA256'] == receipt['sourceClosureSHA256'], 'independent compiled source closure')
    for name, binding in inputs.items():
        current = producer / name if name in ('build.py', 'support.py') else producer / 'fixture' / name
        support.need(support.bind(current) == binding, 'producer fixture source snapshot ' + name)
    for name in ('receipt.json', 'source-lock.json', 'built-artifacts.json'):
        support.need((runtime / ('component-scroll-reset-fix-build-' + name)).read_bytes() == (candidate / name).read_bytes(), 'runtime copied exact private build ' + name)
    before = support.read(runtime / 'source-identity-preinstall.json')
    after = support.read(runtime / 'source-identity-predispatch.json')
    support.need(before == after, 'runtime executable/source identity stability')
    for key in ('sourceClosureSHA256', 'apkSHA256', 'debugCertificateSHA256', 'productionSourceClosureSHA256'):
        expected = build['apk']['sha256'] if key == 'apkSHA256' else build[key]
        support.need(before[key] == expected, 'predispatch bound identity ' + key)
        if key != 'productionSourceClosureSHA256':
            support.need(receipt[key] == expected, 'runtime bound identity ' + key)
    support.need(before['privatePackage'] == 'dev.mixer.android.authoredtogglekeyboardfixture', 'exact private fixture package')
    support.need(receipt['runnerSHA256'] == support.bind(producer / 'run.py')['sha256'], 'exact completed runtime wrapper')
    support.need(support.read(producer / 'runner-contract.json')['concreteSHA256'] == support.bind(producer / 'derived-runner.py')['sha256'], 'exact completed concrete runner contract')

    # Decompression stays in bounded memory; no APK extraction or native tool run.
    with gzip.open(candidate / 'authored-toggle-supplement.apk.gz', 'rb') as stream:
        apk = stream.read(build['apk']['bytes'] + 1)
    support.need(support.data_bind(apk) == build['apk'], 'exact retained private APK bytes')
    with zipfile.ZipFile(io.BytesIO(apk)) as archive:
        names = archive.namelist()
        support.need(len(names) == len(set(names)) == 26, 'exact APK entry set without duplicates')
        entries = {name: support.data_bind(archive.read(name)) for name in names}
    support.need(entries == support.read(candidate / 'apk-entries.json'), 'independent exact APK entry hashes')
    baseline = support.ROOT / 'verification/android-authored-toggle-input/candidate-3'
    original_entries = support.read(baseline / 'apk-entries.json')
    libraries = {name: value for name, value in entries.items() if name.startswith('lib/')}
    support.need(len(libraries) == 18 and libraries == {name: value for name, value in original_entries.items() if name.startswith('lib/')}, 'eighteen unchanged native libraries')
    artifacts = support.read(candidate / 'built-artifacts.json')
    production = {name: value for name, value in artifacts.items() if name.startswith('production-classes/')}
    support.need(len(production) == 159 and production == {name: value for name, value in support.read(baseline / 'built-artifacts.json').items() if name.startswith('production-classes/')}, '159 unchanged product classes')
    private = {name: value for name, value in artifacts.items() if not name.startswith('production-classes/')}
    with tarfile.open(candidate / 'supplement-class-dex.tar.gz', 'r:gz') as archive:
        members = archive.getmembers()
        support.need(len(members) == len(private) and all(member.isfile() and member.name in private for member in members), 'finite private class/DEX archive')
        replay = {member.name: support.data_bind(archive.extractfile(member).read()) for member in members}
    support.need(replay == private and len([name for name in private if name.startswith('supplement-classes/')]) == 9, 'exact retained nine fixture classes and DEX')
    host = support.read(producer / 'host-2/receipt.json')
    support.need(host['exactDexReplay'] is True and host['replayedFixtureClasses'] == 9 and host['unchangedProductionClasses'] == 159 and host['unchangedNativeLibraries'] == 18, 'retained host exact class and DEX replay')

    commands = {row['name']: row for row in receipt['commands']}
    for row in receipt['commands']:
        support.need(support.bind(runtime / row['output'])['sha256'] == row['sha256'], 'runtime command log binding ' + row['name'])
        support.need(row.get('ownedCommandGroupCleanup', {}).get('after') == [], 'runtime command group cleanup ' + row['name'])
    certificate = build['debugCertificateSHA256']
    signatures = {}
    for name in ('apk-apksigner-predispatch', 'apk-apksigner-preinstall'):
        row = commands[name]
        text = (runtime / row['output']).read_text()
        support.need(row['exitCode'] == 0 and '\nVerifies\n' in text and 'Verified using v3 scheme (APK Signature Scheme v3): true' in text,
                     'retained official APK signature success ' + name)
        support.need(re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})', text) == [certificate], 'retained exact signing certificate ' + name)
        signatures[name] = support.bind(runtime / row['output'])
    installed = (runtime / 'installed-apk-hash.log').read_text()
    support.need(commands['install-private-apk']['exitCode'] == commands['installed-apk-hash']['exitCode'] == 0 and
                 installed.startswith(build['apk']['sha256'] + '  /data/app/') and installed.endswith('/base.apk\n') and
                 before['privatePackage'] in installed, 'installed private APK identity')
    for name in ('apk-zipalign-predispatch', 'apk-zipalign-preinstall'):
        support.need(commands[name]['exitCode'] == 0 and (runtime / commands[name]['output']).read_text().rstrip().endswith('Verification successful'), 'retained official alignment ' + name)

    payload = (runtime / 'toggle-supplement-results.json').read_bytes()
    instrument = (runtime / 'actual-native-component.log').read_bytes()
    support.need(payload == (runtime / 'native-results-export.log').read_bytes(), 'retained raw result byte identity')
    support.need(re.findall(rb'INSTRUMENTATION_RESULT: exportSHA256=([0-9a-f]{64})', instrument) == [support.data_bind(payload)['sha256'].encode()], 'native export hash binding')
    support.need(commands['actual-native-component']['exitCode'] == 0 and b'INSTRUMENTATION_RESULT: status=passed-component-only\n' in instrument and b'INSTRUMENTATION_CODE: -1\n' in instrument, 'native terminal component status')
    for field, name in [('diagnosticSHA256', 'diagnostic-private-fixture.log'), ('scrollTraceSHA256', 'scroll-private-trace.log')]:
        support.need(re.findall(('INSTRUMENTATION_RESULT: ' + field + '=([0-9a-f]{64})').encode(), instrument) == [support.bind(runtime / name)['sha256'].encode()], 'native immutable diagnostic hash ' + field)
    scroll = receipt['scrollDiagnostics']
    support.need(scroll['traceValid'] is True and scroll['instrumentationHashVerified'] is True and scroll['completedScrollCases'] == [18, 19] and scroll['entryCount'] == 162, 'retained native original scroll evidence')
    for row in scroll['conjunctStates']:
        state = row['state']
        support.need(state['scrollY'] == 365 and state['zeroProposals'] is True and state['notPressed'] is True and state['proposals'] == 0 and state['pressed'] is False, 'retained original native scroll conjuncts')

    support.need(receipt['status'] == 'failed-native-attempt-retained' and receipt['failure'] == "ValueError('native mode trace exact schema')", 'original failed outer collection preserved')
    support.need(receipt['target']['ro.kernel.qemu'] == '1' and receipt['target']['ro.build.version.sdk'] == '37' and receipt['physicalTargetsQueried'] is False, 'actual emulator-only environment')
    support.need(receipt['cleanup'] == 'stopped' and receipt['ownedEmulatorGroupCleanup']['after'] == [], 'retained owned emulator stopped')
    for port in ('5586', '5587'):
        row = commands['port-after-' + port]
        support.need(row['exitCode'] == 1 and support.bind(runtime / row['output'])['bytes'] == 0, 'retained owned port released ' + port)
    support.need(commands['stop-only-owned-emulator']['exitCode'] == 0, 'retained exact owned-emulator stop')
    cleanup = receipt['extractionCleanup']
    support.need(cleanup['status'] == 'removed' and cleanup['pathAbsentAfterCleanup'] is True and not (runtime / '.build').exists(), 'native extraction absent now and in retained receipt')
    support.need(cleanup['openHoldersCheck']['exitCode'] == 1 and support.bind(runtime / cleanup['openHoldersCheck']['output'])['bytes'] == 0, 'retained native extraction had no open holders')

    focus = support.read_bytes(payload)['keyboardSetup']
    return {
        'schema': 1, 'status': 'passed-independent-offline-source-apk-runtime-cleanup-audit', 'upstream': upstream,
        'sourceRevision': receipt['sourceRevision'], 'productionTreeDigest': lock['productionClosureSHA256'],
        'productionTreeDigestAlgorithm': before['sourceTreeAlgorithm'], 'fixtureSourceClosureSHA256': closure,
        'fixtureSourceInputs': inputs, 'compiledAPK': build['apk'], 'privatePackage': before['privatePackage'],
        'unchangedProductClasses': len(production), 'unchangedNativeLibraries': len(libraries),
        'fixtureClasses': 9, 'retainedHostExactClassAndDexReplay': support.bind(producer / 'host-2/receipt.json'),
        'signatureEvidence': {'debugCertificateSHA256': certificate, 'retainedOfficialVerifierLogs': signatures,
                              'verificationScope': 'exact sealed official verifier outputs and APK/certificate identity rechecked offline; native verifier not rerun'},
        'buildToolBindings': build['tools'], 'runtimeToolVersions': {name: (runtime / (name + '-version.log')).read_text()
                                                                   for name in ('python', 'adb', 'emulator')},
        'runtimeTarget': receipt['target'], 'nativeCompleted': {'cases': 45, 'originalAssertions': 213, 'setupAssertions': 26,
                                                               'totalAssertions': 239, 'countedMotionEvents': 118,
                                                               'knownUncountedHistoricalMotionEvents': 1,
                                                               'separateKeyboardSetupKeys': 8},
        'observedSerializerSequences': {'nativeKeyTrace': [row['sequence'] for row in focus['nativeKeyTrace']],
                                        'nativeModeTrace': [row['sequence'] for row in focus['nativeModeTrace']]},
        'originalOuterCollector': {'status': receipt['status'], 'failure': receipt['failure'],
                                    'receiptBinding': support.bind(runtime / 'receipt.json')},
        'cleanup': {'retainedNativeOwnedInstance': receipt['ownedInstance'], 'retainedNativeStatus': receipt['cleanup'],
                    'ownedCommandGroupAfter': [], 'ownedPortsReleasedInRetainedEvidence': [5586, 5587],
                    'retainedExtractionCleanup': cleanup, 'nativeExtractionAbsentNow': True,
                    'scope': 'offline filesystem and sealed cleanup evidence only; no live native/process query'},
        'nativeCommandsExecuted': 0, 'CUACommandsExecuted': 0, 'GitCommandsExecuted': 0,
        'physicalPhones': 'deferred disconnected', 'rootIndependentAcceptance': 'pending',
        'screenshotPixelAcceptance': 'pending root visual review', 'engineAuthority': 'not established',
        'AppleParity': 'pending', 'publishedFieldLogQualification': 'pending', 'GA': 'not accepted',
        'extraSourceEvidenceBindings': {str(path.relative_to(support.ROOT)): support.bind(path) for path in
                                        (baseline / 'apk-entries.json', baseline / 'built-artifacts.json')},
    }
