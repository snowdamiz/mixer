#!/usr/bin/env python3
"""Reproduce original independent host review; no device discovery or execution."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRANSPORT = ROOT / 'native/android/signed-guest-ui/transport'
BUILD = HERE / 'build'
BUILD.mkdir(exist_ok=True)
XCODE = Path('/Applications/Xcode_26.6.app/Contents/Developer')
CLANG = XCODE / 'Toolchains/XcodeDefault.xctoolchain/usr/bin/clang'
SYSROOT = XCODE / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'
NDK = Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d')
INCLUDE = NDK / 'toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/include'
ENV = os.environ.copy()
ENV['DEVELOPER_DIR'] = str(XCODE)
ENV.pop('SDKROOT', None)
ENV['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
ENV['UBSAN_OPTIONS'] = 'halt_on_error=1'
ENV['TSAN_OPTIONS'] = 'halt_on_error=1'
commands = []


def run(name, args, append=False, timeout=30):
    argv = [str(arg) for arg in args]
    result = subprocess.run(argv, cwd=ROOT, env=ENV, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    log = HERE / (name + '.log')
    with log.open('ab' if append else 'wb') as output:
        output.write(result.stdout)
    commands.append({'argv': argv, 'exit_code': result.returncode,
                     'output': str(log.relative_to(ROOT))})
    if result.returncode != 0:
        raise RuntimeError(name + ': ' + result.stdout.decode(errors='replace'))
    return result.stdout.decode(errors='replace').strip()


def manifest():
    selected = sorted(TRANSPORT.rglob('*.c')) + sorted(TRANSPORT.rglob('*.h'))
    selected += [TRANSPORT / 'verify.py', ROOT / 'AGENTS.md', ROOT / 'THIRD_PARTY.yml',
                 ROOT / 'docs/android-guest-ui-transport-design.md',
                 ROOT / 'verification/android-guest-ui-transport/receipt.json',
                 ROOT / 'verification/android-guest-ui-transport/source-manifest.sha256',
                 HERE / 'probes.c', Path(__file__).resolve()]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in selected}


before = manifest()
original_manifest = ROOT / 'verification/android-guest-ui-transport/source-manifest.sha256'
original_matches = {}
for line in original_manifest.read_text().splitlines():
    expected, path = line.split('  ', 1)
    original_matches[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
if not all(original_matches.values()):
    raise RuntimeError('implementation receipt no longer matches its selected source inputs')
(HERE / 'original-source-match.json').write_text(json.dumps(original_matches, indent=2) + '\n')
revision_before = run('source-revision-before', ['git', 'rev-parse', 'HEAD'])
run('source-status-before', ['git', 'status', '--short'])
versions = {'clang': run('clang-version', [CLANG, '--version']),
            'python': run('python-version', [sys.executable, '--version']),
            'ndk': (NDK / 'source.properties').read_text().strip()}
flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wpedantic', '-Wconversion',
         '-Wsign-conversion', '-Wstrict-prototypes', '-pthread', '-isysroot', SYSROOT,
         '-idirafter', INCLUDE]
results = {}
for mode, options in {
        'debug': ['-O0', '-g'], 'release': ['-O2', '-DNDEBUG'],
        'asan-ubsan': ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'],
        'tsan': ['-O1', '-g', '-fsanitize=thread', '-fno-omit-frame-pointer']}.items():
    binary = BUILD / ('probes-' + mode)
    run(mode + '-build', [CLANG, *flags, *options, TRANSPORT / 'transport.c',
                         TRANSPORT / 'platform_android.c', HERE / 'probes.c', '-o', binary])
    cases = run(mode + '-cases', [binary, '--list']).splitlines()
    (HERE / (mode + '-tests.log')).write_text('')
    for case in cases:
        output = run(mode + '-tests', [binary, case], append=True, timeout=15)
        if f'ANDROID_TRANSPORT_REVIEW_PASS {case} checks=' not in output:
            raise RuntimeError('missing explicit marker: ' + mode + '/' + case)
    results[mode] = {'cases_passed': len(cases), 'cases': cases,
                     'output': str((HERE / (mode + '-tests.log')).relative_to(ROOT))}
after = manifest()
revision_after = run('source-revision-after', ['git', 'rev-parse', 'HEAD'])
run('source-status-after', ['git', 'status', '--short'])
if before != after:
    raise RuntimeError('reviewed selected sources changed during execution')
manifest_text = ''.join(f'{digest}  {path}\n' for path, digest in before.items())
(HERE / 'source-before.sha256').write_text(manifest_text)
(HERE / 'source-after.sha256').write_text(manifest_text)
receipt = {
    'schema_version': 1,
    'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'executor': 'Independent Android transport review lane',
    'source_revision_before': revision_before, 'source_revision_after': revision_after,
    'selected_sources_unchanged': True,
    'implementation_receipt_selected_sources_match': original_matches,
    'source_tree_digest': hashlib.sha256(manifest_text.encode()).hexdigest(),
    'source_before_manifest': str((HERE / 'source-before.sha256').relative_to(ROOT)),
    'source_after_manifest': str((HERE / 'source-after.sha256').relative_to(ROOT)),
    'tool_versions': versions,
    'tool_inputs_sha256': {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in [CLANG, INCLUDE / 'android/looper.h', SYSROOT / 'SDKSettings.json']},
    'environment': {'DEVELOPER_DIR': str(XCODE), 'host_sysroot': str(SYSROOT),
                    'ASAN_OPTIONS': ENV['ASAN_OPTIONS'], 'UBSAN_OPTIONS': ENV['UBSAN_OPTIONS'],
                    'TSAN_OPTIONS': ENV['TSAN_OPTIONS']},
    'commands': commands, 'results': results,
    'review': 'review.md',
    'scope': 'Unchanged transport.c and platform_android.c on POSIX host using installed official android/looper.h and original test-only ALooper symbol implementations.',
    'limitations': [
        'No actual Android Looper, Java main-thread proof, JNI, Swift continuation or Task.value execution.',
        'Synthetic consumer_joined assertions establish only transport pinning behavior.',
        'No emulator or physical device discovery, queries, runs or reconnect request.',
        'No Android native mobile, signed runtime, widget, health, publication or GA gate qualification.',
        'ASan leak detection is disabled; no RSS, energy or leak qualification.'],
}
(HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'source_tree_digest': receipt['source_tree_digest'], 'results': results}, indent=2))
