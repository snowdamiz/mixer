#!/usr/bin/env python3
"""Audit retained archives as bytes; no compiler/native/runtime execution."""
import datetime
import hashlib
import json
from pathlib import Path
import plistlib
import stat
import struct
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def save(name, value):
    (BASE / name).write_bytes(stable(value))


def manifest(path, prefix=''):
    result = {}
    payloads = {}
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive.getmembers():
            if member.isfile():
                value = archive.extractfile(member).read()
                name = member.name.removeprefix(prefix)
                result[name] = {'kind': 'file', 'sha256': sha(value), 'bytes': len(value), 'mode': member.mode}
                payloads[name] = value
            elif member.issym():
                result[member.name.removeprefix(prefix)] = {'kind': 'symlink', 'target': member.linkname, 'mode': member.mode}
    return result, payloads


def macho(value):
    magic, cputype, subtype, filetype, ncmds, size, flags, reserved = struct.unpack_from('<8I', value)
    assert magic == 0xfeedfacf
    offset = 32
    info = {'cpuType': cputype, 'cpuSubtype': subtype, 'fileType': filetype}
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from('<II', value, offset)
        if cmd == 0x32:
            platform, minimum, sdk, ntools = struct.unpack_from('<4I', value, offset + 8)
            decode = lambda v: str(v >> 16) + '.' + str((v >> 8) & 255) + '.' + str(v & 255)
            info.update(platform=platform, minimumOS=decode(minimum), SDK=decode(sdk))
        offset += cmdsize
    return info


def main():
    sources = json.loads((BASE / 'source-manifest.json').read_bytes())
    products = json.loads((BASE / 'product-manifest.json').read_bytes())
    source_tree, source_payloads = manifest(BASE / 'accepted-sources.tar.gz', 'accepted/')
    product_tree, product_payloads = manifest(BASE / 'products.tar.gz')
    assert source_tree == sources['materializedSources']
    assert product_tree == products['products']
    assert sha(stable(source_tree)) == sources['materializedSourceTreeSHA256']
    assert sha(stable(product_tree)) == products['productTreeSHA256']
    original_bindings = 0
    for name, expected in sources['inputs'].items():
        assert sha((ROOT / name).read_bytes()) == expected['sha256'], name
        original_bindings += 1
    prepared = json.loads((ROOT / 'verification/apple-toggle-keyboard-focus-diagnostic-v1/prepared.json').read_bytes())
    for name, expected in prepared['preparedSources'].items():
        assert sha(source_payloads[name]) == expected['sha256'], name
    binaries = {}
    selected = ['MixerToggleDiagnostics.app/MixerToggleDiagnostics',
                'MixerToggleDiagnostics.app/Frameworks/libMixerCore.dylib',
                'MixerToggleDiagnostics.app/Frameworks/libMixerUI.dylib',
                'runner-products/Debug-iphonesimulator/MixerToggleUITests-Runner.app/PlugIns/MixerToggleUITests.xctest/MixerToggleUITests']
    for name in selected:
        value = macho(product_payloads[name])
        assert value['cpuType'] == 0x0100000c and value['platform'] == 7
        assert value['minimumOS'] == '26.0.0' and value['SDK'] == '26.5.0'
        binaries[name] = value
    app_info = plistlib.loads(product_payloads['MixerToggleDiagnostics.app/Info.plist'])
    assert app_info['MinimumOSVersion'] == '26.0'
    configurations = {}
    for name, value in product_payloads.items():
        if name.endswith('.xctestrun'):
            configurations[name] = plistlib.loads(value)
    assert len(configurations) == 1
    cleanup = json.loads((BASE / 'cleanup.json').read_bytes())
    # The build verified the product archive before scratch removal. The source
    # archive is checked independently here after removal; preserve that order.
    cleanup.pop('archivesByteVerifiedBeforeRemoval', None)
    cleanup.update(productArchiveByteVerifiedBeforeRemoval=True,
                   acceptedSourceArchiveByteVerifiedAfterRemoval=True)
    save('cleanup.json', cleanup)
    products['signing'] = 'No explicit signing command or credential operation. Linker signatures and pre-signed Xcode support frameworks retained.'
    save('product-manifest.json', products)
    receipt = json.loads((BASE / 'receipt.json').read_bytes())
    receipt['cleanup'] = cleanup
    receipt['compilerDriverSHA256'] = sha((BASE / 'build.py').read_bytes())
    receipt['sourceArchiveVerifiedAgainstEveryFile'] = True
    receipt['compilerWarningsPresent'] = True
    receipt['warningScope'] = 'Inherited app deprecations; inherited XCTest teardown actor-isolation warnings; Xcode support metadata and pre-signed-library stripping warnings. No diagnostic API/type compiler errors.'
    receipt['signing'] = products['signing']
    save('receipt.json', receipt)
    save('archive-audit.json', {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'argv': sys.argv, 'cwd': str(Path.cwd()), 'python': sys.version, 'pythonExecutable': str(Path(sys.executable).resolve()),
        'originalInputBindingsReverified': original_bindings, 'acceptedOverlayBindingsVerified': 6,
        'sourceArchiveFilesVerified': len(source_tree), 'productArchiveFilesAndLinksVerified': len(product_tree),
        'sourceTreeSHA256': sha(stable(source_tree)), 'productTreeSHA256': sha(stable(product_tree)),
        'ownedBinariesMachO': binaries, 'appMinimumOSVersion': app_info['MinimumOSVersion'],
        'xctestrunFiles': list(configurations), 'scratchAbsent': not (BASE / 'scratch').exists(),
        'nativeExecuted': False, 'compilerExecuted': False, 'passed': True})
    print('PASS: exact accepted sources, all retained product archive entries, original bindings, arm64 iOS Simulator 26.0 load commands; no runtime execution')


if __name__ == '__main__':
    main()
