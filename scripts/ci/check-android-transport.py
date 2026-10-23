#!/usr/bin/env python3
"""Portable host regressions for the private Android transport; no devices."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--cc', default='cc')
parser.add_argument('--ndk', required=True, type=Path)
parser.add_argument('--sysroot', type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
source = out / 'source'
source.mkdir()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
includes = list(args.ndk.glob('toolchains/llvm/prebuilt/*/sysroot/usr/include'))
if len(includes) != 1 or not (includes[0] / 'android/looper.h').is_file():
    raise SystemExit('One official NDK sysroot with android/looper.h is required')
include = includes[0].resolve()
cc = Path(shutil.which(args.cc) or args.cc).resolve(strict=True)
transport = Path('native/android/signed-guest-ui/transport')
paths = [p.relative_to(root) for p in (root / transport).rglob('*')
         if p.is_file() and p.suffix in ('.c', '.h')]
paths += [Path('verification/android-transport-review/probes.c'),
          Path('verification/android-facade-transport-review/probes.c')]
manifest = {}
for relative in sorted(paths):
    dest = source / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes((root / relative).read_bytes())
    dest.chmod(0o444)
    manifest[str(relative)] = sha(dest)
receipt = {'observed_utc': datetime.now(timezone.utc).isoformat(),
           'command': sys.argv, 'python': platform.python_version(),
           'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
           'source_files': manifest, 'collector_sha256': sha(Path(__file__)),
           'compiler': str(cc), 'compiler_sha256': sha(cc),
           'looper_header': str(include / 'android/looper.h'),
           'looper_header_sha256': sha(include / 'android/looper.h'),
           'commands': [], 'counts': {},
           'scope': 'Strict Debug/Release host simulation of C transport and fixed Android Looper adapter hooks. No actual Looper/Swift/JNI/device/display execution or GA acceptance.'}


def save():
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


def run(name, argv):
    argv = [str(x) for x in argv]
    result = subprocess.run(argv, cwd=source, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=45)
    log = out / (name + '.log')
    log.write_bytes(result.stdout)
    receipt['commands'].append({'name': name, 'argv': argv, 'cwd': str(source),
                                'exit': result.returncode, 'log': str(log), 'sha256': sha(log)})
    save()
    if result.returncode != 0:
        raise RuntimeError(f'{name}: exit {result.returncode}; see {log}')
    return result.stdout.decode()


flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wpedantic', '-Wconversion',
         '-Wsign-conversion', '-Wstrict-prototypes', '-pthread',
         '-DMIXER_UI_TRANSPORT_TESTING=1', '-idirafter', include]
if args.sysroot:
    flags += ['-isysroot', args.sysroot]
adapter = transport / 'platform_android.c'
progress = transport / 'tests/progress_probe.c'
suites = {
    'original': ([transport / 'tests/host_tests.c', progress], 'MXUIT_CASE_PASS', 26),
    'prior-review': ([adapter, paths[-2], progress], 'ANDROID_TRANSPORT_REVIEW_PASS', 9),
    'facade': ([adapter, transport / 'tests/facade_tests.c'], 'MXUIT_FACADE_PASS', 27),
    'facade-review': ([adapter, paths[-1]], 'MXUIT_REVIEW_PASS', 11),
}
try:
    receipt['compiler_version'] = run('compiler-version', [cc, '--version'])
    for mode, optimization in [('debug', ['-O0', '-g']), ('release', ['-O2', '-DNDEBUG'])]:
        for suite, (inputs, marker, expected) in suites.items():
            name = mode + '-' + suite
            binary = out / name
            run(name + '-build', [cc, *flags, *optimization, transport / 'transport.c', *inputs, '-o', binary])
            cases = run(name + '-list', [binary, '--list']).splitlines()
            if len(cases) != expected or len(set(cases)) != expected:
                raise RuntimeError('Unexpected case inventory: ' + name)
            for index, case in enumerate(cases):
                result = run(f'{name}-{index:02}', [binary, case])
                if f'{marker} {case} ' not in result:
                    raise RuntimeError('Missing explicit pass marker: ' + name + '/' + case)
            receipt['counts'][name] = len(cases)
            receipt.setdefault('artifacts', {})[str(binary)] = sha(binary)
            print(name, len(cases), 'passed', flush=True)
    for relative, digest in manifest.items():
        if sha(root / relative) != digest or sha(source / relative) != digest:
            raise RuntimeError('Source changed: ' + relative)
    receipt['result'] = 'passed'
finally:
    save()
