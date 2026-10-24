#!/usr/bin/env python3
"""Execute the frozen coordinator runner with a separately bound Wi-Fi fallback."""
import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'verification/android-coordinator-runner-cleanup/run.py'
HELPER = BASE.with_name('owned_process.py')
PROBE = ROOT / 'verification/android-emulator-boot-diagnosis/boot_probe.py'
BOOT_RECEIPT = PROBE.parent / 'boot-probe-1/receipt.json'
CONTRACT = HERE / 'runner-contract.json'
CONTRACT_SHA256 = 'a9ce1c1575e6c51c7723c01658240ac8acd408ff452d85be97f6315ed95f4f9b'
BINDINGS = {
    'verification/android-coordinator-runner-cleanup/run.py': 'cc77d1e449b0f946e12d1ed345b29a8eed392e635462c70c76e81c84714f225e',
    'verification/android-coordinator-runner-cleanup/owned_process.py': '209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216',
    'verification/android-coordinator-runner-cleanup/test_cleanup.py': 'c8f9763c2e891c808fcc84c9eea0f511a4968ffd4490d2c5eeb05d124229ca05',
    'verification/android-coordinator-runner-cleanup/test_runner_guards.py': 'cc565c8ef305c217fb90203c4f9e3a4b4fe0cc33725167ea143cce212d4031e8',
    'verification/android-emulator-boot-diagnosis/boot_probe.py': '97acdc54e9f45e5a08ab629154101e97328886e63460e21dae0019962827b366',
    'verification/android-emulator-boot-diagnosis/probe-contract.json': '954c48ab47b5b3da0c3aaca3b0e65b7c0727771dc8a9b39234e617bdb02bbec4',
    'verification/android-emulator-boot-diagnosis/boot-probe-1/receipt.json': '3dc7a3ad26bd6c0747bf41b9c5f682aead15987ae5b973bf1d64a7cc2dae5beb',
}
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
    """Each concrete source site must occur exactly once in the immutable base."""
    changes = [
        ('accepted-helper-import', 'from owned_process import execute, stop_group',
         'execute, stop_group = _accepted_helper.execute, _accepted_helper.stop_group'),
        ('candidate-helper-binding', "if sha(HERE / 'owned_process.py') != PROCESS_HELPER_SHA256:",
         'if sha(_helper_path) != PROCESS_HELPER_SHA256:'),
        ('receipt-helper-binding', "'ownedProcessHelperSHA256': sha(HERE / 'owned_process.py'),",
         "'ownedProcessHelperSHA256': sha(_helper_path), 'adaptation': _ADAPTATION,"),
        ('exact-headless-identity', '''    tokens = shlex.split(command)
    if not tokens or tokens[0] != str(pid):
        return False
    if not any(Path(token).name in ('emulator', 'qemu-system-aarch64') for token in tokens[1:2]):
        return False
    return all(tokens.count(flag) == 1 and tokens.index(flag) + 1 < len(tokens)
               and tokens[tokens.index(flag) + 1] == value
               for flag, value in [('-port', str(PORT)), ('-avd', AVD)])''',
         '    return _wifi_identity(command, pid)'),
        ('fallback-after-base-session-equality', '''        if session['argv'] != expected_argv or session['serial'] != SERIAL:
            raise ValueError('bounded owned-instance contract changed')''',
         '''        if session['argv'] != expected_argv or session['serial'] != SERIAL:
            raise ValueError('bounded owned-instance contract changed')
        expected_argv += ['-feature', '-WiFiPacketStream']'''),
        ('current-runner-source-evidence', "        run('python-version', [sys.executable, '--version'])",
         """        _, revision = run('runner-source-revision', ['git', 'rev-parse', 'HEAD'])
        _, tree = run('runner-source-tree', ['git', 'rev-parse', 'HEAD^{tree}'])
        receipt['adaptation']['runnerSourceRevision'] = revision.decode().strip()
        receipt['adaptation']['runnerSourceTree'] = tree.decode().strip()
        run('python-version', [sys.executable, '--version'])"""),
    ]
    for label in ('use', 'stop', 'terminate', 'kill'):
        # The four distinct use/stop/fallback source sites are individually counted.
        old = "run('owned-process-before-" + label + "', ['ps', '-p', str(process.pid), '-o', 'pid=,command='])"
        changes.append(('owned-pgid-before-' + label, old, old.replace('pid=,command=', 'pid=,pgid=,command=')))
    return changes


