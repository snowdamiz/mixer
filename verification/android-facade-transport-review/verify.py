#!/usr/bin/env python3
"""Independent facade/entry/progress probes and preserved regressions; no devices."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BUILD = OUT / 'build'
BUILD.mkdir(exist_ok=True)
TRANSPORT = ROOT / 'native/android/signed-guest-ui/transport'
XCODE = Path('/Applications/Xcode_26.6.app/Contents/Developer')
CLANG = XCODE / 'Toolchains/XcodeDefault.xctoolchain/usr/bin/clang'
SYSROOT = XCODE / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'
NDK = Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d')
BIN = NDK / 'toolchains/llvm/prebuilt/darwin-x86_64/bin'
ANDROID = BIN / 'aarch64-linux-android30-clang'
ENV = dict(os.environ, DEVELOPER_DIR=str(XCODE), ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1', TSAN_OPTIONS='halt_on_error=1')
ENV.pop('SDKROOT', None)
commands = []

def run(name, argv, *, expected=0, append=False, timeout=25):
    argv = list(map(str, argv))
    result = subprocess.run(argv, cwd=ROOT, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    path = OUT / (name + '.log')
    with path.open('ab' if append else 'wb') as file:
        file.write(result.stdout)
    commands.append({'argv': argv, 'exit_code': result.returncode, 'expected': expected,
                     'output': str(path.relative_to(ROOT))})
    if (result.returncode == 0) != (expected == 0):
        (OUT / 'earliest-failure.json').write_text(json.dumps(commands[-1], indent=2) + '\n')
        raise RuntimeError(name + ': ' + result.stdout.decode(errors='replace'))
    return result.stdout.decode(errors='replace')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    paths = [p for p in TRANSPORT.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT / p for p in ['AGENTS.md', 'docs/android-guest-ui-transport-design.md',
              'docs/android-signed-ui-binding-contract.md', 'verification/android-binding-contract-acceptance.json',
              'verification/android-transport-review/probes.c', 'verification/android-facade-transport/receipt.json',
              'verification/android-facade-transport/source-manifest.sha256']]
    paths += [OUT / 'probes.c', OUT / 'verify.py']
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}

before = sources()
acceptance = json.loads((ROOT / 'verification/android-binding-contract-acceptance.json').read_text())
assert sha(ROOT / acceptance['contract']) == acceptance['contract_sha256']
owner_receipt = json.loads((ROOT / 'verification/android-facade-transport/receipt.json').read_text())
owner_manifest = dict((line.split('  ', 1)[1], line.split('  ', 1)[0]) for line in (ROOT / owner_receipt['source_manifest']).read_text().splitlines())
for name, digest in owner_manifest.items():
    assert sha(ROOT / name) == digest, 'Owner receipt source mismatch: ' + name
manifest = ''.join(f'{value}  {name}\n' for name, value in before.items())
(OUT / 'source-before.sha256').write_text(manifest)
revision = run('source-revision', ['git', 'rev-parse', 'HEAD']).strip()
run('source-status', ['git', 'status', '--short'])
versions = {'host_clang': run('host-clang-version', [CLANG, '--version']),
            'android_clang': run('android-clang-version', [ANDROID, '--version']),
            'python': run('python-version', [sys.executable, '--version']),
            'ndk': (NDK / 'source.properties').read_text()}
flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wpedantic', '-Wconversion', '-Wsign-conversion', '-Wstrict-prototypes']
modes = {'debug': ['-O0', '-g'], 'release': ['-O2', '-DNDEBUG'],
         'asan-ubsan': ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'],
         'tsan': ['-O1', '-g', '-fsanitize=thread', '-fno-omit-frame-pointer']}
suites = {
    'review': ([TRANSPORT / 'platform_android.c', OUT / 'probes.c'], 'MXUIT_REVIEW_PASS', 11),
    'original': ([TRANSPORT / 'tests/host_tests.c', TRANSPORT / 'tests/progress_probe.c'], 'MXUIT_CASE_PASS', 26),
    'prior-review': ([TRANSPORT / 'platform_android.c', ROOT / 'verification/android-transport-review/probes.c', TRANSPORT / 'tests/progress_probe.c'], 'ANDROID_TRANSPORT_REVIEW_PASS', 9),
    'owner-facade': ([TRANSPORT / 'platform_android.c', TRANSPORT / 'tests/facade_tests.c'], 'MXUIT_FACADE_PASS', 27),
}
results = {}
for mode, options in modes.items():
    results[mode] = {}
    for suite, (inputs, marker, count) in suites.items():
        name = mode + '-' + suite
        binary = BUILD / name
        run(name + '-build', [CLANG, '-isysroot', SYSROOT, '-idirafter', BIN / '../sysroot/usr/include',
                             *flags, '-pthread', '-DMIXER_UI_TRANSPORT_TESTING=1', *options,
                             TRANSPORT / 'transport.c', *inputs, '-o', binary])
        cases = run(name + '-cases', [binary, '--list']).splitlines()
        assert len(cases) == count, name
        (OUT / (name + '-tests.log')).write_text('')
        for case in cases:
            output = run(name + '-tests', [binary, case], append=True)
            assert f'{marker} {case} ' in output, name + '/' + case
        results[mode][suite] = {'count': count, 'cases': cases}
    print(mode + ': review=11 original=26 prior-review=9 owner-facade=27', flush=True)

objects = []
for source in ['transport.c', 'platform_android.c']:
    obj = BUILD / (source + '.o')
    run('android-' + source, [ANDROID, *flags, '-O2', '-fPIC', '-fvisibility=hidden', '-c', TRANSPORT / source, '-o', obj])
    objects.append(obj)
link_flags = ['-shared', '-Wl,--no-undefined', '-Wl,-z,max-page-size=16384', '-Wl,-z,relro,-z,now', '-landroid']
missing = run('android-missing-all-hooks', [ANDROID, *objects, *link_flags, '-o', BUILD / 'missing.so'], expected=1)
for symbol in ['mxuit_drain', 'mxuit_complete', 'mxuit_progress']:
    assert symbol in missing
missing = run('android-missing-progress', [ANDROID, *flags, '-fPIC', '-DMXUIT_PROBE_OMIT_PROGRESS=1', *objects,
             TRANSPORT / 'tests/android_link_probe.c', *link_flags, '-o', BUILD / 'missing-progress.so'], expected=1)
assert 'mxuit_progress' in missing
library = BUILD / 'libreview-link.so'
run('android-link', [ANDROID, *flags, '-fPIC', '-fvisibility=hidden', *objects, TRANSPORT / 'tests/android_link_probe.c', *link_flags, '-o', library])
symbols = run('android-product-symbols', [BIN / 'llvm-nm', '-g', *objects])
assert 'mxuit_test_' not in symbols
run('android-elf', [BIN / 'llvm-readelf', '-h', '-l', '-d', '-W', library])
after = sources()
(OUT / 'source-after.sha256').write_text(''.join(f'{value}  {name}\n' for name, value in after.items()))
assert before == after, 'Selected source changed during review'
receipt = {
    'schema_version': 1,
    'reviewer': 'Independent Android facade transport review lane',
    'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_revision': revision, 'source_tree_digest': hashlib.sha256(manifest.encode()).hexdigest(),
    'source_manifest': str((OUT / 'source-before.sha256').relative_to(ROOT)),
    'selected_inputs_unchanged_during_checks': True,
    'owner_receipt_sha256': before['verification/android-facade-transport/receipt.json'],
    'owner_source_binding_verified': True, 'accepted_contract_sha256': acceptance['contract_sha256'],
    'tool_versions': versions,
    'tool_inputs_sha256': {str(p.resolve()): sha(p) for p in [CLANG, ANDROID.resolve(), NDK / 'source.properties', SYSROOT / 'SDKSettings.json', BIN / '../sysroot/usr/include/android/looper.h']},
    'environment': {key: ENV[key] for key in ['DEVELOPER_DIR', 'ASAN_OPTIONS', 'UBSAN_OPTIONS', 'TSAN_OPTIONS']},
    'explicit_host_sysroot': str(SYSROOT), 'commands': commands, 'results': results,
    'android_artifacts_sha256': {str(p.relative_to(ROOT)): sha(p) for p in objects + [library]},
    'preserved_test_hashes': owner_receipt['preserved_test_sources_sha256'],
    'findings': [],
    'limitations': ['Host ALooper model, no Android execution, display or Java main-Looper proof.',
                    'No JNI/Swift implementation or actual Swift Task.value/resource destructor qualification.',
                    'Progress observer cells are a native test model, not Swift continuation lost-wake proof.',
                    'Final C facade reclaim assumes separately validated Swift cleanup receipt.',
                    'ASan leak detection disabled; no RSS/energy/leak/performance claim.',
                    'Android API30 arm64 object/shared-link checks only; hooks in link probe are inert test-only.',
                    'Phones disconnected: no discovery, device runs or reconnect requests.',
                    'No publication, signing, customer or GA authority; Android signed UI remains unsupported.']}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('Independent review complete: 292 host case executions, Android API30 arm64 cross-link.', flush=True)
