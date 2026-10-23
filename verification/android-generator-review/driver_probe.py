#!/usr/bin/env python3
"""Independent bounded driver negative probes; writes only review-owned temporary fixtures."""
import hashlib
import json
import pathlib
import runpy
import subprocess
import sys

OUT = pathlib.Path(__file__).resolve().parent
BASE = OUT / '.local/driver-probes'
BASE.mkdir(parents=True, exist_ok=True)
DRIVER = OUT / '.local/source/cli/Sources/MixerBuild/Resources/android-build.py'
module = runpy.run_path(str(DRIVER))
config = {'schema': 1, 'name': 'SafeApp', 'application': 'dev.mixer.review', 'language': 'swift', 'targets': ['ios', 'android'], 'toolchainLock': 'mixer.lock', 'capabilities': [], 'updates': {'activation': 'cold-start', 'compatibility': 'exact-runtime-fingerprint', 'requireArtifactSignature': True, 'requireAssignmentSignature': True}}
empty = hashlib.sha256(b'').hexdigest()
results = []

def fixture(name):
    root = BASE / name
    for relative in ['Generated/MixerSDK', 'Generated/MixerAndroid', 'Resources']:
        (root / relative).mkdir(parents=True)
    (root / 'mixer.lock').write_text(json.dumps({'schema': 1, 'sdkDigest': empty, 'android': {'adapterDigest': empty, 'toolchain': {}}}))
    (root / 'mixer.yml').write_text(json.dumps(config))
    return root

def run(name, root, expected_message=None, preserved=None):
    command = [sys.executable, str(DRIVER), 'build', str(root)]
    p = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = OUT / ('driver-' + name + '.log'); log.write_text(p.stdout)
    result = {'name': name, 'command': command, 'exit_code': p.returncode, 'output': log.name, 'output_sha256': hashlib.sha256(p.stdout.encode()).hexdigest(), 'expected_message_observed': expected_message is None or expected_message in p.stdout}
    if preserved is not None: result['sentinels_preserved'] = {str(path.relative_to(BASE)): path.exists() and path.read_text() == 'sentinel' for path in preserved}
    results.append(result)
    return result

for index, unsafe in enumerate(['../../victim', '/tmp/review-victim', 'a/b', 'a;command', 'A\n', 'A' * 65]):
    root = fixture('name-' + str(index)); bad = dict(config); bad['name'] = unsafe
    (root / 'mixer.yml').write_text(json.dumps(bad))
    result = run('name-' + str(index), root, 'Invalid Android application name')
    assert result['exit_code'] != 0 and result['expected_message_observed'] and not (root / '.mixer').exists()
for key, value in [('targets', ['android', 'android']), ('capabilities', ['storage.files']), ('updates', {'activation': 'hot'})]:
    root = fixture('bad-' + key); bad = dict(config); bad[key] = value
    (root / 'mixer.yml').write_text(json.dumps(bad))
    result = run('bad-' + key, root)
    assert result['exit_code'] != 0 and not (root / '.mixer').exists()
root = fixture('resource'); (root / 'Resources/required.txt').write_text('required')
assert run('resource', root, 'resources cannot be omitted')['expected_message_observed']
root = fixture('source-drift'); (root / 'Generated/MixerSDK/mutation.swift').write_text('// changed')
assert run('source-drift', root, 'differs from mixer.lock')['expected_message_observed']
for placement in ['mixer-parent', 'build-output']:
    root = fixture('symlink-' + placement)
    external = BASE / ('external-' + placement); external.mkdir()
    output = external / 'android-build' if placement == 'mixer-parent' else external
    output.mkdir(exist_ok=True)
    sentinels = [output / 'build-receipt.json', output / 'SafeApp-unsigned.apk']
    for path in sentinels: path.write_text('sentinel')
    if placement == 'mixer-parent': (root / '.mixer').symlink_to(external, target_is_directory=True)
    else:
        (root / '.mixer').mkdir(); (root / '.mixer/android-build').symlink_to(external, target_is_directory=True)
    run('symlink-' + placement, root, preserved=sentinels)
# Direct distribution-tree coverage rejects untracked escaping directory content.
distribution = BASE / 'distribution'; distribution.mkdir(); outside = BASE / 'tool-outside'; outside.mkdir()
(distribution / 'external').symlink_to(outside, target_is_directory=True)
try: module['tree'](distribution); raise AssertionError('Directory escape accepted')
except RuntimeError as error:
    assert 'symlink escapes hashed root' in str(error)
    results.append({'name': 'tool-directory-symlink-escape', 'rejected': True, 'message': str(error)})
(OUT / 'driver-probe-results.json').write_text(json.dumps({'driver_sha256': hashlib.sha256(DRIVER.read_bytes()).hexdigest(), 'results': results}, indent=2) + '\n')
print(json.dumps(results[-3:], indent=2))
