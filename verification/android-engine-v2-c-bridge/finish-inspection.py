#!/usr/bin/env python3
"""Finish candidate-1's tool-discovery failure without repeating passed builds."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OLD = HERE / 'candidate-1'
OUT = HERE / 'inspection-completion'
OUT.mkdir(exist_ok=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


receipt = json.loads((OLD / 'receipt.json').read_text())
assert receipt['status'] == 'failed' and receipt['failure'].startswith('AssertionError([PosixPath(')
manifest = json.loads((OLD / 'source-manifest.json').read_text())
assert sha(OLD / 'source-manifest.json') == receipt['sourceManifestSHA256']
assert sha(OLD / 'source.tar.gz') == receipt['sourceArchiveSHA256']
bindings = 2
with tarfile.open(OLD / 'source.tar.gz') as archive:
    for name, expected in manifest.items():
        assert hashlib.sha256(archive.extractfile(name).read()).hexdigest() == expected, name
        if name != 'verification/android-engine-v2-c-bridge/verify.py':
            assert sha(ROOT / name) == expected, name
        bindings += 1
for command in receipt['commands']:
    assert command['exitCode'] == 0 and sha(ROOT / command['log']) == command['sha256']
    bindings += 1
assert receipt['commands'][-1]['label'] == 'android-link'
for path, expected in receipt['artifacts'].items():
    assert sha(ROOT / path) == expected, path
    bindings += 1
for mode in ['debug', 'release']:
    assert receipt[mode + 'CAssertions'] == 77
    assert (OLD / (mode + '-c-run.log')).read_text() == 'PASS 77 C ABI assertions\n'
nm = Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-nm')
commands = []
for label, argv in [('nm-version', [nm, '--version']),
                    ('android-symbols', [nm, '--defined-only', '--dynamic', OLD / 'artifacts/android/libMixerAndroidEngine.so'])]:
    result = subprocess.run(list(map(str, argv)), cwd=ROOT, capture_output=True)
    log = OUT / (label + '.log')
    log.write_bytes(result.stdout + result.stderr)
    commands.append({'argv': list(map(str, argv)), 'cwd': str(ROOT), 'exitCode': result.returncode,
                     'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
    assert result.returncode == 0
symbols = (OUT / 'android-symbols.log').read_text()
for name in ['prepare', 'commit', 'abort']:
    assert re.search(r'\bT mixer_android_' + name + r'_v2$', symbols, re.M)
completion = {
    'status': 'passed-c-abi-and-android-export-inspection',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevision': receipt['sourceRevision'], 'verifiedBindings': bindings,
    'originalReceiptSHA256': sha(OLD / 'receipt.json'),
    'originalFailure': 'All compilation and execution commands passed; collector searched unrelated Android SDK NDK installations instead of the Swift SDK bundled NDK r27d.',
    'repair': 'Use the official Swift SDK bundled llvm-nm, inspect the unchanged retained arm64 library; preserve the failed original receipt. No product, C client, binary, or previous output changes.',
    'correctedCollectorSHA256': sha(HERE / 'verify.py'),
    'completionScriptSHA256': sha(Path(__file__)), 'nmSHA256': sha(nm),
    'commands': commands, 'hostCAssertionsPerMode': 77, 'hostModes': ['debug', 'release'],
    'cppHeaderAndLinkExecutions': 2,
    'scope': receipt['scope'], 'pending': receipt['pending'], 'gaPass': False,
}
(OUT / 'receipt.json').write_text(json.dumps(completion, indent=2) + '\n')
print(json.dumps({'status': completion['status'], 'bindings': bindings, 'CAssertionsPerMode': 77}))
