#!/usr/bin/env python3
"""Explicit generic-simulator compile only; no simctl, launch, service, or test run."""
import argparse
import datetime
import os
from pathlib import Path
import platform
import plistlib
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time

import prepare

DEVELOPER = Path('/Applications/Xcode_26.6.app/Contents/Developer')
SDK = DEVELOPER / 'Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk'
SWIFTC = DEVELOPER / 'Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc'


def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()


def tree(path):
    result = {}
    for item in sorted(path.rglob('*')):
        name = str(item.relative_to(path))
        if item.is_symlink():
            target = os.readlink(item)
            prepare.require(not Path(target).is_absolute() and '..' not in Path(target).parts, 'Unsafe product symlink')
            result[name] = {'kind': 'symlink', 'mode': stat.S_IMODE(item.lstat().st_mode), 'target': target}
        elif item.is_file(): result[name] = prepare.row(item)
        else: prepare.require(item.is_dir(), 'Unexpected output kind')
    return result


def archive_products(path, source, expected):
    prepare.require(not path.exists(), 'Preserve prior compiled archive')
    with tarfile.open(path, 'w:gz') as output:
        for child in sorted(source.iterdir()): output.add(child, arcname=child.name, recursive=True)
    actual = {}
    with tarfile.open(path, 'r:gz') as output:
        seen = set()
        for member in output:
            prepare.require(member.name not in seen and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts,
                            'Unsafe/duplicate compiled archive member')
            seen.add(member.name)
            if member.isdir(): continue
            if member.issym(): actual[member.name] = {'kind': 'symlink', 'mode': member.mode, 'target': member.linkname}
            else:
                prepare.require(member.isfile(), 'Unexpected compiled archive kind')
                data = output.extractfile(member).read()
                actual[member.name] = {'kind': 'file', 'bytes': len(data), 'mode': member.mode, 'sha256': prepare.sha(data)}
    prepare.require(actual == expected, 'Compiled archive round trip mismatch')


