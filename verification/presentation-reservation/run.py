#!/usr/bin/env python3
"""Compile the exact reservation and its real error dependency; run isolated XCTest."""
import argparse
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
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
args = parser.parse_args()
assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
out = HERE / args.name
out.mkdir(exist_ok=False)
work = HERE / '.build' / args.name
source = work / 'source'
source.mkdir(parents=True, exist_ok=False)
names = [
    'updates/Sources/MixerUpdates/CanonicalValue.swift',
    'capability-activation/Sources/MixerCapabilityActivation/CapabilityAttemptReservation.swift',
    'capability-activation/Tests/MixerCapabilityActivationTests/CapabilityAttemptReservationTests.swift',
    'verification/presentation-reservation/PrivateClient.swift',
    'verification/presentation-reservation/run.py',
]
files = {}
for name in names:
    dest = source / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes((ROOT / name).read_bytes())
    files[name] = sha(dest)
    dest.chmod(0o444)
receipt = {
    'started_at': datetime.now(timezone.utc).isoformat(),
    'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'source_files': files,
    'tree_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
    'source': str(source), 'commands': [], 'artifacts': {},
    'scope': 'Internal outer reservation only. Exact current reservation and entire reservation XCTest file, with unmodified actual CanonicalValue.swift compiled as the error dependency. No simulated reservation implementation, full activation graph, presentation binding, JNI, Android runtime, device, signed release or GA qualification.',
}
env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')

def save():
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

def stable():
    for name, expected in files.items():
        assert sha(source / name) == expected == sha(ROOT / name), name

def run(name, command, extra=None, expected=0):
    stable()
    start = time.monotonic()
    try:
        result = subprocess.run([str(x) for x in command], cwd=source, env=env | (extra or {}), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        data, code = result.stdout, result.returncode
    except subprocess.TimeoutExpired as error:
        data, code = (error.stdout or b'') + b'\nTIMEOUT\n', 124
    log = out / (name + '.log')
    log.write_bytes(data)
    receipt['commands'].append({'name': name, 'argv': [str(x) for x in command], 'cwd': str(source), 'environment': {'DEVELOPER_DIR': env['DEVELOPER_DIR']} | (extra or {}), 'exit': code, 'expected_exit': expected, 'seconds': time.monotonic() - start, 'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
    save()
    stable()
    print(name + ': ' + str(code), flush=True)
    assert code == expected, name
    assert b'WARNING: ThreadSanitizer' not in data, name
    return data.decode(errors='replace')

try:
    run('swift-version', ['xcrun', 'swiftc', '--version'])
    run('xcode-version', ['xcodebuild', '-version'])
    xctest = run('xctest-path', ['xcrun', '--find', 'xctest']).strip()
    frameworks = Path(env['DEVELOPER_DIR']) / 'Platforms/MacOSX.platform/Developer/Library/Frameworks'
    overlays = frameworks.parents[1] / 'usr/lib'
    resource = run('clang-resource', ['xcrun', 'clang', '-print-resource-dir']).strip()
    tsan = Path(resource) / 'lib/darwin/libclang_rt.tsan_osx_dynamic.dylib'
    for mode in ['debug', 'release', 'tsan']:
        products = work / mode
        products.mkdir()
        flags = ['xcrun', 'swiftc', '-parse-as-library', '-swift-version', '6', '-warnings-as-errors']
        if mode == 'release': flags += ['-O']
        if mode == 'tsan': flags += ['-sanitize=thread']
        updates = products / 'MixerUpdates.o'
        run(mode + '-error-module', flags + ['-emit-module', '-emit-object', '-module-name', 'MixerUpdates', '-emit-module-path', products / 'MixerUpdates.swiftmodule', source / names[0], '-o', updates])
        library = products / 'libMixerPresentationReservation.dylib'
        run(mode + '-reservation-module', flags + ['-emit-module', '-emit-library', '-enable-testing', '-module-name', 'MixerCapabilityActivation', '-emit-module-path', products / 'MixerCapabilityActivation.swiftmodule', '-I', products, source / names[1], updates, '-Xlinker', '-install_name', '-Xlinker', '@rpath/' + library.name, '-o', library])
        bundle = products / 'MixerPresentationReservationTests.xctest'
        executable = bundle / 'Contents/MacOS/MixerPresentationReservationTests'
        executable.parent.mkdir(parents=True)
        (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': executable.name, 'CFBundleIdentifier': 'dev.mixer.presentation-reservation-tests', 'CFBundlePackageType': 'BNDL', 'CFBundleVersion': '1'}))
        run(mode + '-tests-link', flags + ['-emit-library', '-module-name', 'MixerPresentationReservationTests', '-I', products, '-I', overlays, '-F', frameworks, source / names[2], '-L', products, '-lMixerPresentationReservation', '-L', overlays, '-Xlinker', '-rpath', '-Xlinker', products, '-Xlinker', '-rpath', '-Xlinker', frameworks, '-Xlinker', '-rpath', '-Xlinker', overlays, '-o', executable])
        log = run(mode + '-tests', [xctest, bundle], {'DYLD_INSERT_LIBRARIES': str(tsan)} if mode == 'tsan' else None)
        assert 'Executed 1 test, with 0 failures' in log, mode
        negative = run(mode + '-private-api', flags + ['-I', products, '-typecheck', source / names[3]], expected=1)
        assert "cannot find type 'CapabilityPresentationObligation' in scope" in negative
        receipt['artifacts'][mode] = {str(p): sha(p) for p in [updates, library, executable, products / 'MixerCapabilityActivation.swiftmodule']}
        save()
    receipt['result'] = 'Debug/Release/TSan reservation tests and public-access rejections passed. Full activation integration remains pending.'
except BaseException as error:
    receipt['result'] = 'failed check preserved'
    receipt['problem'] = str(error)
    raise
finally:
    receipt['completed_at'] = datetime.now(timezone.utc).isoformat()
    save()
