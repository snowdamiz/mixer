#!/usr/bin/env python3
"""Compile the accepted diagnostic overlay; never run app, harness, or authority."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PREP = ROOT / 'verification/apple-toggle-keyboard-focus-diagnostic-v1'
V9 = ROOT / 'verification/apple-toggle-keyboard-focus-v9-preparation'
V3 = ROOT / 'verification/apple-toggle-keyboard-full-case-preparation-v3'
DEVELOPER = Path('/Applications/Xcode_26.6.app/Contents/Developer')
SDK = DEVELOPER / 'Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk'
SWIFTC = DEVELOPER / 'Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc'
SCRATCH = BASE / 'scratch'
COMMANDS = []


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def save(name, value):
    (BASE / name).write_bytes(stable(value))


def row(path):
    if path.is_symlink():
        return {'kind': 'symlink', 'target': os.readlink(path), 'mode': stat.S_IMODE(path.lstat().st_mode)}
    data = path.read_bytes()
    return {'kind': 'file', 'bytes': len(data), 'sha256': sha(data), 'mode': stat.S_IMODE(path.stat().st_mode)}


def tree(path):
    return {str(p.relative_to(path)): row(p) for p in sorted(path.rglob('*')) if p.is_file() or p.is_symlink()}


def bound(path, expected=None):
    if path.is_symlink() or not path.is_file() or path.resolve() != path:
        raise ValueError('Noncanonical input: ' + str(path))
    value = row(path)
    if expected is not None and value['sha256'] != expected:
        raise ValueError('Input changed: ' + str(path))
    return value


def command(name, argv, timeout=180):
    argv = [str(v) for v in argv]
    output = BASE / 'commands'
    output.mkdir(exist_ok=True)
    stdout = output / (name + '.stdout')
    stderr = output / (name + '.stderr')
    env = os.environ.copy()
    explicit = {'DEVELOPER_DIR': str(DEVELOPER), 'SDKROOT': str(SDK),
                'CLANG_MODULE_CACHE_PATH': str(SCRATCH / 'module-cache'),
                'SWIFT_MODULECACHE_PATH': str(SCRATCH / 'module-cache'),
                'TMPDIR': str(SCRATCH / 'tmp') + '/', 'LC_ALL': 'C'}
    env.update(explicit)
    start = time.monotonic()
    observed = now()
    with stdout.open('wb') as out, stderr.open('wb') as err:
        process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=out, stderr=err, start_new_session=True)
        timed_out = False
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, 15)
            try:
                code = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, 9)
                code = process.wait(timeout=5)
    value = {'name': name, 'argv': argv, 'cwd': str(ROOT), 'explicitEnvironment': explicit,
             'startedUTC': observed, 'finishedUTC': now(), 'elapsedSeconds': time.monotonic() - start,
             'exitCode': code, 'timedOut': timed_out, 'timeoutSeconds': timeout,
             'stdout': str(stdout.relative_to(BASE)), 'stderr': str(stderr.relative_to(BASE)),
             'stdoutBinding': row(stdout), 'stderrBinding': row(stderr)}
    COMMANDS.append(value)
    save('command-receipts.json', {'schema': 1, 'commands': COMMANDS})
    print(name + ': exit ' + str(code), flush=True)
    return code


def main():
    if SCRATCH.exists() or (BASE / 'receipt.json').exists():
        raise ValueError('Fresh owned scratch/receipt required; preserve prior attempts')
    (SCRATCH / 'tmp').mkdir(parents=True)
    acceptance = ROOT / 'verification/apple-toggle-keyboard-full-case-root-review/focus-diagnostic-v1/acceptance.json'
    reviewed = json.loads(acceptance.read_bytes())
    accepted_manifest = json.loads((PREP / 'prepared.json').read_bytes())
    inputs = {str(acceptance.relative_to(ROOT)): bound(acceptance),
              str((PREP / 'prepared.json').relative_to(ROOT)): bound(PREP / 'prepared.json'),
              str((PREP / 'source.patch').relative_to(ROOT)): bound(PREP / 'source.patch', reviewed['patchSHA256']),
              str((V9 / 'source-lock.json').relative_to(ROOT)): bound(V9 / 'source-lock.json'),
              str((V3 / 'provenance.json').relative_to(ROOT)): bound(V3 / 'provenance.json')}
    for name, entry in accepted_manifest['preparationInputs'].items():
        inputs[str((PREP / name).relative_to(ROOT))] = bound(PREP / name, entry['sha256'])
    # Only this inspected, standalone stdlib-only module is imported. All six
    # returned sources remain data; no bridge/harness/runtime/authority import.
    spec = importlib.util.spec_from_file_location('accepted_source_preparation_only', PREP / 'prepare.py')
    preparation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preparation)
    originals = preparation.verified_inputs()
    for name, payload in originals.items():
        inputs[name] = bound(ROOT / name, sha(payload))
    patch, manifest = preparation.artifacts()
    if patch != (PREP / 'source.patch').read_bytes() or manifest != (PREP / 'prepared.json').read_bytes():
        raise ValueError('Accepted preparation generation mismatch')
    if accepted_manifest['preparedSourceTreeSHA256'] != reviewed['preparedSourceTreeSHA256']:
        raise ValueError('Root review overlay digest mismatch')
    _, changed = preparation.render(originals)
    materialized = SCRATCH / 'accepted'
    lock = json.loads((V9 / 'source-lock.json').read_bytes())
    for name, expected in lock['sha256'].items():
        source = V9 / 'source' / name
        inputs[str(source.relative_to(ROOT))] = bound(source, expected)
        target = materialized / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    for name, expected in json.loads((V3 / 'provenance.json').read_bytes())['runnerSourceFiles'].items():
        source = V3 / 'harness' / name
        inputs[str(source.relative_to(ROOT))] = bound(source, expected)
        target = materialized / 'harness' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    for name, value in changed.items():
        target = materialized / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value.encode())
        if sha(target.read_bytes()) != accepted_manifest['preparedSources'][name]['sha256']:
            raise ValueError('Overlay render mismatch: ' + name)
    source_tree = tree(materialized)
    save('source-manifest.json', {'schema': 1, 'sourceRevisionLabel': reviewed['sourceRevision'],
         'sourceRevisionMeaning': 'Inherited accepted review label; no Git command in this lane.',
         'inputTreeSHA256': sha(stable(inputs)), 'inputs': inputs,
         'materializedSourceTreeSHA256': sha(stable(source_tree)), 'materializedSources': source_tree,
         'acceptedSixSourceTreeSHA256': reviewed['preparedSourceTreeSHA256'],
         'importedRepositoryModules': ['verification/apple-toggle-keyboard-focus-diagnostic-v1/prepare.py']})
    # Preserve the exact materialized source input, including Python data only.
    with tarfile.open(BASE / 'accepted-sources.tar.gz', 'w:gz') as archive:
        archive.add(materialized, arcname='accepted', recursive=True)
    tool_paths = [DEVELOPER / 'usr/bin/xcodebuild', SWIFTC, SWIFTC.with_name('swift-frontend'),
                  SWIFTC.with_name('clang'), SWIFTC.with_name('ld'),
                  DEVELOPER.parent / 'Info.plist', SDK / 'SDKSettings.json', Path(sys.executable).resolve()]
    tools = {str(path): bound(path.resolve()) for path in tool_paths}
    save('tool-bindings.json', {'schema': 1, 'tools': tools, 'toolTreeSHA256': sha(stable(tools)),
         'pythonVersion': sys.version, 'platform': platform.platform(), 'SDKPath': str(SDK)})
    command('xcode-version', [DEVELOPER / 'usr/bin/xcodebuild', '-version'])
    command('swift-version', [SWIFTC, '--version'])
    command('sdk-version', [DEVELOPER / 'usr/bin/xcodebuild', '-version', '-sdk', str(SDK), 'SDKVersion'])
    command('python-version', [sys.executable, '--version'])
    app = SCRATCH / 'products/MixerToggleDiagnostics.app'
    frameworks = app / 'Frameworks'
    frameworks.mkdir(parents=True)
    modules = SCRATCH / 'modules'
    modules.mkdir()
    common = [SWIFTC, '-swift-version', '6', '-sdk', SDK, '-target', 'arm64-apple-ios26.0-simulator',
              '-module-cache-path', SCRATCH / 'module-cache', '-Onone', '-g']
    core = sorted((materialized / 'source/sdk/Sources/MixerCore').glob('*.swift'))
    ui = sorted((materialized / 'source/sdk/Sources/MixerUI').glob('*.swift'))
    prototype = sorted((materialized / 'source/Prototype').glob('*.swift'))
    core_code = command('attempt-1-mixer-core', common + ['-parse-as-library', '-emit-library', '-emit-module',
        '-module-name', 'MixerCore', '-emit-module-path', modules / 'MixerCore.swiftmodule',
        '-Xlinker', '-install_name', '-Xlinker', '@rpath/libMixerCore.dylib'] + core + ['-o', frameworks / 'libMixerCore.dylib'])
    ui_code = None
    app_code = None
    if core_code == 0:
        ui_code = command('attempt-1-mixer-ui', common + ['-parse-as-library', '-emit-library', '-emit-module',
            '-module-name', 'MixerUI', '-emit-module-path', modules / 'MixerUI.swiftmodule', '-I', modules,
            '-L', frameworks, '-lMixerCore', '-Xlinker', '-install_name', '-Xlinker', '@rpath/libMixerUI.dylib']
            + ui + ['-o', frameworks / 'libMixerUI.dylib'])
    if ui_code == 0:
        app_code = command('attempt-1-app', common + ['-I', modules, '-L', frameworks, '-lMixerUI', '-lMixerCore',
            '-Xlinker', '-rpath', '-Xlinker', '@executable_path/Frameworks'] + prototype + ['-o', app / 'MixerToggleDiagnostics'])
    runner_code = command('attempt-1-runner', [DEVELOPER / 'usr/bin/xcodebuild', 'build-for-testing',
        '-project', materialized / 'harness/MixerToggleUITests.xcodeproj', '-scheme', 'MixerToggleUITests',
        '-sdk', 'iphonesimulator', '-destination', 'generic/platform=iOS Simulator',
        '-derivedDataPath', SCRATCH / 'runner-build', '-disableAutomaticPackageResolution', '-skipPackageUpdates',
        'CODE_SIGNING_ALLOWED=NO', 'CODE_SIGNING_REQUIRED=NO', 'ARCHS=arm64', 'IPHONEOS_DEPLOYMENT_TARGET=26.0',
        'COMPILER_INDEX_STORE_ENABLE=NO', 'SWIFT_MODULE_CACHE_PATH=' + str(SCRATCH / 'module-cache'),
        'CLANG_MODULE_CACHE_PATH=' + str(SCRATCH / 'module-cache')], timeout=240)
    after = tree(materialized)
    if after != source_tree:
        # Xcode creates workspace/user metadata; source bytes must remain exact.
        for name, expected in source_tree.items():
            if after.get(name) != expected:
                raise ValueError('Materialized source mutated: ' + name)
    preserved = {}
    cleanup = {'performed': False, 'scope': 'Only this lane scratch; no simulator instance created or queried.'}
    passed = core_code == ui_code == app_code == runner_code == 0
    if passed:
        info = plistlib.loads((materialized / 'source/Prototype/Info.plist').read_bytes())
        info['MinimumOSVersion'] = '26.0'
        (app / 'Info.plist').write_bytes(plistlib.dumps(info))
        save('packaging-derivation.json', {'scope': 'Owned product metadata only; accepted plist unchanged',
             'source': source_tree['source/Prototype/Info.plist'], 'product': row(app / 'Info.plist'),
             'changedProperty': 'MinimumOSVersion', 'before': '17.0', 'after': '26.0',
             'signing': 'No codesign invocation or credential access; products unsigned.'})
        exported = SCRATCH / 'export'
        exported.mkdir()
        shutil.copytree(app, exported / app.name, symlinks=True)
        shutil.copytree(SCRATCH / 'runner-build/Build/Products', exported / 'runner-products', symlinks=True)
        product_tree = tree(exported)
        archive_path = BASE / 'products.tar.gz'
        with tarfile.open(archive_path, 'w:gz') as archive:
            for child in sorted(exported.iterdir()):
                archive.add(child, arcname=child.name, recursive=True)
        with tarfile.open(archive_path, 'r:gz') as archive:
            actual = {}
            for member in archive.getmembers():
                if member.isfile():
                    payload = archive.extractfile(member).read()
                    actual[member.name] = {'kind': 'file', 'bytes': len(payload), 'sha256': sha(payload), 'mode': member.mode}
                elif member.issym():
                    actual[member.name] = {'kind': 'symlink', 'target': member.linkname, 'mode': member.mode}
        if actual != product_tree:
            raise ValueError('Archive byte/mode/link verification failed')
        save('product-manifest.json', {'schema': 1, 'products': product_tree,
            'productTreeSHA256': sha(stable(product_tree)), 'archive': row(archive_path),
            'archiveVerifiedAgainstEveryFile': True, 'signing': 'unsigned; no signing credential operation',
            'target': 'arm64-apple-ios26.0-simulator', 'destination': 'generic/platform=iOS Simulator',
            'purpose': 'Compilation products retained for separately selected later run; no runtime qualification.'})
        bytes_before = sum(p.stat().st_size for p in SCRATCH.rglob('*') if p.is_file() and not p.is_symlink())
        preserved = {'productsArchive': row(archive_path), 'acceptedSourcesArchive': row(BASE / 'accepted-sources.tar.gz'),
                     'productTreeSHA256': sha(stable(product_tree))}
        shutil.rmtree(SCRATCH)
        cleanup = {'performed': True, 'removedPath': str(SCRATCH), 'removedFileBytes': bytes_before,
                   'scratchAbsent': not SCRATCH.exists(), 'archivesByteVerifiedBeforeRemoval': True,
                   'otherProjectsOrInstancesTouched': False, 'simulatorInstancesCreatedOrQueried': 0}
    unchanged = all(bound(ROOT / name)['sha256'] == expected['sha256'] for name, expected in inputs.items())
    save('cleanup.json', cleanup)
    save('receipt.json', {'schema': 1, 'observedUTC': now(), 'status': 'compiled-generic-simulator-only' if passed else 'compile-failed-retained',
        'sourceRevisionLabel': reviewed['sourceRevision'], 'gitQueried': False, 'acceptedSourceUnchanged': unchanged,
        'acceptedSixSourceTreeSHA256': reviewed['preparedSourceTreeSHA256'], 'materializedSourceTreeSHA256': sha(stable(source_tree)),
        'compilerAttempt': 1, 'maximumCompilerAttempts': 3,
        'exitCodes': {'core': core_code, 'ui': ui_code, 'app': app_code, 'runner': runner_code},
        'products': preserved, 'cleanup': cleanup, 'nativeExecuted': False, 'nativeInstancesQueried': False,
        'uiOrCapturePerformed': False, 'signingCredentialsAccessed': False, 'networkServiceRequested': False,
        'physicalPhones': 'disconnected-deferred', 'runtimeSelected': False, 'acceptanceCredit': 'Swift compilation only',
        'limitations': ['No simulator/device inventory, boot, app launch, test execution, UI, capture, or physical-phone operation.',
            'No focus behavior/oracle/first-Tab repair or native acceptance; retained failed actualNativeFocusTraversal remains unresolved.',
            'No carrier, OTA, immutable published-package dogfood, signing, store, customer, operational, or GA qualification.',
            'UIKit/XCTest runtime semantics and diagnostic timing interference remain unverified.']})
    print('COMPILE_ONLY_PASS' if passed else 'COMPILE_FAILURE_RETAINED', flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
