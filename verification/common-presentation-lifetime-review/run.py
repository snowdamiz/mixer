#!/usr/bin/env python3
"""Independent probes against an immutable copy of the owner's frozen source."""
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
parser.add_argument('--modes', nargs='+', choices=['debug', 'release', 'tsan'], default=['debug', 'release', 'tsan'])
args = parser.parse_args()
assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
out = HERE / args.name
out.mkdir(exist_ok=False)
work = HERE / '.build' / args.name
source = work / 'source'
source.mkdir(parents=True, exist_ok=False)
owner_receipt = ROOT / 'verification/common-presentation-lifetime/final-1/receipt.json'
owner = json.loads(owner_receipt.read_text())
owner_source = Path(owner['source'])
owner_work = owner_source.parent
assert owner['source_tree_sha256'] == '8d540e60a53c40267e68de822cee181e22f92b69e61fe023d03e05ad6f247f47'
files = dict(owner['source_files'])
for relative, digest in files.items():
    original = owner_source / relative
    assert sha(original) == digest, relative
    if relative.startswith('capability-activation/') or relative in ['docs/android-signed-ui-binding-contract.md', 'verification/android-binding-contract-acceptance.json']:
        assert sha(ROOT / relative) == digest, relative
    destination = source / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original, destination)
    destination.chmod(0o444)
for filename in ['IndependentLifetimeTests.swift', 'PrivateReceiptClient.swift', 'run.py']:
    relative = str((HERE / filename).relative_to(ROOT))
    destination = source / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / filename, destination)
    destination.chmod(0o444)
    files[relative] = sha(destination)
dependency = ROOT / owner['dependency_receipt']
assert sha(dependency) == owner['dependency_receipt_sha256']
base = json.loads(dependency.read_text())
base_work = Path(base['dylib']).parents[1]
for relative, digest in owner['dependency_artifacts'].items():
    assert sha(base_work / relative) == digest, relative
base_manifest = ROOT / base['source_manifest']
assert sha(base_manifest) == owner['dependency_source_manifest_sha256']
for relative, digest in json.loads(base_manifest.read_text())['files'].items():
    assert sha(Path(base['source']) / relative) == digest, relative

receipt = {
    'started_utc': datetime.now(timezone.utc).isoformat(),
    'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'owner_receipt': str(owner_receipt.relative_to(ROOT)), 'owner_receipt_sha256': sha(owner_receipt),
    'owner_source_tree_sha256': owner['source_tree_sha256'],
    'source': str(source), 'source_files': files,
    'source_tree_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
    'dependency_receipt': owner['dependency_receipt'], 'dependency_receipt_sha256': sha(dependency),
    'dependency_artifacts': owner['dependency_artifacts'],
    'dependency_source_manifest_sha256': sha(base_manifest),
    'commands': [], 'artifacts': {},
    'scope': 'Independent complete activation source build and host executable lifetime/core probes against owner final-1. Actual Swift Tasks, held MainActor retirement, 64-way data-only reentry and 64 bind/core-close races; public and testable private-constructor rejection. Dependency objects/archive are retained exact builds, not reinstrumented. Host Apple model retirement is not Android Looper/JNI/native/device or Apple public-model destruction proof. No physical, package consumer, signing, store, release or GA evidence.',
    'pending': ['Android binding remains unsupported; C/JNI integration is not present.', 'No physical phones are discovered or run.', 'Positive visible native window and immutable published-package consumer qualification remain pending.'],
}
env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
env.pop('MIXER_GUEST_UI_VISIBLE_WINDOW', None)

def save():
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

def stable():
    for relative, digest in files.items():
        assert sha(source / relative) == digest, relative
    for relative, digest in owner['source_files'].items():
        if relative.startswith('capability-activation/'):
            assert sha(ROOT / relative) == digest, relative

