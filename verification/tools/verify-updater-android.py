#!/usr/bin/env python3
"""Run an identified Swift Testing updater binary on an explicit physical device.

This is private /data/local/tmp filesystem evidence, not app-sandbox OTA or
physical power-loss qualification. All input/output paths are private to this run.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb', type=Path, required=True)
    p.add_argument('--serial', required=True)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--binary-sha256', required=True)
    p.add_argument('--swift-libs', type=Path, required=True)
    p.add_argument('--libcxx', type=Path, required=True)
    p.add_argument('--source-revision', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert sha(a.binary) == a.binary_sha256
    source_receipt_path = ROOT / 'updates/verification/cold-start-store.json'
    source_receipt = json.loads(source_receipt_path.read_text())
    for entry in source_receipt['source']['files']:
        assert sha(ROOT / entry['path']) == entry['sha256'], 'Updater source drift: ' + entry['path']
    revision = subprocess.check_output(['git', 'rev-parse', a.source_revision + '^{commit}'], cwd=ROOT, text=True).strip()
    for entry in source_receipt['source']['files']:
        committed = subprocess.check_output(['git', 'show', revision + ':' + entry['path']], cwd=ROOT)
        assert hashlib.sha256(committed).hexdigest() == entry['sha256'], 'Revision does not match tested source'
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--', 'updates/Sources', 'updates/Tests', 'updates/Package.swift'], cwd=ROOT)
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    commands = []
    adb = [a.adb, '-s', a.serial]

    def run(name, command):
        command = list(map(str, command))
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
        log = out / (name + '.log')
        log.write_text(result.stdout)
        commands.append({'name': name, 'command': command, 'exit_code': result.returncode,
                         'output': str(log), 'sha256': sha(log)})
        if result.returncode:
            raise RuntimeError(f'{name} failed: {result.stdout[-12000:]}')
        return result.stdout

    props = {key: run('property-' + key, adb + ['shell', 'getprop', key]).strip() for key in
             ['ro.product.model', 'ro.build.version.sdk', 'ro.product.cpu.abi', 'ro.kernel.qemu', 'ro.boot.qemu']}
    assert not a.serial.startswith('emulator-') and not any(props[k] == '1' for k in ['ro.kernel.qemu', 'ro.boot.qemu'])
    remote = '/data/local/tmp/mixer-updater-' + uuid.uuid4().hex
    run('mkdir', adb + ['shell', 'mkdir', '-m', '700', remote, remote + '/lib', remote + '/tmp',
                        remote + '/MixerUpdates_MixerUpdatesTests.resources',
                        remote + '/MixerUpdates_MixerUpdatesTests.resources/Fixtures'])
    resources = a.binary.parent / 'MixerUpdates_MixerUpdatesTests.resources'
    inputs = [(a.binary, remote + '/MixerUpdatesPackageTests.xctest'),
              (a.libcxx, remote + '/lib/' + a.libcxx.name)]
    inputs += [(path, remote + '/lib/' + path.name) for path in sorted(a.swift_libs.glob('*.so'))]
    inputs += [(path, remote + '/MixerUpdates_MixerUpdatesTests.resources/' + str(path.relative_to(resources)))
               for path in sorted(resources.rglob('*')) if path.is_file()]
    assert len(inputs) > 20 and any(path.name == 'signed-release-v1.json' for path, _ in inputs)
    installed = []
    try:
        for index, (path, destination) in enumerate(inputs):
            digest = sha(path)
            run(f'push-{index}', adb + ['push', path, destination])
            observed = run(f'hash-{index}', adb + ['shell', 'sha256sum', destination]).split()[0]
            assert observed == digest and sha(path) == digest, path
            installed.append({'source': str(path), 'destination': destination, 'sha256': digest, 'bytes': path.stat().st_size})
        run('chmod', adb + ['shell', 'chmod', '700', remote + '/MixerUpdatesPackageTests.xctest'])
        result = run('test', adb + ['shell', 'env', 'LD_LIBRARY_PATH=' + remote + '/lib',
                    'TMPDIR=' + remote + '/tmp', remote + '/MixerUpdatesPackageTests.xctest',
                    '--testing-library', 'swift-testing'])
        matches = re.findall(r'Test run with (\d+) tests(?: in \d+ suites)? passed', result)
        assert matches == ['28'], result[-4000:]
        assert 'failed' not in result.lower(), result[-4000:]
        assert 'skipped' not in result.lower(), result[-4000:]
    finally:
        run('cleanup', adb + ['shell', 'rm', '-rf', remote])
    receipt = {'schema': 1, 'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'reviewer': 'root integrator', 'source_revision': revision,
               'source_digest': source_receipt['source']['digest'], 'source_receipt_sha256': sha(source_receipt_path),
               'binary_sha256': a.binary_sha256, 'runner_sha256': sha(Path(__file__)),
               'device_serial': a.serial, 'device_properties': props, 'physical_device': True,
               'test_functions_passed': 28, 'test_executions_including_parameters': 40,
               'installed_inputs': installed, 'commands': commands,
               'scope': 'Swift verifier and durable store tests on physical Android filesystem; injected interruption boundaries',
               'limitations': ['Test payloads use an explicit fixture validator, not actual VM activation',
                   'Shell-owned temporary storage, not Android app sandbox or lifecycle integration',
                   'Fault injection/reopen is not physical power-loss or OS process-kill evidence',
                   'No FieldLog OTA, iOS updater execution, app-data migration or GA acceptance']}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'receipt': str(out / 'receipt.json'), 'test_functions_passed': 28}, indent=2))


if __name__ == '__main__':
    main()
