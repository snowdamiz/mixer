#!/usr/bin/env python3
"""Qualify frozen owned VM session sources on the host or a physical Android device."""
import argparse
import datetime
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--platform', choices=['host', 'android'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--adb', default='/opt/homebrew/share/android-commandlinetools/platform-tools/adb')
    parser.add_argument('--serial')
    parser.add_argument('--ndk', type=Path)
    args = parser.parse_args()
    if args.platform == 'android' and (not args.serial or not args.ndk):
        parser.error('Android requires --serial and --ndk')
    revision = subprocess.check_output(['git', 'rev-parse', args.revision + '^{commit}'], cwd=ROOT, text=True).strip()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = out / 'source'
    source.mkdir()
    archive = subprocess.check_output(['git', 'archive', revision, 'vm', 'contracts/vm-profile-v1.json',
                                       'contracts/vm-session-v1.json'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(source, filter='data')
    paths = sorted(p for p in source.rglob('*') if p.is_file() and '/verification/' not in p.relative_to(source).as_posix())
    manifest = ''.join(f'{sha(p)}  {p.relative_to(source)}\n' for p in paths)
    (out / 'source-manifest.sha256').write_text(manifest)
    env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'], CARGO_TARGET_DIR=str(out / 'target'))
    commands = []

    def run(name, command):
        command = list(map(str, command))
        result = subprocess.run(command, cwd=source, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=600)
        log = out / (name + '.log')
        log.write_text(result.stdout)
        commands.append({'name': name, 'command': command, 'exit_code': result.returncode,
                         'log': str(log), 'log_sha256': sha(log)})
        if result.returncode:
            raise RuntimeError(f'{name} failed; see {log}')
        return result.stdout

    versions = {name: run('version-' + name, command).strip() for name, command in {
        'rustc': ['rustc', '--version'], 'cargo': ['cargo', '--version'],
        'host': ['sw_vers'], 'node': ['node', '--version'],
    }.items()}
    base = ['cargo', 'test', '--manifest-path', source / 'vm/Cargo.toml']
    results = {}
    installed = []
    device = None
    if args.platform == 'host':
        run('format', ['cargo', 'fmt', '--manifest-path', source / 'vm/Cargo.toml', '--check'])
        run('clippy', ['cargo', 'clippy', '--manifest-path', source / 'vm/Cargo.toml', '--all-targets', '--', '-D', 'warnings'])
        text = run('host-tests', base)
        counts = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored', text)
        assert sum(int(c[0]) for c in counts) == 86 and all(c[1] == '0' for c in counts), counts
        results['host_unit'] = {'passed': 86, 'explicit_oracle_functions_initially_ignored': 8}
        text = run('session-release', base + ['--release', '--test', 'sessions', '--lib'])
        assert text.count('test result: ok. 7 passed; 0 failed; 0 ignored') == 2
        results['session_and_ffi_release'] = {'passed': 14, 'failed': 0, 'ignored': 0}
        text = run('explicit-oracles', base + ['--release', '--test', 'differential', '--test', 'float_differential',
                    '--test', 'table_memory_differential', '--', '--ignored', '--nocapture'])
        counts = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored', text)
        assert sum(int(c[0]) for c in counts) == 8 and all(c[1:] == ('0','0') for c in counts), counts
        results['explicit_development_oracles'] = {'passed_functions': 8, 'failed': 0, 'ignored': 0}
        run('library', ['cargo','build','--release','--manifest-path',source/'vm/Cargo.toml','--lib'])
        for name in ['ffi_smoke','ffi_numeric_smoke','ffi_table_memory_smoke','ffi_session_smoke']:
            binary = out / name
            run('build-'+name,['clang','-std=c11','-Wall','-Wextra','-Werror','-I',source/'vm/include',
                    source/f'vm/tests/{name}.c',out/'target/release/libmixer_vm.a','-o',binary])
            results[name] = run('run-'+name,[binary]).strip()
    else:
        clang = args.ndk.resolve() / 'toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android28-clang'
        env['CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER'] = str(clang)
        versions['clang'] = run('version-clang',[clang,'--version']).strip()
        text = run('build-android', base + ['--release','--target','aarch64-linux-android','--test','sessions',
                                          '--lib','--no-run','--message-format=json'])
        binaries = {}
        for line in text.splitlines():
            if line.startswith('{'):
                item = json.loads(line)
                if item.get('reason') == 'compiler-artifact' and item.get('executable') and item['profile']['test']:
                    binaries[item['target']['name']] = Path(item['executable'])
        assert set(binaries) == {'sessions','mixer_vm'}, binaries
        run('library',['cargo','build','--release','--manifest-path',source/'vm/Cargo.toml','--target','aarch64-linux-android','--lib'])
        binary = out/'ffi-session-smoke'
        run('build-c',[''+str(clang),'-std=c11','-Wall','-Wextra','-Werror','-I',source/'vm/include',
            source/'vm/tests/ffi_session_smoke.c',out/'target/aarch64-linux-android/release/libmixer_vm.a','-lm','-ldl','-o',binary])
        adb = [args.adb,'-s',args.serial]
        props = {key: run('property-'+key,adb+['shell','getprop',key]).strip() for key in [
            'ro.product.model','ro.product.cpu.abi','ro.build.version.release','ro.build.version.sdk','ro.kernel.qemu','ro.boot.qemu']}
        assert not args.serial.startswith('emulator-') and not any(props[k]=='1' for k in ['ro.kernel.qemu','ro.boot.qemu'])
        assert props['ro.product.cpu.abi']=='arm64-v8a'
        device = {'serial':args.serial,'physical':True,'properties':props}
        remote = '/data/local/tmp/mixer-sessions-'+uuid.uuid4().hex
        run('create-remote',adb+['shell','mkdir','-m','700',remote])
        try:
            for name, path in {**binaries, 'c_abi':binary}.items():
                destination = remote+'/'+path.name
                run('push-'+name,adb+['push',path,destination])
                digest = run('hash-'+name,adb+['shell','sha256sum',destination]).split()[0]
                assert digest == sha(path)
                installed.append({'local':str(path),'remote':destination,'sha256':digest})
                run('chmod-'+name,adb+['shell','chmod','700',destination])
                text = run('device-'+name,adb+['shell',destination]+([] if name=='c_abi' else ['--nocapture','--test-threads=1']))
                if name=='c_abi':
                    assert 'Persistent session C ABI smoke: passed' in text
                    results[name] = text.strip()
                else:
                    assert 'test result: ok. 7 passed; 0 failed; 0 ignored' in text
                    results[name] = {'passed':7,'failed':0,'ignored':0}
        finally:
            run('remove-remote',adb+['shell','rm','-rf',remote])
    assert manifest == ''.join(f'{sha(p)}  {p.relative_to(source)}\n' for p in paths), 'Frozen source drift'
    receipt = {'schema':1,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_revision':revision,'source_archive_sha256':hashlib.sha256(archive).hexdigest(),
        'source_digest':hashlib.sha256(manifest.encode()).hexdigest(),'runner_sha256':sha(Path(__file__)),
        'platform':args.platform,'device':device,'results':results,'installed_artifacts':installed,
        'tool_versions':versions,'environment_overrides':{k:env[k] for k in ['PATH','CARGO_TARGET_DIR'] +
            (['CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER'] if args.platform=='android' else [])},
        'commands':commands,'limits':['Unchanged frozen source and assertions; no guest Wasm runtime replacement',
            'Development reference runs on the host only','No full Swift guest execution, FieldLog integration, OTA activation, standards/fuzz/audit or GA approval']}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'receipt':str(out/'receipt.json'),'results':results},indent=2))


if __name__ == '__main__':
    main()
