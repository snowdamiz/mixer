#!/usr/bin/env python3
"""Replay the unchanged root probe using an explicitly qualified candidate."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
args = argparse.ArgumentParser()
args.add_argument('--candidate', required=True, type=int, choices=[3])
a = args.parse_args()
out = HERE / ('cold-recovery-replay-' + str(a.candidate))
out.mkdir(exist_ok=False)
base = ROOT / ('capability-activation/.build/transitions-qualified-2026-10-23-candidate-' + str(a.candidate))
native = base / 'native'
probe = HERE / 'negative-cold-interruption/ColdInterruptionProbe.swift'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
r = {
    'scope': 'Identical original root probe with borrowed signed fixture scaffold. Actual native boot/enable; controlled persisted close/reopen, not process-crash or physical evidence.',
    'candidate': a.candidate, 'python': sys.version, 'host': platform.platform(),
    'probe_sha256': sha(probe), 'driver_sha256': sha(Path(__file__)),
    'negative_receipt_sha256': sha(HERE / 'negative-cold-interruption/receipt.json'),
    'inputs': {str(p.relative_to(base / 'source')): sha(p) for p in (base / 'source/capability-activation/Sources/MixerCapabilityActivation').glob('*.swift')},
    'native_sha256': sha(native / 'lib/libmixer_vm_capability_experimental.a'),
    'products': {}, 'commands': [],
}


def save():
    (out / 'receipt.json').write_text(json.dumps(r, indent=2) + '\n')


def run(name, argv):
    start = time.monotonic()
    result = subprocess.run(argv, capture_output=True, timeout=60)
    log = out / (name + '.log')
    log.write_bytes(result.stdout + result.stderr)
    r['commands'].append({'name': name, 'command': argv, 'exit_code': result.returncode,
                          'seconds': time.monotonic() - start, 'log': log.name, 'log_sha256': sha(log)})
    save()
    print(name, result.returncode, result.stdout.decode()[:700], result.stderr.decode()[:1000], flush=True)
    return result.returncode


run('swift-version', ['swiftc', '--version'])
for mode in ['debug', 'release', 'tsan']:
    retained = base / ('retained-' + mode)
    products, maps = retained / 'products', retained / 'modulemaps'
    binary = base / ('root-cold-recovery-' + mode)
    r['products'][mode] = {str(f.relative_to(retained)): sha(f) for f in retained.rglob('*') if f.is_file() and not f.is_symlink()}
    flags = ['swiftc', '-swift-version', '6', '-warnings-as-errors', '-parse-as-library', '-I' + str(products),
             '-L' + str(products), '-lMixerCapabilityActivation', '-L' + str(native / 'lib'),
             '-lmixer_vm_capability_experimental', '-Xcc', '-I' + str(native / 'include')]
    for module in ['CMixerVMCapability', 'MixerCapabilityDurableIO', 'MixerCapabilityIO', 'MixerDurableIO']:
        flags += ['-Xcc', '-fmodule-map-file=' + str(maps / (module + '.modulemap'))]
    if mode == 'release': flags += ['-O']
    if mode == 'tsan': flags += ['-sanitize=thread']
    if run(mode + '-compile', flags + [str(probe), '-o', str(binary)]) == 0:
        r.setdefault('binaries', {})[mode] = {'path': str(binary), 'sha256': sha(binary)}
        for case in ['incomplete-before-effects', 'incomplete-after-effects', 'recorded-after-effects']:
            run(mode + '-' + case, [str(binary), str(base / 'source/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures'), case])
    if not all(sha(retained / n) == d for n, d in r['products'][mode].items()):
        raise RuntimeError('Retained dependencies changed')
r['status'] = 'all9 cold-recovery replays pass' if len(r['commands']) == 13 and all(c['exit_code'] == 0 for c in r['commands']) else 'failure preserved'
save()
raise SystemExit(0 if r['status'].startswith('all9') else 1)
