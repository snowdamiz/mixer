#!/usr/bin/env python3
"""Compile an immutable FieldLog revision with official full Swift SDKs.

This is compiler/model evidence using trusted installed developer tools. Node is
an oracle, never a product runtime. Owned execution/OTA gates remain open.
"""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import tarfile
import uuid

from qualification_support import (CommandRecorder, clean_environment, digest,
                                   model_observations, strict_json, tool_identity, vm_receipt)

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fieldlog', required=True, type=Path)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cross-swift', required=True, type=Path)
    parser.add_argument('--developer-dir', required=True, type=Path)
    parser.add_argument('--swift-sdks', type=Path, default=Path.home()/'.swiftpm/swift-sdks')
    parser.add_argument('--wasm-sdk', default='swift-6.3.3-RELEASE_wasm')
    parser.add_argument('--adb', type=Path)
    parser.add_argument('--device')
    parser.add_argument('--libcxx', type=Path)
    args = parser.parse_args()
    if bool(args.device) != bool(args.adb) or bool(args.device) != bool(args.libcxx):
        parser.error('--device, --adb and --libcxx must be provided together')
    if args.device and not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', args.device, flags=re.ASCII):
        parser.error('Unsupported adb device serial')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', args.wasm_sdk, flags=re.ASCII):
        parser.error('Unsupported Swift SDK identifier')
    # Resolve caller-relative paths before running any command in ROOT.
    for name in ['fieldlog', 'output', 'cross_swift', 'developer_dir', 'swift_sdks', 'adb', 'libcxx']:
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).absolute())
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    commands = []
    recorder = CommandRecorder(output, commands, ROOT)
    base_env = clean_environment()
    tools = {}
    receipt = {'schema': 2, 'status': 'running',
               'scope': 'actual FieldLog model compiler/oracle checks with trusted installed tools',
               'ownedSwiftExecutionQualified': False, 'deviceOTAQualified': False,
               'commands': commands, 'tools': tools,
               'trustBoundary': 'Installed compiler, SDK, Node, adb and owned VM executables are trusted local tools; hashes identify observed bytes, not sandboxing or source-build attestation.'}
    remote = None
    adb = None

    def find_tool(name):
        path = shutil.which(name, path=base_env.get('PATH', os.defpath))
        if not path:
            raise ValueError(f'Required installed tool missing: {name}')
        return str(Path(path).absolute())

    def run(name, command, **kwargs):
        return recorder.run(name, command, env=kwargs.pop('env', base_env), **kwargs)

    def artifact(path):
        return {'path': str(path.relative_to(output)), 'bytes': path.stat().st_size, 'sha256': digest(path)}

    try:
        git, node = find_tool('git'), find_tool('node')
        native_developer = run('native-developer-dir', ['/usr/bin/xcode-select', '-p']).strip()
        native_env = dict(base_env, DEVELOPER_DIR=native_developer)
        native_swift = run('native-compiler-path', ['/usr/bin/xcrun', '--find', 'swift'], env=native_env).strip()
        cross_env = dict(base_env, DEVELOPER_DIR=str(args.developer_dir))
        tools.update({'git': tool_identity(git), 'nativeSwift': tool_identity(native_swift),
                      'crossSwift': tool_identity(args.cross_swift), 'node': tool_identity(node)})
        receipt['compilerConfiguration'] = {'nativeDeveloperDirectory': native_developer,
            'crossDeveloperDirectory': str(args.developer_dir), 'swiftSDKsPath': str(args.swift_sdks),
            'wasmSDK': args.wasm_sdk, 'androidSDK': 'aarch64-unknown-linux-android28',
            'sdkMetadata': [{'path': str(path), 'sha256': digest(path)}
                            for path in sorted(args.swift_sdks.glob('*.artifactbundle/info.json'))],
            'sdkContentsAttested': False, 'ambientToolOverrides': 'removed; clean per-command environment'}
        receipt['harnessSources'] = {str(path.relative_to(ROOT)): digest(path) for path in
            [Path(__file__), ROOT/'compiler/qualification_support.py', ROOT/'compiler/Fixtures/FieldLogCorpus/main.swift']}
        revision = run('source-revision', [git, '-C', args.fieldlog, 'rev-parse', '--verify', '--end-of-options', args.revision+'^{commit}']).strip()
        if not re.fullmatch(r'[0-9a-f]{40}', revision, flags=re.ASCII):
            raise ValueError('Expected a full Git commit identity')
        receipt['fieldlogRevision'] = revision
        archive = output/'fieldlog-source.tar'
        run('source-export', [git, '-C', args.fieldlog, 'archive', '--format=tar', '--output='+str(archive), revision])
        source = output/'fieldlog'; source.mkdir()
        with tarfile.open(archive) as tar:
            tar.extractall(source, filter='data')
        receipt['sourceArchiveSHA256'] = digest(archive)
        harness = output/'Sources/FieldLogCorpus'; harness.mkdir(parents=True)
        shutil.copyfile(ROOT/'compiler/Fixtures/FieldLogCorpus/main.swift', harness/'main.swift')
        receipt['harnessSHA256'] = digest(harness/'main.swift')
        (output/'Package.swift').write_text('''// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "FieldLogCorpus", platforms: [.macOS(.v14)],
    products: [.executable(name: "fieldlog-corpus", targets: ["FieldLogCorpus"])],
    dependencies: [.package(path: "fieldlog")],
    targets: [.executableTarget(name: "FieldLogCorpus", dependencies: [.product(name: "FieldLogModels", package: "fieldlog")])])
''')
        receipt['generatedPackageSHA256'] = digest(output/'Package.swift')
        receipt['toolVersions'] = {
            'nativeSwift': run('native-version', [native_swift, '--version'], env=native_env).strip(),
            'crossSwift': run('cross-version', [args.cross_swift, '--version'], env=cross_env).strip(),
            'node': run('node-version', [node, '--version']).strip()}
        run('native-build', [native_swift, 'build', '--package-path', output, '-c', 'release', '-j', '4'], env=native_env)
        native_binary = output/'.build/release/fieldlog-corpus'
        native = model_observations(strict_json(run('native-run', [native_binary])))
        run('wasm-build', [args.cross_swift, 'build', '--package-path', output, '--scratch-path', output/'.build/wasm',
                          '--swift-sdks-path', args.swift_sdks, '--swift-sdk', args.wasm_sdk, '-c', 'release', '-j', '4'], env=cross_env)
        wasm = output/'.build/wasm/wasm32-unknown-wasip1/release/fieldlog-corpus.wasm'
        wasm_identity = artifact(wasm)
        oracle = '''import {WASI} from 'node:wasi'; import {readFile} from 'node:fs/promises';
const wasi=new WASI({version:'preview1',args:['fieldlog-corpus'],env:{},preopens:{},returnOnExit:true});
const module=await WebAssembly.compile(await readFile(process.argv[1]));
const instance=await WebAssembly.instantiate(module,wasi.getImportObject());
process.exitCode=wasi.start(instance);'''
        wasm_result = model_observations(strict_json(run('wasm-oracle', [node, '--input-type=module', '-e', oracle, wasm])))
        if native != wasm_result:
            raise ValueError('Native/Wasm model observations differ')
        run('android-build', [args.cross_swift, 'build', '--package-path', output, '--scratch-path', output/'.build/android',
                             '--swift-sdks-path', args.swift_sdks, '--swift-sdk', 'aarch64-unknown-linux-android28',
                             '--static-swift-stdlib', '-c', 'release', '-j', '4'], env=cross_env)
        android = output/'.build/android/aarch64-unknown-linux-android28/release/fieldlog-corpus'
        receipt['artifacts'] = {'native': artifact(native_binary), 'wasm': wasm_identity, 'android': artifact(android)}
        receipt['modelObservations'] = native
        receipt['nativeVersusWasmOracle'] = 'passed'
        receipt['androidExecution'] = 'not-run'
        if args.device:
            if args.libcxx.name != 'libc++_shared.so' or not args.libcxx.is_file():
                raise ValueError('--libcxx must identify the matching regular libc++_shared.so')
            tools['adb'] = tool_identity(args.adb)
            receipt['androidRuntimeLibrary'] = {'path': str(args.libcxx), 'bytes': args.libcxx.stat().st_size, 'sha256': digest(args.libcxx)}
            adb = [args.adb, '-s', args.device]
            if run('device-state', adb+['get-state']).strip() != 'device':
                raise ValueError('Selected adb device is not ready')
            # UUID prevents a stale executable or library from satisfying a rerun.
            remote = '/data/local/tmp/mixer-fieldlog-corpus-'+uuid.uuid4().hex
            receipt['androidRunDirectory'] = remote
            run('device-mkdir', adb+['shell', 'mkdir', remote])
            run('device-push', adb+['push', android, args.libcxx, remote+'/'])
            hashes = run('device-hashes', adb+['shell', 'sha256sum', remote+'/fieldlog-corpus', remote+'/libc++_shared.so'])
            expected = {remote+'/fieldlog-corpus': receipt['artifacts']['android']['sha256'],
                        remote+'/libc++_shared.so': receipt['androidRuntimeLibrary']['sha256']}
            observed = {}
            for line in hashes.splitlines():
                parts = line.split()
                if len(parts) != 2 or parts[1] in observed:
                    raise ValueError('Invalid or duplicate remote artifact hash')
                observed[parts[1]] = parts[0]
            if observed != expected:
                raise ValueError('Uploaded Android executable/runtime hashes differ')
            receipt['androidUploadedSHA256'] = observed
            run('device-chmod', adb+['shell', 'chmod', '700', remote+'/fieldlog-corpus'])
            actual = model_observations(strict_json(run('android-run', adb+['shell', 'env', 'LD_LIBRARY_PATH='+remote, remote+'/fieldlog-corpus'])))
            if actual != native:
                raise ValueError('ADB Android/native model observations differ')
            receipt['androidExecution'] = 'passed'
            receipt['androidDevice'] = {'serial': args.device, 'hardwareAttested': False,
                'properties': {key: run('device-'+key, adb+['shell', 'getprop', key]).strip()
                               for key in ['ro.product.model', 'ro.build.version.release', 'ro.build.fingerprint', 'ro.kernel.qemu']}}
        # Freeze a standalone VM binary so a concurrent local rebuild cannot alter
        # the validator between inventory and validation. It remains a trusted tool.
        vm_source = ROOT/'vm/target/release/mixer-vm'
        original_vm = tool_identity(vm_source)
        (output/'tools').mkdir()
        vm = output/'tools/mixer-vm'
        shutil.copyfile(vm_source, vm); vm.chmod(0o500)
        if tool_identity(vm_source) != original_vm or digest(vm) != original_vm['sha256']:
            raise ValueError('Owned VM changed while copying the local tool')
        tools['ownedVM'] = {'source': original_vm, 'snapshot': tool_identity(vm), 'sourceBuildCorrespondenceAttested': False}
        inventory = vm_receipt(strict_json(run('owned-vm-inventory', [vm, 'inventory', wasm], expected=(0, 2))), commands[-1]['exitCode'])
        validation = vm_receipt(strict_json(run('owned-vm-validation', [vm, 'validate', wasm], expected=(0, 2))), commands[-1]['exitCode'])
        receipt['ownedVMValidation'] = validation
        receipt['ownedVMProfileStatus'] = 'accepted' if validation['valid'] else 'rejected'
        receipt['opcodeInventoryFile'] = 'owned-vm-inventory.stdout'
        receipt['opcodeInventoryComplete'] = inventory['inventory_complete']
        for key, path in [('native', native_binary), ('wasm', wasm), ('android', android)]:
            if artifact(path) != receipt['artifacts'][key]:
                raise ValueError(f'{key} artifact changed during qualification')
        for key in ['git', 'nativeSwift', 'crossSwift', 'node'] + (['adb'] if args.device else []):
            if tool_identity(tools[key]['path']) != tools[key]:
                raise ValueError(f'{key} installed executable changed during qualification')
        receipt['status'] = 'compiler-model-checks-passed' if args.device else 'compiler-model-checks-passed-android-execution-not-run'
        receipt['limitations'] = ['No owned full Swift execution receipt; VM profile acceptance alone is not execution',
            'No UI, effect, storage or OTA qualification', 'SDK and installed-tool dependencies are not fully attested',
            'ADB properties are observations, not independent physical-device attestation',
            'Source snapshot is for diagnostics, not immutable published SDK adoption',
            'Timing is command wall time, not an app performance measurement']
    except Exception as error:
        receipt['status'] = 'failed'; receipt['failure'] = str(error)
        raise
    finally:
        if remote and adb:
            try:
                run('device-cleanup', adb+['shell', 'rm', '-rf', remote], timeout=15)
                receipt['androidRunDirectoryRemoved'] = True
            except Exception as error:
                receipt['androidRunDirectoryRemoved'] = False
                receipt['cleanupFailure'] = str(error)
                receipt['status'] = 'failed'
        (output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    if receipt['status'] == 'failed':
        raise RuntimeError(receipt.get('cleanupFailure', 'Qualification failed'))
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
