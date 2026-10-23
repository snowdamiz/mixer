#!/usr/bin/env python3
"""Compile only the current activation target against retained frozen dependencies."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, time
ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
p = argparse.ArgumentParser(); p.add_argument('--name', required=True); a = p.parse_args()
out = OWN / a.name; out.mkdir(exist_ok=False)
work = OWN / '.build' / a.name; work.mkdir(parents=True, exist_ok=False)
base = ROOT / 'capability-activation/.build/transitions-qualified-2026-10-23-candidate-2'
products = base / 'retained-debug/products'; maps = base / 'retained-debug/modulemaps'; native = base / 'native'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
paths = sorted((ROOT / 'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))
sources = {str(v.relative_to(ROOT)): sha(v) for v in paths}
for path in paths: (out / (path.name + '.txt')).write_bytes(path.read_bytes())
command = ['swiftc', '-swift-version', '6', '-warnings-as-errors', '-enable-testing', '-parse-as-library', '-whole-module-optimization', '-module-name', 'MixerCapabilityActivation', '-I' + str(products), '-Xcc', '-I' + str(native / 'include')]
for name in ['CMixerVMCapability', 'MixerCapabilityDurableIO', 'MixerCapabilityIO', 'MixerDurableIO']:
    command += ['-Xcc', '-fmodule-map-file=' + str(maps / (name + '.modulemap'))]
command += ['-emit-module', '-emit-module-path', str(work / 'MixerCapabilityActivation.swiftmodule'), '-emit-object', '-o', str(work / 'MixerCapabilityActivation.o')] + [str(v) for v in paths]
began = time.monotonic()
r = subprocess.run(command, cwd=ROOT, env=os.environ | {'DEVELOPER_DIR': '/Applications/Xcode.app/Contents/Developer'}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
(out / 'compile.log').write_bytes(r.stdout)
record = {'scope': 'Development direct target-only compile; current active-lane source snapshot, not final qualification. No SwiftPM graph or native rebuild.', 'sources': sources, 'command': command, 'cwd': str(ROOT), 'environment': {'DEVELOPER_DIR': '/Applications/Xcode.app/Contents/Developer'}, 'exitCode': r.returncode, 'elapsedSeconds': time.monotonic() - began, 'logSHA256': sha(out / 'compile.log'), 'sourcesUnchanged': all(sha(ROOT / name) == digest for name, digest in sources.items()), 'dependencyProducts': {str(v): sha(v) for v in sorted(products.glob('*.o')) if v.name != 'MixerCapabilityActivation.o'}, 'nativeSHA256': sha(native / 'lib/libmixer_vm_capability_experimental.a'), 'output': str(work)}
if r.returncode == 0: record['compiledProducts'] = {str(v): sha(v) for v in work.glob('*') if v.is_file()}
(out / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
print(r.stdout.decode()); print('compile', r.returncode)
raise SystemExit(r.returncode)
