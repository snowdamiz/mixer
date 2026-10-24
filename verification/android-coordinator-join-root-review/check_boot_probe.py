#!/usr/bin/env python3
"""Review the saved diagnostic without launching or discovering native targets."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/android-emulator-boot-diagnosis'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def main():
    bindings = {}

    def bind(path, expected=None):
        path = Path(path)
        if not path.is_absolute():
            path = ROOT / path
        actual = sha(path)
        if expected is not None and actual != expected:
            raise ValueError('changed evidence: ' + str(path))
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        bindings[key] = actual
        return actual

    dispatch = read(HERE / 'boot-probe-dispatch.json')
    for path, expected in dispatch['bindings'].items():
        bind(path, expected)
    bind(HERE / 'boot-probe-dispatch.json')
    contract = read(PACKET / 'probe-contract.json')
    for entry in contract['bindings']:
        bind(entry['path'], entry['sha256'])

    analysis = read(PACKET / 'analysis-1/receipt.json')
    assert len(analysis['assertions']) == 69
    assert all(entry['passed'] for entry in analysis['assertions'])
    for entry in analysis['inputFiles']:
        bind(entry['path'], entry['sha256'])
    inputs = sorted(analysis['inputFiles'], key=lambda entry: entry['path'])
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert digest == analysis['analysisInputTreeSHA256']

    host = read(PACKET / 'host-review-1/receipt.json')
    assert host['tests'] == 15 and host['nativeLaunches'] == 0
    for path, expected in host['bindings'].items():
        bind(PACKET / path, expected)
    for folder, receipt in [('analysis-1', analysis), ('host-review-1', host)]:
        bind(PACKET / folder / 'receipt.json')
        for command in receipt['commands']:
            bind(PACKET / folder / command['output'], command['outputSHA256'])

    run = read(PACKET / 'boot-probe-1/receipt.json')
    assert run['status'] == 'boot-only-diagnostic-passed'
    assert run['cleanup'] == 'stopped' and run['ownedEmulatorGroupCleanup']['after'] == []
    assert run['sourceRevision'] == 'a1f78d1e88d6e1e934a08cdb85ce90f87f6ff343'
    assert run['runnerSHA256'] == sha(PACKET / 'boot_probe.py')
    assert run['contractSHA256'] == sha(PACKET / 'probe-contract.json')
    assert run['boundInputTreeSHA256'] == contract['bindingTreeSHA256']
    assert run['ownedInstance']['argv'] == contract['argv'] == contract['baseArgv'] + ['-feature', '-WiFiPacketStream']
    assert run['target'] == {
        'ro.kernel.qemu': '1', 'ro.product.model': 'sdk_gphone64_arm64',
        'ro.build.version.sdk': '37', 'ro.product.cpu.abi': 'arm64-v8a',
        'ro.build.fingerprint': 'google/sdk_gphone64_arm64/emu64a:17/CE2A.260420.019/15611780:userdebug/dev-keys',
        'ro.boot.qemu.avd_name': 'megpt-parity-api37', 'sys.boot_completed': '1',
    }
    for key in ('apkInstalled', 'appAssertionsRun', 'physicalTargetsQueried', 'sharedNetsimOrGlobalSettingsMutated'):
        assert run[key] is False
    by_name = {entry['name']: entry for entry in run['commands']}
    assert len(by_name) == len(run['commands'])
    for command in run['commands']:
        bind(PACKET / 'boot-probe-1' / command['output'], command['outputSHA256'])
        assert command['ownedCommandGroupCleanup']['after'] == []
        if Path(command['argv'][0]).name == 'adb' and command['argv'][1:] != ['version']:
            assert command['argv'][1:3] == ['-s', 'emulator-5586']
            assert command['argv'][3:5] in (['shell', 'getprop'], ['emu', 'kill'])
    for port in (5586, 5587):
        command = by_name['port-after-' + str(port)]
        assert command['exitCode'] == 1
        assert (PACKET / 'boot-probe-1' / command['output']).read_bytes() == b''
    for path in sorted((PACKET / 'boot-probe-1').iterdir()):
        if path.is_file():
            bind(path)
    bind(__file__)
    result = {
        'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'accepted-boot-only-diagnostic',
        'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'command': ['python3', '-B', str(Path(__file__).relative_to(ROOT))],
        'pythonVersion': platform.python_version(), 'bindings': bindings,
        'producerEvidenceAssertions': 69, 'producerHostGuards': 15, 'rootHostGuards': 15,
        'reviewHarnessCorrection': 'First replay incorrectly required target selection on the host-only adb version command and stopped without acceptance. Corrected to exempt exactly adb version; all runtime adb calls still require the owned serial.',
        'nativeProfile': run['target'], 'onlyLaunchDelta': ['-feature', '-WiFiPacketStream'],
        'cleanup': 'owned process group absent and both reserved ports empty',
        'scope': 'The saved root-dispatched API37 arm64 boot succeeds with the process-local Wi-Fi fallback. No APK was installed or app assertion executed. This does not establish the shared daemon cause, app acceptance, physical evidence, or a GA gate.',
        'next': 'Root review and dispatch of a separately bound full APK runner adaptation.',
    }
    (HERE / 'boot-probe-acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'bindings': len(bindings)}))


if __name__ == '__main__':
    main()
