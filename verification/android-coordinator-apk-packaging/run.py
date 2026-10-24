#!/usr/bin/env python3
"""Root-only private coordinator run with fail-closed APK packaging checks."""
import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tarfile
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PARENT = ROOT / 'verification/android-coordinator-click-fixture/run.py'
BASE = ROOT / 'verification/android-coordinator-runner-cleanup/run.py'
HELPER = BASE.with_name('owned_process.py')
PROBE = ROOT / 'verification/android-emulator-boot-diagnosis/boot_probe.py'
CONTRACT = HERE / 'runner-contract.json'
CONTRACT_SHA256 = '7654121b8cfbb6f3d14fdb3107def2144408091f6a35e7d35b28b363e52db889'
BINDINGS = {
    'verification/android-coordinator-click-fixture/run.py': '8e09a2d95734a0287384d65590c27ee65e14611513e8da1a7b153b30ea4f82d4',
    'verification/android-coordinator-click-fixture/packet-seal-2.json': '7d67d6869f017ddb60baae9a53bd25d922ec2ee833fe00a55b0de82bdf37cc31',
    'verification/android-coordinator-click-fixture/runtime-1/receipt.json': '0f17eb3953877c60e6a8dcb09a9ff8ebdec386b0f5d83158035d78e08d60ab7e',
    'verification/android-coordinator-click-fixture/runtime-1/install-private-apk.log': '6675304125427d85369664827dda6ba2e845c913afefd882234aecda4687b66a',
}
EXECUTABLES = {
    '/opt/homebrew/share/android-commandlinetools/emulator/emulator': '5e2249e94368759aabd8fa942d2961cfef07b980a44639a2ec9b7ced3fbe2281',
    '/opt/homebrew/share/android-commandlinetools/emulator/qemu/darwin-aarch64/qemu-system-aarch64-headless': 'debac868b79f1170e64c5c202f8b39ce3dd0215c358b8d0e62ba63256ef6a819',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def transformations():
    contract = json.loads(CONTRACT.read_text())
    return [
        ('packaging-build-directory', "BUILDS = ROOT / 'verification/android-coordinator-click-fixture'",
         "BUILDS = ROOT / 'verification/android-coordinator-apk-packaging'"),
        ('packaging-archive', "ARCHIVE_SHA256 = 'feaa639b8b719492c5889222246cb62ebd4e9dd807379ccd984c5062f60660a4'",
         "ARCHIVE_SHA256 = '" + contract['buildBindings']['built-artifacts.tar.gz'] + "'"),
        ('packaging-build-metadata', 'BUILD_BINDINGS = ' + json.dumps(contract['acceptedBuildBindings'], indent=4, sort_keys=True),
         'BUILD_BINDINGS = ' + json.dumps(contract['buildBindings'], indent=4, sort_keys=True)),
        ('packaging-binding-description', 'Bind the separate runner to the 105-input test-only corrected candidate1 packet.',
         'Bind the separate runner to the 105-input APK-only packaging-corrected candidate1 packet.'),
        ('packaging-cli-help', "help='corrected test-only candidate-1 only'", "help='packaging corrected test-only candidate-1 only'"),
        ('packaging-cli-error', "parser.error('bound corrected candidate-1 and fresh runtime-N required')",
         "parser.error('bound packaging candidate-1 and fresh runtime-N required')"),
        ('packaging-before-native-bind', '    return metadata\n',
         "    metadata['packagingPreDispatch'] = _packaging_check_archive(built, metadata)\n    return metadata\n"),
        ('packaging-before-native-evidence', "                        'buildReceiptSHA256': sha(built / 'receipt.json')})",
         "                        'buildReceiptSHA256': sha(built / 'receipt.json'),\n                        'packagingPreDispatch': metadata['packagingPreDispatch']})"),
        ('packaging-before-install-recheck', "        run('install-private-apk', adb + ['install', '-r', '--no-incremental', apk], timeout=60)",
         """        save(out / 'apk-packaging-preinstall.json', _packaging_check_path(apk))
        run('apk-zipalign-preinstall', [SDK / 'build-tools/37.0.0/zipalign', '-c', '-P', '16', '-v', '4', apk])
        run('install-private-apk', adb + ['install', '-r', '--no-incremental', apk], timeout=60)"""),
    ]


def transform(source):
    changes = []
    for name, old, new in transformations():
        count = source.count(old)
        if count != 1:
            raise ValueError(f'expected exactly one source site for {name}; observed {count}')
        source = source.replace(old, new, 1)
        changes.append({'name': name, 'count': count,
            'beforeSHA256': hashlib.sha256(old.encode()).hexdigest(), 'afterSHA256': hashlib.sha256(new.encode()).hexdigest()})
    return source, changes


def load_contract():
    if sha(CONTRACT) != CONTRACT_SHA256:
        raise ValueError('APK packaging runner contract drift')
    contract = json.loads(CONTRACT.read_text())
    if contract['bindings'] != BINDINGS:
        raise ValueError('APK packaging reference bindings changed')
    for relative, expected in BINDINGS.items():
        if sha(ROOT / relative) != expected:
            raise ValueError('bound input drift: ' + relative)
    if sha(HERE / 'apk_packaging.py') != contract['packagingValidatorSHA256']:
        raise ValueError('APK packaging validator drift')
    parent = load_module('packaging_contract_parent', PARENT)
    _, probe = parent.load_contract()
    for path, expected in contract['toolBindings'].items():
        if sha(path) != expected:
            raise ValueError('packaging tool drift: ' + path)
    for relative, expected in contract['buildBindings'].items():
        if sha(HERE / 'candidate-1' / relative) != expected:
            raise ValueError('APK packaging build binding drift: ' + relative)
    metadata = json.loads((HERE / 'candidate-1/receipt.json').read_text())
    if (metadata['apkSHA256'] != contract['frozenAPK_SHA256'] or metadata['sourceClosureSHA256'] != contract['sourceClosureSHA256']
            or metadata['sourceDerivation']['changedInputs'] or not metadata['productionArtifactsUnchanged']
            or metadata['productionArtifactsRecompiled'] or not metadata['correctedInstrumentationUnchanged']
            or metadata['privateKeyRetained'] or metadata['buildScratchCleanup']['status'] != 'removed'):
        raise ValueError('APK-only packaging derivation failed')
    return contract, probe


def archive_packaging_check(built, metadata, guard):
    artifacts = json.loads((built / 'built-artifacts.json').read_text())
    with tarfile.open(built / 'built-artifacts.tar.gz', 'r:gz') as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        if len(names) != len(set(names)) or set(names) != set(artifacts):
            raise ValueError('packaging archive membership drift')
        for member in members:
            if not member.isfile() or Path(member.name).is_absolute() or '..' in Path(member.name).parts:
                raise ValueError('unsafe packaging archive member')
        data = archive.extractfile('coordinator-join.apk').read()
    if hashlib.sha256(data).hexdigest() != metadata['apkSHA256']:
        raise ValueError('pre-native APK identity drift')
    return guard.validate(data)


def load_runner():
    contract, _ = load_contract()
    parent = load_module('packaging_bound_parent_runner', PARENT)
    inherited, original, _ = parent.load_runner()
    if hashlib.sha256(original.encode()).hexdigest() != contract['acceptedConcreteRunnerSHA256']:
        raise ValueError('accepted corrected concrete runner drift')
    source, changes = transform(original)
    digest = hashlib.sha256(source.encode()).hexdigest()
    if digest != contract['transformedRunnerSHA256'] or changes != contract['sourceDeltas']:
        raise ValueError('packaging concrete runner drift')
    guard = load_module('packaging_bound_validator', HERE / 'apk_packaging.py')
    runner = ModuleType('mixer_apk_packaging_runner'); runner.__file__ = str(HERE / 'run.py')
    for name in ('_accepted_helper', '_helper_path', '_wifi_identity', '_accepted_wifi_sha_globals'):
        setattr(runner, name, getattr(inherited, name))
    runner._packaging_check_archive = lambda built, metadata: archive_packaging_check(built, metadata, guard)
    runner._packaging_check_path = guard.validate
    runner._ADAPTATION = dict(inherited._ADAPTATION, apkPackagingFixture={
        'contractSHA256': sha(CONTRACT), 'wrapperSHA256': sha(__file__),
        'acceptedCorrectedWrapperSHA256': sha(PARENT), 'acceptedConcreteRunnerSHA256': contract['acceptedConcreteRunnerSHA256'],
        'transformedRunnerSHA256': digest, 'sourceDeltas': changes,
        'packagingValidatorSHA256': sha(HERE / 'apk_packaging.py'),
        'originalInstallFailureEvidence': contract['originalInstallFailureEvidence'],
        'runtimeClaim': 'fresh install and corrected app assertions only; packaging and host fixtures alone never qualify native acceptance'})
    exec(compile(source, str(HERE / 'transformed_runner.py'), 'exec'), runner.__dict__)
    return runner, source, ''.join(difflib.unified_diff(original.splitlines(keepends=True), source.splitlines(keepends=True),
        fromfile='accepted-click-concrete-runner.py', tofile='verification/android-coordinator-apk-packaging/transformed_runner.py'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, choices=['candidate-1'])
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--execute-native', action='store_true')
    args = parser.parse_args()
    if not args.execute_native:
        parser.error('runtime is NOT RUN; --execute-native requires explicit root dispatch')
    if not re.fullmatch(r'runtime-[0-9]+', args.attempt):
        parser.error('fresh runtime-N required')
    if (HERE / args.attempt).exists() or (HERE / args.attempt).is_symlink():
        parser.error('fresh output required; existing attempts are immutable')
    runner, _, _ = load_runner()
    runner.main()


if __name__ == '__main__':
    main()
