#!/usr/bin/env python3
"""Build fresh ordinary Swift libraries and execute real C/C++ staging clients."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ANDROID_SWIFT = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
SDKS = Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks')
EXPORTS = ['mixer_android_prepare_v2', 'mixer_android_commit_v2', 'mixer_android_abort_v2']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.candidate):
        parser.error('candidate must be one bounded directory name')
    out = HERE / args.candidate
    out.mkdir(exist_ok=False)
    source = out / '.build/source'
    source.mkdir(parents=True)
    paths = set(subprocess.check_output(['git', 'ls-files', '-z', '--', 'sdk', 'native/android/engine'], cwd=ROOT).decode().strip('\0').split('\0'))
    paths.update(['AGENTS.md', 'native/android/bridge/mixer_android.h',
                  'native/android/bridge/mixer_android_v2.h', 'docs/android-engine-v2-c-bridge.md',
                  'verification/android-engine-v2-c-bridge/client.c',
                  'verification/android-engine-v2-c-bridge/header.cpp',
                  'verification/android-engine-v2-c-bridge/verify.py'])
    manifest = {}
    for name in sorted(paths):
        src, dst = ROOT / name, source / name
        assert src.is_file() and not src.is_symlink(), name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        manifest[name] = sha(dst)
    (out / 'source-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    with tarfile.open(out / 'source.tar.gz', 'w:gz') as archive:
        for name in sorted(paths):
            archive.add(source / name, arcname=name, recursive=False)
    receipt = {'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'status': 'running', 'commands': [], 'artifacts': {},
               'sourceManifestSHA256': sha(out / 'source-manifest.json'),
               'sourceArchiveSHA256': sha(out / 'source.tar.gz'),
               'scope': 'Actual C/C++ calls into fresh host Debug/Release Swift libraries; official Android arm64 API28 compilation and symbol inspection. No JNI/native screen/emulator execution or generated-app opt-in.',
               'pending': ['JNI allocation failure and token ownership', 'native coordinator integration',
                           'generated application staging exports', 'dynamic counter exhaustion', 'final hardware qualification']}

    def run(label, argv, env=None):
        argv = [str(x) for x in argv]
        log = out / (label + '.log')
        started = time.monotonic()
        with log.open('wb') as stream:
            result = subprocess.run(argv, cwd=source, env=dict(os.environ, **(env or {})),
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=900)
        receipt['commands'].append({'label': label, 'argv': argv, 'cwd': str(source),
                                    'environment': env or {}, 'exitCode': result.returncode,
                                    'seconds': time.monotonic() - started,
                                    'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
        print(label, result.returncode, flush=True)
        if result.returncode:
            for line in log.read_text(errors='replace').splitlines()[-15:]:
                print(line[:400], flush=True)
            raise RuntimeError(label)
        return log

    def retain(src, name):
        dst = out / 'artifacts' / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        receipt['artifacts'][str(dst.relative_to(ROOT))] = sha(dst)
        return dst

    try:
        run('swift-version', ['swift', '--version'])
        run('clang-version', ['clang', '--version'])
        run('xcode-version', ['xcodebuild', '-version'])
        run('python-version', ['python3', '--version'])
        for mode in ['debug', 'release']:
            scratch = out / '.build' / mode
            run(mode + '-build', ['swift', 'build', '--package-path', 'native/android/engine',
                                 '--scratch-path', scratch, '--product', 'MixerAndroidEngine', '-c', mode,
                                 '-Xswiftc', '-warnings-as-errors'])
            libdir = scratch / mode
            library = retain(libdir / 'libMixerAndroidEngine.dylib', mode + '/libMixerAndroidEngine.dylib')
            symbols = run(mode + '-symbols', ['nm', '-gU', library]).read_text()
            for name in EXPORTS:
                assert re.search(r'\bT _' + name + r'$', symbols, re.M), name
            common = ['-Wall', '-Wextra', '-Werror', '-pedantic', '-I', source / 'native/android/bridge',
                      '-L', library.parent, '-lMixerAndroidEngine', '-Wl,-rpath,' + str(library.parent)]
            client = library.parent / 'client'
            run(mode + '-c-compile', ['clang', '-std=c11', *common,
                                     source / 'verification/android-engine-v2-c-bridge/client.c', '-o', client])
            receipt['artifacts'][str(client.relative_to(ROOT))] = sha(client)
            text = run(mode + '-c-run', [client]).read_text()
            count = re.fullmatch(r'PASS ([0-9]+) C ABI assertions\n', text)
            assert count and int(count.group(1)) >= 70
            receipt[mode + 'CAssertions'] = int(count.group(1))
            cpp = library.parent / 'header-client'
            run(mode + '-cpp-compile', ['clang++', '-std=c++17', *common,
                                       source / 'verification/android-engine-v2-c-bridge/header.cpp', '-o', cpp])
            receipt['artifacts'][str(cpp.relative_to(ROOT))] = sha(cpp)
            run(mode + '-cpp-run', [cpp])
        android_env = {'DEVELOPER_DIR': '/Applications/Xcode_26.6.app/Contents/Developer'}
        run('android-swift-version', [ANDROID_SWIFT, '--version'], android_env)
        scratch = out / '.build/android'
        run('android-link', [ANDROID_SWIFT, 'build', '--package-path', 'native/android/engine',
                             '--scratch-path', scratch, '--swift-sdks-path', SDKS,
                             '--swift-sdk', 'aarch64-unknown-linux-android28', '--product', 'MixerAndroidEngine',
                             '-c', 'release', '-Xswiftc', '-warnings-as-errors'], android_env)
        library = retain(scratch / 'aarch64-unknown-linux-android28/release/libMixerAndroidEngine.so', 'android/libMixerAndroidEngine.so')
        nm = SDKS / 'swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-nm'
        run('android-nm-version', [nm, '--version'])
        symbols = run('android-symbols', [nm, '--defined-only', '--dynamic', library]).read_text()
        for name in EXPORTS:
            assert re.search(r'\bT ' + name + r'$', symbols, re.M), name
        receipt['unchangedLiveInputs'] = all(sha(ROOT / name) == value for name, value in manifest.items())
        assert receipt['unchangedLiveInputs']
        receipt['status'] = 'passed'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['failure'] = repr(error)
        raise
    finally:
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
