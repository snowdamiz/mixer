"""Inspect retained and ordinary APKs from disposable local builds of the same Starter."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(tool, *arguments, expected=0):
    result = subprocess.run([tool, *arguments], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
    require(result.returncode == expected, f'{tool.name} returned {result.returncode}: {result.stdout[-3000:]}')
    return result.stdout


def entries(archive):
    require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate APK entry')
    return [{'path': path, 'sha256': sha(archive.read(path)), 'sizeBytes': archive.getinfo(path).file_size,
             'directory': archive.getinfo(path).is_dir()} for path in sorted(archive.namelist())]


def inspect(store, ordinary, project, build_tools, ndk_bin):
    report = json.loads((store / 'android-build-v1.json').read_bytes())

    def content(kind):
        product = report[kind]
        path = store / product['sha256']
        data = path.read_bytes()
        require(path == Path(product['ownedPath']) and sha(data) == product['sha256']
                and len(data) == product['sizeBytes'], 'Retained content-addressed object differs: ' + kind)
        return path

    apk = content('unsignedAPK')
    symbols = content('debugSymbols')
    inventory = json.loads(content('resourceInventory').read_bytes())
    badging = run(build_tools / 'aapt2', 'dump', 'badging', apk)
    ordinary_badging = run(build_tools / 'aapt2', 'dump', 'badging', ordinary)
    identity_fields = ('package: ', 'launchable-activity: ', 'native-code: ', 'minSdkVersion:', 'targetSdkVersion:')
    identity = [line for line in badging.splitlines() if line.startswith(identity_fields)]
    require(identity == [line for line in ordinary_badging.splitlines() if line.startswith(identity_fields)],
            'APK identity differs from the ordinary Starter build')
    for prefix, expected, trailing in [
        ('package: ', f"name='{inventory['application']}'", r'(?: .*)?'),
        ('launchable-activity: ', f"name='{inventory['activity']}'", r'(?: .*)?'),
        ('native-code: ', f"'{inventory['abi']}'", ''),
        ('minSdkVersion:', f"'{inventory['minAPI']}'", ''),
        ('targetSdkVersion:', f"'{inventory['targetAPI']}'", ''),
    ]:
        matching = [line for line in identity if line.startswith(prefix)]
        require(len(matching) == 1 and re.fullmatch(re.escape(prefix + expected) + trailing, matching[0]),
                'APK badging differs from inventory: ' + prefix + expected)
    run(build_tools / 'zipalign', '-c', '-P', '16', '4', apk)
    signing = run(build_tools / 'apksigner', 'verify', apk, expected=1)
    require('DOES NOT VERIFY' in signing and 'Missing META-INF/MANIFEST.MF' in signing, 'Unexpected signing result')

    with (zipfile.ZipFile(apk) as retained, zipfile.ZipFile(ordinary) as baseline,
          zipfile.ZipFile(symbols) as debug, tempfile.TemporaryDirectory(prefix='android-elf-') as directory):
        require(inventory['entries'] == entries(retained), 'Inventory differs from APK entry paths, sizes or hashes')
        require(set(retained.namelist()) == set(baseline.namelist()), 'APK roster differs from ordinary Android build')
        libraries = {product['library'] for product in inventory['debugProducts']}
        require(set(debug.namelist()) == {p['debugPath'] for p in inventory['debugProducts']},
                'Debug ZIP roster differs')
        for path in retained.namelist():
            if path not in libraries:
                require(retained.read(path) == baseline.read(path), 'Unexpected ordinary APK payload change: ' + path)
        asset = 'assets/MixerAppearanceV2/descriptor.json'
        source = project / 'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json'
        require(retained.read(asset) == source.read_bytes(), 'APK appearance asset differs from the locked source')
        notices = sorted(path for path in retained.namelist() if path.startswith('third-party-notices/'))
        require(notices, 'APK carries no runtime notices')

        for item in inventory['debugProducts']:
            name = Path(item['library']).name
            binary, before, detached = (Path(directory) / (name + suffix) for suffix in ('.apk', '.ordinary', '.debug'))
            binary.write_bytes(retained.read(item['library']))
            before.write_bytes(baseline.read(item['library']))
            detached.write_bytes(debug.read(item['debugPath']))
            data = detached.read_bytes()
            require(sha(data) == item['sha256'] and len(data) == item['sizeBytes'], 'Debug ELF identity differs: ' + name)
            readelf = ndk_bin / 'llvm-readelf'
            for path in (binary, detached):
                notes = run(readelf, '--notes', path)
                require(re.findall(r'Build ID: ([a-f0-9]{40})\b', notes) == [item['buildId']],
                        'APK and debug ELF build ID differ: ' + name)
                header = run(readelf, '--file-header', path)
                require('ELF64' in header and 'AArch64' in header, 'Unexpected ELF architecture: ' + name)
            require('.debug_info' in run(readelf, '--sections', '--wide', detached), 'DWARF missing: ' + name)
            require('.debug_info' not in run(readelf, '--sections', '--wide', binary), 'DWARF still in APK: ' + name)
            require('No errors.' in run(ndk_bin / 'llvm-dwarfdump', '--verify', detached), 'DWARF verification was inconclusive')
            nm = ndk_bin / 'llvm-nm'
            symbols_for = lambda path: sorted(line.split()[:2] for line in run(
                nm, '-D', '--defined-only', '--format=posix', path).splitlines())
            require(symbols_for(binary) == symbols_for(before), 'Dynamic exports differ: ' + name)
            dynamic = run(readelf, '--dynamic', binary)
            require(re.findall(r'\(NEEDED\).*\[([^\]]+)\]', dynamic) == inventory['nativeDependencies'][name]
                    == re.findall(r'\(NEEDED\).*\[([^\]]+)\]', run(readelf, '--dynamic', before)),
                    'Native dependency ABI differs: ' + name)
            loads = [line.split()[-1] for line in run(readelf, '--program-headers', '--wide', binary).splitlines()
                     if line.lstrip().startswith('LOAD ')]
            require(loads and min(map(lambda value: int(value, 16), loads)) >= 16384,
                    'APK library LOAD alignment is below 16 KiB: ' + name)

    return {'identity': identity, 'entryCount': len(inventory['entries']), 'notices': notices,
            'appearanceSHA256': sha(source.read_bytes()), 'debugProducts': inventory['debugProducts'],
            'checked': ['artifact-bytes', 'badging', 'unsigned', 'zipalign-16KiB', 'exact-inventory',
                        'ordinary-roster-and-other-payloads', 'native-dynamic-exports-and-dependencies',
                        'ELF-build-IDs', 'ELF-load-alignment', 'verified-DWARF']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('store', 'ordinary', 'project', 'build_tools', 'ndk_bin'):
        parser.add_argument(name, type=Path)
    print(json.dumps(inspect(**vars(parser.parse_args())), sort_keys=True))


if __name__ == '__main__':
    main()
