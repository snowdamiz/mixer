#!/usr/bin/env python3
"""Link only the fixed owner dylib; no package graph or second native archive."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
parser.add_argument('--owner', required=True)
parser.add_argument('--mode', choices=['debug', 'release', 'tsan'], default='debug')
a = parser.parse_args()
if not re.fullmatch('[a-z0-9-]{1,64}', a.label): raise ValueError('label')
out = HERE / a.label
out.mkdir(exist_ok=False)
work = HERE / '.build' / a.label
work.mkdir(parents=True, exist_ok=False)
probe = work / 'ColdStartFlowProbe.swift'
probe.write_bytes((HERE / probe.name).read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
owner = ROOT / a.owner
r = json.loads(owner.read_text())
products = Path(r['artifacts'][a.mode]['module']['path']).parent
dependency = ROOT / ('capability-activation/.build/transitions-qualified-2026-10-23-candidate-3/retained-' + a.mode)
binary = work / 'probe'
record = {
    'scope': 'Four original root flows with credited transition signed-fixture scaffold; controlled wall clock, real monotonic/native/store. Synthetic milestone reports are not real UI/FieldLog evidence.',
    'owner': a.owner, 'mode': a.mode, 'python': sys.version, 'driver_sha256': sha(Path(__file__)),
    'owner_receipt_sha256': sha(owner), 'owner_source_manifest_sha256': r['source_manifest_sha256'],
    'probe_sha256': sha(probe), 'probe_source': str(probe),
    'production_inputs': {n: d for n, d in r['source_files'].items() if '/Sources/' in n},
    'artifacts': r['artifacts'][a.mode], 'commands': [],
}
for entry in r['artifacts'][a.mode].values():
    if sha(Path(entry['path'])) != entry['sha256']: raise RuntimeError('owner artifact changed')
for name, digest in r['source_files'].items():
    if sha(Path(r['export']) / name) != digest: raise RuntimeError('owner input changed: ' + name)
flags = ['swiftc', '-swift-version', '6', '-warnings-as-errors', '-parse-as-library',
         '-I', str(products), '-I', str(dependency / 'products'), '-L', str(products),
         '-lMixerCapabilityActivationColdStart', '-Xlinker', '-rpath', '-Xlinker', str(products)]
for module in ['CMixerVMCapability', 'MixerCapabilityDurableIO', 'MixerCapabilityIO', 'MixerDurableIO']:
    flags += ['-Xcc', '-fmodule-map-file=' + str(dependency / 'modulemaps' / (module + '.modulemap'))]
if a.mode == 'release': flags += ['-O']
if a.mode == 'tsan': flags += ['-sanitize=thread']


def save():
    (out / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')


def run(name, command):
    began = time.monotonic()
    result = subprocess.run(command, capture_output=True, timeout=60,
                            env=os.environ | {'DEVELOPER_DIR': '/Applications/Xcode.app/Contents/Developer'})
    log = out / (name + '.log')
    log.write_bytes(result.stdout + result.stderr)
    record['commands'].append({'name': name, 'command': command, 'exit_code': result.returncode,
                               'seconds': time.monotonic() - began, 'log': log.name, 'log_sha256': sha(log)})
    save()
    print(name, result.returncode, result.stdout.decode()[:4000], result.stderr.decode()[:3000], flush=True)
    return result.returncode


if run('compile', flags + [str(probe), '-o', str(binary)]) == 0:
    record['binary'] = {'path': str(binary), 'sha256': sha(binary)}
    run('execute', [str(binary), str(Path(r['export']) / 'capability-activation/Tests/MixerCapabilityActivationTests/Fixtures')])
record['status'] = 'four root flows passed' if len(record['commands']) == 2 and all(c['exit_code'] == 0 for c in record['commands']) else 'failure preserved'
save()
raise SystemExit(0 if record['status'].startswith('four') else 1)