def run(name, argv, expected=0, extra=None):
    stable()
    argv = [str(x) for x in argv]
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=source, env=env | (extra or {}), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
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
    run('python-version', ['python3', '--version'])
    run('platform', ['uname', '-a'])
    xctest = run('xctest-path', ['xcrun', '--find', 'xctest']).strip()
    resource = run('clang-resource', ['xcrun', 'clang', '-print-resource-dir']).strip()
    tsan = Path(resource) / 'lib/darwin/libclang_rt.tsan_osx_dynamic.dylib'
    frameworks = Path(env['DEVELOPER_DIR']) / 'Platforms/MacOSX.platform/Developer/Library/Frameworks'
    overlays = frameworks.parents[1] / 'usr/lib'
    source_tests = source / 'capability-activation/Tests/MixerCapabilityActivationTests'
    review_source = source / HERE.relative_to(ROOT)
    for mode in args.modes:
        products = work / mode
        products.mkdir()
        original = next(row['argv'] for row in owner['commands'] if row['name'] == mode + '-full-module-link')
        argv = [value.replace(str(owner_source), str(source)).replace(str(owner_work / mode), str(products)).replace('libMixerCommonPresentation.dylib', 'libMixerIndependentPresentation.dylib') for value in original]
        run(mode + '-full-module-link', argv)
        prefix = next(row['argv'] for row in owner['commands'] if row['name'] == mode + '-xctest-link')
        prefix = prefix[:prefix.index('-emit-library')]
        flags = [value.replace(str(owner_work / mode), str(products)) for value in prefix]
        bundle = products / 'MixerIndependentPresentationTests.xctest'
        executable = bundle / 'Contents/MacOS/MixerIndependentPresentationTests'
        executable.parent.mkdir(parents=True)
        shutil.copytree(source_tests / 'Fixtures', bundle / 'Contents/Resources/Fixtures')
        (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': executable.name, 'CFBundleIdentifier': 'dev.mixer.independent-presentation-tests', 'CFBundlePackageType': 'BNDL', 'CFBundleVersion': '1'}))
        link = ['-L', products, '-lMixerIndependentPresentation', '-L', overlays, '-Xlinker', '-rpath', '-Xlinker', products, '-Xlinker', '-rpath', '-Xlinker', frameworks, '-Xlinker', '-rpath', '-Xlinker', overlays]
        run(mode + '-tests-link', flags + ['-emit-library', '-module-name', 'MixerIndependentPresentationTests', review_source / 'IndependentLifetimeTests.swift', source_tests / 'CapabilityColdStartRuntimeTests.swift', source / 'verification/common-presentation-lifetime/TestResources.swift'] + link + ['-o', executable])
        output = run(mode + '-tests', [xctest, bundle], extra={'DYLD_INSERT_LIBRARIES': str(tsan)} if mode == 'tsan' else None)
        assert 'with 0 failures' in output and 'IndependentPresentationLifetimeTests' in output
        regular = run(mode + '-public-api-rejection', flags + ['-typecheck', source / 'verification/common-presentation-lifetime/PrivateClient.swift'], expected=1)
        for name in ['CapabilityPreparedPresentation', 'CapabilityPresentationJoinPermit', 'CapabilityPresentationLifetimeReceipt', 'CapabilityGuestUIPresentationBinding']:
            assert "cannot find type '" + name + "' in scope" in regular
        private = run(mode + '-private-constructor-rejection', flags + ['-typecheck', review_source / 'PrivateReceiptClient.swift'], expected=1)
        assert private.count("initializer is inaccessible") >= 4
        receipt['artifacts'][mode] = {str(path): sha(path) for path in [products / 'libMixerIndependentPresentation.dylib', executable, products / 'MixerCapabilityActivation.swiftmodule']}
        save()
    receipt['result'] = 'Independent source-bound probes passed in all selected modes.'
except BaseException as error:
    receipt['result'] = 'failed verification preserved'
    receipt['problem'] = str(error)
    raise
finally:
    receipt['completed_utc'] = datetime.now(timezone.utc).isoformat()
    save()
