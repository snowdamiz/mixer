#!/usr/bin/env python3
"""Facade/lease progress slice plus preserved transport regressions; no devices."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / 'verification/android-facade-transport'
BUILD = OUT / 'build'
BUILD.mkdir(parents=True, exist_ok=True)
XCODE = Path('/Applications/Xcode_26.6.app/Contents/Developer')
CLANG = XCODE / 'Toolchains/XcodeDefault.xctoolchain/usr/bin/clang'
SYSROOT = XCODE / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'
NDK = Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d')
NDKBIN = NDK / 'toolchains/llvm/prebuilt/darwin-x86_64/bin'
ANDROID_CLANG = NDKBIN / 'aarch64-linux-android30-clang'
NDK_INCLUDE = NDKBIN / '../sysroot/usr/include'
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
    sources += [ROOT / 'AGENTS.md', ROOT / 'docs/android-guest-ui-transport-design.md',
                ROOT / 'docs/android-signed-ui-binding-contract.md',
                ROOT / 'verification/android-binding-contract-acceptance.json',
                ROOT / 'verification/android-transport-review/probes.c']
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sources}


before = source_manifest()
acceptance = json.loads((ROOT / 'verification/android-binding-contract-acceptance.json').read_text())
contract = ROOT / acceptance['contract']
if hashlib.sha256(contract.read_bytes()).hexdigest() != acceptance['contract_sha256']:
    raise RuntimeError('accepted contract source does not match root receipt')
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
original = HERE / 'tests/host_tests.c'
independent = ROOT / 'verification/android-transport-review/probes.c'
# Freeze both existing test bodies; supplying the new required fixed hook in a
# separate link input does not rewrite or weaken their assertions.
preserved_tests = {}
for path, manifest in [(original, ROOT / 'verification/android-guest-ui-transport/source-manifest.sha256'),
                       (independent, ROOT / 'verification/android-transport-review/source-before.sha256')]:
    expected = {line.split('  ', 1)[1]: line.split('  ', 1)[0]
                for line in manifest.read_text().splitlines()}
    key = str(path.relative_to(ROOT))
    if before[key] != expected[key]:
        raise RuntimeError('preserved regression source changed: ' + key)
    preserved_tests[key] = before[key]
for mode, options in modes.items():
    host[mode] = {}
    suites = {
        'original': ([original, HERE / 'tests/progress_probe.c'], 'MXUIT_CASE_PASS', 26),
        'independent': ([HERE / 'platform_android.c', independent, HERE / 'tests/progress_probe.c'],
                        'ANDROID_TRANSPORT_REVIEW_PASS', 9),
        'facade': ([HERE / 'platform_android.c', HERE / 'tests/facade_tests.c'], 'MXUIT_FACADE_PASS', 27),
    }
    for suite, (sources, marker, count) in suites.items():
        name = mode + '-' + suite
        binary = BUILD / name
        run(name + '-build', [CLANG, '-isysroot', SYSROOT, '-idirafter', NDK_INCLUDE,
            *warnings, '-pthread', '-DMIXER_UI_TRANSPORT_TESTING=1', *options,
            HERE / 'transport.c', *sources, '-o', binary])
        cases = run(name + '-cases', [binary, '--list']).splitlines()
        if len(cases) != count:
            raise RuntimeError('unexpected suite size: ' + name)
        (OUT / (name + '-tests.log')).write_bytes(b'')
        for case in cases:
            output = run(name + '-tests', [binary, case], append=True, timeout=15)
            if f'{marker} {case} checks=' not in output:
                raise RuntimeError('missing explicit pass marker: ' + name + '/' + case)
        host[mode][suite] = {'cases_passed': len(cases), 'cases': cases,
                            'output': str((OUT / (name + '-tests.log')).relative_to(ROOT))}

objects = []
for source in ['transport.c', 'platform_android.c']:
    target = BUILD / (source.removesuffix('.c') + '-android.o')
    run('android-' + source.removesuffix('.c') + '-object', [ANDROID_CLANG, *warnings,
        '-O2', '-fPIC', '-fvisibility=hidden', '-c', HERE / source, '-o', target])
    objects.append(target)
symbols = run('android-product-symbols', [NDKBIN / 'llvm-nm', '-g', *objects])
if 'mxuit_test_' in symbols:
    raise RuntimeError('test controls appeared in product objects')
for symbol in ['mxuit_drain', 'mxuit_complete', 'mxuit_progress', 'mxuit_facade_acquire',
               'mxuit_acquire_for_facade', 'mxuit_facade_begin_close', 'mxuit_ui_enter',
               'mxuit_ui_leave', 'mxuit_ui_validate', 'mxuit_facade_try_reclaim',
               'ALooper_addFd', 'ALooper_acquire', 'ALooper_forThread']:
    if symbol not in symbols:
        raise RuntimeError('missing expected link seam: ' + symbol)
link_flags = ['-shared', '-Wl,--no-undefined', '-Wl,-z,max-page-size=16384',
              '-Wl,-z,relro,-z,now', '-landroid']
negative = run('android-required-hooks-negative', [ANDROID_CLANG, *objects,
    *link_flags, '-o', BUILD / 'missing-hooks.so'], success=False)
if any(symbol not in negative for symbol in ['mxuit_drain', 'mxuit_complete', 'mxuit_progress']):
    raise RuntimeError('negative link did not reject all three missing fixed hooks')
negative_progress = run('android-required-progress-negative', [ANDROID_CLANG, *warnings,
    '-fPIC', '-DMXUIT_PROBE_OMIT_PROGRESS=1', *objects, HERE / 'tests/android_link_probe.c',
    *link_flags, '-o', BUILD / 'missing-progress.so'], success=False)
if 'mxuit_progress' not in negative_progress:
    raise RuntimeError('negative link did not reject missing process progress hook')
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
    'executor': 'Android facade transport implementation lane',
    'reviewer': 'root independent review pending', 'source_revision': revision,
    'selected_inputs_unchanged_during_checks': True,
    'source_tree_digest': hashlib.sha256(manifest_text.encode()).hexdigest(),
    'source_manifest': str((OUT / 'source-manifest.sha256').relative_to(ROOT)),
    'tool_versions': versions, 'tool_input_sha256': tool_inputs,
    'environment': {'DEVELOPER_DIR': str(XCODE), 'explicit_host_sysroot': str(SYSROOT),
                    'ASAN_OPTIONS': ENV['ASAN_OPTIONS'], 'UBSAN_OPTIONS': ENV['UBSAN_OPTIONS'],
                    'TSAN_OPTIONS': ENV['TSAN_OPTIONS']},
    'commands': commands, 'host_results': host, 'android_artifact_sha256': outputs,
    'preserved_test_sources_sha256': preserved_tests,
    'accepted_contract_sha256': acceptance['contract_sha256'],
    'android_checks': ['API30 arm64 product C objects compiled with strict warnings',
                       'missing all fixed hooks and missing progress alone failed no-undefined link',
                       'test-only fixed-hook probe linked with libandroid',
                       'ELF/symbols recorded; test controls absent from product objects'],
    'resource_baseline': {'process_lifetime_pipe_fds': 2, 'process_lifetime_registration': 1,
                          'process_lifetime_acquired_looper_references': 1, 'owner_slots': 16,
                          'additional_scalar_facade_slots': 16, 'global_active_ui_leases': 1},
    'scope': 'C facade/endpoint/UI-entry/progress state machines and unchanged 26+9 regression cases on POSIX host plus Android object/shared-link checks only.',
    'limitations': ['Host driver simulates serialized callback return; no Android Looper execution.',
                    'consumer_joined is internal caller assertion; C does not prove actual Swift Task.value.',
                    'Android probe hooks are test-only inert link inputs, never an application host.',
                    'ASan leak detection disabled; no RSS/energy/lifetime performance qualification.',
                    'Direct JNI-entry and native-to-Java nesting probes simulate the scalar admission schedule; no JNI or Java code executes.',
                    'C facade reclaim assumes caller holds its separate exact final Swift cleanup receipt; it is not resource destruction proof.',
                    'No Swift/Java/activation/generator integration, signed selection, native UI, health or release authority; Android signed UI remains unsupported.',
                    'No emulator executed in this bounded slice; emulator execution remains permitted.',
                    'Physical phone queries/runs remain prohibited; no device tool called.'],
}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'source_revision': revision,
                  'source_tree_digest': receipt['source_tree_digest'],
                  'host_case_counts': {mode: {suite: value['cases_passed'] for suite, value in suites.items()}
                                       for mode, suites in host.items()},
                  'android': receipt['android_checks']}, indent=2))
