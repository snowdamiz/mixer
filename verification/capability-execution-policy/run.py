#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
inputs = json.loads((HERE / 'inputs.json').read_text())
source = Path(inputs['source'])
native = Path(inputs['native'])
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def unchanged():
    for path, expected in inputs['files'].items():
        if digest(source / path) != expected: raise RuntimeError(path)
    for path in ['capability-activation/Sources/MixerCapabilityActivation/CapabilityExecutionPolicy.swift',
                 'capability-activation/Tests/MixerCapabilityActivationTests/ExecutionPolicyTests.swift']:
        if digest(ROOT / path) != inputs['files'][path]: raise RuntimeError(path)
unchanged()
receipt = {'status': 'running', 'source_manifest_sha256': inputs['source_manifest_sha256'], 'commands': [], 'scope': inputs['scope']}
def save(): (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
for name, extra in [('debug', []), ('release', ['-c', 'release'])]:
    argv = ['swift', 'test', '--package-path', str(source / 'capability-activation'), '--scratch-path', str(source.parent / 'build'),
        '-Xcc', '-I' + str(native / 'include'), '-Xlinker', '-L' + str(native / 'lib'), '-Xswiftc', '-warnings-as-errors'] + extra
    start = time.monotonic()
    result = subprocess.run(argv, cwd=source, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = HERE / (name + '.log'); log.write_bytes(result.stdout)
    receipt['commands'].append({'name': name, 'argv': argv, 'cwd': str(source), 'exit_code': result.returncode,
        'seconds': time.monotonic() - start, 'log_sha256': digest(log)})
    unchanged(); save(); print(name, result.returncode, flush=True)
    if result.returncode:
        receipt['status'] = 'development failure preserved'; save(); raise SystemExit(result.returncode)
receipt['status'] = 'host tests passed'; receipt['source_unchanged'] = True; save()
