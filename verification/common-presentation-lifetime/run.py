#!/usr/bin/env python3
"""Freeze the actual activation source; compile/link with exact retained dependencies."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
parser.add_argument('--modes', nargs='+', default=['debug', 'release', 'tsan'], choices=['debug', 'release', 'tsan'])
args = parser.parse_args()
assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
out = HERE / args.name
out.mkdir(exist_ok=False)
work = HERE / '.build' / args.name
source = work / 'source'
source.mkdir(parents=True, exist_ok=False)
dependency = ROOT / 'verification/guest-ui-teardown-window/builds/current-caaa005-1/build-receipt.json'
assert sha(dependency) == '8abd4367111a5cd4f4d4438750bfb24bc588d56e1e98fbe269f781fddd6b799c'
base = json.loads(dependency.read_text())
base_work = Path(base['dylib']).parents[1]
base_source = Path(base['source'])
manifest = json.loads((ROOT / base['source_manifest']).read_text())
for relative, digest in base['artifacts'].items():
    assert sha(base_work / relative) == digest, relative
for relative, digest in manifest['files'].items():
    assert sha(base_source / relative) == digest, relative
    if relative.startswith(('sdk/Sources/', 'updates/Sources/', 'runtime-identity/Sources/', 'experimental-capability-runtime/Sources/')):
        assert sha(ROOT / relative) == digest, relative
paths = sorted((ROOT / 'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))
tests = ROOT / 'capability-activation/Tests/MixerCapabilityActivationTests'
paths += [tests / name for name in ['GuestUIPresentationLifetimeTests.swift', 'GuestUIPresentationModelTests.swift', 'GuestUIPresentationWindowTests.swift', 'CapabilityColdStartRuntimeTests.swift']]
paths += sorted((tests / 'Fixtures').glob('*'))
paths += [HERE / name for name in ['TestMain.swift', 'TestResources.swift', 'PrivateClient.swift', 'run.py']]
paths += [ROOT / 'docs/android-signed-ui-binding-contract.md', ROOT / 'verification/android-binding-contract-acceptance.json']
files = {}
for path in paths:
    relative = str(path.relative_to(ROOT))
    dest = source / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(path.read_bytes())
    files[relative] = sha(dest)
    dest.chmod(0o444)
receipt = {
    'started_utc': datetime.now(timezone.utc).isoformat(),
    'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'source_files': files, 'source_tree_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
    'source': str(source), 'dependency_receipt': str(dependency.relative_to(ROOT)), 'dependency_receipt_sha256': sha(dependency),
    'dependency_artifacts': base['artifacts'], 'dependency_source_manifest_sha256': base['source_manifest_sha256'],
    'commands': [], 'artifacts': {},
    'scope': 'Actual complete current activation source compiled and linked with exact retained Swift/C dependency objects and VM archive. Current common/core/worker/presentation source and tests are rebuilt in each selected mode. TSan instruments these rebuilt files; retained dependency objects are not rebuilt or instrumented. Real host Task joins, XCTest core lifecycle regressions and Swift Testing Apple model/hidden-window regressions; public API rejection. No native Android/physical iOS or Android, JNI, positive visible display, immutable package consumer, release or GA qualification.',
    'pending': ['Android binding remains unsupported and unimplemented.', 'Visible native window opt-in test is explicitly skipped.', 'Physical phones remain disconnected; no discovery or run is attempted.'],
}
env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
env.pop('MIXER_GUEST_UI_VISIBLE_WINDOW', None)

def save():
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

def stable():
    for relative, digest in files.items():
        assert sha(source / relative) == digest == sha(ROOT / relative), relative

def run(name, argv, expected=0, extra=None):
    stable()
    argv = [str(value) for value in argv]
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=source, env=env | (extra or {}), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        data, code = result.stdout, result.returncode
    except subprocess.TimeoutExpired as error:
        data, code = (error.stdout or b'') + b'\nTIMEOUT\n', 124
    log = out / (name + '.log')
    log.write_bytes(data)
    receipt['commands'].append({'name': name, 'argv': argv, 'cwd': str(source), 'environment': {'DEVELOPER_DIR': env['DEVELOPER_DIR']} | (extra or {}), 'seconds': time.monotonic() - start, 'exit': code, 'expected_exit': expected, 'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
    save(); print(name, code, flush=True)
    stable()
    assert code == expected, name
    assert b'WARNING: ThreadSanitizer' not in data, name
    return data.decode(errors='replace')

try:
    run('swift-version', ['xcrun', 'swiftc', '--version'])
    run('xcode-version', ['xcodebuild', '-version'])
    run('git-version', ['git', '--version'])
    run('python-version', ['python3', '--version'])
    run('platform', ['uname', '-a'])
    xctest = run('xctest-path', ['xcrun', '--find', 'xctest']).strip()
    resource = run('clang-resource', ['xcrun', 'clang', '-print-resource-dir']).strip()
    tsan = Path(resource) / 'lib/darwin/libclang_rt.tsan_osx_dynamic.dylib'
    testing_macros = Path(env['DEVELOPER_DIR']) / 'Toolchains/XcodeDefault.xctoolchain/usr/lib/swift/host/plugins/testing/libTestingMacros.dylib'
    receipt['testing_macros'] = {'path': str(testing_macros), 'sha256': sha(testing_macros)}
    original = next(row['argv'] for row in base['commands'] if row['name'] == 'link-current-runtime')
    frameworks = Path(env['DEVELOPER_DIR']) / 'Platforms/MacOSX.platform/Developer/Library/Frameworks'
    overlays = frameworks.parents[1] / 'usr/lib'
    source_tests = source / 'capability-activation/Tests/MixerCapabilityActivationTests'
    source_here = source / 'verification/common-presentation-lifetime'
    for mode in args.modes:
        products = work / mode
        products.mkdir()
        mode_flags = ['-O'] if mode == 'release' else ['-sanitize=thread'] if mode == 'tsan' else []
        library = products / 'libMixerCommonPresentation.dylib'
        argv = []
        for arg in original:
            if arg.startswith(str(base_source / 'capability-activation/Sources/MixerCapabilityActivation')):
                continue
            if arg == base['dylib']: arg = str(library)
            elif arg.endswith('/products/MixerCapabilityActivation.swiftmodule'): arg = str(products / 'MixerCapabilityActivation.swiftmodule')
            elif arg == '@rpath/libMixerGuestUITeardownRuntime.dylib': arg = '@rpath/' + library.name
            argv.append(arg)
        insertion = argv.index('-emit-library')
        argv[insertion:insertion] = mode_flags + [str(path) for path in sorted((source / 'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))]
        run(mode + '-full-module-link', argv)
        prefix = original[:original.index('-emit-library')]
        flags = prefix[:2] + ['-I', products] + prefix[2:] + mode_flags + ['-I', overlays, '-F', frameworks]
        link = ['-L', products, '-lMixerCommonPresentation', '-L', overlays, '-Xlinker', '-rpath', '-Xlinker', products, '-Xlinker', '-rpath', '-Xlinker', frameworks, '-Xlinker', '-rpath', '-Xlinker', overlays]
        bundle = products / 'MixerCommonPresentationTests.xctest'
        executable = bundle / 'Contents/MacOS/MixerCommonPresentationTests'
        executable.parent.mkdir(parents=True)
        resources = bundle / 'Contents/Resources'
        shutil.copytree(source_tests / 'Fixtures', resources / 'Fixtures')
        (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': executable.name, 'CFBundleIdentifier': 'dev.mixer.common-presentation-tests', 'CFBundlePackageType': 'BNDL', 'CFBundleVersion': '1'}))
        run(mode + '-xctest-link', flags + ['-emit-library', '-module-name', 'MixerCommonPresentationTests', source_tests / 'GuestUIPresentationLifetimeTests.swift', source_tests / 'CapabilityColdStartRuntimeTests.swift', source_here / 'TestResources.swift'] + link + ['-o', executable])
        output = run(mode + '-xctests', [xctest, bundle], extra={'DYLD_INSERT_LIBRARIES': str(tsan)} if mode == 'tsan' else None)
        assert 'with 0 failures' in output and 'GuestUIPresentationLifetimeTests' in output
        model = products / 'MixerPresentationModels'
        run(mode + '-model-tests-link', flags + ['-load-plugin-library', testing_macros, '-module-name', 'MixerPresentationModels', source_tests / 'GuestUIPresentationModelTests.swift', source_tests / 'GuestUIPresentationWindowTests.swift', source_here / 'TestMain.swift'] + link + ['-o', model])
        model_output = run(mode + '-model-tests', [model], extra={'DYLD_INSERT_LIBRARIES': str(tsan)} if mode == 'tsan' else None)
        assert 'passed' in model_output and 'skipped' in model_output
        negative = run(mode + '-private-api', flags + ['-typecheck', source_here / 'PrivateClient.swift'], expected=1)
        for name in ['CapabilityPreparedPresentation', 'CapabilityPresentationJoinPermit', 'CapabilityPresentationLifetimeReceipt', 'CapabilityGuestUIPresentationBinding']:
            assert "cannot find type '" + name + "' in scope" in negative
        receipt['artifacts'][mode] = {str(path): sha(path) for path in [library, executable, model, products / 'MixerCapabilityActivation.swiftmodule']}
        save()
    receipt['result'] = 'Selected full-module builds, real Task/core XCTest, Apple model/hidden-window regressions and private API rejection passed.'
except BaseException as error:
    receipt['result'] = 'failed verification preserved'
    receipt['problem'] = str(error)
    raise
finally:
    receipt['completed_utc'] = datetime.now(timezone.utc).isoformat()
    save()
