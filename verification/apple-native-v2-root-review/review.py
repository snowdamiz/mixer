#!/usr/bin/env python3
"""Replay sealed Apple source/artifacts and its pure host helper; never run UIKit."""
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/apple-native-appearance-v2/headless-cover-final-coordinates'
INDEPENDENT = ROOT / 'verification/native-v2-transaction-independent-review/apple-headless-review-2'
bindings = {}


def read(path):
    data = path.read_bytes()
    bindings[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return data


def obj(path):
    return json.loads(read(path))


def main():
    lock = obj(PRODUCER / 'source-lock.json')['sha256']
    result = obj(PRODUCER / 'result.json')
    assert len(lock) == 36
    closure = hashlib.sha256(json.dumps(lock, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert closure == result['sourceClosureSHA256'] == '81a376c19b38281a5e82a033e67b17f98dd1e09aab7e8f4fbed932263a6adc56'
    assert result['hostPureExecuted'] and not result['nativeExecuted'] and not result['guiExecuted']
    for name, digest in lock.items():
        assert hashlib.sha256(read(ROOT / name)).hexdigest() == digest, name
    archive = obj(PRODUCER / 'source-archive.json')
    raw = read(PRODUCER / archive['archive'])
    assert hashlib.sha256(raw).hexdigest() == archive['sha256']
    with tarfile.open(fileobj=io.BytesIO(raw)) as stream:
        members = stream.getmembers()
        assert len(members) == len(lock) and {m.name for m in members} == set(lock)
        for member in members:
            assert member.isfile()
            assert hashlib.sha256(stream.extractfile(member).read()).hexdigest() == lock[member.name]
    independent = obj(INDEPENDENT / 'receipt.json')
    # Explicitly bind the reviewer's entire receipt closure, including current
    # source copies, actual Mach-O identities and historical failed-coordinate evidence.
    assert independent['status'] == 'passed-apple-headless-source-and-artifact-review-native-pending'
    assert independent['nativeAcceptance'] is False
    for name, digest in independent['evidenceSHA256'].items():
        assert hashlib.sha256(read(ROOT / name)).hexdigest() == digest, name
    artifacts = obj(PRODUCER / 'artifact-manifest.json')
    raw = read(PRODUCER / artifacts['archive'])
    assert hashlib.sha256(raw).hexdigest() == artifacts['sha256']
    contents = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as stream:
        for member in stream.getmembers():
            assert member.isfile() and member.name not in contents
            data = stream.extractfile(member).read()
            assert artifacts['files'][member.name] == {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            contents[member.name] = data
    assert set(contents) == set(artifacts['files'])
    # Only three explicitly named macOS members are extracted and executed.
    host_names = ['cover-geometry-definitions', 'libMixerCore.dylib', 'libMixerUI.dylib']
    target = Path(tempfile.mkdtemp(prefix='mixer-apple-v2-root-pure-'))
    for name in host_names:
        path = target / name
        path.write_bytes(contents['host/' + name])
        path.chmod(0o755)
    env = dict(os.environ, DYLD_LIBRARY_PATH=str(target), DYLD_PRINT_LIBRARIES='1')
    argv = [str(target / host_names[0])]
    process = subprocess.run(argv, cwd=target, env=env, capture_output=True, text=True)
    (HERE / 'host-stdout.json').write_text(process.stdout)
    (HERE / 'host-stderr.log').write_text(process.stderr)
    assert process.returncode == 0, process.stderr
    outcomes = json.loads(process.stdout)
    assert outcomes == obj(PRODUCER / 'host-pure-stdout.json')
    assert len(outcomes) == 8 and all(item['passed'] for item in outcomes)
    for name in host_names[1:]:
        assert str(target / name) in process.stderr, ('archived-library-not-loaded', name)
    assert 'UIKit' not in process.stderr
    for name, digest in lock.items():
        assert hashlib.sha256(read(ROOT / name)).hexdigest() == digest
    for name in ['review.py', 'host-stdout.json', 'host-stderr.log']:
        read(HERE / name)
    receipt = {
        'status': 'accepted-headless-source-compile-and-pure-geometry-only',
        'reviewer': 'root', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'sourceClosureSHA256': closure, 'sourceFiles': len(lock),
        'pythonVersion': platform.python_version(), 'bindings': bindings,
        'pureHostReplay': {'argv': argv, 'cwd': str(target), 'exitCode': process.returncode,
                           'environment': {'DYLD_LIBRARY_PATH': str(target), 'DYLD_PRINT_LIBRARIES': '1'},
                           'archivedLibrariesLoaded': host_names[1:], 'passed': len(outcomes)},
        'nativeAcceptance': False, 'guiExecuted': False, 'gaAcceptance': False,
        'limitations': ['iOS consumer and harness compiled, never executed for this source.',
                        '12pt switch cover is not a proven bound on native glass.',
                        'Held/cancel/input/accessibility/IME/style and excluded RTL contexts remain pending.',
                        'Public bootstrap, signed path and engine/native integration remain separate.'],
    }
    (HERE / 'acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'bindings': len(bindings), 'pureHostPassed': len(outcomes)}))


if __name__ == '__main__':
    main()
