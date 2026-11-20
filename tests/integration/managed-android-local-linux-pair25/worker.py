#!/usr/bin/env python3
"""Run the rendered Pair25 driver with the Linux toolchain in a private worker."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from zipfile import ZipFile

SWIFT_IMAGE = 'sha256:3ad77b443f5f41d8c6c693659d9c951538dfeb79403e67cd40abca2501d4f191'
PROJECT = Path('/project')
DELIVERY = Path('/deliver')
RETAINED = Path('/work/retained')
LOCK = PROJECT / 'mixer.lock'
PIN = 'Platforms/Android/Package.resolved'
APP = 'com.example.upgradestarter'
ABI = 'arm64-v8a'
MIB = 1024 * 1024


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def configured_driver():
    require(platform.system() == 'Linux' and platform.machine() == 'aarch64',
            'Expected native Linux arm64 Swift worker')
    manifest = os.environ.get('PAIR25_VERIFIED_SWIFT_MANIFEST')
    require(manifest == SWIFT_IMAGE, 'Launch through replay.sh to verify the Swift image')
    os.environ.update({
        'ANDROID_HOME': '/android-sdk',
        'MIXER_JDK': '/toolchain/jdk',
        'MIXER_SWIFT': '/usr/bin/swift',
        'MIXER_SWIFT_SDKS_PATH': '/toolchain/sdk',
    })
    spec = importlib.util.spec_from_file_location(
        'pair25_android', PROJECT / 'Generated/MixerAndroid/android-build.py')
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    driver.NDK = driver.ART / 'android-ndk-r27d/toolchains/llvm/prebuilt/linux-x86_64'

    # The standalone driver hashes a relocatable Xcode toolchain directory.
    # replay.sh verifies the image manifest and config before starting this worker.
    # Keep normal on-disk inspection for every other tool/distribution.
    tree = driver.tree

    def distribution_tree(path, digest_file=None):
        return manifest.removeprefix('sha256:') if path == Path('/') else tree(path, digest_file)

    driver.tree = distribution_tree
    return driver


def readback(driver, apk, report):
    expected_identity = {
        'application': APP, 'activity': APP + '.androidhost.PublicActivity',
        'abi': ABI, 'minAPI': 36, 'targetAPI': 37,
    }
    require(report['apk_identity'] == expected_identity, 'Unexpected APK identity')
    if driver.resolved_lock(PROJECT, PIN)[0] != driver.resolved_lock(
            PROJECT, 'Generated/MixerSDK/Package.resolved')[0]:
        raise RuntimeError('Starter dependency lock differs from pinned SDK bytes')

    with ZipFile(apk) as archive:
        names = archive.namelist()
        require(len(set(names)) == len(names) and archive.testzip() is None,
                'APK has duplicate entries or a ZIP CRC failure')
        require(archive.read('classes.dex').startswith(b'dex\n'), 'DEX missing')
        native = sorted(n for n in names if n.startswith('lib/') and n.endswith('.so'))
        require(native and all(n.startswith('lib/' + ABI + '/') for n in native),
                'Unexpected native ABI set')
        require({'libAppAndroid.so', 'libmixer_public_android_jni.so'} <=
                {Path(n).name for n in native}, 'Swift or JNI payload missing')
        notices = {n: hashlib.sha256(archive.read(n)).hexdigest()
                   for n in names if n.startswith('third-party-notices/')}
        require({'third-party-notices/Swift-SDK-LICENSE.txt',
                 'third-party-notices/Apple-ICU-76.1-LICENSE.txt'} <= notices.keys(),
                'Required runtime licenses missing')
        require(archive.read('third-party-notices/Swift-SDK-LICENSE.txt') ==
                (driver.ART / 'swift-resources/usr/share/swift/LICENSE.txt').read_bytes(),
                'Swift SDK license bytes differ')
        require(archive.read('third-party-notices/Apple-ICU-76.1-LICENSE.txt') ==
                driver.APPLE_ICU_LICENSE.encode(), 'Foundation ICU notice bytes differ')

        # Check ELF bytes extracted from the APK itself, including its app and JNI load segments.
        elf_alignment = {}
        extracted = Path('/tmp/apk-readback.so')
        for entry in native:
            extracted.write_bytes(archive.read(entry))
            name = Path(entry).name
            require(driver.digest(extracted) == report['native_libraries'][name],
                    f'APK native bytes differ from build staging: {name}')
            elf = subprocess.check_output(
                [driver.NDK / 'bin/llvm-readelf', '-h', '-lW', extracted], text=True)
            require('ELF64' in elf and 'AArch64' in elf, f'Invalid Android ELF: {name}')
            elf_alignment[name] = [int(line.split()[-1], 16) for line in elf.splitlines()
                                   if line.strip().startswith('LOAD ')]
            require(elf_alignment[name], f'Missing load segments: {name}')
        require(all(min(elf_alignment[name]) >= 16384 for name in
                    ('libAppAndroid.so', 'libmixer_public_android_jni.so')),
                'App or JNI ELF load segments lack 16 KiB alignment')
        extracted.unlink()
        with apk.open('rb') as stream:
            stream.seek(archive.start_dir - 16)
            require(stream.read(16) != b'APK Sig Block 42' and
                    all(not n.startswith('META-INF/') for n in names), 'Unexpected APK signature')

    return {'zipEntries': len(names), 'zipCRCVerified': True, 'unsigned': True,
            'noticeSHA256': notices, 'elfLoadAlignmentBytes': elf_alignment}


def retain_products(driver, apk, report):
    symbols = RETAINED / 'debug-symbols.zip'
    sources = [
        ('unsigned_native_binary', apk, report['apk_bytes'], report['apk_sha256'], 32 * MIB),
        ('debug_symbols', symbols, report['symbols_bytes'], report['symbols_sha256'], 16 * MIB),
    ]
    artifacts = []
    for kind, source, size, digest, limit in sources:
        require(0 < size <= limit and source.stat().st_size == size and driver.digest(source) == digest,
                f'Retained {kind} size or digest differs')
        artifacts.append({'kind': kind, 'file': source.name, 'sizeBytes': size, 'sha256': digest})

    debug = report['debug_products']
    require({row['library'] for row in debug} ==
            {f'lib/{ABI}/libAppAndroid.so', f'lib/{ABI}/libmixer_public_android_jni.so'} and len(debug) == 2,
            'Unexpected debug libraries')
    with ZipFile(symbols) as archive:
        require(archive.namelist() == [row['debugPath'] for row in debug],
                'Debug archive membership differs from the driver receipt')
        for row in debug:
            entry = archive.getinfo(row['debugPath'])
            require(0 < entry.file_size == row['sizeBytes'], 'Debug data size differs')
            with archive.open(entry) as content:
                require(hashlib.file_digest(content, 'sha256').hexdigest() == row['sha256'],
                        'Debug data digest differs')

    inventory = DELIVERY / 'resource-inventory.json'
    inventory.write_text(json.dumps({
        'formatVersion': 1,
        'apkSHA256': report['apk_sha256'],
        'debugSymbolsSHA256': report['symbols_sha256'],
        **report['apk_identity'],
        'androidHost': report['android_host'],
        'entries': report['apk_entries'],
        'nativeDependencies': report['native_dependencies'],
        'debugProducts': debug,
    }, indent=2, sort_keys=True) + '\n')
    size = inventory.stat().st_size
    require(0 < size <= 16 * MIB, 'Resource inventory exceeds the retained limit')
    artifacts.append({'kind': 'resource_inventory', 'file': inventory.name,
                      'sizeBytes': size, 'sha256': driver.digest(inventory)})

    for _, source, size, digest, _ in sources:
        destination = DELIVERY / source.name
        shutil.copyfile(source, destination)
        require(destination.stat().st_size == size and driver.digest(destination) == digest,
                f'Copied {source.name} differs from the produced artifact')
    return artifacts


def main():
    driver = configured_driver()
    if sys.argv[1:] == ['lock']:
        # The host mounts this Linux projection over only mixer.lock for the
        # isolated build. The original export and its Mac toolchain lock stay intact.
        lock = driver.read_json(LOCK)
        lock['android']['toolchain'] = driver.inspect()
        (DELIVERY / 'linux-mixer.lock').write_text(json.dumps(lock, indent=2) + '\n')
        return
    require(sys.argv[1:] == ['build'], 'Usage: worker.py lock | build')
    driver.build(PROJECT, retained_output=RETAINED)
    report = driver.read_json(RETAINED / 'build-receipt.json')
    apk = RETAINED / 'UpgradeStarter-unsigned.apk'
    facts = readback(driver, apk, report)
    facts['build'] = {key: report[key] for key in (
        'apk_bytes', 'apk_sha256', 'apk_content_sha256', 'apk_identity',
        'platform_dependency_lock', 'source_tree_sha256', 'source_tree_after_sha256',
        'sdk_digest', 'adapter_digest', 'source_profile', 'appearance_descriptor',
        'native_dependencies', 'native_libraries', 'debug_products')}
    facts['commands'] = [
        {'argvStart': command['command'][:2], 'argCount': len(command['command']),
         'exitCode': command['exit_code']}
        for command in report['commands']
    ]
    facts['artifacts'] = retain_products(driver, apk, report)
    (DELIVERY / 'readback.json').write_text(json.dumps(facts, indent=2) + '\n')


if __name__ == '__main__':
    main()
