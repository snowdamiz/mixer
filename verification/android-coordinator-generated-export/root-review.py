#!/usr/bin/env python3
"""Root offline closure and actual APK symbol/DEX inspection."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE / 'candidate-3'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    bindings, commands = {}, []

    def bind(path, expected=None):
        actual = sha(path)
        assert expected is None or actual == expected, str(path)
        bindings[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)] = actual

    def run(name, argv):
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        for stream in ['stdout', 'stderr']:
            output = HERE / ('root-' + name + '.' + stream)
            output.write_text(getattr(result, stream))
            bind(output)
        commands.append({'name': name, 'argv': argv, 'exitCode': result.returncode})
        assert result.returncode == 0, (name, result.stderr)
        return result.stdout

    run('offline', ['python3', str(HERE / 'review.py'), 'candidate-3'])
    offline = json.loads((CANDIDATE / 'offline-review.json').read_text())
    for name, expected in offline['bindings'].items():
        bind(ROOT / name, expected)
    manifest = json.loads((CANDIDATE / 'source-manifest.json').read_text())
    for name, expected in manifest.items():
        bind(ROOT / name, expected)
    receipt = json.loads((CANDIDATE / 'receipt.json').read_text())
    app = json.loads((CANDIDATE / 'baseline/build-receipt.json').read_text())
    assert receipt['liveCapturedInputChanges'] == []
    tools = app['toolchain']['tools']
    for name in ['nm', 'dexdump']:
        bind(Path(tools[name]['path']), tools[name]['sha256'])
    with tempfile.TemporaryDirectory(prefix='mixer-root-export-inspect-') as temporary:
        temporary = Path(temporary)
        with zipfile.ZipFile(CANDIDATE / 'baseline/CoordinatorApp-unsigned.apk') as archive:
            (temporary / 'classes.dex').write_bytes(archive.read('classes.dex'))
            (temporary / 'libAppAndroid.so').write_bytes(archive.read('lib/arm64-v8a/libAppAndroid.so'))
        dex = run('dex', [tools['dexdump']['path'], '-d', str(temporary / 'classes.dex')])
        assert "Class descriptor  : 'Ldev/mixer/android/NativeCoordinatorV2;'" in dex
        for forbidden in ['NativeCoordinatorV2HostTests', 'NativeCoordinatorV2IntegrationActivity',
                          'NativeCoordinatorV2IntegrationInstrumentation', 'AdapterInstrumentation']:
            assert forbidden not in dex, forbidden
        exports = run('exports', [tools['nm']['path'], '-D', '--defined-only', str(temporary / 'libAppAndroid.so')])
        names = {line.split()[-1] for line in exports.splitlines() if line.split()}
        assert len(receipt['ordinaryCExports']) == 6
        assert set(receipt['ordinaryCExports']) <= names
    bind(Path(__file__))
    bind(HERE / 'review.py')
    bind(CANDIDATE / 'offline-review.json')
    result = {
        'status': 'accepted-generated-private-coordinator-export-cross-build-scope',
        'reviewer': 'root integrator', 'pythonVersion': platform.python_version(),
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'sourceTreeSHA256': receipt['sourceTreeSHA256'], 'sourceInputs': len(manifest),
        'bindings': bindings, 'commands': commands,
        'coordinatorClassSHA256': receipt['compiledCoordinatorClassSHA256'],
        'apkSHA256': app['apk_sha256'], 'minAPI': 28, 'privateNativeAPIFloor': 36,
        'decision': 'Accept exact private coordinator source export and source-lock coverage; fresh unsigned generated arm64 APK cross-build and offline contents pass. Public V1 Activity/bootstrap remains unchanged.',
        'nativeRuntime': False, 'physicalAcceptance': False, 'gaAcceptance': False,
        'publicV2OptIn': False, 'signedPresentation': False
    }
    (HERE / 'root-acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['bindings', 'commands']}))


if __name__ == '__main__':
    main()