def main(attempt, reviewed_source):
    verified = prepare.verify()
    prepare.require(reviewed_source == verified['preparedSHA256'], 'Compile requires exact reviewed fresh source contract')
    prepare.require(type(attempt) is int and 1 <= attempt <= 3, 'At most three explicitly selected compiler attempts')
    base = prepare.BASE / f'compile-attempt-{attempt}'
    prepare.require(not base.exists(), 'Preserve previous compiler attempt')
    scratch = base / 'scratch'
    (scratch / 'tmp').mkdir(parents=True)
    (base / 'commands').mkdir()
    commands = []

    def save(name, data): (base / name).write_bytes(prepare.stable(data))

    def command(name, argv, timeout=180):
        values = [str(value) for value in argv]
        env = os.environ.copy()
        explicit = {'DEVELOPER_DIR': str(DEVELOPER), 'SDKROOT': str(SDK), 'LC_ALL': 'C',
            'CLANG_MODULE_CACHE_PATH': str(scratch / 'module-cache'), 'SWIFT_MODULECACHE_PATH': str(scratch / 'module-cache'),
            'TMPDIR': str(scratch / 'tmp') + '/'}
        env.update(explicit)
        stdout, stderr = base / 'commands' / (name + '.stdout'), base / 'commands' / (name + '.stderr')
        started, stamp = time.monotonic(), utc()
        timed_out = False
        with stdout.open('wb') as out, stderr.open('wb') as err:
            process = subprocess.Popen(values, cwd=prepare.ROOT, env=env, stdout=out, stderr=err, start_new_session=True)
            try: code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try: code = process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    code = process.wait(timeout=5)
        try: os.killpg(process.pid, 0); group_absent = False
        except ProcessLookupError: group_absent = True
        value = {'name': name, 'argv': values, 'cwd': str(prepare.ROOT), 'explicitEnvironment': explicit,
            'startedUTC': stamp, 'finishedUTC': utc(), 'elapsedSeconds': time.monotonic() - started,
            'exitCode': code, 'timedOut': timed_out, 'timeoutSeconds': timeout, 'ownedProcessGroupAbsent': group_absent,
            'stdout': str(stdout.relative_to(base)), 'stderr': str(stderr.relative_to(base)),
            'stdoutBinding': prepare.row(stdout), 'stderrBinding': prepare.row(stderr)}
        commands.append(value); save('command-receipts.json', {'schema': 1, 'commands': commands})
        print(name + ': exit ' + str(code), flush=True)
        prepare.require(group_absent, 'Owned compiler process group survives; preserve scratch for root recovery')
        return code

    values, source_rows, _, contract = prepare.generated()
    accepted = scratch / 'accepted'
    for name, data in values.items():
        target = accepted / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data); target.chmod(source_rows[name]['mode'])
    prepare.require(tree(accepted) == source_rows, 'Materialized compile source differs')
    tool_paths = [DEVELOPER / 'usr/bin/xcodebuild', SWIFTC, SWIFTC.with_name('swift-frontend'), SWIFTC.with_name('clang'),
                  SWIFTC.with_name('ld'), DEVELOPER.parent / 'Info.plist', SDK / 'SDKSettings.json', Path(sys.executable).resolve()]
    tools = {str(path): prepare.row(path.resolve()) for path in tool_paths}
    save('tool-bindings.json', {'schema': 1, 'tools': tools, 'toolTreeSHA256': prepare.sha(prepare.stable(tools)),
        'python': sys.version, 'platform': platform.platform(), 'SDKPath': str(SDK)})
    version_codes = {
        'xcode': command('xcode-version', [DEVELOPER / 'usr/bin/xcodebuild', '-version']),
        'swift': command('swift-version', [SWIFTC, '--version']),
        'sdk': command('sdk-version', [DEVELOPER / 'usr/bin/xcodebuild', '-version', '-sdk', str(SDK), 'SDKVersion']),
        'python': command('python-version', [sys.executable, '--version'])}
    prepare.require(all(code == 0 for code in version_codes.values()), 'Compiler version query failed')
    prepare.require((base / 'commands/xcode-version.stdout').read_text() == 'Xcode 26.6\nBuild version 17F113\n', 'Pinned Xcode version changed')
    prepare.require((base / 'commands/sdk-version.stdout').read_text().strip() == '26.5', 'Pinned simulator SDK changed')
    app = scratch / 'products/MixerToggleDiagnostics.app'
    frameworks, modules = app / 'Frameworks', scratch / 'modules'
    frameworks.mkdir(parents=True); modules.mkdir()
    common = [SWIFTC, '-swift-version', '6', '-sdk', SDK, '-target', 'arm64-apple-ios26.0-simulator',
              '-module-cache-path', scratch / 'module-cache', '-Onone', '-g']
    core = sorted((accepted / 'source/sdk/Sources/MixerCore').glob('*.swift'))
    ui = sorted((accepted / 'source/sdk/Sources/MixerUI').glob('*.swift'))
    prototype = sorted((accepted / 'source/Prototype').glob('*.swift'))
    codes = {'core': command('mixer-core', common + ['-parse-as-library', '-emit-library', '-emit-module', '-module-name', 'MixerCore',
        '-emit-module-path', modules / 'MixerCore.swiftmodule', '-Xlinker', '-install_name', '-Xlinker', '@rpath/libMixerCore.dylib']
        + core + ['-o', frameworks / 'libMixerCore.dylib']), 'ui': None, 'app': None, 'runner': None}
    if codes['core'] == 0:
        codes['ui'] = command('mixer-ui', common + ['-parse-as-library', '-emit-library', '-emit-module', '-module-name', 'MixerUI',
            '-emit-module-path', modules / 'MixerUI.swiftmodule', '-I', modules, '-L', frameworks, '-lMixerCore',
            '-Xlinker', '-install_name', '-Xlinker', '@rpath/libMixerUI.dylib'] + ui + ['-o', frameworks / 'libMixerUI.dylib'])
    if codes['ui'] == 0:
        codes['app'] = command('app', common + ['-I', modules, '-L', frameworks, '-lMixerUI', '-lMixerCore',
            '-Xlinker', '-rpath', '-Xlinker', '@executable_path/Frameworks'] + prototype + ['-o', app / 'MixerToggleDiagnostics'])
    codes['runner'] = command('runner', [DEVELOPER / 'usr/bin/xcodebuild', 'build-for-testing',
        '-project', accepted / 'harness/MixerToggleUITests.xcodeproj', '-scheme', 'MixerToggleUITests',
        '-sdk', 'iphonesimulator', '-destination', 'generic/platform=iOS Simulator', '-derivedDataPath', scratch / 'runner-build',
        '-disableAutomaticPackageResolution', '-skipPackageUpdates', 'CODE_SIGNING_ALLOWED=NO', 'CODE_SIGNING_REQUIRED=NO',
        'ARCHS=arm64', 'IPHONEOS_DEPLOYMENT_TARGET=26.0', 'COMPILER_INDEX_STORE_ENABLE=NO',
        'SWIFT_MODULE_CACHE_PATH=' + str(scratch / 'module-cache'), 'CLANG_MODULE_CACHE_PATH=' + str(scratch / 'module-cache')], timeout=240)
    prepare.require(all(tree(accepted).get(name) == item for name, item in source_rows.items()), 'Compiler changed source bytes')
    passed = all(value == 0 for value in codes.values())
    if codes['app'] == 0:
        info = plistlib.loads(values['source/Prototype/Info.plist'])
        before = info['MinimumOSVersion']; info['MinimumOSVersion'] = '26.0'
        (app / 'Info.plist').write_bytes(plistlib.dumps(info))
        save('packaging-derivation.json', {'source': source_rows['source/Prototype/Info.plist'], 'product': prepare.row(app / 'Info.plist'),
            'changedProperty': 'MinimumOSVersion', 'before': before, 'after': '26.0', 'sourceUnchanged': True, 'signing': 'unsigned'})
    exported = scratch / 'export'
    exported.mkdir()
    shutil.copytree(app, exported / app.name, symlinks=True)
    runner_products = scratch / 'runner-build/Build/Products'
    if runner_products.is_dir(): shutil.copytree(runner_products, exported / 'runner-products', symlinks=True)
    products = tree(exported)
    product_archive = base / ('products.tar.gz' if passed else 'failed-partial-products.tar.gz')
    archive_products(product_archive, exported, products)
    save('product-manifest.json', {'schema': 1, 'products': products, 'productTreeSHA256': prepare.sha(prepare.stable(products)),
        'archive': prepare.row(product_archive), 'archiveVerifiedAgainstEveryFile': True,
        'target': 'arm64-apple-ios26.0-simulator', 'destination': 'generic/platform=iOS Simulator', 'signing': 'unsigned',
        'purpose': 'Compile-only derivative; separate runtime review and assembly required'})
    bytes_before = sum(path.stat().st_size for path in scratch.rglob('*') if path.is_file() and not path.is_symlink())
    source_unchanged = prepare.verify() == verified
    prepare.require(source_unchanged, 'Bound derivative/archive changed during compilation')
    shutil.rmtree(scratch)
    cleanup = {'performed': True, 'removedPath': str(scratch), 'removedFileBytes': bytes_before, 'scratchAbsent': not scratch.exists(),
        'derivativeSourcesAndProductArchiveVerifiedBeforeRemoval': True, 'ownedCompilerGroupsAbsent': all(c['ownedProcessGroupAbsent'] for c in commands),
        'explicitSimulatorOrDeviceCommands': 0, 'otherProjectsOrInstancesTouched': False}
    save('cleanup.json', cleanup)
    receipt = {'schema': 'mixer.apple-focus-reference-compile-receipt.1', 'observedUTC': utc(),
        'command': [sys.executable, '-B', str(prepare.BASE / 'build.py'), '--attempt', str(attempt), '--reviewed-source', reviewed_source],
        'cwd': str(prepare.ROOT), 'python': sys.version, 'sourceRevisionLabel': contract['sourceRevisionLabel'], **verified,
        'buildScript': prepare.row(prepare.BASE / 'build.py'), 'sourceArchive': prepare.row(prepare.BASE / 'accepted-sources.tar.gz'),
        'status': 'compiled-generic-simulator-only' if passed else 'compile-failed-preserved', 'compilerAttempt': attempt, 'maximumCompilerAttempts': 3,
        'exitCodes': codes, 'allBoundInputsAndSourceUnchanged': source_unchanged, 'productArchive': prepare.row(product_archive),
        'productTreeSHA256': prepare.sha(prepare.stable(products)), 'toolTreeSHA256': prepare.sha(prepare.stable(tools)), 'cleanup': cleanup,
        'nativeExecuted': False, 'runtimeSelected': False, 'explicitSimulatorOrDeviceCommands': 0, 'servicesRequested': 0,
        'uiOrCapturePerformed': False, 'signingCredentialsAccessed': False, 'completeCaseSet': False, 'runPassed': False,
        'fullSixCaseQualification': False, 'carrierAccepted': False, 'physicalPhones': 'disconnected-deferred', 'gaAccepted': False,
        'limitations': ['Swift/generic simulator compilation only; native focus behavior untested.',
            'No runnable runtime packet selected or assembled.', 'Original authored-first failure remains frozen and unresolved.',
            'Physical-phone, comparator, full keyboard, FieldLog, signing, store, operational and GA gates remain open.']}
    save('receipt.json', receipt)
    print('PASS: compile-only products archived; owned compile scratch removed' if passed else 'FAIL: compiler attempt preserved; owned compile scratch removed')
    if not passed: raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', type=int, default=1)
    parser.add_argument('--reviewed-source', required=True)
    args = parser.parse_args()
    main(args.attempt, args.reviewed_source)
