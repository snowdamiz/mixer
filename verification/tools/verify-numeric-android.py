#!/usr/bin/env python3
"""Qualify a frozen owned VM revision on an explicitly selected Android device.

Node executes reference Wasm on the development Mac only. The generated mobile
test uses the same owned cases, verifies their exact serialized inputs against
the captured reference, and compares the physical VM's results to those outputs.
The VM library is never patched. The test-only transport change is recorded.
"""
import argparse
import datetime
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--revision', required=True)
    p.add_argument('--serial', required=True)
    p.add_argument('--adb', required=True, type=Path)
    p.add_argument('--ndk', required=True, type=Path)
    p.add_argument('--rust-bin', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env['PATH'] = str(args.rust_bin) + os.pathsep + env['PATH']
    env['CARGO_TARGET_DIR'] = str(out / 'target')
    clang = args.ndk / 'toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android28-clang'
    env['CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER'] = str(clang)
    commands = []

    def run(name, command, extra_env=None):
        command = list(map(str, command))
        result = subprocess.run(command, cwd=ROOT, env=env | (extra_env or {}),
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = out / (name + '.log')
        log.write_text(result.stdout)
        commands.append({'name': name, 'command': command, 'exit_code': result.returncode,
                         'log': str(log), 'sha256': sha(log)})
        if result.returncode:
            raise RuntimeError(f'{name} failed: {result.stdout[-8000:]}')
        return result.stdout

    revision = run('revision', ['git', 'rev-parse', args.revision + '^{commit}']).strip()
    source = out / 'source'
    source.mkdir()
    archive = subprocess.check_output(['git', 'archive', revision, 'vm', 'contracts/vm-profile-v1.json'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(source, filter='data')
    original_files = {str(f.relative_to(source)): sha(f) for f in sorted(source.rglob('*'))
                      if f.is_file() and 'verification' not in f.relative_to(source).parts}
    baseline = source / 'vm/tests/float_differential.rs'
    original = baseline.read_text()
    start = original.index('    let mut child = Command::new(')
    end = original.index('    let lines = text.lines()', start)
    reference = out / 'oracle'
    reference.mkdir()
    replacement = '''    let directory = std::env::var("MIXER_ORACLE_DIRECTORY").unwrap();
    let stem = format!("{directory}/{}", cases.len());
    #[cfg(not(target_os = "android"))]
    let text = {
        std::fs::write(format!("{stem}.input"), &input).unwrap();
        let mut child = Command::new("node").args(["-e", script])
            .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap();
        child.stdin.take().unwrap().write_all(input.as_bytes()).unwrap();
        let output = child.wait_with_output().unwrap();
        assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
        let text = String::from_utf8(output.stdout).unwrap();
        std::fs::write(format!("{stem}.expected"), &text).unwrap();
        text
    };
    #[cfg(target_os = "android")]
    let text = {
        assert_eq!(std::fs::read_to_string(format!("{stem}.input")).unwrap(), input,
                   "reference inputs must be identical to device inputs");
        std::fs::read_to_string(format!("{stem}.expected")).unwrap()
    };
'''
    generated = source / 'vm/tests/mobile_float_oracle.rs'
    generated.write_text(original[:start] + replacement + original[end:])
    (out / 'oracle-transport.patch').write_text(''.join(difflib.unified_diff(
        original.splitlines(keepends=True), generated.read_text().splitlines(keepends=True),
        fromfile='float_differential.rs', tofile='mobile_float_oracle.rs')))
    base = ['cargo', 'test', '--manifest-path', source / 'vm/Cargo.toml']
    host = run('host-reference', base + ['--release', '--test', 'mobile_float_oracle', '--',
               '--ignored', '--nocapture', '--test-threads=1'], {'MIXER_ORACLE_DIRECTORY': str(reference)})
    expected_cases = sum(map(int, re.findall(r'numeric-v2 differential cases matched: (\d+)', host)))
    assert expected_cases == 29794, expected_cases
    build = run('android-build', base + ['--release', '--target', 'aarch64-linux-android',
                '--test', 'mobile_float_oracle', '--test', 'float', '--test', 'interpreter',
                '--test', 'review_boundaries', '--no-run', '--message-format=json'])
    binaries = {}
    for line in build.splitlines():
        if not line.startswith('{'):
            continue
        item = json.loads(line)
        if item.get('reason') == 'compiler-artifact' and item.get('executable') and item['profile']['test']:
            binaries[item['target']['name']] = Path(item['executable'])
    assert set(binaries) == {'mobile_float_oracle', 'float', 'interpreter', 'review_boundaries'}, binaries
    run('android-library', ['cargo', 'build', '--manifest-path', source / 'vm/Cargo.toml',
                           '--release', '--target', 'aarch64-linux-android', '--lib'])
    c_binaries = {}
    for name, c_source in {
        'numeric-c-abi': source / 'vm/tests/ffi_numeric_smoke.c',
        'numeric-fp-control': ROOT / 'verification/tools/numeric-fp-android.c',
    }.items():
        binary = out / name
        run('build-' + name, [clang, '-std=c11', '-Wall', '-Wextra', '-Werror',
            '-I', source / 'vm/include', c_source,
            out / 'target/aarch64-linux-android/release/libmixer_vm.a', '-lm', '-ldl', '-o', binary])
        c_binaries[name] = binary
    adb = [args.adb, '-s', args.serial]
    props = {}
    for key in ['ro.product.model', 'ro.build.version.release', 'ro.build.version.sdk', 'ro.product.cpu.abi',
                'ro.kernel.qemu', 'ro.boot.qemu']:
        props[key] = run('property-' + key, adb + ['shell', 'getprop', key]).strip()
    physical = not args.serial.startswith('emulator-') and not any(props[k] == '1' for k in ['ro.kernel.qemu', 'ro.boot.qemu'])
    assert physical, 'Physical qualification requires a non-emulator device'
    assert props['ro.product.cpu.abi'] == 'arm64-v8a'
    remote = '/data/local/tmp/mixer-numeric-' + uuid.uuid4().hex
    run('create-remote', adb + ['shell', 'mkdir', '-m', '700', remote])
    installed = []
    results = {}
    try:
        for file in list(reference.iterdir()) + list(binaries.values()) + list(c_binaries.values()):
            remote_file = remote + '/' + file.name
            run('push-' + file.name, adb + ['push', file, remote_file])
            actual = run('hash-' + file.name, adb + ['shell', 'sha256sum', remote_file]).split()[0]
            assert actual == sha(file), file
            installed.append({'local': str(file), 'remote': remote_file, 'sha256': actual})
        for name, binary in binaries.items():
            path = remote + '/' + binary.name
            run('chmod-' + name, adb + ['shell', 'chmod', '700', path])
            command = adb + ['shell', 'env', 'MIXER_ORACLE_DIRECTORY=' + remote, path]
            if name == 'mobile_float_oracle':
                command += ['--ignored']
            result = run('device-' + name, command + ['--nocapture', '--test-threads=1'])
            counts = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored', result)
            assert len(counts) == 1 and counts[0][1:] == ('0', '0'), result
            results[name] = {'passed': int(counts[0][0]), 'failed': 0, 'ignored': 0}
            if name == 'mobile_float_oracle':
                actual_cases = sum(map(int, re.findall(r'numeric-v2 differential cases matched: (\d+)', result)))
                assert actual_cases == expected_cases
                results[name]['matched_cases'] = actual_cases
        for name, binary in c_binaries.items():
            path = remote + '/' + binary.name
            run('chmod-' + name, adb + ['shell', 'chmod', '700', path])
            result = run('device-' + name, adb + ['shell', path])
            assert ': passed' in result, result
            results[name] = {'exit_code': 0, 'output': result.strip()}
    finally:
        # This exact randomly generated directory was created by this invocation.
        run('remove-remote', adb + ['shell', 'rm', '-rf', remote])
    assert all(sha(source / path) == digest for path, digest in original_files.items()), 'Source drift'
    manifest = ''.join(f'{digest}  {path}\n' for path, digest in original_files.items())
    (out / 'source-manifest.sha256').write_text(manifest)
    receipt = {'schema': 1, 'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'source_revision': revision, 'source_digest': hashlib.sha256(manifest.encode()).hexdigest(),
               'reviewer': 'root integrator', 'source_archive_sha256': hashlib.sha256(archive).hexdigest(),
               'original_harness_sha256': sha(baseline), 'mobile_harness_sha256': sha(generated),
               'runner_sha256': sha(Path(__file__)),
               'independent_c_harness_sha256': sha(ROOT / 'verification/tools/numeric-fp-android.c'),
               'transport_patch': str(out / 'oracle-transport.patch'), 'device_serial': args.serial,
               'physical_device': physical, 'device_properties': props, 'results': results,
               'installed_artifacts': installed, 'commands': commands,
               'tool_versions': {n: run('version-' + n, cmd).strip() for n, cmd in {
                   'rustc': ['rustc', '--version'], 'cargo': ['cargo', '--version'],
                   'node': ['node', '--version'], 'clang': [clang, '--version']}.items()},
               'limits': ['Release Rust library at frozen revision; test transport only modified',
                          'Node is a development reference only and does not run on the device',
                          'No full Swift/FieldLog guest execution or OTA activation',
                          'No iOS execution, full device matrix, security audit or GA gate acceptance']}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'receipt': str(out / 'receipt.json'), 'results': results}, indent=2))


if __name__ == '__main__':
    main()
