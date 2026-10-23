#!/usr/bin/env python3
"""Verify frozen default/stream/cache/execution feature configurations separately."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'feature-matrix-1'
OUT.mkdir(exist_ok=False)
base_path = HERE / 'combined-1/receipt.json'
base = json.loads(base_path.read_text())
source = Path(base['source'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(source / p) == h == sha(ROOT / p) for p, h in base['source_files'].items())
env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'], CARGO_TARGET_DIR=str(source.parent / 'target'))
r = {'started_utc': datetime.now(timezone.utc).isoformat(), 'driver_sha256': sha(Path(__file__)), 'source_receipt': str(base_path.relative_to(ROOT)), 'source_receipt_sha256': sha(base_path), 'source_tree_sha256': base['source_tree_sha256'], 'commands': [], 'scope': 'Separate host feature combinations on exactly the combined-1 immutable snapshot. No target execution/mobile/release qualification.'}
failed = False
for feature in ['', 'experimental-stream-validation', 'experimental-function-cache', 'experimental-span-execution']:
    for mode in ['debug', 'release']:
        name = (feature or 'default') + '-' + mode
        argv = ['cargo', 'test', '--locked', '--manifest-path', 'vm/Cargo.toml']
        if feature: argv += ['--features', feature]
        if mode == 'release': argv += ['--release']
        start = time.monotonic()
        result = subprocess.run(argv, cwd=source, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        log = OUT / (name + '.log')
        log.write_bytes(result.stdout)
        stable = all(sha(source / p) == h for p, h in base['source_files'].items())
        r['commands'].append({'name': name, 'argv': argv, 'cwd': str(source), 'environment': {'CARGO_TARGET_DIR': env['CARGO_TARGET_DIR']}, 'exit': result.returncode, 'seconds': time.monotonic() - start, 'source_stable': stable, 'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
        failed |= result.returncode != 0 or not stable
        (OUT / 'receipt.json').write_text(json.dumps(r, indent=2) + '\n')
        print(name, result.returncode, flush=True)
r.update(passed=not failed, completed_utc=datetime.now(timezone.utc).isoformat())
(OUT / 'receipt.json').write_text(json.dumps(r, indent=2) + '\n')
raise SystemExit(1 if failed else 0)
