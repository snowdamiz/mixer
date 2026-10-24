#!/usr/bin/env python3
"""Read-only input capture for the authored-toggle contract. No native tools/Git."""
import datetime
import hashlib
import json
import pathlib
import platform
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
EXPECTED_DIAGNOSIS_SEAL = '802e1939b44e43237471732c89bfd6132f4678622d5899ad759be35219e93e44'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def capture():
    seal_path = ROOT / 'verification/android-pointer-native-diagnosis/packet-seal.json'
    seal_bytes = seal_path.read_bytes()
    assert sha(seal_bytes) == EXPECTED_DIAGNOSIS_SEAL
    sealed = json.loads(seal_bytes)['files']
    assert len(sealed) == 20
    for path, expected in sealed.items():
        data = (ROOT / path).read_bytes()
        assert len(data) == expected['bytes'] and sha(data) == expected['sha256'], path
    paths = set(sealed) | {'verification/android-pointer-native-diagnosis/packet-seal.json'}
    paths.update([
        'AGENTS.md', 'mixer-product-plan.md',
        'docs/android-pointer-native-checkpoint.md',
        'docs/android-native-input-matrix-contract.md',
        'docs/apple-authored-toggle-contract.md',
        'verification/apple-authored-toggle-contract/candidate-2-directional-pan/source/Prototype/TogglePanPolicy.swift',
        'verification/apple-authored-toggle-contract/candidate-2-directional-pan/receipt.json',
        'verification/android-pointer-native-root-review/receipt.json',
        'verification/android-pointer-timing-correction/runtime/runtime-1/receipt.json',
        'verification/android-pointer-timing-correction/runtime/runtime-1/pointer-sequence-3.json',
        'verification/android-pointer-timing-correction/runtime/runtime-1/pointer-observations.jsonl',
        'verification/android-pointer-timing-correction/oracle.py',
        'verification/android-pointer-timing-correction/runner-contract.json',
        'verification/android-pointer-oracle-repair/CoordinatorJoinInstrumentation.java',
        'verification/android-pointer-oracle-repair/CoordinatorJoinActivity.java',
        'verification/android-coordinator-join/operations.json',
    ])
    for name in ('NativeAppearanceViewsV2', 'NativeRenderer', 'NativeCoordinatorV2',
                 'NativeEnvironmentV2', 'AppearanceGeometryV2', 'AppearanceDescriptorV2',
                 'AppearanceResolverV2'):
        paths.add(f'native/android/app/src/dev/mixer/android/{name}.java')
    bindings = {}
    for name in sorted(paths):
        data = (ROOT / name).read_bytes()
        destination = OUT / 'inputs' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        bindings[name] = {'bytes': len(data), 'sha256': sha(data), 'snapshot': str(destination.relative_to(OUT))}
    # Every source used by this lane is retained, rather than importing production code.
    write_json(OUT / 'input-bindings.json', bindings)
    closure = sha(json.dumps({k:v['sha256'] for k,v in bindings.items()}, sort_keys=True, separators=(',', ':')).encode())
    commands = [
        ['python3', '--version'],
        ['uname', '-srm'],
        ['sed', '-n', '332,347p', 'mixer-product-plan.md'],
        ['sed', '-n', '75,90p', 'native/android/app/src/dev/mixer/android/NativeRenderer.java'],
        ['sed', '-n', '95,108p', 'native/android/app/src/dev/mixer/android/NativeRenderer.java'],
        ['sed', '-n', '130,145p', 'native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java'],
        ['sed', '-n', '601,625p', 'native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java'],
        ['sed', '-n', '215,238p', 'verification/android-pointer-oracle-repair/CoordinatorJoinInstrumentation.java'],
    ]
    executions = []
    for index, argv in enumerate(commands):
        result = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        filename = f'commands/read-{index + 1:02}.log'
        (OUT / filename).parent.mkdir(exist_ok=True)
        (OUT / filename).write_bytes(result.stdout)
        executions.append({'argv': argv, 'cwd': str(ROOT), 'exitCode': result.returncode, 'output': filename,
                           'outputSHA256': sha(result.stdout)})
        assert result.returncode == 0
    refs = [
        ('android-viewgroup.html', 'https://developer.android.com/develop/ui/views/touch-and-input/gestures/viewgroup'),
        ('android-viewconfiguration.html', 'https://developer.android.com/reference/android/view/ViewConfiguration'),
        ('android-compoundbutton.html', 'https://developer.android.com/reference/android/widget/CompoundButton'),
    ]
    fetched = []
    for filename, url in refs:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mixer independent contract evidence capture'})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
            metadata = {'url': url, 'resolvedURL': response.url, 'status': response.status,
                        'contentType': response.headers.get('Content-Type'), 'bytes': len(data), 'sha256': sha(data),
                        'tool': 'Python standard-library urllib.request.urlopen', 'timeoutSeconds': 30,
                        'requestHeaders': {'User-Agent': 'Mixer independent contract evidence capture'},
                        'output': 'official-specs/' + filename}
        destination = OUT / metadata['output']
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes(data)
        fetched.append(metadata)
    write_json(OUT / 'official-specs/fetch-receipt.json', fetched)
    write_json(OUT / 'capture-receipt.json', {
        'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve())],
        'pythonVersion': sys.version, 'pythonExecutable': sys.executable,
        'pythonExecutableSHA256': sha(pathlib.Path(sys.executable).resolve().read_bytes()),
        'host': platform.platform(), 'sourceInputClosureSHA256': closure, 'sourceInputs': len(bindings),
        'sourceRevisionPolicy': 'No Git invoked; frozen candidate and runner identities are retained from bound prior receipts. Current source identity is the copied input closure, not an asserted Git commit.',
        'diagnosisSealSHA256': sha(seal_bytes), 'diagnosisFilesVerified': len(sealed), 'commands': executions,
        'nativeCommands': 0, 'gitCommands': 0, 'physicalTargetsQueried': False,
        'productionImplementationChanged': False, 'scope': 'Read-only sources and official public documentation for a proposed contract only',
    })
    output = json.dumps({'status': 'captured', 'sourceInputs': len(bindings), 'diagnosisFilesVerified': len(sealed), 'inputClosureSHA256': closure})
    (OUT / 'commands/capture.log').write_text(output + '\n')
    print(output)

if __name__ == '__main__':
    capture()
