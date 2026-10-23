#!/usr/bin/env python3
"""Freeze and execute pure appearance data qualification; never access a device."""
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


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    label = sys.argv[1] if len(sys.argv) == 2 else 'candidate-1'
    if not label or '/' in label or label in ('.', '..'):
        raise ValueError('single output directory label required')
    out = HERE / label
    out.mkdir(exist_ok=False)
    archive = out / 'inputs'
    files = {ROOT / p for p in [
        'AGENTS.md', 'mixer-product-plan.md', 'sdk/Package.swift',
        'docs/ui-shared-appearance-contract.md', 'docs/ui-appearance-resolution-v1.md',
        'verification/ui-shared-appearance-contract/v2/foundation-seam.md',
        'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json',
        'verification/ui-appearance-foundation/design-corpus.json',
        'verification/ui-appearance-foundation/candidate-1/receipt.json',
        'verification/ui-appearance-foundation/candidate-1/input-lock.json',
        'verification/apple-appearance-reference/receipt.json',
        'verification/apple-appearance-reference/observations.md',
    ]}
    files.update(p for folder in ['sdk/Sources', 'sdk/Tests'] for p in (ROOT / folder).rglob('*') if p.is_file())
    files.update(HERE / p for p in ['verify.py', 'PublicConsumer.swift', 'NegativeConsumer.swift'])
    sources = {}
    for path in sorted(files):
        relative = path.relative_to(ROOT)
        data = path.read_bytes()
        sources[str(relative)] = sha(data)
        target = archive / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    digest = sha(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode())
    lock = dict(format='mixer.ui-appearance-resolution-inputs.1', files=sources, source_tree_sha256=digest)
    (out / 'input-lock.json').write_text(json.dumps(lock, indent=2) + '\n')
    receipt = dict(
        format='mixer.ui-appearance-resolution-evidence.1', status='running', started_at=utc(),
        head_at_start=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        head_tree_at_start=subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(),
        source_tree_sha256=digest, source_file_count=len(sources), commands=[], artifacts={},
        scope='Pure bounded sharedCandidate1 style data for ten current kinds. Complete frozen SDK Debug/Release host tests and host/iOS/official Android public module compilation. No native adapter capability or consumption, resource capture, installed/signed authority, numerical appearance/raster parity, device, publication or GA qualification.',
        provisional_recipe='Existing sealed default tokens unchanged. Apple reference section/navigation/toggle token approval pending.',
        resource_boundary='Descriptor metadata only. No actual file/digest/format/font identity/glyph/license/fallback coverage verification.',
        physical_devices=dict(discovered=False, used=False, reconnection_requested=False),
        pending=['independent root acceptance', 'native recipe support/admission and widget consumption',
            'actual resource capture and packaging', 'signed installation/display/input/health integration',
            'native text/layout/state/IME/accessibility measurement', 'Apple candidate token approval',
            'physical iOS/Android parity', 'immutable published FieldLog consumption',
            'signing/store/customer/operational/GA gates'])

    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(name, args, env=None, cwd=archive, expected_failure=False, timeout=600):
        argv = list(map(str, args))
        start = time.monotonic()
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        log = out / (name + '.log')
        log.write_bytes(result.stdout)
        receipt['commands'].append(dict(name=name, argv=argv, cwd=str(cwd), exit_code=result.returncode,
            expected_failure=expected_failure, elapsed_seconds=time.monotonic() - start,
            environment_overrides={'DEVELOPER_DIR': env['DEVELOPER_DIR']} if env else {},
            log=str(log.relative_to(ROOT)), log_sha256=sha(result.stdout)))
        save()
        print(f'{name}: {result.returncode}' + (' (expected failure)' if expected_failure else ''), flush=True)
        if (result.returncode == 0) == expected_failure:
            receipt.update(status='failed: ' + name, completed_at=utc())
            save()
            raise RuntimeError(receipt['status'])
        return result.stdout.decode(errors='replace').strip()

    save()
    apple = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
    android = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
    run('python-version', ['python3', '--version'])
    run('host-swift-version', ['swift', '--version'], apple)
    run('apple-xcode-version', ['xcodebuild', '-version'], apple)
    run('official-android-swift-version', [OFFICIAL, '--version'], android)
    run('android-xcode-version', ['xcodebuild', '-version'], android)
    ios_sdk = run('iphoneos-sdk', ['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], apple)
    for mode in ['debug', 'release']:
        run('sdk-' + mode, ['swift', 'test', '--package-path', 'sdk', '-c', mode, '-Xswiftc', '-warnings-as-errors'], apple)
    receipt['android_sdk_metadata'] = {str(p): sha(p.read_bytes()) for p in [ANDROID / 'swift-sdk.json', ANDROID / 'swift-toolset.json']}
    for platform, compiler, flags, env in [
        ('host', 'swiftc', [], apple),
        ('ios', 'swiftc', ['-target', 'arm64-apple-ios17.0', '-sdk', ios_sdk], apple),
        ('android', OFFICIAL, ['-target', 'aarch64-unknown-linux-android30', '-sdk', ANDROID / 'ndk-sysroot',
            '-resource-dir', ANDROID / 'swift-resources/usr/lib/swift-aarch64'], android),
    ]:
        folder = out / '.build' / platform
        folder.mkdir(parents=True)
        common = ['-swift-version', '6', '-warnings-as-errors', '-parse-as-library',
            '-module-cache-path', folder / 'cache', '-I', folder] + flags
        for module in ['MixerCore', 'MixerUI']:
            output = folder / (module + '.swiftmodule')
            inputs = sorted((archive / 'sdk/Sources' / module).glob('*.swift'))
            run(platform + '-' + module, [compiler] + common + ['-emit-module', '-module-name', module,
                '-emit-module-path', output] + inputs, env)
            if not output.is_file():
                raise RuntimeError('module output: ' + module)
            receipt['artifacts'][str(output.relative_to(ROOT))] = dict(sha256=sha(output.read_bytes()), bytes=output.stat().st_size)
        probes = archive / 'verification/ui-appearance-resolution'
        run(platform + '-public-consumer', [compiler] + common + ['-typecheck', probes / 'PublicConsumer.swift'], env)
        failure = run(platform + '-immutable-output-negative', [compiler] + common + ['-typecheck', probes / 'NegativeConsumer.swift'],
            env, expected_failure=True)
        if 'disabled' not in failure or 'let' not in failure:
            raise RuntimeError('negative probe failed for an unexpected reason')
    for path, expected in sources.items():
        if sha((ROOT / path).read_bytes()) != expected or sha((archive / path).read_bytes()) != expected:
            receipt.update(status='failed: source changed during qualification', completed_at=utc())
            save()
            raise RuntimeError(path)
    receipt.update(status='passed-pure-data-and-compilation-only', completed_at=utc(),
        unchanged_live_and_archive_source_checks=len(sources) * 2)
    save()
    print('PASS: ' + str(out / 'receipt.json'), flush=True)


if __name__ == '__main__':
    main()
