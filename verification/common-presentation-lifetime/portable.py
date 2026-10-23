#!/usr/bin/env python3
"""Execute the actual #else presentation branch on host, with MixerApple unavailable."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'portable-1'
OUT.mkdir(exist_ok=False)
WORK = HERE / '.build/portable-1'
WORK.mkdir(parents=True, exist_ok=False)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
reference = HERE / 'final-1/receipt.json'
final = json.loads(reference.read_text())
assert final['result'].startswith('Selected full-module builds')
source = Path(final['source'])
for relative, digest in final['source_files'].items():
    assert sha(source / relative) == digest == sha(ROOT / relative), relative
dependency = ROOT / final['dependency_receipt']
assert sha(dependency) == final['dependency_receipt_sha256']
base = json.loads(dependency.read_text())
base_work = Path(base['dylib']).parents[1]
base_source = Path(base['source'])
for relative, digest in base['artifacts'].items():
    assert sha(base_work / relative) == digest, relative
original = next(row['argv'] for row in base['commands'] if row['name'] == 'link-current-runtime')
modules = WORK / 'real-dependency-modules'
modules.mkdir()
copied = {}
for path in sorted((base_work / 'products').glob('*.swiftmodule')):
    if path.stem in ['MixerApple', 'MixerCapabilityActivation']:
        continue
    destination = modules / path.name
    destination.write_bytes(path.read_bytes())
    copied[str(destination)] = sha(destination)
assert not (modules / 'MixerApple.swiftmodule').exists()
test_source = WORK / 'source'
test_source.mkdir()
inputs = {}
for path in [Path(__file__), HERE / 'PortableTests.swift']:
    dest = test_source / path.name
    dest.write_bytes(path.read_bytes()); dest.chmod(0o444)
    inputs[str(path.relative_to(ROOT))] = sha(dest)
receipt = {
    'started_utc': datetime.now(timezone.utc).isoformat(),
    'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'reference_receipt': str(reference.relative_to(ROOT)), 'reference_receipt_sha256': sha(reference),
    'source_tree_sha256': final['source_tree_sha256'], 'extra_inputs': inputs,
    'real_dependency_modules': copied, 'commands': [], 'artifacts': {},
    'scope': 'Actual complete activation source from the successful final host matrix, compiled on macOS with the real MixerApple module intentionally unavailable. This executes its unchanged portable #else rejection/unused-obligation-retirement branch, without mocks or replacement product source. This is NOT an Android compiler, native transport, JNI, runtime, or device receipt. No C facade/endpoint/resource owner or presentation Task is constructed by this branch.',
}
env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')

def save():
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

def stable():
    for relative, digest in final['source_files'].items():
        assert sha(source / relative) == digest == sha(ROOT / relative), relative
    for relative, digest in inputs.items():
        assert sha(ROOT / relative) == digest, relative

def run(name, argv, extra=None):
    stable()
    argv = [str(value) for value in argv]
    started = time.monotonic()
    result = subprocess.run(argv, cwd=test_source, env=env | (extra or {}), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    log = OUT / (name + '.log')
    log.write_bytes(result.stdout)
    receipt['commands'].append({'name': name, 'argv': argv, 'cwd': str(test_source), 'environment': {'DEVELOPER_DIR': env['DEVELOPER_DIR']} | (extra or {}), 'exit': result.returncode, 'seconds': time.monotonic() - started, 'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
    save(); print(name, result.returncode, flush=True)
    stable()
    assert result.returncode == 0, name
    assert b'WARNING: ThreadSanitizer' not in result.stdout, name
    return result.stdout.decode(errors='replace')

try:
    run('swift-version', ['xcrun', 'swiftc', '--version'])
    run('xcode-version', ['xcodebuild', '-version'])
    xctest = run('xctest-path', ['xcrun', '--find', 'xctest']).strip()
    resource = run('clang-resource', ['xcrun', 'clang', '-print-resource-dir']).strip()
    tsan = Path(resource) / 'lib/darwin/libclang_rt.tsan_osx_dynamic.dylib'
    frameworks = Path(env['DEVELOPER_DIR']) / 'Platforms/MacOSX.platform/Developer/Library/Frameworks'
    overlays = frameworks.parents[1] / 'usr/lib'
    for mode in ['debug', 'release', 'tsan']:
        products = WORK / mode
        products.mkdir()
        library = products / 'libMixerPortablePresentation.dylib'
        flags = ['-O'] if mode == 'release' else ['-sanitize=thread'] if mode == 'tsan' else []
        argv = []
        for arg in original:
            if arg.startswith(str(base_source / 'capability-activation/Sources/MixerCapabilityActivation')):
                continue
            if arg == str(base_work / 'products'): arg = str(modules)
            elif arg == base['dylib']: arg = str(library)
            elif arg.endswith('/products/MixerCapabilityActivation.swiftmodule'): arg = str(products / 'MixerCapabilityActivation.swiftmodule')
            elif arg == '@rpath/libMixerGuestUITeardownRuntime.dylib': arg = '@rpath/' + library.name
            argv.append(arg)
        insertion = argv.index('-emit-library')
        argv[insertion:insertion] = flags + [str(path) for path in sorted((source / 'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))]
        run(mode + '-portable-full-module-link', argv)
        prefix = argv[:argv.index('-emit-library')]
        # Prefix contains actual product source paths for the module build;
        # remove those before compiling the test client against that module.
        prefix = [arg for arg in prefix if not arg.endswith('.swift')]
        bundle = products / 'MixerPortablePresentationTests.xctest'
        executable = bundle / 'Contents/MacOS/MixerPortablePresentationTests'
        executable.parent.mkdir(parents=True)
        (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': executable.name, 'CFBundleIdentifier': 'dev.mixer.portable-presentation-tests', 'CFBundlePackageType': 'BNDL', 'CFBundleVersion': '1'}))
        run(mode + '-portable-tests-link', prefix[:2] + ['-I', products] + prefix[2:] + ['-emit-library', '-module-name', 'MixerPortablePresentationTests', '-I', overlays, '-F', frameworks, test_source / 'PortableTests.swift', '-L', products, '-lMixerPortablePresentation', '-L', overlays, '-Xlinker', '-rpath', '-Xlinker', products, '-Xlinker', '-rpath', '-Xlinker', frameworks, '-Xlinker', '-rpath', '-Xlinker', overlays, '-o', executable])
        output = run(mode + '-portable-tests', [xctest, bundle], {'DYLD_INSERT_LIBRARIES': str(tsan)} if mode == 'tsan' else None)
        assert 'Executed 1 test, with 0 failures' in output
        receipt['artifacts'][mode] = {str(path): sha(path) for path in [library, executable, products / 'MixerCapabilityActivation.swiftmodule']}
    receipt['result'] = 'Actual portable branch full-module compilation and unused-obligation rejection tests passed in Debug/Release/TSan on host.'
except BaseException as error:
    receipt['result'] = 'failed portable verification preserved'; receipt['problem'] = str(error)
    raise
finally:
    receipt['completed_utc'] = datetime.now(timezone.utc).isoformat(); save()
