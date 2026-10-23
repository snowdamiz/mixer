#!/usr/bin/env python3
"""Host state-machine tests and official Android object/link checks; no devices."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / 'verification/android-guest-ui-transport'
BUILD = OUT / 'build'
BUILD.mkdir(parents=True, exist_ok=True)
XCODE = Path('/Applications/Xcode_26.6.app/Contents/Developer')
CLANG = XCODE / 'Toolchains/XcodeDefault.xctoolchain/usr/bin/clang'
SYSROOT = XCODE / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'
NDK = Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d')
NDKBIN = NDK / 'toolchains/llvm/prebuilt/darwin-x86_64/bin'
ANDROID_CLANG = NDKBIN / 'aarch64-linux-android30-clang'
ENV = os.environ.copy()
ENV['DEVELOPER_DIR'] = str(XCODE)
ENV.pop('SDKROOT', None)
ENV['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
ENV['UBSAN_OPTIONS'] = 'halt_on_error=1'
ENV['TSAN_OPTIONS'] = 'halt_on_error=1'
commands = []
warnings = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wpedantic',
            '-Wconversion', '-Wsign-conversion', '-Wstrict-prototypes']


def run(name, command, *, success=True, append=False, timeout=30):
    argv = [str(value) for value in command]
    result = subprocess.run(argv, cwd=ROOT, env=ENV, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    log = OUT / (name + '.log')
    with log.open('ab' if append else 'wb') as target:
        target.write(result.stdout)
    commands.append({'argv': argv, 'exit_code': result.returncode,
                     'output': str(log.relative_to(ROOT)), 'expected_success': success})
    if (result.returncode == 0) != success:
        raise RuntimeError(f'{name}: unexpected exit {result.returncode}: '
                           + result.stdout.decode(errors='replace'))
    return result.stdout.decode(errors='replace')


def source_manifest():
    sources = sorted(path for path in HERE.rglob('*') if path.is_file()
                     and '__pycache__' not in path.parts)
    sources += [ROOT / 'AGENTS.md', ROOT / 'THIRD_PARTY.yml',
                ROOT / 'docs/android-guest-ui-transport-design.md']
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sources}


before = source_manifest()
revision = run('source-revision', ['git', 'rev-parse', 'HEAD']).strip()
run('source-status', ['git', 'status', '--short'])
versions = {
    'host_clang': run('version-host-clang', [CLANG, '--version']).strip(),
    'android_clang': run('version-android-clang', [ANDROID_CLANG, '--version']).strip(),
    'python': run('version-python', [sys.executable, '--version']).strip(),
    'ndk': (NDK / 'source.properties').read_text().strip(),
}
tool_inputs = {}
for path in [CLANG, ANDROID_CLANG.resolve(), NDK / 'source.properties',
             NDKBIN / '../sysroot/usr/include/android/looper.h', SYSROOT / 'SDKSettings.json']:
    tool_inputs[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()

modes = {'debug': ['-O0', '-g'], 'release': ['-O2', '-DNDEBUG'],
         'asan-ubsan': ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'],
         'tsan': ['-O1', '-g', '-fsanitize=thread', '-fno-omit-frame-pointer']}
host = {}
for mode, options in modes.items():
    binary = BUILD / ('host-' + mode)
    run(mode + '-build', [CLANG, '-isysroot', SYSROOT, *warnings, '-pthread',
        '-DMIXER_UI_TRANSPORT_TESTING=1', *options, HERE / 'transport.c',
        HERE / 'tests/host_tests.c', '-o', binary])
    cases = run(mode + '-cases', [binary, '--list']).splitlines()
    (OUT / (mode + '-tests.log')).write_bytes(b'')
    for case in cases:
        output = run(mode + '-tests', [binary, case], append=True, timeout=15)
        if f'MXUIT_CASE_PASS {case} checks=' not in output:
            raise RuntimeError('missing explicit pass marker: ' + mode + '/' + case)
    host[mode] = {'cases_passed': len(cases), 'cases': cases,
                  'output': str((OUT / (mode + '-tests.log')).relative_to(ROOT))}

objects = []
for source in ['transport.c', 'platform_android.c']:
    target = BUILD / (source.removesuffix('.c') + '-android.o')
    run('android-' + source.removesuffix('.c') + '-object', [ANDROID_CLANG, *warnings,
        '-O2', '-fPIC', '-fvisibility=hidden', '-c', HERE / source, '-o', target])
    objects.append(target)
symbols = run('android-product-symbols', [NDKBIN / 'llvm-nm', '-g', *objects])
if 'mxuit_test_' in symbols:
    raise RuntimeError('test controls appeared in product objects')
for symbol in ['mxuit_drain', 'mxuit_complete', 'ALooper_addFd', 'ALooper_acquire', 'ALooper_forThread']:
    if symbol not in symbols:
        raise RuntimeError('missing expected link seam: ' + symbol)
link_flags = ['-shared', '-Wl,--no-undefined', '-Wl,-z,max-page-size=16384',
              '-Wl,-z,relro,-z,now', '-landroid']
negative = run('android-required-hooks-negative', [ANDROID_CLANG, *objects,
    *link_flags, '-o', BUILD / 'missing-hooks.so'], success=False)
if 'mxuit_drain' not in negative or 'mxuit_complete' not in negative:
    raise RuntimeError('negative link did not reject both missing fixed hooks')
library = BUILD / 'libmxuit-link-probe.so'
run('android-probe-link', [ANDROID_CLANG, *warnings, '-fPIC', '-fvisibility=hidden',
    *objects, HERE / 'tests/android_link_probe.c', *link_flags, '-o', library])
dynamic = run('android-probe-dynamic', [NDKBIN / 'llvm-readelf', '-d', library])
if '[libandroid.so]' not in dynamic:
    raise RuntimeError('probe did not link documented Android Looper library')
run('android-probe-elf', [NDKBIN / 'llvm-readelf', '-h', '-l', '-W', library])
run('android-probe-symbols', [NDKBIN / 'llvm-nm', '-g', library])
after = source_manifest()
if before != after:
    raise RuntimeError('selected inputs changed during run')
manifest_text = ''.join(f'{digest}  {name}\n' for name, digest in before.items())
(OUT / 'source-manifest.sha256').write_text(manifest_text)
outputs = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
           for path in objects + [library]}
receipt = {
    'schema_version': 1, 'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'executor': 'Android guest UI transport implementation lane',
    'reviewer': 'root independent review pending', 'source_revision': revision,
    'selected_inputs_unchanged_during_checks': True,
    'source_tree_digest': hashlib.sha256(manifest_text.encode()).hexdigest(),
    'source_manifest': str((OUT / 'source-manifest.sha256').relative_to(ROOT)),
    'tool_versions': versions, 'tool_input_sha256': tool_inputs,
    'environment': {'DEVELOPER_DIR': str(XCODE), 'explicit_host_sysroot': str(SYSROOT),
                    'ASAN_OPTIONS': ENV['ASAN_OPTIONS'], 'UBSAN_OPTIONS': ENV['UBSAN_OPTIONS'],
                    'TSAN_OPTIONS': ENV['TSAN_OPTIONS']},
    'commands': commands, 'host_results': host, 'android_artifact_sha256': outputs,
    'android_checks': ['API30 arm64 product C objects compiled with strict warnings',
                       'missing fixed hooks failed no-undefined link',
                       'test-only fixed-hook probe linked with libandroid',
                       'ELF/symbols recorded; test controls absent from product objects'],
    'resource_baseline': {'process_lifetime_pipe_fds': 2, 'process_lifetime_registration': 1,
                          'process_lifetime_acquired_looper_references': 1, 'owner_slots': 16},
    'scope': 'Original C transport state machine on POSIX host plus Android object/shared-link checks only.',
    'limitations': ['Host driver simulates serialized callback return; no Android Looper execution.',
                    'consumer_joined is internal caller assertion; C does not prove actual Swift Task.value.',
                    'Android probe hooks are test-only inert link inputs, never an application host.',
                    'ASan leak detection disabled; no RSS/energy/lifetime performance qualification.',
                    'No Swift/Java/activation/generator integration, signed selection, native UI, health or release authority.',
                    'No emulator executed in this bounded slice; emulator execution remains permitted.',
                    'Physical phone queries/runs remain prohibited; no device tool called.'],
}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'source_revision': revision,
                  'source_tree_digest': receipt['source_tree_digest'],
                  'host_case_counts': {key: value['cases_passed'] for key, value in host.items()},
                  'android': receipt['android_checks']}, indent=2))
