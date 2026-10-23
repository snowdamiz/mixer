#!/usr/bin/env python3
"""Check the root-owned descriptor overlay on the clean pushed VM source."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / '.build/source'
INPUTS = json.loads((ROOT / 'inputs.json').read_text())
ENV = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])

def verify_inputs():
    actual = {str(p.relative_to(SOURCE)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in SOURCE.rglob('*') if p.is_file() and 'target' not in p.parts}
    if actual != INPUTS['files']:
        raise RuntimeError('Frozen source changed')

verify_inputs()
commands = [
    ['rustc', '-Vv'], ['cargo', '-V'],
    ['cargo', 'test', '--locked', '--manifest-path', 'vm/Cargo.toml', '--features', 'experimental-swift-reactor'],
    ['cargo', 'test', '--locked', '--release', '--manifest-path', 'vm/Cargo.toml', '--features', 'experimental-swift-reactor'],
]
for features in ['experimental-swift-reactor', 'experimental-function-cache',
                 'experimental-span-execution',
                 'experimental-stream-validation,experimental-function-cache,experimental-span-execution,experimental-swift-wasi,experimental-swift-reactor,experimental-capability-native']:
    commands.append(['cargo', 'clippy', '--locked', '--manifest-path', 'vm/Cargo.toml',
                     '--lib', '--features', features, '--', '-D', 'warnings'])
results = []
for index, argv in enumerate(commands):
    log = ROOT / f'{index:02d}.log'
    if log.exists():
        raise RuntimeError(f'Refusing to overwrite {log}')
    started = time.time()
    with log.open('x') as stream:
        result = subprocess.run(argv, cwd=SOURCE, env=ENV, stdout=stream, stderr=subprocess.STDOUT)
    results.append({'argv': argv, 'cwd': str(SOURCE), 'exit_code': result.returncode,
                    'duration_seconds': time.time()-started, 'log': log.name,
                    'sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
    print(index, result.returncode, ' '.join(argv), flush=True)
    if result.returncode:
        break
verify_inputs()
receipt = {
    'baseline': INPUTS['baseline'], 'overlay': INPUTS['overlay'],
    'inputs_sha256': hashlib.sha256((ROOT/'inputs.json').read_bytes()).hexdigest(),
    'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'commands': results, 'passed': len(results) == len(commands) and all(x['exit_code'] == 0 for x in results),
    'scope': 'Host minimal-feature tests and descriptor cfg/dead-code lint repair. No cache candidate or executor implementation included; no target execution, device or GA qualification.'
}
(ROOT/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
raise SystemExit(0 if receipt['passed'] else 1)
