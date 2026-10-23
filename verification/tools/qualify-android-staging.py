#!/usr/bin/env python3
"""Frozen local containment repair and unsigned APK qualification; no devices."""
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
REVISION = 'b588481e21c521e264826a5c442901b8157fc112'
OUT = ROOT / 'verification/android-staging-fix-2026-10-22'
OUT.mkdir(exist_ok=True)
LOCAL = pathlib.Path(tempfile.mkdtemp(prefix='android-staging-fix-', dir=ROOT / 'verification/local'))
SOURCE = LOCAL / 'source'
APP = LOCAL / 'Application'
HOST_ENV = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
ANDROID_ENV = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected(name):
    if name.startswith(('cli/', 'sdk/', 'updates/')):
        return '/verification/' not in name
    return name == 'native/android/engine/Package.swift' or name.startswith((
        'native/android/engine/Sources/', 'native/android/engine/Tests/',
        'native/android/bridge/', 'native/android/app/src/', 'native/android/contracts/'))


files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', REVISION], cwd=ROOT, text=True).splitlines()
manifest = {}
for name in sorted(filter(selected, files)):
    path = SOURCE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(subprocess.check_output(['git', 'show', REVISION + ':' + name], cwd=ROOT))
    manifest[name] = sha(path)
manifest_text = ''.join(value + '  ' + name + '\n' for name, value in manifest.items())
(OUT / 'source-manifest.sha256').write_text(manifest_text)
receipt = {
    'schema': 1, 'status': 'running', 'sourceRevision': REVISION,
    'sourceDigest': hashlib.sha256(manifest_text.encode()).hexdigest(),
    'sourceManifest': 'verification/android-staging-fix-2026-10-22/source-manifest.sha256',
    'sourceFiles': len(manifest), 'frozenSource': str(SOURCE), 'application': str(APP),
    'qualifier': {'path': str(pathlib.Path(__file__).relative_to(ROOT)), 'sha256': sha(pathlib.Path(__file__))},
    'commands': [],
    'scope': 'Static local staging containment, CLI/runtime host regression and actual unsigned Android arm64 APK build from immutable exported source. No concurrent same-user filesystem isolation or arbitrary package-code sandbox.',
    'pending': ['physical devices', 'signing/installability', 'independent CI APK build',
                'immutable published native packages', 'FieldLog D2', 'lifecycle/accessibility/performance/store/GA']
}


def save():
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


def run(name, args, android=False):
    args = list(map(str, args))
    output = OUT / (name + '.log')
    env = ANDROID_ENV if android else HOST_ENV
    with output.open('w') as stream:
        result = subprocess.run(args, cwd=SOURCE, env=env, stdout=stream, stderr=subprocess.STDOUT)
    receipt['commands'].append({'name': name, 'command': args, 'exitCode': result.returncode,
                                'developerDirectory': env['DEVELOPER_DIR'],
                                'output': str(output.relative_to(ROOT)), 'sha256': sha(output)})
    save()
    if result.returncode:
        raise RuntimeError(name + ' failed; see ' + str(output))
    print(name + ' passed', flush=True)


try:
    run('host-toolchain', ['/usr/bin/swift', '--version'])
    run('staging-normal', ['python3', '-B', '-m', 'unittest', 'discover', '-s', SOURCE / 'cli/build-tests', '-v'])
    run('staging-optimized', ['python3', '-O', '-B', '-m', 'unittest', 'discover', '-s', SOURCE / 'cli/build-tests', '-v'])
    run('cli-host', ['/usr/bin/swift', 'test', '--package-path', SOURCE / 'cli'])
    run('runtime-host', ['/usr/bin/swift', 'test', '--package-path', SOURCE / 'native/android/engine'])
    cli = SOURCE / 'cli/.build/debug/mixer'
    run('create', [cli, 'create', 'StagingFixed', '--directory', APP, '--application', 'dev.mixer.stagingfixed',
                   '--platform', 'android', '--sdk-path', SOURCE / 'sdk', '--android-adapter-path', SOURCE / 'native/android'], android=True)
    run('generated-host', ['/usr/bin/swift', 'test', '--package-path', APP / 'Platforms/Android'])
    run('android-build', [cli, 'build', '--platform', 'android', '--directory', APP], android=True)
    build = APP / '.mixer/android-build/build-receipt.json'
    record = json.loads(build.read_text())
    (OUT / 'build-receipt.json').write_bytes(build.read_bytes())
    apk = pathlib.Path(record['apk'])
    if sha(apk) != record['apk_sha256']:
        raise RuntimeError('APK differs from successful build receipt')
    # A real second build exercises SwiftPM's internal cache symlinks, not just a fixture.
    run('android-rebuild', [cli, 'build', '--platform', 'android', '--directory', APP], android=True)
    rebuilt = json.loads(build.read_text())
    (OUT / 'rebuild-receipt.json').write_bytes(build.read_bytes())
    if sha(apk) != rebuilt['apk_sha256']:
        raise RuntimeError('Rebuilt APK differs from receipt')
    receipt['apk'] = {key: rebuilt[key] for key in ['apk', 'apk_bytes', 'apk_sha256', 'apk_content_sha256']}
    receipt['buildReceipts'] = {name: sha(OUT / name) for name in ['build-receipt.json', 'rebuild-receipt.json']}
    for name, expected in manifest.items():
        if sha(SOURCE / name) != expected:
            raise RuntimeError('Frozen source changed: ' + name)
    receipt['status'] = 'passed scoped local containment and unsigned cross-build'
except Exception as error:
    receipt['status'] = 'failed'
    receipt['error'] = str(error)
    raise
finally:
    receipt['observedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()
