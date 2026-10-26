#!/usr/bin/env python3
"""Compile the unselected signature experiment. This never loads Android code."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import struct
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK = Path('/opt/homebrew/share/android-commandlinetools')


def main():
    output = HERE / 'cross-compile'
    output.mkdir(exist_ok=True)
    records = []

    def run(args):
        result = subprocess.run(list(map(str, args)), cwd=HERE, capture_output=True, text=True,
                                env=os.environ | {'JAVA_HOME': str(JDK)})
        index = len(records) + 1
        (output / f'command-{index}.stdout.txt').write_text(result.stdout)
        (output / f'command-{index}.stderr.txt').write_text(result.stderr)
        records.append({'argv': list(map(str, args)), 'exit': result.returncode,
                        'stdout': f'cross-compile/command-{index}.stdout.txt',
                        'stderr': f'cross-compile/command-{index}.stderr.txt'})
        if result.returncode:
            raise RuntimeError(result.stderr)
        return result.stdout

    with tempfile.TemporaryDirectory(prefix='mixer-editor-signature-') as temporary:
        scratch = Path(temporary)
        classes = scratch / 'classes'
        classes.mkdir()
        run([JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
             '-classpath', SDK / 'platforms/android-37.0/android.jar', '-d', classes,
             HERE / 'prototype/SignatureShape.java', HERE / 'prototype/EditorInfoShape.java'])
        names = [str(p.relative_to(classes)).removesuffix('.class').replace('/', '.')
                 for p in sorted(classes.rglob('*.class'))]
        text = run([JDK / 'bin/javap', '-p', '-s', '-c', '-verbose', '-classpath', classes, *names])
        (output / 'classes.javap.txt').write_text(text)
        jar = output / 'signature-shape.jar'
        with zipfile.ZipFile(jar, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob('*.class')):
                info = zipfile.ZipInfo(str(path.relative_to(classes)), date_time=(1980, 1, 1, 0, 0, 0))
                archive.writestr(info, path.read_bytes())
        dex = scratch / 'dex'
        dex.mkdir()
        run([SDK / 'build-tools/37.0.0/d8', '--min-api', '28', '--lib',
             SDK / 'platforms/android-37.0/android.jar', '--output', dex, jar])
        data = (dex / 'classes.dex').read_bytes()
        (output / 'classes.dex').write_bytes(data)
        # DEX header/class definition metadata only. Not an ART verifier or loader.
        count = struct.unpack_from('<I', data, 96)[0]
        assert count >= len(names), (count, names)
        artifacts = {str(p.relative_to(HERE)): {'bytes': p.stat().st_size,
                     'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in [jar, output / 'classes.dex', output / 'classes.javap.txt']}
        receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.UTC).isoformat(),
                   'scope': 'Unselected method/signature shape only; no Mixer code executed',
                   'commands': records, 'java_classes': names, 'dex_class_defs': count,
                   'artifacts': artifacts, 'owned_scratch_removed': True,
                   'Android_runtime_or_classloading_or_OTA_authorization': False}
        (HERE / 'cross-compile.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Signature-only Java17/SDK37 and D8 min28 compiled; owned host scratch removed. No ART/native execution.')


if __name__ == '__main__':
    main()
