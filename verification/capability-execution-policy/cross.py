#!/usr/bin/env python3
"""Compile the frozen policy target with official iOS and Android SDKs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
inputs = json.loads((HERE / 'inputs.json').read_text())
source = Path(inputs['source'])
old = json.loads((ROOT / 'verification/capability-durable-io/cross-receipt.json').read_text())
record = {'status': 'running', 'commands': [], 'artifacts': {},
          'source_manifest_sha256': inputs['source_manifest_sha256'], 'scope': 'Official module/object compilation only; no application link or execution.'}
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def unchanged():
    for path, expected in inputs['files'].items():
        if digest(source / path) != expected: raise RuntimeError(path)
def save(): (HERE / 'cross-receipt.json').write_text(json.dumps(record, indent=2) + '\n')
unchanged()
for command in old['commands']:
    name = command['name']
    args = [x.replace('/durable-io-qualified/', '/execution-policy/') for x in command['argv']]
    result = subprocess.run(args, cwd=source, env=dict(os.environ, **command['environment']), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = HERE / (name + '.log'); log.write_bytes(result.stdout)
    record['commands'].append({'name': name, 'argv': args, 'cwd': str(source), 'environment': command['environment'],
        'exit_code': result.returncode, 'log_sha256': digest(log)})
    unchanged(); save(); print(name, result.returncode, flush=True)
    if result.returncode:
        record['status'] = 'failed preserved'; save(); raise SystemExit(result.returncode)
    work = source.parent / name
    paths = [p for p in work.rglob('*') if p.is_file() and p.name in
             ['CapabilityExecutionPolicy.o', 'CapabilityExecutionPolicy.swift.o', 'MixerCapabilityActivation.swiftmodule']]
    if len(paths) != 2: raise RuntimeError('expected actual policy object and module: ' + name)
    record['artifacts'][name] = {str(p): digest(p) for p in paths}
    save()
record['status'] = 'passed'; record['source_unchanged'] = True; save()
