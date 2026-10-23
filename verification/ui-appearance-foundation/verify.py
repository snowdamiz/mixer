#!/usr/bin/env python3
"""Frozen-source appearance data qualification. Never discover or run a device."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OFFICIAL = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc')
ANDROID = Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android')
DEFAULT_SHA = 'e94f6988744bde16b83001db8e5047aeac4f15f6b045f99a4660445e7e2062d2'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    label = sys.argv[1] if len(sys.argv) == 2 else 'candidate-1'
    if '/' in label or label in ('.', '..'):
        raise ValueError('single output directory label required')
    out = HERE / label
    out.mkdir(exist_ok=False)
    archive = out / 'inputs'
    files = {ROOT / p for p in ['AGENTS.md', 'mixer-product-plan.md', 'docs/ui-shared-appearance-contract.md',
        'sdk/Package.swift', 'verification/ui-shared-appearance-root-review/acceptance.json',
        'verification/ui-shared-appearance-contract/v2/foundation-seam.md',
        'verification/ui-shared-appearance-contract/v2/AppearanceV1Declarations.swift',
        'verification/ui-shared-appearance-contract/v2/descriptor-schema.json',
        'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json',
        'verification/ui-shared-appearance-contract/v2/validate_descriptor.py',
        'verification/ui-shared-appearance-contract/v2/test_descriptor.py']}
    files.update(p for folder in ['sdk/Sources', 'sdk/Tests'] for p in (ROOT / folder).rglob('*') if p.is_file())
    files.update([HERE / name for name in ['verify.py', 'build-corpus.py', 'design-corpus.json', 'scope.md']])
    sources = {}
    for path in sorted(files):
        relative = path.relative_to(ROOT)
        data = path.read_bytes()
        sources[str(relative)] = sha(data)
        target = archive / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    digest = sha(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode())
    (out / 'input-lock.json').write_text(json.dumps({'files': sources, 'tree_sha256': digest}, indent=2) + '\n')
    receipt = dict(status='running', source_tree_sha256=digest, source_file_count=len(sources),
        head_at_start=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), commands=[], artifacts={},
        scope='Pure appearance data values, canonical codec, exact embedded default and checked integer math. Frozen complete SDK Debug/Release host tests and iOS/official Android module compilation. No native renderer, widget consumption, resource capture, installed/signed authority, runtime, device, parity, dogfood, publication or GA qualification.',
        limitation='The sealed Python design oracle checks font variants only when referenced. Documented invariant is enforced for every fontSFNT entry by Swift, with explicit raw-graph regression coverage. The oracle corpus is additional shape/canonical evidence, not the full Swift contract or native resource verification.')

    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(name, args, env=None, cwd=archive, timeout=600):
        argv = list(map(str, args))
        start = time.monotonic()
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        log = out / (name + '.log')
        log.write_bytes(result.stdout)
        receipt['commands'].append(dict(name=name, argv=argv, cwd=str(cwd), exit_code=result.returncode,
            elapsed_seconds=time.monotonic() - start, environment_overrides={'DEVELOPER_DIR': env['DEVELOPER_DIR']} if env else {},
            log=str(log.relative_to(ROOT)), log_sha256=sha(result.stdout)))
        save()
        print(f'{name}: {result.returncode}', flush=True)
        if result.returncode:
            receipt['status'] = 'failed: ' + name
            save()
            raise RuntimeError(receipt['status'])
        return result.stdout.decode(errors='replace').strip()

    apple = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
    android = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
    run('python-version', ['python3', '--version'])
    run('host-swift-version', ['swift', '--version'], apple)
    run('apple-xcode-version', ['xcodebuild', '-version'], apple)
    run('official-swift-version', [OFFICIAL, '--version'], android)
    run('android-xcode-version', ['xcodebuild', '-version'], android)
    ios_sdk = run('iphoneos-sdk', ['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], apple)
    design = archive / 'verification/ui-shared-appearance-contract/v2'
    for optimized in [False, True]:
        run('sealed-design-oracle-' + ('optimized' if optimized else 'normal'),
            ['python3'] + (['-O'] if optimized else []) + ['-m', 'unittest', 'discover', '-s', design, '-p', 'test_descriptor.py'])
    # Exact canonical bytes are independently checked against the accepted SHA;
    # actual SDK tests prove public mixerDefaultV1 emits this same fixture.
    fixture = design / 'mixer-default-appearance-v1.json'
    raw = fixture.read_bytes()
    if len(raw) != 1906 or sha(raw) != DEFAULT_SHA:
        raise RuntimeError('default fixture identity')
    receipt['accepted_default'] = dict(bytes=len(raw), sha256=sha(raw))
    for mode in ['debug', 'release']:
        run('sdk-' + mode, ['swift', 'test', '--package-path', 'sdk', '-c', mode, '-Xswiftc', '-warnings-as-errors'], apple)

    receipt['android_sdk_metadata'] = {str(p): sha(p.read_bytes()) for p in [ANDROID / 'swift-sdk.json', ANDROID / 'swift-toolset.json']}
    for platform, compiler, flags, env in [
        ('ios', 'swiftc', ['-target', 'arm64-apple-ios17.0', '-sdk', ios_sdk], apple),
        ('android', OFFICIAL, ['-target', 'aarch64-unknown-linux-android30', '-sdk', ANDROID / 'ndk-sysroot',
            '-resource-dir', ANDROID / 'swift-resources/usr/lib/swift-aarch64'], android),
    ]:
        folder = out / '.build' / platform
        folder.mkdir(parents=True)
        for module in ['MixerCore', 'MixerUI']:
            output = folder / (module + '.swiftmodule')
            inputs = sorted((archive / 'sdk/Sources' / module).glob('*.swift'))
            run(platform + '-' + module, [compiler, '-swift-version', '6', '-warnings-as-errors', '-parse-as-library',
                '-emit-module', '-module-name', module, '-emit-module-path', output, '-module-cache-path', folder / 'cache',
                '-I', folder] + flags + inputs, env)
            if not output.is_file():
                raise RuntimeError('module output: ' + module)
            receipt['artifacts'][str(output.relative_to(ROOT))] = dict(sha256=sha(output.read_bytes()), bytes=output.stat().st_size)
    for path, expected in sources.items():
        if sha((ROOT / path).read_bytes()) != expected or sha((archive / path).read_bytes()) != expected:
            receipt['status'] = 'failed: source changed during qualification'
            save()
            raise RuntimeError(path)
    receipt.update(status='passed', completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        unchanged_live_and_archive_source_checks=len(sources) * 2)
    save()
    print('PASS: ' + str(out / 'receipt.json'), flush=True)


if __name__ == '__main__':
    main()
