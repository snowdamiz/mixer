#!/usr/bin/env python3
"""Fresh-source ordinary Android registry transaction verification; no native UI."""
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
SWIFT = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
SDKS = Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}', args.candidate):
        parser.error('candidate must be one bounded directory name')
    out = HERE / args.candidate
    out.mkdir(exist_ok=False)
    source = out / '.build/source'
    source.mkdir(parents=True)
    # Other lanes' untracked Apple consumer files are not inputs to these targets.
    # Keep the complete tracked SDK/engine package closure plus this owned test.
    paths = set(subprocess.check_output(['git', 'ls-files', '-z', '--', 'sdk', 'native/android/engine'], cwd=ROOT).decode().strip('\0').split('\0'))
    paths.add('native/android/engine/Tests/MixerAndroidRuntimeTests/TransactionTests.swift')
    manifest = {}
    for name in sorted(paths):
        src = ROOT / name
        assert src.is_file() and not src.is_symlink(), name
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        manifest[name] = digest(target)
    (out / 'source-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    with tarfile.open(out / 'source.tar.gz', 'w:gz') as archive:
        for name in sorted(paths):
            archive.add(source / name, arcname=name, recursive=False)
    receipt = {
        'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'running', 'commands': [],
        'sourceManifestSHA256': digest(out / 'source-manifest.json'),
        'sourceArchiveSHA256': digest(out / 'source.tar.gz'),
        'scope': 'Actual production registry and engine tests on host Debug/Release/ThreadSanitizer; official Android cross-compilation. No JNI/Activity/native screen transaction or emulator execution.',
    }

    def run(label, argv, env=None):
        argv = [str(x) for x in argv]
        started = time.monotonic()
        environment = dict(os.environ, **(env or {}))
        with (out / (label + '.log')).open('wb') as log:
            process = subprocess.run(argv, cwd=source, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=600)
        log = out / (label + '.log')
        receipt['commands'].append({'label': label, 'argv': argv, 'cwd': str(source), 'environment': env or {},
                                    'exitCode': process.returncode, 'seconds': time.monotonic() - started,
                                    'log': str(log.relative_to(ROOT)), 'sha256': digest(log)})
        print(label, process.returncode, flush=True)
        if process.returncode:
            for line in log.read_text(errors='replace').splitlines():
                if 'error:' in line or 'failed' in line.lower(): print(line[:400], flush=True)
            raise RuntimeError(label)
        return log

    try:
        run('swift-version', ['swift', '--version'])
        run('xcode-version', ['xcodebuild', '-version'])
        run('python-version', ['python3', '--version'])
        for mode in ['debug', 'release']:
            run(mode, ['swift', 'test', '--package-path', 'native/android/engine', '--build-system', 'native',
                       '--scratch-path', out / '.build' / mode, '-c', mode, '-Xswiftc', '-warnings-as-errors'])
        log = run('tsan', ['swift', 'test', '--package-path', 'native/android/engine', '--build-system', 'native',
                          '--scratch-path', out / '.build/tsan', '--sanitize', 'thread', '-Xswiftc', '-warnings-as-errors'])
        assert 'WARNING: ThreadSanitizer' not in log.read_text()
        android_env = {'DEVELOPER_DIR': '/Applications/Xcode_26.6.app/Contents/Developer'}
        run('android-swift-version', [SWIFT, '--version'], android_env)
        run('android-link', [SWIFT, 'build', '--package-path', 'native/android/engine',
                            '--scratch-path', out / '.build/android', '--swift-sdks-path', SDKS,
                            '--swift-sdk', 'aarch64-unknown-linux-android28', '-c', 'release', '-Xswiftc', '-warnings-as-errors'], android_env)
        binary = out / '.build/android/aarch64-unknown-linux-android28/release/libMixerAndroidEngine.so'
        receipt['androidBinarySHA256'] = digest(binary)
        receipt['status'] = 'passed'
        receipt['unchangedLiveInputs'] = all(digest(ROOT / name) == value for name, value in manifest.items())
        assert receipt['unchangedLiveInputs']
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['failure'] = str(error)
        raise
    finally:
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
