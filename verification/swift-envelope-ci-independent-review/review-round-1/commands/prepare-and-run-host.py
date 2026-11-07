#!/usr/bin/env python3
"""Independent byte audit and black-box host invocation; imports no candidate."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[4]
ROUND = Path(__file__).resolve().parents[1]
WORK = ROUND / 'portable-root'
RUNNER = REPO / 'scripts/ci/check-analyzer-envelope.py'
PACK = REPO / 'verification/swift-envelope-ci-pack'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def emit(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')


def utc():
    return datetime.now(timezone.utc).isoformat()


expected = {
    RUNNER: '4f5c6d64cb821b3fc1984794c96f81c8610c441ec47e3ff37cabb95b01fb43f1',
    PACK / 'manifest.json': '4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a',
    REPO / 'scripts/ci/tests/test_analyzer_envelope_runner.py': '97caf9f78553369f23c584e625723ae85255bd486adc7772501e01d04b883495',
    REPO / 'verification/swift-envelope-ci-implementation/seal.json': '5c871c7ca9de706b319f14689dc6f8b438b9f0b142ee310bd898efda511eecc1',
}
for path, value in expected.items():
    if digest(path) != value:
        raise RuntimeError('admitted input changed: ' + str(path))
manifest = json.loads((PACK / 'manifest.json').read_bytes())
actual = []
for path in sorted(PACK.rglob('*')):
    if path.is_symlink():
        raise RuntimeError('pack symlink: ' + str(path))
    if path.is_file() and path.name != 'manifest.json':
        actual.append({'path': path.relative_to(PACK).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)})
if actual != manifest['members']:
    raise RuntimeError('closed pack inventory differs')
originals = json.loads((PACK / 'inventories/selected-input-manifest.json').read_bytes())['inputs']
copies = []
for item in originals:
    for destination in item['packed_destinations']:
        path = PACK / destination
        if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise RuntimeError('selected original copy differs: ' + destination)
        copies.append(destination)
derived = json.loads((PACK / 'inventories/proposed-layout.json').read_bytes())['derived_test_only_files']
for item in derived:
    original = next(x for x in originals if x['path'] == item['original']['path'])
    source = PACK / original['packed_destinations'][0]
    data = source.read_bytes() + item['appendix_utf8'].encode()
    target = PACK / item['packed_path']
    if target.read_bytes() != data or hashlib.sha256(data).hexdigest() != item['sha256']:
        raise RuntimeError('derived construction differs')
(WORK / 'scripts/ci').mkdir(parents=True)
(WORK / 'verification').mkdir()
(WORK / 'runs').mkdir()
shutil.copyfile(RUNNER, WORK / 'scripts/ci/check-analyzer-envelope.py')
shutil.copytree(PACK, WORK / 'verification/swift-envelope-ci-pack')
audit = {
    'schema': 1, 'at': utc(), 'command': [sys.executable, '-B', str(Path(__file__).resolve())],
    'python_executable': sys.executable, 'python_version': sys.version,
    'git_version': subprocess.check_output(['git', '--version'], cwd=REPO, text=True).strip(),
    'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
    'committed_tree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=REPO, text=True).strip(),
    'os': platform.platform(), 'machine': platform.machine(),
    'admitted_inputs': [{'path': str(p.relative_to(REPO)), 'sha256': v} for p, v in expected.items()],
    'pack_members': actual, 'pack_member_count': len(actual), 'pack_member_bytes': sum(x['bytes'] for x in actual),
    'selected_original_count': len(originals), 'selected_original_bytes': sum(x['bytes'] for x in originals),
    'original_copies_verified': copies, 'derived_constructions_verified': derived,
    'portable_runner_sha256': digest(WORK / 'scripts/ci/check-analyzer-envelope.py'),
    'source_pack_tree_sha256': manifest['tree_sha256'],
    'scope': 'Byte-identical portable root copy; no helper import, model evaluation, native runtime or capture.',
}
emit(ROUND / 'input-audit.json', audit)
out = WORK / 'runs/actual-host'
argv = [sys.executable, '-B', str(WORK / 'scripts/ci/check-analyzer-envelope.py'), '--out', str(out)]
start = time.monotonic()
row = {'schema': 1, 'argv': argv, 'cwd': str(REPO), 'started_utc': utc(), 'timeout_seconds': 600,
       'runner_sha256': digest(RUNNER), 'source_pack_tree_sha256': manifest['tree_sha256']}
with (ROUND / 'actual-host.stdout').open('xb') as stdout, (ROUND / 'actual-host.stderr').open('xb') as stderr:
    result = subprocess.run(argv, cwd=REPO, stdout=stdout, stderr=stderr, timeout=600)
row.update({'exit': result.returncode, 'finished_utc': utc(), 'elapsed_seconds': round(time.monotonic()-start,6)})
for name in ('stdout','stderr'):
    path = ROUND / ('actual-host.' + name)
    row[name] = {'path': path.name, 'bytes': path.stat().st_size, 'sha256': digest(path)}
emit(ROUND / 'actual-host-command.json', row)
print(json.dumps({'status': 'independent-actual-host-returned', 'exit': result.returncode, 'elapsed_seconds': row['elapsed_seconds'], 'receipt': str(out / 'receipt.json')}, sort_keys=True))
sys.exit(result.returncode)
