#!/usr/bin/env python3
"""Freeze a named official Android API/source closure; never run Android."""
from pathlib import Path
import base64
import concurrent.futures
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SDK = Path('/opt/homebrew/share/android-commandlinetools')
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')


def identity(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    official = HERE / 'official'
    official.mkdir(exist_ok=True)
    inventory = {'collected_at': datetime.datetime.now(datetime.UTC).isoformat(), 'python': sys.version,
                 'provenance': 'Installed official SDK plus enumerated android.googlesource.com platform source',
                 'commands': [], 'installed': [], 'remote': []}
    for name in ['platforms/android-37.0/source.properties', 'platforms/android-37.0/data/api-versions.xml',
                 'platforms/android-36/source.properties', 'platforms/android-36/data/api-versions.xml',
                 'build-tools/37.0.0/source.properties']:
        source = SDK / name
        dest = official / 'sdk' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        inventory['installed'].append(identity(source) | {'snapshot': str(dest.relative_to(HERE))})
    for name in ['platforms/android-37.0/android.jar', 'platforms/android-36/android.jar',
                 'build-tools/37.0.0/d8', 'build-tools/37.0.0/lib/d8.jar']:
        inventory['installed'].append(identity(SDK / name))
    for name in ['java', 'javac', 'javap']:
        tool = JDK / 'bin' / name
        inventory['installed'].append(identity(tool.resolve()))
        args = [str(tool), '-version']
        run = subprocess.run(args, text=True, capture_output=True, check=False)
        inventory['commands'].append({'argv': args, 'exit': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr})
        if run.returncode:
            raise RuntimeError(args)
    for api in ['37.0', '36']:
        args = [str(JDK / 'bin/javap'), '-p', '-s', '-constants', '-classpath', str(SDK / f'platforms/android-{api}/android.jar'),
                'android.view.inputmethod.InputConnection', 'android.view.inputmethod.InputConnectionWrapper',
                'android.view.inputmethod.BaseInputConnection', 'android.view.inputmethod.EditorInfo',
                'android.view.inputmethod.TextBoundsInfoResult']
        run = subprocess.run(args, text=True, capture_output=True, check=False)
        stdout = official / f'javap-sdk{api}.txt'
        stdout.write_text(run.stdout)
        inventory['commands'].append({'argv': args, 'exit': run.returncode, 'stdout_file': str(stdout.relative_to(HERE)), 'stderr': run.stderr})
        if run.returncode:
            raise RuntimeError(args)
    # Explicit source roster, not a repository/tree scan. These are platform references,
    # not copied Mixer implementation, fixtures, dependencies or generated product code.
    tags = {28: 'android-9.0.0_r1', 29: 'android-10.0.0_r1', 30: 'android-11.0.0_r1',
            31: 'android-12.0.0_r1', 32: 'android-12.1.0_r1', 33: 'android-13.0.0_r1',
            34: 'android-14.0.0_r1', 35: 'android-15.0.0_r1', 36: 'android-16.0.0_r1'}
    roster = [(api, tag, f'core/java/android/view/inputmethod/{name}.java')
              for api, tag in tags.items() for name in ['InputConnection', 'InputConnectionWrapper']]
    roster += [(36, tags[36], 'core/java/com/android/internal/inputmethod/EditableInputConnection.java'),
               (36, tags[36], 'core/java/android/view/inputmethod/BaseInputConnection.java'),
               (36, tags[36], 'core/java/android/widget/TextView.java')]

    def fetch(item):
        api, tag, path = item
        url = f'https://android.googlesource.com/platform/frameworks/base/+/refs/tags/{tag}/{path}?format=TEXT'
        with urllib.request.urlopen(url, timeout=30) as response:
            data = base64.b64decode(response.read(), validate=True)
        dest = official / 'aosp' / str(api) / Path(path).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return {'api': api, 'tag': tag, 'url': url, 'snapshot': str(dest.relative_to(HERE)),
                'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

    # Independent source reads only, bounded to 4 requests.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        inventory['remote'] = list(pool.map(fetch, roster))
    classes = {}
    api_root = ET.parse(official / 'sdk/platforms/android-37.0/data/api-versions.xml').getroot()
    names = ['android/view/inputmethod/InputConnection', 'android/view/inputmethod/InputConnectionWrapper',
             'android/view/inputmethod/SurroundingText', 'android/view/inputmethod/TextAttribute',
             'android/view/inputmethod/TextSnapshot', 'android/view/inputmethod/TextBoundsInfoResult',
             'android/view/inputmethod/HandwritingGesture', 'android/view/inputmethod/PreviewableHandwritingGesture',
             'android/view/inputmethod/EditorInfo']
    for name in names:
        node = next(c for c in api_root.findall('class') if c.attrib['name'] == name)
        classes[name] = {'attributes': node.attrib, 'members': [{'kind': c.tag, **c.attrib} for c in node]}
    # Adjacent preflight APIs only: exact setter signatures and floors.
    for name, prefixes in [('android/widget/TextView', ['setTextCursorDrawable(', 'setTextSelectHandle(', 'setTextSelectHandleLeft(', 'setTextSelectHandleRight(']),
                           ('android/view/View', ['setStateDescription('])]:
        node = next(c for c in api_root.findall('class') if c.attrib['name'] == name)
        classes[name] = {'attributes': node.attrib, 'members': [{'kind': c.tag, **c.attrib} for c in node if any(c.attrib.get('name', '').startswith(p) for p in prefixes)]}
    (HERE / 'api-inventory.json').write_text(json.dumps(classes, indent=2) + '\n')
    (HERE / 'official-inputs.json').write_text(json.dumps(inventory, indent=2) + '\n')
    print(f'Frozen {len(roster)} named official source files; SDK36/37 method descriptors and API floors recorded.')


if __name__ == '__main__':
    main()
