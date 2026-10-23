#!/usr/bin/env python3
"""Original bounded close-race probes; link only the exact frozen owner dylib."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=['debug', 'release', 'tsan'], required=True)
a = parser.parse_args()
out = HERE / ('2026-10-23-' + a.mode)
work = HERE / '.build' / ('2026-10-23-' + a.mode)
out.mkdir(exist_ok=False)
work.mkdir(parents=True, exist_ok=False)
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
owner_path = ROOT / 'verification/capability-cold-start-runtime/2026-10-23-candidate-1/receipt.json'
seal_path = ROOT / 'verification/capability-cold-start-runtime/final-receipt.json'
owner = json.loads(owner_path.read_text())
assert owner['source_manifest_sha256'] == '68177f0a8488386138c8e9f2a92c7ea7d4c788caf74b7053c8f648179f95c078'
assert sha(seal_path) == '32d31ae27e2665dd92ba6d4e0fcfed59a9402ff18bc2a64004518c7d5db69661'
products = Path(owner['artifacts'][a.mode]['module']['path']).parent
dependency = ROOT / ('capability-activation/.build/transitions-qualified-2026-10-23-candidate-3/retained-' + a.mode)
probe = work / 'ColdStartCommitCloseProbe.swift'
probe.write_bytes((HERE / probe.name).read_bytes())
binary = work / 'probe'
record = {
    'scope': 'Two original real health-commit / repeated public close races; signed TESTONLY fixture scaffold credited to root review and transition candidate3. Synthetic embedding milestones; real monotonic clock, store, native VM and lifecycle. No production source changes or publication.',
    'mode': a.mode, 'python': sys.version,
    'source_manifest_sha256': owner['source_manifest_sha256'],
    'baseline_revision': owner.get('baseline_revision'),
    'owner_receipt_sha256': sha(owner_path), 'owner_final_seal_sha256': sha(seal_path),
    'driver_sha256': sha(__file__), 'probe_sha256': sha(probe),
    'credited_scaffold_path': 'verification/capability-cold-start-runtime-root-review/ColdStartFlowProbe.swift',
    'artifacts': owner['artifacts'][a.mode], 'commands': [],
    'limitations': ['Controlled synchronous filesystem boundary holds do not prove all scheduler interleavings.',
                    'No physical iOS/Android device tools or runs; those gates remain pending.',
                    'Swift TSan excludes uninstrumented Rust and system frameworks.',
                    'Synthetic embedding milestone reports do not qualify UI, FieldLog, publication, customer or GA gates.'],
}


def save():
    (out / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')


def verify():
    for entry in owner['artifacts'][a.mode].values():
        assert sha(entry['path']) == entry['sha256'], 'owner artifact changed'
    for name, digest in owner['source_files'].items():
        assert sha(Path(owner['export']) / name) == digest, 'frozen owner source changed: ' + name
        assert sha(ROOT / name) == digest, 'workspace owner source changed: ' + name
    assert sha(seal_path) == record['owner_final_seal_sha256'], 'owner final seal changed'


def run(name, command, timeout=60):
    began = time.monotonic()
    result = subprocess.run(command, capture_output=True, timeout=timeout,
                            env=os.environ | {'DEVELOPER_DIR': '/Applications/Xcode.app/Contents/Developer'})
    log = out / (name + '.log')
    log.write_bytes(result.stdout + result.stderr)
    record['commands'].append({'name': name, 'command': command, 'cwd': str(ROOT),
        'environment': {'DEVELOPER_DIR': '/Applications/Xcode.app/Contents/Developer'},
        'exit_code': result.returncode, 'seconds': time.monotonic() - began,
        'log': log.name, 'log_sha256': sha(log)})
    save()
    print(name, result.returncode, result.stdout.decode()[:6000], result.stderr.decode()[:3000], flush=True)
    return result.returncode


verify()
run('swift-version', ['swiftc', '--version'])
run('xcode-version', ['xcodebuild', '-version'])
flags = ['swiftc', '-swift-version', '6', '-warnings-as-errors', '-parse-as-library',
         '-I', str(products), '-I', str(dependency / 'products'), '-L', str(products),
         '-lMixerCapabilityActivationColdStart', '-Xlinker', '-rpath', '-Xlinker', str(products)]
for module in ['CMixerVMCapability', 'MixerCapabilityDurableIO', 'MixerCapabilityIO', 'MixerDurableIO']:
    flags += ['-Xcc', '-fmodule-map-file=' + str(dependency / 'modulemaps' / (module + '.modulemap'))]
if a.mode == 'release': flags += ['-O']
if a.mode == 'tsan': flags += ['-sanitize=thread']
if run('compile', flags + [str(probe), '-o', str(binary)]) == 0:
    record['binary'] = {'path': str(binary), 'sha256': sha(binary)}
    run('defined-native-symbols', ['nm', '-gU', str(binary)])
    symbols = (out / 'defined-native-symbols.log').read_text()
    assert 'mixer_vm_capability_' not in symbols, 'probe contains duplicate native implementation'
    run('linked-libraries', ['otool', '-L', str(binary)])
    run('execute', [str(binary), str(Path(owner['export']) / 'capability-activation/Tests/MixerCapabilityActivationTests/Fixtures'), str(out / 'state')])
verify()
record['frozen_inputs_unchanged'] = True
record['state_files'] = {str(p.relative_to(out)): sha(p) for p in sorted((out / 'state').rglob('*')) if p.is_file()}
record['status'] = 'two original close race cases passed' if len(record['commands']) == 6 and all(c['exit_code'] == 0 for c in record['commands']) else 'failed experiment preserved'
record['completed_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
save()
raise SystemExit(0 if record['status'].startswith('two') else 1)
