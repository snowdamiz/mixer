#!/usr/bin/env python3
"""Verify one retained bounded native-path receipt, with optional live-source match."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('candidate', type=Path)
parser.add_argument('--check-live', action='store_true')
args = parser.parse_args()
out = args.candidate.resolve()
if out.parent != HERE or not out.is_dir():
    parser.error('candidate must be a direct receipt directory under this verifier')
seal = json.loads((out / 'artifact-seal.json').read_text())
actual = {str(path.relative_to(out)): sha(path) for path in sorted(out.rglob('*'))
          if path.is_file() and path != out / 'artifact-seal.json'}
if actual != seal:
    raise SystemExit('FAIL retained artifact seal mismatch')
receipt = json.loads((out / 'receipt.json').read_text())
manifest = receipt['sourceManifest']
closure = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
if closure != receipt['sourceClosureSHA256'] or not receipt['sourceUnchanged']:
    raise SystemExit('FAIL bounded source closure mismatch')
for name, digest in manifest.items():
    if sha(out / 'inputs' / name) != digest:
        raise SystemExit('FAIL retained source ' + name)
    if args.check_live and sha(ROOT / name) != digest:
        raise SystemExit('FAIL live source ' + name)
for command in receipt['commands']:
    log = ROOT / command['output']
    if sha(log) != command['sha256']:
        raise SystemExit('FAIL command log ' + str(log))
if receipt['status'] not in ('passed-compile-and-native-emulator', 'passed-compile-native-pending'):
    raise SystemExit('FAIL receipt status ' + receipt['status'])
print('PASS artifact seal, bounded source closure and command logs; live=' + str(args.check_live))
print(receipt['status'], receipt['native'])
