#!/usr/bin/env python3
"""Build a frozen VM and run captured numeric references through its iOS C ABI.

The reference directory must be an earlier verify-numeric-android.py output;
its captured Node inputs/outputs and frozen revision are checked before use.
Signing uses the explicitly supplied existing team; no portal update is enabled.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', required=True, type=Path)
    p.add_argument('--device', required=True)
    p.add_argument('--team', required=True)
    p.add_argument('--rust-bin', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    reference = a.reference.resolve()
    prior = json.loads((reference / 'receipt.json').read_text())
    assert prior['results']['mobile_float_oracle']['matched_cases'] == 29794
    identity = {Path(entry['local']).name: entry['sha256'] for entry in prior['installed_artifacts']}
    for count in [27944, 1290, 560]:
        for suffix in ['input', 'expected']:
            file = reference / 'oracle' / f'{count}.{suffix}'
            assert sha(file) == identity[file.name], file
    revision = prior['source_revision']
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env['PATH'] = str(a.rust_bin) + os.pathsep + env['PATH']
    env['CARGO_TARGET_DIR'] = str(out / 'target')
    env['IPHONEOS_DEPLOYMENT_TARGET'] = '17.0'
    commands = []

    def run(name, command):
        command = list(map(str, command))
        result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = out / (name + '.log')
        log.write_text(result.stdout)
        commands.append({'name': name, 'command': command, 'exit_code': result.returncode,
                         'log': str(log), 'sha256': sha(log)})
        if result.returncode:
            raise RuntimeError(f'{name} failed: {result.stdout[-8000:]}')
        return result.stdout

    source = out / 'source'
    source.mkdir()
    archive = subprocess.check_output(['git', 'archive', revision, 'vm', 'contracts/vm-profile-v1.json'], cwd=ROOT)
    assert hashlib.sha256(archive).hexdigest() == prior['source_archive_sha256']
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(source, filter='data')
    run('rust-build', ['cargo', 'build', '--manifest-path', source / 'vm/Cargo.toml',
                      '--release', '--target', 'aarch64-apple-ios', '--lib'])
    app = out / 'app'
    template = ROOT / 'verification/tools/ios-numeric'
    shutil.copytree(template, app)
    shutil.copytree(reference / 'oracle', app / 'oracle')
    (app / 'lib').mkdir()
    library = app / 'lib/libmixer_vm.a'
    shutil.copy(out / 'target/aarch64-apple-ios/release/libmixer_vm.a', library)
    shutil.copy(source / 'vm/include/mixer_vm.h', app / 'lib/mixer_vm.h')
    run('build', ['xcodebuild', '-project', app / 'NumericVM.xcodeproj', '-scheme', 'NumericVM',
                 '-configuration', 'Debug', '-destination', 'platform=iOS,id=' + a.device,
                 '-derivedDataPath', out / 'build', 'CODE_SIGN_STYLE=Automatic',
                 'DEVELOPMENT_TEAM=' + a.team, 'CODE_SIGN_IDENTITY=Apple Development', 'build'])
    bundle = out / 'build/Build/Products/Debug-iphoneos/NumericVM.app'
    run('device-info', ['xcrun', 'devicectl', 'device', 'info', 'details', '--device', a.device,
                       '--json-output', out / 'device.json'])
    run('install', ['xcrun', 'devicectl', 'device', 'install', 'app', '--device', a.device,
                    '--json-output', out / 'install.json', bundle])
    launch = run('launch', ['xcrun', 'devicectl', 'device', 'process', 'launch', '--device', a.device,
                 '--console', '--terminate-existing', '--json-output', out / 'launch.json',
                 'dev.mixer.numericqualification'])
    result = json.loads((out / 'launch.json').read_text())
    assert result['result']['terminationResult']['exitCode'] == 0
    assert 'MIXER_NUMERIC_IOS_PASSED 29794' in launch and 'MIXER_NUMERIC_IOS_FAILED' not in launch
    for count in [27944, 1290, 560]:
        assert f'MIXER_NUMERIC_GROUP_PASSED {count}' in launch
    receipt = {'schema': 1, 'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'source_revision': revision, 'reviewer': 'root integrator', 'reference_receipt': str(reference / 'receipt.json'),
               'reference_receipt_sha256': sha(reference / 'receipt.json'), 'matched_cases': 29794,
               'interface': 'public mixer_vm_invoke_numeric_v2 C ABI through independent Swift harness',
               'library_sha256': sha(library), 'app_executable_sha256': sha(bundle / 'NumericVM'),
               'harness_files': {str(f.relative_to(template)): sha(f) for f in sorted(template.rglob('*')) if f.is_file()},
               'runner_sha256': sha(Path(__file__)), 'device': a.device, 'commands': commands,
               'device_info': str(out / 'device.json'), 'device_info_sha256': sha(out / 'device.json'),
               'launch_result': result,
               'limitations': ['Dedicated development harness, not FieldLog or published SDK adoption',
                               'No full Swift guest, OTA activation or UI behavior claim',
                               'No full device matrix, standards conformance, performance or security audit claim',
                               'No D0-D8 or GA gate passed']}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'receipt': str(out / 'receipt.json'), 'matched_cases': 29794}, indent=2))


if __name__ == '__main__':
    main()