def transform(source):
    applied = []
    for name, old, new in transformations():
        count = source.count(old)
        if count != 1:
            raise ValueError(f'expected exactly one source site for {name}; observed {count}')
        source = source.replace(old, new, 1)
        applied.append({'name': name, 'count': count,
                        'beforeSHA256': hashlib.sha256(old.encode()).hexdigest(),
                        'afterSHA256': hashlib.sha256(new.encode()).hexdigest()})
    return source, applied


def load_contract():
    if sha(CONTRACT) != CONTRACT_SHA256:
        raise ValueError('Wi-Fi runner contract drift')
    contract = json.loads(CONTRACT.read_text())
    if contract['bindings'] != BINDINGS or contract['executableBindings'] != EXECUTABLES:
        raise ValueError('Wi-Fi runner bindings differ from accepted contract')
    for relative, expected in BINDINGS.items():
        if sha(ROOT / relative) != expected:
            raise ValueError('bound input drift: ' + relative)
    for path, expected in EXECUTABLES.items():
        if sha(path) != expected:
            raise ValueError('installed owned executable drift: ' + path)
    probe = load_module('mixer_wifi_bound_probe', PROBE)
    probe_contract = probe.load_contract()
    receipt = json.loads(BOOT_RECEIPT.read_text())
    if (receipt['status'] != 'boot-only-diagnostic-passed' or receipt['cleanup'] != 'stopped'
            or receipt['apkInstalled'] or receipt['appAssertionsRun'] or receipt['physicalTargetsQueried']
            or receipt['ownedEmulatorGroupCleanup']['after']
            or receipt['ownedInstance']['argv'] != probe_contract['argv']):
        raise ValueError('successful cleaned boot-only evidence required')
    return contract, probe


def owned_identity(command, pid, probe):
    # The accepted boot guard checks exact installed paths and all launch contracts.
    # Re-hash the observed executable at EVERY use/cleanup authorization decision.
    if not probe.owned_identity(command, pid, pid):
        return False
    tokens = probe.shlex.split(command.strip().split(None, 2)[2])
    path = tokens[0]
    try:
        return path in EXECUTABLES and sha(path) == EXECUTABLES[path]
    except OSError:
        return False


def load_runner():
    contract, probe = load_contract()
    original = BASE.read_text()
    source, changes = transform(original)
    digest = hashlib.sha256(source.encode()).hexdigest()
    if digest != contract['transformedRunnerSHA256'] or changes != contract['sourceDeltas']:
        raise ValueError('concrete transformed runner differs from accepted contract')
    helper = load_module('mixer_wifi_bound_helper', HELPER)
    runner = ModuleType('mixer_wifi_adapted_runner')
    runner.__file__ = str(HERE / 'run.py')
    runner._accepted_helper = helper
    runner._helper_path = HELPER
    runner._wifi_identity = lambda command, pid: owned_identity(command, pid, probe)
    runner._ADAPTATION = {
        'schema': 1, 'contractSHA256': sha(CONTRACT), 'adapterSHA256': sha(__file__),
        'baseRunnerPath': str(BASE.relative_to(ROOT)), 'baseRunnerSHA256': sha(BASE),
        'transformedRunnerSHA256': digest, 'sourceDeltas': changes,
        'acceptedProbeSHA256': sha(PROBE), 'acceptedProbeContractSHA256': sha(probe.CONTRACT),
        'successfulBootOnlyReceiptSHA256': sha(BOOT_RECEIPT),
        'executableBindings': EXECUTABLES, 'argvDelta': ['-feature', '-WiFiPacketStream'],
        'knownLimitation': contract['knownLimitation'],
        'runtimeClaim': 'actual unchanged APK assertions only; boot evidence and host fixtures alone never qualify app acceptance',
        'physicalPhoneMatrix': 'deferred; phones disconnected',
    }
    exec(compile(source, str(HERE / 'transformed_runner.py'), 'exec'), runner.__dict__)
    return runner, source, ''.join(difflib.unified_diff(
        original.splitlines(keepends=True), source.splitlines(keepends=True),
        fromfile=str(BASE.relative_to(ROOT)), tofile='verification/android-coordinator-wifi-runner/transformed_runner.py'))


def main():
    # Check dispatch and the fresh bounded output name before binding or native work.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, choices=['candidate-2'])
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--execute-native', action='store_true')
    args = parser.parse_args()
    if not args.execute_native:
        parser.error('runtime is NOT RUN; --execute-native requires explicit root dispatch')
    import re
    if not re.fullmatch(r'runtime-[0-9]+', args.attempt):
        parser.error('fresh runtime-N required')
    if (HERE / args.attempt).exists() or (HERE / args.attempt).is_symlink():
        parser.error('fresh output required; existing attempts are immutable')
    runner, _, _ = load_runner()
    runner.main()


if __name__ == '__main__':
    main()
