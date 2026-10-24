#!/usr/bin/env python3
"""Root-dispatched corrected instrumentation using the accepted Wi-Fi runner."""
import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WIFI = ROOT / 'verification/android-coordinator-wifi-runner/run.py'
BASE = ROOT / 'verification/android-coordinator-runner-cleanup/run.py'
HELPER = BASE.with_name('owned_process.py')
PROBE = ROOT / 'verification/android-emulator-boot-diagnosis/boot_probe.py'
CONTRACT = HERE / 'runner-contract.json'
CONTRACT_SHA256 = '6cb78b235730f9f8557ba2221b8ac292f0418e1aa838c22d38028fdebf9c6e76'
BINDINGS = {'verification/android-coordinator-wifi-runner/run.py':
    'f1c5d48aee17eaee472ced89c9e09f878f7088eab610429e3f702981467bcaff',
    'verification/android-coordinator-wifi-runner/runtime-1/receipt.json':
    'e5efafd64bdc53b649628c12744d32ac42c67a6391c2726d425f6b37dd2aca2a',
    'verification/android-coordinator-wifi-runner/runtime-1/native-results.json':
    'ef6210f55d0a01e080e08b56cc07bf27c8c0a7fd224435d2687603e4f145a34c'}
EXECUTABLES = {
    '/opt/homebrew/share/android-commandlinetools/emulator/emulator': '5e2249e94368759aabd8fa942d2961cfef07b980a44639a2ec9b7ced3fbe2281',
    '/opt/homebrew/share/android-commandlinetools/emulator/qemu/darwin-aarch64/qemu-system-aarch64-headless': 'debac868b79f1170e64c5c202f8b39ce3dd0215c358b8d0e62ba63256ef6a819',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def transformations():
    contract = json.loads(CONTRACT.read_text())
    old_bindings = '''BUILD_BINDINGS = {
    'receipt.json': '0a2493763af34e9de77fc80a6bf18258ece94d8d30c57ca041c83d6af8d32bb5',
    'source-lock.json': '31cb65d8dc08d4741ced3dd7130f418c0805d0ff35760cb85a7895d69733e12f',
    'built-artifacts.json': 'c02f45553610fc7c22e168a7d19e306daed148630e67f5b670228ddf278cb77a',
    'built-artifacts.tar.gz': ARCHIVE_SHA256,
}'''
    return [
        ('derived-build-directory', "BUILDS = ROOT / 'verification/android-coordinator-join'",
         "BUILDS = ROOT / 'verification/android-coordinator-click-fixture'"),
        ('derived-source-closure', "SOURCE_CLOSURE_SHA256 = 'ec2acb7c78862d899a4722d8f2c11d90d47c2cc4726af00976d392536fb85b30'",
         "SOURCE_CLOSURE_SHA256 = '" + contract['sourceClosureSHA256'] + "'"),
        ('derived-archive', "ARCHIVE_SHA256 = '642962760271300298db98efd9f2018c159a2e9767843e4ef2bad84d9f824459'",
         "ARCHIVE_SHA256 = '" + contract['buildBindings']['built-artifacts.tar.gz'] + "'"),
        ('derived-build-metadata', old_bindings, 'BUILD_BINDINGS = ' + json.dumps(contract['buildBindings'], indent=4, sort_keys=True)),
        ('derived-build-cli-help', "help='unchanged retained candidate-2 only'", "help='corrected test-only candidate-1 only'"),
        ('derived-build-cli-choice', "if args.build != 'candidate-2' or not re.fullmatch", "if args.build != 'candidate-1' or not re.fullmatch"),
        ('derived-build-cli-error', "parser.error('bound candidate-2 and fresh runtime-N required')",
         "parser.error('bound corrected candidate-1 and fresh runtime-N required')"),
        ('derived-binding-description', 'Bind the separate runner to the unchanged 105-input candidate2 packet.',
         'Bind the separate runner to the 105-input test-only corrected candidate1 packet.'),
    ]


def transform(source):
    changes = []
    for name, old, new in transformations():
        count = source.count(old)
        if count != 1:
            raise ValueError(f'expected exactly one source site for {name}; observed {count}')
        source = source.replace(old, new, 1)
        changes.append({'name': name, 'count': count,
            'beforeSHA256': hashlib.sha256(old.encode()).hexdigest(),
            'afterSHA256': hashlib.sha256(new.encode()).hexdigest()})
    return source, changes


def load_contract():
    if sha(CONTRACT) != CONTRACT_SHA256:
        raise ValueError('corrected fixture runner contract drift')
    contract = json.loads(CONTRACT.read_text())
    if contract['bindings'] != BINDINGS:
        raise ValueError('corrected fixture references changed')
    for relative, expected in BINDINGS.items():
        if sha(ROOT / relative) != expected:
            raise ValueError('bound input drift: ' + relative)
    wifi = load_module('click_bound_accepted_wifi', WIFI)
    _, probe = wifi.load_contract()
    for relative, expected in contract['buildBindings'].items():
        if sha(HERE / 'candidate-1' / relative) != expected:
            raise ValueError('corrected build binding drift: ' + relative)
    receipt = json.loads((HERE / 'candidate-1/receipt.json').read_text())
    if (receipt['sourceClosureSHA256'] != contract['sourceClosureSHA256']
            or receipt['apkSHA256'] != contract['frozenAPK_SHA256']
            or not receipt['productionArtifactsUnchanged'] or receipt['productionArtifactsRecompiled'] != 0
            or receipt['sourceDerivation']['changedInputs'] != ['verification/android-coordinator-join/CoordinatorJoinInstrumentation.java']
            or receipt['privateKeyRetained'] or receipt['buildScratchCleanup']['status'] != 'removed'):
        raise ValueError('corrected test-only derivation contract failed')
    return contract, probe


def load_runner():
    contract, _ = load_contract()
    wifi = load_module('click_accepted_wifi_runner', WIFI)
    inherited, original, _ = wifi.load_runner()
    if hashlib.sha256(original.encode()).hexdigest() != contract['acceptedConcreteRunnerSHA256']:
        raise ValueError('accepted concrete runner drift')
    source, changes = transform(original)
    digest = hashlib.sha256(source.encode()).hexdigest()
    if digest != contract['transformedRunnerSHA256'] or changes != contract['sourceDeltas']:
        raise ValueError('corrected concrete runner differs from contract')
    runner = ModuleType('mixer_click_fixture_runner')
    runner.__file__ = str(HERE / 'run.py')
    runner._accepted_helper = inherited._accepted_helper
    runner._helper_path = inherited._helper_path
    runner._wifi_identity = inherited._wifi_identity
    runner._accepted_wifi_sha_globals = inherited._wifi_identity.__globals__
    runner._ADAPTATION = dict(inherited._ADAPTATION, correctedClickFixture={
        'contractSHA256': sha(CONTRACT), 'wrapperSHA256': sha(__file__),
        'acceptedWiFiWrapperSHA256': sha(WIFI),
        'acceptedConcreteRunnerSHA256': contract['acceptedConcreteRunnerSHA256'],
        'transformedRunnerSHA256': digest, 'sourceDeltas': changes,
        'buildBindings': contract['buildBindings'], 'sourceClosureSHA256': contract['sourceClosureSHA256'],
        'originalFailureEvidence': contract['originalFailureEvidence'],
        'runtimeClaim': 'fresh corrected fixture assertions only; host tests do not qualify app acceptance'})
    exec(compile(source, str(HERE / 'transformed_runner.py'), 'exec'), runner.__dict__)
    return runner, source, ''.join(difflib.unified_diff(original.splitlines(keepends=True),
        source.splitlines(keepends=True), fromfile='accepted-wifi-concrete-runner.py',
        tofile='verification/android-coordinator-click-fixture/transformed_runner.py'))


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
