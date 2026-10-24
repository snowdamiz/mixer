#!/usr/bin/env python3
"""Independently inspect retained private join artifacts and frozen source identities, headlessly."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile
import zipfile
from run import validate_members

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True)
    parser.add_argument('--attempt', required=True, help='fresh headless-review-N')
    args = parser.parse_args()
    if not re.fullmatch(r'candidate-[0-9]+', args.build) or not re.fullmatch(r'headless-review-[0-9]+', args.attempt):
        parser.error('bounded fresh candidate-N/headless-review-N required')
    out = HERE / args.attempt
    out.mkdir()
    built = HERE / args.build
    receipt = json.loads((built / 'receipt.json').read_text())
    result = {'status': 'failed', 'reviewer': 'lane headless artifact verifier; not root/native acceptance',
              'verifierSHA256': sha(Path(__file__)), 'buildReceiptSHA256': sha(built / 'receipt.json'),
              'nativeRuntime': 'NOT RUN', 'nativeAssertionsExecuted': 0,
              'gaAcceptance': False, 'nativeAcceptance': False}
    try:
        assert receipt['status'] == 'actual-private-apk-built-runtime-NOT-RUN'
        assert receipt['sourceUnchanged'] and receipt['privateKeyRetained'] is False
        assert receipt['compiledMinAPI'] == 36 and receipt['sourceSDKTargetTripleAPI'] == 28
        assert receipt['actuallyQualifiedRuntimeAPI'] is None
        assert receipt['hostLeavesPackaged'] is False
        seal = json.loads((built / 'artifact-seal.json').read_text())
        for relative, expected in seal.items():
            path = built / relative
            assert path.is_file() and path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'], relative
        locked = json.loads((built / 'source-lock.json').read_text())
        files = locked['files']
        assert hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == receipt['sourceClosureSHA256']
        for relative, expected in files.items():
            assert sha(built / 'inputs' / relative) == expected, relative
            assert sha(ROOT / relative) == expected, 'live source drift ' + relative
        for relative in ['verification/android-coordinator-join/build.py',
                         'verification/android-coordinator-join/run.py',
                         'verification/android-coordinator-join/owned_process.py',
                         'verification/android-coordinator-join/test_runner.py']:
            assert relative in files
        # Bind the concrete renderer production closure to root's accepted candidate16.
        acceptance_path = ROOT / 'verification/android-native-appearance-v2/candidate-16-root-review/acceptance.json'
        acceptance = json.loads(acceptance_path.read_text())
        assert acceptance['reviewer'] == 'root' and acceptance['result']['status'] == 'passed'
        accepted_path = 'verification/android-native-appearance-v2/candidate-16/receipt.json'
        assert sha(ROOT / accepted_path) == acceptance['bindings'][accepted_path]
        accepted = json.loads((ROOT / accepted_path).read_text())
        renderer_sources = [name for name in receipt['compiledProductionSources']
                            if not name.endswith('/NativeBridge.java') and not name.endswith('/NativeCoordinatorV2.java')]
        for relative in renderer_sources:
            assert files[relative] == accepted['sourceManifest'][relative], relative
        for command in receipt['commands']:
            assert command['exitCode'] == 0, command['name']
            assert sha(built / command['output']) == command['sha256']
            assert command['ownedCommandGroupCleanup']['after'] == []
        guards = (built / 'headless-runner-guards.log').read_text()
        assert 'Ran 4 tests' in guards and '\nOK\n' in guards
        artifacts = json.loads((built / 'built-artifacts.json').read_text())
        archive_path = built / 'built-artifacts.tar.gz'
        assert sha(archive_path) == receipt['builtArchiveSHA256']
        work = out / '.build'
        work.mkdir()
        with tarfile.open(archive_path, 'r:gz') as archive:
            members = archive.getmembers()
            validate_members(members, artifacts)
            archive.extractall(work, members=members, filter='data')
        for relative, expected in artifacts.items():
            assert sha(work / relative) == expected['sha256'], relative
            assert not relative.endswith('.keystore')
            assert 'HostLeaves' not in relative
            if relative.endswith('.class'):
                assert '/dev/mixer/android/' in relative, 'SDK/test leaf class packaged ' + relative
        coordinator = work / 'production-classes/dev/mixer/android/NativeCoordinatorV2.class'
        assert sha(coordinator) == receipt['coordinatorClassSHA256']
        apk = work / 'coordinator-join.apk'
        assert sha(apk) == receipt['apkSHA256']
        entries = json.loads((built / 'apk-entries.json').read_text())
        with zipfile.ZipFile(apk) as archive:
            assert set(archive.namelist()) == set(entries)
            for relative, expected in entries.items():
                assert hashlib.sha256(archive.read(relative)).hexdigest() == expected['sha256'], relative
                if relative.endswith('.so'):
                    assert relative.startswith('lib/arm64-v8a/')
                    assert expected['sha256'] == sha(work / 'apk' / relative)
                if relative.endswith('.dex'):
                    assert expected['sha256'] == sha(work / 'dex' / relative)
            assert hashlib.sha256(archive.read('assets/MixerAppearanceV2/descriptor.json')).hexdigest() == receipt['descriptorSHA256']
        certs = re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})',
                           (built / 'private-debug-signature-cert.log').read_text())
        assert certs == [receipt['debugCertificateSHA256']]
        result.update({'status': 'passed-headless-private-apk-identity-and-build-only',
                       'sourceRevision': receipt['sourceRevision'], 'sourceClosureSHA256': receipt['sourceClosureSHA256'],
                       'apkSHA256': receipt['apkSHA256'], 'debugCertificateSHA256': receipt['debugCertificateSHA256'],
                       'retainedBuiltArtifacts': len(artifacts), 'sourceInputs': len(files),
                       'rootAcceptedRendererSourcesMatched': len(renderer_sources),
                       'successfulBuildCommands': len(receipt['commands']), 'headlessRunnerGuardTestsPassed': 4,
                       'actualCompiledClosure': ['ordinary Swift Android engine and SessionRegistry', 'actual C JNI bridge',
                           'production NativeBridge/NativeCoordinatorV2', 'root-accepted concrete native renderer',
                           'verification-owned native Activity/Instrumentation'],
                       'limitations': receipt['limitations']})
    except BaseException as failure:
        result['failure'] = repr(failure)
        raise
    finally:
        (out / 'receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
